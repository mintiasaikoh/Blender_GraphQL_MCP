"""
HTTP Server Adapter - GraphQL APIサーバーをSimpleHttpServerインターフェースで利用するためのアダプター
"""
import sys
import os
import threading
import importlib
import json
import uuid
import time
import queue
from datetime import datetime
import logging
from typing import Optional, Any, Callable

# ロギング設定
logger = logging.getLogger(__name__)

# スレッド処理システムをインポート
try:
    from . import threading as mcp_threading
    THREADING_MODULE_LOADED = True
except ImportError:
    logger.error("スレッド処理システムをインポートできません")
    THREADING_MODULE_LOADED = False

class SimpleHttpServer:
    """
    GraphQL APIサーバーをラップするシンプルなアダプター
    """
    def __init__(self):
        self.running = False
        self.port = 8000
        self.server_instance = None
        self._load_server()
    
    def _load_server(self):
        """既存のMCPHttpServerモジュールをロード - 複数のインポート方法を試行"""
        # 現在のパスを取得と記録
        current_path = os.path.dirname(__file__)
        parent_path = os.path.dirname(current_path)  # アドオンのルートディレクトリ
        logger.info(f"サーバーアダプターパス: {current_path}")
        logger.info(f"アドオンパス: {parent_path}")

        # 複数のインポート方法を試行
        methods_tried = []

        # 方法1: 相対インポートを試行
        try:
            methods_tried.append("相対インポート")
            # 同じディレクトリ内のhttp_serverモジュールをインポート
            from . import http_server
            module = http_server
            logger.info("相対インポートでサーバーモジュールをロードしました")
        except ImportError as e:
            logger.warning(f"相対インポートでのサーバーモジュールロードに失敗: {str(e)}")
            
            # 方法2: フルパッケージ名でのインポート
            try:
                methods_tried.append("フルパッケージインポート")
                # アドオン名を取得
                package_name = os.path.basename(parent_path)
                module = importlib.import_module(f'{package_name}.core.http_server')
                logger.info(f"パッケージインポート({package_name})でサーバーモジュールをロードしました")
            except ImportError as e:
                logger.warning(f"パッケージインポートでのサーバーモジュールロードに失敗: {str(e)}")
                
                # 方法3: sys.pathを変更して絶対インポート
                try:
                    methods_tried.append("sys.path変更と絶対インポート")
                    # coreディレクトリをsys.pathに追加
                    if current_path not in sys.path:
                        sys.path.insert(0, current_path)
                    module = importlib.import_module('http_server')
                    logger.info("絶対インポートでサーバーモジュールをロードしました")
                except ImportError as e:
                    logger.warning(f"絶対インポートでのサーバーモジュールロードに失敗: {str(e)}")
                    
                    # 最後の手段: 直接パスからロード
                    try:
                        methods_tried.append("直接ファイルからロード")
                        spec = importlib.util.spec_from_file_location(
                            "http_server", 
                            os.path.join(current_path, "http_server.py")
                        )
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        logger.info("直接ファイルからサーバーモジュールをロードしました")
                    except Exception as e:
                        logger.error(f"すべてのインポート方法が失敗: {str(e)}")
                        logger.error(f"試行したメソッド: {', '.join(methods_tried)}")
                        return False
        
        # サーバークラスの取得と初期化
        try:
            server_class = getattr(module, 'MCPHttpServer', None)
            if server_class:
                self.server_instance = server_class.get_instance()
                logger.info("MCPHttpServerのロードと初期化に成功しました")
                return True
            else:
                logger.error("MCPHttpServerクラスが見つかりません")
                return False
        except Exception as e:
            logger.error(f"サーバーインスタンスの初期化エラー: {str(e)}")
            return False
    
    def start_server(self, host="localhost", port=8000):
        """サーバーを起動する"""
        # 既にサーバーが起動しているか確認
        # 接続テストも含めた厳密な確認
        existing_connection = False
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            s.close()
            existing_connection = True
            logger.info(f"ポート {port} が既に使用されています。既存の接続を検出しました。")
        except Exception:
            # 接続できない = ポートは利用可能
            pass
        
        # フラグが実行中で実際に接続もできる場合
        if self.running and existing_connection:
            logger.warning("サーバーはすでに起動しています")
            return True
        
        # フラグが実行中だが接続テストに失敗した場合
        if self.running and not existing_connection:
            logger.warning("サーバーは実行中のフラグですが接続できません。状態をリセットします。")
            self.running = False
        
        # サーバーインスタンスのロード
        if not self.server_instance:
            if not self._load_server():
                logger.error("サーバーインスタンスの読み込みに失敗しました")
                return False
        
        try:
            self.port = port
            self.host = host
            
            # GraphQL APIサーバーを起動
            logger.info(f"GraphQL APIサーバーを起動します (host: {host}, port: {port})")
            
            # サーバー起動メソッドを確認して呼び出す
            result = False
            
            # 事前にログで利用可能なメソッドを確認
            logger.info(f"サーバーインスタンスメソッド: {dir(self.server_instance)}")
            
            # サーバー起動メソッドを適切に選択
            if hasattr(self.server_instance, 'start_graphql_server'):
                # start_graphql_serverメソッドがあれば使用
                logger.info("start_graphql_serverメソッドを使用してサーバーを起動します")
                result = self.server_instance.start_graphql_server(host=host, port=port)
            elif hasattr(self.server_instance, 'start'):
                # startメソッドがあれば使用 - これが標準的
                logger.info("startメソッドを使用してサーバーを起動します")
                # 事前にポートとホストを設定
                self.server_instance.port = port
                self.server_instance.host = host
                result = self.server_instance.start()
            else:
                # 適切なメソッドが見つからない
                logger.error("サーバー起動用の適切なメソッドが見つかりません")
                return False
            
            # 結果をログに記録
            if result:
                logger.info(f"サーバー起動成功: host={host}, port={port}")
                self.running = True
                
                # サーバー起動の確認 - 接続テスト
                import socket
                import time
                
                # サーバーが完全に起動するまで少し待機
                time.sleep(1.0)
                
                # 複数回の接続試行を実装
                max_retries = 3
                retry_delay = 0.5
                connected = False
                
                for retry in range(max_retries):
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(2)
                        s.connect(("127.0.0.1", port))
                        s.close()
                        logger.info(f"サーバー接続テスト成功: 127.0.0.1:{port} (試行 {retry+1})")
                        connected = True
                        break
                    except Exception as e:
                        logger.warning(f"サーバー接続テスト失敗 (試行 {retry+1}): {e}")
                        if retry < max_retries - 1:
                            logger.info(f"{retry_delay}秒後に再試行します...")
                            time.sleep(retry_delay)
                
                if not connected:
                    logger.error(f"サーバー起動後の接続テストに {max_retries} 回失敗しました。サーバー構成を確認してください。")
                    # この場合でもUIには成功と表示 - 実際のサーバー状態は定期的にチェックされる
            else:
                logger.error("サーバー起動失敗")
            
            return result
        except Exception as e:
            logger.error(f"サーバー起動エラー: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """サーバーを停止"""
        if not self.running:
            logger.warning("サーバーは起動していません")
            return False
        
        if not self.server_instance:
            logger.warning("サーバーインスタンスが初期化されていません")
            return False
        
        try:
            result = self.server_instance.stop()
            if result:
                self.running = False
                logger.info("サーバーを停止しました")
                
                # サーバー停止の確認 - ソケット接続テストで確認
                import socket
                import time
                
                # サーバーが完全に停止するまで少し待機
                time.sleep(1.0)
                
                # 接続テスト（ポートが解放されたことを確認）
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    s.connect(("127.0.0.1", self.port))
                    s.close()
                    # まだ接続できる場合はサーバーが停止していない
                    logger.warning(f"サーバーが停止したにもかかわらず、ポート {self.port} に接続できます")
                    return False
                except Exception:
                    # 接続できない = ポートが解放された = 正常に停止
                    logger.info(f"サーバー停止確認: ポート {self.port} への接続に失敗（正常な動作）")
                    return True
            return result
        except Exception as e:
            logger.error(f"サーバー停止エラー: {str(e)}")
            return False
    
    def is_running(self) -> bool:
        """サーバーの実行状態を取得し、実際の接続性も確認"""
        # 状態確認のトレースログを追加
        server_instance_status = False
        adapter_status = self.running
        
        if self.server_instance and hasattr(self.server_instance, 'server_running'):
            server_instance_status = self.server_instance.server_running
            
        # 両方の状態をログに記録
        logger.debug(f"サーバー状態確認: サーバーインスタンス={server_instance_status}, アダプター={adapter_status}")
        
        # 状態確認結果
        running_status = server_instance_status or adapter_status
        
        # ソケット接続テスト - サーバーが実行中の場合または状態が不明な場合実行
        if running_status or not running_status and not adapter_status and not server_instance_status:
            try:
                import socket
                import time
                
                # ポート番号を取得
                port = self.get_port()
                
                # ソケット接続テスト
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)  # 1秒のタイムアウトを設定
                
                # 接続試行前のデバッグログ
                logger.debug(f"サーバーポート {port} に接続を試行します...")
                
                # 接続を試行
                s.connect(("127.0.0.1", port))
                s.close()
                
                # 接続成功 - サーバーは実際に実行中
                logger.info(f"サーバー実行確認: ポート {port} に接続成功")
                
                # フラグを更新して内部状態と一致させる
                if not running_status:
                    logger.warning("フラグ状態の不一致を検出。内部状態を'実行中'に修正します")
                    self.running = True
                    if self.server_instance and hasattr(self.server_instance, 'server_running'):
                        self.server_instance.server_running = True
                
                return True
                
            except Exception as e:
                # 接続に失敗した場合のログ出力
                logger.debug(f"サーバーポート {self.get_port()} に接続できません: {str(e)}")
                
                if running_status:
                    # フラグは実行中を示しているが、接続テストが失敗した場合
                    logger.warning(f"サーバーは実行状態だが、ポート {self.get_port()} に接続できません。状態を'停止'に更新します")
                    # 状態表示の精度を上げるため、接続テストが失敗した場合は実行していないと判断
                    self.running = False
                    if self.server_instance and hasattr(self.server_instance, 'server_running'):
                        self.server_instance.server_running = False
                    return False
                else:
                    # フラグが停止を示しており、接続テストも失敗 - 正常
                    return False
        
        return running_status
    
    def get_port(self) -> int:
        """現在のポート番号を取得"""
        if self.server_instance and hasattr(self.server_instance, 'port'):
            return self.server_instance.port
        return self.port

# グローバルインスタンス
_server_instance = None

def get_server_instance() -> SimpleHttpServer:
    """シングルトンサーバーインスタンスを取得"""
    global _server_instance
    if _server_instance is None:
        _server_instance = SimpleHttpServer()
    return _server_instance

# 統合スレッド処理システムを使用したメインスレッド実行
def execute_in_main_thread(func: Callable, *args, **kwargs) -> Any:
    """
    関数をBlenderのメインスレッドで実行するためのヘルパー
    
    Args:
        func: 実行する関数
        *args: 関数の位置引数
        **kwargs: 関数のキーワード引数
    
    Returns:
        関数の実行結果
    
    Raises:
        TimeoutError: 実行がタイムアウトした場合
        Exception: 関数実行中に例外が発生した場合
    """
    # スレッド処理システムが利用可能な場合はそちらを使用
    if THREADING_MODULE_LOADED:
        try:
            return mcp_threading.execute_in_main_thread(func, *args, **kwargs)
        except Exception as e:
            logger.error(f"統合スレッド処理システムによる実行に失敗しました: {str(e)}")
            # 失敗した場合、後述のフォールバック実装を使用
    
    # 互換性のためのフォールバック実装
    # 対象モジュールがロードされていない場合のために互換性を確保
    logger.warning("統合スレッド処理システムが利用できません。互換モードで実行します。")
    
    # 後方互換性のため、ここではインポートエラーの場合を想定した実装を行う
    # 注意: こちらは直接インポートエラーが発生した場合のバックアップ実装であり
    # 新しい統合スレッド処理システムの導入後はなるべく使用されないようにする
    try:
        import bpy
        if hasattr(bpy.app, 'timers'):
            task_id = str(uuid.uuid4())
            result_dict = {}
            
            # Blenderのタイマーを使用してメインスレッドで実行
            def timer_fn():
                try:
                    result_dict['result'] = func(*args, **kwargs)
                    result_dict['completed'] = True
                except Exception as e:
                    result_dict['exception'] = e
                    result_dict['completed'] = True
                return None  # 一度だけ実行
                
            bpy.app.timers.register(timer_fn)
            
            # タイムアウト設定
            timeout = kwargs.pop('_timeout', 30.0)  # デフォルトタイムアウト: 30秒
            start_time = time.time()
            
            # ポーリングで実行完了を待つ
            while not result_dict.get('completed', False):
                # タイムアウトチェック
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"メインスレッドでの関数実行がタイムアウトしました ({timeout}秒)")
                
                # 少し待機
                time.sleep(0.1)
            
            # 例外があれば再送出
            if 'exception' in result_dict:
                raise result_dict['exception']
                
            return result_dict.get('result')
            
        else:
            # bpy.app.timersが利用できない場合は直接実行
            logger.warning("Blenderのタイマーが使用できないため、直接関数を実行します")
            return func(*args, **kwargs)
    
    except Exception as e:
        logger.error(f"メインスレッドでの関数実行に失敗しました: {str(e)}")
        raise

def process_main_thread_queue():
    """
    メインスレッドキューの処理を統合スレッド処理システムに委任
    互換性のためのスタブ関数 - 統合スレッド処理システムを参照
    """
    if THREADING_MODULE_LOADED:
        try:
            # 統合スレッド処理システムのキュー処理を呼び出す
            mcp_threading.process_main_thread_queue()
            return True
        except Exception as e:
            logger.error(f"統合スレッド処理システムのキュー処理に失敗しました: {str(e)}")
            return False
    else:
        # 利用可能でない場合はログメッセージのみ
        logger.warning("統合スレッド処理システムが利用できないため、キュー処理をスキップしました")
        return False


# ヘルパー関数: __init__.pyから直接呼び出せるようにするための関数
def start_server(host="localhost", port=8765):
    """サーバーを起動するヘルパー関数"""
    server = get_server_instance()
    return server.start_server(host=host, port=port)


def stop_server():
    """サーバーを停止するヘルパー関数"""
    server = get_server_instance()
    return server.stop()


def is_server_running():
    """サーバーの実行状態を確認するヘルパー関数"""
    server = get_server_instance()
    running = server.is_running()
    logger.info(f"サーバー状態確認: is_running={running}")
    return running
