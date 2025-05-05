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
            # メインスレッドでの実行をスケジュール
            result = []
            def exec_func():
                try:
                    with blender_lock:
                        result.append(func(*args, **kwargs))
                except Exception as e:
                    logger.error(f"エラー in {func.__name__}: {str(e)}")
                    result.append({"error": str(e)})
            
            bpy.app.timers.register(exec_func)
            
            # 結果が返るまで待機（最大5秒）
            timeout = 5.0
            start_time = time.time()
            while not result and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if not result:
                return {"error": f"Timeout waiting for {func.__name__} to execute"}
            return result[0]
    
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
def execute_command(command: str) -> Dict[str, Any]:
    """
    Blender内でPythonコマンドを実行
    
    Args:
        command: 実行するPythonコマンド文字列
        
    Returns:
        Dict: 実行結果
    """
    try:
        # 実行結果を格納する辞書
        locals_dict = {}
        
        # コマンドをグローバルコンテキストで実行
        exec(command, {"bpy": bpy}, locals_dict)
        
        # 実行結果の取得
        if "result" in locals_dict:
            result = locals_dict["result"]
            if isinstance(result, (dict, list, str, int, float, bool, type(None))):
                return {"success": True, "result": result}
            else:
                return {"success": True, "result": str(result)}
        else:
            return {"success": True, "message": "Command executed successfully"}
    except Exception as e:
        logger.error(f"コマンド実行エラー: {str(e)}")
        return {"success": False, "error": str(e)}

@run_in_main_thread
def execute_mcp_command(command_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCPコマンドを実行
    
    Args:
        command_data: コマンドデータ（JSON）
        
    Returns:
        Dict: 実行結果
    """
    try:
        # コマンドハンドラーモジュールをインポート
        from . import command_handler
        
        # コマンドを実行
        result = command_handler.handle_command(command_data)
        return result
    except Exception as e:
        logger.error(f"MCPコマンド実行エラー: {str(e)}")
        return {
            "status": "error",
            "message": f"Command execution failed: {str(e)}",
            "details": {
                "exception": str(e)
            }
        }

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
            if "command" not in params:
                return {"error": "Missing 'command' parameter"}
            
            command = params["command"]
            return execute_command(command)
        
        elif endpoint == "command":
            if not params:
                return {"error": "Missing command data"}
            
            return execute_mcp_command(params)
        
        elif endpoint == "analyze_scene":
            # シーン分析コマンドを直接実行
            from . import meta_commands
            return meta_commands.handle_analyze_scene_command(params)
        
        elif endpoint == "analyze_object":
            # オブジェクト分析コマンドを直接実行
            from . import meta_commands
            return meta_commands.handle_analyze_object_command(params)
        
        else:
            return {"error": f"Unknown endpoint: {endpoint}"}
    
    except Exception as e:
        logger.error(f"APIハンドラーエラー: {str(e)}")
        return {"error": str(e)}
