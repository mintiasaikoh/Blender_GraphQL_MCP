"""
Async Handler for Blender
Blenderの制約を考慮した擬似非同期処理
"""

import bpy
import threading
import queue
import time
import functools
from typing import Callable, Any, Dict

class BlenderAsyncHandler:
    """
    Blenderでの擬似非同期処理
    - 別スレッドでの処理
    - メインスレッドとの安全な通信
    - タイマーベースの実行
    """
    
    def __init__(self):
        self.task_queue = queue.Queue()
        self.result_callbacks = {}
        self.timer_active = False
        self._task_id = 0
    
    def submit_task(self, func: Callable, *args, callback: Callable = None, **kwargs) -> int:
        """
        タスクをキューに追加
        
        Args:
            func: 実行する関数
            args: 関数の引数
            callback: 結果を受け取るコールバック（メインスレッドで実行）
            kwargs: 関数のキーワード引数
            
        Returns:
            タスクID
        """
        task_id = self._get_next_task_id()
        
        # タスクをキューに追加
        task = {
            'id': task_id,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'callback': callback
        }
        
        self.task_queue.put(task)
        
        # ワーカースレッドを起動
        threading.Thread(target=self._worker, daemon=True).start()
        
        # タイマーを開始
        if not self.timer_active:
            self._start_timer()
        
        return task_id
    
    def _get_next_task_id(self) -> int:
        """次のタスクIDを生成"""
        self._task_id += 1
        return self._task_id
    
    def _worker(self):
        """ワーカースレッド"""
        try:
            # タスクを取得
            task = self.task_queue.get(timeout=1.0)
            
            # 実行
            result = task['func'](*task['args'], **task['kwargs'])
            
            # 結果を保存
            self.result_callbacks[task['id']] = {
                'callback': task['callback'],
                'result': result
            }
            
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Worker error: {e}")
    
    def _start_timer(self):
        """タイマーを開始"""
        self.timer_active = True
        bpy.app.timers.register(self._timer_callback, first_interval=0.1)
    
    def _timer_callback(self):
        """タイマーコールバック（メインスレッド）"""
        # 完了したタスクのコールバックを実行
        for task_id in list(self.result_callbacks.keys()):
            task_info = self.result_callbacks.pop(task_id)
            callback = task_info['callback']
            result = task_info['result']
            
            if callback:
                try:
                    callback(result)
                except Exception as e:
                    print(f"Callback error: {e}")
        
        # キューが空になったらタイマーを停止
        if self.task_queue.empty() and not self.result_callbacks:
            self.timer_active = False
            return None  # タイマーを停止
        
        return 0.1  # 100ms後に再実行

# デコレーターで簡単に使えるように
def async_execute(callback: Callable = None):
    """非同期実行デコレーター"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_async_handler()
            return handler.submit_task(func, *args, callback=callback, **kwargs)
        return wrapper
    return decorator

# グローバルハンドラー
_async_handler = None

def get_async_handler() -> BlenderAsyncHandler:
    """非同期ハンドラーのシングルトン"""
    global _async_handler
    if _async_handler is None:
        _async_handler = BlenderAsyncHandler()
    return _async_handler

# 使用例
@async_execute(callback=lambda result: print(f"Result: {result}"))
def long_running_task(duration: float) -> str:
    """長時間かかる処理の例"""
    time.sleep(duration)
    return f"Task completed after {duration} seconds"

class AsyncOperator(bpy.types.Operator):
    """非同期処理を使用するオペレーターの例"""
    bl_idname = "mcp.async_example"
    bl_label = "Async Example"
    
    def execute(self, context):
        # 非同期でタスクを実行
        handler = get_async_handler()
        
        def on_complete(result):
            """完了時のコールバック"""
            self.report({'INFO'}, f"Task completed: {result}")
        
        # 長時間かかる処理を非同期で実行
        handler.submit_task(
            self.heavy_computation,
            duration=2.0,
            callback=on_complete
        )
        
        self.report({'INFO'}, "Task submitted")
        return {'FINISHED'}
    
    def heavy_computation(self, duration: float) -> Dict[str, Any]:
        """重い計算処理"""
        import numpy as np
        
        # 実際の処理（例：大規模なメッシュ解析）
        time.sleep(duration)
        
        # 結果を返す
        return {
            "status": "completed",
            "duration": duration,
            "result": "Heavy computation done"
        }