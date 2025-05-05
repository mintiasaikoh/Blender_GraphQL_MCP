"""
JSON APIハンドラー
Blender操作をJSONメッセージで行うためのモジュール
"""

import bpy
import logging
import traceback
from typing import Dict, Any, List, Optional

# ロガー設定
logger = logging.getLogger('unified_mcp.json_handlers')

def execute_in_main_thread(func, *args, **kwargs):
    """
    Blenderのメインスレッドで関数を実行する
    """
    try:
        # タイマーで実行した結果を格納するリスト
        result_container = []
        
        # メインスレッドに登録するためのタイマー関数
        def main_thread_func():
            try:
                result = func(*args, **kwargs)
                result_container.append({"success": True, "result": result})
            except Exception as e:
                result_container.append({
                    "success": False, 
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
            return None  # 一度だけ実行するためにNoneを返す
        
        # タイマーに登録
        bpy.app.timers.register(main_thread_func, first_interval=0.0)
        
        # すぐにダミー結果を返す（非同期実行）
        return {"success": True, "execution": "async", "message": "処理がメインスレッドに登録されました"}
    
    except Exception as e:
        logger.error(f"メインスレッド実行エラー: {str(e)}")
        return {
            "success": False,
            "message": f"メインスレッド実行エラー: {str(e)}",
            "error": str(e)
        }

def create_primitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    基本的なプリミティブを作成する
    
    Args:
        data: {
            "type": "cube|sphere|cylinder|cone", 
            "name": "オブジェクト名", 
            "location": [x, y, z],
            "scale": [x, y, z] or float,
            "rotation": [x, y, z],
            "color": [r, g, b, a]
        }
        
    Returns:
        作成結果
    """
    try:
        # 必須フィールドを確認
        if "type" not in data:
            return {
                "success": False,
                "message": "typeフィールドが必要です",
                "required_fields": ["type"]
            }
        
        # パラメータを取得
        primitive_type = data["type"].lower()
        name = data.get("name", f"Object_{primitive_type.capitalize()}")
        location = data.get("location", [0, 0, 0])
        
        # scaleがリストまたは数値のどちらでも受け付ける
        scale_param = data.get("scale", 1.0)
        if isinstance(scale_param, (int, float)):
            scale = [scale_param, scale_param, scale_param]
        else:
            scale = scale_param
            
        rotation = data.get("rotation", [0, 0, 0])
        color = data.get("color", [0.8, 0.8, 0.8, 1.0])
        
        # プリミティブに応じた作成関数
        if primitive_type == "cube":
            def create_func():
                bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
                obj = bpy.context.active_object
                obj.name = name
                obj.scale = scale
                obj.rotation_euler = rotation
                
                # マテリアルを作成して適用
                mat = bpy.data.materials.new(name=f"{name}_Material")
                mat.diffuse_color = color
                obj.data.materials.clear()
                obj.data.materials.append(mat)
                
                return {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [round(v, 4) for v in obj.location],
                    "dimensions": [round(v, 4) for v in obj.dimensions]
                }
            
        elif primitive_type == "sphere":
            def create_func():
                segments = int(data.get("segments", 32))
                rings = int(data.get("rings", segments//2))
                radius = float(data.get("radius", 1.0))
                
                bpy.ops.mesh.primitive_uv_sphere_add(
                    radius=radius, 
                    segments=segments,
                    ring_count=rings,
                    location=location
                )
                obj = bpy.context.active_object
                obj.name = name
                obj.scale = scale
                obj.rotation_euler = rotation
                
                # マテリアルを作成して適用
                mat = bpy.data.materials.new(name=f"{name}_Material")
                mat.diffuse_color = color
                obj.data.materials.clear()
                obj.data.materials.append(mat)
                
                return {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [round(v, 4) for v in obj.location],
                    "dimensions": [round(v, 4) for v in obj.dimensions]
                }
            
        elif primitive_type == "cylinder":
            def create_func():
                vertices = int(data.get("vertices", 32))
                radius = float(data.get("radius", 1.0))
                depth = float(data.get("depth", 2.0))
                
                bpy.ops.mesh.primitive_cylinder_add(
                    radius=radius,
                    depth=depth,
                    vertices=vertices,
                    location=location
                )
                obj = bpy.context.active_object
                obj.name = name
                obj.scale = scale
                obj.rotation_euler = rotation
                
                # マテリアルを作成して適用
                mat = bpy.data.materials.new(name=f"{name}_Material")
                mat.diffuse_color = color
                obj.data.materials.clear()
                obj.data.materials.append(mat)
                
                return {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [round(v, 4) for v in obj.location],
                    "dimensions": [round(v, 4) for v in obj.dimensions]
                }
            
        elif primitive_type == "cone":
            def create_func():
                vertices = int(data.get("vertices", 32))
                radius = float(data.get("radius", 1.0))
                depth = float(data.get("depth", 2.0))
                
                bpy.ops.mesh.primitive_cone_add(
                    radius1=radius,
                    depth=depth, 
                    vertices=vertices,
                    location=location
                )
                obj = bpy.context.active_object
                obj.name = name
                obj.scale = scale
                obj.rotation_euler = rotation
                
                # マテリアルを作成して適用
                mat = bpy.data.materials.new(name=f"{name}_Material")
                mat.diffuse_color = color
                obj.data.materials.clear()
                obj.data.materials.append(mat)
                
                return {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [round(v, 4) for v in obj.location],
                    "dimensions": [round(v, 4) for v in obj.dimensions]
                }
            
        else:
            return {
                "success": False,
                "message": f"未サポートのプリミティブタイプ: {primitive_type}",
                "supported_types": ["cube", "sphere", "cylinder", "cone"]
            }
        
        # メインスレッドで実行
        return execute_in_main_thread(create_func)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"プリミティブ作成エラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"プリミティブ作成エラー: {error_msg}",
            "error": error_msg
        }

def delete_objects(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクトを削除する
    
    Args:
        data: {
            "keep_cameras": true/false,
            "keep_lights": true/false,
            "objects": ["obj1", "obj2"]  # 特定のオブジェクト名のリスト（指定時は他パラメータは無視）
        }
        
    Returns:
        削除結果
    """
    try:
        # パラメータを取得
        keep_cameras = data.get("keep_cameras", True)
        keep_lights = data.get("keep_lights", True)
        specific_objects = data.get("objects", None)  # 特定のオブジェクトのみを削除する場合
        
        def delete_func():
            deleted = []
            kept = []
            
            # 特定のオブジェクトのみを削除
            if specific_objects:
                for obj_name in specific_objects:
                    obj = bpy.data.objects.get(obj_name)
                    if obj:
                        bpy.data.objects.remove(obj)
                        deleted.append(obj_name)
                    else:
                        kept.append(f"{obj_name} (not found)")
            
            # すべてのオブジェクトをフィルタリングして削除
            else:
                for obj in list(bpy.data.objects):
                    skip = False
                    
                    # カメラとライトは条件に応じて保持
                    if keep_cameras and obj.type == 'CAMERA':
                        skip = True
                    
                    if keep_lights and obj.type == 'LIGHT':
                        skip = True
                    
                    if skip:
                        kept.append(obj.name)
                    else:
                        obj_name = obj.name
                        bpy.data.objects.remove(obj)
                        deleted.append(obj_name)
            
            return {
                "deleted": deleted,
                "kept": kept,
                "deleted_count": len(deleted),
                "kept_count": len(kept)
            }
        
        # メインスレッドで実行
        return execute_in_main_thread(delete_func)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"オブジェクト削除エラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"オブジェクト削除エラー: {error_msg}",
            "error": error_msg
        }

def transform_object(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクトの変換（移動、回転、スケール）
    
    Args:
        data: {
            "name": "オブジェクト名", 
            "location": [x, y, z],     # オプション
            "rotation": [x, y, z],     # オプション
            "scale": [x, y, z] or float, # オプション
            "mode": "absolute|relative" # 絶対値か相対値か（デフォルトは絶対値）
        }
        
    Returns:
        変換結果
    """
    try:
        # 必須フィールドを確認
        if "name" not in data:
            return {
                "success": False,
                "message": "nameフィールドが必要です",
                "required_fields": ["name"]
            }
        
        # パラメータを取得
        obj_name = data["name"]
        location = data.get("location", None)
        rotation = data.get("rotation", None)
        scale_param = data.get("scale", None)
        mode = data.get("mode", "absolute").lower()
        
        # スケールがリストまたは数値のどちらでも受け付ける
        if scale_param is not None:
            if isinstance(scale_param, (int, float)):
                scale = [scale_param, scale_param, scale_param]
            else:
                scale = scale_param
        else:
            scale = None
        
        def transform_func():
            # オブジェクトを取得
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                return {
                    "success": False,
                    "message": f"オブジェクト '{obj_name}' が見つかりません"
                }
            
            # 変換を適用
            if location is not None:
                if mode == "absolute":
                    obj.location = location
                else:  # relative
                    obj.location[0] += location[0]
                    obj.location[1] += location[1]
                    obj.location[2] += location[2]
            
            if rotation is not None:
                if mode == "absolute":
                    obj.rotation_euler = rotation
                else:  # relative
                    obj.rotation_euler[0] += rotation[0]
                    obj.rotation_euler[1] += rotation[1]
                    obj.rotation_euler[2] += rotation[2]
            
            if scale is not None:
                if mode == "absolute":
                    obj.scale = scale
                else:  # relative
                    obj.scale[0] += scale[0]
                    obj.scale[1] += scale[1]
                    obj.scale[2] += scale[2]
            
            return {
                "success": True,
                "name": obj.name,
                "location": [round(v, 4) for v in obj.location],
                "rotation": [round(v, 4) for v in obj.rotation_euler],
                "scale": [round(v, 4) for v in obj.scale],
                "dimensions": [round(v, 4) for v in obj.dimensions]
            }
        
        # メインスレッドで実行
        return execute_in_main_thread(transform_func)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"オブジェクト変換エラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"オブジェクト変換エラー: {error_msg}",
            "error": error_msg
        }

def get_scene_info() -> Dict[str, Any]:
    """
    シーン情報を取得する
    
    Returns:
        シーン情報
    """
    try:
        scene = bpy.context.scene
        active_object = bpy.context.active_object
        
        # オブジェクト一覧を取得
        objects_data = []
        for obj in scene.objects:
            obj_data = {
                "name": obj.name,
                "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
                "dimensions": [obj.dimensions.x, obj.dimensions.y, obj.dimensions.z],
            }
            
            # メッシュ情報（存在する場合）
            if obj.type == 'MESH' and obj.data:
                mesh = obj.data
                obj_data["vertices"] = len(mesh.vertices)
                obj_data["polygons"] = len(mesh.polygons)
                
                # マテリアル情報
                if obj.material_slots:
                    materials = []
                    for slot in obj.material_slots:
                        if slot.material:
                            mat = slot.material
                            materials.append({
                                "name": mat.name,
                                "color": list(mat.diffuse_color)
                            })
                    obj_data["materials"] = materials
            
            objects_data.append(obj_data)
        
        # シーン情報を構築
        scene_info = {
            "name": scene.name,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "objects_count": len(scene.objects),
            "objects": objects_data,
            "active_object": active_object.name if active_object else None,
        }
        
        return {
            "success": True,
            "scene": scene_info
        }
        
    except Exception as e:
        logger.error(f"シーン情報取得エラー: {str(e)}")
        return {
            "success": False,
            "message": f"シーン情報取得エラー: {str(e)}",
            "error": str(e)
        }

def modify_object_geometry(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    既存オブジェクトのジオメトリを修正する
    
    Args:
        data: {
            "name": "オブジェクト名",
            "operation": "subdivide|decimate|smooth|add_modifier",
            "params": {}
        }
        
    Returns:
        修正結果
    """
    try:
        # 必須フィールドを確認
        if "name" not in data or "operation" not in data:
            return {
                "success": False,
                "message": "name と operation フィールドが必要です",
                "required_fields": ["name", "operation"]
            }
        
        name = data["name"]
        operation = data["operation"].lower()
        params = data.get("params", {})
        
        # オブジェクトの存在確認
        if name not in bpy.data.objects:
            return {
                "success": False,
                "message": f"オブジェクト '{name}' が見つかりません"
            }
        
        obj = bpy.data.objects[name]
        
        # メッシュオブジェクトかどうか確認
        if obj.type != 'MESH':
            return {
                "success": False,
                "message": f"オブジェクト '{name}' はメッシュではありません (type: {obj.type})"
            }
        
        # 操作に応じた処理
        def execute_operation():
            # 現在のコンテキストでオブジェクトを選択
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            if operation == "subdivide":
                # サブディビジョン
                levels = params.get("levels", 1)
                bpy.ops.object.subdivision_set(level=levels, relative=False)
                return {"message": f"オブジェクト '{name}' にサブディビジョン (レベル {levels}) を適用しました"}
                
            elif operation == "decimate":
                # デシメート（ポリゴン削減）
                ratio = params.get("ratio", 0.5)
                # デシメートモディファイアを追加
                modifier = obj.modifiers.new(name="Decimate", type='DECIMATE')
                modifier.ratio = ratio
                # モディファイアを適用
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                return {"message": f"オブジェクト '{name}' にデシメート (比率 {ratio}) を適用しました"}
                
            elif operation == "smooth":
                # スムージング
                bpy.ops.object.shade_smooth()
                return {"message": f"オブジェクト '{name}' にスムージングを適用しました"}
                
            elif operation == "add_modifier":
                # モディファイア追加
                modifier_type = params.get("type", "")
                if not modifier_type:
                    return {"success": False, "message": "モディファイアの type が指定されていません"}
                
                # 対応するモディファイアを追加
                try:
                    modifier = obj.modifiers.new(name=modifier_type, type=modifier_type.upper())
                    # パラメータに応じた設定
                    for param_name, param_value in params.items():
                        if param_name != "type" and hasattr(modifier, param_name):
                            setattr(modifier, param_name, param_value)
                    
                    return {"message": f"オブジェクト '{name}' にモディファイア '{modifier_type}' を追加しました"}
                except Exception as e:
                    return {"success": False, "message": f"モディファイア追加エラー: {str(e)}"}
            else:
                return {"success": False, "message": f"未知の操作: {operation}"}
        
        # メインスレッドで実行
        result = execute_in_main_thread(execute_operation)
        
        if result.get("execution") == "async":
            result["message"] = f"オブジェクト '{name}' の {operation} 操作がキューに追加されました"
            return result
        
        return result
        
    except Exception as e:
        logger.error(f"ジオメトリ修正エラー: {str(e)}")
        return {
            "success": False,
            "message": f"ジオメトリ修正エラー: {str(e)}",
            "error": str(e)
        }

def set_object_property(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクトのプロパティを設定する
    
    Args:
        data: {
            "name": "オブジェクト名",
            "properties": {
                "property_name": value,
                ...
            }
        }
        
    Returns:
        設定結果
    """
    try:
        # 必須フィールドを確認
        if "name" not in data or "properties" not in data:
            return {
                "success": False,
                "message": "name と properties フィールドが必要です",
                "required_fields": ["name", "properties"]
            }
        
        name = data["name"]
        properties = data["properties"]
        
        # オブジェクトの存在確認
        if name not in bpy.data.objects:
            return {
                "success": False,
                "message": f"オブジェクト '{name}' が見つかりません"
            }
        
        obj = bpy.data.objects[name]
        
        # プロパティを設定する関数
        def set_properties():
            applied_props = []
            failed_props = []
            
            for prop_name, prop_value in properties.items():
                try:
                    # 特殊なプロパティ名の処理
                    if prop_name == "color" and obj.material_slots:
                        # 最初のマテリアルの色を変更
                        if obj.material_slots[0].material:
                            mat = obj.material_slots[0].material
                            if isinstance(prop_value, list) and len(prop_value) >= 3:
                                if len(prop_value) == 3:
                                    prop_value.append(1.0)  # アルファ値がない場合は1.0を追加
                                mat.diffuse_color = prop_value
                                applied_props.append(f"material.diffuse_color = {prop_value}")
                    elif prop_name in ["hide", "hide_viewport", "hide_render"]:
                        # 表示/非表示関連
                        setattr(obj, prop_name, bool(prop_value))
                        applied_props.append(f"{prop_name} = {bool(prop_value)}")
                    elif hasattr(obj, prop_name):
                        # 一般的なプロパティ
                        setattr(obj, prop_name, prop_value)
                        applied_props.append(f"{prop_name} = {prop_value}")
                    else:
                        # カスタムプロパティとして追加
                        obj[prop_name] = prop_value
                        applied_props.append(f"custom[{prop_name}] = {prop_value}")
                except Exception as prop_error:
                    failed_props.append({"name": prop_name, "error": str(prop_error)})
            
            return {
                "success": len(failed_props) == 0,
                "message": f"オブジェクト '{name}' のプロパティを設定しました ({len(applied_props)} 成功, {len(failed_props)} 失敗)",
                "applied": applied_props,
                "failed": failed_props
            }
        
        # メインスレッドで実行
        result = execute_in_main_thread(set_properties)
        
        if result.get("execution") == "async":
            result["message"] = f"オブジェクト '{name}' のプロパティ設定がキューに追加されました"
            return result
        
        return result
        
    except Exception as e:
        logger.error(f"プロパティ設定エラー: {str(e)}")
        return {
            "success": False,
            "message": f"プロパティ設定エラー: {str(e)}",
            "error": str(e)
        }
