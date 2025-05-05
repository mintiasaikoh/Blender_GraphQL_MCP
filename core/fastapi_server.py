"""
Blender Unified MCP - FastAPIベースの高度なサーバー実装
高機能なREST APIとGraphQLをサポートするMCPサーバー
"""

import logging
import threading
import time
import json
import os
import inspect
import socket
from typing import Dict, List, Any, Optional, Union, Callable, Type

try:
    import bpy
except ImportError:
    # テスト環境用ダミー
    bpy = None

# FastAPI関連のインポート - 互換モードなし
import asyncio
import json
import logging
import threading
from typing import Dict, Any, Optional, List, Union

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# JSONハンドラーのインポート
try:
    from .json_handlers import create_primitive, delete_objects, transform_object, get_scene_info
except ImportError as e:
    logging.error(f"JSON handlers import error: {e}")

# 常にFastAPIモードを有効に設定
FASTAPI_AVAILABLE = True

# GraphQL関連のインポート
try:
    import graphene
    from starlette.graphql import GraphQLApp
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False

# ロギング設定
logger = logging.getLogger("mcp.fastapi_server")

# モデル定義
class CommandRequest(BaseModel):
    """コマンド実行リクエスト"""
    command: str
    params: Dict[str, Any] = Field(default_factory=dict)

class APIResponse(BaseModel):
    """標準APIレスポンス"""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success(cls, message: str = "Success", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """成功レスポンスを生成"""
        return cls(status="success", message=message, data=data).dict()
    
    @classmethod
    def error(cls, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """エラーレスポンスを生成"""
        return cls(status="error", message=message, data=data).dict()

class ObjectInfo(BaseModel):
    """オブジェクト情報モデル"""
    name: str
    type: str
    location: Optional[List[float]] = None
    dimensions: Optional[List[float]] = None
    vertices: Optional[int] = None
    faces: Optional[int] = None
    materials: Optional[List[str]] = None

class SceneInfo(BaseModel):
    """シーン情報モデル"""
    name: str
    objects_count: int
    active_object: Optional[str] = None
    frame_current: int
    frame_start: int
    frame_end: int

class DeleteObjectsRequest(BaseModel):
    keep_cameras: bool = Field(True, description="カメラを残す")
    keep_lights: bool = Field(True, description="ライトを残す")
    objects: Optional[List[str]] = Field(None, description="削除する特定のオブジェクト名のリスト（指定した場合は他のオプションは無視）")

# メインスレッド実行ユーティリティ
def execute_in_main_thread(func: Callable, *args, **kwargs) -> Any:
    """Blenderのメインスレッドで関数を実行するユーティリティ"""
    if bpy is None:
        # Blender環境でない場合は直接実行
        return func(*args, **kwargs)
    
    result_container = []
    error_container = []
    
    def wrapper():
        try:
            result = func(*args, **kwargs)
            result_container.append(result)
        except Exception as e:
            error_container.append(e)
        return None  # タイマーから削除
    
    # メインスレッドでの実行をスケジュール
    bpy.app.timers.register(wrapper)
    
    # 結果を待つ
    max_wait = 10.0  # 最大待機時間（秒）
    start_time = time.time()
    
    while not result_container and not error_container:
        if time.time() - start_time > max_wait:
            raise TimeoutError(f"Function execution timed out after {max_wait}s")
        time.sleep(0.1)
    
    if error_container:
        raise error_container[0]
    
    return result_container[0]

# コマンドレジストリ
class Command:
    """基本コマンドクラス"""
    name = "abstract_command"
    description = "Abstract base command"
    group = "default"
    parameters = {}
    
    def execute(self, **kwargs) -> Any:
        """コマンドを実行"""
        raise NotImplementedError("Subclasses must implement execute()")
    
    @classmethod
    def get_parameter_schema(cls) -> Dict[str, Any]:
        """パラメータスキーマを取得"""
        return cls.parameters

class CommandRegistry:
    """コマンド登録と管理システム"""
    
    def __init__(self):
        self.commands: Dict[str, Type[Command]] = {}
        self.command_groups: Dict[str, List[str]] = {}
    
    def register_command(self, command_class: Type[Command]) -> None:
        """新しいコマンドを登録"""
        name = getattr(command_class, 'name', command_class.__name__)
        self.commands[name] = command_class
        
        # グループによる整理
        group = getattr(command_class, 'group', 'default')
        if group not in self.command_groups:
            self.command_groups[group] = []
        self.command_groups[group].append(name)
        
        logger.info(f"コマンド '{name}' を登録しました (グループ: {group})")
    
    def execute_command(self, command_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """コマンドを実行"""
        if command_name not in self.commands:
            raise ValueError(f"Unknown command: {command_name}")
            
        command_class = self.commands[command_name]
        command_instance = command_class()
        
        # パラメータのデフォルト値を適用
        effective_params = {}
        for param_name, param_spec in command_class.get_parameter_schema().items():
            if params and param_name in params:
                effective_params[param_name] = params[param_name]
            elif 'default' in param_spec:
                effective_params[param_name] = param_spec['default']
        
        # Blenderのメインスレッドで実行
        try:
            return execute_in_main_thread(command_instance.execute, **effective_params)
        except Exception as e:
            logger.error(f"コマンド '{command_name}' の実行中にエラーが発生しました: {str(e)}")
            raise
    
    def get_all_commands(self) -> Dict[str, Any]:
        """すべてのコマンド情報を取得"""
        result = {}
        for name, cmd_class in self.commands.items():
            result[name] = {
                'name': name,
                'description': getattr(cmd_class, 'description', ''),
                'group': getattr(cmd_class, 'group', 'default'),
                'parameters': cmd_class.get_parameter_schema()
            }
        return result

# FastAPIサーバー実装
class MCPFastAPIServer:
    """FastAPIベースのMCPサーバー実装"""
    
    def __init__(self):
        self.app = None
        self.command_registry = CommandRegistry()
        self.server_thread = None
        self.running = False
        self.host = "localhost"
        self.port = 8000
    
    def initialize(self):
        """サーバーを初期化"""
        if not FASTAPI_AVAILABLE:
            logger.error("FastAPIが利用できません。必要なライブラリをインストールしてください。")
            return False
        
        # FastAPIアプリケーションの作成
        self.app = FastAPI(
            title="Blender Unified MCP API",
            description="Blenderの3D機能にAPIからアクセスするためのModel Context Protocol",
            version="1.0.0"
        )
        
        # CORSミドルウェアの設定
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # JSON APIエンドポイントを直接追加
        self._add_json_api_endpoints()
        
        # エラーハンドラの設定
        @self.app.exception_handler(Exception)
        async def generic_exception_handler(request: Request, exc: Exception):
            logger.error(f"APIエラー: {str(exc)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=APIResponse.error(f"Internal server error: {str(exc)}")
            )
        
        # ルートエンドポイント
        @self.app.get("/", tags=["Base"])
        async def root():
            """ルートエンドポイント - サーバーステータスを返す"""
            return APIResponse.success("Blender Unified MCP API is running")
        
        # API情報エンドポイント
        @self.app.get("/api/info", tags=["Base"])
        async def api_info():
            """API情報を返す"""
            return APIResponse.success("API Information", {
                "name": "Blender Unified MCP API",
                "version": "1.0.0",
                "blender_version": getattr(bpy.app, "version_string", "Unknown") if bpy else "Blender not available",
                "endpoints": [
                    "/api/commands",
                    "/api/commands/{command_name}",
                    "/api/execute",
                    "/api/objects",
                    "/api/scene"
                ]
            })
        
        # コマンドリストエンドポイント
        @self.app.get("/api/commands", tags=["Commands"])
        async def get_commands():
            """利用可能なコマンドのリストを返す"""
            commands = self.command_registry.get_all_commands()
            return APIResponse.success("Available commands", {
                "count": len(commands),
                "commands": commands,
                "groups": self.command_registry.command_groups
            })
        
        # 特定コマンド情報エンドポイント
        @self.app.get("/api/commands/{command_name}", tags=["Commands"])
        async def get_command_info(command_name: str):
            """特定のコマンドの詳細情報を返す"""
            commands = self.command_registry.get_all_commands()
            if command_name not in commands:
                raise HTTPException(status_code=404, detail=f"Command '{command_name}' not found")
            
            return APIResponse.success(f"Command '{command_name}' details", commands[command_name])
        
        # JSONベースのコマンド実行エンドポイント
        @self.app.post("/execute", tags=["Commands"])
        async def execute_command(request: CommandRequest):
            """コマンドをJSONで実行する"""
            try:
                command_name = request.command
                params = request.params
                
                # コマンドに応じて処理を分岐
                # デバッグログを出力
                self.logger.info(f"コマンド実行: {command_name} - パラメータ: {params}")
                
                # インポートが正しく行われているか確認
                try:
                    # 必要なハンドラーを確認
                    from .json_handlers import create_primitive, delete_objects, transform_object, get_scene_info
                    
                    if command_name == "create_primitive":
                        result = create_primitive(params)
                    elif command_name == "delete_objects":
                        result = delete_objects(params)
                    elif command_name == "transform_object":
                        result = transform_object(params)
                    elif command_name == "get_scene_info":
                        result = get_scene_info()
                except Exception as import_error:
                    self.logger.error(f"JSONハンドラーのインポートエラー: {str(import_error)}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    return APIResponse.error(f"JSONハンドラーのインポートエラー: {str(import_error)}")
                
                else:
                    return APIResponse.error(f"未知のコマンド: {command_name}", {
                        "available_commands": [
                            "create_primitive",
                            "delete_objects",
                            "transform_object",
                            "get_scene_info"
                        ]
                    })
                
                if result.get("success", False):
                    return APIResponse.success(
                        f"コマンド '{command_name}' が正常に実行されました",
                        result
                    )
                else:
                    return APIResponse.error(
                        result.get("message", f"コマンド '{command_name}' の実行に失敗しました"),
                        result
                    )
            except Exception as e:
                self.logger.error(f"コマンド実行エラー: {str(e)}")
                return APIResponse.error(f"コマンド実行エラー: {str(e)}")
        
        # オブジェクト削除エンドポイント
        @self.app.post("/delete_objects", tags=["Objects"])
        async def delete_objects(request: DeleteObjectsRequest):
            """シーン内のオブジェクトを削除する"""
            try:
                import bpy
                
                # 実行前のオブジェクト数を記録
                initial_count = len(bpy.data.objects)
                
                # メインスレッドで実行する関数
                def delete_objects_main():
                    deleted = []
                    kept = []
                    
                    # オブジェクトの選択を解除
                    bpy.ops.object.select_all(action='DESELECT')
                    
                    # 全オブジェクトをループして削除対象を選択
                    for obj in bpy.data.objects:
                        skip = False
                        
                        # カメラとライトはオプションによって除外
                        if request.keep_cameras and obj.type == 'CAMERA':
                            skip = True
                        
                        if request.keep_lights and obj.type == 'LIGHT':
                            skip = True
                        
                        if skip:
                            kept.append(obj.name)
                        else:
                            obj.select_set(True)
                            deleted.append(obj.name)
                    
                    # 選択したオブジェクトを削除
                    if deleted:
                        bpy.ops.object.delete()
                    
                    return {
                        "deleted": deleted,
                        "kept": kept
                    }
                
                # メインスレッドで実行
                result = execute_in_main_thread(delete_objects_main)
                final_count = len(bpy.data.objects)
                
                return APIResponse.success(f"{len(result['deleted'])}個のオブジェクトを削除しました", {
                    "initial_count": initial_count,
                    "final_count": final_count,
                    "deleted": result["deleted"],
                    "kept": result["kept"]
                })
                
            except Exception as e:
                logger.error(f"オブジェクト削除エラー: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Object deletion error: {str(e)}")
        
        # オブジェクト一覧エンドポイント
        @self.app.get("/api/objects", tags=["Objects"])
        async def get_objects(detailed: bool = False):
            """シーン内のオブジェクト一覧を返す"""
            if not bpy:
                return APIResponse.error("Blender environment not available")
            
            def get_objects_data():
                objects_data = []
                for obj in bpy.data.objects:
                    obj_data = {
                        "name": obj.name,
                        "type": obj.type
                    }
                    
                    if detailed:
                        obj_data.update({
                            "location": [round(v, 4) for v in obj.location],
                            "dimensions": [round(v, 4) for v in obj.dimensions]
                        })
                        
                        if obj.type == 'MESH' and obj.data:
                            obj_data.update({
                                "vertices": len(obj.data.vertices),
                                "faces": len(obj.data.polygons),
                                "materials": [mat.name for mat in obj.data.materials if mat]
                            })
                    
                    objects_data.append(obj_data)
                
                return objects_data
            
            objects = execute_in_main_thread(get_objects_data)
            
            return APIResponse.success("Objects list", {
                "count": len(objects),
                "objects": objects
            })
        
        # シーン情報エンドポイント
        @self.app.get("/api/scene", tags=["Scene"])
        async def get_scene_info():
            """現在のシーン情報を返す"""
            if not bpy:
                return APIResponse.error("Blender environment not available")
            
            def get_scene_data():
                scene = bpy.context.scene
                return {
                    "name": scene.name,
                    "objects_count": len(scene.objects),
                    "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
                    "frame_current": scene.frame_current,
                    "frame_start": scene.frame_start,
                    "frame_end": scene.frame_end
                }
            
            scene_data = execute_in_main_thread(get_scene_data)
            return APIResponse.success("Scene information", scene_data)
        
        # JSON APIエンドポイントの追加処理
        def _add_json_api_endpoints(self):
            """JSON APIエンドポイントを追加する"""
            self.logger.info("JSON APIエンドポイントの初期化開始")
            try:
                # JSON API情報エンドポイント
                self.logger.info("JSON API情報エンドポイントを登録します")
                @self.app.get("/json", tags=["JSON API"])
                async def json_api_info():
                    """JSON API情報を返す"""
                    return APIResponse.success("Blender JSON API", {
                        "version": "1.0",
                        "endpoints": [
                            {"/json/create": "オブジェクト作成"},
                            {"/json/delete": "オブジェクト削除"},
                            {"/json/transform": "オブジェクト変換"},
                            {"/json/scene": "シーン情報取得"}
                        ]
                    })
                
                # オブジェクト作成エンドポイント
                self.logger.info("オブジェクト作成エンドポイントを登録します: /json/create")
                @self.app.post("/json/create", tags=["JSON API"])
                async def create_object(request: Request):
                    """JSONデータからオブジェクトを作成する"""
                    try:
                        data = await request.json()
                        self.logger.info(f"create_primitive呼び出し: {data}")
                        
                        # importされていることを確認
                        if 'create_primitive' not in globals():
                            from .json_handlers import create_primitive as cp
                            globals()['create_primitive'] = cp
                        
                        result = create_primitive(data)
                        self.logger.info(f"create_primitive結果: {result}")
                        
                        if result.get("success", False):
                            return APIResponse.success(
                                "オブジェクトが作成されました",
                                result
                            )
                        else:
                            return APIResponse.error(
                                result.get("message", "オブジェクト作成エラー"),
                                result
                            )
                    except Exception as e:
                        self.logger.error(f"オブジェクト作成エラー: {str(e)}")
                        import traceback
                        self.logger.error(traceback.format_exc())
                        return APIResponse.error(f"オブジェクト作成エラー: {str(e)}")
                

                # オブジェクト削除エンドポイント
                @self.app.post("/json/delete", tags=["JSON API"])
                async def delete_json_objects(request: Request):
                    """JSONデータからオブジェクトを削除する"""
                    try:
                        data = await request.json()
                        result = delete_objects(data)
                        
                        if result.get("success", False):
                            return APIResponse.success(
                                "オブジェクトが削除されました",
                                result
                            )
                        else:
                            return APIResponse.error(
                                result.get("message", "オブジェクト削除エラー"),
                                result
                            )
                    except Exception as e:
                        self.logger.error(f"オブジェクト削除エラー: {str(e)}")
                        return APIResponse.error(f"オブジェクト削除エラー: {str(e)}")
                
                # オブジェクト変換エンドポイント
                @self.app.post("/json/transform", tags=["JSON API"])
                async def transform_json_object(request: Request):
                    """JSONデータからオブジェクトを変換する"""
                    try:
                        data = await request.json()
                        result = transform_object(data)
                        
                        if result.get("success", False):
                            return APIResponse.success(
                                "オブジェクトが変換されました",
                                result
                            )
                        else:
                            return APIResponse.error(
                                result.get("message", "オブジェクト変換エラー"),
                                result
                            )
                    except Exception as e:
                        self.logger.error(f"オブジェクト変換エラー: {str(e)}")
                        return APIResponse.error(f"オブジェクト変換エラー: {str(e)}")
                
                # シーン情報取得エンドポイント
                @self.app.get("/json/scene", tags=["JSON API"])
                async def get_json_scene():
                    """現在のシーン情報を返す"""
                    try:
                        result = get_scene_info()
                        
                        if result.get("success", False):
                            return APIResponse.success(
                                "シーン情報を取得しました",
                                result
                            )
                        else:
                            return APIResponse.error(
                                result.get("message", "シーン情報取得エラー"),
                                result
                            )
                    except Exception as e:
                        self.logger.error(f"シーン情報取得エラー: {str(e)}")
                        return APIResponse.error(f"シーン情報取得エラー: {str(e)}")
                        
                self.logger.info("JSON APIエンドポイントが追加されました")
            except Exception as e:
                self.logger.error(f"JSON APIエンドポイント追加エラー: {str(e)}")
                
        # GraphQL
        if GRAPHQL_AVAILABLE:
            # GraphQLのスキーマ定義は別ファイルで実装
            logger.info("GraphQLサポートが有効です")
        
        logger.info("FastAPIサーバーの初期化が完了しました")
        return True
    
    def _find_available_port(self, start_port=8000, max_attempts=10):
        """利用可能なポートを検索する"""
        current_port = start_port
        host_to_check = self.host if hasattr(self, 'host') and self.host else 'localhost'
        
        logger.info(f"利用可能なポートを検索します: 開始ポート={start_port}, ホスト={host_to_check}")
        
        # 'localhost'を使用する場合は'127.0.0.1'もチェック
        if host_to_check == 'localhost':
            hosts_to_check = ['127.0.0.1', 'localhost']
        elif host_to_check == '0.0.0.0':
            # 全てのインターフェースにバインドする場合はローカルアドレスもチェック
            hosts_to_check = ['0.0.0.0']
        else:
            hosts_to_check = [host_to_check]
        
        for _ in range(max_attempts):
            # 各ポートについて全てのホストをチェック
            port_available = True
            
            for host in hosts_to_check:
                try:
                    # ポートが利用可能か確認
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1.0)  # 1秒のタイムアウト
                    sock.bind((host, current_port))
                    sock.close()
                    logger.debug(f"ホスト {host} のポート {current_port} は利用可能です")
                except OSError as e:
                    logger.warning(f"ホスト {host} のポート {current_port} は使用中です: {str(e)}")
                    port_available = False
                    break
                except Exception as e:
                    logger.error(f"ホスト {host} のポート {current_port} の確認エラー: {str(e)}")
                    port_available = False
                    break
            
            if port_available:
                logger.info(f"利用可能なポートが見つかりました: {current_port}")
                return current_port
            else:
                # このポートは使用中なので次を試す
                logger.warning(f"ポート {current_port} は使用中です。次を試します...")
                current_port += 1
        
        # 利用可能なポートが見つからなかった
        logger.error(f"{max_attempts} 回の試行後も利用可能なポートが見つかりませんでした")
        return None
    
    def start(self, host="localhost", port=8000):
        """サーバーを起動"""
        # サーバーが既に実行中か確認
        if self.running:
            logger.warning("サーバーは既に実行中です")
            # 現在のサーバー情報を返す
            logger.info(f"現在実行中のサーバー: http://{self.host}:{self.port}")
            return True
        
        # FastAPIの依存関係確認
        try:
            import fastapi
            import uvicorn
            import pydantic
            logger.info(f"FastAPI v{fastapi.__version__}, Uvicorn v{uvicorn.__version__}, Pydantic v{pydantic.__version__} が利用可能です")
            FASTAPI_AVAILABLE = True
        except ImportError as e:
            logger.error(f"FastAPI関連ライブラリが利用できません: {str(e)}")
            logger.warning("互換モードで起動しています。機能が制限されます。")
            FASTAPI_AVAILABLE = False
            return False
        
        # アプリ初期化
        if not self.app:
            if not self.initialize():
                logger.error("サーバーの初期化に失敗しました")
                return False
        
        # ホスト設定を保存してからポート検索を行う
        self.host = host  # ホストを設定
        
        # 与えられたポートが使用可能か確認、使用中なら別のポートを自動選択
        available_port = self._find_available_port(start_port=port)
        
        if available_port is None:
            logger.error("利用可能なポートが見つかりませんでした")
            return False
        
        # ポートを設定
        self.port = available_port
        
        logger.info(f"FastAPIサーバーを起動します (host: {self.host}, port: {self.port})")
        
        # スレッド初期化状態を確保
        self.should_exit = False  # 終了フラグを追加
        
        # 現在のサーバーをリセット
        if hasattr(self, 'server_thread') and self.server_thread:
            logger.info("既存のサーバースレッドをリセットします")
            self.server_thread = None
        
        # サーバーを別スレッドで起動
        def run_server():
            try:
                # uvicorn設定を詳細にログ出力
                logger.info(f"Uvicorn設定: ホスト={self.host}, ポート={self.port}, アプリ={self.app}")
                
                config = uvicorn.Config(
                    app=self.app,
                    host=self.host,
                    port=self.port,
                    log_level="info",
                    access_log=True,  # アクセスログを有効化
                    interface="asgi3",  # 最新のインターフェースを使用
                    workers=1,  # ワーカー数
                    timeout_keep_alive=120  # 長時間の接続を許可
                )
                
                server = uvicorn.Server(config)
                logger.info("サーバーインスタンスの作成に成功しました")
                self.uvicorn_server = server  # インスタンスを保存
                
                # サーバーの状態を実行中に設定
                self.running = True
                logger.info(f"FastAPIサーバーを開始しました: http://{self.host}:{self.port}")
                
                # サーバー実行
                server.run()
                logger.info("サーバーが正常終了しました")
            except Exception as e:
                # 全ての例外をキャッチしてログ出力
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Uvicornサーバーの実行中にエラーが発生しました: {str(e)}")
                logger.debug(f"エラー詳細: {error_trace}")
                self.running = False
            finally:
                # 最終的にサーバーの実行状態をリセット
                logger.info("サーバースレッドが終了しました")
                self.running = False
        
        try:
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            # サーバーが起動するまで少し待機
            time.sleep(0.5)
            
            return True
        except Exception as e:
            logger.error(f"サーバースレッド開始中にエラーが発生しました: {str(e)}")
            self.running = False
            return False
    
    def stop(self):
        """サーバーを停止"""
        if not self.running:
            logger.warning("サーバーは実行されていません")
            return False
        
        try:
            # uvicornサーバーの停止
            if hasattr(self, 'uvicorn_server'):
                self.uvicorn_server.should_exit = True
                logger.info("uvicornサーバーに終了シグナルを送信しました")
            
            # 状態フラグを更新
            self.running = False
            self.should_exit = True
            
            # 短時間待機（uvicornの終了を待つ）
            time.sleep(1.0)
            
            logger.info("FastAPIサーバーを停止しました")
            return True
        except Exception as e:
            logger.error(f"サーバー停止中にエラーが発生しました: {str(e)}")
            # 強制的に状態を更新
            self.running = False
            return False
    
    def register_command(self, command_class):
        """コマンドを登録"""
        self.command_registry.register_command(command_class)

# シングルトンインスタンス
_instance = None

def get_instance():
    """MCPFastAPIServerのシングルトンインスタンスを取得"""
    global _instance
    if _instance is None:
        _instance = MCPFastAPIServer()
    return _instance
