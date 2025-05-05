"""
Mesh Operations Module - 高度なメッシュ操作機能
"""

import bpy
import bmesh
import mathutils
import math
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
import logging

# ロギング設定
logger = logging.getLogger(__name__)

def run_boolean_operation(target_name: str, cutter_name: str, operation: str, 
                          solver: str = 'EXACT', auto_repair: bool = True) -> Dict[str, Any]:
    """
    ブーリアン操作を実行
    
    Args:
        target_name: 対象オブジェクト名
        cutter_name: カッターオブジェクト名
        operation: 操作タイプ ('UNION', 'DIFFERENCE', 'INTERSECT')
        solver: 使用するソルバー ('EXACT', 'FAST')
        auto_repair: 操作前に自動修復を行うかどうか
        
    Returns:
        Dict: 操作結果
    """
    try:
        # オブジェクトの存在確認
        target = bpy.data.objects.get(target_name)
        cutter = bpy.data.objects.get(cutter_name)
        
        if not target or not cutter:
            return {
                "status": "error",
                "message": f"Objects not found: {'target' if not target else 'cutter'}",
                "details": {
                    "target_exists": target is not None,
                    "cutter_exists": cutter is not None
                }
            }
        
        # オブジェクトタイプの確認
        if target.type != 'MESH' or cutter.type != 'MESH':
            return {
                "status": "error",
                "message": "Both objects must be meshes",
                "details": {
                    "target_type": target.type,
                    "cutter_type": cutter.type
                }
            }
        
        # 操作タイプの検証
        valid_operations = ['UNION', 'DIFFERENCE', 'INTERSECT']
        if operation.upper() not in valid_operations:
            return {
                "status": "error",
                "message": f"Invalid operation: {operation}. Must be one of {valid_operations}",
                "details": {
                    "requested_operation": operation,
                    "valid_operations": valid_operations
                }
            }
        
        # 自動修復が有効な場合、メッシュの前処理を行う
        if auto_repair:
            repair_result_target = repair_mesh(target_name)
            repair_result_cutter = repair_mesh(cutter_name)
            
            if repair_result_target.get("status") == "error" or repair_result_cutter.get("status") == "error":
                return {
                    "status": "error",
                    "message": "Failed to repair meshes",
                    "details": {
                        "target_repair": repair_result_target,
                        "cutter_repair": repair_result_cutter
                    }
                }
        
        # オブジェクトの状態を保存（操作比較用）
        before_stats = get_mesh_stats(target_name)
        
        # 既存のブーリアンモディファイア確認
        existing_modifiers = [mod for mod in target.modifiers if mod.type == 'BOOLEAN' and mod.object == cutter]
        
        # 既存のモディファイアを使用するか新規作成
        if existing_modifiers:
            bool_mod = existing_modifiers[0]
            bool_mod.operation = operation.upper()
            bool_mod.solver = solver
        else:
            # 新しいブーリアンモディファイアを追加
            bool_mod = target.modifiers.new(name="MCP_Boolean", type='BOOLEAN')
            bool_mod.operation = operation.upper()
            bool_mod.object = cutter
            bool_mod.solver = solver
        
        # モディファイアを適用
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=bool_mod.name)
        
        # 操作後の統計
        after_stats = get_mesh_stats(target_name)
        
        # 変更の計算
        changes = calculate_mesh_changes(before_stats, after_stats)
        
        return {
            "status": "success",
            "message": f"Boolean {operation.lower()} operation completed",
            "details": {
                "target": target_name,
                "cutter": cutter_name,
                "operation": operation.upper(),
                "solver": solver,
                "changes": changes,
                "before": before_stats,
                "after": after_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Boolean operation failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Boolean operation failed: {str(e)}",
            "details": {
                "target": target_name,
                "cutter": cutter_name,
                "operation": operation,
                "exception": str(e)
            }
        }

def repair_mesh(object_name: str) -> Dict[str, Any]:
    """
    メッシュの問題を自動修復
    
    Args:
        object_name: 修復するオブジェクト名
        
    Returns:
        Dict: 修復結果
    """
    try:
        obj = bpy.data.objects.get(object_name)
        
        if not obj or obj.type != 'MESH':
            return {
                "status": "error",
                "message": f"Object {object_name} is not a valid mesh",
                "details": {
                    "exists": obj is not None,
                    "type": obj.type if obj else None
                }
            }
        
        # 修復前の統計情報
        before_stats = get_mesh_stats(object_name)
        issues_before = detect_mesh_issues(object_name)
        
        # BMeshを使用して修復操作を実行
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        # BMeshを取得
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        
        # 1. 重複した頂点を削除
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
        
        # 2. エッジと面を再計算
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        
        # 3. 非マニフォールドジオメトリを修復
        non_manifold_verts = [v for v in bm.verts if not v.is_manifold]
        non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
        
        if non_manifold_verts:
            bmesh.ops.dissolve_verts(bm, verts=non_manifold_verts)
        
        if non_manifold_edges:
            bmesh.ops.dissolve_edges(bm, edges=non_manifold_edges)
        
        # 4. 孤立した頂点を削除
        loose_verts = [v for v in bm.verts if len(v.link_edges) == 0]
        if loose_verts:
            bmesh.ops.delete(bm, geom=loose_verts, context='VERTS')
        
        # 5. 面積ゼロの面を削除
        zero_faces = [f for f in bm.faces if f.calc_area() < 0.000001]
        if zero_faces:
            bmesh.ops.delete(bm, geom=zero_faces, context='FACES')
        
        # 変更をメッシュに反映
        bmesh.update_edit_mesh(mesh)
        
        # オブジェクトモードに戻る
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 修復後の統計情報
        after_stats = get_mesh_stats(object_name)
        issues_after = detect_mesh_issues(object_name)
        
        # 変更の計算
        changes = calculate_mesh_changes(before_stats, after_stats)
        fixed_issues = calculate_fixed_issues(issues_before, issues_after)
        
        return {
            "status": "success",
            "message": "Mesh repair completed",
            "details": {
                "object": object_name,
                "changes": changes,
                "fixed_issues": fixed_issues,
                "remaining_issues": issues_after
            }
        }
        
    except Exception as e:
        logger.error(f"Mesh repair failed: {str(e)}")
        
        # 何かエラーが発生した場合は、オブジェクトモードに戻す
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
            
        return {
            "status": "error",
            "message": f"Mesh repair failed: {str(e)}",
            "details": {
                "object": object_name,
                "exception": str(e)
            }
        }

def get_mesh_stats(object_name: str) -> Dict[str, Any]:
    """
    メッシュの統計情報を取得
    
    Args:
        object_name: 分析するオブジェクト名
        
    Returns:
        Dict: メッシュ統計情報
    """
    obj = bpy.data.objects.get(object_name)
    
    if not obj or obj.type != 'MESH':
        return {}
    
    mesh = obj.data
    
    # BMeshを使用してより詳細な分析を行う
    bm = bmesh.new()
    bm.from_mesh(mesh)
    
    # トライアングル、クワッド、Nゴン数をカウント
    triangles = 0
    quads = 0
    ngons = 0
    
    for face in bm.faces:
        vert_count = len(face.verts)
        if vert_count == 3:
            triangles += 1
        elif vert_count == 4:
            quads += 1
        else:
            ngons += 1
    
    # 面積と体積を計算
    total_area = sum(f.calc_area() for f in bm.faces)
    
    # 閉じたメッシュの場合のみ体積を計算
    volume = 0
    if all(e.is_manifold for e in bm.edges):
        volume = bm.calc_volume()
    
    # BMeshを解放
    bm.free()
    
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "faces": len(mesh.polygons),
        "triangles": triangles,
        "quads": quads,
        "ngons": ngons,
        "area": round(total_area, 6),
        "volume": round(volume, 6) if volume else 0,
        "dimensions": [round(d, 6) for d in obj.dimensions],
        "is_manifold": all(e.is_manifold for e in bm.edges) if bm else False
    }

def detect_mesh_issues(object_name: str) -> Dict[str, Any]:
    """
    メッシュの問題を検出
    
    Args:
        object_name: 検査するオブジェクト名
        
    Returns:
        Dict: 検出された問題
    """
    obj = bpy.data.objects.get(object_name)
    
    if not obj or obj.type != 'MESH':
        return {"error": f"Object {object_name} is not a valid mesh"}
    
    # BMeshを使用して問題を検出
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    # 非マニフォールドの検出
    non_manifold_verts = [v.index for v in bm.verts if not v.is_manifold]
    non_manifold_edges = [e.index for e in bm.edges if not e.is_manifold]
    
    # 孤立した頂点
    loose_verts = [v.index for v in bm.verts if len(v.link_edges) == 0]
    
    # 自己交差面の検出
    # 注: 完全な自己交差検出はより複雑だが、ここではシンプルな実装
    self_intersecting = False
    
    # 法線の一貫性
    inconsistent_normals = False
    for f in bm.faces:
        for e in f.edges:
            if len(e.link_faces) > 1:
                # 隣接する面の法線の向きが一貫していないかチェック
                dot_product = f.normal.dot(e.link_faces[0].normal if e.link_faces[0] != f else e.link_faces[1].normal)
                if dot_product < 0:
                    inconsistent_normals = True
                    break
        if inconsistent_normals:
            break
    
    # 面積ゼロの面
    zero_faces = [f.index for f in bm.faces if f.calc_area() < 0.000001]
    
    # BMeshを解放
    bm.free()
    
    return {
        "non_manifold_vertices": len(non_manifold_verts),
        "non_manifold_edges": len(non_manifold_edges),
        "loose_vertices": len(loose_verts),
        "self_intersecting": self_intersecting,
        "inconsistent_normals": inconsistent_normals,
        "zero_area_faces": len(zero_faces),
        "details": {
            "non_manifold_verts": non_manifold_verts[:10],  # 最初の10個だけ表示
            "non_manifold_edges": non_manifold_edges[:10],
            "loose_verts": loose_verts[:10],
            "zero_faces": zero_faces[:10]
        }
    }

def calculate_mesh_changes(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    メッシュの変更点を計算
    
    Args:
        before: 変更前の統計
        after: 変更後の統計
        
    Returns:
        Dict: 変更点
    """
    if not before or not after:
        return {}
    
    changes = {}
    
    for key in before:
        if key in after:
            if isinstance(before[key], (int, float)):
                changes[key] = {
                    "before": before[key],
                    "after": after[key],
                    "diff": after[key] - before[key],
                    "percent": round((after[key] - before[key]) / max(before[key], 1) * 100, 2)
                }
            elif isinstance(before[key], list) and isinstance(after[key], list):
                if len(before[key]) == len(after[key]):
                    diff = [after[key][i] - before[key][i] for i in range(len(before[key]))]
                    changes[key] = {
                        "before": before[key],
                        "after": after[key],
                        "diff": diff
                    }
            elif isinstance(before[key], bool) and isinstance(after[key], bool):
                changes[key] = {
                    "before": before[key],
                    "after": after[key],
                    "changed": before[key] != after[key]
                }
    
    return changes

def calculate_fixed_issues(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    修正された問題を計算
    
    Args:
        before: 修正前の問題
        after: 修正後の問題
        
    Returns:
        Dict: 修正された問題
    """
    if not before or not after or "error" in before or "error" in after:
        return {}
    
    fixed = {}
    
    for key in before:
        if key in after and key != "details":
            if isinstance(before[key], (int, bool)):
                if before[key] > 0 or before[key] is True:
                    fixed[key] = {
                        "before": before[key],
                        "after": after[key],
                        "fixed": before[key] - after[key] if isinstance(before[key], int) else before[key] and not after[key],
                        "fully_fixed": after[key] == 0 or after[key] is False
                    }
    
    return fixed
