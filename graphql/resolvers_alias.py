"""
GraphQLリゾルバエイリアス
schema.pyとの後方互換性のためのエイリアス定義
"""

from . import resolvers

# 基本関数エイリアス
resolvers.resolve_hello = resolvers.hello
resolvers.resolve_scene = resolvers.scene
resolvers.resolve_scene_info = resolvers.scene_info
resolvers.resolve_object = resolvers.object
resolvers.resolve_objects = resolvers.objects

# マテリアル関連エイリアス
resolvers.resolve_material = resolvers.material
resolvers.resolve_materials = resolvers.materials
resolvers.resolve_create_material = resolvers.create_material
resolvers.resolve_assign_material = resolvers.assign_material

# オブジェクト操作エイリアス
resolvers.resolve_create_object = resolvers.create_object
resolvers.resolve_create_smart_object = resolvers.create_smart_object
resolvers.resolve_transform_object = resolvers.transform_object
resolvers.resolve_delete_object = resolvers.delete_object
resolvers.resolve_boolean_operation = resolvers.boolean_operation

# テクスチャ関連エイリアス
resolvers.resolve_textures = resolvers.textures
resolvers.resolve_add_texture = resolvers.add_texture

# Polyhaven関連エイリアス
resolvers.resolve_search_polyhaven = resolvers.search_polyhaven
resolvers.resolve_import_polyhaven_asset = resolvers.import_polyhaven_asset

# カメラ関連エイリアス
resolvers.resolve_cameras = resolvers.cameras
resolvers.resolve_camera = resolvers.camera
resolvers.resolve_create_camera = resolvers.create_camera
resolvers.resolve_update_camera = resolvers.update_camera
resolvers.resolve_delete_camera = resolvers.delete_camera

# ライト関連エイリアス
resolvers.resolve_lights = resolvers.lights
resolvers.resolve_light = resolvers.light
resolvers.resolve_create_light = resolvers.create_light
resolvers.resolve_update_light = resolvers.update_light
resolvers.resolve_delete_light = resolvers.delete_light

# レンダリング関連エイリアス
resolvers.resolve_render_settings = resolvers.render_settings
resolvers.resolve_update_render_settings = resolvers.update_render_settings
resolvers.resolve_render_frame = resolvers.render_frame

# モディファイア関連エイリアス
resolvers.resolve_modifiers = resolvers.modifiers
resolvers.resolve_add_modifier = resolvers.add_modifier
resolvers.resolve_update_modifier = resolvers.update_modifier
resolvers.resolve_apply_modifier = resolvers.apply_modifier
resolvers.resolve_delete_modifier = resolvers.delete_modifier
