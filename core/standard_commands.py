"""
Blender Unified MCP - 標準コマンド実装
FastAPIサーバーで使用する標準コマンドセット
"""

import logging
import bpy
import mathutils
import os
import json
import tempfile
from typing import Dict, List, Any, Optional, Union, Tuple

# ロギング設定
logger = logging.getLogger("mcp.commands")

# コマンド基底クラスのインポート
from .fastapi_server import Command

# ユーティリティ関数
def safe_name(name: str) -> str:
    """名前の衝突を避けるための安全な名前生成"""
    base_name = name
    counter = 1
    while base_name in bpy.data.objects:
        base_name = f"{name}.{counter:03d}"
        counter += 1
    return base_name

# システム・情報コマンド
class PingCommand(Command):
    """単純な接続テスト用コマンド"""
    name = "ping"
    description = "サーバーの応答を確認するための単純なコマンド"
    group = "system"
    parameters = {
        "message": {
            "type": "string",
            "description": "エコーするメッセージ",
            "default": "ping"
        }
    }
    
    def execute(self, message="ping"):
        return {
            "message": message,
            "response": "pong",
            "blender_version": bpy.app.version_string
        }

class GetBlenderInfoCommand(Command):
    """Blenderの情報を取得"""
    name = "get_blender_info"
    description = "Blenderのバージョンや設定情報を取得"
    group = "system"
    parameters = {}
    
    def execute(self):
        return {
            "version": bpy.app.version_string,
            "version_tuple": list(bpy.app.version),
            "build_date": bpy.app.build_date,
            "build_platform": bpy.app.build_platform,
            "binary_path": bpy.app.binary_path,
            "tempdir": bpy.app.tempdir
        }

# シーン操作コマンド
class GetSceneInfoCommand(Command):
    """シーン情報を取得"""
    name = "get_scene_info"
    description = "現在のシーンの詳細情報を取得"
    group = "scene"
    parameters = {}
    
    def execute(self):
        scene = bpy.context.scene
        return {
            "name": scene.name,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "render": {
                "engine": scene.render.engine,
                "resolution_x": scene.render.resolution_x,
                "resolution_y": scene.render.resolution_y,
                "resolution_percentage": scene.render.resolution_percentage,
                "fps": scene.render.fps
            },
            "objects_count": len(scene.objects)
        }

class SetFrameCommand(Command):
    """フレームを設定"""
    name = "set_frame"
    description = "現在のフレームを設定"
    group = "scene"
    parameters = {
        "frame": {
            "type": "integer",
            "description": "設定するフレーム番号",
            "required": True
        }
    }
    
    def execute(self, frame):
        bpy.context.scene.frame_current = frame
        return {
            "frame": bpy.context.scene.frame_current
        }

# オブジェクト操作コマンド
class ListObjectsCommand(Command):
    """オブジェクト一覧を取得"""
    name = "list_objects"
    description = "シーン内のオブジェクト一覧を取得"
    group = "object"
    parameters = {
        "detailed": {
            "type": "boolean",
            "description": "詳細情報を含めるかどうか",
            "default": False
        },
        "type_filter": {
            "type": "string",
            "description": "特定のタイプのみ取得 (MESH, CAMERA, LIGHT, ARMATURE, EMPTY, CURVE, など)",
            "default": None
        }
    }
    
    def execute(self, detailed=False, type_filter=None):
        objects_data = []
        for obj in bpy.data.objects:
            if type_filter and obj.type != type_filter:
                continue
                
            obj_data = {
                "name": obj.name,
                "type": obj.type
            }
            
            if detailed:
                obj_data.update({
                    "location": [round(v, 4) for v in obj.location],
                    "rotation": [round(v, 4) for v in obj.rotation_euler],
                    "scale": [round(v, 4) for v in obj.scale],
                    "dimensions": [round(v, 4) for v in obj.dimensions],
                    "parent": obj.parent.name if obj.parent else None,
                    "visible": obj.visible_get()
                })
                
                if obj.type == 'MESH' and obj.data:
                    obj_data.update({
                        "vertices_count": len(obj.data.vertices),
                        "edges_count": len(obj.data.edges),
                        "faces_count": len(obj.data.polygons),
                        "materials": [mat.name for mat in obj.data.materials if mat]
                    })
            
            objects_data.append(obj_data)
        
        return {
            "count": len(objects_data),
            "objects": objects_data
        }

class GetObjectCommand(Command):
    """特定のオブジェクト情報を取得"""
    name = "get_object"
    description = "名前を指定してオブジェクトの詳細情報を取得"
    group = "object"
    parameters = {
        "name": {
            "type": "string",
            "description": "取得するオブジェクト名",
            "required": True
        },
        "include_mesh_data": {
            "type": "boolean",
            "description": "メッシュデータを含めるかどうか",
            "default": False
        }
    }
    
    def execute(self, name, include_mesh_data=False):
        if name not in bpy.data.objects:
            raise ValueError(f"Object '{name}' not found")
        
        obj = bpy.data.objects[name]
        obj_data = {
            "name": obj.name,
            "type": obj.type,
            "location": [round(v, 4) for v in obj.location],
            "rotation": [round(v, 4) for v in obj.rotation_euler],
            "scale": [round(v, 4) for v in obj.scale],
            "dimensions": [round(v, 4) for v in obj.dimensions],
            "parent": obj.parent.name if obj.parent else None,
            "visible": obj.visible_get()
        }
        
        if obj.type == 'MESH' and obj.data:
            mesh_data = {
                "vertices_count": len(obj.data.vertices),
                "edges_count": len(obj.data.edges),
                "faces_count": len(obj.data.polygons),
                "materials": [mat.name for mat in obj.data.materials if mat]
            }
            
            if include_mesh_data:
                verts = []
                for v in obj.data.vertices:
                    verts.append([round(c, 4) for c in v.co])
                
                faces = []
                for p in obj.data.polygons:
                    faces.append(list(p.vertices))
                
                mesh_data.update({
                    "vertices": verts,
                    "faces": faces
                })
            
            obj_data.update({"mesh_data": mesh_data})
        
        return obj_data

class CreatePrimitiveCommand(Command):
    """基本的な3Dプリミティブを作成"""
    name = "create_primitive"
    description = "立方体、球、円柱などの基本的な3Dプリミティブを作成"
    group = "object"
    parameters = {
        "primitive_type": {
            "type": "string",
            "description": "作成するプリミティブの種類 (cube, sphere, cylinder, plane, cone, torus)",
            "required": True,
            "enum": ["cube", "sphere", "cylinder", "plane", "cone", "torus"]
        },
        "name": {
            "type": "string",
            "description": "作成するオブジェクトの名前",
            "default": None
        },
        "location": {
            "type": "array",
            "description": "作成位置 (X, Y, Z)",
            "items": {"type": "number"},
            "default": [0, 0, 0]
        },
        "scale": {
            "type": "array",
            "description": "スケール (X, Y, Z)",
            "items": {"type": "number"},
            "default": [1, 1, 1]
        },
        "size": {
            "type": "number",
            "description": "全体的なサイズ (立方体のみ)",
            "default": 2.0
        },
        "radius": {
            "type": "number",
            "description": "半径 (球、円柱、円錐、トーラス)",
            "default": 1.0
        },
        "depth": {
            "type": "number",
            "description": "深さ/高さ (円柱、円錐)",
            "default": 2.0
        }
    }
    
    def execute(self, primitive_type, name=None, location=None, scale=None, size=2.0, radius=1.0, depth=2.0):
        # デフォルト値の処理
        if location is None:
            location = [0, 0, 0]
        if scale is None:
            scale = [1, 1, 1]
        
        # 名前の設定
        if name is None:
            name = f"{primitive_type.capitalize()}"
        
        # 既存のオブジェクトを選択解除
        bpy.ops.object.select_all(action='DESELECT')
        
        # プリミティブ作成
        if primitive_type == "cube":
            bpy.ops.mesh.primitive_cube_add(size=size, location=location)
        elif primitive_type == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location)
        elif primitive_type == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=location)
        elif primitive_type == "plane":
            bpy.ops.mesh.primitive_plane_add(size=size, location=location)
        elif primitive_type == "cone":
            bpy.ops.mesh.primitive_cone_add(radius1=radius, depth=depth, location=location)
        elif primitive_type == "torus":
            bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=radius/4, location=location)
        else:
            raise ValueError(f"Unsupported primitive type: {primitive_type}")
        
        # 作成されたオブジェクトを取得
        obj = bpy.context.active_object
        
        # 名前を設定
        obj.name = safe_name(name)
        
        # スケールを設定
        obj.scale = mathutils.Vector(scale)
        
        return {
            "name": obj.name,
            "type": obj.type,
            "location": [round(v, 4) for v in obj.location],
            "dimensions": [round(v, 4) for v in obj.dimensions]
        }

class TransformObjectCommand(Command):
    """オブジェクトの変換（移動・回転・スケール）"""
    name = "transform_object"
    description = "オブジェクトの位置、回転、スケールを変更"
    group = "object"
    parameters = {
        "name": {
            "type": "string",
            "description": "変換するオブジェクト名",
            "required": True
        },
        "location": {
            "type": "array",
            "description": "新しい位置 (X, Y, Z)",
            "items": {"type": "number"},
            "default": None
        },
        "rotation": {
            "type": "array",
            "description": "新しい回転 (X, Y, Z) - ラジアン単位",
            "items": {"type": "number"},
            "default": None
        },
        "scale": {
            "type": "array",
            "description": "新しいスケール (X, Y, Z)",
            "items": {"type": "number"},
            "default": None
        },
        "relative": {
            "type": "boolean",
            "description": "現在の値に対して相対的に変更するかどうか",
            "default": False
        }
    }
    
    def execute(self, name, location=None, rotation=None, scale=None, relative=False):
        if name not in bpy.data.objects:
            raise ValueError(f"Object '{name}' not found")
        
        obj = bpy.data.objects[name]
        
        # 位置の変更
        if location is not None:
            if relative:
                obj.location += mathutils.Vector(location)
            else:
                obj.location = mathutils.Vector(location)
        
        # 回転の変更
        if rotation is not None:
            if relative:
                for i in range(3):
                    obj.rotation_euler[i] += rotation[i]
            else:
                obj.rotation_euler = mathutils.Euler(rotation)
        
        # スケールの変更
        if scale is not None:
            if relative:
                for i in range(3):
                    obj.scale[i] *= scale[i]
            else:
                obj.scale = mathutils.Vector(scale)
        
        return {
            "name": obj.name,
            "location": [round(v, 4) for v in obj.location],
            "rotation": [round(v, 4) for v in obj.rotation_euler],
            "scale": [round(v, 4) for v in obj.scale]
        }

class DeleteObjectCommand(Command):
    """オブジェクトを削除"""
    name = "delete_object"
    description = "指定したオブジェクトを削除"
    group = "object"
    parameters = {
        "name": {
            "type": "string",
            "description": "削除するオブジェクト名",
            "required": True
        }
    }
    
    def execute(self, name):
        if name not in bpy.data.objects:
            raise ValueError(f"Object '{name}' not found")
        
        obj = bpy.data.objects[name]
        
        # 選択解除して対象だけ選択
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        
        # 削除
        bpy.ops.object.delete()
        
        return {
            "status": "success",
            "message": f"Object '{name}' has been deleted"
        }

# マテリアル操作コマンド
class CreateMaterialCommand(Command):
    """マテリアルを作成"""
    name = "create_material"
    description = "新しいマテリアルを作成し、オプションでオブジェクトに適用"
    group = "material"
    parameters = {
        "name": {
            "type": "string",
            "description": "作成するマテリアル名",
            "default": None
        },
        "color": {
            "type": "array",
            "description": "マテリアルの色 (R, G, B, A)",
            "items": {"type": "number"},
            "default": [0.8, 0.8, 0.8, 1.0]
        },
        "metallic": {
            "type": "number",
            "description": "金属度 (0.0 - 1.0)",
            "default": 0.0
        },
        "roughness": {
            "type": "number",
            "description": "粗さ (0.0 - 1.0)",
            "default": 0.5
        },
        "object_name": {
            "type": "string",
            "description": "マテリアルを適用するオブジェクト名",
            "default": None
        }
    }
    
    def execute(self, name=None, color=None, metallic=0.0, roughness=0.5, object_name=None):
        # デフォルト値の処理
        if color is None:
            color = [0.8, 0.8, 0.8, 1.0]
        
        # 名前の設定
        if name is None:
            name = "New_Material"
        
        # 既存のマテリアルをチェック
        if name in bpy.data.materials:
            mat = bpy.data.materials[name]
        else:
            # 新しいマテリアルを作成
            mat = bpy.data.materials.new(name=name)
        
        # マテリアルプロパティの設定
        mat.use_nodes = True
        principled_bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if principled_bsdf:
            principled_bsdf.inputs['Base Color'].default_value = color
            principled_bsdf.inputs['Metallic'].default_value = metallic
            principled_bsdf.inputs['Roughness'].default_value = roughness
        
        # オブジェクトに適用
        if object_name:
            if object_name not in bpy.data.objects:
                raise ValueError(f"Object '{object_name}' not found")
            
            obj = bpy.data.objects[object_name]
            if obj.type != 'MESH':
                raise ValueError(f"Object '{object_name}' is not a mesh")
            
            # マテリアルスロットがなければ追加
            if len(obj.data.materials) == 0:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat
        
        return {
            "name": mat.name,
            "color": color,
            "metallic": metallic,
            "roughness": roughness,
            "object_applied": object_name
        }

# レンダリングコマンド
class RenderSceneCommand(Command):
    """シーンをレンダリング"""
    name = "render_scene"
    description = "現在のシーンをレンダリングして画像を保存"
    group = "render"
    parameters = {
        "output_path": {
            "type": "string",
            "description": "レンダリング画像の保存パス",
            "default": None
        },
        "resolution_x": {
            "type": "integer",
            "description": "出力横解像度",
            "default": None
        },
        "resolution_y": {
            "type": "integer",
            "description": "出力縦解像度",
            "default": None
        },
        "engine": {
            "type": "string",
            "description": "レンダリングエンジン (BLENDER_EEVEE, CYCLES)",
            "default": None
        },
        "samples": {
            "type": "integer",
            "description": "サンプル数",
            "default": None
        }
    }
    
    def execute(self, output_path=None, resolution_x=None, resolution_y=None, engine=None, samples=None):
        scene = bpy.context.scene
        render = scene.render
        
        # 元の設定を保存
        original_path = render.filepath
        original_engine = render.engine
        original_res_x = render.resolution_x
        original_res_y = render.resolution_y
        
        # 出力パスの設定
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, "blender_render.png")
        
        render.filepath = output_path
        
        # 解像度の設定
        if resolution_x is not None:
            render.resolution_x = resolution_x
        if resolution_y is not None:
            render.resolution_y = resolution_y
        
        # レンダリングエンジンの設定
        if engine is not None:
            render.engine = engine
        
        # サンプル数の設定
        if samples is not None:
            if render.engine == 'CYCLES':
                scene.cycles.samples = samples
            elif render.engine == 'BLENDER_EEVEE':
                scene.eevee.taa_render_samples = samples
        
        # レンダリング実行
        bpy.ops.render.render(write_still=True)
        
        # 元の設定を復元
        render.filepath = original_path
        render.engine = original_engine
        render.resolution_x = original_res_x
        render.resolution_y = original_res_y
        
        return {
            "status": "success",
            "output_path": output_path,
            "resolution": [render.resolution_x, render.resolution_y],
            "engine": render.engine
        }

# コマンドの登録関数
def register_standard_commands(server):
    """標準コマンドをサーバーに登録"""
    # システム・情報コマンド
    server.register_command(PingCommand)
    server.register_command(GetBlenderInfoCommand)
    
    # シーン操作コマンド
    server.register_command(GetSceneInfoCommand)
    server.register_command(SetFrameCommand)
    
    # オブジェクト操作コマンド
    server.register_command(ListObjectsCommand)
    server.register_command(GetObjectCommand)
    server.register_command(CreatePrimitiveCommand)
    server.register_command(TransformObjectCommand)
    server.register_command(DeleteObjectCommand)
    
    # マテリアル操作コマンド
    server.register_command(CreateMaterialCommand)
    
    # レンダリングコマンド
    server.register_command(RenderSceneCommand)
    
    logger.info(f"標準コマンドを登録しました")
