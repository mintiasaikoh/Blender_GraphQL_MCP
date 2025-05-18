"""
Blender GraphQL Resolvers Package
カテゴリ別に整理されたリゾルバモジュールを提供

各リゾルバはクラスベースで整理され、機能ごとにモジュール化されています
"""

import logging
import traceback
from typing import Dict, List, Any, Optional, Union

# ロガー初期化 - 命名を修正してblender_graphql_mcpに統一
logger = logging.getLogger("blender_graphql_mcp.tools.handlers")

# リゾルバの基本クラスとヘルパー
try:
    from .base import ResolverBase, create_success_response, create_error_response, handle_exceptions
    BASE_AVAILABLE = True
except ImportError as e:
    logger.error(f"基本リゾルバモジュールのインポートに失敗しました: {e}")
    logger.debug(traceback.format_exc())
    BASE_AVAILABLE = False
    
    # 基本機能のフォールバック実装
    def create_success_response(message=None, data=None):
        response = {"success": True}
        if message:
            response["message"] = message
        if data:
            if isinstance(data, dict):
                response.update(data)
            else:
                response["data"] = data
        return response
    
    def create_error_response(message, details=None):
        response = {"success": False, "message": message}
        if details:
            response["details"] = details
        return response
    
    def handle_exceptions(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"リゾルバエラー {func.__name__}: {str(e)}")
                logger.debug(traceback.format_exc())
                return create_error_response(f"処理エラー: {str(e)}")
        return wrapper
    
    class ResolverBase:
        """基本リゾルバのフォールバック実装"""
        def __init__(self):
            self.logger = logging.getLogger(f"blender_graphql_mcp.tools.handlers.fallback")
            
        def success_response(self, message=None, data=None):
            return create_success_response(message, data)
            
        def error_response(self, message, details=None):
            return create_error_response(message, details)

# 各リゾルバをインポート - 個別にtry-exceptで囲んで一部が失敗しても他に影響しないようにする
RESOLVERS_AVAILABLE = {}  # リゾルバの利用可能性を追跡

# リゾルバインスタンス
scene_resolver = None
object_resolver = None
material_resolver = None
camera_resolver = None
light_resolver = None
render_resolver = None
polyhaven_resolver = None
modifier_resolver = None
vrm_resolver = None
addon_resolver = None

# シーンリゾルバ
try:
    from .scene import SceneResolver
    scene_resolver = SceneResolver()
    RESOLVERS_AVAILABLE['scene'] = True
    logger.info("シーンリゾルバをロードしました")
except ImportError as e:
    logger.error(f"シーンリゾルバのインポートに失敗しました: {e}")
    logger.debug(traceback.format_exc())
    RESOLVERS_AVAILABLE['scene'] = False
    
    # フォールバッククラス
    class FallbackSceneResolver(ResolverBase):
        def hello(self, obj, info):
            return "GraphQL API (フォールバックリゾルバ)"
            
        def info(self, obj, info):
            return {"name": "デフォルトシーン", "objects": []}
            
        def get(self, obj, info, name=None):
            return {"name": name or "デフォルトシーン", "objects": []}
    
    scene_resolver = FallbackSceneResolver()

# オブジェクトリゾルバ
try:
    from .object import ObjectResolver
    object_resolver = ObjectResolver()
    RESOLVERS_AVAILABLE['object'] = True
    logger.info("オブジェクトリゾルバをロードしました")
except ImportError as e:
    logger.error(f"オブジェクトリゾルバのインポートに失敗しました: {e}")
    RESOLVERS_AVAILABLE['object'] = False
    
    # フォールバッククラス
    class FallbackObjectResolver(ResolverBase):
        def get(self, obj, info, name):
            return {"name": name, "type": "UNKNOWN"}
            
        def get_all(self, obj, info, type_name=None, name_pattern=None):
            return []
            
        def create(self, obj, info, type='CUBE', name=None, location=None):
            return create_error_response("オブジェクト作成は現在利用できません")
            
        def transform(self, obj, info, name, location=None, rotation=None, scale=None):
            return create_error_response("オブジェクト変換は現在利用できません")
            
        def delete(self, obj, info, name):
            return create_error_response("オブジェクト削除は現在利用できません")
            
        def boolean_operation(self, obj, info, operation, objectName, targetName, resultName=None):
            return create_error_response("ブーリアン操作は現在利用できません")
            
        def get_mesh_data(self, obj, info, name):
            return {"name": name, "vertices": [], "edges": [], "faces": []}
    
    object_resolver = FallbackObjectResolver()

# マテリアルリゾルバ - 簡略化のため他のリゾルバは同様の構造で実装
try:
    from .material import MaterialResolver
    material_resolver = MaterialResolver()
    RESOLVERS_AVAILABLE['material'] = True
    logger.info("マテリアルリゾルバをロードしました")
except ImportError as e:
    logger.error(f"マテリアルリゾルバのインポートに失敗しました: {e}")
    RESOLVERS_AVAILABLE['material'] = False
    material_resolver = ResolverBase()  # 基本フォールバック

# カメラリゾルバ
try:
    from .camera import CameraResolver
    camera_resolver = CameraResolver()
    RESOLVERS_AVAILABLE['camera'] = True
    logger.info("カメラリゾルバをロードしました")
except ImportError as e:
    logger.error(f"カメラリゾルバのインポートに失敗しました: {e}")
    RESOLVERS_AVAILABLE['camera'] = False
    camera_resolver = ResolverBase()  # 基本フォールバック

# ライトリゾルバ
try:
    from .light import LightResolver
    light_resolver = LightResolver()
    RESOLVERS_AVAILABLE['light'] = True
    logger.info("ライトリゾルバをロードしました")
except ImportError as e:
    logger.error(f"ライトリゾルバのインポートに失敗しました: {e}")
    RESOLVERS_AVAILABLE['light'] = False
    light_resolver = ResolverBase()  # 基本フォールバック

# レンダリングリゾルバ
try:
    from .render import RenderResolver
    render_resolver = RenderResolver()
    RESOLVERS_AVAILABLE['render'] = True
    logger.info("レンダリングリゾルバをロードしました")
except ImportError as e:
    logger.error(f"レンダリングリゾルバのインポートに失敗しました: {e}")
    RESOLVERS_AVAILABLE['render'] = False
    render_resolver = ResolverBase()  # 基本フォールバック

# Polyhavenリゾルバ
try:
    from .polyhaven import PolyhavenResolver
    polyhaven_resolver = PolyhavenResolver()
    RESOLVERS_AVAILABLE['polyhaven'] = True
    logger.info("Polyhavenリゾルバをロードしました")
except ImportError as e:
    logger.error(f"Polyhavenリゾルバのインポートに失敗しました: {e}")
    RESOLVERS_AVAILABLE['polyhaven'] = False
    polyhaven_resolver = ResolverBase()  # 基本フォールバック

# モディファイアリゾルバ
try:
    from .modifier import ModifierResolver
    modifier_resolver = ModifierResolver()
    RESOLVERS_AVAILABLE['modifier'] = True
    logger.info("モディファイアリゾルバをロードしました")
except ImportError as e:
    logger.error(f"モディファイアリゾルバのインポートに失敗しました: {e}")
    RESOLVERS_AVAILABLE['modifier'] = False
    modifier_resolver = ResolverBase()  # 基本フォールバック

# VRMリゾルバ
try:
    from .vrm import VrmResolver
    vrm_resolver = VrmResolver()
    
    # VRM拡張リゾルバも試行
    try:
        from .export_vrm_extended import VrmExportResolver
        vrm_export_resolver = VrmExportResolver()
        # 拡張エクスポート機能をVRMリゾルバに追加
        setattr(vrm_resolver, 'export_vrm_extended', vrm_export_resolver.export_vrm_extended)
        logger.info("VRM拡張エクスポートリゾルバをロードしました")
    except ImportError as ee:
        logger.warning(f"VRM拡張エクスポートリゾルバのインポートに失敗しました: {ee}")
        logger.debug(traceback.format_exc())
    
    RESOLVERS_AVAILABLE['vrm'] = True
    logger.info("VRMリゾルバをロードしました")
except ImportError as e:
    logger.error(f"VRMリゾルバのインポートに失敗しました: {e}")
    RESOLVERS_AVAILABLE['vrm'] = False
    vrm_resolver = ResolverBase()  # 基本フォールバック

# アドオンリゾルバ
try:
    from .addon import AddonResolver
    addon_resolver = AddonResolver()
    RESOLVERS_AVAILABLE['addon'] = True
    logger.info("アドオンリゾルバをロードしました")
except ImportError as e:
    logger.error(f"アドオンリゾルバのインポートに失敗しました: {e}")
    RESOLVERS_AVAILABLE['addon'] = False
    addon_resolver = ResolverBase()  # 基本フォールバック

# リゾルバ状態をログに記録
available_resolvers = [name for name, available in RESOLVERS_AVAILABLE.items() if available]
unavailable_resolvers = [name for name, available in RESOLVERS_AVAILABLE.items() if not available]

if available_resolvers:
    logger.info(f"利用可能なリゾルバ: {', '.join(available_resolvers)}")
else:
    logger.warning("利用可能なリゾルバがありません。すべてフォールバックを使用します。")

if unavailable_resolvers:
    logger.warning(f"利用できないリゾルバ: {', '.join(unavailable_resolvers)}")

# =============================
# GraphQLスキーマから参照される関数名
# 新しいクラスベースの実装にマッピング
# これらの関数はスキーマ定義で参照される
# =============================

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

def import_polyhaven_asset(obj, info, assetId, resolution='2k', materialName=None):
    return polyhaven_resolver.import_asset(obj, info, assetId, resolution, materialName)

# VRM関連
def create_vrm_model(obj, info, name):
    if hasattr(vrm_resolver, 'create_model'):
        return vrm_resolver.create_model(obj, info, name)
    return create_error_response("VRM機能は利用できません")

def apply_vrm_template(obj, info, modelId, templateType):
    if hasattr(vrm_resolver, 'apply_template'):
        return vrm_resolver.apply_template(obj, info, modelId, templateType)
    return create_error_response("VRM機能は利用できません")

def generate_vrm_rig(obj, info, modelId):
    if hasattr(vrm_resolver, 'generate_rig'):
        return vrm_resolver.generate_rig(obj, info, modelId)
    return create_error_response("VRM機能は利用できません")

def assign_auto_weights(obj, info, modelId):
    if hasattr(vrm_resolver, 'assign_auto_weights'):
        return vrm_resolver.assign_auto_weights(obj, info, modelId)
    return create_error_response("VRM機能は利用できません")

def add_blend_shape(obj, info, modelId, blendShape):
    if hasattr(vrm_resolver, 'add_blend_shape'):
        return vrm_resolver.add_blend_shape(obj, info, modelId, blendShape)
    return create_error_response("VRM機能は利用できません")

def update_blend_shape(obj, info, modelId, name, weight):
    if hasattr(vrm_resolver, 'update_blend_shape'):
        return vrm_resolver.update_blend_shape(obj, info, modelId, name, weight)
    return create_error_response("VRM機能は利用できません")

def export_vrm(obj, info, modelId, filepath, metadata=None):
    if hasattr(vrm_resolver, 'export_vrm'):
        return vrm_resolver.export_vrm(obj, info, modelId, filepath, metadata)
    return create_error_response("VRM機能は利用できません")

def export_vrm_extended(obj, info, modelId, filepath, metadata=None, options=None):
    if hasattr(vrm_resolver, 'export_vrm_extended'):
        return vrm_resolver.export_vrm_extended(obj, info, modelId, filepath, metadata, options)
    return create_error_response("VRM拡張エクスポート機能は利用できません")

def export_fbx_for_unity(obj, info, modelId, filepath, optimizeForUnity=True):
    if hasattr(vrm_resolver, 'export_fbx_for_unity'):
        return vrm_resolver.export_fbx_for_unity(obj, info, modelId, filepath, optimizeForUnity)
    return create_error_response("VRM機能は利用できません")

def validate_vrm_model(obj, info, modelId):
    if hasattr(vrm_resolver, 'validate_vrm_model'):
        return vrm_resolver.validate_vrm_model(obj, info, modelId)
    return create_error_response("VRM機能は利用できません")

def setup_unity_project(obj, info, projectPath, createVrmSupportFiles=True):
    if hasattr(vrm_resolver, 'setup_unity_project'):
        return vrm_resolver.setup_unity_project(obj, info, projectPath, createVrmSupportFiles)
    return create_error_response("VRM機能は利用できません")

def export_to_unity_editor(obj, info, modelId, unityProjectPath, createPrefab=True):
    if hasattr(vrm_resolver, 'export_to_unity_editor'):
        return vrm_resolver.export_to_unity_editor(obj, info, modelId, unityProjectPath, createPrefab)
    return create_error_response("VRM機能は利用できません") 

def generate_unity_materials(obj, info, modelId, unityProjectPath, materialType='Standard'):
    if hasattr(vrm_resolver, 'generate_unity_materials'):
        return vrm_resolver.generate_unity_materials(obj, info, modelId, unityProjectPath, materialType)
    return create_error_response("VRM機能は利用できません")

# 後方互換性のための別名 - 以前のresolve_接頭辞を使用する関数もサポート
resolve_hello = hello
resolve_scene = scene
resolve_scene_info = scene_info
resolve_object = object
resolve_objects = objects
resolve_material = material
resolve_materials = materials
resolve_mesh_data = object_resolver.get_mesh_data if hasattr(object_resolver, 'get_mesh_data') else lambda *args, **kwargs: {"vertices": [], "edges": [], "faces": []}
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

# VRM機能の後方互換性エイリアス
resolve_create_vrm_model = create_vrm_model
resolve_apply_vrm_template = apply_vrm_template
resolve_generate_vrm_rig = generate_vrm_rig
resolve_assign_auto_weights = assign_auto_weights
resolve_add_blend_shape = add_blend_shape
resolve_update_blend_shape = update_blend_shape
resolve_export_vrm = export_vrm
resolve_export_vrm_extended = export_vrm_extended
resolve_export_fbx_for_unity = export_fbx_for_unity
resolve_validate_vrm_model = validate_vrm_model
resolve_setup_unity_project = setup_unity_project
resolve_export_to_unity_editor = export_to_unity_editor
resolve_generate_unity_materials = generate_unity_materials

# アドオン関連
def get_addon_info(obj, info, addon_name):
    return addon_resolver.get_addon_info_resolver(addon_name)

def get_all_addons(obj, info):
    return addon_resolver.get_all_addons_resolver()

def enable_addon(obj, info, addon_name):
    return addon_resolver.enable_addon_resolver(addon_name)

def disable_addon(obj, info, addon_name):
    return addon_resolver.disable_addon_resolver(addon_name)

def install_addon(obj, info, file_path):
    return addon_resolver.install_addon_resolver(file_path)

def install_addon_from_url(obj, info, url):
    return addon_resolver.install_addon_from_url_resolver(url)

def update_addon(obj, info, addon_name):
    return addon_resolver.update_addon_resolver(addon_name)

def check_addon_updates(obj, info):
    return addon_resolver.check_addon_updates_resolver()

# アドオン機能の後方互換性エイリアス
resolve_get_addon_info = get_addon_info
resolve_get_all_addons = get_all_addons
resolve_enable_addon = enable_addon
resolve_disable_addon = disable_addon
resolve_install_addon = install_addon
resolve_install_addon_from_url = install_addon_from_url
resolve_update_addon = update_addon
resolve_check_addon_updates = check_addon_updates