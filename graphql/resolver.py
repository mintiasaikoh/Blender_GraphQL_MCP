"""
Unified MCP GraphQL Resolvers
すべてのGraphQLクエリの解決処理を1つのファイルに統合
"""

import bpy
import json
import math
import traceback
import re
import logging
from typing import Dict, List, Any, Optional, Union
import mathutils

# 共通モジュールとユーティリティをインポート
try:
    from ..utils.common import (
        vector_to_dict, dict_to_vector, get_object_data,
        create_success_response, create_error_response
    )
    from ..utils.error_handler import handle_exceptions, log_and_handle_exceptions
    COMMON_UTILS_AVAILABLE = True
except ImportError:
    COMMON_UTILS_AVAILABLE = False

# GraphQLスキーマと定数をインポート
from .schema import GRAPHQL_AVAILABLE
from .constants import (
    RELATIONSHIP_ABOVE, RELATIONSHIP_BELOW, RELATIONSHIP_LEFT, RELATIONSHIP_RIGHT,
    RELATIONSHIP_FRONT, RELATIONSHIP_BACK, RELATIONSHIP_INSIDE, RELATIONSHIP_AROUND,
    RELATIONSHIP_ALIGNED,
    
    SMART_OBJECT_CUBE, SMART_OBJECT_SPHERE, SMART_OBJECT_CYLINDER, SMART_OBJECT_PLANE,
    SMART_OBJECT_CONE, SMART_OBJECT_TORUS, SMART_OBJECT_TEXT, SMART_OBJECT_EMPTY,
    SMART_OBJECT_LIGHT, SMART_OBJECT_CAMERA,
    
    BOOLEAN_OPERATION_UNION, BOOLEAN_OPERATION_DIFFERENCE, BOOLEAN_OPERATION_INTERSECT,
    BOOLEAN_SOLVER_FAST, BOOLEAN_SOLVER_EXACT,
    
    ERROR_OBJECT_NOT_FOUND, ERROR_INVALID_RELATIONSHIP, ERROR_INVALID_OBJECT_TYPE,
    ERROR_INVALID_OPERATION, ERROR_PROPERTY_PARSE,
    SUCCESS_OBJECT_CREATED, SUCCESS_RELATIONSHIP_SET, SUCCESS_BOOLEAN_OPERATION
)

# ロガー設定
logger = logging.getLogger('unified_mcp.graphql.resolver')

# -----------------------------
# シーン関連リゾルバ
# -----------------------------

@log_and_handle_exceptions("シーン情報の取得", level="debug")
def resolve_scene(name: Optional[str] = None) -> Dict[str, Any]:
    """シーン情報を取得"""
    scene = bpy.data.scenes.get(name) if name else bpy.context.scene
    if not scene:
        return None
    
    return {
        'id': str(scene.name),
        'name': scene.name,
        'objects': [resolve_object(obj.name) for obj in scene.objects],
        'active_object': resolve_object(bpy.context.active_object.name) if bpy.context.active_object else None,
        'selected_objects': [resolve_object(obj.name) for obj in bpy.context.selected_objects],
        'frame_current': scene.frame_current,
        'frame_start': scene.frame_start,
        'frame_end': scene.frame_end,
    }

@log_and_handle_exceptions("オブジェクト情報の取得", level="debug")
def resolve_object(name: str) -> Dict[str, Any]:
    """オブジェクト情報を取得"""
    obj = bpy.data.objects.get(name)
    if not obj:
        return None
    
    # 共通関数を使用してオブジェクトデータを取得
    if COMMON_UTILS_AVAILABLE:
        data = get_object_data(obj)
        # idを追加
        data['id'] = str(obj.name)
        return data
    else:
        # 共通関数が使えない場合は独自実装で取得
        return {
            'id': str(obj.name),
            'name': obj.name,
            'type': obj.type,
            'location': {
                'x': obj.location.x,
                'y': obj.location.y,
                'z': obj.location.z
            },
            'rotation': {
                'x': obj.rotation_euler.x,
                'y': obj.rotation_euler.y,
                'z': obj.rotation_euler.z
            },
            'dimensions': {
                'x': obj.dimensions.x,
                'y': obj.dimensions.y,
                'z': obj.dimensions.z
            }
        }

def resolve_objects(type_name: Optional[str] = None, name_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
    """条件に一致するオブジェクト一覧を取得"""
    try:
        filtered_objects = bpy.data.objects
        
        if type_name:
            filtered_objects = [obj for obj in filtered_objects if obj.type == type_name]
        
        if name_pattern:
            name_pattern = name_pattern.lower()
            filtered_objects = [obj for obj in filtered_objects if name_pattern in obj.name.lower()]
        
        return [resolve_object(obj.name) for obj in filtered_objects]
    except Exception as e:
        print(f"オブジェクト一覧解決エラー: {str(e)}")
        traceback.print_exc()
        return []

def resolve_material(name: str) -> Dict[str, Any]:
    """マテリアル情報を取得"""
    try:
        material = bpy.data.materials.get(name)
        if not material:
            return None
        
        if material.use_nodes:
            principled_bsdf = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled_bsdf:
                color = principled_bsdf.inputs['Base Color'].default_value
                metallic = principled_bsdf.inputs['Metallic'].default_value
                roughness = principled_bsdf.inputs['Roughness'].default_value
            else:
                color = material.diffuse_color
                metallic = 0.0
                roughness = 0.5
        else:
            color = material.diffuse_color
            metallic = material.metallic
            roughness = material.roughness
        
        return {
            'id': str(material.name),
            'name': material.name,
            'color': {
                'r': color[0],
                'g': color[1],
                'b': color[2],
                'a': color[3] if len(color) > 3 else 1.0
            },
            'metallic': metallic,
            'roughness': roughness,
            'use_nodes': material.use_nodes
        }
    except Exception as e:
        print(f"マテリアル解決エラー ({name}): {str(e)}")
        traceback.print_exc()
        return None

def resolve_materials() -> List[Dict[str, Any]]:
    """マテリアル一覧を取得"""
    try:
        return [resolve_material(material.name) for material in bpy.data.materials]
    except Exception as e:
        print(f"マテリアル一覧解決エラー: {str(e)}")
        traceback.print_exc()
        return []

# -----------------------------
# オブジェクト操作リゾルバ
# -----------------------------

def resolve_set_object_location(object_name: str, location: Dict[str, float]) -> Dict[str, Any]:
    """オブジェクトの位置を設定"""
    try:
        obj = bpy.data.objects.get(object_name)
        if not obj:
            return create_error_response(f"Object '{object_name}' not found")
        
        # 位置を設定
        obj.location.x = location.get('x', obj.location.x)
        obj.location.y = location.get('y', obj.location.y)
        obj.location.z = location.get('z', obj.location.z)
        
        return create_success_response({
            'name': obj.name,
            'location': vector_to_dict(obj.location)
        })
    except Exception as e:
        error_msg = str(e)
        print(f"位置設定エラー: {error_msg}")
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f"位置設定エラー: {error_msg}",
            'data': None
        }

def resolve_set_object_rotation(object_name: str, rotation: Dict[str, float], is_degrees: bool = True) -> Dict[str, Any]:
    """オブジェクトの回転を設定"""
    try:
        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {
                'status': 'error',
                'message': f"オブジェクト '{object_name}' が見つかりません",
                'data': None
            }
        
        x = rotation.get('x', obj.rotation_euler.x)
        y = rotation.get('y', obj.rotation_euler.y)
        z = rotation.get('z', obj.rotation_euler.z)
        
        if is_degrees:
            x = math.radians(x)
            y = math.radians(y)
            z = math.radians(z)
        
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = (x, y, z)
        
        return {
            'status': 'success',
            'message': f"オブジェクト '{object_name}' の回転を更新しました",
            'data': json.dumps({
                'rotation': {
                    'x': math.degrees(obj.rotation_euler.x),
                    'y': math.degrees(obj.rotation_euler.y),
                    'z': math.degrees(obj.rotation_euler.z)
                }
            })
        }
    except Exception as e:
        error_msg = str(e)
        print(f"回転設定エラー: {error_msg}")
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f"回転設定エラー: {error_msg}",
            'data': None
        }

def resolve_set_object_scale(object_name: str, scale: Dict[str, float]) -> Dict[str, Any]:
    """オブジェクトのスケールを設定"""
    try:
        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {
                'status': 'error',
                'message': f"オブジェクト '{object_name}' が見つかりません",
                'data': None
            }
        
        if 'x' in scale:
            obj.scale.x = scale['x']
        if 'y' in scale:
            obj.scale.y = scale['y']
        if 'z' in scale:
            obj.scale.z = scale['z']
        
        return {
            'status': 'success',
            'message': f"オブジェクト '{object_name}' のスケールを更新しました",
            'data': json.dumps({
                'scale': {
                    'x': obj.scale.x,
                    'y': obj.scale.y,
                    'z': obj.scale.z
                }
            })
        }
    except Exception as e:
        error_msg = str(e)
        print(f"スケール設定エラー: {error_msg}")
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f"スケール設定エラー: {error_msg}",
            'data': None
        }

def resolve_set_material_color(material_name: str, color: Dict[str, float]) -> Dict[str, Any]:
    """マテリアルの色を設定"""
    try:
        material = bpy.data.materials.get(material_name)
        if not material:
            return {
                'status': 'error',
                'message': f"マテリアル '{material_name}' が見つかりません",
                'data': None
            }
        
        r = color.get('r', 1.0)
        g = color.get('g', 1.0)
        b = color.get('b', 1.0)
        a = color.get('a', 1.0)
        
        if material.use_nodes:
            principled_bsdf = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled_bsdf:
                principled_bsdf.inputs['Base Color'].default_value = (r, g, b, a)
            
            material.diffuse_color = (r, g, b, a)
        else:
            material.diffuse_color = (r, g, b, a)
        
        return {
            'status': 'success',
            'message': f"マテリアル '{material_name}' の色を更新しました",
            'data': json.dumps({
                'color': {
                    'r': r,
                    'g': g,
                    'b': b,
                    'a': a
                }
            })
        }
    except Exception as e:
        error_msg = str(e)
        print(f"マテリアル色設定エラー: {error_msg}")
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f"マテリアル色設定エラー: {error_msg}",
            'data': None
        }
# 高度なオブジェクト操作
# -----------------------------

@log_and_handle_exceptions("空間関係の設定")
def resolve_set_spatial_relationship(
    target_object: str, 
    reference_object: str, 
    relationship: str, 
    distance: Optional[float] = None, 
    maintain_rotation: bool = True
) -> Dict[str, Any]:
    """オブジェクト間の空間関係を設定"""
    # オブジェクトの取得
    target = bpy.data.objects.get(target_object)
    reference = bpy.data.objects.get(reference_object)
    
    if not target:
        return create_error_response(ERROR_OBJECT_NOT_FOUND.format(target_object))
    
    if not reference:
        return create_error_response(ERROR_OBJECT_NOT_FOUND.format(reference_object))
    
    # 関係タイプのバリデーション
    valid_relationships = [
        RELATIONSHIP_ABOVE, RELATIONSHIP_BELOW, RELATIONSHIP_LEFT, RELATIONSHIP_RIGHT,
        RELATIONSHIP_FRONT, RELATIONSHIP_BACK, RELATIONSHIP_INSIDE, RELATIONSHIP_AROUND,
        RELATIONSHIP_ALIGNED
    ]
    
    if relationship not in valid_relationships:
        return create_error_response(ERROR_INVALID_RELATIONSHIP.format(relationship))
    
    # 元の回転を記録
    original_rotation = target.rotation_euler.copy() if maintain_rotation else None
    
    # リファレンスオブジェクトの位置と寸法を取得
    ref_loc = reference.location
    ref_dims = reference.dimensions
    
    # 定数チェック、デフォルトの距離
    default_distance = max(max(ref_dims) * 0.1, 0.5)  # デフォルト距離はオブジェクトサイズの10%か、50cmの大きい方
    relation_distance = distance if distance is not None else default_distance
    
    # 関係に基づいて位置を設定
    if relationship == RELATIONSHIP_ABOVE:
        target.location = (ref_loc.x, ref_loc.y, ref_loc.z + ref_dims.z/2 + relation_distance + target.dimensions.z/2)
    elif relationship == RELATIONSHIP_BELOW:
        target.location = (ref_loc.x, ref_loc.y, ref_loc.z - ref_dims.z/2 - relation_distance - target.dimensions.z/2)
    elif relationship == RELATIONSHIP_LEFT:
        target.location = (ref_loc.x - ref_dims.x/2 - relation_distance - target.dimensions.x/2, ref_loc.y, ref_loc.z)
    elif relationship == RELATIONSHIP_RIGHT:
        target.location = (ref_loc.x + ref_dims.x/2 + relation_distance + target.dimensions.x/2, ref_loc.y, ref_loc.z)
    elif relationship == RELATIONSHIP_FRONT:
        target.location = (ref_loc.x, ref_loc.y - ref_dims.y/2 - relation_distance - target.dimensions.y/2, ref_loc.z)
    elif relationship == RELATIONSHIP_BACK:
        target.location = (ref_loc.x, ref_loc.y + ref_dims.y/2 + relation_distance + target.dimensions.y/2, ref_loc.z)
    elif relationship == RELATIONSHIP_INSIDE:
        # 内部に配置する場合は距離を無視
        scale_factor = min([
            ref_dims.x / (target.dimensions.x * 1.05),
            ref_dims.y / (target.dimensions.y * 1.05),
            ref_dims.z / (target.dimensions.z * 1.05)
        ])
        
        if scale_factor < 1.0:
            # 自動スケールダウン
            target.scale = (target.scale.x * scale_factor, target.scale.y * scale_factor, target.scale.z * scale_factor)
        
        target.location = ref_loc.copy()
    elif relationship == RELATIONSHIP_AROUND:
        # 周りを囲むように配置する場合は距離を空間として扱う
        scale_factor = max([
            (ref_dims.x + relation_distance * 2) / target.dimensions.x,
            (ref_dims.y + relation_distance * 2) / target.dimensions.y,
            (ref_dims.z + relation_distance * 2) / target.dimensions.z
        ])
        
        target.scale = (target.scale.x * scale_factor, target.scale.y * scale_factor, target.scale.z * scale_factor)
        target.location = ref_loc.copy()
    elif relationship == RELATIONSHIP_ALIGNED:
        # 中心を合わせる
        target.location = ref_loc.copy()
    
    # 結果の評価
    if original_rotation and maintain_rotation:
        target.rotation_euler = original_rotation
    
    # カスタム成功応答を返す
    if COMMON_UTILS_AVAILABLE:
        return create_success_response(
            {
                'target': target_object,
                'reference': reference_object,
                'relationship': relationship,
                'new_location': vector_to_dict(target.location)
            },
            SUCCESS_RELATIONSHIP_SET.format(target_object, reference_object, relationship)
        )
    else:
        return {
            'status': 'success',
            'message': SUCCESS_RELATIONSHIP_SET.format(target_object, reference_object, relationship),
            'data': {
                'target': target_object,
                'reference': reference_object,
                'relationship': relationship,
                'new_location': {
                    'x': target.location.x,
                    'y': target.location.y,
                    'z': target.location.z
                }
            }
        }

@log_and_handle_exceptions("スマートオブジェクトの作成")
def resolve_create_smart_object(
    object_type: str,
    name: Optional[str] = None,
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    scale: Optional[Dict[str, float]] = None,
    properties: Optional[str] = None
) -> Dict[str, Any]:
    """よく使われるオブジェクトを簡単に作成"""
    # 引数とオブジェクトタイプのバリデーション
    valid_object_types = [
        SMART_OBJECT_CUBE, SMART_OBJECT_SPHERE, SMART_OBJECT_CYLINDER, SMART_OBJECT_PLANE,
        SMART_OBJECT_CONE, SMART_OBJECT_TORUS, SMART_OBJECT_TEXT, SMART_OBJECT_EMPTY,
        SMART_OBJECT_LIGHT, SMART_OBJECT_CAMERA
    ]
    
    if object_type not in valid_object_types:
        return create_error_response(ERROR_INVALID_OBJECT_TYPE.format(object_type))
    
    # プロパティのJSON解析、指定がなければ空辞書
    props = {}
    if properties:
        try:
            props = json.loads(properties)
        except json.JSONDecodeError:
            return create_error_response(ERROR_PROPERTY_PARSE.format(properties))
    
    # 座標、回転、スケールを設定
    loc = dict_to_vector(location) if location else (0, 0, 0)
    rot = dict_to_vector(rotation) if rotation else (0, 0, 0)
    scl = dict_to_vector(scale) if scale else (1, 1, 1)
    
    # オブジェクトのデフォルト名を生成
    default_name = f"Smart{object_type.capitalize()}" if name is None else name
    
    new_obj = None
    
    # オブジェクトの種類に基づいて作成
    if object_type == SMART_OBJECT_CUBE:
        bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot, scale=scl)
        new_obj = bpy.context.active_object
        new_obj.name = default_name
    
    elif object_type == SMART_OBJECT_SPHERE:
        # スフィア特有のプロパティを取得
        segments = props.get('segments', 32)
        rings = props.get('rings', 16)
        
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=segments, ring_count=rings,
            location=loc, rotation=rot, scale=scl
        )
        new_obj = bpy.context.active_object
        new_obj.name = default_name
    
    elif object_type == SMART_OBJECT_CYLINDER:
        # シリンダー特有のプロパティを取得
        vertices = props.get('vertices', 32)
        depth = props.get('depth', 2.0)
        
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=vertices, depth=depth,
            location=loc, rotation=rot, scale=scl
        )
        new_obj = bpy.context.active_object
        new_obj.name = default_name
    
    elif object_type == SMART_OBJECT_PLANE:
        bpy.ops.mesh.primitive_plane_add(location=loc, rotation=rot, scale=scl)
        new_obj = bpy.context.active_object
        new_obj.name = default_name
    
    elif object_type == SMART_OBJECT_CONE:
        # コーン特有のプロパティを取得
        vertices = props.get('vertices', 32)
        
        bpy.ops.mesh.primitive_cone_add(
            vertices=vertices,
            location=loc, rotation=rot, scale=scl
        )
        new_obj = bpy.context.active_object
        new_obj.name = default_name
    
    elif object_type == SMART_OBJECT_TORUS:
        # トーラス特有のプロパティを取得
        major_segments = props.get('major_segments', 48)
        minor_segments = props.get('minor_segments', 12)
        major_radius = props.get('major_radius', 1.0)
        minor_radius = props.get('minor_radius', 0.25)
        
        bpy.ops.mesh.primitive_torus_add(
            major_segments=major_segments, minor_segments=minor_segments,
            major_radius=major_radius, minor_radius=minor_radius,
            location=loc, rotation=rot
        )
        new_obj = bpy.context.active_object
        new_obj.name = default_name
        # torusの場合はスケールを後から設定
        new_obj.scale = scl
    
    elif object_type == SMART_OBJECT_TEXT:
        # テキスト特有のプロパティを取得
        text = props.get('text', 'Text')
        
        bpy.ops.object.text_add(location=loc, rotation=rot)
        new_obj = bpy.context.active_object
        new_obj.name = default_name
        new_obj.data.body = text
        new_obj.scale = scl
    
    elif object_type == SMART_OBJECT_EMPTY:
        # エンプティ特有のプロパティを取得
        empty_type = props.get('empty_type', 'PLAIN_AXES')
        empty_size = props.get('empty_size', 1.0)
        
        bpy.ops.object.empty_add(type=empty_type, location=loc, rotation=rot)
        new_obj = bpy.context.active_object
        new_obj.name = default_name
        new_obj.empty_display_size = empty_size
        new_obj.scale = scl
    
    elif object_type == SMART_OBJECT_LIGHT:
        # ライト特有のプロパティを取得
        light_type = props.get('light_type', 'POINT')
        energy = props.get('energy', 1000.0)
        color = props.get('color', (1.0, 1.0, 1.0))
        
        bpy.ops.object.light_add(type=light_type, location=loc, rotation=rot)
        new_obj = bpy.context.active_object
        new_obj.name = default_name
        new_obj.data.energy = energy
        new_obj.data.color = color
        new_obj.scale = scl
    
    elif object_type == SMART_OBJECT_CAMERA:
        # カメラ特有のプロパティを取得
        lens = props.get('lens', 50.0)
        
        bpy.ops.object.camera_add(location=loc, rotation=rot)
        new_obj = bpy.context.active_object
        new_obj.name = default_name
        new_obj.data.lens = lens
        new_obj.scale = scl
    
    # オブジェクト情報を取得
    obj_data = resolve_object(new_obj.name)
    
    return create_success_response(
        obj_data,
        SUCCESS_OBJECT_CREATED.format(new_obj.name)
    )

def resolve_enhanced_boolean_operation(
    target_object: str,
    tool_object: str,
    operation: str,
    solver: str = 'EXACT',
    auto_repair: bool = True
) -> Dict[str, Any]:
    """高度なブーリアン操作を実行"""
    try:
        target = bpy.data.objects.get(target_object)
        tool = bpy.data.objects.get(tool_object)
        
        if not target:
            return {
                'status': 'error',
                'message': f"ターゲットオブジェクト '{target_object}' が見つかりません",
                'data': None
            }
        
        if not tool:
            return {
                'status': 'error',
                'message': f"ツールオブジェクト '{tool_object}' が見つかりません",
                'data': None
            }
        
        if target.type != 'MESH' or tool.type != 'MESH':
            return {
                'status': 'error',
                'message': f"ブーリアン操作はメッシュオブジェクト間でのみ実行できます",
                'data': None
            }
        
        original_selection = bpy.context.selected_objects.copy()
        original_active = bpy.context.active_object
        
        if auto_repair:
            bpy.ops.object.select_all(action='DESELECT')
            target.select_set(True)
            bpy.context.view_layer.objects.active = target
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.mesh.select_non_manifold()
            bpy.ops.mesh.edge_face_add()
            bpy.ops.object.mode_set(mode='OBJECT')
            
            bpy.ops.object.select_all(action='DESELECT')
            tool.select_set(True)
            bpy.context.view_layer.objects.active = tool
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.mesh.select_non_manifold()
            bpy.ops.mesh.edge_face_add()
            bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        
        boolean_mod = target.modifiers.new(name=f"Boolean_{operation}", type='BOOLEAN')
        boolean_mod.operation = operation
        boolean_mod.solver = solver
        boolean_mod.object = tool
        
        bpy.ops.object.modifier_apply(modifier=boolean_mod.name)
        tool.hide_set(True)
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            if obj != tool:  # ツールオブジェクトは選択から除外
                obj.select_set(True)
        
        if original_active and original_active != tool:
            bpy.context.view_layer.objects.active = original_active
        elif original_active == tool:
            bpy.context.view_layer.objects.active = target
        
        return {
            'status': 'success',
            'message': f"'{target_object}' と '{tool_object}' の間で {operation} ブーリアン操作を実行しました",
            'data': json.dumps({
                'targetObject': target_object,
                'toolObject': tool_object,
                'operation': operation,
                'vertexCount': len(target.data.vertices),
                'faceCount': len(target.data.polygons)
            })
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"ブーリアン操作エラー: {error_msg}")
        traceback.print_exc()
        
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
            
        return {
            'status': 'error',
            'message': f"ブーリアン操作エラー: {error_msg}",
            'data': None
        }

# リゾルバ関数の登録
def register_resolvers(resolvers_dict):
    """リゾルバ関数をスキーマに登録"""
    try:
        # Query型のリゾルバ
        if 'Query' not in resolvers_dict:
            resolvers_dict['Query'] = {}
        
        # 基本的なクエリリゾルバを登録
        resolvers_dict['Query']['scene'] = lambda root, info, name=None: resolve_scene(name)
        resolvers_dict['Query']['object'] = lambda root, info, name: resolve_object(name)
        resolvers_dict['Query']['objects'] = lambda root, info, type=None: resolve_objects(type_name=type)
        
        # Mutation型のリゾルバ
        if 'Mutation' not in resolvers_dict:
            resolvers_dict['Mutation'] = {}
        
        # 基本的なミューテーションリゾルバを登録
        resolvers_dict['Mutation']['setObjectLocation'] = lambda root, info, name, x=None, y=None, z=None: resolve_set_object_location(name, {'x': x, 'y': y, 'z': z})
        resolvers_dict['Mutation']['setObjectRotation'] = lambda root, info, name, x=None, y=None, z=None: resolve_set_object_rotation(name, {'x': x, 'y': y, 'z': z})
        resolvers_dict['Mutation']['setObjectScale'] = lambda root, info, name, x=None, y=None, z=None: resolve_set_object_scale(name, {'x': x, 'y': y, 'z': z})
        resolvers_dict['Mutation']['setMaterialColor'] = lambda root, info, objectName, materialName=None, r=None, g=None, b=None: resolve_set_material_color(objectName, materialName, {'r': r, 'g': g, 'b': b})
        resolvers_dict['Mutation']['setSpatialRelationship'] = lambda root, info, sourceObject, targetObject, relationship: resolve_set_spatial_relationship(sourceObject, targetObject, relationship)
        resolvers_dict['Mutation']['createSmartObject'] = lambda root, info, type, name=None, location=None, rotation=None, scale=None, material=None: resolve_create_smart_object(type, name, location, rotation, scale, json.dumps(material) if material else None)
        resolvers_dict['Mutation']['enhancedBooleanOperation'] = lambda root, info, targetObject, toolObject, operation, solver: resolve_enhanced_boolean_operation(targetObject, toolObject, operation, solver)
        
        # 穴貫通チェック用リゾルバを登録
        from .hole_penetration import RESOLVERS as hole_penetration_resolvers
        for type_name, fields in hole_penetration_resolvers.items():
            if type_name not in resolvers_dict:
                resolvers_dict[type_name] = {}
            for field_name, resolver_fn in fields.items():
                resolvers_dict[type_name][field_name] = resolver_fn
        
        logger.info("リゾルバ関数を正常に登録しました")
        return True
    except Exception as e:
        logger.error(f"リゾルバ登録エラー: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

# モジュール登録関数
def register():
    """リゾルバモジュールを登録"""
    logger.info("統合リゾルバモジュールを登録しています...")
    # モジュール登録時の初期化処理があればここに追加
    logger.info("統合リゾルバモジュールを登録しました")

def unregister():
    """リゾルバモジュールの登録解除"""
    logger.info("統合リゾルバモジュールを登録解除しています...")
    # 登録解除時のクリーンアップ処理があればここに追加
    logger.info("統合リゾルバモジュールを登録解除しました")
