"""
オブジェクトコンテキストモジュール
Blenderの個別オブジェクトに関する詳細情報を提供
"""

import bpy
import math
import bmesh
from mathutils import Vector
from typing import Dict, List, Any, Optional, Tuple
from .base_context import BaseContext

class ObjectContext(BaseContext):
    """
    Blenderの個別オブジェクト情報を取得・管理するクラス
    """
    
    @classmethod
    def get_object_info(cls, object_name: str, detail_level: str = "standard") -> Dict[str, Any]:
        """
        特定のオブジェクトの詳細情報を取得
        
        Args:
            object_name: 対象オブジェクト名
            detail_level: 詳細レベル ("basic", "standard", "detailed")
            
        Returns:
            オブジェクト情報
        """
        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"error": f"Object '{object_name}' not found"}
        
        # 基本情報（すべてのレベルで含まれる）- BaseContextから継承した共通メソッドを使用
        info = cls.get_object_basic_info(obj)
        
        # 標準以上のレベルなら追加情報
        if detail_level != "basic":
            info.update({
                "collections": [coll.name for coll in obj.users_collection],
                "data_name": obj.data.name if obj.data else None,
                "hide_render": obj.hide_render,
                "instance_type": obj.instance_type if obj.instance_type != 'NONE' else None
            })
            
            # タイプ別の特殊情報
            if obj.type == 'MESH':
                info.update(cls._get_mesh_details(obj, detail_level))
            elif obj.type == 'CAMERA':
                info.update(cls._get_camera_details(obj))
            elif obj.type == 'LIGHT':
                info.update(cls._get_light_details(obj))
            elif obj.type == 'ARMATURE':
                info.update(cls._get_armature_details(obj))
            elif obj.type == 'CURVE':
                info.update(cls._get_curve_details(obj))
            elif obj.type == 'EMPTY':
                info.update(cls._get_empty_details(obj))
        
        # 詳細レベルなら詳細情報
        if detail_level == "detailed":
            # モディファイア情報
            if obj.modifiers:
                info["modifiers"] = [{
                    "name": mod.name,
                    "type": mod.type,
                    "show_viewport": mod.show_viewport,
                    "show_render": mod.show_render
                } for mod in obj.modifiers]
            
            # マテリアル情報
            if obj.material_slots:
                info["materials"] = [{
                    "name": slot.material.name if slot.material else None,
                    "link": slot.link,
                    "index": i
                } for i, slot in enumerate(obj.material_slots)]
            
            # カスタムプロパティ
            if obj.keys():
                custom_props = {}
                for key in obj.keys():
                    if key != "_RNA_UI" and not key.startswith("cycles"):
                        try:
                            value = obj[key]
                            # 複雑なデータ型は文字列に変換
                            if isinstance(value, (list, dict, tuple, set)):
                                value = str(value)
                            custom_props[key] = value
                        except:
                            custom_props[key] = "不明な値"
                
                if custom_props:
                    info["custom_properties"] = custom_props
        
        return info
    
    @classmethod
    def _get_mesh_details(cls, obj, detail_level: str) -> Dict[str, Any]:
        """メッシュの詳細情報"""
        mesh = obj.data
        
        details = {
            "vertex_count": len(mesh.vertices),
            "edge_count": len(mesh.edges),
            "polygon_count": len(mesh.polygons),
            "material_count": len(obj.material_slots),
            "is_smooth": any(poly.use_smooth for poly in mesh.polygons)
        }
        
        # UVマップ情報
        if mesh.uv_layers:
            details["uv_maps"] = [uvmap.name for uvmap in mesh.uv_layers]
        
        # 頂点グループ情報
        if obj.vertex_groups:
            details["vertex_groups"] = [vg.name for vg in obj.vertex_groups]
        
        # 詳細レベルならさらに詳細情報
        if detail_level == "detailed":
            # トポロジー分析（共通の基底クラスのメソッドを使用）
            details.update(cls._analyze_mesh_topology(obj))
        
        return details
    
    @classmethod
    def _get_camera_details(cls, obj) -> Dict[str, Any]:
        """カメラの詳細情報"""
        camera = obj.data
        return {
            "lens": round(camera.lens, 2),
            "lens_unit": camera.lens_unit,
            "type": camera.type,
            "sensor_width": round(camera.sensor_width, 2),
            "sensor_height": round(camera.sensor_height, 2),
            "clip_start": round(camera.clip_start, 3),
            "clip_end": round(camera.clip_end, 1)
        }
    
    @classmethod
    def _get_light_details(cls, obj) -> Dict[str, Any]:
        """ライトの詳細情報"""
        light = obj.data
        details = {
            "type": light.type,
            "color": [round(c, 3) for c in light.color],
            "energy": round(light.energy, 2),
            "specular_factor": round(light.specular_factor, 2),
            "shadow": light.use_shadow
        }
        
        # ライトタイプ固有のパラメータ
        if light.type == 'POINT':
            details["radius"] = round(light.shadow_soft_size, 3)
        elif light.type == 'SPOT':
            details["spot_size"] = round(math.degrees(light.spot_size), 1)
            details["spot_blend"] = round(light.spot_blend, 3)
        elif light.type == 'SUN':
            details["angle"] = round(math.degrees(light.angle), 2)
        elif light.type == 'AREA':
            details["size"] = round(light.size, 3)
            if hasattr(light, 'size_y'):
                details["size_y"] = round(light.size_y, 3)
            details["shape"] = light.shape
            
        return details
    
    @classmethod
    def _get_armature_details(cls, obj) -> Dict[str, Any]:
        """アーマチュアの詳細情報"""
        armature = obj.data
        
        # ボーン情報
        bones = []
        for bone in armature.bones:
            bones.append({
                "name": bone.name,
                "length": round(bone.length, 4),
                "parent": bone.parent.name if bone.parent else None,
                "children": [child.name for child in bone.children]
            })
        
        return {
            "display_type": armature.display_type,
            "show_names": armature.show_names,
            "bones_count": len(armature.bones),
            "bones": bones
        }
    
    @classmethod
    def _get_curve_details(cls, obj) -> Dict[str, Any]:
        """カーブの詳細情報"""
        curve = obj.data
        return {
            "dimensions": curve.dimensions,
            "spline_count": len(curve.splines),
            "fill_mode": curve.fill_mode,
            "use_path": curve.use_path,
            "bevel_depth": round(curve.bevel_depth, 4),
            "extrude": round(curve.extrude, 4)
        }
    
    @classmethod
    def _get_empty_details(cls, obj) -> Dict[str, Any]:
        """空オブジェクトの詳細情報"""
        return {
            "empty_display_type": obj.empty_display_type,
            "empty_display_size": round(obj.empty_display_size, 4)
        }
    
    @classmethod
    def _analyze_mesh_topology(cls, obj) -> Dict[str, Any]:
        """メッシュのトポロジー分析"""
        mesh = obj.data
        
        # 基底クラスの共通メソッドを使用してトポロジーを分析
        topology_data = cls.analyze_mesh_topology(mesh)
        
        # ObjectContextのフォーマットに合わせる
        return {
            "topology": {
                "tris": topology_data["tris"],
                "quads": topology_data["quads"],
                "ngons": topology_data["ngons"]
            },
            "mesh_issues": {
                "non_manifold_edges": topology_data["manifold_analysis"].get("non_manifold_edges", 0),
                "non_manifold_vertices": topology_data["manifold_analysis"].get("non_manifold_vertices", 0),
                "has_issues": not topology_data["manifold_analysis"].get("is_manifold", True)
            }
        }