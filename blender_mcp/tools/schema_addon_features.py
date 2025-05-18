"""
Blender GraphQL MCP - addon features schema extensions
アドオン機能のGraphQLスキーマ拡張
"""

import logging
from tools import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLString,
    GraphQLInt,
    GraphQLFloat,
    GraphQLBoolean,
    GraphQLList,
    GraphQLNonNull,
    GraphQLField,
    GraphQLArgument
)

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_addon_features")

def extend_schema_with_addon_features(schema):
    """
    既存のスキーマにアドオン機能実行関連の型と操作を追加
    
    Args:
        schema: 既存のGraphQLスキーマ
        
    Returns:
        拡張されたGraphQLスキーマ
    """
    existing_query_fields = schema.query_type.fields
    existing_mutation_fields = schema.mutation_type.fields
    
    # -----------------------------
    # 共通の結果型
    # -----------------------------
    
    # ノードグループ結果型
    node_group_result_type = GraphQLObjectType(
        name='NodeGroupResult',
        fields={
            'success': GraphQLField(GraphQLBoolean, description='成功フラグ'),
            'status': GraphQLField(GraphQLString, description='ステータス'),
            'message': GraphQLField(GraphQLString, description='メッセージ'),
            'node_group_name': GraphQLField(GraphQLString, description='ノードグループ名'),
            'modifier_name': GraphQLField(GraphQLString, description='モディファイア名'),
            'object_name': GraphQLField(GraphQLString, description='オブジェクト名'),
            'setup_type': GraphQLField(GraphQLString, description='セットアップタイプ')
        }
    )
    
    # アニメーションツリー結果型
    animation_tree_result_type = GraphQLObjectType(
        name='AnimationTreeResult',
        fields={
            'success': GraphQLField(GraphQLBoolean, description='成功フラグ'),
            'status': GraphQLField(GraphQLString, description='ステータス'),
            'message': GraphQLField(GraphQLString, description='メッセージ'),
            'tree_name': GraphQLField(GraphQLString, description='ツリー名'),
            'object_name': GraphQLField(GraphQLString, description='オブジェクト名'),
            'setup_type': GraphQLField(GraphQLString, description='セットアップタイプ')
        }
    )
    
    # マテリアルセットアップ結果型
    material_setup_result_type = GraphQLObjectType(
        name='MaterialSetupResult',
        fields={
            'success': GraphQLField(GraphQLBoolean, description='成功フラグ'),
            'status': GraphQLField(GraphQLString, description='ステータス'),
            'message': GraphQLField(GraphQLString, description='メッセージ'),
            'material_name': GraphQLField(GraphQLString, description='マテリアル名'),
            'base_color': GraphQLField(GraphQLString, description='基本色'),
            'metallic': GraphQLField(GraphQLFloat, description='金属度'),
            'roughness': GraphQLField(GraphQLFloat, description='粗さ'),
            'nodes_created': GraphQLField(
                GraphQLList(GraphQLString),
                description='作成されたノード'
            ),
            'objects_using_material': GraphQLField(
                GraphQLList(GraphQLString),
                description='このマテリアルを使用しているオブジェクト'
            )
        }
    )
    
    # -----------------------------
    # ミューテーション
    # -----------------------------
    
    # リゾルバモジュールを取得
    try:
        from . import resolvers
        RESOLVER_MODULE = resolvers
        logger.info("リゾルバモジュールをロードしました")
    except ImportError as e:
        from . import resolver
        RESOLVER_MODULE = resolver
        logger.info("代替リゾルバモジュールをロードしました")
    except Exception as e:
        logger.error(f"リゾルバモジュールのロードに失敗しました: {e}")
        return schema
    
    # アドオン機能ミューテーション
    addon_feature_mutation_fields = {
        # ジオメトリノード機能
        'createGeometryNodeGroup': GraphQLField(
            node_group_result_type,
            description='ジオメトリノードグループを作成し、オブジェクトに適用',
            args={
                'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ノードグループ名'),
                'object_name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='対象オブジェクト名'),
                'setup_type': GraphQLArgument(GraphQLString, description='セットアップタイプ', default_value='BASIC')
            },
            resolve=lambda obj, info, name, object_name, setup_type='BASIC': RESOLVER_MODULE.create_geometry_node_group(
                obj, info, name, object_name, setup_type
            )
        ),
        
        # アニメーションノード機能
        'createAnimationNodeTree': GraphQLField(
            animation_tree_result_type,
            description='アニメーションノードツリーを作成',
            args={
                'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ツリー名'),
                'setup_type': GraphQLArgument(GraphQLString, description='セットアップタイプ', default_value='BASIC'),
                'target_object': GraphQLArgument(GraphQLString, description='ターゲットオブジェクト名')
            },
            resolve=lambda obj, info, name, setup_type='BASIC', target_object=None: RESOLVER_MODULE.create_animation_node_tree(
                obj, info, name, setup_type, target_object
            )
        ),
        
        # ノードラングラー機能
        'setupPBRMaterial': GraphQLField(
            material_setup_result_type,
            description='PBRマテリアルをセットアップ',
            args={
                'material_name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='マテリアル名'),
                'base_color': GraphQLArgument(GraphQLString, description='基本色（16進数カラーコード）', default_value='#FFFFFF'),
                'metallic': GraphQLArgument(GraphQLFloat, description='金属度', default_value=0.0),
                'roughness': GraphQLArgument(GraphQLFloat, description='粗さ', default_value=0.5)
            },
            resolve=lambda obj, info, material_name, base_color='#FFFFFF', metallic=0.0, roughness=0.5: RESOLVER_MODULE.setup_pbr_material(
                obj, info, material_name, base_color, metallic, roughness
            )
        )
    }
    
    # -----------------------------
    # リゾルバ関数の追加
    # -----------------------------
    
    # ジオメトリノード関数
    def create_geometry_node_group(obj, info, name, object_name, setup_type='BASIC'):
        from ...core.commands.addon_feature_commands import create_geometry_node_group as cmd
        result = cmd(name, object_name, setup_type)
        return result
    
    # アニメーションノード関数
    def create_animation_node_tree(obj, info, name, setup_type='BASIC', target_object=None):
        from ...core.commands.addon_feature_commands import create_animation_node_tree as cmd
        result = cmd(name, setup_type, target_object)
        return result
    
    # ノードラングラー関数
    def setup_pbr_material(obj, info, material_name, base_color='#FFFFFF', metallic=0.0, roughness=0.5):
        from ...core.commands.addon_feature_commands import setup_pbr_material as cmd
        result = cmd(material_name, base_color, metallic, roughness)
        return result
    
    # リゾルバモジュールにメソッドを追加
    setattr(RESOLVER_MODULE, 'create_geometry_node_group', create_geometry_node_group)
    setattr(RESOLVER_MODULE, 'create_animation_node_tree', create_animation_node_tree)
    setattr(RESOLVER_MODULE, 'setup_pbr_material', setup_pbr_material)
    
    # 既存のミューテーションとマージ
    merged_mutation_fields = {**existing_mutation_fields, **addon_feature_mutation_fields}
    
    # 新しいミューテーションタイプを作成
    new_mutation_type = GraphQLObjectType(
        name='Mutation',
        fields=merged_mutation_fields
    )
    
    # 新しいスキーマを作成して返す
    return GraphQLSchema(
        query=schema.query_type,
        mutation=new_mutation_type,
        directives=schema.directives,
        types=schema.type_map.values()
    )