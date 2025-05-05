"""
Blender GraphQL Resolvers
完全統合版GraphQLリゾルバ関数を提供するモジュール
すべてのリゾルバ関数を一つのファイルに集約
"""

import bpy
import json
import math
import logging
import traceback
from typing import Dict, List, Optional, Any, Union
import functools

# 定数定義
BOOLEAN_OPERATION_UNION = 'UNION'
BOOLEAN_OPERATION_DIFFERENCE = 'DIFFERENCE'
BOOLEAN_OPERATION_INTERSECT = 'INTERSECT'

def create_success_response(message: str = None, data: Any = None) -> Dict[str, Any]:
    """
    成功レスポンスを生成
    
    Args:
        message: 成功メッセージ
        data: 付加データ
    """
    response = {'success': True}
    
    if message:
        response['message'] = message
    
    if data is not None:
        response.update(data)
    
    return response

def create_error_response(message: str) -> Dict[str, Any]:
    """
    エラーレスポンスを生成
    
    Args:
        message: エラーメッセージ
    """
    return {
        'success': False,
        'message': message
    }

def handle_exceptions(func):
    """
    リゾルバ関数用の例外処理デコレータ
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"リゾルバエラー [{func.__name__}]: {str(e)}")
            logger.error(traceback.format_exc())
            return create_error_response(f"処理中にエラーが発生しました: {str(e)}")
    return wrapper
import re
import bmesh
from math import degrees, radians
from typing import Dict, List, Any, Optional, Union, Tuple
from mathutils import Vector, Matrix

# ロガー初期化
logger = logging.getLogger("blender_json_mcp.graphql.resolvers")

# 共通定数
# 空間関係

RELATIONSHIP_ABOVE = "ABOVE"
RELATIONSHIP_BELOW = "BELOW"
RELATIONSHIP_LEFT = "LEFT"
RELATIONSHIP_RIGHT = "RIGHT"
RELATIONSHIP_FRONT = "FRONT"
RELATIONSHIP_BACK = "BACK"
RELATIONSHIP_INSIDE = "INSIDE"
RELATIONSHIP_AROUND = "AROUND"
RELATIONSHIP_ALIGNED = "ALIGNED"

# オブジェクトタイプ
SMART_OBJECT_CUBE = "CUBE"
SMART_OBJECT_SPHERE = "SPHERE"
SMART_OBJECT_CYLINDER = "CYLINDER"
SMART_OBJECT_PLANE = "PLANE"
SMART_OBJECT_CONE = "CONE"
SMART_OBJECT_TORUS = "TORUS"
SMART_OBJECT_TEXT = "TEXT"
SMART_OBJECT_EMPTY = "EMPTY"
SMART_OBJECT_LIGHT = "LIGHT"
SMART_OBJECT_CAMERA = "CAMERA"
SMART_OBJECT_SUZANNE = "SUZANNE"
SMART_OBJECT_MESH = "MESH"

# ブーリアン操作
BOOLEAN_OPERATION_UNION = "UNION"
BOOLEAN_OPERATION_DIFFERENCE = "DIFFERENCE"
BOOLEAN_OPERATION_INTERSECT = "INTERSECT"
BOOLEAN_SOLVER_FAST = "FAST"
BOOLEAN_SOLVER_EXACT = "EXACT"

# エラーメッセージ
ERROR_OBJECT_NOT_FOUND = "オブジェクトが見つかりません"
ERROR_INVALID_RELATIONSHIP = "無効な関係指定です"
ERROR_INVALID_OBJECT_TYPE = "無効なオブジェクトタイプです"
ERROR_INVALID_OPERATION = "無効な操作です"
ERROR_PROPERTY_PARSE = "プロパティの解析に失敗しました"

# ユーティリティ関数
def vector_to_dict(vec):
    """ベクトルを辞書に変換"""
    return {
        'x': vec[0],
        'y': vec[1],
        'z': vec[2] if len(vec) > 2 else 0
    }

def dict_to_vector(vec_dict):
    """辞書からベクトルを作成"""
    if not vec_dict:
        return Vector((0, 0, 0))
    return Vector((vec_dict.get('x', 0), vec_dict.get('y', 0), vec_dict.get('z', 0)))

def get_object_data(obj):
    """オブジェクトデータを取得"""
    if not obj:
        return None
        
    return {
        'name': obj.name,
        'type': obj.type,
        'location': vector_to_dict(obj.location),
        'rotation': vector_to_dict([degrees(a) for a in obj.rotation_euler]),
        'scale': vector_to_dict(obj.scale),
        'dimensions': vector_to_dict(obj.dimensions)
    }

def create_success_response(success=True, message=None, data=None):
    """成功レスポンスを作成"""
    response = {'success': success}
    if message:
        response['message'] = message
    if data:
        response.update(data)
    return response

def create_error_response(message, details=None):
    """エラーレスポンスを作成"""
    response = {
        'success': False,
        'message': message
    }
    if details:
        response['details'] = details
    return response

def handle_exceptions(func):
    """リゾルバ関数の例外処理デコレータ"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"リゾルバ関数 {func.__name__} でエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return create_error_response(str(e))
    return wrapper

# リゾルバ関数定義
# -------------------------------
# 基本リゾルバ関数
# -------------------------------

def hello(obj, info):
    """
    基本的な挙拶メッセージリゾルバ
    """
    logger.debug("resolve_hello が呼び出されました")
    return "Hello from Blender GraphQL API!"

@handle_exceptions
def scene(obj, info, name: Optional[str] = None):
    """
    シーン情報を返すリゾルバ
    
    Args:
        name: シーン名（省略時は現在のアクティブシーン）
    """
    logger.debug(f"resolve_scene が呼び出されました: {name}")
    
    scene = bpy.context.scene if name is None else bpy.data.scenes.get(name)
    if not scene:
        return create_error_response(f"シーン '{name}' が見つかりません")
    
    objects = []
    for obj in scene.objects:
        objects.append(get_object_data(obj))
    
    return {
        'name': scene.name,
        'objects': objects,
        'frame_current': scene.frame_current,
        'frame_start': scene.frame_start,
        'frame_end': scene.frame_end,
        'render': {
            'engine': scene.render.engine,
            'resolution_x': scene.render.resolution_x,
            'resolution_y': scene.render.resolution_y,
            'resolution_percentage': scene.render.resolution_percentage
        }
    }

# 互換性のためのresolve_scene_info関数
@handle_exceptions
def scene_info(obj, info):
    """
    現在のシーン情報を返すリゾルバ
    resolve_sceneとの互換性を提供
    """
    logger.debug("resolve_scene_info が呼び出されました")
    return scene(obj, info)

@handle_exceptions
def object(obj, info, name):
    """
    特定の名前のオブジェクト情報を返すリゾルバ
    
    Args:
        name: オブジェクト名
    """
    logger.debug(f"resolve_object が呼び出されました: {name}")
    
    # オブジェクトの存在確認
    if name not in bpy.data.objects:
        return create_error_response(f"オブジェクト '{name}' が見つかりません")
    
    bl_obj = bpy.data.objects[name]
    result = get_object_data(bl_obj)
    
    # 追加情報を取得
    if bl_obj.type == 'MESH':
        mesh = bl_obj.data
        result['vertices_count'] = len(mesh.vertices)
        result['faces_count'] = len(mesh.polygons)
        result['edges_count'] = len(mesh.edges)
        
        # マテリアル情報
        materials = []
        for mat_slot in bl_obj.material_slots:
            if mat_slot.material:
                materials.append(mat_slot.material.name)
        result['materials'] = materials
        
    # モディファイア情報
    modifiers = []
    for mod in bl_obj.modifiers:
        modifiers.append({
            'name': mod.name,
            'type': mod.type
        })
    result['modifiers'] = modifiers
    
    # 親子関係
    if bl_obj.parent:
        result['parent'] = bl_obj.parent.name
    
    result['children'] = [child.name for child in bl_obj.children]
    
    return result

@handle_exceptions
def objects(obj, info, type_name: Optional[str] = None, name_pattern: Optional[str] = None):
    """
    条件に一致するオブジェクトリストを取得
    
    Args:
        type_name: フィルタリングするオブジェクトタイプ
        name_pattern: 名前パターン（正規表現）
    """
    logger.debug(f"resolve_objects が呼び出されました: type={type_name}, pattern={name_pattern}")
    
    objects = []
    pattern = re.compile(name_pattern) if name_pattern else None
    
    for bl_obj in bpy.data.objects:
        # タイプフィルター
        if type_name and bl_obj.type != type_name:
            continue
            
        # 名前パターンフィルター
        if pattern and not pattern.search(bl_obj.name):
            continue
            
        # 一致したオブジェクトを追加
        objects.append(get_object_data(bl_obj))
    
    return objects

@handle_exceptions
def material(obj, info, name: str):
    """
    マテリアル情報を取得
    
    Args:
        name: マテリアル名
    """
    logger.debug(f"resolve_material が呼び出されました: {name}")
    
    # マテリアルの存在確認
    if name not in bpy.data.materials:
        return create_error_response(f"マテリアル '{name}' が見つかりません")
    
    mat = bpy.data.materials[name]
    result = {
        'name': mat.name,
        'use_nodes': mat.use_nodes,
        'is_grease_pencil': getattr(mat, 'is_grease_pencil', False)
    }
    
    # プリンシプルBSDFノードを探す
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                # ベースカラー
                base_color = node.inputs['Base Color'].default_value
                result['baseColor'] = {
                    'x': base_color[0],
                    'y': base_color[1],
                    'z': base_color[2]
                }
                
                # メタリックとラフネス
                result['metallic'] = node.inputs['Metallic'].default_value
                result['roughness'] = node.inputs['Roughness'].default_value
                break
    else:
        # ノードを使用しない場合の単色マテリアル
        result['baseColor'] = {
            'x': mat.diffuse_color[0],
            'y': mat.diffuse_color[1],
            'z': mat.diffuse_color[2]
        }
    
    return result

@handle_exceptions
def materials(obj, info):
    """
    マテリアル一覧を取得
    """
    logger.debug("resolve_materials が呼び出されました")
    
    materials = []
    for mat in bpy.data.materials:
        materials.append(resolve_material(obj, info, mat.name))
    
    return materials

@handle_exceptions
def create_object(obj, info, type='CUBE', name=None, location=None):
    """
    新しいオブジェクトを作成するリゾルバ
    
    Args:
        type: オブジェクトタイプ
        name: オブジェクト名（指定しない場合は自動生成）
        location: 位置情報
    """
    logger.debug(f"resolve_create_object が呼び出されました: type={type}, name={name}, location={location}")
    
    # オブジェクト名が指定されていない場合は自動生成
    if name is None:
        name = f"Object_{type}_{len(bpy.data.objects)}"
    
    # 名前が既に存在する場合は連番を付ける
    base_name = name
    counter = 1
    while name in bpy.data.objects:
        name = f"{base_name}.{counter:03d}"
        counter += 1
    
    # 位置情報がない場合はデフォルト値を使用
    loc = dict_to_vector(location) if location else Vector((0, 0, 0))
    loc_tuple = (loc.x, loc.y, loc.z)
    
    # オブジェクトタイプに応じて作成
    if type == 'CUBE':
        bpy.ops.mesh.primitive_cube_add(location=loc_tuple)
    elif type == 'SPHERE':
        bpy.ops.mesh.primitive_uv_sphere_add(location=loc_tuple)
    elif type == 'CYLINDER':
        bpy.ops.mesh.primitive_cylinder_add(location=loc_tuple)
    elif type == 'CONE':
        bpy.ops.mesh.primitive_cone_add(location=loc_tuple)
    elif type == 'PLANE':
        bpy.ops.mesh.primitive_plane_add(location=loc_tuple)
    elif type == 'EMPTY':
        bpy.ops.object.empty_add(location=loc_tuple)
    elif type == 'TORUS':
        bpy.ops.mesh.primitive_torus_add(location=loc_tuple)
    elif type == 'SUZANNE':
        bpy.ops.mesh.primitive_monkey_add(location=loc_tuple)
    else:
        return create_error_response(f"無効なオブジェクトタイプ: {type}")
    
    # 作成されたオブジェクトに名前を付ける
    created_obj = bpy.context.active_object
    created_obj.name = name
    
    logger.info(f"新規オブジェクトを作成しました: {name} ({type})")
    
    # 結果を返す
    return create_success_response(
        message=f"オブジェクトを作成しました: {name}",
        data={'object': get_object_data(created_obj)}
    )

@handle_exceptions
def create_smart_object(obj, info, object_type: str, name: Optional[str] = None,
                              location: Optional[Dict[str, float]] = None,
                              rotation: Optional[Dict[str, float]] = None,
                              scale: Optional[Dict[str, float]] = None,
                              properties: Optional[str] = None):
    """
    よく使われるオブジェクトを簡単に作成
    
    Args:
        object_type: オブジェクトタイプ（CUBE, SPHEREなど）
        name: オブジェクト名（任意）
        location: 位置情報
        rotation: 回転情報（度数法）
        scale: スケール情報
        properties: 追加プロパティ（JSON形式）
    """
    logger.debug(f"resolve_create_smart_object が呼び出されました: type={object_type}")
    
    # オブジェクト名が指定されていない場合は自動生成
    if name is None:
        name = f"{object_type.lower()}_{len(bpy.data.objects)}"
    
    # 名前が既に存在する場合は連番を付ける
    base_name = name
    counter = 1
    while name in bpy.data.objects:
        name = f"{base_name}_{counter:03d}"
        counter += 1
        
    # 引数をベクトルに変換
    loc = dict_to_vector(location) if location else Vector((0, 0, 0))
    loc_tuple = (loc.x, loc.y, loc.z)
    
    # オブジェクトを作成
    # 基本プリミティブ
    if object_type == SMART_OBJECT_CUBE:
        bpy.ops.mesh.primitive_cube_add(location=loc_tuple)
    elif object_type == SMART_OBJECT_SPHERE:
        bpy.ops.mesh.primitive_uv_sphere_add(location=loc_tuple)
    elif object_type == SMART_OBJECT_CYLINDER:
        bpy.ops.mesh.primitive_cylinder_add(location=loc_tuple)
    elif object_type == SMART_OBJECT_PLANE:
        bpy.ops.mesh.primitive_plane_add(location=loc_tuple)
    elif object_type == SMART_OBJECT_CONE:
        bpy.ops.mesh.primitive_cone_add(location=loc_tuple)
    elif object_type == SMART_OBJECT_TORUS:
        bpy.ops.mesh.primitive_torus_add(location=loc_tuple)
    elif object_type == SMART_OBJECT_SUZANNE:
        bpy.ops.mesh.primitive_monkey_add(location=loc_tuple)
    elif object_type == SMART_OBJECT_EMPTY:
        bpy.ops.object.empty_add(location=loc_tuple)
    else:
        return create_error_response(f"無効なオブジェクトタイプ: {object_type}")
    
    # 作成されたオブジェクトを取得し、名前を設定
    created_obj = bpy.context.active_object
    created_obj.name = name
    
    # 回転情報が指定されていれば設定
    if rotation:
        rot = dict_to_vector(rotation)
        created_obj.rotation_euler = (radians(rot.x), radians(rot.y), radians(rot.z))
    
    # スケール情報が指定されていれば設定
    if scale:
        scl = dict_to_vector(scale)
        created_obj.scale = (scl.x, scl.y, scl.z)
    
    # 追加プロパティが指定されていれば設定
    if properties:
        try:
            props = json.loads(properties)
            
            # プロパティを適用
            for key, value in props.items():
                if hasattr(created_obj, key):
                    setattr(created_obj, key, value)
                else:
                    logger.warning(f"プロパティ '{key}' はオブジェクトに存在しません")
                    
        except json.JSONDecodeError:
            logger.error(f"プロパティJSONのパースエラー: {properties}")
            return create_error_response(ERROR_PROPERTY_PARSE)
    
    logger.info(f"スマートオブジェクト作成成功: {name} ({object_type})")
    
    # 結果を返す
    return create_success_response(
        message=f"オブジェクトを作成しました: {name}",
        data={
            'object': get_object_data(created_obj)
        }
    )

@handle_exceptions
def transform_object(obj, info, name, location=None, rotation=None, scale=None):
    """
    オブジェクトを変換（移動・回転・スケール）するリゾルバ
    
    Args:
        name: オブジェクト名
        location: 新しい位置情報
        rotation: 新しい回転情報（度数法）
        scale: 新しいスケール情報
    """
    logger.debug(f"resolve_transform_object が呼び出されました: name={name}, location={location}, rotation={rotation}, scale={scale}")
    
    # オブジェクトの存在確認
    if name not in bpy.data.objects:
        return create_error_response(f"オブジェクト '{name}' が見つかりません")
    
    bl_obj = bpy.data.objects[name]
    
    # 位置を変更
    if location:
        loc = dict_to_vector(location)
        bl_obj.location = loc
    
    # 回転を変更
    if rotation:
        rot = dict_to_vector(rotation)
        bl_obj.rotation_euler = (radians(rot.x), radians(rot.y), radians(rot.z))
    
    # スケールを変更
    if scale:
        scl = dict_to_vector(scale)
        bl_obj.scale = (scl.x, scl.y, scl.z)
    
    # 変更を確定
    bpy.context.view_layer.update()
    
    # 結果を返す
    return create_success_response(
        message=f"オブジェクト '{name}' を変換しました",
        data={'object': get_object_data(bl_obj)}
    )

@handle_exceptions
def delete_object(obj, info, name):
    """
    オブジェクトを削除するリゾルバ
    
    Args:
        name: 削除するオブジェクト名
    """
    logger.debug(f"resolve_delete_object が呼び出されました: name={name}")
    
    # オブジェクトの存在確認
    if name not in bpy.data.objects:
        return create_error_response(f"オブジェクト '{name}' が見つかりません")
    
    # オブジェクトを選択し、削除
    obj = bpy.data.objects[name]
    bpy.data.objects.remove(obj)
    
    # 結果を返す
    return create_success_response(message=f"オブジェクト '{name}' を削除しました")

@handle_exceptions
def boolean_operation(obj, info, operation: str, objectName: str, targetName: str, resultName: Optional[str] = None):
    """
    ブーリアン操作を実行
    
    Args:
        operation: 操作タイプ（UNION, DIFFERENCE, INTERSECT）
        objectName: 対象オブジェクト名
        targetName: 操作相手オブジェクト名
        resultName: 結果オブジェクト名（省略時は自動生成）
    """
    logger.debug(f"resolve_boolean_operation が呼び出されました: operation={operation}, object={objectName}, target={targetName}, result={resultName}")
    
    # ブーリアン操作タイプを確認
    if operation not in [BOOLEAN_OPERATION_UNION, BOOLEAN_OPERATION_DIFFERENCE, BOOLEAN_OPERATION_INTERSECT]:
        return create_error_response(f"無効なブーリアン操作タイプ: {operation}")
    
    # オブジェクトの存在確認
    if objectName not in bpy.data.objects:
        return create_error_response(f"オブジェクト '{objectName}' が見つかりません")
    
    if targetName not in bpy.data.objects:
        return create_error_response(f"オブジェクト '{targetName}' が見つかりません")
    
    # オブジェクト取得
    obj1 = bpy.data.objects[objectName]
    obj2 = bpy.data.objects[targetName]
    
    # メッシュタイプ確認
    if obj1.type != 'MESH' or obj2.type != 'MESH':
        return create_error_response("ブーリアン操作はメッシュタイプのオブジェクトのみで実行できます")
    
    # 結果オブジェクト名
    if not resultName:
        resultName = f"{objectName}_{operation.lower()}_{targetName}"
    
    # 現在の選択を保存
    active_obj = bpy.context.active_object
    selection = bpy.context.selected_objects.copy()
    
    # オブジェクトを複製
    bpy.ops.object.select_all(action='DESELECT')
    obj1.select_set(True)
    bpy.context.view_layer.objects.active = obj1
    bpy.ops.object.duplicate()
    result_obj = bpy.context.active_object
    result_obj.name = resultName
    
    # ブーリアンモディファイアを追加
    bool_mod = result_obj.modifiers.new(name="Boolean", type='BOOLEAN')
    bool_mod.object = obj2
    
    # 操作タイプ設定
    if operation == BOOLEAN_OPERATION_UNION:
        bool_mod.operation = 'UNION'
    elif operation == BOOLEAN_OPERATION_DIFFERENCE:
        bool_mod.operation = 'DIFFERENCE'
    elif operation == BOOLEAN_OPERATION_INTERSECT:
        bool_mod.operation = 'INTERSECT'
    
    # モディファイアを適用
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    
    # 元の選択状態を復元
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selection:
        if obj and obj.name in bpy.data.objects:
            obj.select_set(True)
    if active_obj and active_obj.name in bpy.data.objects:
        bpy.context.view_layer.objects.active = active_obj
    
    # 結果を返す
    return create_success_response(
        message=f"ブーリアン操作を実行しました: {operation}",
        data={'object': get_object_data(result_obj)}
    )

@handle_exceptions
def create_material(obj, info, name: Optional[str] = None, baseColor = None, metallic: float = 0.0, roughness: float = 0.5, useNodes: bool = True):
    """
    新規マテリアルを作成
    
    Args:
        name: マテリアル名（省略時は自動生成）
        baseColor: ベースカラー
        metallic: 金属度
        roughness: 粗さ
        useNodes: ノード使用フラグ
    """
    logger.debug(f"resolve_create_material が呼び出されました: name={name}")
    
    # マテリアル名が指定されていない場合は自動生成
    if name is None:
        name = f"Material_{len(bpy.data.materials)}"
    
    # 名前が既に存在する場合は連番を付ける
    base_name = name
    counter = 1
    while name in bpy.data.materials:
        name = f"{base_name}.{counter:03d}"
        counter += 1
    
    # マテリアル作成
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = useNodes
    
    # ベースカラーを設定
    if baseColor:
        color_vec = dict_to_vector(baseColor)
        if mat.use_nodes:
            # ノードベースの場合
            principled_bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if principled_bsdf:
                principled_bsdf.inputs['Base Color'].default_value = (color_vec.x, color_vec.y, color_vec.z, 1.0)
                principled_bsdf.inputs['Metallic'].default_value = metallic
                principled_bsdf.inputs['Roughness'].default_value = roughness
        else:
            # ノードを使用しない場合
            mat.diffuse_color = (color_vec.x, color_vec.y, color_vec.z, 1.0)
    
    logger.info(f"新規マテリアルを作成しました: {name}")
    
    # 結果を返す
    return create_success_response(
        message=f"マテリアルを作成しました: {name}",
        data={'material': resolve_material(obj, info, name)}
    )

@handle_exceptions
def assign_material(obj, info, objectName: str, materialName: str):
    """
    オブジェクトにマテリアルを割り当て
    
    Args:
        objectName: オブジェクト名
        materialName: マテリアル名
    """
    logger.debug(f"resolve_assign_material が呼び出されました: object={objectName}, material={materialName}")
    
    # オブジェクトとマテリアルの存在確認
    if objectName not in bpy.data.objects:
        return create_error_response(f"オブジェクト '{objectName}' が見つかりません")
    
    if materialName not in bpy.data.materials:
        return create_error_response(f"マテリアル '{materialName}' が見つかりません")
    
    # オブジェクトとマテリアル取得
    obj = bpy.data.objects[objectName]
    mat = bpy.data.materials[materialName]
    
    # メッシュタイプのみマテリアルを割り当て可能
    if obj.type != 'MESH':
        return create_error_response(f"オブジェクト '{objectName}' はメッシュタイプではないため、マテリアルを割り当てられません")
    
    # 現在のマテリアルスロットをクリア
    obj.data.materials.clear()
    
    # マテリアルを割り当て
    obj.data.materials.append(mat)
    
    # 結果を返す
    return create_success_response(
        message=f"オブジェクト '{objectName}' にマテリアル '{materialName}' を割り当てました",
        data={'material': resolve_material(obj, info, materialName)}
    )

@handle_exceptions
def textures(obj, info):
    """
    テクスチャ一覧を取得
    """
    logger.debug("resolve_textures が呼び出されました")
    
    textures = []
    for tex in bpy.data.images:
        texture_data = {
            'name': tex.name,
            'type': 'IMAGE',
            'filepath': tex.filepath
        }
        textures.append(texture_data)
    
    return textures

@handle_exceptions
def add_texture(obj, info, materialName: str, texturePath: str, textureType: str = 'color'):
    """
    マテリアルにテクスチャを追加
    
    Args:
        materialName: マテリアル名
        texturePath: テクスチャファイルのパス
        textureType: テクスチャタイプ (color, normal, roughness, etc.)
    """
    logger.debug(f"resolve_add_texture が呼び出されました: material={materialName}, texture={texturePath}, type={textureType}")
    
    # マテリアルの存在確認
    if materialName not in bpy.data.materials:
        return create_error_response(f"マテリアル '{materialName}' が見つかりません")
    
    # テクスチャファイルの存在確認
    import os
    if not os.path.exists(texturePath):
        return create_error_response(f"テクスチャファイル '{texturePath}' が見つかりません")
    
    # マテリアル取得
    mat = bpy.data.materials[materialName]
    
    # マテリアルがノードを使用していない場合は有効化
    if not mat.use_nodes:
        mat.use_nodes = True
    
    # イメージのロード(ファイルが存在すれば名前を基にユニークな名前を使用)
    base_name = os.path.splitext(os.path.basename(texturePath))[0]
    img_name = f"{base_name}_{materialName}_{textureType}"
    
    # 発見し、すでに存在する場合は再利用
    img = None
    for existing_img in bpy.data.images:
        if existing_img.filepath == texturePath:
            img = existing_img
            break
    
    # 存在しない場合はロード
    if not img:
        img = bpy.data.images.load(texturePath)
        img.name = img_name
    
    # ノードツリー取得
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # イメージテクスチャノードを作成
    tex_node = nodes.new('ShaderNodeTexImage')
    tex_node.image = img
    tex_node.label = textureType.capitalize()
    
    # プリンシパルBSDFノードを取得
    principled = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled = node
            break
    
    # プリンシパルBSDFが無い場合は作成
    if not principled:
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        output = None
        
        # 出力ノードを探す
        for node in nodes:
            if node.type == 'OUTPUT_MATERIAL':
                output = node
                break
        
        # 出力ノードが無い場合は作成
        if not output:
            output = nodes.new('ShaderNodeOutputMaterial')
        
        # 出力に接続
        links.new(principled.outputs[0], output.inputs[0])
    
    # テクスチャタイプに応じた接続
    if textureType.lower() == 'color' or textureType.lower() == 'albedo' or textureType.lower() == 'diffuse':
        links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
    elif textureType.lower() == 'normal':
        # 法線を適用するときは法線マップノードが必要
        normal_node = nodes.new('ShaderNodeNormalMap')
        links.new(tex_node.outputs['Color'], normal_node.inputs['Color'])
        links.new(normal_node.outputs['Normal'], principled.inputs['Normal'])
    elif textureType.lower() == 'roughness':
        links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
    elif textureType.lower() == 'metallic':
        links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
    elif textureType.lower() == 'displacement' or textureType.lower() == 'height':
        # 変位を追加するときは変位ノードが必要
        disp_node = nodes.new('ShaderNodeDisplacement')
        links.new(tex_node.outputs['Color'], disp_node.inputs['Height'])
        
        # 出力ノードを探す
        output = None
        for node in nodes:
            if node.type == 'OUTPUT_MATERIAL':
                output = node
                break
                
        if output:
            links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])
    
    # 結果を返す
    return create_success_response(
        message=f"マテリアル '{materialName}' にテクスチャ '{texturePath}' ({textureType}) を追加しました",
        data={'material': resolve_material(obj, info, materialName)}
    )

@handle_exceptions
def search_polyhaven(obj, info, query: Optional[str] = None, category: Optional[str] = None, limit: int = 10):
    """
    Polyhavenアセットを検索
    
    Args:
        query: 検索キーワード
        category: カテゴリフィルタ（hdri, model, texture）
        limit: 取得件数上限
    """
    logger.debug(f"resolve_search_polyhaven が呼び出されました: query={query}, category={category}, limit={limit}")
    
    # Polyhaven APIのURLを構築
    url = "https://api.polyhaven.com/assets"
    
    # リクエストパラメータを作成
    params = {}
    if category:
        # カテゴリでフィルタリング
        params['type'] = category.lower()
    
    try:
        # HTTPリクエストモジュールをインポート
        import urllib.request
        import urllib.parse
        import json
        
        # クエリパラメータがあれば追加
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        
        # HTTPリクエストを実行
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # 結果をフィルタリング（キーワード検索）
        filtered_assets = {}
        if query:
            query_lower = query.lower()
            for asset_id, asset_data in data.items():
                # IDや名前、タグにキーワードが含まれているかチェック
                asset_name = asset_data.get('name', '').lower()
                if query_lower in asset_id.lower() or query_lower in asset_name:
                    filtered_assets[asset_id] = asset_data
                    continue
                
                # タグに含まれているかチェック
                tags = asset_data.get('tags', [])
                for tag in tags:
                    if query_lower in tag.lower():
                        filtered_assets[asset_id] = asset_data
                        break
        else:
            # キーワードがない場合は全件取得
            filtered_assets = data
        
        # 結果を整形して返す
        assets_list = []
        count = 0
        
        for asset_id, asset_data in filtered_assets.items():
            if count >= limit:
                break
                
            thumbnail_url = ""
            # サムネイルリンクがあれば取得
            if 'renders' in asset_data and asset_data['renders']:
                # 最初のレンダーのサムネイルを使用
                render_keys = list(asset_data['renders'].keys())
                if render_keys:
                    first_render = render_keys[0]
                    if 'thumbnails' in asset_data['renders'][first_render]:
                        thumbnail_sizes = asset_data['renders'][first_render]['thumbnails']
                        # 小さめのサムネイルを使用
                        if '256' in thumbnail_sizes:
                            thumbnail_url = f"https://cdn.polyhaven.com/asset_img/thumbs/{asset_id}.png?height=256"
            
            # アセットデータを作成
            asset_info = {
                'id': asset_id,
                'title': asset_data.get('name', asset_id),
                'category': asset_data.get('type', ''),
                'downloadUrl': f"https://api.polyhaven.com/files/{asset_id}",
                'thumbnailUrl': thumbnail_url
            }
            
            assets_list.append(asset_info)
            count += 1
        
        # 結果を返す
        return {
            'totalCount': len(filtered_assets),
            'assets': assets_list
        }
        
    except Exception as e:
        logger.error(f"Polyhaven APIエラー: {str(e)}")
        logger.error(traceback.format_exc())
        return create_error_response(f"Polyhavenアセット検索中にエラーが発生しました: {str(e)}")

@handle_exceptions
def import_polyhaven_asset(obj, info, assetId: str, assetType: str, resolution: str = '2k'):
    """
    Polyhavenアセットをインポート
    
    Args:
        assetId: アセットID
        assetType: アセットタイプ(hdri, model, texture)
        resolution: 解像度(1k, 2k, 4k, 8k)
    """
    logger.debug(f"resolve_import_polyhaven_asset が呼び出されました: id={assetId}, type={assetType}, resolution={resolution}")
    
    # 一時ディレクトリの取得
    import tempfile
    import os
    import urllib.request
    import json
    import zipfile
    import shutil
    
    # 一時ディレクトリを作成
    temp_dir = tempfile.mkdtemp()
    logger.debug(f"一時ディレクトリを作成しました: {temp_dir}")
    
    try:
        # アセット情報を取得
        asset_info_url = f"https://api.polyhaven.com/assets/{assetId}"
        with urllib.request.urlopen(asset_info_url) as response:
            asset_info = json.loads(response.read().decode('utf-8'))
        
        # アセットタイプに応じた処理
        if assetType.lower() == 'hdri':
            return import_polyhaven_hdri(asset_info, assetId, resolution, temp_dir)
        elif assetType.lower() == 'model':
            return import_polyhaven_model(asset_info, assetId, resolution, temp_dir)
        elif assetType.lower() == 'texture':
            return import_polyhaven_texture(asset_info, assetId, resolution, temp_dir)
        else:
            return create_error_response(f"サポートされていないアセットタイプです: {assetType}")
        
    except Exception as e:
        logger.error(f"Polyhavenアセットインポートエラー: {str(e)}")
        logger.error(traceback.format_exc())
        return create_error_response(f"Polyhavenアセットをインポート中にエラーが発生しました: {str(e)}")
    finally:
        # 一時ディレクトリを削除
        try:
            shutil.rmtree(temp_dir)
            logger.debug(f"一時ディレクトリを削除しました: {temp_dir}")
        except Exception as e:
            logger.warning(f"一時ディレクトリの削除に失敗しました: {temp_dir}, エラー: {str(e)}")


def import_polyhaven_hdri(asset_info, asset_id, resolution, temp_dir):
    """
    PolyhavenからHDRIをインポート
    
    Args:
        asset_info: アセット情報
        asset_id: アセットID
        resolution: 解像度
        temp_dir: 一時ディレクトリ
    """

# この関数は既に1029行目付近で定義されているため削除しました

# カメラ関連のリゾルバ関数
@handle_exceptions
def cameras(obj, info):
    """
    カメラ一覧を取得
    """
    logger.debug("resolve_cameras が呼び出されました")
    
    cameras = []
    for cam in bpy.data.cameras:
        # カメラデータを取得
        # 対応するオブジェクトを探す
        cam_obj = None
        for obj in bpy.data.objects:
            if obj.type == 'CAMERA' and obj.data == cam:
                cam_obj = obj
                break
        
        if cam_obj:
            # 回転を度数法に変換
            rot_euler = cam_obj.rotation_euler
            rotation = {
                'x': math.degrees(rot_euler.x),
                'y': math.degrees(rot_euler.y),
                'z': math.degrees(rot_euler.z)
            }
            
            # カメラタイプを確認
            camera_type = "PERSP" if cam.type == 'PERSP' else "ORTHO"
            
            # 視野角の計算
            fov = 0.0
            if camera_type == "PERSP":
                # サイズに応じて計算
                fov = math.degrees(cam.angle)
            
            camera_data = {
                'name': cam_obj.name,
                'location': {
                    'x': cam_obj.location.x,
                    'y': cam_obj.location.y,
                    'z': cam_obj.location.z
                },
                'rotation': rotation,
                'type': camera_type,
                'lens': cam.lens,
                'sensor_width': cam.sensor_width,
                'sensor_height': cam.sensor_height,
                'clip_start': cam.clip_start,
                'clip_end': cam.clip_end,
                'perspective_type': camera_type,
                'fov': fov
            }
            cameras.append(camera_data)
    
    return cameras

@handle_exceptions
def camera(obj, info, name):
    """
    特定のカメラ情報を取得
    
    Args:
        name: カメラ名
    """
    logger.debug(f"resolve_camera が呼び出されました: name={name}")
    
    # カメラオブジェクトの存在確認
    cam_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA' and obj.name == name:
            cam_obj = obj
            break
    
    if not cam_obj:
        raise ValueError(f"カメラ '{name}' が見つかりません")
    
    # カメラデータ取得
    cam = cam_obj.data
    
    # 回転を度数法に変換
    rot_euler = cam_obj.rotation_euler
    rotation = {
        'x': math.degrees(rot_euler.x),
        'y': math.degrees(rot_euler.y),
        'z': math.degrees(rot_euler.z)
    }
    
    # カメラタイプを確認
    camera_type = "PERSP" if cam.type == 'PERSP' else "ORTHO"
    
    # 視野角の計算
    fov = 0.0
    if camera_type == "PERSP":
        fov = math.degrees(cam.angle)
    
    return {
        'name': cam_obj.name,
        'location': {
            'x': cam_obj.location.x,
            'y': cam_obj.location.y,
            'z': cam_obj.location.z
        },
        'rotation': rotation,
        'type': camera_type,
        'lens': cam.lens,
        'sensor_width': cam.sensor_width,
        'sensor_height': cam.sensor_height,
        'clip_start': cam.clip_start,
        'clip_end': cam.clip_end,
        'perspective_type': camera_type,
        'fov': fov
    }

@handle_exceptions
def create_camera(obj, info, name=None, location=None, rotation=None, type="PERSP", lens=50.0, clip_start=0.1, clip_end=100.0):
    """
    新規カメラを作成
    
    Args:
        name: カメラ名（省略時は自動生成）
        location: 位置
        rotation: 回転（度数法）
        type: カメラタイプ（PERSP/ORTHO）
        lens: 焦点距離
        clip_start: クリップ開始
        clip_end: クリップ終了
    """
    logger.debug(f"resolve_create_camera が呼び出されました: name={name}, type={type}")
    
    # カメラデータ作成
    cam = bpy.data.cameras.new(name=name or "Camera")
    
    # カメラタイプ設定
    cam.type = type
    cam.lens = lens
    cam.clip_start = clip_start
    cam.clip_end = clip_end
    
    # カメラオブジェクト作成
    cam_obj = bpy.data.objects.new(name or "Camera", cam)
    
    # シーンにリンク
    bpy.context.collection.objects.link(cam_obj)
    
    # 位置、回転設定
    if location:
        location_vec = dict_to_vector(location)
        cam_obj.location = (location_vec.x, location_vec.y, location_vec.z)
    
    if rotation:
        rotation_vec = dict_to_vector(rotation)
        # 度数法からラジアンに変換
        cam_obj.rotation_euler = (math.radians(rotation_vec.x), math.radians(rotation_vec.y), math.radians(rotation_vec.z))
    
    # 作成したカメラの情報を返す
    return create_success_response(
        message=f"カメラを作成しました: {cam_obj.name}",
        data={'camera': resolve_camera(obj, info, cam_obj.name)}
    )

@handle_exceptions
def update_camera(obj, info, name, location=None, rotation=None, lens=None, clip_start=None, clip_end=None):
    """
    既存カメラを編集
    
    Args:
        name: カメラ名
        location: 新しい位置
        rotation: 新しい回転（度数法）
        lens: 新しい焦点距離
        clip_start: 新しいクリップ開始
        clip_end: 新しいクリップ終了
    """
    logger.debug(f"resolve_update_camera が呼び出されました: name={name}")
    
    # カメラオブジェクトの存在確認
    cam_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA' and obj.name == name:
            cam_obj = obj
            break
    
    if not cam_obj:
        return create_error_response(f"カメラ '{name}' が見つかりません")
    
    cam = cam_obj.data
    
    # 各パラメータを更新
    if location:
        location_vec = dict_to_vector(location)
        cam_obj.location = (location_vec.x, location_vec.y, location_vec.z)
    
    if rotation:
        rotation_vec = dict_to_vector(rotation)
        # 度数法からラジアンに変換
        cam_obj.rotation_euler = (math.radians(rotation_vec.x), math.radians(rotation_vec.y), math.radians(rotation_vec.z))
    
    if lens is not None:
        cam.lens = lens
    
    if clip_start is not None:
        cam.clip_start = clip_start
    
    if clip_end is not None:
        cam.clip_end = clip_end
    
    # 更新したカメラの情報を返す
    return create_success_response(
        message=f"カメラを更新しました: {name}",
        data={'camera': resolve_camera(obj, info, name)}
    )

@handle_exceptions
def delete_camera(obj, info, name):
    """
    カメラを削除
    
    Args:
        name: カメラ名
    """
    logger.debug(f"resolve_delete_camera が呼び出されました: name={name}")
    
    # カメラオブジェクトの存在確認
    cam_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA' and obj.name == name:
            cam_obj = obj
            break
    
    if not cam_obj:
        return create_error_response(f"カメラ '{name}' が見つかりません")
    
    # カメラデータを保存
    cam_data = resolve_camera(obj, info, name)
    
    # カメラオブジェクトとデータを削除
    cam = cam_obj.data
    bpy.data.objects.remove(cam_obj)
    bpy.data.cameras.remove(cam)
    
    # 削除したカメラの情報を返す
    return create_success_response(
        message=f"カメラを削除しました: {name}",
        data={'camera': cam_data}
    )

# ライト関連のリゾルバ関数
@handle_exceptions
def lights(obj, info):
    """
    ライト一覧を取得
    """
    logger.debug("resolve_lights が呼び出されました")
    
    lights = []
    for light in bpy.data.lights:
        # 対応するオブジェクトを探す
        light_obj = None
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT' and obj.data == light:
                light_obj = obj
                break
        
        if light_obj:
            # 回転を度数法に変換
            rot_euler = light_obj.rotation_euler
            rotation = {
                'x': math.degrees(rot_euler.x),
                'y': math.degrees(rot_euler.y),
                'z': math.degrees(rot_euler.z)
            }
            
            # 色情報を取得
            color = {
                'x': light.color[0],
                'y': light.color[1],
                'z': light.color[2]
            }
            
            light_data = {
                'name': light_obj.name,
                'type': light.type,
                'location': {
                    'x': light_obj.location.x,
                    'y': light_obj.location.y,
                    'z': light_obj.location.z
                },
                'rotation': rotation,
                'color': color,
                'energy': light.energy,
                'shadow': light.use_shadow,
                'size': getattr(light, 'size', 0.0) if hasattr(light, 'size') else 0.0
            }
            lights.append(light_data)
    
    return lights

@handle_exceptions
def light(obj, info, name):
    """
    特定のライト情報を取得
    
    Args:
        name: ライト名
    """
    logger.debug(f"resolve_light が呼び出されました: name={name}")
    
    # ライトオブジェクトの存在確認
    light_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT' and obj.name == name:
            light_obj = obj
            break
    
    if not light_obj:
        raise ValueError(f"ライト '{name}' が見つかりません")
    
    # ライトデータ取得
    light = light_obj.data
    
    # 回転を度数法に変換
    rot_euler = light_obj.rotation_euler
    rotation = {
        'x': math.degrees(rot_euler.x),
        'y': math.degrees(rot_euler.y),
        'z': math.degrees(rot_euler.z)
    }
    
    # 色情報を取得
    color = {
        'x': light.color[0],
        'y': light.color[1],
        'z': light.color[2]
    }
    
    return {
        'name': light_obj.name,
        'type': light.type,
        'location': {
            'x': light_obj.location.x,
            'y': light_obj.location.y,
            'z': light_obj.location.z
        },
        'rotation': rotation,
        'color': color,
        'energy': light.energy,
        'shadow': light.use_shadow,
        'size': getattr(light, 'size', 0.0) if hasattr(light, 'size') else 0.0
    }

@handle_exceptions
def create_light(obj, info, name=None, type="POINT", location=None, rotation=None, color=None, energy=10.0, shadow=True):
    """
    新規ライトを作成
    
    Args:
        name: ライト名（省略時は自動生成）
        type: ライトタイプ（POINT/SUN/SPOT/AREA）
        location: 位置
        rotation: 回転（度数法）
        color: 色
        energy: 強度
        shadow: シャドウフラグ
    """
    logger.debug(f"resolve_create_light が呼び出されました: name={name}, type={type}")
    
    # ライトタイプを確認
    valid_types = ['POINT', 'SUN', 'SPOT', 'AREA']
    if type not in valid_types:
        return create_error_response(f"無効なライトタイプ: {type}, 有効なタイプは {', '.join(valid_types)}")
    
    # ライトデータ作成
    light = bpy.data.lights.new(name=name or f"Light_{type}", type=type)
    
    # ライト設定
    light.energy = energy
    light.use_shadow = shadow
    
    if color:
        color_vec = dict_to_vector(color)
        light.color = (color_vec.x, color_vec.y, color_vec.z)
    
    # ライトオブジェクト作成
    light_obj = bpy.data.objects.new(name or f"Light_{type}", light)
    
    # シーンにリンク
    bpy.context.collection.objects.link(light_obj)
    
    # 位置、回転設定
    if location:
        location_vec = dict_to_vector(location)
        light_obj.location = (location_vec.x, location_vec.y, location_vec.z)
    
    if rotation:
        rotation_vec = dict_to_vector(rotation)
        # 度数法からラジアンに変換
        light_obj.rotation_euler = (math.radians(rotation_vec.x), math.radians(rotation_vec.y), math.radians(rotation_vec.z))
    
    # 作成したライトの情報を返す
    return create_success_response(
        message=f"ライトを作成しました: {light_obj.name}",
        data={'light': resolve_light(obj, info, light_obj.name)}
    )

@handle_exceptions
def update_light(obj, info, name, location=None, rotation=None, color=None, energy=None, shadow=None):
    """
    既存ライトを編集
    
    Args:
        name: ライト名
        location: 新しい位置
        rotation: 新しい回転（度数法）
        color: 新しい色
        energy: 新しい強度
        shadow: 新しいシャドウフラグ
    """
    logger.debug(f"resolve_update_light が呼び出されました: name={name}")
    
    # ライトオブジェクトの存在確認
    light_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT' and obj.name == name:
            light_obj = obj
            break
    
    if not light_obj:
        return create_error_response(f"ライト '{name}' が見つかりません")
    
    light = light_obj.data
    
    # 各パラメータを更新
    if location:
        location_vec = dict_to_vector(location)
        light_obj.location = (location_vec.x, location_vec.y, location_vec.z)
    
    if rotation:
        rotation_vec = dict_to_vector(rotation)
        # 度数法からラジアンに変換
        light_obj.rotation_euler = (math.radians(rotation_vec.x), math.radians(rotation_vec.y), math.radians(rotation_vec.z))
    
    if color:
        color_vec = dict_to_vector(color)
        light.color = (color_vec.x, color_vec.y, color_vec.z)
    
    if energy is not None:
        light.energy = energy
    
    if shadow is not None:
        light.use_shadow = shadow
    
    # 更新したライトの情報を返す
    return create_success_response(
        message=f"ライトを更新しました: {name}",
        data={'light': resolve_light(obj, info, name)}
    )

@handle_exceptions
def delete_light(obj, info, name):
    """
    ライトを削除
    
    Args:
        name: ライト名
    """
    logger.debug(f"resolve_delete_light が呼び出されました: name={name}")
    
    # ライトオブジェクトの存在確認
    light_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT' and obj.name == name:
            light_obj = obj
            break
    
    if not light_obj:
        return create_error_response(f"ライト '{name}' が見つかりません")
    
    # ライトデータを保存
    light_data = resolve_light(obj, info, name)
    
    # ライトオブジェクトとデータを削除
    light = light_obj.data
    bpy.data.objects.remove(light_obj)
    bpy.data.lights.remove(light)
    
    # 削除したライトの情報を返す
    return create_success_response(
        message=f"ライトを削除しました: {name}",
        data={'light': light_data}
    )

# レンダリング関連のリゾルバ関数
@handle_exceptions
def render_settings(obj, info):
    """
    現在のレンダリング設定を取得
    """
    logger.debug("resolve_render_settings が呼び出されました")
    
    render = bpy.context.scene.render
    
    # レンダリングエンジンによって返す値を変更
    samples = 0
    if render.engine == 'CYCLES':
        samples = bpy.context.scene.cycles.samples
    elif render.engine == 'BLENDER_EEVEE':
        samples = bpy.context.scene.eevee.taa_render_samples
    
    return {
        'engine': render.engine,
        'resolution_x': render.resolution_x,
        'resolution_y': render.resolution_y,
        'resolution_percentage': render.resolution_percentage,
        'file_format': render.image_settings.file_format,
        'filepath': bpy.context.scene.render.filepath,
        'use_motion_blur': getattr(render, 'use_motion_blur', False),
        'samples': samples
    }

@handle_exceptions
def update_render_settings(obj, info, engine=None, resolution_x=None, resolution_y=None, resolution_percentage=None, file_format=None, filepath=None, samples=None):
    """
    レンダリング設定を更新
    
    Args:
        engine: レンダーエンジン（CYCLES/EEVEE/WORKBENCH）
        resolution_x: X解像度
        resolution_y: Y解像度
        resolution_percentage: 解像度パーセンテージ
        file_format: ファイルフォーマット
        filepath: 出力ファイルパス
        samples: サンプル数
    """
    logger.debug(f"resolve_update_render_settings が呼び出されました")
    
    render = bpy.context.scene.render
    
    # エンジンを設定
    valid_engines = ['CYCLES', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH']
    if engine is not None:
        if engine in valid_engines:
            render.engine = engine
        else:
            return create_error_response(f"無効なレンダーエンジン: {engine}, 有効なエンジンは {', '.join(valid_engines)}")
    
    # 解像度設定
    if resolution_x is not None:
        render.resolution_x = resolution_x
    
    if resolution_y is not None:
        render.resolution_y = resolution_y
    
    if resolution_percentage is not None:
        render.resolution_percentage = resolution_percentage
    
    # ファイル形式設定
    if file_format is not None:
        render.image_settings.file_format = file_format
    
    # 出力パス設定
    if filepath is not None:
        render.filepath = filepath
    
    # サンプル数設定
    if samples is not None:
        if render.engine == 'CYCLES':
            bpy.context.scene.cycles.samples = samples
        elif render.engine == 'BLENDER_EEVEE':
            bpy.context.scene.eevee.taa_render_samples = samples
    
    # 更新後の設定を返す
    return create_success_response(
        message="レンダリング設定を更新しました",
        data={'settings': resolve_render_settings(obj, info)}
    )

@handle_exceptions
def render_frame(obj, info, filepath=None, frame=None):
    """
    レンダリングを実行
    
    Args:
        filepath: 出力ファイルパス（省略時は現在の設定を使用）
        frame: レンダリングするフレーム番号（省略時は現在のフレーム）
    """
    logger.debug(f"resolve_render_frame が呼び出されました: filepath={filepath}, frame={frame}")
    
    # 元の設定を保存
    original_filepath = bpy.context.scene.render.filepath
    original_frame = bpy.context.scene.frame_current
    
    try:
        # ファイルパスが指定されていれば設定
        if filepath:
            bpy.context.scene.render.filepath = filepath
        
        # フレーム番号が指定されていれば設定
        if frame is not None:
            bpy.context.scene.frame_set(frame)
        
        # レンダリング実行
        bpy.ops.render.render(write_still=True)
        
        # 実際に使用されたファイルパスを取得
        actual_filepath = bpy.context.scene.render.filepath
        
        # 結果を返す
        return create_success_response(
            message=f"レンダリングを実行しました: フレーム={bpy.context.scene.frame_current}",
            data={
                'filepath': actual_filepath,
                'settings': resolve_render_settings(obj, info)
            }
        )
    finally:
        # 元の設定を復元
        bpy.context.scene.render.filepath = original_filepath
        bpy.context.scene.frame_set(original_frame)

# モディファイアー関連のリゾルバ関数
@handle_exceptions
def modifiers(obj, info, object_name):
    """
    指定オブジェクトのモディファイアー一覧を取得
    
    Args:
        object_name: オブジェクト名
    """
    logger.debug(f"resolve_modifiers が呼び出されました: object_name={object_name}")
    
    # オブジェクトの存在確認
    if object_name not in bpy.data.objects:
        raise ValueError(f"オブジェクト '{object_name}' が見つかりません")
    
    obj = bpy.data.objects[object_name]
    modifiers = []
    
    for mod in obj.modifiers:
        # 共通プロパティ
        modifier = {
            'name': mod.name,
            'type': mod.type,
            'show_viewport': mod.show_viewport,
            'show_render': mod.show_render
        }
        
        # タイプ別の追加プロパティ
        if mod.type == 'SUBSURF':
            modifier['levels'] = mod.levels
            modifier['render_levels'] = mod.render_levels
        elif mod.type == 'BEVEL':
            modifier['width'] = mod.width
            modifier['segments'] = mod.segments
        elif mod.type == 'MIRROR':
            modifier['use_axis'] = [
                mod.use_axis[0],
                mod.use_axis[1],
                mod.use_axis[2]
            ]
        elif mod.type == 'SOLIDIFY':
            modifier['thickness'] = mod.thickness
        elif mod.type == 'ARRAY':
            modifier['count'] = mod.count
            modifier['relative_offset_displace'] = [
                mod.relative_offset_displace[0],
                mod.relative_offset_displace[1],
                mod.relative_offset_displace[2]
            ]
        
        modifiers.append(modifier)
    
    return modifiers

@handle_exceptions
def add_modifier(obj, info, object_name, mod_type, mod_name=None):
    """
    オブジェクトにモディファイアーを追加
    
    Args:
        object_name: オブジェクト名
        mod_type: モディファイアータイプ
        mod_name: モディファイアー名（省略時はタイプから自動生成）
    """
    logger.debug(f"resolve_add_modifier が呼び出されました: object_name={object_name}, mod_type={mod_type}, mod_name={mod_name}")
    
    # オブジェクトの存在確認
    if object_name not in bpy.data.objects:
        return create_error_response(f"オブジェクト '{object_name}' が見つかりません")
    
    # オブジェクト取得
    obj = bpy.data.objects[object_name]
    
    # 指定されたモディファイアータイプが合法か確認
    try:
        # モディファイアー追加
        modifier = obj.modifiers.new(name=mod_name or mod_type, type=mod_type)
    except Exception as e:
        return create_error_response(f"モディファイアー追加エラー: {str(e)}")
    
    # 追加したモディファイアーの情報を返す
    return create_success_response(
        message=f"モディファイアーを追加しました: {modifier.name} ({mod_type})",
        data={
            'object_name': object_name,
            'modifier': {
                'name': modifier.name,
                'type': modifier.type,
                'show_viewport': modifier.show_viewport,
                'show_render': modifier.show_render
            }
        }
    )

@handle_exceptions
def update_modifier(obj, info, object_name, mod_name, params):
    """
    モディファイアーの設定を更新
    
    Args:
        object_name: オブジェクト名
        mod_name: モディファイアー名
        params: 更新するパラメータの辞書
    """
    logger.debug(f"resolve_update_modifier が呼び出されました: object_name={object_name}, mod_name={mod_name}")
    
    # オブジェクトの存在確認
    if object_name not in bpy.data.objects:
        return create_error_response(f"オブジェクト '{object_name}' が見つかりません")
    
    obj = bpy.data.objects[object_name]
    
    # モディファイアーの存在確認
    if mod_name not in obj.modifiers:
        return create_error_response(f"モディファイアー '{mod_name}' が見つかりません")
    
    modifier = obj.modifiers[mod_name]
    
    # パラメータを更新
    updates = []
    for param_name, param_value in params.items():
        try:
            if hasattr(modifier, param_name):
                # ログ出力
                logger.debug(f"パラメータ更新: {param_name} = {param_value}")
                
                # リスト組やタプル組の場合の特別処理
                current_value = getattr(modifier, param_name)
                if isinstance(current_value, (list, tuple)) and isinstance(param_value, (list, dict)):
                    # 辞書の場合はインデックスから値を取得
                    if isinstance(param_value, dict):
                        for idx, val in param_value.items():
                            current_value[int(idx)] = val
                    # リストの場合は直接変換
                    else:
                        new_value = [float(v) for v in param_value]
                        setattr(modifier, param_name, new_value)
                else:
                    # 通常パラメータの場合
                    setattr(modifier, param_name, param_value)
                
                # 更新成功のログ
                updates.append(param_name)
            else:
                logger.warning(f"無効なパラメータ: {param_name}")
        except Exception as e:
            logger.error(f"パラメータ更新エラー ({param_name}): {str(e)}")
    
    # 更新したモディファイアーの情報を返す
    return create_success_response(
        message=f"モディファイアーを更新しました: {mod_name} (変更: {', '.join(updates)})",
        data={
            'object_name': object_name,
            'modifier': {
                'name': modifier.name,
                'type': modifier.type,
                'show_viewport': modifier.show_viewport,
                'show_render': modifier.show_render,
                'updated_params': updates
            }
        }
    )

@handle_exceptions
def apply_modifier(obj, info, object_name, mod_name):
    """
    モディファイアーを適用
    
    Args:
        object_name: オブジェクト名
        mod_name: モディファイアー名
    """
    logger.debug(f"resolve_apply_modifier が呼び出されました: object_name={object_name}, mod_name={mod_name}")
    
    # オブジェクトの存在確認
    if object_name not in bpy.data.objects:
        return create_error_response(f"オブジェクト '{object_name}' が見つかりません")
    
    obj = bpy.data.objects[object_name]
    
    # モディファイアーの存在確認
    if mod_name not in obj.modifiers:
        return create_error_response(f"モディファイアー '{mod_name}' が見つかりません")
    
    # モディファイアーの情報を記録
    mod_info = {
        'name': mod_name,
        'type': obj.modifiers[mod_name].type
    }
    
    # 現在のコンテキストを定義
    override = bpy.context.copy()
    override["object"] = obj
    override["modifier"] = obj.modifiers[mod_name]
    
    try:
        # モディファイアーを適用
        bpy.ops.object.modifier_apply(override, modifier=mod_name)
        
        # 成功の場合のレスポンス
        return create_success_response(
            message=f"モディファイアーを適用しました: {mod_info['name']} ({mod_info['type']})",
            data={
                'object_name': object_name,
                'modifier': mod_info
            }
        )
    except Exception as e:
        return create_error_response(f"モディファイアー適用エラー: {str(e)}")

@handle_exceptions
def delete_modifier(obj, info, object_name, mod_name):
    """
    モディファイアーを削除
    
    Args:
        object_name: オブジェクト名
        mod_name: モディファイアー名
    """
    logger.debug(f"resolve_delete_modifier が呼び出されました: object_name={object_name}, mod_name={mod_name}")
    
    # オブジェクトの存在確認
    if object_name not in bpy.data.objects:
        return create_error_response(f"オブジェクト '{object_name}' が見つかりません")
    
    obj = bpy.data.objects[object_name]
    
    # モディファイアーの存在確認
    if mod_name not in obj.modifiers:
        return create_error_response(f"モディファイアー '{mod_name}' が見つかりません")
    
    # モディファイアーの情報を記録
    mod_type = obj.modifiers[mod_name].type
    
    # モディファイアーを削除
    obj.modifiers.remove(obj.modifiers[mod_name])
    
    # 削除したモディファイアーの情報を返す
    return create_success_response(
        message=f"モディファイアーを削除しました: {mod_name} ({mod_type})",
        data={
            'object_name': object_name,
            'modifier': {
                'name': mod_name,
                'type': mod_type
            }
        }
    )

def import_polyhaven_texture(asset_info, asset_id, resolution, temp_dir):
    """
    Polyhavenからテクスチャをインポート
    
    Args:
        asset_info: アセット情報
        asset_id: アセットID
        resolution: 解像度
        temp_dir: 一時ディレクトリ
    """
    import os
    import urllib.request
    import zipfile
    import json
    
    # 解像度のフォーマットを確認
    if resolution not in ['1k', '2k', '4k', '8k']:
        resolution = '2k'  # デフォルトは2k
    
    # テクスチャファイルのURLを取得
    texture_files_url = f"https://api.polyhaven.com/files/{asset_id}"
    
    try:
        # ファイル情報を取得
        with urllib.request.urlopen(texture_files_url) as response:
            files_info = json.loads(response.read().decode('utf-8'))
        
        # 解像度とファイルタイプを確認
        texture_maps = {}
        if 'Texture' in files_info:
            texture_files = files_info['Texture']
            # 解像度を確認
            if resolution in texture_files:
                maps = texture_files[resolution]
                # 各マップタイプのURLを取得
                for map_type, map_url in maps.items():
                    # JPGファイルを優先するが、存在しない場合はPNGを使用
                    if map_type.endswith('_jpg'):
                        base_type = map_type[:-4]  # _jpgを削除
                        texture_maps[base_type] = map_url
                    elif map_type.endswith('_png') and not map_type[:-4] in texture_maps:
                        base_type = map_type[:-4]  # _pngを削除
                        texture_maps[base_type] = map_url
        
        if not texture_maps:
            return create_error_response(f"適切なテクスチャマップが見つかりません: {asset_id}, {resolution}")
        
        # マテリアルを作成
        material_name = f"{asset_id}_{resolution}"
        
        # 既存マテリアルを確認
        existing_mat = None
        for mat in bpy.data.materials:
            if mat.name == material_name or mat.name.startswith(f"{material_name}."):
                existing_mat = mat
                break
        
        # マテリアルが存在しない場合は新規作成
        if not existing_mat:
            mat = bpy.data.materials.new(name=material_name)
        else:
            mat = existing_mat
        
        # ノードを有効化
        mat.use_nodes = True
        
        # ノードツリーを取得
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # 初期化
        if not existing_mat:
            # ノードをクリア
            nodes.clear()
            
            # Principled BSDFを作成
            principled = nodes.new('ShaderNodeBsdfPrincipled')
            principled.location = (0, 0)
            
            # 出力ノードを作成
            output = nodes.new('ShaderNodeOutputMaterial')
            output.location = (300, 0)
            
            # ノードを接続
            links.new(principled.outputs[0], output.inputs[0])
        else:
            # 既存ノードを再利用
            principled = None
            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled = node
                    break
            
            if not principled:
                # Principled BSDFがない場合はマテリアルをリセット
                nodes.clear()
                principled = nodes.new('ShaderNodeBsdfPrincipled')
                principled.location = (0, 0)
                output = nodes.new('ShaderNodeOutputMaterial')
                output.location = (300, 0)
                links.new(principled.outputs[0], output.inputs[0])
        
        # テクスチャをダウンロードして適用
        loaded_maps = {}
        for map_type, map_url in texture_maps.items():
            # ファイル拡張子をチェック
            file_ext = '.jpg' if map_url.endswith('.jpg') else '.png'
            map_filename = f"{asset_id}_{resolution}_{map_type}{file_ext}"
            map_filepath = os.path.join(temp_dir, map_filename)
            
            # テクスチャをダウンロード
            urllib.request.urlretrieve(map_url, map_filepath)
            logger.debug(f"テクスチャをダウンロードしました: {map_filepath}")
            
            # 画像をロード
            img_name = f"{asset_id}_{resolution}_{map_type}"
            
            # 既存画像を確認
            existing_img = None
            for img in bpy.data.images:
                if img.name == img_name or img.name.startswith(f"{img_name}."):
                    existing_img = img
                    break
            
            # 画像をロード
            if existing_img:
                existing_img.filepath = map_filepath
                existing_img.reload()
                img = existing_img
            else:
                img = bpy.data.images.load(map_filepath)
                img.name = img_name
            
            # 画像情報を保存
            loaded_maps[map_type] = {
                'image': img,
                'path': map_filepath
            }
        
        # マップタイプに応じてノードを追加
        map_nodes = {}
        for map_type, map_data in loaded_maps.items():
            # テクスチャノードを作成
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = map_data['image']
            tex_node.label = map_type.capitalize()
            
            # ノード位置を設定
            y_offset = len(map_nodes) * -300
            tex_node.location = (-300, y_offset)
            
            map_nodes[map_type] = tex_node
        
        # マップを接続
        # カラー/アルベドマップ
        if 'diffuse' in map_nodes or 'albedo' in map_nodes or 'color' in map_nodes:
            color_node = map_nodes.get('diffuse') or map_nodes.get('albedo') or map_nodes.get('color')
            links.new(color_node.outputs['Color'], principled.inputs['Base Color'])
        
        # 法線マップ
        if 'nor' in map_nodes or 'normal' in map_nodes:
            normal_node = map_nodes.get('nor') or map_nodes.get('normal')
            normal_map_node = nodes.new('ShaderNodeNormalMap')
            normal_map_node.location = (-100, -100)
            links.new(normal_node.outputs['Color'], normal_map_node.inputs['Color'])
            links.new(normal_map_node.outputs['Normal'], principled.inputs['Normal'])
        
        # 粗さマップ
        if 'rough' in map_nodes:
            links.new(map_nodes['rough'].outputs['Color'], principled.inputs['Roughness'])
        
        # 金属マップ
        if 'metal' in map_nodes:
            links.new(map_nodes['metal'].outputs['Color'], principled.inputs['Metallic'])
        
        # 高さ/変位マップ
        if 'disp' in map_nodes or 'height' in map_nodes:
            disp_node = map_nodes.get('disp') or map_nodes.get('height')
            
            # 変位ノードを作成
            displace_node = nodes.new('ShaderNodeDisplacement')
            displace_node.location = (0, -300)
            
            # 接続
            links.new(disp_node.outputs['Color'], displace_node.inputs['Height'])
            
            # 出力ノードを探す
            output = None
            for node in nodes:
                if node.type == 'OUTPUT_MATERIAL':
                    output = node
                    break
            
            if output:
                links.new(displace_node.outputs['Displacement'], output.inputs['Displacement'])
        
        # 結果を返す
        return create_success_response(
            message=f"テクスチャ '{asset_id}' ({resolution}) をインポートし、マテリアル '{material_name}' を作成しました",
            data={
                'material': {
                    'name': material_name,
                    'type': 'texture',
                    'maps': list(loaded_maps.keys())
                }
            }
        )
    
    except Exception as e:
        logger.error(f"テクスチャインポートエラー: {str(e)}")
        return create_error_response(f"テクスチャのインポートに失敗しました: {str(e)}")

def import_polyhaven_model(asset_info, asset_id, resolution, temp_dir):
    """
    Polyhavenからモデルをインポート
    
    Args:
        asset_info: アセット情報
        asset_id: アセットID
        resolution: 解像度(テクスチャ用)
        temp_dir: 一時ディレクトリ
    """
    import os
    import urllib.request
    import zipfile
    import tempfile
    import json
    
    try:
        # モデルファイルのURLを取得
        model_url = None
        if 'files' in asset_info and 'blend' in asset_info['files']:
            # Blenderファイルがあれば優先して使用
            blend_files = asset_info['files']['blend']
            if 'blend' in blend_files:
                model_url = blend_files['blend']
        
        # OBJファイルを代替として使用
        if not model_url and 'files' in asset_info and 'obj' in asset_info['files']:
            obj_files = asset_info['files']['obj']
            if 'obj' in obj_files:
                model_url = obj_files['obj']
            
        if not model_url and 'files' in asset_info and 'fbx' in asset_info['files']:
            fbx_files = asset_info['files']['fbx']
            if 'fbx' in fbx_files:
                model_url = fbx_files['fbx']
        
        if not model_url:
            return create_error_response(f"モデルファイルが見つかりません: {asset_id}")
        
        # ファイル拡張子をチェック
        file_ext = os.path.splitext(model_url)[1]
        model_filename = f"{asset_id}{file_ext}"
        model_filepath = os.path.join(temp_dir, model_filename)
        
        # モデルをダウンロード
        urllib.request.urlretrieve(model_url, model_filepath)
        logger.debug(f"モデルをダウンロードしました: {model_filepath}")
        
        # ファイルタイプに応じたインポート処理
        model_objects = []
        
        # 現在の選択状態を保存
        active_obj = bpy.context.active_object
        selection = bpy.context.selected_objects.copy()
        
        # 選択を解除
        bpy.ops.object.select_all(action='DESELECT')
        
        # ファイルタイプに応じたインポート
        if file_ext.lower() == '.blend':
            # Blenderファイルの場合、オブジェクトをリンク
            with bpy.data.libraries.load(model_filepath, link=False) as (data_from, data_to):
                data_to.objects = data_from.objects
            
            # オブジェクトをシーンに追加
            for obj in data_to.objects:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
                    obj.select_set(True)
                    model_objects.append(obj.name)
        
        elif file_ext.lower() == '.obj':
            # OBJファイルをインポート
            bpy.ops.import_scene.obj(filepath=model_filepath)
            
            # 新規追加されたオブジェクトを取得
            for obj in bpy.context.selected_objects:
                model_objects.append(obj.name)
        
        elif file_ext.lower() == '.fbx':
            # FBXファイルをインポート
            bpy.ops.import_scene.fbx(filepath=model_filepath)
            
            # 新規追加されたオブジェクトを取得
            for obj in bpy.context.selected_objects:
                model_objects.append(obj.name)
        
        # テクスチャもインポートする場合はマテリアルを作成して適用
        material_name = None
        if resolution != 'none':
            try:
                texture_result = import_polyhaven_texture(asset_info, asset_id, resolution, temp_dir)
                if texture_result and 'success' in texture_result and texture_result['success']:
                    if 'material' in texture_result and 'name' in texture_result['material']:
                        material_name = texture_result['material']['name']
                    
                        # マテリアルを全てのメッシュオブジェクトに適用
                        if material_name:
                            mat = bpy.data.materials.get(material_name)
                            if mat:
                                for obj_name in model_objects:
                                    obj = bpy.data.objects.get(obj_name)
                                    if obj and obj.type == 'MESH':
                                        # マテリアルスロットをクリア
                                        obj.data.materials.clear()
                                        # マテリアルを追加
                                        obj.data.materials.append(mat)
            except Exception as tex_err:
                logger.warning(f"テクスチャの適用中にエラーが発生しました: {str(tex_err)}")
        
        # 元の選択状態を復元
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selection:
            if obj and obj.name in bpy.data.objects:
                obj.select_set(True)
        if active_obj and active_obj.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = active_obj
        
        # 結果を返す
        return create_success_response(
            message=f"モデル '{asset_id}' をインポートしました",
            data={
                'objects': model_objects,
                'material': material_name
            }
        )
        
    except Exception as e:
        logger.error(f"モデルインポートエラー: {str(e)}")
        return create_error_response(f"モデルのインポートに失敗しました: {str(e)}")

    import os
    import urllib.request
    
    # 解像度のフォーマットを確認
    if resolution not in ['1k', '2k', '4k', '8k', '16k']:
        resolution = '2k'  # デフォルトは2k
    
    # ファイルのURLを取得
    hdri_url = None
    if 'files' in asset_info and 'hdri' in asset_info['files']:
        hdri_files = asset_info['files']['hdri']
        # 指定された解像度があるか確認
        if resolution in hdri_files:
            hdri_data = hdri_files[resolution]
            if 'hdr' in hdri_data:
                hdri_url = hdri_data['hdr']
        
        # 指定された解像度がない場合は使用可能な解像度を使用
        if not hdri_url:
            available_resolutions = list(hdri_files.keys())
            if available_resolutions:
                # 使用可能な中で最も高い解像度を使用
                for res in ['2k', '1k', '4k', '8k', '16k']: 
                    if res in available_resolutions and 'hdr' in hdri_files[res]:
                        hdri_url = hdri_files[res]['hdr']
                        break
    
    if not hdri_url:
        return create_error_response(f"HDRIファイルが見つかりません: {asset_id}")
    
    # HDRIファイルをダウンロード
    hdri_filename = f"{asset_id}_{resolution}.hdr"
    hdri_filepath = os.path.join(temp_dir, hdri_filename)
    
    try:
        # ファイルをダウンロード
        urllib.request.urlretrieve(hdri_url, hdri_filepath)
        logger.debug(f"HDRIファイルをダウンロードしました: {hdri_filepath}")
        
        # ワールドに設定
        hdri_name = f"{asset_id}_{resolution}"
        
        # 既存イメージを確認
        existing_img = None
        for img in bpy.data.images:
            if img.name == hdri_name or img.name.startswith(f"{hdri_name}."):
                existing_img = img
                break
        
        # 新規イメージを読み込み
        if existing_img:
            # 既存イメージを再ロード
            existing_img.filepath = hdri_filepath
            existing_img.reload()
            img = existing_img
        else:
            # 新規イメージをロード
            img = bpy.data.images.load(hdri_filepath)
            img.name = hdri_name
        
        # 現在のワールド設定を保存
        world = bpy.context.scene.world
        if not world:
            # ワールドがない場合は作成
            world = bpy.data.worlds.new(name=f"World_{asset_id}")
            bpy.context.scene.world = world
        
        # ワールドのノードを有効化
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        
        # ノードをクリアして新しいノードを作成
        nodes.clear()
        
        # ノードを追加
        tex_env = nodes.new('ShaderNodeTexEnvironment')
        tex_env.image = img
        tex_env.location = (-300, 0)
        
        background = nodes.new('ShaderNodeBackground')
        background.location = (0, 0)
        
        output = nodes.new('ShaderNodeOutputWorld')
        output.location = (300, 0)
        
        # ノードを接続
        links.new(tex_env.outputs['Color'], background.inputs['Color'])
        links.new(background.outputs['Background'], output.inputs['Surface'])
        
        # HDRIの強度を設定
        background.inputs['Strength'].default_value = 1.0
        
        # 当面のワールド設定を反映させる
        bpy.context.view_layer.update()
        
        # 結果を返す
        return create_success_response(
            message=f"HDRI '{asset_id}' ({resolution}) をインポートしました",
            data={'name': hdri_name, 'type': 'hdri', 'resolution': resolution}
        )
        
    except Exception as e:
        logger.error(f"HDRIインポートエラー: {str(e)}")
        return create_error_response(f"HDRIのインポートに失敗しました: {str(e)}")