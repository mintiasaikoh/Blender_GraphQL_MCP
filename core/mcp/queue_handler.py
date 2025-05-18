"""
Queue Handler for Blender MCP
適切なキュー管理システムの実装
"""

import bpy
import threading
import queue
import json
import time
import uuid
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Task:
    """タスクデータクラス"""
    id: str
    type: str
    command: str
    metadata: Dict[str, Any]
    created_at: datetime
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    completed_at: Optional[datetime] = None

class QueueHandler:
    """
    キュー管理システム
    - 複数のリクエストをキューに貯める
    - 順次処理
    - 結果の非同期取得
    """
    
    def __init__(self, max_queue_size: int = 100):
        # タスクキュー
        self.task_queue = queue.Queue(maxsize=max_queue_size)
        
        # タスク情報の保存
        self.tasks: Dict[str, Task] = {}
        self.task_lock = threading.Lock()
        
        # 結果待ちのイベント
        self.result_events: Dict[str, threading.Event] = {}
        
        # 処理ステータス
        self.processing = False
        self.current_task: Optional[Task] = None
        
        # タイマー
        self.timer = None
        
    def submit_task(self, command: str, task_type: str = "execute", 
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        タスクをキューに追加
        
        Returns:
            タスクID
        """
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            type=task_type,
            command=command,
            metadata=metadata or {},
            created_at=datetime.now()
        )
        
        # タスクを保存
        with self.task_lock:
            self.tasks[task_id] = task
            self.result_events[task_id] = threading.Event()
        
        # キューに追加
        try:
            self.task_queue.put(task, block=False)
        except queue.Full:
            with self.task_lock:
                task.status = "failed"
                task.error = "Queue is full"
            raise Exception("Task queue is full")
        
        # 処理を開始
        if not self.processing:
            self.start_processing()
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Task]:
        """タスクの状態を取得"""
        with self.task_lock:
            return self.tasks.get(task_id)
    
    def wait_for_result(self, task_id: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """
        タスクの完了を待つ
        
        Args:
            task_id: タスクID
            timeout: タイムアウト時間（秒）
        
        Returns:
            結果またはNone
        """
        event = self.result_events.get(task_id)
        if not event:
            return None
        
        # 結果を待つ
        if event.wait(timeout):
            with self.task_lock:
                task = self.tasks.get(task_id)
                if task:
                    return {
                        "id": task.id,
                        "status": task.status,
                        "result": task.result,
                        "error": task.error
                    }
        
        return None
    
    def start_processing(self):
        """処理を開始"""
        if not self.processing:
            self.processing = True
            self.timer = bpy.app.timers.register(self._process_queue, first_interval=0.1)
    
    def stop_processing(self):
        """処理を停止"""
        self.processing = False
        if self.timer:
            try:
                bpy.app.timers.unregister(self._process_queue)
            except:
                pass
    
    def _process_queue(self) -> Optional[float]:
        """
        キューを処理（メインスレッド）
        
        Returns:
            次回実行までの時間（秒）、またはNone（停止）
        """
        try:
            # キューからタスクを取得（ノンブロッキング）
            task = self.task_queue.get_nowait()
            self.current_task = task
            
            # タスクのステータスを更新
            with self.task_lock:
                task.status = "processing"
            
            # タスクを実行
            try:
                result = self._execute_task(task)
                
                # 成功
                with self.task_lock:
                    task.status = "completed"
                    task.result = result
                    task.completed_at = datetime.now()
                
            except Exception as e:
                # エラー
                with self.task_lock:
                    task.status = "failed"
                    task.error = str(e)
                    task.completed_at = datetime.now()
            
            # 完了イベントをセット
            event = self.result_events.get(task.id)
            if event:
                event.set()
            
            self.current_task = None
            
        except queue.Empty:
            # キューが空
            if not self.processing:
                return None  # タイマー停止
        
        except Exception as e:
            print(f"Queue processing error: {e}")
        
        return 0.05  # 50ms後に再実行
    
    def _execute_task(self, task: Task) -> Dict[str, Any]:
        """タスクを実行"""
        if task.type == "execute":
            return self._execute_command(task.command, task.metadata)
        elif task.type == "get_state":
            return self._get_state()
        elif task.type == "batch":
            return self._execute_batch(task.metadata.get("commands", []))
        else:
            raise ValueError(f"Unknown task type: {task.type}")
    
    def _execute_command(self, command: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """コマンドを実行"""
        from core.blender_mcp import get_blender_mcp
        mcp = get_blender_mcp()
        
        # Pythonコードか自然言語か判別
        if 'import bpy' in command or 'bpy.' in command:
            from core.mcp_command_processor import get_mcp_processor
            processor = get_mcp_processor()
            result = processor.process_raw_command(command, metadata)
        else:
            result = mcp.process_natural_command(command)
        
        return result
    
    def _get_state(self) -> Dict[str, Any]:
        """Blenderの状態を取得"""
        from core.blender_context import get_context_manager
        context = get_context_manager()
        return context.get_complete_context()
    
    def _execute_batch(self, commands: List[str]) -> Dict[str, Any]:
        """バッチコマンドを実行"""
        results = []
        for command in commands:
            try:
                result = self._execute_command(command, {})
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        
        return {"batch_results": results}
    
    def get_queue_status(self) -> Dict[str, Any]:
        """キューの状態を取得"""
        with self.task_lock:
            pending_tasks = [t for t in self.tasks.values() if t.status == "pending"]
            processing_tasks = [t for t in self.tasks.values() if t.status == "processing"]
            completed_tasks = [t for t in self.tasks.values() if t.status == "completed"]
            failed_tasks = [t for t in self.tasks.values() if t.status == "failed"]
            
            return {
                "queue_size": self.task_queue.qsize(),
                "pending": len(pending_tasks),
                "processing": len(processing_tasks),
                "completed": len(completed_tasks),
                "failed": len(failed_tasks),
                "current_task": self.current_task.id if self.current_task else None,
                "tasks": {
                    task.id: {
                        "status": task.status,
                        "type": task.type,
                        "created_at": task.created_at.isoformat(),
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None
                    }
                    for task in self.tasks.values()
                }
            }
    
    def clear_completed_tasks(self):
        """完了したタスクをクリア"""
        with self.task_lock:
            completed_ids = [
                task_id for task_id, task in self.tasks.items()
                if task.status in ["completed", "failed"]
            ]
            
            for task_id in completed_ids:
                del self.tasks[task_id]
                if task_id in self.result_events:
                    del self.result_events[task_id]

# グローバルインスタンス
_queue_handler = None

def get_queue_handler() -> QueueHandler:
    """キューハンドラーのシングルトン"""
    global _queue_handler
    if _queue_handler is None:
        _queue_handler = QueueHandler()
    return _queue_handler