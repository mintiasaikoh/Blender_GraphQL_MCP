"""
タスクキューモジュール
重い処理をバックグラウンドで実行するためのキューシステム
"""

import threading
import queue
import time
import uuid
import json
import logging
from typing import Dict, Any, List, Callable, Optional, Union
from enum import Enum

# ロギング設定
logger = logging.getLogger('unified_mcp.task_queue')

# タスク状態の定義
class TaskStatus(Enum):
    PENDING = "pending"     # キューに入っているが未実行
    RUNNING = "running"     # 実行中
    COMPLETED = "completed" # 正常完了
    FAILED = "failed"       # 失敗
    CANCELLED = "cancelled" # キャンセル済み

class Task:
    """
    キューに追加される非同期タスクを表すクラス
    """
    
    def __init__(self, task_type: str, 
                 params: Dict[str, Any], 
                 callback: Optional[Callable] = None,
                 priority: int = 0,
                 name: Optional[str] = None):
        """
        タスクを初期化
        
        Args:
            task_type: タスクの種類
            params: タスクパラメータ
            callback: タスク完了時に呼び出されるコールバック関数（オプション）
            priority: 優先度（値が大きいほど優先）
            name: タスク名（オプション）
        """
        self.id = str(uuid.uuid4())
        self.type = task_type
        self.params = params
        self.callback = callback
        self.priority = priority
        self.name = name or f"Task_{self.id[:8]}"
        
        self.status = TaskStatus.PENDING
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.progress = 0.0  # 0.0 - 1.0
        self.message = "タスクがキューに追加されました"
    
    def to_dict(self) -> Dict[str, Any]:
        """タスク情報を辞書として返す"""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error if self.error else None,
            "params": self.params,  # 注意: 機密情報が含まれる場合は除外すべき
        }
    
    def update_progress(self, progress: float, message: Optional[str] = None) -> None:
        """タスクの進捗を更新"""
        self.progress = max(0.0, min(1.0, progress))  # 0.0-1.0に制限
        if message:
            self.message = message
        logger.debug(f"タスク '{self.name}' の進捗を更新: {self.progress:.1%} {message or ''}")

class TaskQueue:
    """
    非同期タスクの処理キュー
    """
    
    def __init__(self, num_workers: int = 2, polling_interval: float = 0.5):
        """
        タスクキューを初期化
        
        Args:
            num_workers: ワーカースレッドの数
            polling_interval: ポーリング間隔（秒）
        """
        self.task_queue = queue.PriorityQueue()
        self.tasks = {}  # タスクID -> タスク
        self.lock = threading.RLock()  # スレッドセーフな操作のためのロック
        self.polling_interval = polling_interval
        self.workers = []
        self.num_workers = num_workers
        self.running = False
        self.task_handlers = {}  # タスクタイプ -> ハンドラー関数
        
        logger.info(f"タスクキューを初期化しました（ワーカー数: {num_workers}）")
    
    def register_task_handler(self, task_type: str, handler: Callable) -> None:
        """タスクハンドラーを登録"""
        with self.lock:
            if task_type in self.task_handlers:
                logger.warning(f"タスクハンドラー '{task_type}' は既に登録されています。上書きします。")
            self.task_handlers[task_type] = handler
            logger.info(f"タスクハンドラー '{task_type}' を登録しました")
    
    def add_task(self, task: Task) -> str:
        """
        タスクをキューに追加
        
        Args:
            task: 追加するタスク
            
        Returns:
            タスクID
        """
        with self.lock:
            # タスクを登録
            self.tasks[task.id] = task
            
            # キューに追加（優先度の高いものが先に処理されるよう負の値）
            self.task_queue.put((-task.priority, task.id))
            logger.info(f"タスク '{task.name}' (ID: {task.id}) をキューに追加しました")
            
            return task.id
    
    def create_and_add_task(self, task_type: str, params: Dict[str, Any], 
                           priority: int = 0, name: Optional[str] = None) -> str:
        """
        タスクを作成してキューに追加
        
        Args:
            task_type: タスクの種類
            params: タスクパラメータ
            priority: 優先度
            name: タスク名（オプション）
            
        Returns:
            タスクID
        """
        task = Task(task_type, params, priority=priority, name=name)
        return self.add_task(task)
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        タスク情報を取得
        
        Args:
            task_id: 取得するタスクのID
            
        Returns:
            タスク情報の辞書
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                return task.to_dict()
            return None
    
    def get_all_tasks(self, filter_status: Optional[Union[TaskStatus, List[TaskStatus]]] = None) -> List[Dict[str, Any]]:
        """
        全タスクの情報を取得
        
        Args:
            filter_status: フィルタするステータス（オプション）
            
        Returns:
            タスク情報のリスト
        """
        with self.lock:
            tasks = []
            for task_id, task in self.tasks.items():
                # ステータスフィルタが指定されている場合
                if filter_status:
                    if isinstance(filter_status, list) and task.status not in filter_status:
                        continue
                    elif not isinstance(filter_status, list) and task.status != filter_status:
                        continue
                
                tasks.append(task.to_dict())
            
            # 作成時間順でソート
            tasks.sort(key=lambda x: x["created_at"], reverse=True)
            return tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """
        タスクをキャンセル
        
        Args:
            task_id: キャンセルするタスクのID
            
        Returns:
            キャンセル成功したかどうか
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            # 既に完了または失敗しているタスクはキャンセル不可
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                return False
            
            # 実行中のタスクは中断できない（実装方法による）
            if task.status == TaskStatus.RUNNING:
                logger.warning(f"実行中のタスク '{task.name}' (ID: {task.id})はキャンセルできません")
                return False
            
            # ペンディング状態のタスクをキャンセル
            task.status = TaskStatus.CANCELLED
            task.message = "タスクがキャンセルされました"
            logger.info(f"タスク '{task.name}' (ID: {task.id})をキャンセルしました")
            return True
    
    def clear_completed_tasks(self, max_age_seconds: int = 3600) -> int:
        """
        完了・失敗・キャンセルされたタスクをクリア
        
        Args:
            max_age_seconds: この秒数より古いタスクのみ削除
            
        Returns:
            削除されたタスク数
        """
        with self.lock:
            current_time = time.time()
            to_remove = []
            
            for task_id, task in self.tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    # 完了時間がない場合は作成時間を使用
                    end_time = task.completed_at or task.created_at
                    if current_time - end_time > max_age_seconds:
                        to_remove.append(task_id)
            
            # 削除実行
            for task_id in to_remove:
                del self.tasks[task_id]
            
            logger.info(f"{len(to_remove)}個の古いタスクをクリアしました")
            return len(to_remove)
    
    def start(self) -> None:
        """ワーカースレッドを開始"""
        if self.running:
            logger.warning("タスクキューは既に実行中です")
            return
        
        with self.lock:
            self.running = True
            
            # ワーカースレッドを作成
            self.workers = []
            for i in range(self.num_workers):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"TaskQueueWorker-{i}",
                    daemon=True  # デーモンスレッドとして作成
                )
                self.workers.append(worker)
                worker.start()
                logger.info(f"ワーカースレッド {i+1}/{self.num_workers} を開始しました")
            
            logger.info(f"タスクキューを開始しました（ワーカー数: {self.num_workers}）")
    
    def stop(self) -> None:
        """ワーカースレッドを停止"""
        if not self.running:
            logger.warning("タスクキューは既に停止しています")
            return
        
        with self.lock:
            self.running = False
            logger.info("タスクキューに停止シグナルを送信しました")
            
            # すべてのワーカースレッドが終了するのを待つ（最大5秒）
            for i, worker in enumerate(self.workers):
                if worker.is_alive():
                    worker.join(timeout=5.0)
                    if worker.is_alive():
                        logger.warning(f"ワーカースレッド {i+1} は5秒以内に終了しませんでした")
            
            self.workers = []
            logger.info("タスクキューを停止しました")
    
    def _worker_loop(self) -> None:
        """ワーカースレッドのメインループ"""
        thread_name = threading.current_thread().name
        logger.info(f"ワーカースレッド {thread_name} が開始されました")
        
        while self.running:
            try:
                # キューからタスクを取得（タイムアウト付き）
                try:
                    priority, task_id = self.task_queue.get(timeout=self.polling_interval)
                except queue.Empty:
                    continue
                
                # タスク実行
                self._execute_task(task_id)
                
                # キュータスク完了を通知
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"ワーカースレッド {thread_name} でエラーが発生しました: {str(e)}")
                import traceback
                logger.debug(traceback.format_exc())
                # 短い待機を入れてCPU使用率の急上昇を防止
                time.sleep(1.0)
        
        logger.info(f"ワーカースレッド {thread_name} が終了しました")
    
    def _execute_task(self, task_id: str) -> None:
        """タスクを実行"""
        task = None
        
        # タスク情報を取得
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                logger.warning(f"タスク ID {task_id} が見つかりません")
                return
            
            # タスクが既に実行中または完了・キャンセルされている場合
            if task.status != TaskStatus.PENDING:
                logger.warning(f"タスク '{task.name}' (ID: {task.id}) は既に {task.status.value} 状態です")
                return
            
            # タスク状態を実行中に更新
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            task.message = "タスクを実行中..."
            task.progress = 0.0
        
        # タスクハンドラーを取得
        handler = self.task_handlers.get(task.type)
        if not handler:
            with self.lock:
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                task.error = f"タスクタイプ '{task.type}' のハンドラーが登録されていません"
                task.message = "タスク実行に失敗しました: ハンドラーが見つかりません"
                logger.error(f"タスク '{task.name}' の実行に失敗: {task.error}")
            return
        
        try:
            # タスクを実行（進捗更新コールバック付き）
            def progress_callback(progress: float, message: Optional[str] = None) -> None:
                with self.lock:
                    if task.status == TaskStatus.RUNNING:
                        task.update_progress(progress, message)
            
            # タスク実行
            logger.info(f"タスク '{task.name}' (ID: {task.id}, タイプ: {task.type}) の実行を開始")
            result = handler(task.params, progress_callback)
            
            # 成功結果を記録
            with self.lock:
                if task.status == TaskStatus.RUNNING:  # 実行中の場合のみ更新（キャンセルされた場合は更新しない）
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = time.time()
                    task.progress = 1.0
                    task.result = result
                    task.message = "タスクが正常に完了しました"
                    
                    # 実行時間計算
                    execution_time = task.completed_at - task.started_at
                    logger.info(f"タスク '{task.name}' が正常に完了しました（実行時間: {execution_time:.2f}秒）")
                    
                    # コールバックがあれば実行
                    if task.callback:
                        try:
                            task.callback(task.id, result)
                        except Exception as callback_error:
                            logger.error(f"タスク '{task.name}' のコールバック実行中にエラー: {str(callback_error)}")
            
        except Exception as e:
            # エラーを記録
            with self.lock:
                if task.status == TaskStatus.RUNNING:  # 実行中の場合のみ更新
                    task.status = TaskStatus.FAILED
                    task.completed_at = time.time()
                    task.error = str(e)
                    task.message = f"タスク実行中にエラーが発生: {str(e)}"
                    
                    # スタックトレースをログに記録
                    import traceback
                    logger.error(f"タスク '{task.name}' の実行中にエラー: {str(e)}")
                    logger.debug(traceback.format_exc())

# グローバルタスクキューインスタンス
_task_queue_instance = None

def get_task_queue() -> TaskQueue:
    """グローバルタスクキューインスタンスを取得"""
    global _task_queue_instance
    if _task_queue_instance is None:
        _task_queue_instance = TaskQueue()
    return _task_queue_instance

def initialize_task_queue(num_workers: int = 2) -> None:
    """タスクキューを初期化して開始"""
    queue = get_task_queue()
    queue.num_workers = num_workers
    queue.start()

def shutdown_task_queue() -> None:
    """タスクキューを停止"""
    global _task_queue_instance
    if _task_queue_instance:
        _task_queue_instance.stop()
        _task_queue_instance = None