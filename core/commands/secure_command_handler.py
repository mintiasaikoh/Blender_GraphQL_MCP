"""
Blender GraphQL MCP - 安全なコマンドハンドラー
exec()を使わない安全なコマンド実行のための実装
"""

import bpy
import logging
import inspect
from typing import Dict, Any, List, Callable, Optional

# ロギング設定
logger = logging.getLogger(__name__)

# 安全なコマンドのレジストリ
SAFE_COMMANDS = {}

def register_command(name: str, description: str = ""):
    """
    安全なコマンドを登録するデコレータ
    
    Args:
        name: コマンド名
        description: コマンドの説明（ドキュメント用）
    """
    def decorator(func):
        SAFE_COMMANDS[name] = {
            "function": func,
            "description": description,
            "parameters": inspect.signature(func).parameters
        }
        return func
    return decorator

def validate_params(command_info: Dict[str, Any], params: Dict[str, Any]) -> Optional[str]:
    """
    コマンドパラメータを検証
    
    Args:
        command_info: コマンド情報
        params: 実行時のパラメータ
        
    Returns:
        エラーメッセージ (None = 検証通過)
    """
    func_params = command_info["parameters"]
    
    # 必須パラメータのチェック
    for param_name, param in func_params.items():
        if param.default == inspect.Parameter.empty and param_name != 'self' and param_name not in params:
            return f"Missing required parameter: {param_name}"
    
    # 未知のパラメータをチェック
    for param_name in params:
        if param_name not in func_params:
            return f"Unknown parameter: {param_name}"
    
    return None

def execute_safe_command(command_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    安全なコマンド実行（exec()の代替）
    
    Args:
        command_data: コマンドデータ
            {
                "command": "コマンド名",
                "params": {パラメータ}
            }
            
    Returns:
        Dict: 実行結果
    """
    # 基本的な検証
    if not isinstance(command_data, dict):
        return {"success": False, "error": "Command data must be a dictionary"}
    
    command_name = command_data.get("command")
    if not command_name:
        return {"success": False, "error": "Missing command name"}
    
    # パラメータ取得
    params = command_data.get("params", {})
    
    # 許可されたコマンドかチェック
    if command_name not in SAFE_COMMANDS:
        return {
            "success": False, 
            "error": f"Unknown or forbidden command: {command_name}",
            "available_commands": list(SAFE_COMMANDS.keys())
        }
    
    # コマンド情報取得
    command_info = SAFE_COMMANDS[command_name]
    
    # パラメータ検証
    validation_error = validate_params(command_info, params)
    if validation_error:
        return {"success": False, "error": validation_error}
    
    # コマンド実行
    try:
        result = command_info["function"](**params)
        
        # 結果の整形
        if isinstance(result, (dict, list, str, int, float, bool, type(None))):
            return {"success": True, "result": result}
        else:
            return {"success": True, "result": str(result)}
            
    except Exception as e:
        logger.error(f"コマンド実行エラー ({command_name}): {str(e)}")
        return {"success": False, "error": str(e)}

def get_available_commands() -> List[Dict[str, Any]]:
    """
    利用可能なコマンド一覧を取得
    
    Returns:
        List[Dict]: コマンド情報のリスト
    """
    commands = []
    for name, info in SAFE_COMMANDS.items():
        param_info = {}
        for param_name, param in info["parameters"].items():
            if param_name == 'self':
                continue
                
            param_info[param_name] = {
                "required": param.default == inspect.Parameter.empty,
                "default": None if param.default == inspect.Parameter.empty else param.default,
                "annotation": str(param.annotation) if param.annotation != inspect.Parameter.empty else None
            }
            
        commands.append({
            "name": name,
            "description": info["description"],
            "parameters": param_info
        })
    
    return commands

# --------------------------------------------------
# 安全なコマンド実装例
# --------------------------------------------------

@register_command("select_object", "Blenderオブジェクトを選択")
def select_object(object_name: str, deselect_others: bool = True) -> Dict[str, Any]:
    """
    指定された名前のオブジェクトを選択
    
    Args:
        object_name: 選択するオブジェクト名
        deselect_others: 他のオブジェクトの選択を解除するか
        
    Returns:
        Dict: 実行結果
    """
    # オブジェクトが存在するか確認
    if object_name not in bpy.data.objects:
        return {"success": False, "error": f"Object '{object_name}' not found"}
    
    # 選択状態を変更
    obj = bpy.data.objects[object_name]
    
    if deselect_others:
        # 他のオブジェクトの選択を解除
        for o in bpy.context.selected_objects:
            o.select_set(False)
    
    # 対象オブジェクトを選択
    obj.select_set(True)
    
    # アクティブオブジェクトに設定
    bpy.context.view_layer.objects.active = obj
    
    return {
        "success": True,
        "object": {
            "name": obj.name,
            "type": obj.type,
            "selected": obj.select_get()
        }
    }

@register_command("create_primitive", "プリミティブオブジェクトを作成")
def create_primitive(
    primitive_type: str, 
    name: Optional[str] = None,
    location: Optional[Dict[str, float]] = None,
    scale: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    プリミティブオブジェクトを作成
    
    Args:
        primitive_type: プリミティブタイプ (cube, sphere, plane, cylinder, cone)
        name: オブジェクト名（省略時は自動生成）
        location: 位置 {x, y, z}
        scale: スケール {x, y, z}
        
    Returns:
        Dict: 実行結果
    """
    # プリミティブタイプの検証
    valid_types = {"cube", "sphere", "plane", "cylinder", "cone"}
    if primitive_type.lower() not in valid_types:
        return {
            "success": False, 
            "error": f"Invalid primitive type: {primitive_type}",
            "valid_types": list(valid_types)
        }
    
    # Blender操作
    prim_type = primitive_type.lower()
    
    # 既存の選択を解除
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    
    # プリミティブ作成
    if prim_type == "cube":
        bpy.ops.mesh.primitive_cube_add()
    elif prim_type == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add()
    elif prim_type == "plane":
        bpy.ops.mesh.primitive_plane_add()
    elif prim_type == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add()
    elif prim_type == "cone":
        bpy.ops.mesh.primitive_cone_add()
    
    # 作成されたオブジェクトを取得
    obj = bpy.context.active_object
    
    # 名前設定
    if name:
        obj.name = name
    
    # 位置設定
    if location:
        if 'x' in location:
            obj.location.x = location['x']
        if 'y' in location:
            obj.location.y = location['y']
        if 'z' in location:
            obj.location.z = location['z']
    
    # スケール設定
    if scale:
        if 'x' in scale:
            obj.scale.x = scale['x']
        if 'y' in scale:
            obj.scale.y = scale['y']
        if 'z' in scale:
            obj.scale.z = scale['z']
    
    return {
        "success": True,
        "object": {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z]
        }
    }

@register_command("transform_object", "オブジェクトの変換（位置・回転・スケール）")
def transform_object(
    object_name: str,
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    scale: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    オブジェクトの変換パラメータを設定
    
    Args:
        object_name: 対象オブジェクト名
        location: 位置 {x, y, z}
        rotation: 回転（ラジアン） {x, y, z}
        scale: スケール {x, y, z}
        
    Returns:
        Dict: 実行結果
    """
    # オブジェクトが存在するか確認
    if object_name not in bpy.data.objects:
        return {"success": False, "error": f"Object '{object_name}' not found"}
    
    # オブジェクトを取得
    obj = bpy.data.objects[object_name]
    
    # 位置設定
    if location:
        if 'x' in location:
            obj.location.x = location['x']
        if 'y' in location:
            obj.location.y = location['y']
        if 'z' in location:
            obj.location.z = location['z']
    
    # 回転設定
    if rotation:
        if 'x' in rotation:
            obj.rotation_euler.x = rotation['x']
        if 'y' in rotation:
            obj.rotation_euler.y = rotation['y']
        if 'z' in rotation:
            obj.rotation_euler.z = rotation['z']
    
    # スケール設定
    if scale:
        if 'x' in scale:
            obj.scale.x = scale['x']
        if 'y' in scale:
            obj.scale.y = scale['y']
        if 'z' in scale:
            obj.scale.z = scale['z']
    
    return {
        "success": True,
        "object": {
            "name": obj.name,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z]
        }
    }

@register_command("delete_object", "オブジェクトを削除")
def delete_object(object_name: str) -> Dict[str, Any]:
    """
    指定されたオブジェクトを削除
    
    Args:
        object_name: 削除するオブジェクト名
        
    Returns:
        Dict: 実行結果
    """
    # オブジェクトが存在するか確認
    if object_name not in bpy.data.objects:
        return {"success": False, "error": f"Object '{object_name}' not found"}
    
    # オブジェクトを取得
    obj = bpy.data.objects[object_name]
    
    # オブジェクト情報を保存
    obj_info = {
        "name": obj.name,
        "type": obj.type
    }
    
    # オブジェクトを削除
    bpy.data.objects.remove(obj, do_unlink=True)
    
    return {
        "success": True,
        "deleted_object": obj_info
    }

@register_command("get_object_info", "オブジェクト情報を取得")
def get_object_info(object_name: str) -> Dict[str, Any]:
    """
    オブジェクトの詳細情報を取得
    
    Args:
        object_name: 対象オブジェクト名
        
    Returns:
        Dict: オブジェクト情報
    """
    # オブジェクトが存在するか確認
    if object_name not in bpy.data.objects:
        return {"success": False, "error": f"Object '{object_name}' not found"}
    
    # オブジェクトを取得
    obj = bpy.data.objects[object_name]
    
    # 基本情報の収集
    obj_info = {
        "name": obj.name,
        "type": obj.type,
        "location": [obj.location.x, obj.location.y, obj.location.z],
        "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
        "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
        "dimensions": [obj.dimensions.x, obj.dimensions.y, obj.dimensions.z],
        "visible": obj.visible_get(),
        "selected": obj.select_get(),
        "parent": obj.parent.name if obj.parent else None,
        "collections": [coll.name for coll in obj.users_collection]
    }
    
    # タイプ別の追加情報
    if obj.type == 'MESH':
        mesh_info = {
            "vertices_count": len(obj.data.vertices),
            "edges_count": len(obj.data.edges),
            "faces_count": len(obj.data.polygons),
            "materials": [mat.name if mat else None for mat in obj.data.materials]
        }
        obj_info["mesh_data"] = mesh_info
    elif obj.type == 'CAMERA':
        cam_info = {
            "lens": obj.data.lens,
            "sensor_width": obj.data.sensor_width,
            "sensor_height": obj.data.sensor_height,
            "clip_start": obj.data.clip_start,
            "clip_end": obj.data.clip_end
        }
        obj_info["camera_data"] = cam_info
    elif obj.type == 'LIGHT':
        light_info = {
            "light_type": obj.data.type,
            "energy": obj.data.energy,
            "color": [obj.data.color.r, obj.data.color.g, obj.data.color.b]
        }
        obj_info["light_data"] = light_info
    
    return {
        "success": True,
        "object": obj_info
    }

@register_command("set_render_settings", "レンダリング設定を変更")
def set_render_settings(
    engine: Optional[str] = None,
    resolution_x: Optional[int] = None,
    resolution_y: Optional[int] = None,
    resolution_percentage: Optional[int] = None,
    samples: Optional[int] = None
) -> Dict[str, Any]:
    """
    レンダリング設定を変更
    
    Args:
        engine: レンダリングエンジン ('BLENDER_EEVEE', 'CYCLES', 'BLENDER_WORKBENCH')
        resolution_x: X解像度
        resolution_y: Y解像度
        resolution_percentage: 解像度パーセンテージ
        samples: サンプル数
        
    Returns:
        Dict: 実行結果
    """
    # レンダリング設定を取得
    render = bpy.context.scene.render
    
    # エンジン設定
    if engine:
        valid_engines = {'BLENDER_EEVEE', 'CYCLES', 'BLENDER_WORKBENCH'}
        if engine not in valid_engines:
            return {
                "success": False, 
                "error": f"Invalid render engine: {engine}",
                "valid_engines": list(valid_engines)
            }
        render.engine = engine
    
    # 解像度設定
    if resolution_x:
        render.resolution_x = resolution_x
    if resolution_y:
        render.resolution_y = resolution_y
    if resolution_percentage:
        render.resolution_percentage = resolution_percentage
    
    # サンプル数設定（エンジンによって異なる）
    if samples:
        if render.engine == 'CYCLES':
            bpy.context.scene.cycles.samples = samples
        elif render.engine == 'BLENDER_EEVEE':
            bpy.context.scene.eevee.taa_render_samples = samples
    
    # 更新後の設定を取得
    current_settings = {
        "engine": render.engine,
        "resolution_x": render.resolution_x,
        "resolution_y": render.resolution_y,
        "resolution_percentage": render.resolution_percentage
    }
    
    # エンジン固有の設定
    if render.engine == 'CYCLES':
        current_settings["samples"] = bpy.context.scene.cycles.samples
    elif render.engine == 'BLENDER_EEVEE':
        current_settings["samples"] = bpy.context.scene.eevee.taa_render_samples
    
    return {
        "success": True,
        "render_settings": current_settings
    }