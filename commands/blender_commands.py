"""
基本的なBlenderコマンドの実装
"""

import bpy
import logging
from typing import Dict, Any, List, Optional, Tuple

# ロガー設定
logger = logging.getLogger('unified_mcp.commands')

# ベースコマンドクラス（継承して使用）
class BlenderCommand:
    """Blenderコマンドの基本クラス"""
    name = "abstract_command"
    description = "抽象基本コマンド"
    group = "blender"
    parameters = {}
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """コマンドを実行"""
        raise NotImplementedError("サブクラスで実装する必要があります")
    
    @classmethod
    def get_parameter_schema(cls) -> Dict[str, Any]:
        """パラメータスキーマを取得"""
        return cls.parameters

# 立方体作成コマンド
class CreateCubeCommand(BlenderCommand):
    """シーンに新しい立方体を作成するコマンド"""
    name = "create_cube"
    description = "Blenderシーンに新しい立方体を作成します"
    group = "objects"
    parameters = {
        "location": {
            "type": "array",
            "description": "立方体の位置座標 [x, y, z]",
            "default": [0, 0, 0],
            "items": {"type": "number"}
        },
        "size": {
            "type": "number",
            "description": "立方体のサイズ",
            "default": 2.0
        },
        "name": {
            "type": "string",
            "description": "立方体の名前",
            "default": "Cube"
        },
        "color": {
            "type": "array",
            "description": "立方体の色 [R, G, B, A]",
            "default": [0.8, 0.8, 0.8, 1.0],
            "items": {"type": "number"}
        }
    }
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """立方体を作成"""
        location = kwargs.get("location", [0, 0, 0])
        size = kwargs.get("size", 2.0)
        name = kwargs.get("name", "Cube")
        color = kwargs.get("color", [0.8, 0.8, 0.8, 1.0])
        
        try:
            # 立方体を追加
            bpy.ops.mesh.primitive_cube_add(size=size, location=location)
            obj = bpy.context.active_object
            obj.name = name
            
            # マテリアルを作成
            material_name = f"{name}_Material"
            if material_name not in bpy.data.materials:
                mat = bpy.data.materials.new(name=material_name)
            else:
                mat = bpy.data.materials[material_name]
            
            # 色を設定
            mat.diffuse_color = color
            
            # マテリアルをオブジェクトに適用
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
            
            logger.info(f"立方体 '{name}' を作成しました")
            
            return {
                "success": True,
                "object_name": name,
                "location": location,
                "size": size
            }
        
        except Exception as e:
            logger.error(f"立方体作成中にエラーが発生しました: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# シーン情報取得コマンド
class GetSceneInfoCommand(BlenderCommand):
    """現在のシーン情報を取得するコマンド"""
    name = "get_scene_info"
    description = "現在のBlenderシーンの情報を取得します"
    group = "scene"
    parameters = {}
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """シーン情報を取得"""
        try:
            scene = bpy.context.scene
            
            # シーン内のオブジェクト情報を取得
            objects_info = []
            for obj in bpy.data.objects:
                obj_data = {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [round(v, 4) for v in obj.location],
                    "dimensions": [round(v, 4) for v in obj.dimensions]
                }
                
                # メッシュ特有の情報
                if obj.type == 'MESH' and obj.data:
                    obj_data.update({
                        "vertices": len(obj.data.vertices),
                        "faces": len(obj.data.polygons),
                        "materials": [mat.name for mat in obj.data.materials if mat]
                    })
                
                objects_info.append(obj_data)
            
            # シーン情報を構築
            scene_info = {
                "name": scene.name,
                "objects_count": len(scene.objects),
                "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
                "frame_current": scene.frame_current,
                "frame_start": scene.frame_start,
                "frame_end": scene.frame_end,
                "objects": objects_info
            }
            
            logger.info("シーン情報を取得しました")
            return {
                "success": True,
                "scene": scene_info
            }
        
        except Exception as e:
            logger.error(f"シーン情報取得中にエラーが発生しました: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# カメラ操作コマンド
class FocusCameraCommand(BlenderCommand):
    """カメラをオブジェクトに向けるコマンド"""
    name = "focus_camera"
    description = "カメラを指定したオブジェクトに向けます"
    group = "camera"
    parameters = {
        "target": {
            "type": "string",
            "description": "ターゲットオブジェクト名",
            "required": True
        },
        "distance": {
            "type": "number",
            "description": "カメラとオブジェクトの距離",
            "default": 5.0
        }
    }
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """カメラをオブジェクトに向ける"""
        target_name = kwargs.get("target")
        distance = kwargs.get("distance", 5.0)
        
        if not target_name:
            return {"success": False, "error": "ターゲットオブジェクト名が指定されていません"}
        
        try:
            # ターゲットオブジェクトを取得
            if target_name not in bpy.data.objects:
                return {"success": False, "error": f"オブジェクト '{target_name}' が見つかりません"}
            
            target = bpy.data.objects[target_name]
            
            # カメラがなければ作成
            if 'Camera' not in bpy.data.objects:
                bpy.ops.object.camera_add()
                camera = bpy.context.active_object
                camera.name = 'Camera'
            else:
                camera = bpy.data.objects['Camera']
            
            # カメラを選択して有効化
            bpy.context.view_layer.objects.active = camera
            for obj in bpy.context.selected_objects:
                obj.select_set(False)
            camera.select_set(True)
            
            # ターゲットの位置にカメラを向ける
            direction = (camera.location - target.location).normalized()
            camera.location = target.location + direction * distance
            
            # カメラをターゲットの方向に向ける
            bpy.context.scene.camera = camera
            
            # トラックコンストレイント（カメラがオブジェクトを追跡）を設定
            constraint_name = 'Track To'
            if constraint_name not in camera.constraints:
                constraint = camera.constraints.new('TRACK_TO')
                constraint.name = constraint_name
            else:
                constraint = camera.constraints[constraint_name]
            
            constraint.target = target
            constraint.track_axis = 'TRACK_NEGATIVE_Z'
            constraint.up_axis = 'UP_Y'
            
            logger.info(f"カメラを '{target_name}' に向けました")
            return {
                "success": True,
                "camera": camera.name,
                "target": target_name,
                "distance": distance
            }
        
        except Exception as e:
            logger.error(f"カメラ操作中にエラーが発生しました: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# 利用可能なすべてのコマンドクラスのリスト
available_commands = [
    CreateCubeCommand,
    GetSceneInfoCommand,
    FocusCameraCommand
]
