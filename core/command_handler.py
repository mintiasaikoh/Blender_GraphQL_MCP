"""
Command Handler Module - MCPコマンドインターフェース実装
"""

import bpy
import json
import logging
import importlib
from typing import Dict, List, Any, Optional, Union, Tuple

# ロギング設定
logger = logging.getLogger(__name__)

# モジュールの動的インポート用の辞書
_module_cache = {}

# 安全なコマンドシステムを使用するかどうか
USE_SECURE_COMMAND_SYSTEM = True

def get_module(module_name: str):
    """
    モジュールを動的にインポートまたはキャッシュから取得
    
    Args:
        module_name: インポートするモジュール名
        
    Returns:
        モジュールオブジェクト
    """
    if module_name in _module_cache:
        # キャッシュから取得（既にインポート済み）
        return _module_cache[module_name]
    
    try:
        # モジュールを動的にインポート
        module = importlib.import_module(module_name)
        _module_cache[module_name] = module
        return module
    except ImportError as e:
        logger.error(f"Failed to import module {module_name}: {str(e)}")
        return None

# 安全なコマンドシステムのインポートを試みる
try:
    from .commands.secure_command_handler import execute_safe_command
    SECURE_COMMAND_SYSTEM_LOADED = True
    logger.info("安全なコマンドシステムを読み込みました")
except ImportError as e:
    SECURE_COMMAND_SYSTEM_LOADED = False
    logger.warning(f"安全なコマンドシステムの読み込みに失敗しました: {str(e)}")

# 安全なコード実行システムのインポートを試みる
try:
    from .secure_code_executor import handle_execute_code_command_secure
    SECURE_CODE_EXECUTOR_LOADED = True
    logger.info("安全なコード実行システムを読み込みました")
except ImportError as e:
    SECURE_CODE_EXECUTOR_LOADED = False
    logger.warning(f"安全なコード実行システムの読み込みに失敗しました: {str(e)}")

def handle_command(command_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    コマンドを処理し、適切なハンドラーに委譲
    
    Args:
        command_data: コマンドデータ
        
    Returns:
        Dict: コマンド実行結果
    """
    if not isinstance(command_data, dict):
        return {
            "status": "error",
            "message": "Invalid command format: command data must be a JSON object",
            "details": {
                "received": str(type(command_data))
            }
        }
    
    # コマンドタイプの取得
    command_type = command_data.get("command")
    
    if not command_type:
        return {
            "status": "error",
            "message": "Missing 'command' field in request",
            "details": {
                "required_fields": ["command"]
            }
        }
    
    # execute_code コマンドの場合は安全なコード実行を使用
    if command_type == "execute_code" and SECURE_CODE_EXECUTOR_LOADED:
        try:
            # 安全なコード実行
            result = handle_execute_code_command_secure(command_data)
            
            # 結果形式の変換（後方互換性のため）
            if "success" in result:
                # 新形式から旧形式へ変換
                status = "success" if result["success"] else "error"
                if not result["success"] and "error" in result:
                    message = result["error"]
                else:
                    message = "Code executed successfully"
                
                # 結果を旧形式に合わせる
                converted_result = {
                    "status": status,
                    "message": message
                }
                
                # 詳細情報があれば追加
                if "details" in result:
                    converted_result["details"] = result["details"]
                
                return converted_result
            
            return result
        except Exception as e:
            logger.error(f"安全なコード実行中にエラーが発生しました: {str(e)}")
            # エラーが発生した場合はレガシーハンドラーにフォールバック
            logger.info("レガシーのコード実行ハンドラーにフォールバックします")
    
    # 安全なコマンドシステムを使用する場合
    if USE_SECURE_COMMAND_SYSTEM and SECURE_COMMAND_SYSTEM_LOADED:
        # 新しい形式 (command + params) に変換
        if "params" not in command_data:
            # 基本パラメータをコピー
            params = command_data.copy()
            # コマンド名は削除
            if "command" in params:
                del params["command"]
            # 新しい形式にする
            secure_command_data = {
                "command": command_type,
                "params": params
            }
        else:
            # すでに新しい形式の場合はそのまま使用
            secure_command_data = command_data
        
        # 安全なコマンド実行を試みる
        try:
            result = execute_safe_command(secure_command_data)
            
            # 結果形式の変換（後方互換性のため）
            if "success" in result:
                # 新形式から旧形式へ変換
                status = "success" if result["success"] else "error"
                if not result["success"] and "error" in result:
                    message = result["error"]
                else:
                    message = f"Command {command_type} executed"
                
                # 結果を旧形式に合わせる
                converted_result = {
                    "status": status,
                    "message": message
                }
                
                # 詳細情報があれば追加
                if "result" in result:
                    converted_result["details"] = result["result"]
                elif "details" in result:
                    converted_result["details"] = result["details"]
                
                return converted_result
            
            return result
            
        except Exception as e:
            logger.error(f"安全なコマンド実行中にエラーが発生しました ({command_type}): {str(e)}")
            # エラーが発生した場合はレガシーハンドラーにフォールバック
            logger.info(f"レガシーハンドラーにフォールバックします: {command_type}")
    
    # レガシーコマンド実行（フォールバック）
    # コマンドタイプに基づいてハンドラーを選択
    handlers = {
        # 基本操作
        "create": handle_create_command,
        "modify": handle_modify_command,
        "delete": handle_delete_command,
        "transform": handle_transform_command,
        "select": handle_select_command,
        
        # 高レベル操作
        "boolean": handle_boolean_command,
        "array": handle_array_command,
        "mirror": handle_mirror_command,
        "extrude": handle_extrude_command,
        "subdivide": handle_subdivide_command,
        
        # 分析コマンド
        "analyze_scene": handle_analyze_scene_command,
        "analyze_object": handle_analyze_object_command,
        "compare": handle_compare_command,
        
        # メタコマンド
        "batch": handle_batch_command,
        "undo": handle_undo_command,
        "redo": handle_redo_command,
        "save": handle_save_command,
        "execute_code": handle_execute_code_command
    }
    
    # ハンドラーの取得
    handler = handlers.get(command_type.lower())
    
    if not handler:
        return {
            "status": "error",
            "message": f"Unknown command: {command_type}",
            "details": {
                "available_commands": list(handlers.keys())
            }
        }
    
    try:
        # ハンドラーを実行
        result = handler(command_data)
        return result
    except Exception as e:
        logger.error(f"Error executing command {command_type}: {str(e)}")
        return {
            "status": "error",
            "message": f"Command execution failed: {str(e)}",
            "details": {
                "command": command_type,
                "exception": str(e)
            }
        }

def handle_create_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクト作成コマンドを処理
    
    Args:
        data: コマンドデータ
        
    Returns:
        Dict: 実行結果
    """
    # 必須パラメータの確認
    object_type = data.get("type")
    name = data.get("name")
    
    if not object_type:
        return {
            "status": "error",
            "message": "Missing 'type' parameter for create command",
            "details": {
                "required_parameters": ["type"]
            }
        }
    
    # オブジェクトタイプに基づいて作成関数を選択
    creators = {
        "cube": create_cube,
        "sphere": create_sphere,
        "cylinder": create_cylinder,
        "cone": create_cone,
        "plane": create_plane,
        "torus": create_torus,
        "empty": create_empty,
        "light": create_light,
        "camera": create_camera,
        "text": create_text
    }
    
    creator = creators.get(object_type.lower())
    
    if not creator:
        return {
            "status": "error",
            "message": f"Unknown object type: {object_type}",
            "details": {
                "available_types": list(creators.keys())
            }
        }
    
    try:
        # 作成関数を実行
        result = creator(data)
        return result
    except Exception as e:
        logger.error(f"Error creating object of type {object_type}: {str(e)}")
        return {
            "status": "error",
            "message": f"Object creation failed: {str(e)}",
            "details": {
                "type": object_type,
                "exception": str(e)
            }
        }

def create_cube(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    立方体を作成
    
    Args:
        data: パラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # パラメータの取得
        name = data.get("name", "Cube")
        size = data.get("size", 2.0)
        location = data.get("location", [0, 0, 0])
        
        # Blender APIでキューブを作成
        bpy.ops.mesh.primitive_cube_add(size=size, location=location)
        obj = bpy.context.active_object
        obj.name = name
        
        # 追加のパラメータ適用
        apply_common_parameters(obj, data)
        
        return {
            "status": "success",
            "message": f"Created cube: {name}",
            "details": {
                "name": obj.name,
                "type": "cube",
                "location": [round(v, 6) for v in obj.location],
                "dimensions": [round(v, 6) for v in obj.dimensions]
            }
        }
    except Exception as e:
        logger.error(f"Failed to create cube: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create cube: {str(e)}"
        }

def create_sphere(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    球を作成
    
    Args:
        data: パラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # パラメータの取得
        name = data.get("name", "Sphere")
        radius = data.get("radius", 1.0)
        segments = data.get("segments", 32)
        rings = data.get("rings", 16)
        location = data.get("location", [0, 0, 0])
        
        # Blender APIで球を作成
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=radius, 
            segments=segments, 
            ring_count=rings, 
            location=location
        )
        obj = bpy.context.active_object
        obj.name = name
        
        # 追加のパラメータ適用
        apply_common_parameters(obj, data)
        
        return {
            "status": "success",
            "message": f"Created sphere: {name}",
            "details": {
                "name": obj.name,
                "type": "sphere",
                "location": [round(v, 6) for v in obj.location],
                "dimensions": [round(v, 6) for v in obj.dimensions]
            }
        }
    except Exception as e:
        logger.error(f"Failed to create sphere: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create sphere: {str(e)}"
        }

def create_cylinder(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    円柱を作成
    
    Args:
        data: パラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # パラメータの取得
        name = data.get("name", "Cylinder")
        radius = data.get("radius", 1.0)
        depth = data.get("depth", 2.0)
        vertices = data.get("vertices", 32)
        location = data.get("location", [0, 0, 0])
        
        # Blender APIで円柱を作成
        bpy.ops.mesh.primitive_cylinder_add(
            radius=radius, 
            depth=depth, 
            vertices=vertices, 
            location=location
        )
        obj = bpy.context.active_object
        obj.name = name
        
        # 追加のパラメータ適用
        apply_common_parameters(obj, data)
        
        return {
            "status": "success",
            "message": f"Created cylinder: {name}",
            "details": {
                "name": obj.name,
                "type": "cylinder",
                "location": [round(v, 6) for v in obj.location],
                "dimensions": [round(v, 6) for v in obj.dimensions]
            }
        }
    except Exception as e:
        logger.error(f"Failed to create cylinder: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create cylinder: {str(e)}"
        }

def create_cone(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    円錐を作成
    
    Args:
        data: パラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # パラメータの取得
        name = data.get("name", "Cone")
        radius1 = data.get("radius1", 1.0)  # 底面の半径
        radius2 = data.get("radius2", 0.0)  # 上面の半径
        depth = data.get("depth", 2.0)
        vertices = data.get("vertices", 32)
        location = data.get("location", [0, 0, 0])
        
        # Blender APIで円錐を作成
        bpy.ops.mesh.primitive_cone_add(
            radius1=radius1,
            radius2=radius2,
            depth=depth, 
            vertices=vertices, 
            location=location
        )
        obj = bpy.context.active_object
        obj.name = name
        
        # 追加のパラメータ適用
        apply_common_parameters(obj, data)
        
        return {
            "status": "success",
            "message": f"Created cone: {name}",
            "details": {
                "name": obj.name,
                "type": "cone",
                "location": [round(v, 6) for v in obj.location],
                "dimensions": [round(v, 6) for v in obj.dimensions]
            }
        }
    except Exception as e:
        logger.error(f"Failed to create cone: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create cone: {str(e)}"
        }

def create_plane(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    平面を作成
    
    Args:
        data: パラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # パラメータの取得
        name = data.get("name", "Plane")
        size = data.get("size", 2.0)
        location = data.get("location", [0, 0, 0])
        
        # Blender APIで平面を作成
        bpy.ops.mesh.primitive_plane_add(size=size, location=location)
        obj = bpy.context.active_object
        obj.name = name
        
        # 追加のパラメータ適用
        apply_common_parameters(obj, data)
        
        return {
            "status": "success",
            "message": f"Created plane: {name}",
            "details": {
                "name": obj.name,
                "type": "plane",
                "location": [round(v, 6) for v in obj.location],
                "dimensions": [round(v, 6) for v in obj.dimensions]
            }
        }
    except Exception as e:
        logger.error(f"Failed to create plane: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create plane: {str(e)}"
        }

def create_torus(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    トーラスを作成
    
    Args:
        data: パラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # パラメータの取得
        name = data.get("name", "Torus")
        major_radius = data.get("major_radius", 1.0)
        minor_radius = data.get("minor_radius", 0.25)
        major_segments = data.get("major_segments", 48)
        minor_segments = data.get("minor_segments", 12)
        location = data.get("location", [0, 0, 0])
        
        # Blender APIでトーラスを作成
        bpy.ops.mesh.primitive_torus_add(
            major_radius=major_radius,
            minor_radius=minor_radius,
            major_segments=major_segments,
            minor_segments=minor_segments,
            location=location
        )
        obj = bpy.context.active_object
        obj.name = name
        
        # 追加のパラメータ適用
        apply_common_parameters(obj, data)
        
        return {
            "status": "success",
            "message": f"Created torus: {name}",
            "details": {
                "name": obj.name,
                "type": "torus",
                "location": [round(v, 6) for v in obj.location],
                "dimensions": [round(v, 6) for v in obj.dimensions]
            }
        }
    except Exception as e:
        logger.error(f"Failed to create torus: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create torus: {str(e)}"
        }

def create_empty(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    エンプティオブジェクトを作成
    
    Args:
        data: パラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # パラメータの取得
        name = data.get("name", "Empty")
        empty_type = data.get("empty_type", "PLAIN_AXES")
        location = data.get("location", [0, 0, 0])
        
        # Blender APIでエンプティを作成
        bpy.ops.object.empty_add(type=empty_type, location=location)
        obj = bpy.context.active_object
        obj.name = name
        
        # 追加のパラメータ適用
        if "scale" in data:
            obj.empty_display_size = data["scale"]
        
        apply_common_parameters(obj, data)
        
        return {
            "status": "success",
            "message": f"Created empty: {name}",
            "details": {
                "name": obj.name,
                "type": "empty",
                "empty_type": empty_type,
                "location": [round(v, 6) for v in obj.location]
            }
        }
    except Exception as e:
        logger.error(f"Failed to create empty: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create empty: {str(e)}"
        }

def create_light(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ライトを作成
    
    Args:
        data: パラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # パラメータの取得
        name = data.get("name", "Light")
        light_type = data.get("light_type", "POINT")
        location = data.get("location", [0, 0, 0])
        energy = data.get("energy", 1000.0)
        color = data.get("color", [1.0, 1.0, 1.0])
        
        # Blender APIでライトを作成
        bpy.ops.object.light_add(type=light_type, location=location)
        obj = bpy.context.active_object
        obj.name = name
        
        # ライト固有のパラメータを設定
        light = obj.data
        light.energy = energy
        light.color = color
        
        # スポットライトの場合は追加パラメータ
        if light_type == "SPOT":
            if "spot_size" in data:
                light.spot_size = data["spot_size"]
            if "spot_blend" in data:
                light.spot_blend = data["spot_blend"]
        
        # エリアライトの場合は追加パラメータ
        if light_type == "AREA":
            if "size" in data:
                light.size = data["size"]
            if "size_y" in data:
                light.size_y = data["size_y"]
        
        # 太陽光の場合は追加パラメータ
        if light_type == "SUN":
            if "angle" in data:
                light.angle = data["angle"]
        
        # 追加のパラメータ適用
        apply_common_parameters(obj, data)
        
        return {
            "status": "success",
            "message": f"Created light: {name}",
            "details": {
                "name": obj.name,
                "type": "light",
                "light_type": light_type,
                "location": [round(v, 6) for v in obj.location],
                "energy": energy,
                "color": color
            }
        }
    except Exception as e:
        logger.error(f"Failed to create light: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create light: {str(e)}"
        }

def create_camera(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    カメラを作成
    
    Args:
        data: パラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # パラメータの取得
        name = data.get("name", "Camera")
        location = data.get("location", [0, 0, 0])
        rotation = data.get("rotation", [0, 0, 0])
        lens = data.get("lens", 50.0)
        
        # Blender APIでカメラを作成
        bpy.ops.object.camera_add(location=location, rotation=rotation)
        obj = bpy.context.active_object
        obj.name = name
        
        # カメラ固有のパラメータを設定
        camera = obj.data
        camera.lens = lens
        
        if "sensor_width" in data:
            camera.sensor_width = data["sensor_width"]
        if "sensor_height" in data:
            camera.sensor_height = data["sensor_height"]
        
        # 追加のパラメータ適用
        apply_common_parameters(obj, data)
        
        return {
            "status": "success",
            "message": f"Created camera: {name}",
            "details": {
                "name": obj.name,
                "type": "camera",
                "location": [round(v, 6) for v in obj.location],
                "rotation": [round(v, 6) for v in obj.rotation_euler],
                "lens": lens
            }
        }
    except Exception as e:
        logger.error(f"Failed to create camera: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create camera: {str(e)}"
        }

def create_text(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    3Dテキストを作成
    
    Args:
        data: パラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # パラメータの取得
        name = data.get("name", "Text")
        text = data.get("text", "Text")
        location = data.get("location", [0, 0, 0])
        size = data.get("size", 1.0)
        
        # Blender APIでテキストを作成
        bpy.ops.object.text_add(location=location)
        obj = bpy.context.active_object
        obj.name = name
        
        # テキスト固有のパラメータを設定
        text_data = obj.data
        text_data.body = text
        
        # サイズを調整
        obj.scale = [size, size, size]
        
        # 追加のパラメータ適用
        apply_common_parameters(obj, data)
        
        return {
            "status": "success",
            "message": f"Created text: {name}",
            "details": {
                "name": obj.name,
                "type": "text",
                "body": text,
                "location": [round(v, 6) for v in obj.location],
                "scale": [round(v, 6) for v in obj.scale]
            }
        }
    except Exception as e:
        logger.error(f"Failed to create text: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create text: {str(e)}"
        }

def apply_common_parameters(obj: bpy.types.Object, data: Dict[str, Any]) -> None:
    """
    共通のオブジェクトパラメータを適用
    
    Args:
        obj: 対象オブジェクト
        data: パラメータデータ
    """
    # 回転
    if "rotation" in data:
        rotation = data["rotation"]
        if len(rotation) >= 3:
            obj.rotation_euler = rotation
    
    # スケール
    if "scale" in data:
        scale = data["scale"]
        if isinstance(scale, (int, float)):
            obj.scale = [scale, scale, scale]
        elif len(scale) >= 3:
            obj.scale = scale
    
    # 材質
    if "material" in data:
        material_name = data["material"]
        material = bpy.data.materials.get(material_name)
        
        if not material:
            # 材質が存在しない場合は新規作成
            material = bpy.data.materials.new(name=material_name)
            
            # 材質の色を設定
            if "color" in data:
                color = data["color"]
                if len(color) >= 3:
                    material.diffuse_color = color + [1.0] if len(color) == 3 else color
        
        # オブジェクトに材質を割り当て
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
    
    # コレクションへの追加
    if "collection" in data:
        collection_name = data["collection"]
        collection = bpy.data.collections.get(collection_name)
        
        if collection:
            # 現在のコレクションから削除
            for coll in bpy.data.collections:
                if obj.name in coll.objects:
                    coll.objects.unlink(obj)
            
            # 指定されたコレクションに追加
            collection.objects.link(obj)
    
    # 親オブジェクトの設定
    if "parent" in data:
        parent_name = data["parent"]
        parent = bpy.data.objects.get(parent_name)
        
        if parent:
            obj.parent = parent

# その他の必要なコマンドハンドラー関数はここに実装
# 一部の関数はモジュール分割のため別ファイルに分ける

# サーバーへの関数登録
def register_commands_to_server():
    """
    コマンドハンドラー関数をHTTPサーバーに登録
    """
    try:
        # パッケージ情報を取得
        import os
        import importlib
        import sys
        
        # 現在のモジュールのパスからパッケージ名を取得
        current_dir = os.path.dirname(os.path.abspath(__file__))
        addon_dir = os.path.dirname(current_dir)
        package_name = os.path.basename(addon_dir)
        
        # HTTPサーバーモジュールのインポート
        http_server_module = importlib.import_module(f'{package_name}.core.http_server')
        MCPHttpServer = getattr(http_server_module, 'MCPHttpServer')
        
        # サーバーインスタンスの取得
        server = MCPHttpServer.get_instance()
        
        # コマンドハンドラー関数の登録
        server.register_function(
            handle_command,
            "handle_command",
            examples=[
                {
                    "command": "create",
                    "type": "cube",
                    "name": "MyCube",
                    "size": 2.0
                },
                {
                    "command": "transform",
                    "target": "Cube",
                    "operation": "translate",
                    "value": [1, 0, 0]
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["create", "modify", "delete", "transform", "boolean", "array", "mirror", "analyze_scene"]}
                },
                "required": ["command"]
            }
        )
        
        logger.info("コマンドハンドラー関数がHTTPサーバーに登録されました")
        return True
        
    except Exception as e:
        logger.error(f"コマンドハンドラー関数の登録に失敗: {str(e)}")
        return False
