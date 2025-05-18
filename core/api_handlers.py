"""
Unified MCP API Handlers
Blenderからの情報取得とコマンド実行のためのユーティリティ関数
"""

import bpy
import json
import logging
import time
import os
import threading
from typing import Dict, List, Any, Optional, Union, Tuple

# ロギング設定
logger = logging.getLogger(__name__)

# スレッドセーフなBlender操作のためのロック
blender_lock = threading.RLock()

def run_in_main_thread(func):
    """
    デコレータ: 関数をBlenderのメインスレッドで実行する
    """
    def wrapper(*args, **kwargs):
        if threading.current_thread() is threading.main_thread():
            # すでにメインスレッドの場合は直接実行
            return func(*args, **kwargs)
        else:
            # イベント駆動アプローチ（タイムアウト付き）
            result_container = []
            event = threading.Event()
            
            def exec_func():
                try:
                    with blender_lock:
                        result_container.append(func(*args, **kwargs))
                except Exception as e:
                    logger.error(f"エラー in {func.__name__}: {str(e)}")
                    result_container.append({"error": str(e)})
                finally:
                    event.set()  # 実行完了を通知
            
            bpy.app.timers.register(exec_func)
            
            # イベント待機（タイムアウト付き）
            timeout = 5.0
            if not event.wait(timeout=timeout):
                return {"error": f"Timeout waiting for {func.__name__} to execute"}
            
            return result_container[0]
    
    return wrapper

@run_in_main_thread
def get_scene_info() -> Dict[str, Any]:
    """
    現在のBlenderシーンの基本情報を取得
    
    Returns:
        Dict: シーン情報（名前、オブジェクト数、フレーム情報など）
    """
    scene = bpy.context.scene
    
    return {
        "name": scene.name,
        "frame_current": scene.frame_current,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "fps": scene.render.fps,
        "objects_count": len(scene.objects),
        "collections_count": len(bpy.data.collections),
        "materials_count": len(bpy.data.materials),
        "render_engine": scene.render.engine,
        "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
        "selected_objects": [obj.name for obj in bpy.context.selected_objects]
    }

@run_in_main_thread
def get_objects_list(collection_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    シーン内のオブジェクトリストを取得
    
    Args:
        collection_name: 指定した場合、そのコレクション内のオブジェクトのみ取得
        
    Returns:
        List[Dict]: オブジェクト情報のリスト
    """
    result = []
    
    objects_to_process = []
    if collection_name:
        # 指定されたコレクションが存在するか確認
        if collection_name in bpy.data.collections:
            objects_to_process = bpy.data.collections[collection_name].objects
        else:
            return {"error": f"Collection '{collection_name}' not found"}
    else:
        objects_to_process = bpy.context.scene.objects
    
    for obj in objects_to_process:
        obj_data = {
            "name": obj.name,
            "type": obj.type,
            "location": [round(v, 4) for v in obj.location],
            "rotation": [round(v, 4) for v in obj.rotation_euler],
            "scale": [round(v, 4) for v in obj.scale],
            "dimensions": [round(v, 4) for v in obj.dimensions],
            "visible": obj.visible_get(),
            "selected": obj.select_get(),
            "parent": obj.parent.name if obj.parent else None,
            "material_slots": [slot.material.name if slot.material else None for slot in obj.material_slots]
        }
        
        # オブジェクトタイプに応じた追加情報
        if obj.type == 'MESH':
            obj_data.update({
                "vertices_count": len(obj.data.vertices),
                "edges_count": len(obj.data.edges),
                "faces_count": len(obj.data.polygons)
            })
        elif obj.type == 'CAMERA':
            obj_data.update({
                "lens": obj.data.lens,
                "sensor_width": obj.data.sensor_width
            })
        elif obj.type == 'LIGHT':
            obj_data.update({
                "light_type": obj.data.type,
                "energy": obj.data.energy,
                "color": [round(c, 4) for c in obj.data.color]
            })
        
        result.append(obj_data)
    
    return result

@run_in_main_thread
def get_collections_list() -> List[Dict[str, Any]]:
    """
    コレクション一覧を取得
    
    Returns:
        List[Dict]: コレクション情報のリスト
    """
    result = []
    
    for collection in bpy.data.collections:
        coll_data = {
            "name": collection.name,
            "objects_count": len(collection.objects),
            "objects": [obj.name for obj in collection.objects],
            "children": [child.name for child in collection.children]
        }
        result.append(coll_data)
    
    return result

@run_in_main_thread
def get_materials_list() -> List[Dict[str, Any]]:
    """
    マテリアル一覧を取得
    
    Returns:
        List[Dict]: マテリアル情報のリスト
    """
    result = []
    
    for mat in bpy.data.materials:
        mat_data = {
            "name": mat.name,
            "use_nodes": mat.use_nodes,
            "is_grease_pencil": hasattr(mat, "is_grease_pencil") and mat.is_grease_pencil,
            "users": mat.users
        }
        
        # ノードベースのマテリアルの場合の基本情報
        if mat.use_nodes and mat.node_tree:
            nodes_info = []
            for node in mat.node_tree.nodes:
                nodes_info.append({
                    "name": node.name,
                    "type": node.type,
                    "label": node.label
                })
            mat_data["nodes_count"] = len(mat.node_tree.nodes)
            mat_data["nodes"] = nodes_info
        
        # アクティブなノードを取得
        if mat.use_nodes and mat.node_tree and mat.node_tree.nodes.active:
            mat_data["active_node"] = mat.node_tree.nodes.active.name
        
        result.append(mat_data)
    
    return result

@run_in_main_thread
def execute_command(command_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    安全なコマンド実行（exec()の代わりに安全なコマンドパターンを使用）
    
    Args:
        command_data: コマンドデータ
            {
                "command": "コマンド名",
                "params": {パラメータ}
            }
            または古い形式の文字列
            
    Returns:
        Dict: 実行結果
    """
    # 文字列のコマンドをハンドリング（後方互換性）
    if isinstance(command_data, str):
        logger.warning("文字列形式のコマンドは非推奨です。JSONオブジェクトを使用してください。")
        try:
            # 文字列がJSON形式か確認
            if command_data.strip().startswith('{'):
                command_data = json.loads(command_data)
            else:
                # 古い形式の場合は新しい形式に変換
                return {
                    "success": False,
                    "error": "String commands are no longer supported. Use command object format instead.",
                    "example": {
                        "command": "select_object", 
                        "params": {"object_name": "Cube"}
                    }
                }
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid command format"}
    
    # 安全なコマンド実行システムを使用
    try:
        # コマンドハンドラーをインポート
        from .commands.secure_command_handler import execute_safe_command
        
        # 安全なコマンド実行
        return execute_safe_command(command_data)
    except ImportError:
        logger.error("secure_command_handler モジュールが見つかりません")
        return {
            "success": False, 
            "error": "Command execution system is not available"
        }
    except Exception as e:
        logger.error(f"コマンド実行エラー: {str(e)}")
        return {"success": False, "error": str(e)}

@run_in_main_thread
def execute_mcp_command(command_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCPコマンドを実行（execute_commandへのブリッジ）
    
    Args:
        command_data: コマンドデータ（JSON）
        
    Returns:
        Dict: 実行結果
    """
    return execute_command(command_data)

def api_handler(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    APIエンドポイントに応じたハンドラー関数の呼び出し

    Args:
        endpoint: APIエンドポイント名
        params: リクエストパラメータ

    Returns:
        Dict: 処理結果
    """
    if params is None:
        params = {}

    try:
        # エンドポイントに応じたハンドラーを呼び出す
        if endpoint == "scene":
            return {"status": "success", "data": get_scene_info()}

        elif endpoint == "objects":
            collection_name = params.get("collection", None)
            return {"status": "success", "data": get_objects_list(collection_name)}

        elif endpoint == "collections":
            return {"status": "success", "data": get_collections_list()}

        elif endpoint == "materials":
            return {"status": "success", "data": get_materials_list()}

        elif endpoint == "execute":
            # 新しいコマンド形式を使用
            if "command" not in params:
                return {"status": "error", "message": "Missing 'command' parameter"}

            command = params["command"]
            return execute_command(command)

        elif endpoint == "command":
            if not params:
                return {"status": "error", "message": "Missing command data"}

            return execute_mcp_command(params)

        elif endpoint == "commands":
            # 利用可能なコマンド一覧を返す
            try:
                from .commands.secure_command_handler import get_available_commands
                return {
                    "status": "success",
                    "data": {
                        "available_commands": get_available_commands()
                    }
                }
            except ImportError:
                return {
                    "status": "error",
                    "message": "Command listing is not available"
                }

        elif endpoint == "analyze_scene":
            # シーン分析コマンドを安全なコマンドに変換
            return execute_command({
                "command": "analyze_scene",
                "params": params
            })

        elif endpoint == "analyze_object":
            # オブジェクト分析コマンドを安全なコマンドに変換
            return execute_command({
                "command": "analyze_object",
                "params": params
            })

        elif endpoint == "supported_addons":
            # サポートされているアドオンの一覧を返す
            # addons_bridge/__init__.pyからSUPPORTED_ADDONSを取得
            try:
                from ..addons_bridge import SUPPORTED_ADDONS

                # 各アドオンの状態を確認
                addons_status = {}
                for addon_name in SUPPORTED_ADDONS:
                    is_enabled = addon_name in bpy.context.preferences.addons
                    addons_status[addon_name] = {
                        "name": addon_name,
                        "enabled": is_enabled,
                        "description": f"Blender Extensions Marketplace対応アドオン: {addon_name}"
                    }

                return {
                    "status": "success",
                    "data": {
                        "supported_addons": SUPPORTED_ADDONS,
                        "addons_status": addons_status,
                        "extensions_marketplace_url": "https://extensions.blender.org/"
                    }
                }
            except ImportError:
                return {
                    "status": "error",
                    "message": "サポートされているアドオン情報を取得できません"
                }

        elif endpoint == "addon_info":
            # 特定のアドオン情報を取得
            try:
                from .commands.addon_commands import get_addon_info

                addon_name = params.get("addon_name")
                if not addon_name:
                    return {
                        "status": "error",
                        "message": "アドオン名を指定してください"
                    }

                return get_addon_info(addon_name)

            except ImportError:
                return {
                    "status": "error",
                    "message": "アドオン情報を取得できません"
                }

        elif endpoint == "all_addons":
            # すべてのアドオン情報を取得
            try:
                from .commands.addon_commands import get_all_addons
                return get_all_addons()
            except ImportError:
                return {
                    "status": "error",
                    "message": "アドオン情報を取得できません"
                }

        elif endpoint == "enable_addon":
            # アドオンを有効化
            try:
                from .commands.addon_commands import enable_addon

                addon_name = params.get("addon_name")
                if not addon_name:
                    return {
                        "status": "error",
                        "message": "アドオン名を指定してください"
                    }

                return enable_addon(addon_name)

            except ImportError:
                return {
                    "status": "error",
                    "message": "アドオン操作機能を使用できません"
                }

        elif endpoint == "disable_addon":
            # アドオンを無効化
            try:
                from .commands.addon_commands import disable_addon

                addon_name = params.get("addon_name")
                if not addon_name:
                    return {
                        "status": "error",
                        "message": "アドオン名を指定してください"
                    }

                return disable_addon(addon_name)

            except ImportError:
                return {
                    "status": "error",
                    "message": "アドオン操作機能を使用できません"
                }

        elif endpoint == "install_addon":
            # アドオンをインストール
            try:
                from .commands.addon_commands import install_addon_from_file

                file_path = params.get("file_path")
                if not file_path:
                    return {
                        "status": "error",
                        "message": "アドオンファイルパスを指定してください"
                    }

                overwrite = params.get("overwrite", True)
                return install_addon_from_file(file_path, overwrite)

            except ImportError:
                return {
                    "status": "error",
                    "message": "アドオン操作機能を使用できません"
                }

        elif endpoint == "install_addon_from_url":
            # URLからアドオンをインストール
            try:
                from .commands.addon_commands import install_addon_from_url

                url = params.get("url")
                if not url:
                    return {
                        "status": "error",
                        "message": "アドオンURLを指定してください"
                    }

                overwrite = params.get("overwrite", True)
                return install_addon_from_url(url, overwrite)

            except ImportError:
                return {
                    "status": "error",
                    "message": "アドオン操作機能を使用できません"
                }

        elif endpoint == "update_addon":
            # アドオンを更新
            try:
                from .commands.addon_commands import update_addon

                addon_name = params.get("addon_name")
                if not addon_name:
                    return {
                        "status": "error",
                        "message": "アドオン名を指定してください"
                    }

                return update_addon(addon_name)

            except ImportError:
                return {
                    "status": "error",
                    "message": "アドオン操作機能を使用できません"
                }

        elif endpoint == "check_addon_updates":
            # アドオンの更新を確認
            try:
                from .commands.addon_commands import check_addon_updates
                return check_addon_updates()
            except ImportError:
                return {
                    "status": "error",
                    "message": "アドオン操作機能を使用できません"
                }

        else:
            return {"status": "error", "message": f"Unknown endpoint: {endpoint}"}

    except Exception as e:
        logger.error(f"APIハンドラーエラー: {str(e)}")
        return {"status": "error", "message": str(e)}