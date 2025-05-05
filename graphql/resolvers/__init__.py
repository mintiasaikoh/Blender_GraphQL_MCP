"""
Blender GraphQL Resolvers Package
カテゴリ別に整理されたリゾルバモジュールを提供

各リゾルバはクラスベースで整理され、機能ごとにモジュール化されています
"""

import logging
import bpy
import traceback
from typing import Dict, List, Any, Optional, Union

# ロガー初期化
logger = logging.getLogger("blender_json_mcp.graphql.resolvers")

# 各リゾルバモジュールをインポート
try:
    from .base import ResolverBase, create_success_response, create_error_response, handle_exceptions
    from .scene import SceneResolver
    from .object import ObjectResolver
    from .material import MaterialResolver
    from .camera import CameraResolver
    from .light import LightResolver
    from .render import RenderResolver
    from .polyhaven import PolyhavenResolver
    from .modifier import ModifierResolver
    
    # リゾルバインスタンスを作成
    scene_resolver = SceneResolver()
    object_resolver = ObjectResolver()
    material_resolver = MaterialResolver()
    camera_resolver = CameraResolver()
    light_resolver = LightResolver()
    render_resolver = RenderResolver()
    polyhaven_resolver = PolyhavenResolver()
    modifier_resolver = ModifierResolver()
    
    # リゾルバ状態をログに記録
    logger.info("すべてのリゾルバモジュールが正常にロードされました")
    RESOLVERS_AVAILABLE = True
    
except Exception as e:
    logger.error(f"リゾルバモジュールのロード中にエラーが発生しました: {e}")
    logger.debug(traceback.format_exc())
    RESOLVERS_AVAILABLE = False

# GraphQLスキーマから参照される関数名（従来のAPIとの互換性を維持）
# 新しいクラスベースの実装にマッピング

# 基本クエリ
def hello(obj, info):
    return scene_resolver.hello(obj, info)

def scene_info(obj, info):
    return scene_resolver.info(obj, info)

def scene(obj, info, name=None):
    return scene_resolver.get(obj, info, name)

# オブジェクト関連
def object(obj, info, name):
    return object_resolver.get(obj, info, name)

def objects(obj, info, type_name=None, name_pattern=None):
    return object_resolver.get_all(obj, info, type_name, name_pattern)

def create_object(obj, info, type='CUBE', name=None, location=None):
    return object_resolver.create(obj, info, type, name, location)

def transform_object(obj, info, name, location=None, rotation=None, scale=None):
    return object_resolver.transform(obj, info, name, location, rotation, scale)

def delete_object(obj, info, name):
    return object_resolver.delete(obj, info, name)

def boolean_operation(obj, info, operation, objectName, targetName, resultName=None):
    return object_resolver.boolean_operation(obj, info, operation, objectName, targetName, resultName)

# マテリアル関連
def materials(obj, info):
    return material_resolver.get_all(obj, info)

def material(obj, info, name):
    return material_resolver.get(obj, info, name)

def create_material(obj, info, name=None, baseColor=None, metallic=0.0, roughness=0.5, useNodes=True):
    return material_resolver.create(obj, info, name, baseColor, metallic, roughness, useNodes)

def assign_material(obj, info, objectName, materialName):
    return material_resolver.assign(obj, info, objectName, materialName)

def textures(obj, info):
    return material_resolver.get_textures(obj, info)

def add_texture(obj, info, materialName, texturePath, textureType='color'):
    return material_resolver.add_texture(obj, info, materialName, texturePath, textureType)

# カメラ関連
def cameras(obj, info):
    return camera_resolver.get_all(obj, info)

def camera(obj, info, name):
    return camera_resolver.get(obj, info, name)

def create_camera(obj, info, name=None, location=None, rotation=None, type="PERSP", lens=50.0, clip_start=0.1, clip_end=100.0, fov=None):
    return camera_resolver.create(obj, info, name, location, rotation, type, lens, clip_start, clip_end, fov)

def update_camera(obj, info, name, location=None, rotation=None, lens=None, clip_start=None, clip_end=None, fov=None):
    return camera_resolver.update(obj, info, name, location, rotation, lens, clip_start, clip_end, fov)

def delete_camera(obj, info, name):
    return camera_resolver.delete(obj, info, name)

# ライト関連
def lights(obj, info):
    return light_resolver.get_all(obj, info)

def light(obj, info, name):
    return light_resolver.get(obj, info, name)

def create_light(obj, info, name=None, type="POINT", location=None, rotation=None, color=None, energy=10.0, shadow=True):
    return light_resolver.create(obj, info, name, type, location, rotation, color, energy, shadow)

def update_light(obj, info, name, location=None, rotation=None, color=None, energy=None, shadow=None):
    return light_resolver.update(obj, info, name, location, rotation, color, energy, shadow)

def delete_light(obj, info, name):
    return light_resolver.delete(obj, info, name)

# レンダリング関連
def render_settings(obj, info):
    return render_resolver.get_settings(obj, info)

def update_render_settings(obj, info, engine=None, resolution_x=None, resolution_y=None, 
                          resolution_percentage=None, file_format=None, filepath=None, samples=None):
    return render_resolver.update_settings(obj, info, engine, resolution_x, resolution_y, 
                                          resolution_percentage, file_format, filepath, samples)

def render_frame(obj, info, filepath=None, frame=None):
    return render_resolver.render(obj, info, filepath, frame)

# モディファイア関連
def modifiers(obj, info, objectName):
    return modifier_resolver.get_all(obj, info, objectName)

def add_modifier(obj, info, objectName, modType, modName=None):
    return modifier_resolver.add(obj, info, objectName, modType, modName)

def update_modifier(obj, info, objectName, modName, params):
    return modifier_resolver.update(obj, info, objectName, modName, params)

def apply_modifier(obj, info, objectName, modName):
    return modifier_resolver.apply(obj, info, objectName, modName)

def delete_modifier(obj, info, objectName, modName):
    return modifier_resolver.delete(obj, info, objectName, modName)

# Polyhaven関連
def search_polyhaven(obj, info, query=None, category=None, limit=10):
    return polyhaven_resolver.search(obj, info, query, category, limit)

def import_polyhaven_asset(obj, info, assetId, assetType, resolution='2k'):
    return polyhaven_resolver.import_asset(obj, info, assetId, assetType, resolution)

# 後方互換性のための別名 - 以前のresolve_接頭辞を使用する関数もサポート
resolve_hello = hello
resolve_scene = scene
resolve_scene_info = scene_info
resolve_object = object
resolve_objects = objects
resolve_material = material
resolve_materials = materials
resolve_mesh_data = object_resolver.get_mesh_data
resolve_camera = camera
resolve_cameras = cameras
resolve_light = light
resolve_lights = lights
resolve_render_settings = render_settings
resolve_modifiers = modifiers
resolve_create_object = create_object
resolve_transform_object = transform_object
resolve_delete_object = delete_object
resolve_boolean_operation = boolean_operation
resolve_create_material = create_material
resolve_assign_material = assign_material
resolve_textures = textures
resolve_add_texture = add_texture
resolve_create_camera = create_camera
resolve_update_camera = update_camera
resolve_delete_camera = delete_camera
resolve_create_light = create_light
resolve_update_light = update_light
resolve_delete_light = delete_light
resolve_update_render_settings = update_render_settings
resolve_render_frame = render_frame
resolve_add_modifier = add_modifier
resolve_update_modifier = update_modifier
resolve_apply_modifier = apply_modifier
resolve_delete_modifier = delete_modifier
resolve_search_polyhaven = search_polyhaven
resolve_import_polyhaven_asset = import_polyhaven_asset
