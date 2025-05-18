"""
Numpy/Pandas最適化されたGraphQLリゾルバモジュール
高速なグラフィック処理とデータ操作のためのリゾルバ実装
"""

import time
import logging
import bpy
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

# 依存モジュールをインポート
from ..core.numpy_optimizers import (
    fast_vertex_transform,
    fast_mesh_analysis,
    find_nearest_objects,
    fast_raycast,
    batch_vertex_colors
)
from ..core.pandas_optimizers import (
    batch_object_properties,
    material_analysis,
    scene_hierarchy_analysis,
    BatchProcessor
)
from ..core.query_cache import GraphQLQueryCache

logger = logging.getLogger("blender_graphql_mcp.optimized_resolver")

# グローバルキャッシュインスタンス
query_cache = GraphQLQueryCache(max_size=200, ttl=30)

class OptimizedResolver:
    """Numpy/Pandasを活用した最適化されたGraphQLリゾルバ"""
    
    def __init__(self):
        self.dataframes = {}
        self.cache = query_cache
        self.performance_stats = {
            'total_queries': 0,
            'cached_queries': 0,
            'avg_response_time': 0
        }
    
    def prepare_dataframes(self):
        """頻繁にアクセスされるデータのDataFrameを準備"""
        try:
            # オブジェクトデータ
            objects_data = []
            for obj in bpy.data.objects:
                obj_data = {
                    'name': obj.name,
                    'type': obj.type,
                    'verts': len(obj.data.vertices) if obj.type == 'MESH' and obj.data else 0,
                    'location': [obj.location.x, obj.location.y, obj.location.z]
                }
                objects_data.append(obj_data)
            
            self.dataframes['objects'] = pd.DataFrame(objects_data)
            
            # マテリアルデータ
            materials_data = []
            for mat in bpy.data.materials:
                mat_data = {
                    'name': mat.name,
                    'users': mat.users,
                    'use_nodes': mat.use_nodes
                }
                materials_data.append(mat_data)
            
            self.dataframes['materials'] = pd.DataFrame(materials_data)
            
            logger.info(f"DataFrameを準備: {len(objects_data)}オブジェクト, {len(materials_data)}マテリアル")
        except Exception as e:
            logger.error(f"DataFrame準備中にエラー発生: {str(e)}")
    
    def invalidate_dataframes(self):
        """キャッシュされたDataFrameを無効化"""
        self.dataframes = {}
        logger.info("キャッシュされたDataFrameを無効化")
    
    # GraphQLリゾルバメソッド
    
    def resolve_objects(self, info, **kwargs):
        """シーン内のオブジェクトを解決
        
        Args:
            info: GraphQLの解決情報
            **kwargs: フィルタリングパラメータ
        
        Returns:
            list: オブジェクト情報のリスト
        """
        start_time = time.time()
        
        # キャッシュをチェック
        cache_key = f"resolve_objects:{str(kwargs)}"
        cached_result = self.cache.get(cache_key, {})
        if cached_result:
            logger.debug(f"objectsクエリのキャッシュヒット: {time.time() - start_time:.4f}秒")
            return cached_result
        
        # キャッシュされたDataFrameがなければ準備
        if 'objects' not in self.dataframes:
            self.prepare_dataframes()
        
        # DataFrameの取得とフィルタリング
        df = self.dataframes.get('objects', pd.DataFrame())
        if df.empty:
            logger.warning("オブジェクトDataFrameが空です")
            return []
        
        # 各種フィルタリング
        if 'type' in kwargs:
            df = df[df['type'] == kwargs['type']]
        
        if 'min_verts' in kwargs:
            df = df[df['verts'] >= kwargs['min_verts']]
            
        if 'name_contains' in kwargs:
            df = df[df['name'].str.contains(kwargs['name_contains'], na=False)]
        
        # 結果を生成
        result = df.to_dict('records')
        
        # オブジェクトの詳細情報を追加
        for i, obj_data in enumerate(result):
            obj_name = obj_data['name']
            obj = bpy.data.objects.get(obj_name)
            if obj:
                result[i].update({
                    'dimensions': [obj.dimensions.x, obj.dimensions.y, obj.dimensions.z],
                    'visible': obj.visible_get()
                })
        
        # キャッシュに保存
        self.cache.set(cache_key, result)
        
        processing_time = time.time() - start_time
        logger.info(f"objectsクエリ実行: {len(result)}件, 処理時間: {processing_time:.4f}秒")
        
        # パフォーマンス統計を更新
        self.performance_stats['total_queries'] += 1
        self.performance_stats['avg_response_time'] = (
            (self.performance_stats['avg_response_time'] * (self.performance_stats['total_queries'] - 1)) 
            + processing_time
        ) / self.performance_stats['total_queries']
        
        return result
    
    def resolve_analyze_mesh(self, info, name):
        """メッシュの詳細分析を実行
        
        Args:
            info: GraphQLの解決情報
            name: 分析対象のオブジェクト名
        
        Returns:
            dict: メッシュ分析結果
        """
        start_time = time.time()
        
        # キャッシュをチェック
        cache_key = f"analyze_mesh:{name}"
        cached_result = self.cache.get(cache_key, {})
        if cached_result:
            logger.debug(f"analyze_meshクエリのキャッシュヒット: {time.time() - start_time:.4f}秒")
            return cached_result
        
        # NumPy最適化メッシュ分析を実行
        result = fast_mesh_analysis(name)
        
        # キャッシュに保存
        if 'error' not in result:
            self.cache.set(cache_key, result)
        
        processing_time = time.time() - start_time
        logger.info(f"analyze_meshクエリ実行: {name}, 処理時間: {processing_time:.4f}秒")
        
        return result
    
    def resolve_nearest_objects(self, info, origin, max_distance=10.0, object_types=None):
        """原点から最も近いオブジェクトを検索
        
        Args:
            info: GraphQLの解決情報
            origin: 検索原点 [x, y, z]
            max_distance: 最大検索距離
            object_types: 検索対象のオブジェクトタイプリスト
        
        Returns:
            list: 距離順にソートされたオブジェクト情報
        """
        start_time = time.time()
        
        # NumPy最適化近傍検索を実行
        result = find_nearest_objects(origin, max_distance, object_types)
        
        processing_time = time.time() - start_time
        logger.info(f"nearest_objectsクエリ実行: {len(result)}件, 処理時間: {processing_time:.4f}秒")
        
        return result
    
    def resolve_batch_transform(self, info, transforms):
        """複数オブジェクトの一括変換を実行
        
        Args:
            info: GraphQLの解決情報
            transforms: 変換情報のリスト
        
        Returns:
            dict: 処理結果
        """
        start_time = time.time()
        
        # Pandas最適化バッチ処理を実行
        result = BatchProcessor.batch_transform(transforms)
        
        # バッチ処理後にDataFrameキャッシュを無効化（状態が変更されたため）
        self.invalidate_dataframes()
        
        # 関連キャッシュも無効化
        self.cache.invalidate_type("Object")
        
        processing_time = time.time() - start_time
        logger.info(f"batch_transform実行: {len(transforms)}件, 処理時間: {processing_time:.4f}秒")
        
        return result
    
    def resolve_scene_analysis(self, info):
        """シーン全体の詳細分析を実行
        
        Args:
            info: GraphQLの解決情報
        
        Returns:
            dict: シーン分析結果
        """
        start_time = time.time()
        
        # キャッシュをチェック
        cache_key = "scene_analysis"
        cached_result = self.cache.get(cache_key, {})
        if cached_result:
            logger.debug(f"scene_analysisクエリのキャッシュヒット: {time.time() - start_time:.4f}秒")
            return cached_result
        
        # 各種分析を実行
        object_data = batch_object_properties()
        hierarchy_data = scene_hierarchy_analysis()
        material_data = material_analysis()
        
        # 結果を統合
        result = {
            'objects': object_data,
            'hierarchy': hierarchy_data,
            'materials': material_data,
            'processing_time_ms': (time.time() - start_time) * 1000
        }
        
        # キャッシュに保存
        self.cache.set(cache_key, result)
        
        processing_time = time.time() - start_time
        logger.info(f"scene_analysisクエリ実行: 処理時間: {processing_time:.4f}秒")
        
        return result
    
    def resolve_raycast(self, info, origin, direction, max_distance=100.0):
        """レイキャストを実行
        
        Args:
            info: GraphQLの解決情報
            origin: レイの開始点 [x, y, z]
            direction: レイの方向 [x, y, z]
            max_distance: 最大検索距離
        
        Returns:
            dict: ヒット情報
        """
        start_time = time.time()
        
        # NumPy最適化レイキャストを実行
        result = fast_raycast(origin, direction, max_distance)
        
        processing_time = time.time() - start_time
        logger.info(f"raycastクエリ実行: 処理時間: {processing_time:.4f}秒")
        
        return result
    
    def resolve_transform_vertices(self, info, object_name, transform_matrix):
        """オブジェクトの頂点を変換
        
        Args:
            info: GraphQLの解決情報
            object_name: 対象オブジェクト名
            transform_matrix: 4x4変換行列（16要素のリスト）
        
        Returns:
            dict: 処理結果
        """
        start_time = time.time()
        
        # NumPy最適化頂点変換を実行
        success = fast_vertex_transform(object_name, transform_matrix)
        
        # 変換後にキャッシュを無効化
        self.cache.invalidate_type("Mesh")
        
        processing_time = time.time() - start_time
        logger.info(f"transform_verticesミューテーション実行: {object_name}, 処理時間: {processing_time:.4f}秒")
        
        return {
            'success': success,
            'object_name': object_name,
            'processing_time_ms': processing_time * 1000
        }
    
    def resolve_set_vertex_colors(self, info, object_name, color_data, algorithm='mean'):
        """頂点カラーを設定
        
        Args:
            info: GraphQLの解決情報
            object_name: 対象オブジェクト名
            color_data: 色データ（辞書形式）
            algorithm: 補間アルゴリズム
        
        Returns:
            dict: 処理結果
        """
        start_time = time.time()
        
        # NumPy最適化頂点カラー設定を実行
        success = batch_vertex_colors(object_name, color_data, algorithm)
        
        processing_time = time.time() - start_time
        logger.info(f"set_vertex_colorsミューテーション実行: {object_name}, 処理時間: {processing_time:.4f}秒")
        
        return {
            'success': success,
            'object_name': object_name,
            'processing_time_ms': processing_time * 1000
        }
    
    def get_cache_stats(self, info):
        """キャッシュの統計情報を取得
        
        Args:
            info: GraphQLの解決情報
        
        Returns:
            dict: キャッシュ統計情報
        """
        stats = self.cache.get_stats()
        stats.update(self.performance_stats)
        return stats
    
    def clear_cache(self, info):
        """キャッシュをクリア
        
        Args:
            info: GraphQLの解決情報
        
        Returns:
            dict: クリア結果
        """
        entries_cleared = self.cache.invalidate()
        self.invalidate_dataframes()
        
        return {
            'success': True,
            'entries_cleared': entries_cleared,
            'message': f"キャッシュをクリアしました: {entries_cleared}エントリ"
        }


# シングルトンインスタンス
_instance = None

def get_resolver():
    """最適化リゾルバのシングルトンインスタンスを取得"""
    global _instance
    if _instance is None:
        _instance = OptimizedResolver()
    return _instance