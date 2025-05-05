"""
統一スレッド処理モジュール
Blenderのメインスレッドと通信するための統一された仕組みを提供します
"""

import queue
import threading
import uuid
import time
import logging
import traceback
import bpy
from typing import Any, Callable, Dict, Tuple, Optional, List, Union

logger = logging.getLogger("unified_mcp.threading")

# キューとロックの一元管理
_main_thread_queue = queue.Queue()
_main_thread_lock = threading.RLock()
_main_thread_results: Dict[str, Any] = {}
_modal_operator_running = False

# スレッド処理システムの初期化フラグ
_initialized = False

# タスク管理用データ構造
_active_tasks: Dict[str, Dict[str, Any]] = {}  # 実行中のタスク管理

# 登録したオペレータクラスへの参照を保持
_modal_operator_class = None

# タイムアウト設定
DEFAULT_TIMEOUT = 30.0  # 秒
POLL_INTERVAL = 0.1  # 秒

def initialize():
    """スレッド処理システムを初期化"""
    global _initialized, _modal_operator_running
    
    if _initialized:
        logger.info("スレッド処理システムは既に初期化されています")
        return
    
    # 初期化フラグを設定
    _initialized = True
    _modal_operator_running = False
    
    # モーダルオペレータの登録状態を確認してから登録
    if _modal_operator_class is None:
        logger.info("モーダルオペレータを登録します")
        register_modal_operator()
    else:
        logger.debug("モーダルオペレータは既に登録されています")
    
    logger.info("スレッド処理システムの初期化が完了しました")

def shutdown():
    """スレッド処理システムをシャットダウン"""
    global _modal_operator_running
    logger.info("スレッド処理システムをシャットダウンしています...")
    
    # モーダルオペレータの登録を解除
    _modal_operator_running = False
    
    # 結果を全てクリア
    with _main_thread_lock:
        _main_thread_results.clear()
    
    # キューの中身を全て捨てる
    while not _main_thread_queue.empty():
        try:
            _main_thread_queue.get_nowait()
        except queue.Empty:
            break
    
    logger.info("スレッド処理システムのシャットダウンが完了しました")

def execute_in_main_thread(func: Callable, *args, **kwargs) -> Any:
    """
    関数をBlenderのメインスレッドで実行し、結果を返す
    
    Args:
        func: 実行する関数
        *args, **kwargs: 関数に渡す引数
        timeout: タイムアウト秒数（kwargs内で_timeoutとして指定可能）
    
    Returns:
        関数の戻り値
    
    Raises:
        TimeoutError: 実行がタイムアウトした場合
        Exception: 関数実行中に例外が発生した場合
    """
    # タイムアウトを取得
    timeout = kwargs.pop('_timeout', DEFAULT_TIMEOUT)
    cancellable = kwargs.pop('_cancellable', True)  # キャンセル可能か（デフォルトはキャンセル可能）
    
    # タスク ID を生成
    task_id = str(uuid.uuid4())
    
    # キューに追加する前に結果の場所を確保
    with _main_thread_lock:
        _main_thread_results[task_id] = None
        # アクティブタスクに登録
        _active_tasks[task_id] = {
            'func': func.__name__ if hasattr(func, '__name__') else str(func),
            'start_time': time.time(),
            'timeout': timeout,
            'cancelled': False,
            'cancellable': cancellable
        }
    
    # キューにタスクを追加
    _main_thread_queue.put((task_id, func, args, kwargs))
    
    # 結果を待つ
    start_time = time.time()
    try:
        # ポーリングループ
        while time.time() - start_time < timeout:
            # 単一の原子的操作として結果を取得
            with _main_thread_lock:
                # タスクが完了しているか確認
                if task_id in _main_thread_results and _main_thread_results[task_id] is not None:
                    # 結果を取得
                    result = _main_thread_results[task_id]
                    
                    # 結果キャッシュとアクティブタスクから削除（ロックで保護された単一操作として）
                    del _main_thread_results[task_id]
                    if task_id in _active_tasks:
                        del _active_tasks[task_id]
                    
                    # 例外結果の場合は例外を発生させる
                    if isinstance(result, dict) and 'exception' in result:
                        exception_class = result.get('exception_class', Exception)
                        exception_message = result.get('exception_message', 'Unknown error')
                        # ロックを解放してから例外を発生させる
                        raise exception_class(exception_message)
                    
                    # 通常の結果を返す
                    return result
            
            # 結果がまだない場合は待機
            time.sleep(POLL_INTERVAL)
        
        # タイムアウトエラーを生成
        with _main_thread_lock:
            if task_id in _active_tasks:
                # タスクをキャンセル済みとマーク
                if cancellable:
                    _active_tasks[task_id]['cancelled'] = True
                    logger.warning(f"タスク {_active_tasks[task_id]['func']} ({task_id}) をキャンセルしました")
        
        # タイムアウトエラーを発生
        raise TimeoutError(f"メインスレッドでの実行が{timeout}秒でタイムアウトしました (関数: {func.__name__ if hasattr(func, '__name__') else str(func)})")
            
    finally:
        # きちんと片付けを行う
        with _main_thread_lock:
            # タスク結果をクリア
            if task_id in _main_thread_results:
                del _main_thread_results[task_id]
            
            # 一定時間後にタスク情報をクリーンアップ
            # キャンセルされたタスクは後でクリーンアップされるので残しておく
            if task_id in _active_tasks and not _active_tasks[task_id].get('cancelled', False):
                del _active_tasks[task_id]

def process_main_thread_queue():
    """
    メインスレッドキューから関数を取り出して実行する
    Blenderのモーダルオペレータから定期的に呼び出される
    """
    processed = 0
    max_per_frame = 5  # フレームごとに処理する最大タスク数
    
    while not _main_thread_queue.empty() and processed < max_per_frame:
        try:
            task_id, func, args, kwargs = _main_thread_queue.get_nowait()
            
            try:
                # 関数を実行
                result = func(*args, **kwargs)
                
                # 結果を保存
                with _main_thread_lock:
                    _main_thread_results[task_id] = result
            
            except Exception as e:
                # 例外を捕捉して結果として保存
                exception_info = {
                    'exception': True,
                    'exception_class': e.__class__,
                    'exception_message': str(e),
                    'traceback': traceback.format_exc()
                }
                
                with _main_thread_lock:
                    _main_thread_results[task_id] = exception_info
                
                logger.error(f"メインスレッドでの実行中にエラーが発生: {str(e)}")
                logger.debug(traceback.format_exc())
            
            processed += 1
            
        except queue.Empty:
            break

def cleanup_cancelled_tasks():
    """
    キャンセルされたタスクや古いタスクをクリーンアップする
    """
    current_time = time.time()
    cancelled_tasks = []
    expired_tasks = []
    orphaned_results = []
    
    with _main_thread_lock:
        # 1パス目: 削除候補を特定（実際の削除は別のループで行う）
        for task_id, task_info in _active_tasks.items():
            # キャンセルされたタスクを特定
            if task_info.get('cancelled', False):
                cancelled_tasks.append(task_id)
            
            # タイムアウトした古いタスクを特定（開始時間 + タイムアウト + 30秒のマージン）
            elif 'start_time' in task_info and 'timeout' in task_info:
                time_limit = task_info['start_time'] + task_info['timeout'] + 30.0
                if current_time > time_limit:
                    expired_tasks.append(task_id)
        
        # 孤立した結果を特定（アクティブタスクに存在しないが結果として残っているもの）
        for task_id, result in _main_thread_results.items():
            if task_id not in _active_tasks and result is not None:
                orphaned_results.append(task_id)
        
        # 2パス目: 実際に削除を実行
        # キャンセルされたタスクを削除
        for task_id in cancelled_tasks:
            task_info = _active_tasks[task_id]
            logger.info(f"キャンセルされたタスク {task_info['func']} ({task_id}) をクリーンアップしました")
            del _active_tasks[task_id]
            if task_id in _main_thread_results:
                del _main_thread_results[task_id]
        
        # 古いタスクを削除
        for task_id in expired_tasks:
            task_info = _active_tasks[task_id]
            logger.warning(f"古いタスク {task_info['func']} ({task_id}) を自動クリーンアップしました（開始から {current_time - task_info['start_time']:.1f} 秒経過）")
            del _active_tasks[task_id]
            if task_id in _main_thread_results:
                del _main_thread_results[task_id]
        
        # 孤立した結果を削除
        for task_id in orphaned_results:
            logger.debug(f"孤立したタスク結果 ({task_id}) を削除しました")
            del _main_thread_results[task_id]

def get_active_tasks() -> Dict[str, Dict[str, Any]]:
    """
    アクティブなタスクの状態を取得する
    
    Returns:
        タスクの状態情報が含まれた辞書
    """
    with _main_thread_lock:
        # 活動中のタスク情報のコピーを返す
        active_tasks_copy = {}
        for task_id, task_info in _active_tasks.items():
            # 経過時間を更新
            elapsed = time.time() - task_info['start_time']
            task_info_copy = task_info.copy()
            task_info_copy['elapsed'] = elapsed
            active_tasks_copy[task_id] = task_info_copy
        return active_tasks_copy

def cancel_task(task_id: str) -> bool:
    """
    タスクをキャンセルする
    
    Args:
        task_id: キャンセルするタスクID
    
    Returns:
        キャンセルに成功したかどうか
    """
    with _main_thread_lock:
        if task_id in _active_tasks:
            task_info = _active_tasks[task_id]
            if not task_info.get('cancellable', True):
                logger.warning(f"タスク {task_info['func']} ({task_id}) はキャンセル不可能です")
                return False
                
            _active_tasks[task_id]['cancelled'] = True
            logger.info(f"タスク {task_info['func']} ({task_id}) をキャンセルしました")
            return True
        else:
            logger.warning(f"タスク {task_id} は見つかりません")
            return False

def register_modal_operator():
    """
    モーダルオペレータを登録する
    モーダルオペレータはBlender UIループで定期的に呼び出され、
    メインスレッドキューの処理を行う
    """
    global _modal_operator_class
    
    # すでに登録されている場合は登録解除してから再登録
    if _modal_operator_class is not None:
        try:
            bpy.utils.unregister_class(_modal_operator_class)
            logger.info("既存のモーダルオペレータクラスの登録を解除しました")
        except Exception as e:
            logger.warning(f"既存のモーダルオペレータクラスの登録解除に失敗しました: {str(e)}")
    
    # Blender モーダルオペレータの定義
    class MCPModalOperator(bpy.types.Operator):
        """ブレンダーユニファイドMCPのメインスレッド処理用モーダルオペレータ"""
        bl_idname = "mcp.modal_operator"
        bl_label = "MCP Background Processor"
        
        _timer = None
        _running = False
        
        def modal(self, context, event):
            global _modal_operator_running
            
            if not _modal_operator_running:
                self.cancel(context)
                return {'CANCELLED'}
            
            if event.type == 'TIMER':
                # メインスレッドキューの処理
                process_main_thread_queue()
                
                # キャンセル済みタスクのクリーンアップ
                cleanup_cancelled_tasks()
            
            return {'PASS_THROUGH'}
        
        def execute(self, context):
            global _modal_operator_running
            
            if _modal_operator_running:
                logger.warning("モーダルオペレータはすでに実行中です")
                return {'CANCELLED'}
            
            logger.info("モーダルオペレータを開始します")
            _modal_operator_running = True
            
            # タイマーを追加
            wm = context.window_manager
            self._timer = wm.event_timer_add(0.1, window=context.window)
            wm.modal_handler_add(self)
            
            return {'RUNNING_MODAL'}
        
        def cancel(self, context):
            global _modal_operator_running
            
            logger.info("モーダルオペレータを停止します")
            _modal_operator_running = False
            
            # タイマーを削除
            if self._timer:
                wm = context.window_manager
                wm.event_timer_remove(self._timer)
            
            return {'CANCELLED'}
    
    # オペレータクラスをグローバルに保存
    _modal_operator_class = MCPModalOperator
    
    # オペレータの登録
    try:
        bpy.utils.register_class(MCPModalOperator)
        logger.info("モーダルオペレータクラスを登録しました")
    except Exception as e:
        logger.error(f"モーダルオペレータクラスの登録に失敗しました: {str(e)}")
        _modal_operator_class = None  # クラス参照をクリア
    
    # オペレータの実行をタイマーで遅延起動
    def delayed_start():
        try:
            bpy.ops.mcp.modal_operator()
            logger.info("モーダルオペレータを起動しました")
        except Exception as e:
            logger.error(f"モーダルオペレータの起動に失敗しました: {str(e)}")
        return None  # タイマーを一度だけ実行
    
    try:
        # 1秒後に起動
        bpy.app.timers.register(delayed_start, first_interval=1.0)
        logger.info("モーダルオペレータの遅延起動タイマーを登録しました")
    except Exception as e:
        logger.error(f"モーダルオペレータの遅延起動タイマーの登録に失敗しました: {str(e)}")

# 登録したオペレータクラスへの参照を保持
_modal_operator_class = None

def unregister_modal_operator():
    """モーダルオペレータの登録を解除する"""
    global _modal_operator_running, _modal_operator_class
    
    # 実行フラグをリセット
    _modal_operator_running = False
    
    # クラス参照を使用して登録解除
    if _modal_operator_class is not None:
        try:
            bpy.utils.unregister_class(_modal_operator_class)
            logger.info("モーダルオペレータクラスの登録を解除しました")
        except Exception as e:
            logger.warning(f"モーダルオペレータクラスの登録解除に失敗しました: {str(e)}")
        
        # 参照をクリア
        _modal_operator_class = None
    else:
        # クラス参照がない場合はID名で試行
        try:
            # クラス名ではなくIDで検索
            for cls in bpy.types.Operator.__subclasses__():
                if hasattr(cls, 'bl_idname') and cls.bl_idname == "mcp.modal_operator":
                    bpy.utils.unregister_class(cls)
                    logger.info("モーダルオペレータクラスをIDで検索して登録解除しました")
                    break
        except Exception as e:
            logger.warning(f"モーダルオペレータのID検索による登録解除に失敗しました: {str(e)}")
