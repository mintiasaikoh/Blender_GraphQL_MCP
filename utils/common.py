"""
Unified MCP Common Utilities
基本的なユーティリティ関数を提供
"""

import bpy
import json
import os
import tempfile
from typing import Dict, List, Any, Optional, Tuple, Union, TypedDict

# 基本的な型定義
class Vector3D(TypedDict):
    """3D座標を表す型"""
    x: float
    y: float
    z: float

class BlenderObjectInfo(TypedDict):
    """Blenderオブジェクト情報を表す型"""
    name: str
    type: str
    location: Vector3D
    rotation: Vector3D
    scale: Vector3D
    dimensions: Vector3D
    visible: bool
    materials: List[str]

class BlenderSceneInfo(TypedDict):
    """Blenderシーン情報を表す型"""
    name: str
    objects: List[str]
    active_object: Optional[str]
    selected_objects: List[str]
    frame_current: int
    frame_start: int
    frame_end: int

# オブジェクト操作ユーティリティ
def get_object_data(obj: bpy.types.Object) -> BlenderObjectInfo:
    """オブジェクトの標準データ構造を取得"""
    # マテリアル情報
    materials = []
    if hasattr(obj, "material_slots"):
        materials = [slot.material.name for slot in obj.material_slots 
                    if slot.material is not None]
    
    return {
        "name": obj.name,
        "type": obj.type,
        "location": {
            "x": obj.location.x,
            "y": obj.location.y,
            "z": obj.location.z
        },
        "rotation": {
            "x": obj.rotation_euler.x,
            "y": obj.rotation_euler.y,
            "z": obj.rotation_euler.z
        },
        "scale": {
            "x": obj.scale.x,
            "y": obj.scale.y,
            "z": obj.scale.z
        },
        "dimensions": {
            "x": obj.dimensions.x,
            "y": obj.dimensions.y,
            "z": obj.dimensions.z
        },
        "visible": obj.visible_get(),
        "materials": materials
    }

def get_scene_info() -> BlenderSceneInfo:
    """現在のシーン情報を取得"""
    scene = bpy.context.scene
    
    return {
        "name": scene.name,
        "objects": [obj.name for obj in scene.objects],
        "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
        "selected_objects": [obj.name for obj in bpy.context.selected_objects],
        "frame_current": scene.frame_current,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end
    }

def find_object_by_name(name: str) -> Optional[bpy.types.Object]:
    """名前からオブジェクトを検索"""
    return bpy.data.objects.get(name)

def find_objects_by_type(type_name: str) -> List[bpy.types.Object]:
    """型名からオブジェクトを検索"""
    return [obj for obj in bpy.data.objects if obj.type == type_name]

def find_objects_by_pattern(pattern: str) -> List[bpy.types.Object]:
    """名前パターンからオブジェクトを検索"""
    import re
    regex = re.compile(pattern)
    return [obj for obj in bpy.data.objects if regex.search(obj.name)]

# 位置・回転・スケールのユーティリティ
def vector_to_dict(vector) -> Vector3D:
    """ベクトルを辞書に変換"""
    return {"x": float(vector[0]), "y": float(vector[1]), "z": float(vector[2])}

def dict_to_vector(vector_dict: Vector3D) -> Tuple[float, float, float]:
    """辞書をベクトルに変換"""
    return (
        float(vector_dict.get("x", 0.0)), 
        float(vector_dict.get("y", 0.0)), 
        float(vector_dict.get("z", 0.0))
    )

# ファイル操作ユーティリティ
def ensure_directory(path: str) -> bool:
    """ディレクトリが存在することを確認し、なければ作成"""
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception:
            return False
    return True

def create_temp_blend_file() -> str:
    """一時的なBlendファイルを作成"""
    fd, path = tempfile.mkstemp(suffix='.blend')
    os.close(fd)
    return path

def backup_current_blend() -> str:
    """現在のBlendファイルをバックアップ"""
    backup_path = create_temp_blend_file()
    bpy.ops.wm.save_as_mainfile(filepath=backup_path, compress=True)
    return backup_path

def serialize_to_json(data: Any) -> str:
    """オブジェクトをJSON文字列に変換"""
    class BlenderEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, bpy.types.Object):
                return get_object_data(obj)
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)
    
    return json.dumps(data, cls=BlenderEncoder, indent=2, ensure_ascii=False)

# 標準的な応答フォーマット
def create_success_response(data: Any = None, message: Optional[str] = None) -> Dict[str, Any]:
    """成功応答を作成"""
    response = {
        "status": "success",
        "data": data
    }
    if message:
        response["message"] = message
    return response

def create_error_response(message: str, data: Any = None) -> Dict[str, Any]:
    """エラー応答を作成"""
    return {
        "status": "error",
        "message": message,
        "data": data
    }

def register():
    """共通ユーティリティモジュールを登録"""
    pass

def unregister():
    """共通ユーティリティモジュールの登録解除"""
    pass
