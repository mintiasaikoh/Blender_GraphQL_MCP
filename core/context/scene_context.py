"""
シーンコンテキストモジュール
Blenderのシーン状態を詳細に取得する機能を提供
"""

import bpy
import math
import bmesh
from mathutils import Vector
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from .base_context import BaseContext

class SceneContext(BaseContext):
    """
    Blenderのシーン情報を取得・管理するクラス
    """
    
    @classmethod
    def get_context(cls, detail_level: str = "standard") -> Dict[str, Any]:
        """
        現在のシーンコンテキストを取得
        
        Args:
            detail_level: 詳細レベル ("basic", "standard", "detailed")
            
        Returns:
            シーンコンテキスト情報
        """
        try:
            # 基本情報（どのレベルでも含まれる）
            context = {
                "system": cls._get_system_info(),
                "scene": cls._get_scene_info(),
                "selection": cls._get_selection_info()
            }
            
            # 標準以上のレベルならオブジェクト情報を追加
            if detail_level in ["standard", "detailed"]:
                context["objects"] = cls._get_objects_info(detail_level)
                context["collections"] = cls._get_collections_info()
                context["scene_bounds"] = cls._get_scene_bounds()
            
            # 詳細レベルならさらに詳細情報を追加
            if detail_level == "detailed":
                context["materials"] = cls._get_materials_info()
                context["spatial"] = cls._get_spatial_info()
                context["topology"] = cls._get_topology_info()
            
            return context
            
        except Exception as e:
            # エラーが発生した場合はエラー情報を返す
            import traceback
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "blender_version": ".".join(map(str, bpy.app.version))
            }
    
    @classmethod
    def _get_system_info(cls) -> Dict[str, Any]:
        """システム情報を取得"""
        return {
            "blender_version": ".".join(map(str, bpy.app.version)),
            "platform": bpy.app.build_platform.decode('utf-8') if hasattr(bpy.app, 'build_platform') else "unknown",
            "date": bpy.context.scene.get("date_info", "")
        }
    
    @classmethod
    def _get_scene_info(cls) -> Dict[str, Any]:
        """シーン情報を取得"""
        scene = bpy.context.scene
        return {
            "name": scene.name,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "render_engine": scene.render.engine,
            "unit_system": scene.unit_settings.system,
            "use_gravity": hasattr(scene, 'use_gravity') and scene.use_gravity,
            "objects_count": len(scene.objects),
            "active_object": bpy.context.active_object.name if bpy.context.active_object else None
        }
    
    @classmethod
    def _get_selection_info(cls) -> Dict[str, Any]:
        """選択情報を取得"""
        selected_objects = bpy.context.selected_objects
        
        return {
            "selected_count": len(selected_objects),
            "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
            "selected_objects": [obj.name for obj in selected_objects],
            "selected_types": {obj.type: selected_objects.count(obj.type) for obj in selected_objects} if selected_objects else {}
        }
    
    @classmethod
    def _get_objects_info(cls, detail_level: str) -> List[Dict[str, Any]]:
        """オブジェクト情報を取得"""
        objects_info = []
        
        # 取得対象のオブジェクト（制限が必要なら指定する）
        target_objects = bpy.context.scene.objects
        
        for obj in target_objects:
            # 基本クラスの共通メソッドを使用
            obj_info = cls.get_object_basic_info(obj)
            
            # タイプ固有の情報を追加（詳細レベルに応じて）
            if detail_level == "detailed" and obj.type == 'MESH' and obj.data:
                # メッシュ固有の情報
                mesh = obj.data
                obj_info.update({
                    "vertex_count": len(mesh.vertices),
                    "edge_count": len(mesh.edges),
                    "polygon_count": len(mesh.polygons),
                    "material_count": len(obj.material_slots)
                })
            
            objects_info.append(obj_info)
        
        return objects_info
    
    @classmethod
    def _get_collections_info(cls) -> List[Dict[str, Any]]:
        """コレクション情報を取得"""
        collections_info = []
        
        for coll in bpy.data.collections:
            collections_info.append({
                "name": coll.name,
                "objects": [obj.name for obj in coll.objects],
                "children": [child.name for child in coll.children]
            })
        
        return collections_info
    
    @classmethod
    def _get_scene_bounds(cls) -> Dict[str, Any]:
        """シーンの境界情報を取得"""
        # 全オブジェクトの頂点を考慮したシーン全体の境界を計算
        min_bounds = Vector((float('inf'), float('inf'), float('inf')))
        max_bounds = Vector((float('-inf'), float('-inf'), float('-inf')))
        
        # 境界計算に必要なオブジェクトのみを処理
        for obj in bpy.context.scene.objects:
            if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'ARMATURE', 'LATTICE'}:
                continue
                
            # ワールド座標空間での境界ボックスを取得
            for point in obj.bound_box:
                world_point = obj.matrix_world @ Vector(point)
                min_bounds.x = min(min_bounds.x, world_point.x)
                min_bounds.y = min(min_bounds.y, world_point.y)
                min_bounds.z = min(min_bounds.z, world_point.z)
                max_bounds.x = max(max_bounds.x, world_point.x)
                max_bounds.y = max(max_bounds.y, world_point.y)
                max_bounds.z = max(max_bounds.z, world_point.z)
        
        # 無限値がある場合（境界計算できず）、デフォルト値を設定
        if math.isinf(min_bounds.x) or math.isinf(max_bounds.x):
            min_bounds = Vector((-10, -10, -10))
            max_bounds = Vector((10, 10, 10))
        
        # シーンのサイズと中心点を計算
        dimensions = max_bounds - min_bounds
        center = (min_bounds + max_bounds) / 2
        
        return {
            "min": [round(v, 4) for v in min_bounds],
            "max": [round(v, 4) for v in max_bounds],
            "center": [round(v, 4) for v in center],
            "dimensions": [round(v, 4) for v in dimensions],
            "volume": round(dimensions.x * dimensions.y * dimensions.z, 4)
        }
    
    @classmethod
    def _get_materials_info(cls) -> List[Dict[str, Any]]:
        """マテリアル情報を取得"""
        materials_info = []
        
        for mat in bpy.data.materials:
            mat_info = {
                "name": mat.name,
                "users": mat.users,
                "use_nodes": mat.use_nodes,
                "is_grease_pencil": getattr(mat, 'is_grease_pencil', False)
            }
            
            # ノードベースのマテリアルの場合、基本的なノード情報を取得
            if mat.use_nodes and mat.node_tree:
                node_types = {}
                for node in mat.node_tree.nodes:
                    node_type = node.type
                    node_types[node_type] = node_types.get(node_type, 0) + 1
                
                mat_info["nodes"] = {
                    "count": len(mat.node_tree.nodes),
                    "types": node_types
                }
            
            materials_info.append(mat_info)
        
        return materials_info
    
    @classmethod
    def _get_spatial_info(cls) -> Dict[str, Any]:
        """空間関係の情報を取得"""
        # 各オブジェクトの近接オブジェクトを探す
        relationships = []
        objects = list(bpy.context.scene.objects)
        
        # 十分な数のオブジェクトがあるかチェック
        if len(objects) < 2:
            return {"objects_relationships": [], "origin_reference": {"objects_at_origin": []}}
            
        # 近接オブジェクトを見つける
        for obj in objects:
            if obj.type != 'MESH':
                continue
                
            obj_loc = obj.location
            neighbors = []
            
            for other in objects:
                if other == obj or other.type != 'MESH':
                    continue
                    
                # 距離計算
                distance = (other.location - obj_loc).length
                if distance < 10.0:  # 近接閾値
                    neighbors.append({
                        "name": other.name,
                        "distance": round(distance, 3)
                    })
            
            # 距離でソート
            neighbors.sort(key=lambda x: x["distance"])
            
            if neighbors:
                relationships.append({
                    "object": obj.name,
                    "neighbors": neighbors[:3]  # 最も近い3つのみ
                })
        
        return {
            "objects_relationships": relationships,
            "origin_reference": {
                "objects_at_origin": [
                    obj.name for obj in bpy.data.objects 
                    if all(abs(v) < 0.01 for v in obj.location)
                ]
            }
        }
    
    @classmethod
    def _get_topology_info(cls) -> Dict[str, Any]:
        """トポロジー情報を取得"""
        topology = {
            "total_quads": 0,
            "total_tris": 0,
            "total_ngons": 0,
            "objects": []
        }
        
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or not obj.data:
                continue
                
            mesh = obj.data
            
            # 基底クラスのメソッドを使用してトポロジーを分析
            mesh_topology = cls.analyze_mesh_topology(mesh)
            
            # トータルカウントを更新
            topology["total_quads"] += mesh_topology["quads"]
            topology["total_tris"] += mesh_topology["tris"]
            topology["total_ngons"] += mesh_topology["ngons"]
            
            # オブジェクト固有の情報を追加
            obj_topo = {
                "name": obj.name,
                "quads": mesh_topology["quads"],
                "tris": mesh_topology["tris"],
                "ngons": mesh_topology["ngons"]
            }
            
            # 非マニフォールド情報があれば追加
            if "manifold_analysis" in mesh_topology:
                obj_topo["non_manifold_edges"] = mesh_topology["manifold_analysis"]["non_manifold_edges"]
                obj_topo["is_manifold"] = mesh_topology["manifold_analysis"]["is_manifold"]
            
            topology["objects"].append(obj_topo)
        
        return topology