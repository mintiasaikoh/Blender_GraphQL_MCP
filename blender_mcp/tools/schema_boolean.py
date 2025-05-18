"""
Blender GraphQL MCP - ブーリアンスキーマ拡張
ブーリアン操作のGraphQLスキーマ定義
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
    GraphQLEnumType,
    GraphQLEnumValue
)

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_boolean")

# レジストリのインポート
from .schema_registry import schema_registry
# リゾルバモジュールのインポート
import tools.resolver as RESOLVER_MODULE

def register_boolean_schema():
    """ブーリアン操作のスキーマを登録"""
    
    # -----------------------------
    # ブーリアン操作型
    # -----------------------------
    
    # ブーリアン操作列挙型
    schema_registry.register_type('BooleanOperation', GraphQLEnumType(
        name='BooleanOperation',
        values={
            'UNION': GraphQLEnumValue(description='結合操作'),
            'DIFFERENCE': GraphQLEnumValue(description='差分操作'),
            'INTERSECT': GraphQLEnumValue(description='交差操作')
        },
        description='ブーリアン操作の種類'
    ))
    
    # ブーリアンソルバー列挙型
    schema_registry.register_type('BooleanSolver', GraphQLEnumType(
        name='BooleanSolver',
        values={
            'FAST': GraphQLEnumValue(description='高速ソルバー（精度低）'),
            'EXACT': GraphQLEnumValue(description='正確なソルバー（精度高、処理時間長）')
        },
        description='ブーリアン操作のソルバー'
    ))
    
    # ブーリアン操作結果型
    schema_registry.register_type('BooleanOperationResult', GraphQLObjectType(
        name='BooleanOperationResult',
        fields={
            'success': GraphQLField(GraphQLBoolean, description='成功フラグ'),
            'status': GraphQLField(GraphQLString, description='ステータス'),
            'message': GraphQLField(GraphQLString, description='メッセージ'),
            'target_object': GraphQLField(GraphQLString, description='ターゲットオブジェクト名'),
            'tool_object': GraphQLField(GraphQLString, description='ツールオブジェクト名'),
            'operation': GraphQLField(GraphQLString, description='実行された操作'),
            'solver': GraphQLField(GraphQLString, description='使用されたソルバー'),
            'issues': GraphQLField(GraphQLList(GraphQLString), description='発生した問題点')
        }
    ))
    
    # -----------------------------
    # ブーリアンミューテーション
    # -----------------------------
    
    # 基本ブーリアン操作
    schema_registry.register_mutation('boolean.operation', GraphQLField(
        schema_registry.get_type('BooleanOperationResult'),
        args={
            'target_object': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ターゲットオブジェクト名'),
            'tool_object': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ツールオブジェクト名'),
            'operation': GraphQLArgument(GraphQLNonNull(schema_registry.get_type('BooleanOperation')), 
                                        description='ブーリアン操作タイプ'),
            'auto_repair': GraphQLArgument(GraphQLBoolean, description='操作前にメッシュを自動修復するか', 
                                         default_value=True),
            'validate_result': GraphQLArgument(GraphQLBoolean, description='操作後に結果を検証するか', 
                                            default_value=True),
            'delete_tool': GraphQLArgument(GraphQLBoolean, description='操作後にツールオブジェクトを削除するか', 
                                        default_value=False),
            'solver': GraphQLArgument(schema_registry.get_type('BooleanSolver'), description='使用するソルバー', 
                                   default_value='EXACT')
        },
        description='メッシュのブーリアン操作を実行',
        resolve=lambda obj, info, **kwargs: RESOLVER_MODULE.resolve_boolean_operation(obj, info, **kwargs)
    ))
    
    # 拡張ブーリアン操作
    schema_registry.register_mutation('boolean.enhancedOperation', GraphQLField(
        schema_registry.get_type('BooleanOperationResult'),
        args={
            'target_object': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ターゲットオブジェクト名'),
            'tool_object': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ツールオブジェクト名'),
            'operation': GraphQLArgument(GraphQLNonNull(schema_registry.get_type('BooleanOperation')), 
                                       description='ブーリアン操作タイプ'),
            'solver': GraphQLArgument(schema_registry.get_type('BooleanSolver'), description='使用するソルバー', 
                                   default_value='EXACT')
        },
        description='高度なエラー処理と自動修復機能を持つブーリアン操作',
        resolve=lambda obj, info, **kwargs: RESOLVER_MODULE.resolve_enhanced_boolean_operation(obj, info, **kwargs)
    ))
    
    logger.info("ブーリアンスキーマを登録しました")
