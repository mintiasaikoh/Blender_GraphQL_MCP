"""
高度なJSONベースのBlender操作API - メッシュ編集とブーリアン操作
"""

import bpy
import bmesh
import logging
import traceback
import mathutils
from typing import Dict, Any, List, Tuple, Optional

# ロガー設定
logger = logging.getLogger('unified_mcp.json_api_advanced')

def execute_in_main_thread(func, *args, **kwargs):
    """
    Blenderのメインスレッドで関数を実行する
    """
    try:
        # メインスレッドに登録するためのタイマー関数
        def main_thread_func():
            func(*args, **kwargs)
            return None  # 一度だけ実行するためにNoneを返す
            
        # タイマーに登録
        return bpy.app.timers.register(main_thread_func, first_interval=0.0)
    except Exception as e:
        logger.error(f"メインスレッド実行エラー: {str(e)}")
        return False

def boolean_operation(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    ブーリアン操作を実行する
    
    Args:
        params: {
            "target": 対象オブジェクト名,
            "cutter": カッターオブジェクト名,
            "operation": 操作タイプ ("union", "difference", "intersect"),
            "delete_cutter": カッターを操作後に削除するかどうか (default: True)
        }
        
    Returns:
        操作結果
    """
    try:
        # パラメータを取得
        target_name = params.get('target', '')
        cutter_name = params.get('cutter', '')
        operation_type = params.get('operation', 'difference')
        delete_cutter = params.get('delete_cutter', True)
        
        if not target_name or not cutter_name:
            return {
                "success": False,
                "message": "対象オブジェクトとカッターオブジェクトの両方を指定してください"
            }
        
        # 操作タイプのマッピング
        operation_map = {
            "union": "UNION",
            "difference": "DIFFERENCE",
            "intersect": "INTERSECT"
        }
        
        if operation_type not in operation_map:
            return {
                "success": False,
                "message": f"未サポートの操作タイプ: {operation_type}",
                "supported_types": list(operation_map.keys())
            }
        
        blender_operation = operation_map[operation_type]
        
        def execute_boolean():
            # オブジェクトを取得
            if target_name not in bpy.data.objects or cutter_name not in bpy.data.objects:
                logger.error(f"オブジェクトが見つかりません: target={target_name}, cutter={cutter_name}")
                return {
                    "success": False,
                    "message": f"オブジェクトが見つかりません: target={target_name}, cutter={cutter_name}"
                }
            
            target = bpy.data.objects[target_name]
            cutter = bpy.data.objects[cutter_name]
            
            # アクティブオブジェクトを設定
            bpy.context.view_layer.objects.active = target
            target.select_set(True)
            
            # ブーリアンモディファイアを追加
            boolean_mod = target.modifiers.new(name="Boolean", type="BOOLEAN")
            boolean_mod.object = cutter
            boolean_mod.operation = blender_operation
            
            # モディファイアを適用
            bpy.ops.object.modifier_apply(modifier=boolean_mod.name)
            
            # カッターを削除（オプション）
            if delete_cutter:
                bpy.data.objects.remove(cutter, do_unlink=True)
            
            return {
                "success": True,
                "message": f"ブーリアン操作 '{operation_type}' を実行しました",
                "target": target_name
            }
        
        # メインスレッドで実行
        execute_in_main_thread(execute_boolean)
        
        # 成功とみなす（非同期なので実際の結果は不明）
        return {
            "success": True,
            "message": f"ブーリアン操作 '{operation_type}' をキューに追加しました",
            "target": target_name,
            "cutter": cutter_name,
            "operation": operation_type
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"ブーリアン操作エラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"ブーリアン操作エラー: {error_msg}",
            "error": error_msg
        }

def extrude_face(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    メッシュの面を押し出す
    
    Args:
        params: {
            "object_name": 対象オブジェクト名,
            "face_index": 押し出す面のインデックス (または [x, y, z] のベクトルで最も近い面を選択),
            "direction": 押し出し方向 [x, y, z] (default: 面の法線方向),
            "distance": 押し出し距離 (default: 1.0)
        }
        
    Returns:
        操作結果
    """
    try:
        # パラメータを取得
        object_name = params.get('object_name', '')
        face_index = params.get('face_index', None)
        face_position = params.get('face_position', None)
        direction = params.get('direction', None)
        distance = params.get('distance', 1.0)
        
        if not object_name:
            return {
                "success": False,
                "message": "対象オブジェクト名を指定してください"
            }
            
        if face_index is None and face_position is None:
            return {
                "success": False,
                "message": "face_indexまたはface_positionのいずれかを指定してください"
            }
        
        def execute_extrude():
            # オブジェクトを取得
            if object_name not in bpy.data.objects:
                logger.error(f"オブジェクトが見つかりません: {object_name}")
                return {"success": False, "message": f"オブジェクトが見つかりません: {object_name}"}
            
            obj = bpy.data.objects[object_name]
            if obj.type != 'MESH':
                logger.error(f"オブジェクトはメッシュではありません: {object_name}")
                return {"success": False, "message": f"オブジェクトはメッシュではありません: {object_name}"}
            
            # オブジェクトを選択
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            
            # 編集モードに入る
            bpy.ops.object.mode_set(mode='EDIT')
            
            # bmeshを使用して編集
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)
            
            # 面の選択をクリア
            for face in bm.faces:
                face.select = False
            
            # 指定された面を選択
            if face_index is not None:
                if 0 <= face_index < len(bm.faces):
                    bm.faces[face_index].select = True
                    selected_face = bm.faces[face_index]
                else:
                    logger.error(f"無効な面インデックス: {face_index}, 最大: {len(bm.faces)-1}")
                    bpy.ops.object.mode_set(mode='OBJECT')
                    return {"success": False, "message": f"無効な面インデックス: {face_index}"}
            else:  # face_position で最も近い面を選択
                if len(face_position) != 3:
                    logger.error(f"face_positionは3D座標である必要があります: {face_position}")
                    bpy.ops.object.mode_set(mode='OBJECT')
                    return {"success": False, "message": f"face_positionは3D座標である必要があります: {face_position}"}
                
                # 最も近い面を探す
                pos = mathutils.Vector(face_position)
                closest_face = None
                min_distance = float('inf')
                
                for face in bm.faces:
                    face_center = face.calc_center_median()
                    dist = (face_center - pos).length
                    if dist < min_distance:
                        min_distance = dist
                        closest_face = face
                
                if closest_face:
                    closest_face.select = True
                    selected_face = closest_face
                else:
                    logger.error("面が見つかりませんでした")
                    bpy.ops.object.mode_set(mode='OBJECT')
                    return {"success": False, "message": "面が見つかりませんでした"}
            
            # 面法線を取得
            face_normal = selected_face.normal.copy()
            
            # 押し出し方向を決定
            if direction is None:
                extrude_direction = face_normal
            else:
                if len(direction) != 3:
                    logger.error(f"directionは3Dベクトルである必要があります: {direction}")
                    bpy.ops.object.mode_set(mode='OBJECT')
                    return {"success": False, "message": f"directionは3Dベクトルである必要があります: {direction}"}
                extrude_direction = mathutils.Vector(direction).normalized()
            
            # 押し出し実行
            extrude_vector = extrude_direction * distance
            ret = bmesh.ops.extrude_face_region(bm, geom=[selected_face])
            
            # 押し出した面を移動
            verts = [v for v in ret["geom"] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, vec=extrude_vector, verts=verts)
            
            # メッシュを更新
            bmesh.update_edit_mesh(mesh)
            
            # オブジェクトモードに戻る
            bpy.ops.object.mode_set(mode='OBJECT')
            
            return {
                "success": True,
                "message": f"面を押し出しました: {object_name}",
                "face_index": face_index if face_index is not None else "最も近い面を使用",
                "distance": distance
            }
        
        # メインスレッドで実行
        execute_in_main_thread(execute_extrude)
        
        # 成功とみなす（非同期なので実際の結果は不明）
        return {
            "success": True,
            "message": f"面押し出し操作をキューに追加しました: {object_name}",
            "face_index": face_index,
            "face_position": face_position,
            "distance": distance
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"面押し出しエラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        # エディットモードから抜ける
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
            
        return {
            "success": False,
            "message": f"面押し出しエラー: {error_msg}",
            "error": error_msg
        }

def create_from_vertices(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    頂点リストからメッシュを作成する
    
    Args:
        params: {
            "name": オブジェクト名,
            "vertices": 頂点座標のリスト [[x1, y1, z1], [x2, y2, z2], ...],
            "faces": 面の頂点インデックスのリスト [[v1, v2, v3], [v4, v5, v6], ...],
            "color": マテリアルの色 [r, g, b, a] (default: [0.8, 0.8, 0.8, 1.0])
        }
        
    Returns:
        作成結果
    """
    try:
        # パラメータを取得
        name = params.get('name', 'CustomMesh')
        vertices = params.get('vertices', [])
        faces = params.get('faces', [])
        color = params.get('color', [0.8, 0.8, 0.8, 1.0])
        
        if not vertices:
            return {
                "success": False,
                "message": "頂点データを指定してください"
            }
            
        def execute_create():
            # 新しいメッシュとオブジェクトを作成
            mesh = bpy.data.meshes.new(name + "_Mesh")
            obj = bpy.data.objects.new(name, mesh)
            
            # シーンにリンク
            bpy.context.collection.objects.link(obj)
            
            # メッシュデータを設定
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
            
            # マテリアルを作成して適用
            mat = bpy.data.materials.new(name=f"{name}_Material")
            mat.diffuse_color = color
            
            if mesh.materials:
                mesh.materials[0] = mat
            else:
                mesh.materials.append(mat)
            
            # 法線を再計算
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            return {
                "success": True,
                "message": f"カスタムメッシュを作成しました: {name}",
                "name": obj.name,
                "vertex_count": len(vertices),
                "face_count": len(faces)
            }
        
        # メインスレッドで実行
        execute_in_main_thread(execute_create)
        
        # 成功とみなす（非同期なので実際の結果は不明）
        return {
            "success": True,
            "message": f"カスタムメッシュ作成をキューに追加しました: {name}",
            "vertex_count": len(vertices),
            "face_count": len(faces)
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"カスタムメッシュ作成エラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"カスタムメッシュ作成エラー: {error_msg}",
            "error": error_msg
        }

def subdivide_mesh(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    メッシュをサブディビジョンする
    
    Args:
        params: {
            "object_name": 対象オブジェクト名,
            "levels": サブディビジョンレベル (default: 1),
            "apply_modifier": モディファイアを適用するかどうか (default: True)
        }
        
    Returns:
        操作結果
    """
    try:
        # パラメータを取得
        object_name = params.get('object_name', '')
        levels = params.get('levels', 1)
        apply_modifier = params.get('apply_modifier', True)
        
        if not object_name:
            return {
                "success": False,
                "message": "対象オブジェクト名を指定してください"
            }
            
        def execute_subdivide():
            # オブジェクトを取得
            if object_name not in bpy.data.objects:
                logger.error(f"オブジェクトが見つかりません: {object_name}")
                return {"success": False, "message": f"オブジェクトが見つかりません: {object_name}"}
            
            obj = bpy.data.objects[object_name]
            if obj.type != 'MESH':
                logger.error(f"オブジェクトはメッシュではありません: {object_name}")
                return {"success": False, "message": f"オブジェクトはメッシュではありません: {object_name}"}
            
            # オブジェクトを選択
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            
            # サブディビジョンモディファイアを追加
            subdiv_mod = obj.modifiers.new(name="Subdivision", type="SUBSURF")
            subdiv_mod.levels = levels
            subdiv_mod.render_levels = levels
            
            # モディファイアを適用（オプション）
            if apply_modifier:
                bpy.ops.object.modifier_apply(modifier=subdiv_mod.name)
            
            return {
                "success": True,
                "message": f"サブディビジョンを適用しました: {object_name}",
                "levels": levels,
                "applied": apply_modifier
            }
        
        # メインスレッドで実行
        execute_in_main_thread(execute_subdivide)
        
        # 成功とみなす（非同期なので実際の結果は不明）
        return {
            "success": True,
            "message": f"サブディビジョン操作をキューに追加しました: {object_name}",
            "levels": levels,
            "apply_modifier": apply_modifier
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"サブディビジョンエラー: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"サブディビジョンエラー: {error_msg}",
            "error": error_msg
        }
