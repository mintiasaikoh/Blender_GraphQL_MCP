"""
Blender GraphQL API HTTP Serverモジュール
GraphQLを通してBlenderと通信するHTTPサーバーを提供します
"""

import logging
import os
import sys
from typing import Dict, Any, Callable, List, Optional, Union, Tuple
import threading
import time
import json
import traceback

# FastAPIとUvicornをチェック
try:
    import fastapi
    from fastapi import FastAPI, Request, Response, HTTPException, Depends, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.openapi.utils import get_openapi
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
    HTTP_SERVER_AVAILABLE = True
except ImportError:
    HTTP_SERVER_AVAILABLE = False

# Logger設定
logger = logging.getLogger("blender_graphql_mcp.http_server")

# GraphQL関連のグローバル変数
GRAPHQL_AVAILABLE = False
query_blender = None  # GraphQLクエリ実行関数の参照


def _load_graphql_dependencies():
    """遅延読み込み関数: GraphQL依存関係を読み込みます"""
    global GRAPHQL_AVAILABLE, query_blender
    
    # 既にロード済みの場合は再利用
    if GRAPHQL_AVAILABLE and query_blender is not None:
        logger.info("GraphQL機能は既にロードされています")
        return True
    
    # まず依存ライブラリがインストールされているか確認
    try:
        import graphql
        logger.info(f"graphql-coreベースライブラリが利用可能です (バージョン: {getattr(graphql, '__version__', 'unknown')})")
    except ImportError as e:
        logger.error(f"graphql-coreライブラリがインストールされていません: {e}")
        logger.info("インストール方法: cd /Applications/Blender.app/Contents/Resources/4.4/python/bin && ./python3.11 -m pip install graphql-core")
        GRAPHQL_AVAILABLE = False
        return False
        
    try:
        # GraphQLモジュールをインポートする前に必要なディレクトリを確認
        import os
        import sys
        addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if addon_dir not in sys.path:
            sys.path.append(addon_dir)
            logger.info(f"アドオンディレクトリをパスに追加しました: {addon_dir}")
            
        # GraphQLモジュールを不具合なくインポートできるように再ロード
        import importlib
        if 'blender_graphql_mcp.graphql.api' in sys.modules:
            importlib.reload(sys.modules['blender_graphql_mcp.graphql.api'])
            logger.info("blender_graphql_mcp.graphql.apiを再ロードしました")
            
        # GraphQLモジュールを遅延インポート
        from ..graphql import api
        
        if hasattr(api, 'query_blender'):
            query_blender = api.query_blender
            GRAPHQL_AVAILABLE = getattr(api, 'GRAPHQL_AVAILABLE', True)  # デフォルトでTrueとみなす
            
            # 明示的にモジュールを登録
            if hasattr(api, 'register') and callable(api.register):
                try:
                    api.register()
                    logger.info("GraphQL APIモジュールを登録しました")
                except Exception as e:
                    logger.error(f"GraphQL APIモジュールの登録中にエラーが発生しました: {e}")
                    
            logger.info(f"GraphQL機能を利用可能: {GRAPHQL_AVAILABLE}")
            return GRAPHQL_AVAILABLE
            
        else:
            logger.error("GraphQL APIモジュールにquery_blender関数が見つかりません")
            GRAPHQL_AVAILABLE = False
            return False
            
    except Exception as e:
        logger.error(f"GraphQL依存関係のロード中にエラーが発生しました: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        GRAPHQL_AVAILABLE = False
        return False


class MCPHttpServer:
    """GraphQL APIを実装するHTTPサーバークラス"""
    
    def __init__(self, host: str = "localhost", port: int = 8765, log_file: str = None):
        """GraphQL HTTP APIサーバーの初期化"""
        self.host = host
        self.port = port
        self.log_file = log_file or os.path.expanduser("~/blender_mcp_server.log")
        
        # APIサーバーインスタンス用変数
        self.app = None  # FastAPIアプリケーションインスタンス
        self.server_thread = None  # サーバー実行スレッド
        self.is_running = False  # サーバー実行状態フラグ
        self.setup_logging()  # ロギングを設定
        
    def setup_logging(self):
        """ロギングの設定"""
        if not os.path.exists(os.path.dirname(self.log_file)):
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)
    
    def start_graphql_server(self, host: str = None, port: int = None) -> bool:
        """GraphQL専用サーバーを起動するメソッド"""
        # ホストとポートが指定されていれば上書き
        if host is not None:
            self.host = host
        if port is not None:
            self.port = port
            
        # 通常のstartメソッドを呼び出す
        return self.start()
        
    def start(self) -> bool:
        """GraphQLサーバーを起動"""
        if not HTTP_SERVER_AVAILABLE:
            logger.error("一部の依存関係が不足しているため、サーバーを起動できません")
            return False
        
        if self.is_running:
            logger.warning("サーバーは既に実行中です")
            return True
        
        try:
            # FastAPIアプリを作成
            self.app = FastAPI(title="Blender GraphQL API", version="1.0.0")
            
            # CORSミドルウェアを追加
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            # GraphQL専用モードのミドルウェアを追加
            @self.app.middleware("http")
            async def graphql_only_middleware(request, call_next):
                # GraphQL関連のパスのみを許可
                allowed_paths = ["/", "/graphql", "/graphiql"]
                if request.url.path not in allowed_paths:
                    logger.warning(f"GraphQL専用モード: アクセス拒否 - {request.method} {request.url.path}")
                    return Response(content=json.dumps({
                        "error": "This API only accepts GraphQL requests. Please use the /graphql endpoint.",
                        "graphql_endpoint": "/graphql",
                        "graphiql_interface": "/graphiql"
                    }), media_type="application/json", status_code=400)
                return await call_next(request)
            
            # ルートとルーティングを設定
            self._setup_routes()
            
            # 別スレッドでサーバーを起動
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            
            # 起動を少し待つ
            time.sleep(1)
            self.is_running = True
            logger.info(f"GraphQL APIサーバーを開始: {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"サーバー起動エラー: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def stop(self) -> bool:
        """サーバーを停止"""
        if not self.is_running:
            logger.warning("サーバーは実行中ではありません")
            return True
        
        try:
            self.is_running = False
            # サーバースレッドを終了
            # UvicornサーバーのAPIに直接アクセスする方法はないため、
            # スレッドをデーモンとして実行し、終了時に自動的に終了します
            logger.info("GraphQL APIサーバーを停止")
            return True
        except Exception as e:
            logger.error(f"サーバー停止エラー: {e}")
            return False
    
    def _run_server(self):
        """サーバーを起動するプライベートメソッド"""
        try:
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="error"
            )
        except Exception as e:
            logger.error(f"サーバー実行エラー: {e}")
    
    def _setup_routes(self):
        """APIルートをセットアップ"""
        try:
            # ベースルート
            @self.app.get("/")
            async def root():
                return {
                    "message": "Blender GraphQL API Server", 
                    "status": "running",
                    "graphql_endpoint": "/graphql",
                    "graphiql_interface": "/graphiql"
                }

            # GraphQL依存関係をロード
            graphql_loaded = _load_graphql_dependencies()
            logger.info(f"GraphQLロード状態: {graphql_loaded}")

            # GraphQL専用モードを設定
            logger.info("GraphQL専用モードで継続します")

            # GraphiQLインターフェイスの追加
            try:
                from ..graphql.graphiql import get_graphiql_html
                logger.info("GraphiQLインターフェースを有効化します")

                # GraphiQLインターフェースは/graphiqlパスで提供
                @self.app.get("/graphiql", response_class=HTMLResponse)
                async def graphiql_interface():
                    """
                    GraphiQLインターフェースを提供するエンドポイント
                    """
                    return get_graphiql_html()
            except ImportError as e:
                logger.warning(f"GraphiQLモジュールのインポートに失敗しました: {e}")

            # 正規のGraphQLライブラリを使用したGraphQL APIエンドポイント
            @self.app.post("/graphql")
            async def graphql_endpoint(request: Request):
                """
                GraphQL標準に準拠したAPIエンドポイント
                """
                try:
                    # リクエストボディを解析
                    body = await request.json()
                    query = body.get("query")
                    variables = body.get("variables", {})
                    operation_name = body.get("operationName")
                    
                    # ログ記録
                    logger.info(f"GraphQLリクエスト受信: {query[:100] if query else ''}...")
                    logger.info(f"Operation: {operation_name}, Variables: {variables}")
                    
                    # GraphQL依存関係をチェック
                    if not GRAPHQL_AVAILABLE:
                        error_msg = "GraphQLライブラリがインストールされていません"
                        logger.error(error_msg)
                        return {"errors": [{"message": error_msg}]}
                    
                    # クエリが空の場合はエラー
                    if not query:
                        return {"errors": [{"message": "queryパラメータが必要です"}]}
                    
                    # GraphQL APIモジュールをチェック
                    from ..graphql import api as graphql_api
                    
                    if not hasattr(graphql_api, 'query_blender'):
                        error_msg = "GraphQL APIモジュールにquery_blender関数が見つかりません"
                        logger.error(error_msg)
                        return {"errors": [{"message": error_msg}]}
                    
                    # GraphQLクエリを実行
                    try:
                        result = graphql_api.query_blender(query, variables, operation_name)
                        
                        # 実行結果をログに記録 (デバッグ用)
                        logger.debug(f"GraphQLクエリ結果: {result}")
                        
                        # 結果を返す
                        return JSONResponse(content=result, status_code=200)
                    except Exception as e:
                        # クエリ実行中のエラーをキャッチ
                        logger.error(f"GraphQLクエリ実行エラー: {str(e)}")
                        logger.error(traceback.format_exc())
                        
                        # 詳細なエラー情報を提供
                        error_response = {
                            "errors": [{
                                "message": f"GraphQLクエリ実行エラー: {str(e)}",
                                "extensions": {
                                    "code": "EXECUTION_ERROR",
                                    "classification": "ServerError",
                                    "exception": {
                                        "type": e.__class__.__name__,
                                        "stacktrace": traceback.format_exc().split('\n')
                                    },
                                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                }
                            }]
                        }
                        return JSONResponse(content=error_response, status_code=500)
                    
                    # 結果を返す
                    return JSONResponse(content=result, status_code=200)
                except Exception as e:
                    # クエリ実行中のエラーをキャッチ
                    logger.error(f"GraphQLエンドポイントエラー: {str(e)}")
                    logger.error(traceback.format_exc())
                    
                    # 拡張エラー情報を含むJSONレスポンス
                    error_response = {
                        "errors": [{
                            "message": f"GraphQLエンドポイントエラー: {str(e)}",
                            "extensions": {
                                "code": "GRAPHQL_ENDPOINT_ERROR",
                                "classification": "ServerError",
                                "exception": {"type": e.__class__.__name__},
                                "path": "/graphql",
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                        }]
                    }
                    
                    return JSONResponse(content=error_response, status_code=500)
            
            # GraphQLエンドポイントの設定完了をログ記録
            logger.info("GraphQLエンドポイントを追加: /graphql")

            # 旧MCPコマンドルートをJSON APIが廃止されたため削除しました
            # GraphQL APIのみを使用してください
            logger.info("GraphQLインターフェースのみをサポートします - JSON APIは廃止されました")
            
            # エラーハンドラーの設定
            @self.app.exception_handler(HTTPException)
            async def http_exception_handler(request, exc):
                # GraphQL API専用のシンプルなエラーメッセージ
                error_content = {
                    "error": {
                        "code": exc.status_code,
                        "message": str(exc.detail),
                        "type": "HttpException"
                    },
                    "info": {
                        "description": "Blender GraphQL APIでエラーが発生しました",
                        "graphql_endpoint": "/graphql",
                        "graphiql_interface": "/graphiql"
                    }
                }
                
                return JSONResponse(
                    status_code=exc.status_code,
                    content=error_content
                )
            
            @self.app.exception_handler(Exception)
            async def general_exception_handler(request, exc):
                logger.error(f"サーバーエラー: {exc}")
                
                # GraphQL API専用のシンプルなエラーメッセージ
                error_content = {
                    "error": {
                        "code": "SERVER_ERROR",
                        "message": str(exc),
                        "type": exc.__class__.__name__
                    },
                    "info": {
                        "description": "Blender GraphQL APIサーバーで内部エラーが発生しました",
                        "graphql_endpoint": "/graphql",
                        "graphiql_interface": "/graphiql"
                    }
                }
                
                return JSONResponse(
                    content=error_content,
                    status_code=500
                )
        
        except Exception as e:
            logger.error(f"ルート設定エラー: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        # GraphQL専用モードをログに記録
        logger.info("GraphQL API専用モードで動作しています")
    
    def _run_server(self):
        """サーバーを起動するプライベートメソッド"""
        try:
            import uvicorn
            # uvicornの設定を指定してサーバーを起動
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=False  # アクセスログを無効化
            )
            server = uvicorn.Server(config)
            server.run()
        except Exception as e:
            logger.error(f"サーバー起動中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())