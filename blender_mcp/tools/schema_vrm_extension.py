"""
VRM機能拡張のためのGraphQLスキーマ定義

Blender GraphQL MCPのVRM関連スキーマを拡張します。
新しいテンプレートタイプとエクスポート機能のスキーマを定義します。
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_vrm_extension")

def extend_schema_with_vrm_extensions(schema):
    """
    スキーマにVRM拡張機能を追加します
    
    Args:
        schema: 拡張するGraphQLスキーマ
        
    Returns:
        GraphQLSchema: 拡張されたスキーマ
    """
    if not schema:
        logger.error("スキーマが無効です")
        return None
    
    try:
        from tools import (
            GraphQLSchema, GraphQLObjectType, GraphQLString, GraphQLBoolean,
            GraphQLList, GraphQLNonNull, GraphQLField, GraphQLArgument,
            GraphQLEnumType, GraphQLEnumValue, GraphQLInputObjectType,
            GraphQLInputField, GraphQLID, GraphQLFloat
        )
        
        from . import RESOLVER_MODULE
        
        logger.info("VRM拡張機能のスキーマを構築しています")
        
        # VRMテンプレートタイプの列挙型を定義
        vrm_template_type_enum = GraphQLEnumType(
            name='VrmTemplateType',
            values={
                'HUMANOID': GraphQLEnumValue(description='標準的な人型'),
                'FANTASY_HUMANOID': GraphQLEnumValue(description='ファンタジー風の人間'),
                'FANTASY_ELF': GraphQLEnumValue(description='エルフ（長い耳と細長い体型）'),
                'FANTASY_DWARF': GraphQLEnumValue(description='ドワーフ（がっしりした体型とヒゲ）'),
                'SCIFI_HUMANOID': GraphQLEnumValue(description='未来的な人間'),
                'SCIFI_ROBOT': GraphQLEnumValue(description='機械的なロボット'),
                'SCIFI_CYBORG': GraphQLEnumValue(description='サイボーグ（人間と機械の融合）'),
            }
        )
        
        # VRMエクスポートオプションの入力型を定義
        vrm_export_options_input_type = GraphQLInputObjectType(
            name='VrmExportOptionsInput',
            fields={
                'includeBlendShapes': GraphQLInputField(GraphQLBoolean, description='ブレンドシェイプを含めるか'),
                'optimizeMesh': GraphQLInputField(GraphQLBoolean, description='メッシュを最適化するか'),
                'exportTextures': GraphQLInputField(GraphQLBoolean, description='テクスチャをエクスポートするか'),
                'exportPhysics': GraphQLInputField(GraphQLBoolean, description='物理演算設定をエクスポートするか'),
            }
        )
        
        # VRMエクスポート結果の型を定義
        vrm_export_result_extended_type = GraphQLObjectType(
            name='VrmExportResultExtended',
            fields={
                'success': GraphQLField(GraphQLNonNull(GraphQLBoolean), description='成功フラグ'),
                'message': GraphQLField(GraphQLString, description='メッセージ'),
                'filepath': GraphQLField(GraphQLString, description='エクスポートファイルパス'),
                'metadata': GraphQLField(schema.get_type('VrmMetadata'), description='VRMメタデータ'),
                'usedVrmAddon': GraphQLField(GraphQLBoolean, description='VRMアドオンを使用したか'),
                'fallbackToFbx': GraphQLField(GraphQLBoolean, description='FBXフォールバックを使用したか'),
                'jsonFilepath': GraphQLField(GraphQLString, description='JSONメタデータファイルパス'),
            }
        )
        
        # テンプレート情報の型を定義
        vrm_template_info_type = GraphQLObjectType(
            name='VrmTemplateInfo',
            fields={
                'type': GraphQLField(GraphQLString, description='テンプレートタイプ'),
                'description': GraphQLField(GraphQLString, description='説明'),
                'categoryName': GraphQLField(GraphQLString, description='カテゴリ名'),
                'features': GraphQLField(
                    GraphQLList(GraphQLString),
                    description='テンプレートの特徴'
                ),
            }
        )
        
        # テンプレート情報リストの型を定義
        vrm_template_list_type = GraphQLObjectType(
            name='VrmTemplateList',
            fields={
                'templates': GraphQLField(
                    GraphQLList(vrm_template_info_type),
                    description='利用可能なテンプレートのリスト'
                ),
                'count': GraphQLField(GraphQLFloat, description='テンプレートの数'),
                'categories': GraphQLField(
                    GraphQLList(GraphQLString),
                    description='テンプレートのカテゴリ'
                ),
            }
        )
        
        # 既存のスキーマからクエリ型とミューテーション型を取得
        query_type = schema.get_query_type()
        mutation_type = schema.get_mutation_type()
        
        if not query_type or not mutation_type:
            logger.error("クエリ型またはミューテーション型が見つかりません")
            return schema
            
        # 既存のフィールドをコピー
        query_fields = query_type.fields.copy()
        mutation_fields = mutation_type.fields.copy()
        
        # 新しいクエリフィールドを追加
        query_fields['vrmTemplateInfo'] = GraphQLField(
            vrm_template_list_type,
            description='利用可能なVRMテンプレート情報',
            resolve=lambda obj, info: RESOLVER_MODULE.vrm_template_info(obj, info)
        )
        
        # 新しいミューテーションフィールドを追加
        
        # applyVrmTemplateミューテーションの拡張
        mutation_fields['applyVrmTemplate'] = GraphQLField(
            schema.get_type('VrmModelResult'),
            description='VRMテンプレートを適用',
            args={
                'modelId': GraphQLArgument(GraphQLNonNull(GraphQLID), description='モデルID'),
                'templateType': GraphQLArgument(GraphQLNonNull(vrm_template_type_enum), description='テンプレートタイプ')
            },
            resolve=lambda obj, info, modelId, templateType: RESOLVER_MODULE.apply_vrm_template(obj, info, modelId, templateType)
        )
        
        # exportVrmミューテーションの拡張
        mutation_fields['exportVrmExtended'] = GraphQLField(
            vrm_export_result_extended_type,
            description='拡張VRMエクスポート（外部アドオン検出機能付き）',
            args={
                'modelId': GraphQLArgument(GraphQLNonNull(GraphQLID), description='モデルID'),
                'filepath': GraphQLArgument(GraphQLNonNull(GraphQLString), description='エクスポート先ファイルパス'),
                'metadata': GraphQLArgument(schema.get_type('VrmMetadataInput'), description='VRMメタデータ（オプション）'),
                'options': GraphQLArgument(vrm_export_options_input_type, description='エクスポートオプション')
            },
            resolve=lambda obj, info, modelId, filepath, metadata=None, options=None: 
                RESOLVER_MODULE.export_vrm_extended(obj, info, modelId, filepath, metadata, options)
        )
        
        # 新しいクエリとミューテーション型を作成
        new_query_type = GraphQLObjectType(
            name='Query',
            fields=query_fields
        )
        
        new_mutation_type = GraphQLObjectType(
            name='Mutation',
            fields=mutation_fields
        )
        
        # 拡張されたスキーマを作成
        extended_schema = GraphQLSchema(
            query=new_query_type,
            mutation=new_mutation_type,
            types=schema.type_map.values()
        )
        
        logger.info("VRM拡張機能のスキーマ構築が完了しました")
        return extended_schema
        
    except Exception as e:
        logger.error(f"VRM拡張機能のスキーマ構築中にエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return schema