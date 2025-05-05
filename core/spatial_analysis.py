"""
Spatial Analysis Module - 空間分析と検証機能
"""

import bpy
import bmesh
import mathutils
from mathutils.bvhtree import BVHTree
import math
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
import logging

# ロギング設定
logger = logging.getLogger(__name__)

def analyze_scene_space() -> Dict[str, Any]:
    """
    シーン全体の空間分析を実行
    
    Returns:
        Dict: 空間分析結果
    """
    scene = bpy.context.scene
    objects = [obj for obj in scene.objects if obj.type == 'MESH' and obj.visible_get()]
    
    if not objects:
        return {
            "status": "warning", 
            "message": "No visible mesh objects found in scene",
            "data": {}
        }
    
    # バウンディングボックスの計算
    bounds_min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    bounds_max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
    
    for obj in objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            bounds_min.x = min(bounds_min.x, world_corner.x)
            bounds_min.y = min(bounds_min.y, world_corner.y)
            bounds_min.z = min(bounds_min.z, world_corner.z)
            bounds_max.x = max(bounds_max.x, world_corner.x)
            bounds_max.y = max(bounds_max.y, world_corner.y)
            bounds_max.z = max(bounds_max.z, world_corner.z)
    
    # シーンの寸法と中心
    dimensions = bounds_max - bounds_min
    center = (bounds_min + bounds_max) / 2
    
    # 占有グリッド計算
    grid_size = 10
    occupancy_grid = calculate_occupancy_grid(objects, bounds_min, bounds_max, grid_size)
    
    # オブジェクト間の距離行列
    distances = calculate_distances_matrix(objects)
    
    # 衝突検出
    collisions = detect_collisions(objects)
    
    return {
        "status": "success",
        "message": "Scene space analysis completed",
        "data": {
            "bounds": {
                "min": [round(v, 6) for v in bounds_min],
                "max": [round(v, 6) for v in bounds_max],
                "dimensions": [round(v, 6) for v in dimensions],
                "center": [round(v, 6) for v in center],
                "volume": round(dimensions.x * dimensions.y * dimensions.z, 6)
            },
            "objects_count": len(objects),
            "occupancy": {
                "grid_size": grid_size,
                "occupied_cells": occupancy_grid["occupied_count"],
                "total_cells": occupancy_grid["total_count"],
                "occupancy_rate": occupancy_grid["occupancy_rate"]
            },
            "distances": {
                "min_distance": distances["min_distance"],
                "max_distance": distances["max_distance"],
                "avg_distance": distances["avg_distance"],
                "closest_pair": distances["closest_pair"]
            },
            "collisions": {
                "count": len(collisions),
                "pairs": collisions[:10]  # 最初の10個の衝突ペアのみ
            }
        }
    }

def calculate_occupancy_grid(objects: List[bpy.types.Object], 
                             min_bounds: mathutils.Vector, 
                             max_bounds: mathutils.Vector, 
                             grid_size: int) -> Dict[str, Any]:
    """
    空間占有グリッドを計算
    
    Args:
        objects: メッシュオブジェクトのリスト
        min_bounds: シーンの最小境界
        max_bounds: シーンの最大境界
        grid_size: グリッドの分割数
        
    Returns:
        Dict: 占有グリッド情報
    """
    # グリッドの初期化
    cell_size = [(max_bounds[i] - min_bounds[i]) / grid_size for i in range(3)]
    grid = np.zeros((grid_size, grid_size, grid_size), dtype=bool)
    
    # 各オブジェクトのバウンディングボックスをグリッドにマッピング
    for obj in objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            
            # グリッド座標に変換
            grid_x = int((world_corner.x - min_bounds.x) / cell_size[0])
            grid_y = int((world_corner.y - min_bounds.y) / cell_size[1])
            grid_z = int((world_corner.z - min_bounds.z) / cell_size[2])
            
            # 境界チェック
            grid_x = max(0, min(grid_x, grid_size - 1))
            grid_y = max(0, min(grid_y, grid_size - 1))
            grid_z = max(0, min(grid_z, grid_size - 1))
            
            # セルを占有としてマーク
            grid[grid_x, grid_y, grid_z] = True
    
    # 占有率の計算
    occupied_count = np.sum(grid)
    total_count = grid_size ** 3
    occupancy_rate = occupied_count / total_count
    
    return {
        "occupied_count": int(occupied_count),
        "total_count": total_count,
        "occupancy_rate": round(occupancy_rate, 4),
        "cell_size": [round(s, 4) for s in cell_size]
    }

def calculate_distances_matrix(objects: List[bpy.types.Object]) -> Dict[str, Any]:
    """
    オブジェクト間の距離行列を計算
    
    Args:
        objects: メッシュオブジェクトのリスト
        
    Returns:
        Dict: 距離情報
    """
    n = len(objects)
    if n <= 1:
        return {
            "min_distance": None,
            "max_distance": None,
            "avg_distance": None,
            "closest_pair": None
        }
    
    # 距離行列の初期化
    distances = []
    min_distance = float('inf')
    max_distance = 0
    closest_pair = None
    
    # 各オブジェクトペアの距離を計算
    for i in range(n):
        for j in range(i + 1, n):
            obj1, obj2 = objects[i], objects[j]
            dist = calculate_object_distance(obj1, obj2)
            
            distance_entry = {
                "object1": obj1.name,
                "object2": obj2.name,
                "distance": round(dist, 6)
            }
            distances.append(distance_entry)
            
            if dist < min_distance:
                min_distance = dist
                closest_pair = (obj1.name, obj2.name)
            
            max_distance = max(max_distance, dist)
    
    # 平均距離を計算
    avg_distance = sum(entry["distance"] for entry in distances) / len(distances)
    
    return {
        "min_distance": round(min_distance, 6),
        "max_distance": round(max_distance, 6),
        "avg_distance": round(avg_distance, 6),
        "closest_pair": closest_pair,
        "matrix": distances[:20]  # 最初の20個のエントリのみ
    }

def calculate_object_distance(obj1: bpy.types.Object, obj2: bpy.types.Object) -> float:
    """
    2つのオブジェクト間の最短距離を計算
    
    Args:
        obj1: 1つ目のオブジェクト
        obj2: 2つ目のオブジェクト
        
    Returns:
        float: オブジェクト間の最短距離
    """
    # バウンディングボックスの中心間の距離を計算（近似値）
    center1 = obj1.matrix_world @ (mathutils.Vector(obj1.bound_box[0]) + mathutils.Vector(obj1.bound_box[6])) / 2
    center2 = obj2.matrix_world @ (mathutils.Vector(obj2.bound_box[0]) + mathutils.Vector(obj2.bound_box[6])) / 2
    
    # 近似距離を計算
    approximate_distance = (center2 - center1).length
    
    # 近接している場合は、より正確な計算を行う
    if approximate_distance < (obj1.dimensions.length + obj2.dimensions.length):
        # メッシュデータを取得
        bm1 = bmesh.new()
        bm1.from_mesh(obj1.data)
        bm1.transform(obj1.matrix_world)
        
        bm2 = bmesh.new()
        bm2.from_mesh(obj2.data)
        bm2.transform(obj2.matrix_world)
        
        # BVHツリーを構築
        bvh1 = BVHTree.FromBMesh(bm1)
        bvh2 = BVHTree.FromBMesh(bm2)
        
        # 最短距離を計算
        distance = bvh1.find_nearest_range(bvh2, max_dist=1000.0)
        
        # BMeshを解放
        bm1.free()
        bm2.free()
        
        if distance:
            return min(d[0] for d in distance)
    
    # 簡易計算または正確な計算ができなかった場合は近似値を返す
    return approximate_distance

def detect_collisions(objects: List[bpy.types.Object]) -> List[Tuple[str, str]]:
    """
    オブジェクト間の衝突を検出
    
    Args:
        objects: メッシュオブジェクトのリスト
        
    Returns:
        List[Tuple[str, str]]: 衝突するオブジェクトペアのリスト
    """
    collisions = []
    n = len(objects)
    
    for i in range(n):
        for j in range(i + 1, n):
            obj1, obj2 = objects[i], objects[j]
            
            # メッシュデータを取得
            bm1 = bmesh.new()
            bm1.from_mesh(obj1.data)
            bm1.transform(obj1.matrix_world)
            
            bm2 = bmesh.new()
            bm2.from_mesh(obj2.data)
            bm2.transform(obj2.matrix_world)
            
            # BVHツリーを構築
            bvh1 = BVHTree.FromBMesh(bm1)
            bvh2 = BVHTree.FromBMesh(bm2)
            
            # 交差チェック
            intersect = bvh1.overlap(bvh2)
            
            # BMeshを解放
            bm1.free()
            bm2.free()
            
            if intersect:
                collisions.append((obj1.name, obj2.name))
    
    return collisions

def analyze_object_relations(object_name: str) -> Dict[str, Any]:
    """
    指定オブジェクトと他のオブジェクトとの関係を分析
    
    Args:
        object_name: 分析するオブジェクト名
        
    Returns:
        Dict: オブジェクト関係の分析結果
    """
    obj = bpy.data.objects.get(object_name)
    
    if not obj:
        return {
            "status": "error",
            "message": f"Object {object_name} not found",
            "data": {}
        }
    
    # 他のメッシュオブジェクト
    other_objects = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o != obj and o.visible_get()]
    
    if not other_objects:
        return {
            "status": "warning",
            "message": f"No other mesh objects to analyze relations with {object_name}",
            "data": {
                "object": object_name,
                "position": [round(v, 6) for v in obj.location],
                "dimensions": [round(v, 6) for v in obj.dimensions]
            }
        }
    
    # 近接オブジェクト
    proximity_data = []
    for other in other_objects:
        distance = calculate_object_distance(obj, other)
        proximity_data.append({
            "object": other.name,
            "distance": round(distance, 6),
            "direction": normalize_vector(
                (other.matrix_world.translation - obj.matrix_world.translation).normalized()
            )
        })
    
    # 距離でソート
    proximity_data.sort(key=lambda x: x["distance"])
    
    # 衝突検出
    collisions = []
    for other in other_objects:
        # BVHツリーで交差チェック
        bm1 = bmesh.new()
        bm1.from_mesh(obj.data)
        bm1.transform(obj.matrix_world)
        
        bm2 = bmesh.new()
        bm2.from_mesh(other.data)
        bm2.transform(other.matrix_world)
        
        bvh1 = BVHTree.FromBMesh(bm1)
        bvh2 = BVHTree.FromBMesh(bm2)
        
        intersect = bvh1.overlap(bvh2)
        
        bm1.free()
        bm2.free()
        
        if intersect:
            collisions.append(other.name)
    
    # 空間関係（上、下、左、右、前、後ろ）
    world_matrix = obj.matrix_world
    obj_center = world_matrix @ (mathutils.Vector(obj.bound_box[0]) + mathutils.Vector(obj.bound_box[6])) / 2
    
    spatial_relations = []
    for other in other_objects:
        other_matrix = other.matrix_world
        other_center = other_matrix @ (mathutils.Vector(other.bound_box[0]) + mathutils.Vector(other.bound_box[6])) / 2
        
        # 相対方向ベクトル
        direction = other_center - obj_center
        
        # 主要な方向を特定
        abs_x, abs_y, abs_z = abs(direction.x), abs(direction.y), abs(direction.z)
        max_component = max(abs_x, abs_y, abs_z)
        
        relation = ""
        if max_component == abs_x:
            relation = "right" if direction.x > 0 else "left"
        elif max_component == abs_y:
            relation = "front" if direction.y > 0 else "back"
        else:
            relation = "above" if direction.z > 0 else "below"
        
        spatial_relations.append({
            "object": other.name,
            "relation": relation,
            "distance": round((other_center - obj_center).length, 6)
        })
    
    return {
        "status": "success",
        "message": f"Analyzed relations for {object_name}",
        "data": {
            "object": object_name,
            "position": [round(v, 6) for v in obj.location],
            "dimensions": [round(v, 6) for v in obj.dimensions],
            "proximity": proximity_data[:5],  # 近い順に5つのオブジェクト
            "collisions": collisions,
            "spatial_relations": spatial_relations[:5]  # 5つの空間関係
        }
    }

def normalize_vector(vec: mathutils.Vector) -> List[float]:
    """
    ベクトルを正規化して配列として返す
    
    Args:
        vec: 正規化するベクトル
        
    Returns:
        List[float]: 正規化されたベクトル
    """
    return [round(v, 4) for v in vec]

def compare_states(before_state: Dict[str, Any], after_state: Dict[str, Any], 
                  focus_areas: List[str] = None) -> Dict[str, Any]:
    """
    2つの状態を比較
    
    Args:
        before_state: 変更前の状態
        after_state: 変更後の状態
        focus_areas: 注目する領域リスト
        
    Returns:
        Dict: 比較結果
    """
    if not focus_areas:
        focus_areas = ["geometry", "topology", "dimensions", "statistics"]
    
    comparison = {
        "status": "success",
        "message": "State comparison completed",
        "summary": {},
        "details": {}
    }
    
    # オブジェクトの存在確認
    before_objects = set(before_state.get("objects", {}).keys())
    after_objects = set(after_state.get("objects", {}).keys())
    
    added_objects = after_objects - before_objects
    removed_objects = before_objects - after_objects
    common_objects = before_objects.intersection(after_objects)
    
    comparison["summary"]["objects"] = {
        "before_count": len(before_objects),
        "after_count": len(after_objects),
        "added": list(added_objects),
        "removed": list(removed_objects),
        "modified": [],  # 変更されたオブジェクトリスト（後で追加）
        "unchanged": []  # 変更されていないオブジェクトリスト（後で追加）
    }
    
    # 共通オブジェクトの変更を分析
    modified_objects = []
    unchanged_objects = []
    object_changes = {}
    
    for obj_name in common_objects:
        before_obj = before_state.get("objects", {}).get(obj_name, {})
        after_obj = after_state.get("objects", {}).get(obj_name, {})
        
        changes = {}
        is_modified = False
        
        # ジオメトリの比較
        if "geometry" in focus_areas:
            geo_changes = compare_geometry(before_obj.get("geometry", {}), after_obj.get("geometry", {}))
            if geo_changes["changed"]:
                changes["geometry"] = geo_changes
                is_modified = True
        
        # 寸法の比較
        if "dimensions" in focus_areas:
            dim_changes = compare_dimensions(before_obj.get("dimensions", []), after_obj.get("dimensions", []))
            if dim_changes["changed"]:
                changes["dimensions"] = dim_changes
                is_modified = True
        
        # トポロジーの比較
        if "topology" in focus_areas:
            topo_changes = compare_topology(before_obj.get("topology", {}), after_obj.get("topology", {}))
            if topo_changes["changed"]:
                changes["topology"] = topo_changes
                is_modified = True
        
        # マテリアルの比較
        if "materials" in focus_areas:
            mat_changes = compare_materials(before_obj.get("materials", []), after_obj.get("materials", []))
            if mat_changes["changed"]:
                changes["materials"] = mat_changes
                is_modified = True
        
        # 変更されたかどうかを記録
        if is_modified:
            modified_objects.append(obj_name)
            object_changes[obj_name] = changes
        else:
            unchanged_objects.append(obj_name)
    
    comparison["summary"]["objects"]["modified"] = modified_objects
    comparison["summary"]["objects"]["unchanged"] = unchanged_objects
    comparison["details"]["object_changes"] = object_changes
    
    # 全体的な統計変化
    if "statistics" in focus_areas:
        before_stats = before_state.get("statistics", {})
        after_stats = after_state.get("statistics", {})
        comparison["summary"]["statistics"] = compare_statistics(before_stats, after_stats)
    
    return comparison

def compare_geometry(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    ジオメトリデータを比較
    
    Args:
        before: 変更前のジオメトリデータ
        after: 変更後のジオメトリデータ
        
    Returns:
        Dict: 比較結果
    """
    result = {"changed": False, "changes": {}}
    
    # 比較するキー
    keys = ["vertices_count", "edges_count", "faces_count", "triangles", "quads", "ngons"]
    
    for key in keys:
        if key in before and key in after:
            before_val = before.get(key, 0)
            after_val = after.get(key, 0)
            
            if before_val != after_val:
                result["changed"] = True
                result["changes"][key] = {
                    "before": before_val,
                    "after": after_val,
                    "diff": after_val - before_val,
                    "percent": round((after_val - before_val) / max(before_val, 1) * 100, 2)
                }
    
    # 体積と面積
    volume_before = before.get("volume", 0)
    volume_after = after.get("volume", 0)
    
    if abs(volume_before - volume_after) > 0.0001:
        result["changed"] = True
        result["changes"]["volume"] = {
            "before": volume_before,
            "after": volume_after,
            "diff": volume_after - volume_before,
            "percent": round((volume_after - volume_before) / max(volume_before, 0.0001) * 100, 2)
        }
    
    area_before = before.get("area", 0)
    area_after = after.get("area", 0)
    
    if abs(area_before - area_after) > 0.0001:
        result["changed"] = True
        result["changes"]["area"] = {
            "before": area_before,
            "after": area_after,
            "diff": area_after - area_before,
            "percent": round((area_after - area_before) / max(area_before, 0.0001) * 100, 2)
        }
    
    return result

def compare_dimensions(before: List[float], after: List[float]) -> Dict[str, Any]:
    """
    寸法データを比較
    
    Args:
        before: 変更前の寸法
        after: 変更後の寸法
        
    Returns:
        Dict: 比較結果
    """
    result = {"changed": False, "changes": {}}
    
    if not before or not after or len(before) != len(after):
        return result
    
    # X, Y, Z寸法の比較
    dim_names = ["X", "Y", "Z"]
    
    for i, name in enumerate(dim_names):
        if i < len(before) and i < len(after):
            before_val = before[i]
            after_val = after[i]
            
            if abs(before_val - after_val) > 0.0001:
                result["changed"] = True
                result["changes"][name] = {
                    "before": before_val,
                    "after": after_val,
                    "diff": after_val - before_val,
                    "percent": round((after_val - before_val) / max(before_val, 0.0001) * 100, 2)
                }
    
    return result

def compare_topology(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    トポロジーデータを比較
    
    Args:
        before: 変更前のトポロジーデータ
        after: 変更後のトポロジーデータ
        
    Returns:
        Dict: 比較結果
    """
    result = {"changed": False, "changes": {}}
    
    # 比較するトポロジー属性
    keys = ["manifold", "non_manifold_edges", "non_manifold_vertices", "loose_edges", "n_poles"]
    
    for key in keys:
        if key in before and key in after:
            before_val = before.get(key, 0 if key != "manifold" else False)
            after_val = after.get(key, 0 if key != "manifold" else False)
            
            if before_val != after_val:
                result["changed"] = True
                
                if key == "manifold":
                    result["changes"][key] = {
                        "before": before_val,
                        "after": after_val,
                        "improved": after_val and not before_val
                    }
                else:
                    result["changes"][key] = {
                        "before": before_val,
                        "after": after_val,
                        "diff": after_val - before_val,
                        "improved": after_val < before_val
                    }
    
    return result

def compare_materials(before: List[str], after: List[str]) -> Dict[str, Any]:
    """
    マテリアルリストを比較
    
    Args:
        before: 変更前のマテリアルリスト
        after: 変更後のマテリアルリスト
        
    Returns:
        Dict: 比較結果
    """
    result = {"changed": False, "changes": {}}
    
    before_set = set(before)
    after_set = set(after)
    
    added = after_set - before_set
    removed = before_set - after_set
    
    if added or removed:
        result["changed"] = True
        result["changes"] = {
            "added": list(added),
            "removed": list(removed),
            "before_count": len(before),
            "after_count": len(after)
        }
    
    return result

def compare_statistics(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    統計データを比較
    
    Args:
        before: 変更前の統計データ
        after: 変更後の統計データ
        
    Returns:
        Dict: 比較結果
    """
    result = {"changed": False, "changes": {}}
    
    # 比較する統計属性
    keys = ["total_vertices", "total_edges", "total_faces", "total_objects", 
            "total_meshes", "total_materials", "total_volume", "total_area"]
    
    for key in keys:
        if key in before and key in after:
            before_val = before.get(key, 0)
            after_val = after.get(key, 0)
            
            if abs(before_val - after_val) > 0.0001:
                result["changed"] = True
                result["changes"][key] = {
                    "before": before_val,
                    "after": after_val,
                    "diff": after_val - before_val,
                    "percent": round((after_val - before_val) / max(before_val, 0.0001) * 100, 2)
                }
    
    return result
