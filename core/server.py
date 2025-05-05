""" 
Unified MCP Server Module
統合されたサーバー実装を提供し、複数のバックエンドをサポート
"""

import logging
import threading
import importlib
import json
import os
import sys
import time
import uuid
from typing import Dict, List, Any, Optional, Union, Callable, Type
from http.server import HTTPServer, BaseHTTPRequestHandler
import bpy

# 設定モジュールのインポートエラー時の対策
try:
    from .. import config
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("設定モジュールのインポートに失敗しました。デフォルト設定を使用します。")
    # 最小限の設定インターフェースを提供するダミークラス
    class DummyConfig:
        @staticmethod
        def get_config(section, key, default=None):
            return default
        
        @staticmethod
        def _compare_versions(ver1, ver2):
            """ver1とver2を比較: ver1がver2より大きければ>0、等しければ=0、小さければ<0"""
            v1_parts = ver1.split('.')
            v2_parts = ver2.split('.')
            for i in range(max(len(v1_parts), len(v2_parts))):
                v1 = int(v1_parts[i]) if i < len(v1_parts) else 0
                v2 = int(v2_parts[i]) if i < len(v2_parts) else 0
                if v1 > v2:
                    return 1
                elif v1 < v2:
                    return -1
            return 0
    
    config = DummyConfig()

from . import errors
from . import threading as mcp_threading

# ロギング設定
logger = logging.getLogger('unified_mcp.server')

# FastAPIをチェック
try:
    import fastapi
    import uvicorn
    FASTAPI_AVAILABLE = True
    logger.info("FastAPIが使用可能です (バージョン: {0})".format(fastapi.__version__))
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("FastAPIが見つかりません。シンプルHTTPサーバーを使用します。")

# GraphQLをチェック
try:
    from ..graphql import api as graphql_api
    GRAPHQL_AVAILABLE = graphql_api.GRAPHQL_AVAILABLE
    logger.info("GraphQLが使用可能です")
except ImportError:
    GRAPHQL_AVAILABLE = False
    logger.warning("GraphQLモジュールが見つかりません")

# HTTPリクエストハンドラ
class MCPRequestHandler(BaseHTTPRequestHandler):
    """リクエストを処理するハンドラクラス"""
    
    def _set_headers(self, content_type="application/json"):
        """レスポンスヘッダを設定"""
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    
    def do_GET(self):
        """入力GETリクエストの処理"""
        logger.info(f"GETリクエスト受信: {self.path}")
        
        if self.path == "/info":
            # アドオン情報を返す
            self._set_headers()
            response = {
                "name": "Blender Unified MCP",
                "version": "1.3.0",  # アドオン全体と一致させたバージョン
                "description": "MCPサーバーモジュール",
                "status": "running"
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == "/objects":
            # Blenderオブジェクトの一覧を返す
            self._set_headers()
            objects = [obj.name for obj in bpy.data.objects]
            response = {
                "count": len(objects),
                "objects": objects
            }
            self.wfile.write(json.dumps(response).encode())
            
        else:
            # デフォルトのエンドポイント
            self._set_headers("text/plain")
            message = "Blender Unified MCP API\n"
            message += "Available endpoints: /info, /objects"
            self.wfile.write(message.encode())
    
    def do_OPTIONS(self):
        """プリフライトリクエストに対応"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

# MCPサーバークラス
class MCPServer:
    """
    統合されたMCPサーバー実装
    複数のバックエンド（FastAPI、標準HTTPサーバー）をサポートし、
    シングルトンパターンを使用して単一インスタンスで実行されます。
    """
    
    # シングルトンインスタンス
    _instance = None
    _init_done = False
    _instance_lock = threading.RLock()  # シングルトンインスタンスが競合条件で生成されることを防ぐロック
    
    def __new__(cls, *args, **kwargs):
        """シングルトンパターンの実装: スレッドセーフに常に同じインスタンスを返す"""
        # ダブルチェックロッキングパターン
        if cls._instance is None:
            with cls._instance_lock:  # スレッドセーフなインスタンス生成
                if cls._instance is None:  # 二重チェック
                    logger.debug("MCPServerの新しいインスタンスを作成")
                    cls._instance = super(MCPServer, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """サーバーのシングルトンインスタンスを取得"""
        if cls._instance is None:
            return cls()
        return cls._instance
    
    def __init__(self):
        """サーバーの初期化（スレッドセーフに一度だけ実行される）"""
        # インスタンスロックを取得して初期化の競合状態を防止
        with self.__class__._instance_lock:
            # 初期化が既に完了していたら何もしない
            if self.__class__._init_done:
                return
                
            # この行に到達したら初期化開始としてマーク
            # かつロックで保護されているので競合状態は発生しない
            self.__class__._init_done = True
            
        # スレッドセーフな状態管理のためのロックを追加
        import threading as py_threading  # モジュール名の衝突を避ける
        self._running_lock = py_threading.Lock()
        self._running = False
        
        self.host = config.get_config("server", "default_host", "localhost")
        self.port = config.get_config("server", "default_port", 8000)
        self.server = None
        self.server_thread = None
        self.app = None  # FastAPI/UVICORNアプリ
        self.commands = {}  # 登録されたコマンド
        self.background_tasks = {}  # 長時間実行タスク
        
        # APIバージョン情報を設定から読み込む
        self.api_version = config.get_config("api", "version", "1.0.0")
        self.compatible_versions = config.get_config("api", "compatible_versions", ["1.0.0"])
        self.check_compatibility = config.get_config("api", "check_compatibility", True)
        self.require_version = config.get_config("api", "require_version", False)
        
        # メタデータ
        self.metadata = {
            "name": "Blender Unified MCP",
            "version": self.api_version,
            "description": "Unified Model Control Protocol for Blender",
            "compatible_versions": self.compatible_versions,
            "require_version": self.require_version
        }
        
        # サーバーのバックエンドタイプ
        if FASTAPI_AVAILABLE:
            self.backend_type = "fastapi"
        else:
            self.backend_type = "simple_http"
        
        logger.info(f"サーバーバックエンド: {self.backend_type}")
    
    def register_command(self, name: str, handler: Callable, description: str = None, schema: Dict = None, min_version: str = None):
        """コマンドをサーバーに登録
        
        Args:
            name: コマンド名
            handler: コマンドハンドラ関数
            description: コマンドの説明（オプショナル）
            schema: 引数のスキーマ（オプショナル）
            min_version: このコマンドを使用するために必要な最小クライアントバージョン（オプショナル）
        """
        if name in self.commands:
            logger.warning(f"コマンド '{name}' は既に登録されています。上書きします。")
        
        logger.info(f"コマンド '{name}' を登録しています")
        
        # コマンド情報を保存
        command_info = {
            "handler": handler,
            "description": description or "",
            "schema": schema or {},
        }
        
        # 最小バージョンが指定されていれば追加
        if min_version:
            command_info["min_version"] = min_version
            logger.info(f"コマンド '{name}' に最小バージョン要件: {min_version} を設定しました")
        
        self.commands[name] = command_info
        
        logger.info(f"コマンド '{name}' を登録しました")
        return True
    
    def unregister_command(self, name: str) -> bool:
        """コマンドの登録を解除
        
        Args:
            name: コマンド名
            
        Returns:
            成功したかどうか
        """
        if name in self.commands:
            del self.commands[name]
            logger.info(f"コマンド '{name}' の登録を解除しました")
            return True
        
        logger.warning(f"コマンド '{name}' は登録されていません")
        return False
    
    def start(self, host: str = None, port: int = None) -> bool:
        """サーバーを起動
        
        Args:
            host: ホスト名（省略時はデフォルト値を使用）
            port: ポート番号（省略時はデフォルト値を使用）
            
        Returns:
            起動が成功したかどうか
        """
        if self.running:
            logger.warning("サーバーは既に実行中です")
            return True
        
        # ホスト/ポートの設定
        self.host = host or self.host
        self.port = port or self.port
        
        logger.info(f"サーバーを起動します (ホスト: {self.host}, ポート: {self.port}, バックエンド: {self.backend_type})")
        
        try:
            if self.backend_type == "fastapi":
                return self._start_fastapi_server()
            else:
                return self._start_simple_http_server()
        except Exception as e:
            logger.error(f"サーバーの起動中にエラーが発生しました: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def _start_fastapi_server(self) -> bool:
        """FastAPIサーバーを起動"""
        # 初期状態では実行中ではないことを確認
        if self.running:
            logger.warning("サーバーは既に実行中です")
            return True
            
        # サーバー起動前にまずリソースがクリーンな状態であることを確認
        self.server = None
        self.server_thread = None
        self.app = None
            
        try:
            from fastapi import FastAPI, Request, Response, BackgroundTasks
            from fastapi.middleware.cors import CORSMiddleware
            import uvicorn
            import asyncio
            from pydantic import BaseModel, Field
            import json
            
            logger.info("FastAPIサーバーを初期化しています...")
            
            # FastAPIアプリの作成
            self.app = FastAPI(
                title="Blender Unified MCP API",
                description="Unified MCP API for Blender",
                version="1.3.0"
            )
            
            # CORSミドルウェアの追加
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            # APIバージョンヘッダーミドルウェア
            @self.app.middleware("http")
            async def add_api_version_header(request: Request, call_next):
                response = await call_next(request)
                # すべてのレスポンスにバージョン情報を含める
                response.headers["X-MCP-API-Version"] = self.api_version
                return response
            
            # ルートエンドポイント
            @self.app.get("/")
            async def get_root():
                return {
                    "message": "Blender Unified MCP API",
                    "version": self.api_version,
                    "endpoints": ["/api/info", "/info", "/objects", "/execute/{command_name}", "/graphql"],
                    "docs_url": "/docs"
                }
                
            # APIバージョン情報エンドポイント
            @self.app.get("/api/info")
            async def get_api_info():
                return self.metadata
            
            # 情報エンドポイント
            @self.app.get("/info")
            async def get_info():
                return {
                    "name": "Blender Unified MCP",
                    "version": "1.3.0",
                    "description": "MCPサーバーモジュール",
                    "status": "running",
                    "backend": self.backend_type,
                    "commands": list(self.commands.keys()),
                    "graphql_available": GRAPHQL_AVAILABLE
                }
            
            # オブジェクト一覧エンドポイント
            @self.app.get("/objects")
            async def get_objects():
                objects = mcp_threading.execute_in_main_thread(
                    lambda: [{
                        "name": obj.name,
                        "type": obj.type,
                        "visible": obj.visible_get()
                    } for obj in bpy.data.objects]
                )
                
                return {
                    "count": len(objects),
                    "objects": objects
                }
            
            # コマンド実行エンドポイント
            @self.app.post("/execute/{command_name}")
            async def execute_command(command_name: str, request: Request):
                # コマンド存在チェック
                if command_name not in self.commands:
                    return {
                        "success": False,
                        "error": f"コマンド '{command_name}' が見つかりません"
                    }
                
                # リクエストボディの取得
                try:
                    body = await request.json()
                except:
                    body = {}
                
                # バージョン互換性チェック
                client_version = body.pop('api_version', None)
                
                # 互換性チェックが有効な場合
                if self.check_compatibility:
                    # バージョン情報が必要な場合
                    if self.require_version and client_version is None:
                        return {
                            "success": False,
                            "error": "このサーバーではクライアントからのAPIバージョン提供が必要です。リクエストに'api_version'パラメータを含めてください。"
                        }
                    
                    # バージョンが指定されていれば互換性をチェック
                    if client_version is not None and not self.check_version_compatibility(client_version):
                        return {
                            "success": False,
                            "error": f"互換性のないAPIバージョン: {client_version} (サーバーは {self.api_version} を使用中)"
                        }
                    
                    # コマンドの最小バージョン要件チェック
                    command = self.commands[command_name]
                    if client_version is not None and "min_version" in command:
                        min_version = command["min_version"]
                        if config._compare_versions(client_version, min_version) < 0:
                            return {
                                "success": False,
                                "error": f"このコマンドには最小バージョン {min_version} が必要ですが、クライアントは {client_version} を使用しています"
                            }
                
                command = self.commands[command_name]
                handler = command["handler"]
                
                try:
                    # メインスレッドで実行
                    result = mcp_threading.execute_in_main_thread(handler, **body)
                    return {
                        "success": True,
                        "result": result,
                        "api_version": self.api_version  # レスポンスにバージョン情報を含める
                    }
                except Exception as e:
                    error_response = errors.create_error_response(
                        e, include_traceback=True)
                    # エラーレスポンスにもバージョン情報を含める
                    error_response["api_version"] = self.api_version
                    return error_response
            
            # GraphQLエンドポイント（利用可能な場合）
            if GRAPHQL_AVAILABLE:
                @self.app.post("/graphql")
                async def graphql_endpoint(request: Request):
                    try:
                        body = await request.json()
                        query = body.get("query")
                        variables = body.get("variables", {})
                        
                        if not query:
                            return {
                                "errors": [{
                                    "message": "query パラメーターが必要です"
                                }]
                            }
                        
                        result = graphql_api.query_blender(query, variables)
                        return result
                    except Exception as e:
                        logger.error(f"GraphQLリクエスト処理エラー: {str(e)}")
                        import traceback
                        logger.debug(traceback.format_exc())
                        return {
                            "errors": [{
                                "message": f"GraphQLリクエスト処理エラー: {str(e)}"
                            }]
                        }
            
            # サーバーをスレッドで起動
            def run_server():
                try:
                    # uvicornサーバーを作成し、インスタンスを保存
                    config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="info")
                    self.uvicorn_server = uvicorn.Server(config)
                    
                    # サーバーが実際に起動した状態に設定
                    self.running = True
                    
                    # サーバー起動のログ出力
                    logger.info(f"FastAPI/uvicornサーバーが起動しました (host: {self.host}, port: {self.port})")
                    
                    # サーバーを起動
                    self.uvicorn_server.serve()
                except OSError as e:
                    # ポートが使用中の場合のエラー処理
                    if "Address already in use" in str(e):
                        logger.error(f"ポート {self.port} は既に使用されています")
                        self.running = False
                    else:
                        logger.error(f"uvicornサーバー起動エラー: {str(e)}")
                except Exception as e:
                    logger.error(f"uvicornサーバー実行中に予期しないエラーが発生しました: {str(e)}")
                    import traceback
                    logger.debug(traceback.format_exc())
                finally:
                    # サーバー終了時のクリーンアップ
                    logger.info("uvicornサーバーが停止しました")
                    self.running = False
            
            # サーバースレッドを作成して起動
            self.server_thread = threading.Thread(target=run_server)
            self.server_thread.daemon = True
            
            # サーバースレッドを起動（この時点ではまだサーバーは完全に起動していない）
            logger.info(f"FastAPIサーバーを起動しています... (host: {self.host}, port: {self.port})")
            self.server_thread.start()
            
            # サーバーの起動を待機する小さな遅延（完全な起動を待つわけではない）
            import time
            time.sleep(0.5)
            
            # スレッドが正常に開始されたことをログで知らせる
            logger.info(f"FastAPIサーバーが起動しました (ホスト: {self.host}, ポート: {self.port})")
            return True
        except OSError as ose:
            # ポートが使用中などのOSレベルのエラー
            self.running = False  # 実行中ではない状態に確実に戻す
            
            # リソースのクリーンアップ
            self.server = None
            self.server_thread = None
            
            if "Address already in use" in str(ose):
                logger.error(f"ポート {self.port} は既に使用されています")
                self.report_port_conflict()
            else:
                logger.error(f"FastAPIサーバーの起動中にOSエラーが発生しました: {str(ose)}")
            
            import traceback
            logger.debug(traceback.format_exc())
            return False
        except Exception as e:
            # その他の例外
            self.running = False  # 実行中ではない状態に確実に戻す
            
            # リソースのクリーンアップ
            self.server = None
            self.server_thread = None
            
            logger.error(f"FastAPIサーバーの起動中に予期せぬエラーが発生しました: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def _start_simple_http_server(self) -> bool:
        """シンプルなHTTPサーバーを起動"""
        # 初期状態では実行中ではないことを確認
        if self.running:
            logger.warning("サーバーは既に実行中です")
            return True
            
        # サーバー起動前にまずリソースがクリーンな状態であることを確認
        self.server = None
        self.server_thread = None
            
        try:
            # リクエストハンドラを拡張して現在のサーバーインスタンスへの参照を持たせる
            server_instance = self
            
            class MCPExtendedRequestHandler(MCPRequestHandler):
                def __init__(self, *args, **kwargs):
                    # 正しい順序で初期化: まず親クラスの__init__を呼び出し、その後に自身の属性を設定
                    super().__init__(*args, **kwargs)
                    self.server_instance = server_instance
                
                def do_POST(self):
                    """POSTリクエストの処理"""
                    logger.info(f"POSTリクエスト受信: {self.path}")
                    
                    # コマンド実行エンドポイント
                    if self.path.startswith("/execute/"):
                        command_name = self.path.split("/")[-1]
                        
                        if command_name not in self.server_instance.commands:
                            self._set_headers()
                            response = {
                                "success": False,
                                "error": f"コマンド '{command_name}' が見つかりません"
                            }
                            self.wfile.write(json.dumps(response).encode())
                            return
                        
                        # リクエストボディの取得
                        content_length = int(self.headers['Content-Length'])
                        body = self.rfile.read(content_length).decode('utf-8')
                        
                        try:
                            params = json.loads(body) if body else {}
                        except json.JSONDecodeError:
                            params = {}
                        
                        # コマンドの実行
                        command = self.server_instance.commands[command_name]
                        handler = command["handler"]
                        
                        try:
                            # メインスレッドで実行
                            result = mcp_threading.execute_in_main_thread(handler, **params)
                            
                            self._set_headers()
                            response = {
                                "success": True,
                                "result": result
                            }
                            self.wfile.write(json.dumps(response).encode())
                        except Exception as e:
                            self._set_headers()
                            response = errors.create_error_response(e, include_traceback=True)
                            self.wfile.write(json.dumps(response).encode())
                    
                    # その他のエンドポイント
                    else:
                        self._set_headers()
                        response = {
                            "success": False,
                            "error": f"エンドポイント '{self.path}' が見つかりません"
                        }
                        self.wfile.write(json.dumps(response).encode())
            
            # サーバーの起動を予告
            logger.info(f"シンプルHTTPサーバーを起動しています... (ホスト: {self.host}, ポート: {self.port})")
            
            try:
                # サーバーの起動
                self.server = HTTPServer((self.host, self.port), MCPExtendedRequestHandler)
                self.server_thread = threading.Thread(target=self.server.serve_forever)
                self.server_thread.daemon = True
                self.server_thread.start()
                
                # サーバーの発行処理がスレッド内で開始されるのを待つ短い遅延
                import time
                time.sleep(0.5)
                
                # 起動確認後に状態を設定
                self.running = True
                logger.info(f"シンプルHTTPサーバーが起動しました (ホスト: {self.host}, ポート: {self.port})")
                return True
            except OSError as ose:
                # ポートが使用中などのOSレベルのエラー
                self.running = False  # 実行中ではない状態に確実に戻す
                
                # リソースのクリーンアップ
                self.server = None
                self.server_thread = None
                
                if "Address already in use" in str(ose):
                    logger.error(f"ポート {self.port} は既に使用されています")
                    self.report_port_conflict()
                else:
                    logger.error(f"サーバー起動時にOSエラーが発生しました: {str(ose)}")
                
                import traceback
                logger.debug(traceback.format_exc())
                return False
        except Exception as e:
            # その他の例外
            self.running = False  # 実行中ではない状態に確実に戻す
            
            # リソースのクリーンアップ
            self.server = None
            self.server_thread = None
            
            logger.error(f"シンプルHTTPサーバーの起動中に予期せぬエラーが発生しました: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def stop(self) -> bool:
        """サーバーを停止
        
        Returns:
            停止が成功したかどうか
        """
        # 実行中かどうか確認
        if not self.running:
            logger.info("サーバーは既に停止しています")
            return True
        
        logger.info("サーバーを停止しています...")
        
        try:
            # 先に実行状態を更新して、新しいリクエストが来ないようにする
            self.running = False
            
            # バックエンドタイプによる処理分岐
            if self.backend_type == "fastapi":
                # FastAPI/uvicornサーバーの停止
                if hasattr(self, 'uvicorn_server') and self.uvicorn_server:
                    logger.debug("uvicornサーバーに終了シグナルを送信")
                    self.uvicorn_server.should_exit = True
            else:
                # シンプルHTTPサーバーの停止
                if self.server:
                    logger.debug("シンプルHTTPサーバーをシャットダウン")
                    try:
                        self.server.shutdown()
                        self.server.server_close()
                    except Exception as e:
                        logger.warning(f"サーバーのシャットダウン中にエラーが発生: {str(e)}")
            
            # スレッドの終了を待機（タイムアウト付き）
            if self.server_thread and self.server_thread.is_alive():
                import time
                logger.debug("サーバースレッドの終了を待機中 (5秒タイムアウト)")
                self.server_thread.join(timeout=5.0)  # 5秒間待機
                
                # タイムアウト後もスレッドが終了していない場合をチェック
                if self.server_thread.is_alive():
                    logger.warning("サーバースレッドが5秒以内に終了しませんでしたが、デーモンスレッドなのでプロセス終了時に終了します")
                else:
                    logger.debug("サーバースレッドが正常に終了しました")
            
            self.server = None
            self.server_thread = None
            self.running = False
            
            logger.info("サーバーは正常に停止しました")
            return True
        except Exception as e:
            logger.error(f"サーバー停止中にエラーが発生しました: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    @property
    def running(self):
        """スレッドセーフに実行中かどうかを取得"""
        with self._running_lock:
            return self._running
    
    @running.setter
    def running(self, value):
        """スレッドセーフに実行状態を設定"""
        with self._running_lock:
            old_value = self._running
            self._running = value
            if old_value != value:
                status = "起動" if value else "停止"
                logger.debug(f"サーバーの状態を{status}に変更")
    
    def is_running(self) -> bool:
        """サーバーが実行中かどうかを確認"""
        return self.running  # プロパティアクセッサ経由でスレッドセーフに取得
    
    def get_commands(self) -> List[str]:
        """登録されているコマンドの一覧を取得"""
        return list(self.commands.keys())
    
    def report_port_conflict(self):
        """ポート衝突を通知する処理"""
        # ログにエラーメッセージを出力
        error_msg = f"ポート {self.port} は既に使用中です。設定で別のポートを指定してください。"
        logger.error(error_msg)

        # メインスレッドキューを使用してUI通知を実行
        try:
            # メインスレッドで実行する関数
            def show_error_in_main_thread():
                try:
                    # Blenderユーザーインターフェースへのエラー通知
                    bpy.ops.mcp.report_message('EXEC_DEFAULT', message_type='ERROR', message=error_msg)
                    return True
                except Exception as e:
                    logger.warning(f"UI通知の実行に失敗しました: {str(e)}")
                    return False
            
            # スレッド処理モジュールをインポート
            from . import threading as mcp_threading
            if hasattr(mcp_threading, 'execute_in_main_thread'):
                # メインスレッドキューに送信
                mcp_threading.execute_in_main_thread(show_error_in_main_thread, timeout=1.0)
        except ImportError:
            logger.warning("スレッド処理モジュールをインポートできないため、UI通知をスキップします")
        except Exception as e:
            logger.warning(f"ポート衝突通知処理中にエラーが発生しました: {str(e)}")
        
        # 実行ステータスをリセット
        self.running = False
    
    def check_version_compatibility(self, client_version: str) -> bool:
        """クライアントのバージョンがサーバーと互換性があるか確認
        
        Args:
            client_version: クライアントが使用するAPIバージョン
            
        Returns:
            互換性がある場合はTrue、ない場合はFalse
        """
        # 同じバージョンならOK
        if client_version == self.api_version:
            return True
        
        # 互換性のあるバージョンリストに含まれているか確認
        if client_version in self.compatible_versions:
            return True
        
        # それ以外は互換性なし
        logger.warning(f"互換性のないクライアントバージョン: {client_version} (サーバー: {self.api_version})")
        return False
    
    def execute_command(self, command_name: str, **params) -> Any:
        """コマンドを実行
        
        Args:
            command_name: コマンド名
            **params: コマンドの引数
            
        Returns:
            コマンドの戻り値
        
        Raises:
            KeyError: コマンドが見つからない場合
            ValueError: APIバージョンが互換性がない場合やバージョンが必要な場合
            Exception: コマンド実行中にエラーが発生した場合
        """
        # APIバージョンのチェック
        client_version = params.pop('api_version', None)
        
        # 互換性チェックが有効な場合
        if self.check_compatibility:
            # バージョン情報が必要な場合のチェック
            if self.require_version and client_version is None:
                raise ValueError("このサーバーではクライアントからのAPIバージョン提供が必要です。リクエストに'api_version'パラメータを含めてください。")
            
            # バージョンが提供されていれば互換性をチェック
            if client_version is not None and not self.check_version_compatibility(client_version):
                raise ValueError(f"互換性のないAPIバージョン: {client_version} (サーバーは {self.api_version} を使用中)")
        
        # コマンドの存在確認
        if command_name not in self.commands:
            raise KeyError(f"コマンド '{command_name}' が見つかりません")
        
        command = self.commands[command_name]
        handler = command["handler"]
        
        # コマンドのバージョン要件が指定されている場合のチェック
        if self.check_compatibility and client_version is not None and "min_version" in command:
            min_version = command["min_version"]
            # バージョン比較ユーティリティを使用
            if config._compare_versions(client_version, min_version) < 0:
                raise ValueError(f"このコマンドには最低バージョン {min_version} が必要ですが、クライアントは {client_version} を使用しています")
        
        logger.info(f"コマンド '{command_name}' を実行中...")
        
        try:
            # メインスレッドで実行する
            return mcp_threading.execute_in_main_thread(handler, **params)
        except Exception as e:
            # エラー情報をログに記録
            logger.error(f"コマンド '{command_name}' の実行中にエラーが発生しました: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            
            # より詳細な情報を含む新しい例外を発生させ、元の例外をチェイン
            error_message = f"コマンド '{command_name}' の実行に失敗しました: {str(e)}"
            raise ValueError(error_message) from e
    
# サーバーインスタンス取得用のエイリアス関数
def get_server_instance():
    """サーバーインスタンスを取得するヘルパー関数"""
    return MCPServer.get_instance()

def register():
    """サーバーを登録して起動"""
    logger.info("統合MCPサーバーモジュールを登録・起動します")
    
    try:
        mcp_threading.initialize()
        logger.info("スレッド処理システムを初期化しました")
    except Exception as e:
        logger.error(f"スレッド処理システムの初期化に失敗しました: {str(e)}") 
    
    # サーバーを起動
    server = MCPServer.get_instance()
    if server and not server.is_running():
        # コンフィグからポート番号を取得（指定されていれば）
        port = None
        if config and hasattr(config, 'SERVER_PORT'):
            port = config.SERVER_PORT
        
        success = server.start(port=port)
        if success:
            logger.info(f"MCPサーバーが正常に起動しました (port: {server.port})")
        else:
            logger.error("MCPサーバーの起動に失敗しました")
    else:
        logger.info("サーバーはすでに実行中か、利用できません")

def unregister():
    """サーバーを停止して登録解除"""
    logger.info("統合MCPサーバーモジュールを停止・登録解除します")
    
    # サーバーインスタンスを取得して停止
    server = MCPServer.get_instance()
    if server and server.is_running():
        server.stop()
        logger.info("MCPサーバーが正常に停止しました")
    
    # シングルトンインスタンスをクリア
    MCPServer._instance = None
    
    # スレッド処理システムのシャットダウン
    try:
        mcp_threading.shutdown()
        logger.info("スレッド処理システムをシャットダウンしました")
    except Exception as e:
        logger.warning(f"スレッド処理システムのシャットダウンに失敗しました: {str(e)}")
