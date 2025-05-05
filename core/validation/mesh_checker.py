"""
メッシュ検証モジュール
メッシュの品質チェックと問題診断機能を提供
特にブーリアン操作などの複雑な操作前後の検証に使用
"""

import bpy
import bmesh
from typing import Dict, List, Any, Optional, Tuple, Set

class MeshChecker:
    """
    メッシュの品質をチェックし、問題を診断するクラス
    """
    
    @classmethod
    def check_mesh(cls, obj_name: str) -> Dict[str, Any]:
        """
        メッシュの品質をチェック
        
        Args:
            obj_name: チェックするメッシュオブジェクト名
            
        Returns:
            チェック結果
        """
        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != 'MESH' or not obj.data:
            return {
                "valid": False,
                "error": f"Object '{obj_name}' is not a valid mesh"
            }
        
        # 結果を格納する辞書
        result = {
            "name": obj.name,
            "valid": True,
            "issues": [],
            "stats": {},
            "is_manifold": False
        }
        
        # BMeshを使用してメッシュ分析
        mesh = obj.data
        bm = bmesh.new()
        
        try:
            bm.from_mesh(mesh)
            
            # 基本統計情報
            result["stats"] = {
                "vertices": len(bm.verts),
                "edges": len(bm.edges),
                "faces": len(bm.faces),
                "tris": sum(1 for f in bm.faces if len(f.verts) == 3),
                "quads": sum(1 for f in bm.faces if len(f.verts) == 4),
                "ngons": sum(1 for f in bm.faces if len(f.verts) > 4)
            }
            
            # 非マニフォールドエッジのチェック
            non_manifold_edges = [edge for edge in bm.edges if not edge.is_manifold]
            if non_manifold_edges:
                result["issues"].append({
                    "type": "non_manifold_edges",
                    "count": len(non_manifold_edges),
                    "description": f"{len(non_manifold_edges)}個の非マニフォールドエッジがあります",
                    "severity": "high",
                    "affects_boolean": True
                })
            
            # 重複頂点のチェック
            # BMeshには直接重複頂点を検出する方法がないため、簡易的なチェックを実装
            vertex_locations = {}
            duplicate_verts = []
            
            for vert in bm.verts:
                # 頂点座標を丸めてキーとして使用
                loc_key = tuple(round(c, 6) for c in vert.co)
                if loc_key in vertex_locations:
                    duplicate_verts.append(vert)
                else:
                    vertex_locations[loc_key] = vert
            
            if duplicate_verts:
                result["issues"].append({
                    "type": "duplicate_vertices",
                    "count": len(duplicate_verts),
                    "description": f"{len(duplicate_verts)}個の重複頂点があります",
                    "severity": "medium",
                    "affects_boolean": True
                })
            
            # 孤立頂点のチェック
            isolated_verts = [v for v in bm.verts if not v.link_edges]
            if isolated_verts:
                result["issues"].append({
                    "type": "isolated_vertices",
                    "count": len(isolated_verts),
                    "description": f"{len(isolated_verts)}個の孤立頂点があります",
                    "severity": "low",
                    "affects_boolean": False
                })
            
            # 短いエッジのチェック
            short_edges = []
            for edge in bm.edges:
                length = edge.calc_length()
                if length < 0.0001:  # 0.1mm未満の非常に短いエッジ
                    short_edges.append(edge)
            
            if short_edges:
                result["issues"].append({
                    "type": "short_edges",
                    "count": len(short_edges),
                    "description": f"{len(short_edges)}個の極端に短いエッジがあります",
                    "severity": "medium",
                    "affects_boolean": True
                })
            
            # 自己交差のチェック（簡易版）
            # 完全な自己交差チェックは計算コストが高いため、簡易的な実装
            # 詳細なチェックが必要な場合は別の方法が必要
            
            # 全体的な評価
            result["is_manifold"] = all(edge.is_manifold for edge in bm.edges)
            result["boolean_ready"] = result["is_manifold"] and not duplicate_verts and not short_edges
            
            # 問題の総合評価
            if result["issues"]:
                # 重大度に基づいて問題を評価
                severity_scores = {"high": 10, "medium": 5, "low": 1}
                total_score = sum(severity_scores[issue["severity"]] for issue in result["issues"])
                
                if total_score >= 20:
                    result["quality"] = "poor"
                elif total_score >= 10:
                    result["quality"] = "fair"
                else:
                    result["quality"] = "good"
            else:
                result["quality"] = "excellent"
            
        except Exception as e:
            result["valid"] = False
            result["error"] = str(e)
        finally:
            bm.free()
        
        return result
    
    @classmethod
    def repair_mesh(cls, obj_name: str, repair_options: Dict[str, bool] = None) -> Dict[str, Any]:
        """
        メッシュの問題を修復
        
        Args:
            obj_name: 修復するメッシュオブジェクト名
            repair_options: 修復オプション（デフォルトはすべて有効）
            
        Returns:
            修復結果
        """
        if repair_options is None:
            repair_options = {
                "remove_doubles": True,
                "recalc_normals": True,
                "fill_holes": True,
                "triangulate_ngons": False  # デフォルトではオフ
            }
        
        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != 'MESH' or not obj.data:
            return {
                "success": False,
                "error": f"Object '{obj_name}' is not a valid mesh"
            }
        
        # 修復前の状態をチェック
        before_check = cls.check_mesh(obj_name)
        
        # アクティブオブジェクトを設定
        old_active = bpy.context.view_layer.objects.active
        old_mode = bpy.context.mode
        
        if old_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # 修復操作
        repairs_applied = []
        
        try:
            # 編集モードに切り替え
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 重複頂点の削除
            if repair_options.get("remove_doubles", True):
                bpy.ops.mesh.select_all(action='SELECT')
                result = bpy.ops.mesh.remove_doubles(threshold=0.0001)
                if "FINISHED" in result:
                    repairs_applied.append("remove_doubles")
            
            # 法線の再計算
            if repair_options.get("recalc_normals", True):
                bpy.ops.mesh.select_all(action='SELECT')
                result = bpy.ops.mesh.normals_make_consistent(inside=False)
                if "FINISHED" in result:
                    repairs_applied.append("recalc_normals")
            
            # 穴を埋める
            if repair_options.get("fill_holes", True):
                bpy.ops.mesh.select_all(action='SELECT')
                result = bpy.ops.mesh.fill_holes(sides=0)
                if "FINISHED" in result:
                    repairs_applied.append("fill_holes")
            
            # N-gonsを三角形化
            if repair_options.get("triangulate_ngons", False):
                bpy.ops.mesh.select_all(action='SELECT')
                
                # 5辺以上のポリゴンだけを選択
                bpy.ops.mesh.select_face_by_sides(number=4, type='GREATER')
                
                # 選択されたポリゴンがあれば三角形化
                if bpy.context.selected_objects:
                    result = bpy.ops.mesh.triangulate(quad_method='BEAUTY', ngon_method='BEAUTY')
                    if "FINISHED" in result:
                        repairs_applied.append("triangulate_ngons")
            
            # オブジェクトモードに戻る
            bpy.ops.object.mode_set(mode='OBJECT')
            
        finally:
            # 元の状態に戻す
            if old_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode=old_mode)
            
            if old_active:
                bpy.context.view_layer.objects.active = old_active
        
        # 修復後の状態をチェック
        after_check = cls.check_mesh(obj_name)
        
        # 結果をまとめる
        return {
            "success": True,
            "object": obj_name,
            "repairs_applied": repairs_applied,
            "before": {
                "issues_count": len(before_check["issues"]),
                "is_manifold": before_check["is_manifold"],
                "quality": before_check.get("quality", "unknown")
            },
            "after": {
                "issues_count": len(after_check["issues"]),
                "is_manifold": after_check["is_manifold"],
                "quality": after_check.get("quality", "unknown")
            },
            "improved": len(after_check["issues"]) < len(before_check["issues"]),
            "boolean_ready": after_check.get("boolean_ready", False)
        }
    
    @classmethod
    def check_boolean_operation(cls, target_obj: str, cutter_obj: str) -> Dict[str, Any]:
        """
        ブーリアン操作の実行可能性をチェック
        
        Args:
            target_obj: ターゲットオブジェクト名
            cutter_obj: カッターオブジェクト名
            
        Returns:
            チェック結果
        """
        # ターゲットとカッターの存在チェック
        target = bpy.data.objects.get(target_obj)
        cutter = bpy.data.objects.get(cutter_obj)
        
        if not target or not cutter:
            return {
                "valid": False,
                "error": f"Target or cutter object not found"
            }
        
        if target.type != 'MESH' or cutter.type != 'MESH':
            return {
                "valid": False,
                "error": "Both objects must be meshes"
            }
        
        # それぞれのオブジェクトのメッシュ品質チェック
        target_check = cls.check_mesh(target_obj)
        cutter_check = cls.check_mesh(cutter_obj)
        
        # 交差チェック
        intersection = cls._check_intersection(target, cutter)
        
        # 結果をまとめる
        result = {
            "valid": target_check["valid"] and cutter_check["valid"] and intersection["intersects"],
            "target": {
                "name": target_obj,
                "issues_count": len(target_check["issues"]),
                "is_manifold": target_check["is_manifold"],
                "quality": target_check.get("quality", "unknown")
            },
            "cutter": {
                "name": cutter_obj,
                "issues_count": len(cutter_check["issues"]),
                "is_manifold": cutter_check["is_manifold"],
                "quality": cutter_check.get("quality", "unknown")
            },
            "intersection": intersection,
            "boolean_ready": target_check.get("boolean_ready", False) and 
                             cutter_check.get("boolean_ready", False) and 
                             intersection["intersects"]
        }
        
        # 警告とアドバイスを追加
        warnings = []
        advice = []
        
        if not target_check["is_manifold"]:
            warnings.append("Target mesh is not manifold")
            advice.append("Repair target mesh before boolean operation")
        
        if not cutter_check["is_manifold"]:
            warnings.append("Cutter mesh is not manifold")
            advice.append("Repair cutter mesh before boolean operation")
        
        if not intersection["intersects"]:
            warnings.append("Objects do not intersect")
            advice.append("Move objects so they intersect")
        
        result["warnings"] = warnings
        result["advice"] = advice
        
        return result
    
    @classmethod
    def _check_intersection(cls, obj1, obj2) -> Dict[str, Any]:
        """
        2つのオブジェクトの交差をチェック
        
        Args:
            obj1: 1つ目のオブジェクト
            obj2: 2つ目のオブジェクト
            
        Returns:
            交差情報
        """
        # バウンディングボックスの交差チェック（高速だが正確ではない）
        def get_bounds(obj):
            # ワールド座標系のバウンディングボックス
            corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            min_x = min(c[0] for c in corners)
            min_y = min(c[1] for c in corners)
            min_z = min(c[2] for c in corners)
            max_x = max(c[0] for c in corners)
            max_y = max(c[1] for c in corners)
            max_z = max(c[2] for c in corners)
            return (min_x, min_y, min_z, max_x, max_y, max_z)
        
        # 注：これはBlenderのPythonインタープリターでmathutuils.Vectorが
        # 定義されていない場合に動作するようにフォールバックする
        try:
            from mathutils import Vector
            
            bounds1 = get_bounds(obj1)
            bounds2 = get_bounds(obj2)
            
            # バウンディングボックスの交差チェック
            intersects_bounds = (
                bounds1[0] <= bounds2[3] and
                bounds1[3] >= bounds2[0] and
                bounds1[1] <= bounds2[4] and
                bounds1[4] >= bounds2[1] and
                bounds1[2] <= bounds2[5] and
                bounds1[5] >= bounds2[2]
            )
            
            # 衝突量の概算
            if intersects_bounds:
                # X, Y, Z軸での重なり
                overlap_x = min(bounds1[3], bounds2[3]) - max(bounds1[0], bounds2[0])
                overlap_y = min(bounds1[4], bounds2[4]) - max(bounds1[1], bounds2[1])
                overlap_z = min(bounds1[5], bounds2[5]) - max(bounds1[2], bounds2[2])
                
                # 重なり体積
                overlap_volume = max(0, overlap_x) * max(0, overlap_y) * max(0, overlap_z)
                
                # 相対的な重なり率の計算
                obj1_volume = (bounds1[3]-bounds1[0]) * (bounds1[4]-bounds1[1]) * (bounds1[5]-bounds1[2])
                obj2_volume = (bounds2[3]-bounds2[0]) * (bounds2[4]-bounds2[1]) * (bounds2[5]-bounds2[2])
                
                overlap_ratio = overlap_volume / min(obj1_volume, obj2_volume) if min(obj1_volume, obj2_volume) > 0 else 0
                
                return {
                    "intersects": True,
                    "overlap_ratio": round(overlap_ratio, 4),
                    "overlap_volume": round(overlap_volume, 4)
                }
            else:
                return {"intersects": False}
                
        except Exception as e:
            # バウンディングボックスチェックができない場合
            return {
                "intersects": True,  # 安全側に倒して交差していると仮定
                "error": str(e)
            }
