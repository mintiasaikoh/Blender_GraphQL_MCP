"""
Blender GraphQL MCP - integrated schema extensions
統合APIのGraphQLスキーマ拡張
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
    GraphQLArgument,
    GraphQLInputObjectType,
    GraphQLInputField
)

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_integrated")

def extend_schema_with_integrated_api(schema):
    """
    既存のスキーマに統合APIの型と操作を追加
    
    Args:
        schema: 既存のGraphQLスキーマ
        
    Returns:
        拡張されたGraphQLスキーマ
    """
    existing_query_fields = schema.query_type.fields
    existing_mutation_fields = schema.mutation_type.fields
    
    # -----------------------------
    # パラメータ型定義
    # -----------------------------
    
    # 汎用パラメータ入力型
    params_input_type = GraphQLInputObjectType(
        name='ParamsInput',
        fields={
            'location': GraphQLInputField(GraphQLList(GraphQLFloat), description='位置 [x, y, z]'),
            'rotation': GraphQLInputField(GraphQLList(GraphQLFloat), description='回転 [x, y, z] (度)'),
            'scale': GraphQLInputField(GraphQLList(GraphQLFloat), description='スケール [x, y, z]'),
            'material_color': GraphQLInputField(GraphQLString, description='マテリアル色（16進数カラーコード）'),
            'metallic': GraphQLInputField(GraphQLFloat, description='金属度 (0.0-1.0)'),
            'roughness': GraphQLInputField(GraphQLFloat, description='粗さ (0.0-1.0)'),
            'size': GraphQLInputField(GraphQLFloat, description='サイズ'),
            'resolution': GraphQLInputField(GraphQLInt, description='解像度'),
            'height': GraphQLInputField(GraphQLFloat, description='高さ'),
            'noise_scale': GraphQLInputField(GraphQLFloat, description='ノイズスケール'),
            'seed': GraphQLInputField(GraphQLInt, description='シード値'),
            'radius': GraphQLInputField(GraphQLFloat, description='半径'),
            'subdivision': GraphQLInputField(GraphQLInt, description='分割数'),
            'distortion': GraphQLInputField(GraphQLFloat, description='歪み度'),
            'base_object': GraphQLInputField(GraphQLString, description='基本オブジェクト種類'),
            'animation_type': GraphQLInputField(GraphQLString, description='アニメーション種類'),
            'metal_type': GraphQLInputField(GraphQLString, description='金属タイプ'),
            'color': GraphQLInputField(GraphQLString, description='色（16進数カラーコード）'),
            'ior': GraphQLInputField(GraphQLFloat, description='屈折率')
        }
    )
    
    # -----------------------------
    # 結果型定義
    # -----------------------------
    
    # 統合オブジェクト結果型
    integrated_object_result_type = GraphQLObjectType(
        name='IntegratedObjectResult',
        fields={
            'success': GraphQLField(GraphQLBoolean, description='成功フラグ'),
            'status': GraphQLField(GraphQLString, description='ステータス'),
            'message': GraphQLField(GraphQLString, description='メッセージ'),
            'object_name': GraphQLField(GraphQLString, description='オブジェクト名'),
            'object_type': GraphQLField(GraphQLString, description='オブジェクトタイプ'),
            'node_group_name': GraphQLField(GraphQLString, description='ノードグループ名'),
            'modifier_name': GraphQLField(GraphQLString, description='モディファイア名'),
            'tree_name': GraphQLField(GraphQLString, description='ノードツリー名')
        }
    )
    
    # 統合マテリアル結果型
    integrated_material_result_type = GraphQLObjectType(
        name='IntegratedMaterialResult',
        fields={
            'success': GraphQLField(GraphQLBoolean, description='成功フラグ'),
            'status': GraphQLField(GraphQLString, description='ステータス'),
            'message': GraphQLField(GraphQLString, description='メッセージ'),
            'material_name': GraphQLField(GraphQLString, description='マテリアル名'),
            'material_type': GraphQLField(GraphQLString, description='マテリアルタイプ')
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
    
    # 統合APIミューテーション
    integrated_mutation_fields = {
        # プロシージャルオブジェクト作成
        'createProceduralObject': GraphQLField(
            integrated_object_result_type,
            description='プロシージャルオブジェクトを作成（基本機能とアドオンを統合）',
            args={
                'object_type': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクトタイプ'),
                'name': GraphQLArgument(GraphQLString, description='オブジェクト名（省略時は自動生成）'),
                'params': GraphQLArgument(params_input_type, description='その他のパラメータ')
            },
            resolve=lambda obj, info, object_type, name=None, params=None: RESOLVER_MODULE.create_procedural_object(
                obj, info, object_type, name, params
            )
        ),
        
        # 高度なマテリアル作成
        'createAdvancedMaterial': GraphQLField(
            integrated_material_result_type,
            description='高度なマテリアルを作成（基本機能とアドオンを統合）',
            args={
                'material_type': GraphQLArgument(GraphQLNonNull(GraphQLString), description='マテリアルタイプ'),
                'name': GraphQLArgument(GraphQLString, description='マテリアル名（省略時は自動生成）'),
                'params': GraphQLArgument(params_input_type, description='その他のパラメータ')
            },
            resolve=lambda obj, info, material_type, name=None, params=None: RESOLVER_MODULE.create_advanced_material(
                obj, info, material_type, name, params
            )
        )
    }
    
    # -----------------------------
    # リゾルバ関数の追加
    # -----------------------------
    
    # プロシージャルオブジェクト作成
    def create_procedural_object(obj, info, object_type, name=None, params=None):
        from ...core.commands.integrated_commands import create_procedural_object as cmd
        result = cmd(object_type, name, params)
        return result
    
    # 高度なマテリアル作成
    def create_advanced_material(obj, info, material_type, name=None, params=None):
        from ...core.commands.integrated_commands import create_material as cmd
        result = cmd(material_type, name, params)
        return result
    
    # リゾルバモジュールにメソッドを追加
    setattr(RESOLVER_MODULE, 'create_procedural_object', create_procedural_object)
    setattr(RESOLVER_MODULE, 'create_advanced_material', create_advanced_material)
    
    # 既存のミューテーションとマージ
    merged_mutation_fields = {**existing_mutation_fields, **integrated_mutation_fields}
    
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