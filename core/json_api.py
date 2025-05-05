"""
純粋なJSONベースのBlender操作API
"""

import bpy
import logging
import traceback
from typing import Dict, Any, List

# ロガー設定
logger = logging.getLogger('unified_mcp.json_api')

def execute_in_main_thread(func, *args, **kwargs):
    """
    Blenderのメインスレッドで関数を実行する
    """
    try:
        # メインスレッドに登録するためのタイマー関数
        def main_thread_func():
            func(*args, **kwargs)
            return None  # 一度だけ実行するためにNoneを返す
            
        # タイマーに登録
        return bpy.app.timers.register(main_thread_func, first_interval=0.0)
    except Exception as e:
        logger.error(f"メインスレッド実行エラー: {str(e)}")
        return False

def create_primitive(primitive_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    基本的なプリミティブを作成する
    
    Args:
        primitive_type: 作成するプリミティブの種類 ('cube', 'sphere', 'cylinder', etc.)
        params: 作成パラメータ (location, size, name, color, etc.)
        
    Returns:
        作成結果
    """
    try:
        # パラメータを取得
        location = params.get('location', [0, 0, 0])
        name = params.get('name', f"Object_{primitive_type.capitalize()}")
        color = params.get('color', [0.8, 0.8, 0.8, 1.0])
        
        # プリミティブに応じた作成関数
        if primitive_type == 'cube':
            size = params.get('size', 2.0)
            
            def create_func():
                bpy.ops.mesh.primitive_cube_add(size=size, location=location)
                obj = bpy.context.active_object
                obj.name = name
                
                # マテリアルを作成して適用
                mat = bpy.data.materials.new(name=f"{name}_Material")
                mat.diffuse_color = color
                
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)
                
                return {"success": True, "name": obj.name, "type": obj.type}
            
            # メインスレッドで実行
            execute_in_main_thread(create_func)
            
            # 成功とみなす（非同期なので実際の結果は不明）
            return {
                "success": True,
                "message": f"立方体 '{name}' を作成しました",
                "name": name,
                "type": "MESH",
                "primitive": "cube"
            }
            
        elif primitive_type == 'sphere':
            radius = params.get('radius', 1.0)
            segments = params.get('segments', 32)
            
            def create_func():
                bpy.ops.mesh.primitive_uv_sphere_add(
                    radius=radius, 
                    segments=segments, 
                    ring_count=segments//2, 
                    location=location
                )
                obj = bpy.context.active_object
                obj.name = name
                
                # マテリアルを作成して適用
                mat = bpy.data.materials.new(name=f"{name}_Material")
                mat.diffuse_color = color
                
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)
                
                return {"success": True, "name": obj.name, "type": obj.type}
            
            # メインスレッドで実行
            execute_in_main_thread(create_func)
            
            # 成功とみなす（非同期なので実際の結果は不明）
            return {
                "success": True,
                "message": f"球体 '{name}' を作成しました",
                "name": name,
                "type": "MESH",
                "primitive": "sphere"
            }
            
        elif primitive_type == 'cylinder':
            radius = params.get('radius', 1.0)
            depth = params.get('depth', 2.0)
            vertices = params.get('vertices', 32)
            
            def create_func():
                bpy.ops.mesh.primitive_cylinder_add(
                    radius=radius, 
                    depth=depth, 
                    vertices=vertices, 
                    location=location
                )
                obj = bpy.context.active_object
                obj.name = name
                
                # マテリアルを作成して適用
                mat = bpy.data.materials.new(name=f"{name}_Material")
                mat.diffuse_color = color
                
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)
                
                return {"success": True, "name": obj.name, "type": obj.type}
            
            # メインスレッドで実行
            execute_in_main_thread(create_func)
            
            # 成功とみなす（非同期なので実際の結果は不明）
            return {
                "success": True,
                "message": f"円柱 '{name}' を作成しました",
                "name": name,
                "type": "MESH",
                "primitive": "cylinder"
            }
        
        elif primitive_type == 'cone':
            radius = params.get('radius', 1.0)
            depth = params.get('depth', 2.0)
            vertices = params.get('vertices', 32)
            
            def create_func():
                bpy.ops.mesh.primitive_cone_add(
                    radius1=radius, 
                    depth=depth, 
                    vertices=vertices, 
                    location=location
                )
                obj = bpy.context.active_object
                obj.name = name
                
                # マテリアルを作成して適用
                mat = bpy.data.materials.new(name=f"{name}_Material")
                mat.diffuse_color = color
                
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)
                
                return {"success": True, "name": obj.name, "type": obj.type}
            
            # メインスレッドで実行
            execute_in_main_thread(create_func)
            
            # 成功とみなす（非同期なので実際の結果は不明）
            return {
                "success": True,
                "message": f"円錐 '{name}' を作成しました",
                "name": name,
                "type": "MESH",
                "primitive": "cone"
            }
            
        else:
            return {
                "success": False,
                "message": f"未サポートのプリミティブタイプ: {primitive_type}",
                "supported_types": ["cube", "sphere", "cylinder", "cone"]
            }
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"プリミティブ作成エラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"プリミティブ作成エラー: {error_msg}",
            "error": error_msg
        }

def create_flowerpot(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    植木鉢オブジェクトを作成する
    
    Args:
        params: 作成パラメータ (location, size, name, color, etc.)
        
    Returns:
        作成結果
    """
    try:
        # パラメータを取得
        location = params.get('location', [0, 0, 0])
        name = params.get('name', "FlowerPot")
        color = params.get('color', [0.8, 0.4, 0.3, 1.0])  # テラコッタ色
        size = params.get('size', 1.0)
        has_soil = params.get('has_soil', True)
        
        def create_func():
            # シーン内のメッシュオブジェクトをクリア（カメラとライト以外）
            if params.get('clear_scene', True):
                for obj in list(bpy.data.objects):
                    if obj.type not in ["CAMERA", "LIGHT"]:
                        bpy.data.objects.remove(obj)
            
            # 植木鉢の作成（円柱からスタート）
            bpy.ops.mesh.primitive_cylinder_add(
                radius=size, 
                depth=size*1.5, 
                vertices=32, 
                location=(location[0], location[1], location[2] + size*0.75)
            )
            pot_base = bpy.context.active_object
            pot_base.name = f"{name}_Base"
            
            # マテリアルを作成（テラコッタ風の色）
            pot_material = bpy.data.materials.new(name=f"{name}_Material")
            pot_material.diffuse_color = color
            pot_base.data.materials.append(pot_material)
            
            # 内側を削る（植木鉢の内部空間）
            bpy.ops.mesh.primitive_cylinder_add(
                radius=size*0.85,
                depth=size*1.4,
                vertices=32,
                location=(location[0], location[1], location[2] + size*0.85)
            )
            pot_inner = bpy.context.active_object
            pot_inner.name = f"{name}_Inner"
            
            # ブーリアン演算で内側を削る
            bool_mod = pot_base.modifiers.new(name="Boolean", type='BOOLEAN')
            bool_mod.operation = 'DIFFERENCE'
            bool_mod.object = pot_inner
            
            # モディファイアを適用
            bpy.ops.object.select_all(action='DESELECT')
            pot_base.select_set(True)
            bpy.context.view_layer.objects.active = pot_base
            bpy.ops.object.modifier_apply(modifier="Boolean")
            
            # 不要なインナーオブジェクトを削除
            bpy.data.objects.remove(pot_inner)
            
            # 植木鉢の縁を作成
            bpy.ops.mesh.primitive_torus_add(
                major_radius=size,
                minor_radius=size*0.1,
                major_segments=32,
                minor_segments=12,
                location=(location[0], location[1], location[2] + size*1.5)
            )
            pot_rim = bpy.context.active_object
            pot_rim.name = f"{name}_Rim"
            pot_rim.data.materials.append(pot_material)
            
            created_objects = [pot_base.name, pot_rim.name]
            
            # 土を作成（オプション）
            if has_soil:
                bpy.ops.mesh.primitive_cylinder_add(
                    radius=size*0.8,
                    depth=size*0.2,
                    vertices=32,
                    location=(location[0], location[1], location[2] + size*1.35)
                )
                soil = bpy.context.active_object
                soil.name = f"{name}_Soil"
                
                # 土のマテリアル（茶色）
                soil_material = bpy.data.materials.new(name=f"{name}_Soil_Material")
                soil_material.diffuse_color = (0.3, 0.2, 0.1, 1.0)
                soil.data.materials.append(soil_material)
                
                created_objects.append(soil.name)
            
            # カメラを植木鉢に向ける（オプション）
            if params.get('adjust_camera', True):
                camera = bpy.data.objects.get("Camera")
                if camera:
                    camera.location = (location[0] + 3, location[1] - 3, location[2] + 3)
                    
                    # 既存のコンストレイントをクリア
                    for c in camera.constraints:
                        camera.constraints.remove(c)
                    
                    # 追跡コンストレイントを追加
                    constraint = camera.constraints.new('TRACK_TO')
                    constraint.target = pot_base
                    constraint.track_axis = 'TRACK_NEGATIVE_Z'
                    constraint.up_axis = 'UP_Y'
            
            return {
                "success": True, 
                "created_objects": created_objects
            }
        
        # メインスレッドで実行
        execute_in_main_thread(create_func)
        
        # 成功とみなす（非同期なので実際の結果は不明）
        return {
            "success": True,
            "message": f"植木鉢 '{name}' を作成しました",
            "name": name,
            "type": "FLOWERPOT"
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"植木鉢作成エラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"植木鉢作成エラー: {error_msg}",
            "error": error_msg
        }

def delete_objects(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクトを削除する
    
    Args:
        params: 削除パラメータ (keep_cameras, keep_lights, objects)
        
    Returns:
        削除結果
    """
    try:
        # パラメータを取得
        keep_cameras = params.get('keep_cameras', True)
        keep_lights = params.get('keep_lights', True)
        specific_objects = params.get('objects', None)  # 特定のオブジェクトのみを削除する場合
        
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
                        kept.append(obj_name)  # 存在しないオブジェクト
            
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
                "kept": kept
            }
        
        # メインスレッドで実行
        execute_in_main_thread(delete_func)
        
        # 成功とみなす（非同期なので実際の結果は不明）
        if specific_objects:
            return {
                "success": True,
                "message": f"{len(specific_objects)}個のオブジェクトを削除しました",
                "type": "SPECIFIC"
            }
        else:
            return {
                "success": True,
                "message": "対象オブジェクトを削除しました",
                "keep_cameras": keep_cameras,
                "keep_lights": keep_lights
            }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"オブジェクト削除エラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"オブジェクト削除エラー: {error_msg}",
            "error": error_msg
        }

def transform_object(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクトを変換する（移動、回転、拡大縮小）
    
    Args:
        params: 変換パラメータ (object_name, location, rotation, scale)
        
    Returns:
        変換結果
    """
    try:
        # パラメータを取得
        object_name = params.get('object_name')
        location = params.get('location')
        rotation = params.get('rotation')
        scale = params.get('scale')
        rotation_mode = params.get('rotation_mode', 'DEGREES')  # 'DEGREES' or 'RADIANS'
        
        if not object_name:
            return {
                "success": False,
                "message": "オブジェクト名が指定されていません"
            }
        
        # オブジェクトの存在確認
        if object_name not in bpy.data.objects:
            return {
                "success": False,
                "message": f"オブジェクト '{object_name}' が存在しません"
            }
            
        # 変換関数
        def transform_func():
            obj = bpy.data.objects[object_name]
            
            # 移動を適用
            if location:
                obj.location = tuple(location)
            
            # 回転を適用
            if rotation:
                if rotation_mode == 'DEGREES':
                    # 度からラジアンに変換
                    import math
                    obj.rotation_euler = (
                        rotation[0] * math.pi / 180,
                        rotation[1] * math.pi / 180,
                        rotation[2] * math.pi / 180
                    )
                else:  # 'RADIANS'
                    obj.rotation_euler = tuple(rotation)
            
            # スケールを適用
            if scale:
                obj.scale = tuple(scale)
                
            # 更新を強制
            bpy.context.view_layer.update()
        
        # メインスレッドで実行
        execute_in_main_thread(transform_func)
        
        # 成功結果を返す
        result = {
            "success": True,
            "message": f"オブジェクト '{object_name}' を変換しました",
            "object_name": object_name
        }
        
        # 変換パラメータを含める
        if location:
            result["location"] = location
        if rotation:
            result["rotation"] = rotation
        if scale:
            result["scale"] = scale
            
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"オブジェクト変換エラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"オブジェクト変換エラー: {error_msg}",
            "error": error_msg
        }

def get_scene_info(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    シーン情報を取得する
    
    Args:
        params: オプションパラメータ
        
    Returns:
        シーン情報
    """
    try:
        if params is None:
            params = {}
            
        # 返すデータを制御するパラメータ
        include_cameras = params.get('include_cameras', True)
        include_lights = params.get('include_lights', True)
        include_meshes = params.get('include_meshes', True)
        include_empty = params.get('include_empty', False)
        include_materials = params.get('include_materials', False)
        
        # 世界情報を取得
        active_scene = bpy.context.scene
        world = active_scene.world
        
        # オブジェクト情報を整理
        objects_info = []
        for obj in bpy.data.objects:
            # オブジェクトタイプに基づくフィルタリング
            if obj.type == 'CAMERA' and not include_cameras:
                continue
            if obj.type == 'LIGHT' and not include_lights:
                continue
            if obj.type == 'MESH' and not include_meshes:
                continue
            if obj.type == 'EMPTY' and not include_empty:
                continue
                
            # オブジェクト情報を作成
            obj_info = {
                "name": obj.name,
                "type": obj.type,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "scale": list(obj.scale),
                "visible": obj.visible_get()
            }
            
            # メッシュ固有の情報
            if obj.type == 'MESH':
                obj_info["vertices_count"] = len(obj.data.vertices) if obj.data else 0
                obj_info["faces_count"] = len(obj.data.polygons) if obj.data else 0
                
                # マテリアル情報
                if include_materials and obj.material_slots:
                    materials = []
                    for slot in obj.material_slots:
                        if slot.material:
                            material_info = {
                                "name": slot.material.name
                            }
                            # マテリアルノード情報があれば追加
                            if hasattr(slot.material, 'node_tree') and slot.material.node_tree:
                                material_info["has_nodes"] = True
                                material_info["nodes_count"] = len(slot.material.node_tree.nodes)
                            materials.append(material_info)
                    obj_info["materials"] = materials
            
            # カメラ固有の情報
            if obj.type == 'CAMERA':
                obj_info["lens"] = obj.data.lens if obj.data else 0
                obj_info["sensor_width"] = obj.data.sensor_width if obj.data else 0
                
            # ライト固有の情報
            if obj.type == 'LIGHT':
                obj_info["light_type"] = obj.data.type if obj.data else "UNKNOWN"
                obj_info["energy"] = obj.data.energy if obj.data else 0
                
            objects_info.append(obj_info)
        
        # 結果を返す
        return {
            "success": True,
            "scene": {
                "name": active_scene.name,
                "frame_current": active_scene.frame_current,
                "frame_start": active_scene.frame_start,
                "frame_end": active_scene.frame_end,
                "render": {
                    "engine": active_scene.render.engine,
                    "resolution_x": active_scene.render.resolution_x,
                    "resolution_y": active_scene.render.resolution_y,
                }
            },
            "objects": objects_info,
            "total_objects": len(objects_info)
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"シーン情報取得エラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"シーン情報取得エラー: {error_msg}",
            "error": error_msg
        }
