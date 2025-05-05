"""
基底コンテキストモジュール
コンテキスト分析の共通機能を提供する基底クラス
"""

import bpy
import bmesh
from typing import Dict, List, Any, Optional, Tuple, Set, Union

class BaseContext:
    """
    コンテキスト分析のための共通機能を提供する基底クラス
    シーンとオブジェクトのコンテキストクラスで共有される共通メソッドを含む
    """
    
    @staticmethod
    def analyze_mesh_topology(mesh) -> Dict[str, Any]:
        """
        メッシュのトポロジー分析を行う共通メソッド
        
        Args:
            mesh: 分析対象のメッシュデータ
            
        Returns:
            トポロジー分析結果
        """
        # ポリゴンタイプのカウント
        tris_count = quads_count = ngons_count = 0
        for poly in mesh.polygons:
            vert_count = len(poly.vertices)
            if vert_count == 3:
                tris_count += 1
            elif vert_count == 4:
                quads_count += 1
            else:
                ngons_count += 1
        
        topology = {
            "tris": tris_count,
            "quads": quads_count,
            "ngons": ngons_count,
            "total_polys": tris_count + quads_count + ngons_count
        }
        
        # 非マニフォールド要素のチェック
        try:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            
            non_manifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
            non_manifold_verts = sum(1 for vert in bm.verts if not all(edge.is_manifold for edge in vert.link_edges))
            
            topology["manifold_analysis"] = {
                "non_manifold_edges": non_manifold_edges,
                "non_manifold_vertices": non_manifold_verts,
                "is_manifold": non_manifold_edges == 0 and non_manifold_verts == 0
            }
            
            bm.free()
        except Exception as e:
            # BMeshエラーがあれば無視
            topology["manifold_analysis"] = {
                "error": str(e),
                "is_manifold": None
            }
        
        return topology
    
    @staticmethod
    def get_object_basic_info(obj) -> Dict[str, Any]:
        """
        オブジェクトの基本情報を取得する共通メソッド
        
        Args:
            obj: 情報を取得するオブジェクト
            
        Returns:
            オブジェクトの基本情報
        """
        import math
        
        return {
            "name": obj.name,
            "type": obj.type,
            "location": [round(v, 4) for v in obj.location],
            "rotation": [round(math.degrees(v), 2) for v in obj.rotation_euler],
            "scale": [round(v, 4) for v in obj.scale],
            "dimensions": [round(v, 4) for v in obj.dimensions],
            "visible": not obj.hide_viewport,
            "selected": obj.select_get(),
            "parent": obj.parent.name if obj.parent else None,
            "children_count": len(obj.children)
        }