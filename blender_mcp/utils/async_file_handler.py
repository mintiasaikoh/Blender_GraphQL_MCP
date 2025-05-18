"""
Blender Unified MCP Async File Handler
非同期ファイル操作のサポート
"""

import os
import sys
import logging
import threading
import time
import queue
import traceback
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Tuple

# モジュールレベルのロガー
logger = logging.getLogger('unified_mcp.utils.async_file_handler')

# デバッグモード設定（環境変数から取得）
DEBUG_MODE = os.environ.get('UNIFIED_MCP_DEBUG', '0').lower() in ('1', 'true', 'yes')

# ファイルユーティリティをインポート
try:
    from .fileutils import (
        safe_read_file, safe_write_file, 
        safe_read_json, safe_write_json,
        normalize_path, ensure_directory
    )
    FILE_UTILS_AVAILABLE = True
except ImportError:
    FILE_UTILS_AVAILABLE = False
    logger.warning("fileutilsモジュールがインポートできません。基本実装を使用します。")


# ファイル操作タイプ
class FileOperation(Enum):
    READ = 'read'
    WRITE = 'write'
    READ_JSON = 'read_json'
    WRITE_JSON = 'write_json'
    DELETE = 'delete'
    COPY = 'copy'
    MOVE = 'move'
    LIST_DIR = 'list_dir'
    MAKE_DIR = 'make_dir'


# ファイル操作の結果状態
class OperationStatus(Enum):
    PENDING = 'pending'   # 処理待ち
    RUNNING = 'running'   # 実行中
    SUCCESS = 'success'   # 成功
    FAILURE = 'failure'   # 失敗
    TIMEOUT = 'timeout'   # タイムアウト
    CANCELLED = 'cancelled'  # キャンセル


# ファイル操作タスク
class FileTask:
    """非同期ファイル操作タスク"""
    
    def __init__(self, operation: FileOperation, args: Dict[str, Any], 
                callback: Optional[Callable] = None, timeout: float = 30.0):
        """
        非同期ファイル操作タスクを初期化
        
        Args:
            operation: 実行する操作の種類
            args: 操作に必要な引数
            callback: 完了時に呼び出す関数
            timeout: タイムアウト時間（秒）
        """
        self.id = f"file_task_{id(self)}"
        self.operation = operation
        self.args = args
        self.callback = callback
        self.timeout = timeout
        self.status = OperationStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
    
    def mark_running(self):
        """タスクの実行開始を記録"""
        self.start_time = time.time()
        self.status = OperationStatus.RUNNING
    
    def mark_completed(self, success: bool, result: Any = None, error: Any = None):
        """タスクの完了を記録"""
        self.end_time = time.time()
        self.status = OperationStatus.SUCCESS if success else OperationStatus.FAILURE
        self.result = result
        self.error = error
    
    def mark_timeout(self):
        """タスクのタイムアウトを記録"""
        self.end_time = time.time()
        self.status = OperationStatus.TIMEOUT
        self.error = "操作がタイムアウトしました"
    
    def mark_cancelled(self):
        """タスクのキャンセルを記録"""
        self.end_time = time.time()
        self.status = OperationStatus.CANCELLED
        self.error = "操作がキャンセルされました"
    
    def is_timed_out(self) -> bool:
        """タスクがタイムアウトしているかどうかをチェック"""
        if self.start_time is None or self.status != OperationStatus.RUNNING:
            return False
        return (time.time() - self.start_time) > self.timeout
    
    def execute(self):
        """タスクを実行"""
        self.mark_running()
        
        try:
            # 操作に応じた処理を実行
            if self.operation == FileOperation.READ:
                result = self._read_file()
            elif self.operation == FileOperation.WRITE:
                result = self._write_file()
            elif self.operation == FileOperation.READ_JSON:
                result = self._read_json()
            elif self.operation == FileOperation.WRITE_JSON:
                result = self._write_json()
            elif self.operation == FileOperation.DELETE:
                result = self._delete_file()
            elif self.operation == FileOperation.COPY:
                result = self._copy_file()
            elif self.operation == FileOperation.MOVE:
                result = self._move_file()
            elif self.operation == FileOperation.LIST_DIR:
                result = self._list_directory()
            elif self.operation == FileOperation.MAKE_DIR:
                result = self._make_directory()
            else:
                raise ValueError(f"未実装のファイル操作: {self.operation}")
            
            # 成功時の処理
            self.mark_completed(True, result)
            
        except Exception as e:
            # エラー時の処理
            error_message = str(e)
            if DEBUG_MODE:
                error_message = f"{error_message}\n{traceback.format_exc()}"
            
            self.mark_completed(False, None, error_message)
            logger.error(f"ファイル操作エラー: {error_message}")
        
        # コールバックがあれば実行
        if self.callback:
            try:
                self.callback(self)
            except Exception as e:
                logger.error(f"コールバック実行エラー: {e}")
    
    def _read_file(self):
        """ファイル読み込み処理"""
        file_path = self.args.get('file_path')
        encoding = self.args.get('encoding', 'utf-8')
        binary = self.args.get('binary', False)
        
        if FILE_UTILS_AVAILABLE:
            return safe_read_file(file_path, encoding, binary)
        else:
            # 基本実装
            mode = 'rb' if binary else 'r'
            kwargs = {} if binary else {'encoding': encoding}
            
            with open(file_path, mode, **kwargs) as f:
                return f.read()
    
    def _write_file(self):
        """ファイル書き込み処理"""
        file_path = self.args.get('file_path')
        content = self.args.get('content')
        encoding = self.args.get('encoding', 'utf-8')
        binary = self.args.get('binary', False)
        atomic = self.args.get('atomic', True)
        
        if FILE_UTILS_AVAILABLE:
            return safe_write_file(file_path, content, encoding, binary, atomic)
        else:
            # 基本実装
            # ディレクトリを確保
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # 書き込みモード
            mode = 'wb' if binary else 'w'
            kwargs = {} if binary else {'encoding': encoding}
            
            # アトミック書き込み
            if atomic:
                temp_path = file_path + '.tmp'
                
                with open(temp_path, mode, **kwargs) as f:
                    f.write(content)
                
                # 既存ファイルがあれば削除
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # 一時ファイルを正式な名前に変更
                os.rename(temp_path, file_path)
            else:
                # 直接書き込み
                with open(file_path, mode, **kwargs) as f:
                    f.write(content)
            
            return True
    
    def _read_json(self):
        """JSONファイル読み込み処理"""
        file_path = self.args.get('file_path')
        default = self.args.get('default')
        
        if FILE_UTILS_AVAILABLE:
            return safe_read_json(file_path, default)
        else:
            # 基本実装
            import json
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                if default is not None:
                    return default
                raise
    
    def _write_json(self):
        """JSONファイル書き込み処理"""
        file_path = self.args.get('file_path')
        data = self.args.get('data')
        indent = self.args.get('indent', 2)
        ensure_ascii = self.args.get('ensure_ascii', False)
        sort_keys = self.args.get('sort_keys', False)
        
        if FILE_UTILS_AVAILABLE:
            return safe_write_json(file_path, data, indent, ensure_ascii, sort_keys)
        else:
            # 基本実装
            import json
            # ディレクトリを確保
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # 一時ファイルに書き込み
            temp_path = file_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii, sort_keys=sort_keys)
            
            # 既存ファイルがあれば削除
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # 一時ファイルを正式な名前に変更
            os.rename(temp_path, file_path)
            return True
    
    def _delete_file(self):
        """ファイル削除処理"""
        file_path = self.args.get('file_path')
        validate_path = self.args.get('validate_path', True)
        
        if FILE_UTILS_AVAILABLE:
            from .fileutils import safe_delete
            return safe_delete(file_path, validate_path)
        else:
            # 基本実装
            if not os.path.exists(file_path):
                return True  # すでに存在しない
            
            if os.path.isdir(file_path):
                import shutil
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            
            return True
    
    def _copy_file(self):
        """ファイルコピー処理"""
        src_path = self.args.get('src_path')
        dst_path = self.args.get('dst_path')
        overwrite = self.args.get('overwrite', False)
        
        if FILE_UTILS_AVAILABLE:
            from .fileutils import safe_copy
            return safe_copy(src_path, dst_path, overwrite)
        else:
            # 基本実装
            if not os.path.exists(src_path):
                raise FileNotFoundError(f"コピー元ファイルが存在しません: {src_path}")
            
            if os.path.exists(dst_path) and not overwrite:
                raise FileExistsError(f"コピー先ファイルが既に存在します: {dst_path}")
            
            # ディレクトリを確保
            dst_dir = os.path.dirname(dst_path)
            if dst_dir and not os.path.exists(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)
            
            # ファイルとディレクトリで処理を分ける
            import shutil
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
            
            return True
    
    def _move_file(self):
        """ファイル移動処理"""
        src_path = self.args.get('src_path')
        dst_path = self.args.get('dst_path')
        overwrite = self.args.get('overwrite', False)
        
        if FILE_UTILS_AVAILABLE:
            from .fileutils import safe_move
            return safe_move(src_path, dst_path, overwrite)
        else:
            # 基本実装
            if not os.path.exists(src_path):
                raise FileNotFoundError(f"移動元ファイルが存在しません: {src_path}")
            
            if os.path.exists(dst_path) and not overwrite:
                raise FileExistsError(f"移動先ファイルが既に存在します: {dst_path}")
            
            # ディレクトリを確保
            dst_dir = os.path.dirname(dst_path)
            if dst_dir and not os.path.exists(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)
            
            # 既存のファイルがあれば削除
            if os.path.exists(dst_path) and overwrite:
                if os.path.isdir(dst_path):
                    import shutil
                    shutil.rmtree(dst_path)
                else:
                    os.remove(dst_path)
            
            # 移動
            import shutil
            shutil.move(src_path, dst_path)
            return True
    
    def _list_directory(self):
        """ディレクトリ内のファイル一覧を取得"""
        dir_path = self.args.get('dir_path')
        recursive = self.args.get('recursive', False)
        include_pattern = self.args.get('include_pattern')
        exclude_pattern = self.args.get('exclude_pattern')
        
        if FILE_UTILS_AVAILABLE:
            from .fileutils import list_files
            return list_files(dir_path, recursive, include_pattern, exclude_pattern)
        else:
            # 基本実装
            import re
            
            # 正規表現コンパイル
            include_regex = re.compile(include_pattern) if include_pattern else None
            exclude_regex = re.compile(exclude_pattern) if exclude_pattern else None
            
            result = []
            
            if recursive:
                # 再帰的に検索
                for root, _, files in os.walk(dir_path):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        norm_path = os.path.normpath(file_path)
                        
                        # フィルタリング
                        if include_regex and not include_regex.search(norm_path):
                            continue
                        if exclude_regex and exclude_regex.search(norm_path):
                            continue
                        
                        result.append(norm_path)
            else:
                # 単一ディレクトリのみ検索
                with os.scandir(dir_path) as it:
                    for entry in it:
                        if entry.is_file():
                            norm_path = os.path.normpath(entry.path)
                            
                            # フィルタリング
                            if include_regex and not include_regex.search(norm_path):
                                continue
                            if exclude_regex and exclude_regex.search(norm_path):
                                continue
                            
                            result.append(norm_path)
            
            return result
    
    def _make_directory(self):
        """ディレクトリを作成"""
        dir_path = self.args.get('dir_path')
        
        if FILE_UTILS_AVAILABLE:
            return ensure_directory(dir_path)
        else:
            # 基本実装
            if os.path.exists(dir_path):
                if os.path.isdir(dir_path):
                    return True
                else:
                    raise NotADirectoryError(f"指定されたパスはディレクトリではありません: {dir_path}")
            
            os.makedirs(dir_path, exist_ok=True)
            return True


# 非同期ファイル操作マネージャー
class AsyncFileManager:
    """非同期ファイル操作を管理するクラス"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            cls._instance = AsyncFileManager()
        return cls._instance
    
    def __init__(self, max_workers: int = 5):
        """
        非同期ファイル操作マネージャーを初期化
        
        Args:
            max_workers: 最大ワーカースレッド数
        """
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.active_tasks = {}  # タスクID -> FileTask
        self.completed_tasks = {}  # タスクID -> FileTask
        self.workers = []
        self.running = False
        self.lock = threading.RLock()
    
    def start(self):
        """ワーカースレッドを開始"""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            
            # ワーカースレッドを作成
            for i in range(self.max_workers):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"FileWorker-{i}",
                    daemon=True
                )
                worker.start()
                self.workers.append(worker)
            
            # タイムアウト監視スレッドを作成
            timeout_checker = threading.Thread(
                target=self._timeout_checker_loop,
                name="TimeoutChecker",
                daemon=True
            )
            timeout_checker.start()
            self.workers.append(timeout_checker)
            
            logger.info(f"非同期ファイルマネージャーを開始しました ({self.max_workers} ワーカー)")
    
    def stop(self):
        """ワーカースレッドを停止"""
        with self.lock:
            if not self.running:
                return
            
            self.running = False
            
            # キューに停止信号を送信
            for _ in range(self.max_workers * 2):
                self.task_queue.put(None)
            
            # アクティブなタスクをキャンセル
            for task_id, task in list(self.active_tasks.items()):
                task.mark_cancelled()
                if task.callback:
                    try:
                        task.callback(task)
                    except:
                        pass
            
            self.active_tasks.clear()
            
            logger.info("非同期ファイルマネージャーを停止しました")
    
    def _worker_loop(self):
        """ワーカースレッドのメインループ"""
        while self.running:
            try:
                # キューからタスクを取得
                task = self.task_queue.get(block=True, timeout=0.5)
                
                # 停止信号を受信した場合
                if task is None:
                    break
                
                # タスクを実行
                with self.lock:
                    self.active_tasks[task.id] = task
                
                task.execute()
                
                # 完了タスクを管理
                with self.lock:
                    if task.id in self.active_tasks:
                        del self.active_tasks[task.id]
                    self.completed_tasks[task.id] = task
                    
                    # 完了タスクの数を制限（最新100件を保持）
                    if len(self.completed_tasks) > 100:
                        oldest_task_id = min(
                            self.completed_tasks.keys(),
                            key=lambda tid: self.completed_tasks[tid].end_time or 0
                        )
                        del self.completed_tasks[oldest_task_id]
                
                # キューのタスク完了を通知
                self.task_queue.task_done()
                
            except queue.Empty:
                # タイムアウト - 次のループで再試行
                continue
            except Exception as e:
                logger.error(f"ワーカースレッドエラー: {e}")
                if DEBUG_MODE:
                    logger.debug(traceback.format_exc())
    
    def _timeout_checker_loop(self):
        """タイムアウト監視スレッドのメインループ"""
        while self.running:
            try:
                # アクティブなタスクをチェック
                with self.lock:
                    for task_id, task in list(self.active_tasks.items()):
                        if task.is_timed_out():
                            # タイムアウト処理
                            task.mark_timeout()
                            del self.active_tasks[task_id]
                            self.completed_tasks[task_id] = task
                            
                            # コールバックを実行
                            if task.callback:
                                try:
                                    task.callback(task)
                                except Exception as e:
                                    logger.error(f"タイムアウトコールバックエラー: {e}")
                
                # 一定間隔で再チェック
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"タイムアウトチェッカーエラー: {e}")
                if DEBUG_MODE:
                    logger.debug(traceback.format_exc())
                time.sleep(5.0)  # エラー時は少し長めの間隔で再試行
    
    def read_file_async(self, file_path: str, encoding: str = 'utf-8', binary: bool = False,
                        callback: Optional[Callable] = None, timeout: float = 30.0) -> str:
        """
        ファイルを非同期で読み込む
        
        Args:
            file_path: ファイルパス
            encoding: 文字エンコーディング
            binary: バイナリモードで読み込むかどうか
            callback: 完了時に呼び出すコールバック関数
            timeout: タイムアウト時間（秒）
            
        Returns:
            タスクID
        """
        # ファイルパスの正規化
        if FILE_UTILS_AVAILABLE:
            file_path = normalize_path(file_path)
        
        # タスクを作成
        task = FileTask(
            operation=FileOperation.READ,
            args={
                'file_path': file_path,
                'encoding': encoding,
                'binary': binary
            },
            callback=callback,
            timeout=timeout
        )
        
        # マネージャーが実行中でなければ開始
        if not self.running:
            self.start()
        
        # タスクをキューに追加
        self.task_queue.put(task)
        
        return task.id
    
    def write_file_async(self, file_path: str, content: Union[str, bytes], encoding: str = 'utf-8',
                        binary: bool = False, atomic: bool = True, callback: Optional[Callable] = None,
                        timeout: float = 30.0) -> str:
        """
        ファイルを非同期で書き込む
        
        Args:
            file_path: ファイルパス
            content: 書き込む内容
            encoding: 文字エンコーディング
            binary: バイナリモードで書き込むかどうか
            atomic: アトミック書き込みを使用するかどうか
            callback: 完了時に呼び出すコールバック関数
            timeout: タイムアウト時間（秒）
            
        Returns:
            タスクID
        """
        # ファイルパスの正規化
        if FILE_UTILS_AVAILABLE:
            file_path = normalize_path(file_path)
        
        # タスクを作成
        task = FileTask(
            operation=FileOperation.WRITE,
            args={
                'file_path': file_path,
                'content': content,
                'encoding': encoding,
                'binary': binary,
                'atomic': atomic
            },
            callback=callback,
            timeout=timeout
        )
        
        # マネージャーが実行中でなければ開始
        if not self.running:
            self.start()
        
        # タスクをキューに追加
        self.task_queue.put(task)
        
        return task.id
    
    def read_json_async(self, file_path: str, default: Any = None, callback: Optional[Callable] = None,
                       timeout: float = 30.0) -> str:
        """
        JSONファイルを非同期で読み込む
        
        Args:
            file_path: ファイルパス
            default: ファイルが存在しない場合のデフォルト値
            callback: 完了時に呼び出すコールバック関数
            timeout: タイムアウト時間（秒）
            
        Returns:
            タスクID
        """
        # ファイルパスの正規化
        if FILE_UTILS_AVAILABLE:
            file_path = normalize_path(file_path)
        
        # タスクを作成
        task = FileTask(
            operation=FileOperation.READ_JSON,
            args={
                'file_path': file_path,
                'default': default
            },
            callback=callback,
            timeout=timeout
        )
        
        # マネージャーが実行中でなければ開始
        if not self.running:
            self.start()
        
        # タスクをキューに追加
        self.task_queue.put(task)
        
        return task.id
    
    def write_json_async(self, file_path: str, data: Any, indent: int = 2,
                        ensure_ascii: bool = False, sort_keys: bool = False,
                        callback: Optional[Callable] = None, timeout: float = 30.0) -> str:
        """
        JSONファイルを非同期で書き込む
        
        Args:
            file_path: ファイルパス
            data: 書き込むデータ
            indent: インデント幅
            ensure_ascii: ASCII文字のみ使用するか
            sort_keys: キーをソートするか
            callback: 完了時に呼び出すコールバック関数
            timeout: タイムアウト時間（秒）
            
        Returns:
            タスクID
        """
        # ファイルパスの正規化
        if FILE_UTILS_AVAILABLE:
            file_path = normalize_path(file_path)
        
        # タスクを作成
        task = FileTask(
            operation=FileOperation.WRITE_JSON,
            args={
                'file_path': file_path,
                'data': data,
                'indent': indent,
                'ensure_ascii': ensure_ascii,
                'sort_keys': sort_keys
            },
            callback=callback,
            timeout=timeout
        )
        
        # マネージャーが実行中でなければ開始
        if not self.running:
            self.start()
        
        # タスクをキューに追加
        self.task_queue.put(task)
        
        return task.id
    
    def delete_file_async(self, file_path: str, validate_path: bool = True,
                         callback: Optional[Callable] = None, timeout: float = 30.0) -> str:
        """
        ファイルを非同期で削除
        
        Args:
            file_path: ファイルパス
            validate_path: パスの安全性を検証するかどうか
            callback: 完了時に呼び出すコールバック関数
            timeout: タイムアウト時間（秒）
            
        Returns:
            タスクID
        """
        # ファイルパスの正規化
        if FILE_UTILS_AVAILABLE:
            file_path = normalize_path(file_path)
        
        # タスクを作成
        task = FileTask(
            operation=FileOperation.DELETE,
            args={
                'file_path': file_path,
                'validate_path': validate_path
            },
            callback=callback,
            timeout=timeout
        )
        
        # マネージャーが実行中でなければ開始
        if not self.running:
            self.start()
        
        # タスクをキューに追加
        self.task_queue.put(task)
        
        return task.id
    
    def copy_file_async(self, src_path: str, dst_path: str, overwrite: bool = False,
                       callback: Optional[Callable] = None, timeout: float = 30.0) -> str:
        """
        ファイルを非同期でコピー
        
        Args:
            src_path: コピー元ファイルパス
            dst_path: コピー先ファイルパス
            overwrite: 既存ファイルを上書きするかどうか
            callback: 完了時に呼び出すコールバック関数
            timeout: タイムアウト時間（秒）
            
        Returns:
            タスクID
        """
        # ファイルパスの正規化
        if FILE_UTILS_AVAILABLE:
            src_path = normalize_path(src_path)
            dst_path = normalize_path(dst_path)
        
        # タスクを作成
        task = FileTask(
            operation=FileOperation.COPY,
            args={
                'src_path': src_path,
                'dst_path': dst_path,
                'overwrite': overwrite
            },
            callback=callback,
            timeout=timeout
        )
        
        # マネージャーが実行中でなければ開始
        if not self.running:
            self.start()
        
        # タスクをキューに追加
        self.task_queue.put(task)
        
        return task.id
    
    def move_file_async(self, src_path: str, dst_path: str, overwrite: bool = False,
                       callback: Optional[Callable] = None, timeout: float = 30.0) -> str:
        """
        ファイルを非同期で移動
        
        Args:
            src_path: 移動元ファイルパス
            dst_path: 移動先ファイルパス
            overwrite: 既存ファイルを上書きするかどうか
            callback: 完了時に呼び出すコールバック関数
            timeout: タイムアウト時間（秒）
            
        Returns:
            タスクID
        """
        # ファイルパスの正規化
        if FILE_UTILS_AVAILABLE:
            src_path = normalize_path(src_path)
            dst_path = normalize_path(dst_path)
        
        # タスクを作成
        task = FileTask(
            operation=FileOperation.MOVE,
            args={
                'src_path': src_path,
                'dst_path': dst_path,
                'overwrite': overwrite
            },
            callback=callback,
            timeout=timeout
        )
        
        # マネージャーが実行中でなければ開始
        if not self.running:
            self.start()
        
        # タスクをキューに追加
        self.task_queue.put(task)
        
        return task.id
    
    def list_files_async(self, dir_path: str, recursive: bool = False,
                        include_pattern: Optional[str] = None, exclude_pattern: Optional[str] = None,
                        callback: Optional[Callable] = None, timeout: float = 30.0) -> str:
        """
        ディレクトリ内のファイル一覧を非同期で取得
        
        Args:
            dir_path: ディレクトリパス
            recursive: サブディレクトリも検索するか
            include_pattern: 含めるファイルパターン（正規表現）
            exclude_pattern: 除外するファイルパターン（正規表現）
            callback: 完了時に呼び出すコールバック関数
            timeout: タイムアウト時間（秒）
            
        Returns:
            タスクID
        """
        # ファイルパスの正規化
        if FILE_UTILS_AVAILABLE:
            dir_path = normalize_path(dir_path)
        
        # タスクを作成
        task = FileTask(
            operation=FileOperation.LIST_DIR,
            args={
                'dir_path': dir_path,
                'recursive': recursive,
                'include_pattern': include_pattern,
                'exclude_pattern': exclude_pattern
            },
            callback=callback,
            timeout=timeout
        )
        
        # マネージャーが実行中でなければ開始
        if not self.running:
            self.start()
        
        # タスクをキューに追加
        self.task_queue.put(task)
        
        return task.id
    
    def make_directory_async(self, dir_path: str, callback: Optional[Callable] = None,
                            timeout: float = 30.0) -> str:
        """
        ディレクトリを非同期で作成
        
        Args:
            dir_path: ディレクトリパス
            callback: 完了時に呼び出すコールバック関数
            timeout: タイムアウト時間（秒）
            
        Returns:
            タスクID
        """
        # ファイルパスの正規化
        if FILE_UTILS_AVAILABLE:
            dir_path = normalize_path(dir_path)
        
        # タスクを作成
        task = FileTask(
            operation=FileOperation.MAKE_DIR,
            args={
                'dir_path': dir_path
            },
            callback=callback,
            timeout=timeout
        )
        
        # マネージャーが実行中でなければ開始
        if not self.running:
            self.start()
        
        # タスクをキューに追加
        self.task_queue.put(task)
        
        return task.id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        タスクの状態を取得
        
        Args:
            task_id: タスクID
            
        Returns:
            タスク状態の辞書（存在しない場合はNone）
        """
        with self.lock:
            # アクティブなタスクから検索
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                return {
                    'id': task.id,
                    'operation': task.operation.value,
                    'status': task.status.value,
                    'result': None,
                    'error': None,
                    'start_time': task.start_time,
                    'end_time': None,
                    'elapsed': time.time() - task.start_time if task.start_time else 0
                }
            
            # 完了タスクから検索
            if task_id in self.completed_tasks:
                task = self.completed_tasks[task_id]
                return {
                    'id': task.id,
                    'operation': task.operation.value,
                    'status': task.status.value,
                    'result': task.result,
                    'error': task.error,
                    'start_time': task.start_time,
                    'end_time': task.end_time,
                    'elapsed': (task.end_time - task.start_time) if task.start_time and task.end_time else 0
                }
            
            return None
    
    def wait_for_task(self, task_id: str, timeout: float = None) -> Dict[str, Any]:
        """
        タスクの完了を待機
        
        Args:
            task_id: タスクID
            timeout: タイムアウト時間（秒）
            
        Returns:
            タスク状態の辞書
            
        Raises:
            TimeoutError: タイムアウトした場合
            ValueError: タスクが存在しない場合
        """
        start_time = time.time()
        
        while True:
            # タイムアウトチェック
            if timeout is not None and (time.time() - start_time) > timeout:
                raise TimeoutError(f"タスク待機がタイムアウトしました: {task_id}")
            
            # タスク状態を取得
            status = self.get_task_status(task_id)
            if status is None:
                raise ValueError(f"タスクが存在しません: {task_id}")
            
            # 完了確認
            if status['status'] in ('success', 'failure', 'timeout', 'cancelled'):
                return status
            
            # 少し待機
            time.sleep(0.1)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        タスクをキャンセル
        
        Args:
            task_id: タスクID
            
        Returns:
            キャンセルできたかどうか
        """
        with self.lock:
            # アクティブなタスクから検索
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.mark_cancelled()
                
                # コールバックを実行
                if task.callback:
                    try:
                        task.callback(task)
                    except:
                        pass
                
                # 管理リストを更新
                del self.active_tasks[task_id]
                self.completed_tasks[task_id] = task
                
                return True
            
            return False
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        アクティブなタスクのリストを取得
        
        Returns:
            タスク状態の辞書リスト
        """
        with self.lock:
            return [
                {
                    'id': task.id,
                    'operation': task.operation.value,
                    'status': task.status.value,
                    'start_time': task.start_time,
                    'elapsed': time.time() - task.start_time if task.start_time else 0
                }
                for task in self.active_tasks.values()
            ]


# モジュールレベルの便利な関数
def read_file_async(file_path: str, encoding: str = 'utf-8', binary: bool = False,
                   callback: Optional[Callable] = None, timeout: float = 30.0) -> str:
    """ファイルを非同期で読み込む（モジュールレベル関数）"""
    manager = AsyncFileManager.get_instance()
    return manager.read_file_async(file_path, encoding, binary, callback, timeout)


def write_file_async(file_path: str, content: Union[str, bytes], encoding: str = 'utf-8',
                    binary: bool = False, atomic: bool = True, callback: Optional[Callable] = None,
                    timeout: float = 30.0) -> str:
    """ファイルを非同期で書き込む（モジュールレベル関数）"""
    manager = AsyncFileManager.get_instance()
    return manager.write_file_async(file_path, content, encoding, binary, atomic, callback, timeout)


def read_json_async(file_path: str, default: Any = None, callback: Optional[Callable] = None,
                   timeout: float = 30.0) -> str:
    """JSONファイルを非同期で読み込む（モジュールレベル関数）"""
    manager = AsyncFileManager.get_instance()
    return manager.read_json_async(file_path, default, callback, timeout)


def write_json_async(file_path: str, data: Any, indent: int = 2,
                    ensure_ascii: bool = False, sort_keys: bool = False,
                    callback: Optional[Callable] = None, timeout: float = 30.0) -> str:
    """JSONファイルを非同期で書き込む（モジュールレベル関数）"""
    manager = AsyncFileManager.get_instance()
    return manager.write_json_async(file_path, data, indent, ensure_ascii, sort_keys, callback, timeout)


def wait_for_task(task_id: str, timeout: float = None) -> Dict[str, Any]:
    """タスクの完了を待機（モジュールレベル関数）"""
    manager = AsyncFileManager.get_instance()
    return manager.wait_for_task(task_id, timeout)


def register():
    """非同期ファイルハンドラモジュールを登録"""
    # マネージャーインスタンスを取得
    manager = AsyncFileManager.get_instance()
    
    # 自動的に開始
    if not manager.running:
        manager.start()
    
    logger.info("非同期ファイルハンドラモジュールを登録しました")


def unregister():
    """非同期ファイルハンドラモジュールの登録解除"""
    # マネージャーインスタンスを取得
    manager = AsyncFileManager.get_instance()
    
    # 実行中であれば停止
    if manager.running:
        manager.stop()
    
    logger.info("非同期ファイルハンドラモジュールを登録解除しました")