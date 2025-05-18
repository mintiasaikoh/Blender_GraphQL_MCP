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
    # メインスレッドで既に実行されている場合は直接実行
    if threading.current_thread() is threading.main_thread():
        return func(*args, **kwargs)

    # タイムアウトを取得
    timeout = kwargs.pop('_timeout', DEFAULT_TIMEOUT)
    cancellable = kwargs.pop('_cancellable', True)  # キャンセル可能か（デフォルトはキャンセル可能）

    # タスク ID を生成
    task_id = str(uuid.uuid4())

    # 単一の原子的操作として、結果の場所を確保し、キューにタスクを追加
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
        # キューにタスクを追加 (ロック内で行い、追加と登録の原子性を保証)
        _main_thread_queue.put((task_id, func, args, kwargs))

    # 結果を待つ
    start_time = time.time()
    try:
        # 実行完了またはタイムアウトまでイベントを使用して待機
        event = threading.Event()
        result_container = [None]  # 結果を保存するコンテナ
        timer_registered = [False]  # タイマーが登録されたかどうかを追跡

        # 定期的に結果をチェックする関数
        def check_result():
            with _main_thread_lock:
                # タスクが完了しているか確認
                if task_id in _main_thread_results and _main_thread_results[task_id] is not None:
                    # 結果を取得
                    result_container[0] = _main_thread_results[task_id]

                    # 完了を通知（結果の片付けはfinallyで一元的に行う）
                    event.set()
                    return None  # タイマーを継続しない

            # タイムアウトチェック
            if time.time() - start_time >= timeout:
                # タイムアウトした場合は完了イベントをセット
                event.set()
                return None  # タイマーを継続しない

            # まだ結果がない場合はタイマーを継続
            return POLL_INTERVAL  # 次のチェックまでの時間

        # 待機戦略：まずBlenderのタイマーを試し、ダメなら専用のスレッドを使用
        blender_timer_available = hasattr(bpy.app, 'timers')

        if blender_timer_available:
            try:
                # Blenderのタイマーシステムを使用
                bpy.app.timers.register(check_result)
                timer_registered[0] = True
                logger.debug(f"タスク {task_id[:8]} のためのBlenderタイマーを登録しました")
            except Exception as e:
                logger.warning(f"Blenderタイマー登録に失敗: {e}")
                blender_timer_available = False

        # Blenderのタイマーが使えない場合は専用スレッドを使用
        if not blender_timer_available:
            logger.debug(f"タスク {task_id[:8]} のためのフォールバック待機スレッドを開始します")
            # 専用の待機スレッドを使用
            def timer_thread():
                while not event.is_set() and time.time() - start_time < timeout:
                    # 定期的に結果をチェック
                    check_result()
                    time.sleep(POLL_INTERVAL)
                # 完了していなければ通知
                if not event.is_set():
                    event.set()

            timer = threading.Thread(target=timer_thread, daemon=True, name=f"task_wait_{task_id[:8]}")
            timer.start()

        # 結果またはタイムアウトを待つ
        waited = event.wait(timeout=timeout + 0.5)  # 少し余裕を持たせる

        # 結果を取得 - スレッドセーフに行う
        if result_container[0] is not None:
            result = result_container[0]  # ローカル変数にコピー

            # 例外結果の場合は例外を発生させる
            if isinstance(result, dict) and 'exception' in result:
                exception_class = result.get('exception_class', Exception)
                exception_message = result.get('exception_message', 'Unknown error')
                trace = result.get('traceback', '')

                # スタックトレースが含まれている場合はより詳細なログを出力
                if trace:
                    logger.error(f"メインスレッドでのタスク実行中に例外が発生: {exception_message}\n{trace}")

                # 元の例外を再発生
                if isinstance(exception_class, type) and issubclass(exception_class, Exception):
                    raise exception_class(exception_message)
                else:
                    # 例外クラスが無効な場合は一般的なExceptionを使用
                    raise Exception(f"{exception_message} (元の例外クラス: {exception_class})")

            # 通常の結果を返す
            return result

        # タイムアウトの場合 - 排他的に処理
        with _main_thread_lock:
            if task_id in _active_tasks:
                # タスク情報をローカル変数にコピー（ロック内）
                func_name = _active_tasks[task_id]['func']
                elapsed = time.time() - _active_tasks[task_id]['start_time']

                # タスクをキャンセル済みとマーク
                if cancellable:
                    _active_tasks[task_id]['cancelled'] = True
                    # キャンセル状態を設定してからログを出力
                    logger.warning(f"タスク {func_name} ({task_id[:8]}) をキャンセルしました")

                # タイムアウトを詳細にログ記録
                logger.error(f"タスク {func_name} ({task_id[:8]}) が{elapsed:.2f}秒実行した後タイムアウトしました")

        # タイムアウトエラーを発生
        raise TimeoutError(f"メインスレッドでの実行が{timeout}秒でタイムアウトしました (関数: {func.__name__ if hasattr(func, '__name__') else str(func)})")
            
    finally:
        # 登録したタイマーを確実に削除
        try:
            if 'timer_registered' in locals() and timer_registered[0] and hasattr(bpy.app, 'timers'):
                if 'check_result' in locals() and check_result in bpy.app.timers.callbacks:
                    bpy.app.timers.unregister(check_result)
                    logger.debug(f"タスク {task_id[:8]} のタイマーを正常に削除しました")
        except Exception as e:
            logger.warning(f"タイマー削除中にエラーが発生: {e}")

        # きちんと片付けを行う
        with _main_thread_lock:
            # タスク結果をクリア
            if task_id in _main_thread_results:
                del _main_thread_results[task_id]

            # タスク情報のクリーンアップ
            if task_id in _active_tasks:
                # キャンセルされたタスクは後の一括クリーンアップに任せる
                if not _active_tasks[task_id].get('cancelled', False):
                    # 実行時間を計算して記録
                    elapsed = time.time() - _active_tasks[task_id]['start_time']
                    func_name = _active_tasks[task_id]['func']

                    # タスク情報を削除
                    del _active_tasks[task_id]

                    # 完了ログを出力（削除後に行うことで競合を避ける）
                    logger.debug(f"タスク {func_name} ({task_id[:8]}) を完了しました。実行時間: {elapsed:.2f}秒")

def process_main_thread_queue():
    """
    メインスレッドキューから関数を取り出して実行する
    Blenderのモーダルオペレータから定期的に呼び出される
    """
    processed = 0
    max_per_frame = 5  # フレームごとに処理する最大タスク数
    start_time = time.time()

    while not _main_thread_queue.empty() and processed < max_per_frame:
        try:
            # タスクを取得
            task_id, func, args, kwargs = _main_thread_queue.get_nowait()

            # タスクが既にキャンセルされているか確認
            skip_task = False
            with _main_thread_lock:
                if task_id in _active_tasks and _active_tasks[task_id].get('cancelled', False):
                    logger.info(f"キャンセル済みのタスク {_active_tasks[task_id]['func']} ({task_id[:8]}) の実行をスキップします")
                    skip_task = True

            # キャンセルされていない場合のみ実行
            if not skip_task:
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

                    # エラーログ出力
                    logger.error(f"メインスレッドでの実行中にエラーが発生: {str(e)}")
                    logger.debug(traceback.format_exc())

            processed += 1

            # 長時間の処理を検知してログに出力
            if processed == 1 and time.time() - start_time > 0.1:
                logger.warning(f"タスク処理に時間がかかっています: {time.time() - start_time:.3f}秒 (関数: {func.__name__ if hasattr(func, '__name__') else str(func)})")

        except queue.Empty:
            break
        except Exception as e:
            # キュー処理中の予期しないエラーをログに記録
            logger.error(f"メインスレッドキュー処理中に予期しないエラーが発生: {str(e)}")
            logger.debug(traceback.format_exc())

def cleanup_cancelled_tasks():
    """
    キャンセルされたタスクや古いタスクをクリーンアップする
    定期的に呼び出され、メモリリークを防止する
    """
    start_time = time.time()
    current_time = start_time
    cancelled_tasks = []
    expired_tasks = []
    orphaned_results = []
    stalled_tasks = []
    stats = {
        'total_active_tasks': 0,
        'cancelled_tasks': 0,
        'expired_tasks': 0,
        'orphaned_results': 0,
        'stalled_tasks': 0
    }

    # スレッドセーフなクリーンアップ処理
    with _main_thread_lock:
        # 統計情報を収集
        stats['total_active_tasks'] = len(_active_tasks)

        # 1パス目: 削除候補を特定（実際の削除は別のループで行う）
        for task_id, task_info in _active_tasks.items():
            # キャンセルされたタスクを特定
            if task_info.get('cancelled', False):
                cancelled_tasks.append(task_id)
                stats['cancelled_tasks'] += 1

            # タイムアウトした古いタスクを特定（開始時間 + タイムアウト + 30秒のマージン）
            elif 'start_time' in task_info and 'timeout' in task_info:
                time_limit = task_info['start_time'] + task_info['timeout'] + 30.0
                elapsed = current_time - task_info['start_time']

                # 完全に期限切れのタスク
                if current_time > time_limit:
                    expired_tasks.append(task_id)
                    stats['expired_tasks'] += 1
                # 長時間実行中だが、まだタイムアウトしていないタスク (監視用)
                elif elapsed > task_info['timeout'] * 0.8:
                    stalled_tasks.append((task_id, elapsed, task_info))
                    stats['stalled_tasks'] += 1

        # 孤立した結果を特定（アクティブタスクに存在しないが結果として残っているもの）
        for task_id, result in _main_thread_results.items():
            if task_id not in _active_tasks:
                orphaned_results.append(task_id)
                stats['orphaned_results'] += 1

        # 2パス目: 実際に削除を実行

        # キャンセルされたタスクを削除
        for task_id in cancelled_tasks:
            task_info = _active_tasks[task_id]
            elapsed = current_time - task_info['start_time']
            func_name = task_info['func']

            # タスク情報を削除
            del _active_tasks[task_id]
            if task_id in _main_thread_results:
                del _main_thread_results[task_id]

            # ログを出力（削除後に行い、ロック時間を短縮）
            logger.info(f"キャンセルされたタスク {func_name} ({task_id[:8]}) をクリーンアップしました（キャンセルまで {elapsed:.1f}秒）")

        # 古いタスクを削除
        for task_id in expired_tasks:
            task_info = _active_tasks[task_id]
            elapsed = current_time - task_info['start_time']
            func_name = task_info['func']

            # タスク情報を削除
            del _active_tasks[task_id]
            if task_id in _main_thread_results:
                del _main_thread_results[task_id]

            # ログを出力
            logger.warning(f"古いタスク {func_name} ({task_id[:8]}) を自動クリーンアップしました（開始から {elapsed:.1f}秒経過）")

        # 孤立した結果を削除
        for task_id in orphaned_results:
            # 結果を削除
            del _main_thread_results[task_id]
            # ログを出力
            logger.debug(f"孤立したタスク結果 ({task_id[:8]}) を削除しました")

    # 長時間実行中のタスクを監視（ロック外でログ出力）
    for task_id, elapsed, task_info in stalled_tasks:
        percent = (elapsed / task_info['timeout']) * 100
        logger.debug(f"タスク {task_info['func']} ({task_id[:8]}) が長時間実行中: {elapsed:.1f}秒 ({percent:.0f}% of timeout)")

    # クリーンアップ処理の所要時間をログに出力
    cleanup_time = time.time() - start_time
    if cleanup_time > 0.1 or stats['cancelled_tasks'] > 0 or stats['expired_tasks'] > 0:
        logger.info(f"タスククリーンアップ統計: アクティブ={stats['total_active_tasks']}, "
                    f"キャンセル={stats['cancelled_tasks']}, 期限切れ={stats['expired_tasks']}, "
                    f"孤立={stats['orphaned_results']}, 遅延中={stats['stalled_tasks']} "
                    f"(処理時間: {cleanup_time*1000:.1f}ms)")

    # 大量のタスクが溜まっている場合は警告
    if stats['total_active_tasks'] > 50:
        logger.warning(f"多数のアクティブタスク ({stats['total_active_tasks']}) が残っています。メモリリークの可能性があります。")

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
