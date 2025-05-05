"""
Object Commands Module - オブジェクト操作コマンド実装
"""

import bpy
import math
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

# ロギング設定
logger = logging.getLogger(__name__)

def handle_modify_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクト修正コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "modify",
                "target": "オブジェクト名",
                "properties": {
                    "プロパティ名": 値,
                    ...
                }
            }
        
    Returns:
        Dict: 実行結果
    """
    # 必須パラメータの確認
    target_name = data.get("target")
    properties = data.get("properties", {})
    
    if not target_name:
        return {
            "status": "error",
            "message": "Missing 'target' parameter for modify command",
            "details": {
                "required_parameters": ["target"]
            }
        }
    
    if not properties:
        return {
            "status": "error",
            "message": "Missing 'properties' parameter for modify command",
            "details": {
                "required_parameters": ["properties"]
            }
        }
    
    # ターゲットオブジェクトの取得
    obj = bpy.data.objects.get(target_name)
    
    if not obj:
        return {
            "status": "error",
            "message": f"Object not found: {target_name}",
            "details": {
                "available_objects": [o.name for o in bpy.data.objects]
            }
        }
    
    # 共通プロパティの適用
    modified_props = []
    
    try:
        # 名前の変更
        if "name" in properties:
            new_name = properties["name"]
            old_name = obj.name
            obj.name = new_name
            modified_props.append(f"name: {old_name} -> {new_name}")
        
        # 位置の変更
        if "location" in properties:
            location = properties["location"]
            if len(location) >= 3:
                obj.location = location
                modified_props.append("location")
        
        # 回転の変更
        if "rotation" in properties:
            rotation = properties["rotation"]
            if len(rotation) >= 3:
                obj.rotation_euler = rotation
                modified_props.append("rotation")
        
        # スケールの変更
        if "scale" in properties:
            scale = properties["scale"]
            if isinstance(scale, (int, float)):
                obj.scale = [scale, scale, scale]
                modified_props.append("scale (uniform)")
            elif len(scale) >= 3:
                obj.scale = scale
                modified_props.append("scale")
        
        # 材質の変更
        if "material" in properties:
            material_name = properties["material"]
            material = bpy.data.materials.get(material_name)
            
            if not material:
                # 材質が存在しない場合は新規作成
                material = bpy.data.materials.new(name=material_name)
                
                # 材質の色を設定
                if "color" in properties:
                    color = properties["color"]
                    if len(color) >= 3:
                        material.diffuse_color = color + [1.0] if len(color) == 3 else color
            
            # オブジェクトに材質を割り当て
            if obj.data and hasattr(obj.data, "materials"):
                if obj.data.materials:
                    obj.data.materials[0] = material
                else:
                    obj.data.materials.append(material)
                modified_props.append(f"material: {material_name}")
        
        # コレクションの変更
        if "collection" in properties:
            collection_name = properties["collection"]
            collection = bpy.data.collections.get(collection_name)
            
            if collection:
                # 現在のコレクションから削除
                for coll in bpy.data.collections:
                    if obj.name in coll.objects:
                        coll.objects.unlink(obj)
                
                # 指定されたコレクションに追加
                collection.objects.link(obj)
                modified_props.append(f"collection: {collection_name}")
        
        # 親オブジェクトの変更
        if "parent" in properties:
            parent_name = properties["parent"]
            
            # 親なしの場合
            if not parent_name:
                obj.parent = None
                modified_props.append("parent: None")
            else:
                parent = bpy.data.objects.get(parent_name)
                if parent:
                    obj.parent = parent
                    modified_props.append(f"parent: {parent_name}")
        
        # 可視性の変更
        if "visible" in properties:
            visible = properties["visible"]
            obj.hide_viewport = not visible
            obj.hide_render = not visible
            modified_props.append(f"visible: {visible}")
        
        # オブジェクト固有のプロパティの適用
        apply_object_specific_properties(obj, properties)
        
        return {
            "status": "success",
            "message": f"Modified object: {obj.name}",
            "details": {
                "name": obj.name,
                "modified_properties": modified_props
            }
        }
    except Exception as e:
        logger.error(f"Error modifying object {target_name}: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to modify object: {str(e)}",
            "details": {
                "name": target_name,
                "exception": str(e)
            }
        }

def apply_object_specific_properties(obj: bpy.types.Object, properties: Dict[str, Any]) -> None:
    """
    オブジェクトタイプ固有のプロパティを適用
    
    Args:
        obj: 対象オブジェクト
        properties: プロパティデータ
    """
    obj_type = obj.type
    
    # ライトの場合
    if obj_type == 'LIGHT' and obj.data:
        light = obj.data
        
        if "energy" in properties:
            light.energy = properties["energy"]
        
        if "color" in properties:
            color = properties["color"]
            if len(color) >= 3:
                light.color = color[:3]
        
        if "light_type" in properties:
            light_type = properties["light_type"]
            if light_type in ['POINT', 'SUN', 'SPOT', 'AREA']:
                light.type = light_type
        
        # スポットライトの場合
        if light.type == 'SPOT':
            if "spot_size" in properties:
                light.spot_size = properties["spot_size"]
            if "spot_blend" in properties:
                light.spot_blend = properties["spot_blend"]
        
        # エリアライトの場合
        if light.type == 'AREA':
            if "size" in properties:
                light.size = properties["size"]
            if "size_y" in properties:
                light.size_y = properties["size_y"]
        
        # 太陽光の場合
        if light.type == 'SUN':
            if "angle" in properties:
                light.angle = properties["angle"]
    
    # カメラの場合
    elif obj_type == 'CAMERA' and obj.data:
        camera = obj.data
        
        if "lens" in properties:
            camera.lens = properties["lens"]
        
        if "sensor_width" in properties:
            camera.sensor_width = properties["sensor_width"]
        
        if "sensor_height" in properties:
            camera.sensor_height = properties["sensor_height"]
    
    # テキストの場合
    elif obj_type == 'FONT' and obj.data:
        text_data = obj.data
        
        if "text" in properties:
            text_data.body = properties["text"]
        
        if "extrude" in properties:
            text_data.extrude = properties["extrude"]
        
        if "bevel_depth" in properties:
            text_data.bevel_depth = properties["bevel_depth"]
    
    # エンプティの場合
    elif obj_type == 'EMPTY':
        if "empty_type" in properties:
            empty_type = properties["empty_type"]
            if empty_type in ['PLAIN_AXES', 'ARROWS', 'SINGLE_ARROW', 'CIRCLE', 'CUBE', 'SPHERE', 'CONE', 'IMAGE']:
                obj.empty_display_type = empty_type
        
        if "empty_size" in properties:
            obj.empty_display_size = properties["empty_size"]

def handle_transform_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクト変換コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "transform",
                "target": "オブジェクト名",
                "operation": "translate|rotate|scale",
                "value": [x, y, z],
                "space": "LOCAL|WORLD" (オプション),
                "relative": true|false (オプション)
            }
        
    Returns:
        Dict: 実行結果
    """
    # 必須パラメータの確認
    target_name = data.get("target")
    operation = data.get("operation")
    value = data.get("value")
    
    if not target_name:
        return {
            "status": "error",
            "message": "Missing 'target' parameter for transform command",
            "details": {
                "required_parameters": ["target"]
            }
        }
    
    if not operation:
        return {
            "status": "error",
            "message": "Missing 'operation' parameter for transform command",
            "details": {
                "required_parameters": ["operation"],
                "available_operations": ["translate", "rotate", "scale"]
            }
        }
    
    if not value:
        return {
            "status": "error",
            "message": "Missing 'value' parameter for transform command",
            "details": {
                "required_parameters": ["value"]
            }
        }
    
    # ターゲットオブジェクトの取得
    obj = bpy.data.objects.get(target_name)
    
    if not obj:
        return {
            "status": "error",
            "message": f"Object not found: {target_name}",
            "details": {
                "available_objects": [o.name for o in bpy.data.objects]
            }
        }
    
    # オプションパラメータ
    space = data.get("space", "WORLD").upper()
    relative = data.get("relative", True)
    
    try:
        # 操作に基づいて変換を実行
        if operation.lower() == "translate":
            # 相対変換の場合
            if relative:
                if space == "LOCAL":
                    # ローカル空間での移動
                    mat = obj.matrix_world.to_3x3()
                    local_translation = mat @ mathutils.Vector(value)
                    obj.location += local_translation
                else:
                    # ワールド空間での移動
                    obj.location += mathutils.Vector(value)
            else:
                # 絶対位置設定
                obj.location = value
            
            transform_type = "translation"
            
        elif operation.lower() == "rotate":
            # 回転値をラジアンに変換（入力が度数法の場合）
            if "units" in data and data["units"].lower() == "degrees":
                value = [math.radians(v) for v in value]
            
            # 相対回転の場合
            if relative:
                if space == "LOCAL":
                    # ローカル空間での回転（複雑なため簡略化）
                    obj.rotation_euler.rotate(mathutils.Euler(value))
                else:
                    # ワールド空間での回転
                    for i, v in enumerate(value):
                        obj.rotation_euler[i] += v
            else:
                # 絶対回転設定
                obj.rotation_euler = value
            
            transform_type = "rotation"
            
        elif operation.lower() == "scale":
            # 相対スケールの場合
            if relative:
                # 現在のスケールに乗算
                if isinstance(value, (int, float)):
                    obj.scale = [s * value for s in obj.scale]
                else:
                    obj.scale = [obj.scale[i] * value[i] for i in range(min(len(obj.scale), len(value)))]
            else:
                # 絶対スケール設定
                if isinstance(value, (int, float)):
                    obj.scale = [value, value, value]
                else:
                    obj.scale = value
            
            transform_type = "scale"
            
        else:
            return {
                "status": "error",
                "message": f"Unknown operation: {operation}",
                "details": {
                    "available_operations": ["translate", "rotate", "scale"]
                }
            }
        
        return {
            "status": "success",
            "message": f"Transformed object: {obj.name} ({transform_type})",
            "details": {
                "name": obj.name,
                "operation": operation,
                "space": space,
                "relative": relative,
                "result_location": [round(v, 6) for v in obj.location],
                "result_rotation": [round(v, 6) for v in obj.rotation_euler],
                "result_scale": [round(v, 6) for v in obj.scale]
            }
        }
    except Exception as e:
        logger.error(f"Error transforming object {target_name}: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to transform object: {str(e)}",
            "details": {
                "name": target_name,
                "exception": str(e)
            }
        }

def handle_delete_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクト削除コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "delete",
                "targets": ["オブジェクト名1", "オブジェクト名2", ...] または "オブジェクト名"
            }
        
    Returns:
        Dict: 実行結果
    """
    # ターゲットの取得（文字列または配列）
    targets = data.get("targets")
    
    if not targets:
        return {
            "status": "error",
            "message": "Missing 'targets' parameter for delete command",
            "details": {
                "required_parameters": ["targets"]
            }
        }
    
    # 単一のターゲットを配列に変換
    if isinstance(targets, str):
        targets = [targets]
    
    # 削除するオブジェクトのリスト
    objects_to_delete = []
    missing_objects = []
    
    # ターゲットオブジェクトの取得と検証
    for target_name in targets:
        obj = bpy.data.objects.get(target_name)
        if obj:
            objects_to_delete.append(obj)
        else:
            missing_objects.append(target_name)
    
    # 削除処理
    deleted_objects = []
    
    try:
        for obj in objects_to_delete:
            name = obj.name
            bpy.data.objects.remove(obj)
            deleted_objects.append(name)
        
        # 結果の作成
        result = {
            "status": "success",
            "message": f"Deleted {len(deleted_objects)} object(s)",
            "details": {
                "deleted_objects": deleted_objects
            }
        }
        
        # 見つからなかったオブジェクトがある場合
        if missing_objects:
            result["details"]["missing_objects"] = missing_objects
            result["details"]["warning"] = f"Could not find {len(missing_objects)} object(s)"
        
        return result
    except Exception as e:
        logger.error(f"Error deleting objects: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to delete objects: {str(e)}",
            "details": {
                "deleted_objects": deleted_objects,
                "missing_objects": missing_objects,
                "exception": str(e)
            }
        }

def handle_select_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクト選択コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "select",
                "targets": ["オブジェクト名1", "オブジェクト名2", ...] または "オブジェクト名",
                "deselect_others": true|false,
                "active": "アクティブにするオブジェクト"
            }
        
    Returns:
        Dict: 実行結果
    """
    # ターゲットの取得（文字列または配列）
    targets = data.get("targets")
    deselect_others = data.get("deselect_others", True)
    active_object_name = data.get("active")
    
    if not targets:
        return {
            "status": "error",
            "message": "Missing 'targets' parameter for select command",
            "details": {
                "required_parameters": ["targets"]
            }
        }
    
    # 単一のターゲットを配列に変換
    if isinstance(targets, str):
        targets = [targets]
    
    # 他のオブジェクトの選択解除
    if deselect_others:
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
    
    # 選択するオブジェクトのリスト
    selected_objects = []
    missing_objects = []
    
    # ターゲットオブジェクトの選択
    for target_name in targets:
        obj = bpy.data.objects.get(target_name)
        if obj:
            obj.select_set(True)
            selected_objects.append(obj.name)
        else:
            missing_objects.append(target_name)
    
    # アクティブオブジェクトの設定
    active_set = False
    if active_object_name:
        active_obj = bpy.data.objects.get(active_object_name)
        if active_obj:
            bpy.context.view_layer.objects.active = active_obj
            active_set = True
    elif selected_objects:
        # アクティブオブジェクトが指定されていない場合、最初の選択オブジェクトをアクティブに設定
        active_obj = bpy.data.objects.get(selected_objects[0])
        if active_obj:
            bpy.context.view_layer.objects.active = active_obj
            active_set = True
    
    # 結果の作成
    result = {
        "status": "success",
        "message": f"Selected {len(selected_objects)} object(s)",
        "details": {
            "selected_objects": selected_objects,
            "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
            "active_set": active_set
        }
    }
    
    # 見つからなかったオブジェクトがある場合
    if missing_objects:
        result["details"]["missing_objects"] = missing_objects
        result["details"]["warning"] = f"Could not find {len(missing_objects)} object(s)"
    
    return result
