"""
Unified MCP GraphQL Common Definitions
GraphQLモジュールで共有される型定義と共通関数
"""

import bpy
import json
from typing import Dict, List, Any, Optional, Union, TypedDict, Tuple

# 型定義
class Vector3D(TypedDict):
    """3D座標を表す型"""
    x: float
    y: float
    z: float

class BlenderObject(TypedDict):
    """Blenderオブジェクトのデータを表す型"""
    name: str
    type: str
    location: Vector3D
    rotation: Vector3D
    scale: Vector3D
    dimensions: Vector3D
    visible: bool
    materials: List[str]

class BlenderMaterial(TypedDict):
    """Blenderマテリアルのデータを表す型"""
    name: str
    color: Optional[Tuple[float, float, float, float]]
    use_nodes: bool

class GraphQLResponse(TypedDict):
    """GraphQL応答の標準形式"""
    data: Optional[Any]
    errors: Optional[List[Dict[str, Any]]]

class APIResponse(TypedDict):
    """API応答の標準形式"""
    status: str
    message: Optional[str] 
    data: Optional[Any]

# 共通ユーティリティ関数
def vector_to_dict(vector) -> Vector3D:
    """ベクトルを辞書に変換"""
    return {"x": float(vector[0]), "y": float(vector[1]), "z": float(vector[2])}

def dict_to_vector(vector_dict: Vector3D) -> Tuple[float, float, float]:
    """辞書をベクトルに変換"""
    return (float(vector_dict.get("x", 0.0)), 
            float(vector_dict.get("y", 0.0)), 
            float(vector_dict.get("z", 0.0)))

def get_object_data(obj: bpy.types.Object) -> BlenderObject:
    """オブジェクトの標準データ構造を取得"""
    materials = []
    if hasattr(obj, "material_slots"):
        materials = [slot.material.name for slot in obj.material_slots 
                    if slot.material is not None]
    
    return {
        "name": obj.name,
        "type": obj.type,
        "location": vector_to_dict(obj.location),
        "rotation": vector_to_dict(obj.rotation_euler),
        "scale": vector_to_dict(obj.scale),
        "dimensions": vector_to_dict(obj.dimensions),
        "visible": obj.visible_get(),
        "materials": materials
    }

def get_material_data(mat: bpy.types.Material) -> BlenderMaterial:
    """マテリアルの標準データ構造を取得"""
    color = None
    if hasattr(mat, "diffuse_color"):
        color = tuple(mat.diffuse_color)
    
    return {
        "name": mat.name,
        "color": color,
        "use_nodes": mat.use_nodes
    }

def format_graphql_error(message: str, path: Optional[List[str]] = None) -> Dict[str, Any]:
    """GraphQLエラーメッセージをフォーマット"""
    error = {"message": message}
    if path:
        error["path"] = path
    return error

def create_success_response(data: Any) -> APIResponse:
    """成功応答を作成"""
    return {
        "status": "success",
        "data": data,
        "message": None
    }

def create_error_response(message: str, data: Any = None) -> APIResponse:
    """エラー応答を作成"""
    return {
        "status": "error",
        "message": message,
        "data": data
    }

# モジュール登録関数
def register():
    """GraphQL共通モジュールを登録"""
    pass

def unregister():
    """GraphQL共通モジュールの登録解除"""
    pass
