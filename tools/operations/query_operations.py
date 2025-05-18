"""
Blender GraphQL - クエリ操作定義
"""

import logging
from tools import (
    GraphQLObjectType,
    GraphQLString,
    GraphQLNonNull,
    GraphQLList,
    GraphQLField,
    GraphQLArgument
)

from ..schema_registry import schema_registry
from ..types.base_types import vector3_type
from ..types.object_types import (
    object_type, 
    scene_info_type
)
from ..types.material_types import (
    material_type, 
    texture_type, 
    polyhaven_search_result_type
)

logger = logging.getLogger("blender_graphql_mcp.tools.operations.query_operations")

def build_query_type(resolver_module):
    """リゾルバモジュールを使用してクエリタイプを構築"""
    
    # 必要なリゾルバメソッドがあるか確認
    required_resolvers = [
        'hello', 'scene_info', 'object', 
        'resolve_mesh_data', 'materials', 'resolve_material',
        'search_polyhaven', 'textures', 'cameras', 
        'resolve_camera', 'lights', 'resolve_light',
        'render_settings', 'modifiers'
    ]
    
    for resolver_name in required_resolvers:
        if not hasattr(resolver_module, resolver_name):
            logger.warning(f"リゾルバ関数 '{resolver_name}' が見つかりません。一部の機能が制限されます。")
    
    # クエリタイプの構築
    query_fields = {}
    
    # 基本クエリフィールド
    if hasattr(resolver_module, 'hello'):
        query_fields['hello'] = GraphQLField(
            GraphQLString,
            description='テスト用挨拶メッセージ',
            resolve=resolver_module.hello
        )
    
    if hasattr(resolver_module, 'scene_info'):
        query_fields['sceneInfo'] = GraphQLField(
            scene_info_type,
            description='現在のシーン情報',
            resolve=resolver_module.scene_info
        )
    
    if hasattr(resolver_module, 'object'):
        query_fields['object'] = GraphQLField(
            object_type,
            description='指定された名前のオブジェクト情報',
            args={
                'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名')
            },
            resolve=resolver_module.object
        )
    
    # マテリアル関連クエリ
    if hasattr(resolver_module, 'materials'):
        query_fields['materials'] = GraphQLField(
            GraphQLList(material_type),
            description='全マテリアル一覧',
            resolve=resolver_module.materials
        )
    
    if hasattr(resolver_module, 'resolve_material'):
        query_fields['material'] = GraphQLField(
            material_type,
            description='特定マテリアルの情報',
            args={
                'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='マテリアル名')
            },
            resolve=resolver_module.resolve_material
        )
    
    # Polyhaven素材検索
    if hasattr(resolver_module, 'search_polyhaven'):
        query_fields['searchPolyhaven'] = GraphQLField(
            polyhaven_search_result_type,
            description='Polyhavenアセット検索',
            args={
                'query': GraphQLArgument(GraphQLString, description='検索クエリ'),
                'category': GraphQLArgument(GraphQLString, description='カテゴリフィルタ'),
                'limit': GraphQLArgument(GraphQLInt, description='取得件数制限', default_value=10)
            },
            resolve=resolver_module.search_polyhaven
        )
    
    # テクスチャ一覧取得
    if hasattr(resolver_module, 'textures'):
        query_fields['textures'] = GraphQLField(
            GraphQLList(texture_type),
            description='全テクスチャ一覧',
            resolve=resolver_module.textures
        )
    
    # 他の必要なクエリフィールドを追加...
    
    # クエリタイプを作成して返す
    query_type = GraphQLObjectType(
        name='Query',
        fields=query_fields
    )
    
    # スキーマレジストリに登録
    schema_registry.register_type('Query', query_type)
    
    return query_type