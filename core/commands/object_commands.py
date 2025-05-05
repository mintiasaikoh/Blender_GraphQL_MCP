"""
オブジェクト操作コマンドモジュール
Blenderのオブジェクトを作成・変更・削除するためのコマンドを提供
"""

import bpy
import bmesh
import math
import json
from typing import Dict, List, Any, Optional
from mathutils import Vector, Matrix, Euler

from .base import BlenderCommand, register_command
from ..validation.change_detector import ChangeDetector

class CreateObjectCommand(BlenderCommand):
    """
    新しいオブジェクトを作成するコマンド
    """
    
    command_name = "create_object"
    description = "Blenderシーンに新しいオブジェクトを作成"
    
    parameters_schema = {
        "type": {
            "type": "string",
            "description": "オブジェクトの種類（mesh, curve, camera, light, empty, text）",
            "enum": ["mesh", "curve", "camera", "light", "empty", "text"]
        },
        "name": {
            "type": "string",
            "description": "作成するオブジェクトの名前（オプション）"
        },
        "location": {
            "type": "array",
            "description": "[x, y, z] 形式の位置座標",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3
        },
        "rotation": {
            "type": "array",
            "description": "[x, y, z] 形式の回転（度）",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3
        },
        "scale": {
            "type": "array",
            "description": "[x, y, z] 形式のスケール",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3
        },
        "subtype": {
            "type": "string",
            "description": "オブジェクトのサブタイプ（光源タイプ、プリミティブ種類など）"
        },
        "size": {
            "type": "number",
            "description": "オブジェクトのサイズ（プリミティブの場合）"
        },
        "parameters": {
            "type": "object",
            "description": "追加パラメータ（オブジェクトタイプ固有）"
        }
    }
    
    def validate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """パラメータのバリデーション"""
        errors = []
        
        # 必須パラメータのチェック
        if "type" not in params:
            errors.append("type パラメータが必要です")
        elif params["type"] not in ["mesh", "curve", "camera", "light", "empty", "text"]:
            errors.append(f"無効なオブジェクトタイプ: {params['type']}")
        
        # 座標のチェック
        if "location" in params and (
            not isinstance(params["location"], list) or 
            len(params["location"]) != 3 or
            not all(isinstance(v, (int, float)) for v in params["location"])
        ):
            errors.append("location は [x, y, z] 形式の数値配列である必要があります")
        
        # 回転のチェック
        if "rotation" in params and (
            not isinstance(params["rotation"], list) or 
            len(params["rotation"]) != 3 or
            not all(isinstance(v, (int, float)) for v in params["rotation"])
        ):
            errors.append("rotation は [x, y, z] 形式の数値配列（度単位）である必要があります")
        
        # スケールのチェック
        if "scale" in params and (
            not isinstance(params["scale"], list) or 
            len(params["scale"]) != 3 or
            not all(isinstance(v, (int, float)) for v in params["scale"])
        ):
            errors.append("scale は [x, y, z] 形式の数値配列である必要があります")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def pre_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """実行前処理"""
        # 状態をキャプチャ
        return {
            "before_state": ChangeDetector.capture_state("basic")
        }
    
    def execute(self, params: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """コマンド実行"""
        obj_type = params["type"]
        name = params.get("name", "")
        location = params.get("location", [0, 0, 0])
        rotation = params.get("rotation", [0, 0, 0])
        scale = params.get("scale", [1, 1, 1])
        subtype = params.get("subtype", "")
        size = params.get("size", 1.0)
        extra_params = params.get("parameters", {})
        
        # オブジェクト作成
        obj = None
        
        if obj_type == "mesh":
            obj = self._create_mesh(name, subtype, size, extra_params)
        elif obj_type == "curve":
            obj = self._create_curve(name, subtype, size, extra_params)
        elif obj_type == "camera":
            obj = self._create_camera(name, extra_params)
        elif obj_type == "light":
            obj = self._create_light(name, subtype, size, extra_params)
        elif obj_type == "empty":
            obj = self._create_empty(name, subtype, size)
        elif obj_type == "text":
            obj = self._create_text(name, extra_params.get("text", "Text"))
        
        if not obj:
            return {"success": False, "error": f"Failed to create {obj_type} object"}
        
        # 位置・回転・スケールを設定
        obj.location = location
        obj.rotation_euler = [math.radians(r) for r in rotation]
        obj.scale = scale
        
        # 作成したオブジェクトを選択
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        return {"success": True, "object_name": obj.name}
    
    def post_execute(self, params: Dict[str, Any], result: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """実行後処理"""
        # 成功した場合のみ変更を検出
        if result.get("success", False):
            after_state = ChangeDetector.capture_state("basic")
            changes = ChangeDetector.compare_states(pre_state["before_state"], after_state)
            result["changes"] = changes
        
        return result
    
    def _create_mesh(self, name: str, subtype: str, size: float, params: Dict[str, Any]) -> Optional[bpy.types.Object]:
        """メッシュオブジェクトを作成"""
        if not name:
            name = f"Mesh_{subtype.capitalize()}" if subtype else "Mesh"
        
        # サブタイプに基づいてプリミティブを作成
        if subtype == "cube":
            bpy.ops.mesh.primitive_cube_add(size=size)
        elif subtype == "sphere":
            segments = params.get("segments", 32)
            rings = params.get("rings", 16)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=size)
        elif subtype == "cylinder":
            vertices = params.get("vertices", 32)
            radius = size
            depth = params.get("height", size * 2)
            bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth)
        elif subtype == "cone":
            vertices = params.get("vertices", 32)
            radius = size
            depth = params.get("height", size * 2)
            bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius, radius2=0, depth=depth)
        elif subtype == "torus":
            major_radius = params.get("major_radius", size)
            minor_radius = params.get("minor_radius", size * 0.25)
            major_segments = params.get("major_segments", 48)
            minor_segments = params.get("minor_segments", 12)
            bpy.ops.mesh.primitive_torus_add(
                major_radius=major_radius, 
                minor_radius=minor_radius,
                major_segments=major_segments,
                minor_segments=minor_segments
            )
        elif subtype == "plane":
            bpy.ops.mesh.primitive_plane_add(size=size)
        elif subtype == "grid":
            x_subdivisions = params.get("x_subdivisions", 10)
            y_subdivisions = params.get("y_subdivisions", 10)
            bpy.ops.mesh.primitive_grid_add(x_subdivisions=x_subdivisions, y_subdivisions=y_subdivisions, size=size)
        elif subtype == "monkey":
            bpy.ops.mesh.primitive_monkey_add(size=size)
        else:
            # デフォルトは立方体
            bpy.ops.mesh.primitive_cube_add(size=size)
        
        # 作成されたオブジェクトを取得
        obj = bpy.context.active_object
        if name:
            obj.name = name
        
        return obj
    
    def _create_curve(self, name: str, subtype: str, size: float, params: Dict[str, Any]) -> Optional[bpy.types.Object]:
        """カーブオブジェクトを作成"""
        if not name:
            name = f"Curve_{subtype.capitalize()}" if subtype else "Curve"
        
        # サブタイプに基づいてカーブを作成
        if subtype == "bezier":
            bpy.ops.curve.primitive_bezier_curve_add()
        elif subtype == "circle":
            bpy.ops.curve.primitive_bezier_circle_add(radius=size)
        elif subtype == "nurbs_curve":
            bpy.ops.curve.primitive_nurbs_curve_add()
        elif subtype == "nurbs_circle":
            bpy.ops.curve.primitive_nurbs_circle_add(radius=size)
        elif subtype == "nurbs_path":
            bpy.ops.curve.primitive_nurbs_path_add()
        else:
            # デフォルトはベジェカーブ
            bpy.ops.curve.primitive_bezier_curve_add()
        
        # 作成されたオブジェクトを取得
        obj = bpy.context.active_object
        if name:
            obj.name = name
        
        return obj
    
    def _create_camera(self, name: str, params: Dict[str, Any]) -> Optional[bpy.types.Object]:
        """カメラオブジェクトを作成"""
        if not name:
            name = "Camera"
        
        bpy.ops.object.camera_add()
        
        camera = bpy.context.active_object
        if name:
            camera.name = name
        
        # カメラパラメータの設定
        camera_data = camera.data
        if "lens" in params:
            camera_data.lens = params["lens"]
        if "type" in params:
            camera_type = params["type"].upper()
            if camera_type in ["PERSP", "ORTHO", "PANO"]:
                camera_data.type = camera_type
        if "clip_start" in params:
            camera_data.clip_start = params["clip_start"]
        if "clip_end" in params:
            camera_data.clip_end = params["clip_end"]
        
        return camera
    
    def _create_light(self, name: str, subtype: str, size: float, params: Dict[str, Any]) -> Optional[bpy.types.Object]:
        """ライトオブジェクトを作成"""
        if not name:
            name = f"Light_{subtype.capitalize()}" if subtype else "Light"
        
        # デフォルトのライトタイプ
        light_type = "POINT"
        
        # サブタイプからライトタイプを設定
        if subtype:
            if subtype.upper() in ["POINT", "SUN", "SPOT", "AREA"]:
                light_type = subtype.upper()
        
        bpy.ops.object.light_add(type=light_type)
        
        light = bpy.context.active_object
        if name:
            light.name = name
        
        # ライトパラメータの設定
        light_data = light.data
        if "energy" in params:
            light_data.energy = params["energy"]
        if "color" in params and isinstance(params["color"], list) and len(params["color"]) >= 3:
            light_data.color = params["color"][:3]
        if "shadow_soft_size" in params:
            light_data.shadow_soft_size = params["shadow_soft_size"]
        
        # ライトタイプ別の追加パラメータ
        if light_type == "SPOT":
            if "spot_size" in params:
                light_data.spot_size = math.radians(params["spot_size"])
            if "spot_blend" in params:
                light_data.spot_blend = params["spot_blend"]
        elif light_type == "AREA":
            if "size" in params:
                light_data.size = params["size"]
            if "size_y" in params:
                light_data.size_y = params["size_y"]
        
        return light
    
    def _create_empty(self, name: str, subtype: str, size: float) -> Optional[bpy.types.Object]:
        """エンプティオブジェクトを作成"""
        if not name:
            name = "Empty"
        
        # デフォルトの表示タイプ
        display_type = "PLAIN_AXES"
        
        # サブタイプから表示タイプを設定
        if subtype:
            if subtype.upper() in [
                "PLAIN_AXES", "ARROWS", "SINGLE_ARROW", 
                "CIRCLE", "CUBE", "SPHERE", 
                "CONE", "IMAGE"
            ]:
                display_type = subtype.upper()
        
        bpy.ops.object.empty_add(type=display_type)
        
        empty = bpy.context.active_object
        if name:
            empty.name = name
        
        # サイズを設定
        empty.empty_display_size = size
        
        return empty
    
    def _create_text(self, name: str, text: str) -> Optional[bpy.types.Object]:
        """テキストオブジェクトを作成"""
        if not name:
            name = "Text"
        
        bpy.ops.object.text_add()
        
        text_obj = bpy.context.active_object
        if name:
            text_obj.name = name
        
        # テキストを設定
        text_obj.data.body = text
        
        return text_obj


class DeleteObjectCommand(BlenderCommand):
    """
    オブジェクトを削除するコマンド
    """
    
    command_name = "delete_object"
    description = "指定されたオブジェクトを削除"
    
    parameters_schema = {
        "object_names": {
            "type": "array",
            "description": "削除するオブジェクト名のリスト",
            "items": {"type": "string"}
        },
        "delete_hierarchy": {
            "type": "boolean",
            "description": "階層（子オブジェクト）も削除するかどうか",
            "default": False
        }
    }
    
    def validate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """パラメータのバリデーション"""
        errors = []
        
        # オブジェクト名リストのチェック
        if "object_names" not in params or not params["object_names"]:
            errors.append("削除するオブジェクトを指定してください")
        elif not isinstance(params["object_names"], list):
            errors.append("object_names はオブジェクト名の配列である必要があります")
        
        # オブジェクトの存在チェック
        if "object_names" in params and isinstance(params["object_names"], list):
            not_found = []
            for name in params["object_names"]:
                if not bpy.data.objects.get(name):
                    not_found.append(name)
            
            if not_found:
                errors.append(f"次のオブジェクトが見つかりません: {', '.join(not_found)}")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def pre_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """実行前処理"""
        # 削除前の状態をキャプチャ
        return {
            "before_state": ChangeDetector.capture_state("basic")
        }
    
    def execute(self, params: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """コマンド実行"""
        object_names = params["object_names"]
        delete_hierarchy = params.get("delete_hierarchy", False)
        
        # 削除対象のオブジェクトを取得
        objects_to_delete = []
        for name in object_names:
            obj = bpy.data.objects.get(name)
            if obj:
                objects_to_delete.append(obj)
                
                # 階層も削除する場合は子オブジェクトを追加
                if delete_hierarchy:
                    objects_to_delete.extend(self._get_children_recursive(obj))
        
        # 一度選択を解除
        bpy.ops.object.select_all(action='DESELECT')
        
        # 削除するオブジェクトを選択
        for obj in objects_to_delete:
            obj.select_set(True)
        
        # 削除実行
        if objects_to_delete:
            bpy.ops.object.delete()
        
        return {
            "success": True,
            "deleted_count": len(objects_to_delete),
            "deleted_objects": [obj.name for obj in objects_to_delete]
        }
    
    def post_execute(self, params: Dict[str, Any], result: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """実行後処理"""
        # 変更を検出
        after_state = ChangeDetector.capture_state("basic")
        changes = ChangeDetector.compare_states(pre_state["before_state"], after_state)
        result["changes"] = changes
        
        return result
    
    def _get_children_recursive(self, obj) -> List[bpy.types.Object]:
        """指定オブジェクトの子孫をすべて取得（再帰的に）"""
        children = []
        for child in obj.children:
            children.append(child)
            children.extend(self._get_children_recursive(child))
        return children


class TransformObjectCommand(BlenderCommand):
    """
    オブジェクトを変形（移動・回転・スケール）するコマンド
    """
    
    command_name = "transform_object"
    description = "オブジェクトの変形（位置・回転・スケール）を変更"
    
    parameters_schema = {
        "object_name": {
            "type": "string",
            "description": "変形するオブジェクト名"
        },
        "location": {
            "type": "array",
            "description": "[x, y, z] 形式の位置座標、または変位量（相対モード時）",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3
        },
        "rotation": {
            "type": "array",
            "description": "[x, y, z] 形式の回転角度（度）、または回転量（相対モード時）",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3
        },
        "scale": {
            "type": "array",
            "description": "[x, y, z] 形式のスケール、または拡大率（相対モード時）",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3
        },
        "relative": {
            "type": "boolean",
            "description": "相対変形モード（現在の変形に対する加算）",
            "default": False
        },
        "apply_transform": {
            "type": "boolean",
            "description": "変形を適用するかどうか（オブジェクトのローカル座標系をリセット）",
            "default": False
        }
    }
    
    def validate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """パラメータのバリデーション"""
        errors = []
        
        # オブジェクト名のチェック
        if "object_name" not in params:
            errors.append("変形するオブジェクト名を指定してください")
        elif not bpy.data.objects.get(params["object_name"]):
            errors.append(f"オブジェクト '{params['object_name']}' が見つかりません")
        
        # 変形パラメータのチェック（少なくとも1つは必要）
        if not any(key in params for key in ["location", "rotation", "scale"]):
            errors.append("location, rotation, scale のいずれかを指定してください")
        
        # 座標のチェック
        if "location" in params and (
            not isinstance(params["location"], list) or 
            len(params["location"]) != 3 or
            not all(isinstance(v, (int, float)) for v in params["location"])
        ):
            errors.append("location は [x, y, z] 形式の数値配列である必要があります")
        
        # 回転のチェック
        if "rotation" in params and (
            not isinstance(params["rotation"], list) or 
            len(params["rotation"]) != 3 or
            not all(isinstance(v, (int, float)) for v in params["rotation"])
        ):
            errors.append("rotation は [x, y, z] 形式の数値配列である必要があります")
        
        # スケールのチェック
        if "scale" in params and (
            not isinstance(params["scale"], list) or 
            len(params["scale"]) != 3 or
            not all(isinstance(v, (int, float)) for v in params["scale"])
        ):
            errors.append("scale は [x, y, z] 形式の数値配列である必要があります")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def pre_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """実行前処理"""
        # 変形前の状態をキャプチャ
        return {
            "before_state": ChangeDetector.capture_state("basic")
        }
    
    def execute(self, params: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """コマンド実行"""
        object_name = params["object_name"]
        relative = params.get("relative", False)
        apply_transform = params.get("apply_transform", False)
        
        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "error": f"オブジェクト '{object_name}' が見つかりません"}
        
        # 元の変形値を保存
        original_location = obj.location.copy()
        original_rotation = obj.rotation_euler.copy()
        original_scale = obj.scale.copy()
        
        # 位置の変更
        if "location" in params:
            location = params["location"]
            if relative:
                obj.location[0] += location[0]
                obj.location[1] += location[1]
                obj.location[2] += location[2]
            else:
                obj.location = location
        
        # 回転の変更
        if "rotation" in params:
            rotation = params["rotation"]
            if relative:
                obj.rotation_euler[0] += math.radians(rotation[0])
                obj.rotation_euler[1] += math.radians(rotation[1])
                obj.rotation_euler[2] += math.radians(rotation[2])
            else:
                obj.rotation_euler = [math.radians(r) for r in rotation]
        
        # スケールの変更
        if "scale" in params:
            scale = params["scale"]
            if relative:
                obj.scale[0] *= scale[0]
                obj.scale[1] *= scale[1]
                obj.scale[2] *= scale[2]
            else:
                obj.scale = scale
        
        # 変形の適用（オブジェクトのローカル座標系をリセット）
        if apply_transform:
            # 現在のオブジェクトを選択
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # 変形を適用
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        return {
            "success": True,
            "object": object_name,
            "previous": {
                "location": [round(v, 4) for v in original_location],
                "rotation": [round(math.degrees(v), 2) for v in original_rotation],
                "scale": [round(v, 4) for v in original_scale]
            },
            "current": {
                "location": [round(v, 4) for v in obj.location],
                "rotation": [round(math.degrees(v), 2) for v in obj.rotation_euler],
                "scale": [round(v, 4) for v in obj.scale]
            },
            "applied_transform": apply_transform
        }
    
    def post_execute(self, params: Dict[str, Any], result: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """実行後処理"""
        # 変更を検出
        after_state = ChangeDetector.capture_state("basic")
        changes = ChangeDetector.compare_states(pre_state["before_state"], after_state)
        result["changes"] = changes
        
        return result


# コマンドを登録
def register():
    register_command(CreateObjectCommand)
    register_command(DeleteObjectCommand)
    register_command(TransformObjectCommand)
