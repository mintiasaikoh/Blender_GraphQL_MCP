"""
GraphQLスキーマ最適化モジュール
NumPyとPandas最適化関数のためのGraphQLスキーマ拡張
"""

import tools
from tools import (
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLInt,
    GraphQLFloat,
    GraphQLBoolean,
    GraphQLList,
    GraphQLNonNull,
    GraphQLInputObjectType,
    GraphQLInputField,
    GraphQLEnumType,
    GraphQLEnumValue
)
import logging

logger = logging.getLogger("blender_graphql_mcp.schema_optimizer")

# 最適化されたリゾルバをインポート
from .optimized_resolver import get_resolver

# 既存のスキーマをインポート - 拡張する
from .schema import schema as base_schema

def extend_schema_with_optimized_operations(base_schema):
    """既存のスキーマにパフォーマンス最適化されたクエリとミューテーションを追加
    
    Args:
        base_schema: 拡張する基本スキーマ
        
    Returns:
        graphql.GraphQLSchema: 拡張されたスキーマ
    """
    resolver = get_resolver()
    
    # 既存のクエリとミューテーションタイプを取得
    existing_query_type = base_schema.query_type
    existing_mutation_type = base_schema.mutation_type
    
    # 既存のフィールド定義を取得
    existing_query_fields = existing_query_type.fields
    existing_mutation_fields = existing_mutation_type.fields
    
    # 新しいフィールド定義を準備（既存のフィールドをコピー）
    new_query_fields = dict(existing_query_fields)
    new_mutation_fields = dict(existing_mutation_fields)
    
    # ----- 入力タイプ定義 -----
    
    # Vec3入力タイプ（既存の定義があれば使用）
    Vec3InputType = GraphQLInputObjectType(
        name='Vec3Input',
        fields={
            'x': GraphQLInputField(GraphQLFloat),
            'y': GraphQLInputField(GraphQLFloat),
            'z': GraphQLInputField(GraphQLFloat)
        }
    )
    
    # TransformInput型
    TransformInputType = GraphQLInputObjectType(
        name='TransformInput',
        fields={
            'name': GraphQLInputField(GraphQLNonNull(GraphQLString)),
            'location': GraphQLInputField(GraphQLList(GraphQLFloat)),
            'rotation': GraphQLInputField(GraphQLList(GraphQLFloat)),
            'scale': GraphQLInputField(GraphQLList(GraphQLFloat))
        }
    )
    
    # ColorData入力型
    ColorMapInputType = GraphQLInputObjectType(
        name='ColorMapInput',
        fields={
            'vertex_index': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
            'color': GraphQLInputField(GraphQLNonNull(GraphQLList(GraphQLFloat)))
        }
    )
    
    # 補間アルゴリズム列挙型
    InterpolationAlgorithmEnum = GraphQLEnumType(
        name='InterpolationAlgorithm',
        values={
            'NEAREST': GraphQLEnumValue('nearest'),
            'MEAN': GraphQLEnumValue('mean'),
            'WEIGHTED': GraphQLEnumValue('weighted')
        }
    )
    
    # ----- 出力タイプ定義 -----
    
    # オブジェクト分析結果型
    BoundsType = GraphQLObjectType(
        name='Bounds',
        fields={
            'min': GraphQLField(GraphQLList(GraphQLFloat)),
            'max': GraphQLField(GraphQLList(GraphQLFloat)),
            'center': GraphQLField(GraphQLList(GraphQLFloat)),
            'dimensions': GraphQLField(GraphQLList(GraphQLFloat))
        }
    )
    
    VertexStatsType = GraphQLObjectType(
        name='VertexStats',
        fields={
            'average_distance_from_center': GraphQLField(GraphQLFloat),
            'max_distance_from_center': GraphQLField(GraphQLFloat)
        }
    )
    
    MeshAnalysisType = GraphQLObjectType(
        name='MeshAnalysis',
        fields={
            'vertex_count': GraphQLField(GraphQLInt),
            'face_count': GraphQLField(GraphQLInt),
            'edge_count': GraphQLField(GraphQLInt),
            'bounds': GraphQLField(BoundsType),
            'vertex_stats': GraphQLField(VertexStatsType),
            'processing_time_ms': GraphQLField(GraphQLFloat),
            'error': GraphQLField(GraphQLString)
        }
    )
    
    # 近接オブジェクト結果型
    NearbyObjectType = GraphQLObjectType(
        name='NearbyObject',
        fields={
            'name': GraphQLField(GraphQLString),
            'type': GraphQLField(GraphQLString),
            'distance': GraphQLField(GraphQLFloat),
            'location': GraphQLField(GraphQLList(GraphQLFloat))
        }
    )
    
    # レイキャスト結果型
    RaycastResultType = GraphQLObjectType(
        name='RaycastResult',
        fields={
            'hit': GraphQLField(GraphQLBoolean),
            'object': GraphQLField(GraphQLString),
            'location': GraphQLField(GraphQLList(GraphQLFloat)),
            'normal': GraphQLField(GraphQLList(GraphQLFloat)),
            'distance': GraphQLField(GraphQLFloat),
            'processing_time_ms': GraphQLField(GraphQLFloat),
            'error': GraphQLField(GraphQLString)
        }
    )
    
    # バッチ変換結果型
    TransformResultType = GraphQLObjectType(
        name='TransformResult',
        fields={
            'name': GraphQLField(GraphQLString),
            'success': GraphQLField(GraphQLBoolean),
            'error': GraphQLField(GraphQLString)
        }
    )
    
    BatchTransformResultType = GraphQLObjectType(
        name='BatchTransformResult',
        fields={
            'success': GraphQLField(GraphQLBoolean),
            'results': GraphQLField(GraphQLList(TransformResultType)),
            'success_count': GraphQLField(GraphQLInt),
            'error_count': GraphQLField(GraphQLInt),
            'processing_time_ms': GraphQLField(GraphQLFloat),
            'error': GraphQLField(GraphQLString)
        }
    )
    
    # キャッシュ統計型
    CacheStatsType = GraphQLObjectType(
        name='CacheStats',
        fields={
            'entries': GraphQLField(GraphQLInt),
            'hits': GraphQLField(GraphQLInt),
            'misses': GraphQLField(GraphQLInt),
            'sets': GraphQLField(GraphQLInt),
            'evictions': GraphQLField(GraphQLInt),
            'hit_rate': GraphQLField(GraphQLFloat),
            'total_queries': GraphQLField(GraphQLInt),
            'cached_queries': GraphQLField(GraphQLInt),
            'avg_response_time': GraphQLField(GraphQLFloat)
        }
    )
    
    CacheClearResultType = GraphQLObjectType(
        name='CacheClearResult',
        fields={
            'success': GraphQLField(GraphQLBoolean),
            'entries_cleared': GraphQLField(GraphQLInt),
            'message': GraphQLField(GraphQLString)
        }
    )
    
    # 頂点変換結果型
    VertexTransformResultType = GraphQLObjectType(
        name='VertexTransformResult',
        fields={
            'success': GraphQLField(GraphQLBoolean),
            'object_name': GraphQLField(GraphQLString),
            'processing_time_ms': GraphQLField(GraphQLFloat)
        }
    )
    
    # ----- クエリフィールド追加 -----
    
    # analyzeMesh: 高速なメッシュ分析
    new_query_fields['analyzeMesh'] = GraphQLField(
        MeshAnalysisType,
        args={
            'name': GraphQLNonNull(GraphQLString)
        },
        resolve=lambda obj, info, name: resolver.resolve_analyze_mesh(info, name)
    )
    
    # nearestObjects: 高速な近接オブジェクト検索
    new_query_fields['nearestObjects'] = GraphQLField(
        GraphQLList(NearbyObjectType),
        args={
            'origin': GraphQLNonNull(GraphQLList(GraphQLFloat)),
            'max_distance': GraphQLFloat(default_value=10.0),
            'object_types': GraphQLList(GraphQLString)
        },
        resolve=lambda obj, info, origin, max_distance=10.0, object_types=None: 
            resolver.resolve_nearest_objects(info, origin, max_distance, object_types)
    )
    
    # raycast: 高速なレイキャスト
    new_query_fields['raycast'] = GraphQLField(
        RaycastResultType,
        args={
            'origin': GraphQLNonNull(GraphQLList(GraphQLFloat)),
            'direction': GraphQLNonNull(GraphQLList(GraphQLFloat)),
            'max_distance': GraphQLFloat(default_value=100.0)
        },
        resolve=lambda obj, info, origin, direction, max_distance=100.0:
            resolver.resolve_raycast(info, origin, direction, max_distance)
    )
    
    # optimizedSceneAnalysis: 包括的なシーン分析
    new_query_fields['optimizedSceneAnalysis'] = GraphQLField(
        GraphQLString,  # JSONとして返す
        resolve=lambda obj, info: resolver.resolve_scene_analysis(info)
    )
    
    # cacheStats: キャッシュの統計情報
    new_query_fields['cacheStats'] = GraphQLField(
        CacheStatsType,
        resolve=lambda obj, info: resolver.get_cache_stats(info)
    )
    
    # ----- ミューテーションフィールド追加 -----
    
    # batchTransform: 複数オブジェクトの一括変換
    new_mutation_fields['batchTransform'] = GraphQLField(
        BatchTransformResultType,
        args={
            'transforms': GraphQLNonNull(GraphQLList(GraphQLNonNull(TransformInputType)))
        },
        resolve=lambda obj, info, transforms: resolver.resolve_batch_transform(info, transforms)
    )
    
    # clearCache: キャッシュをクリア
    new_mutation_fields['clearCache'] = GraphQLField(
        CacheClearResultType,
        resolve=lambda obj, info: resolver.clear_cache(info)
    )
    
    # transformVertices: 頂点を高速変換
    new_mutation_fields['transformVertices'] = GraphQLField(
        VertexTransformResultType,
        args={
            'object_name': GraphQLNonNull(GraphQLString),
            'transform_matrix': GraphQLNonNull(GraphQLList(GraphQLFloat))
        },
        resolve=lambda obj, info, object_name, transform_matrix:
            resolver.resolve_transform_vertices(info, object_name, transform_matrix)
    )
    
    # setVertexColors: 頂点カラーを高速設定
    new_mutation_fields['setVertexColors'] = GraphQLField(
        VertexTransformResultType,
        args={
            'object_name': GraphQLNonNull(GraphQLString),
            'color_data': GraphQLNonNull(GraphQLList(GraphQLNonNull(ColorMapInputType))),
            'algorithm': GraphQLField(
                InterpolationAlgorithmEnum,
                default_value='mean'
            )
        },
        resolve=lambda obj, info, object_name, color_data, algorithm='mean':
            # color_dataを辞書に変換
            color_dict = {item['vertex_index']: item['color'] for item in color_data}
            return resolver.resolve_set_vertex_colors(info, object_name, color_dict, algorithm)
    )
    
    # 新しいクエリタイプとミューテーションタイプを作成
    new_query_type = GraphQLObjectType(
        name='Query',
        fields=new_query_fields
    )
    
    new_mutation_type = GraphQLObjectType(
        name='Mutation',
        fields=new_mutation_fields
    )
    
    # 新しいスキーマを作成
    optimized_schema = graphql.GraphQLSchema(
        query=new_query_type,
        mutation=new_mutation_type,
        types=base_schema.type_map.values()
    )
    
    logger.info("NumPy/Pandas最適化操作でスキーマを拡張しました")
    return optimized_schema

# 最適化されたスキーマを作成
schema = extend_schema_with_optimized_operations(base_schema)

# スキーマをエクスポート
__all__ = ['schema']