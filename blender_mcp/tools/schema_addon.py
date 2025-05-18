"""
Blender GraphQL MCP - addon schema extensions
アドオン操作のためのGraphQLスキーマ拡張
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

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_addon")

def extend_schema_with_addon_operations(schema):
    """
    既存のスキーマにアドオン操作関連の型と操作を追加
    
    Args:
        schema: 既存のGraphQLスキーマ
        
    Returns:
        拡張されたGraphQLスキーマ
    """
    existing_query_fields = schema.query_type.fields
    existing_mutation_fields = schema.mutation_type.fields
    
    # アドオン情報型
    addon_info_type = GraphQLObjectType(
        name='AddonInfo',
        fields={
            'name': GraphQLField(GraphQLString, description='アドオン名'),
            'is_enabled': GraphQLField(GraphQLBoolean, description='有効フラグ'),
            'description': GraphQLField(GraphQLString, description='アドオンの説明'),
            'author': GraphQLField(GraphQLString, description='作者'),
            'version': GraphQLField(GraphQLString, description='バージョン'),
            'category': GraphQLField(GraphQLString, description='カテゴリ'),
            'blender_version': GraphQLField(GraphQLString, description='対応Blenderバージョン')
        }
    )
    
    # アドオン操作結果型
    addon_status_type = GraphQLObjectType(
        name='AddonStatus',
        fields={
            'status': GraphQLField(GraphQLString, description='ステータス'),
            'message': GraphQLField(GraphQLString, description='メッセージ'),
            'addon_name': GraphQLField(GraphQLString, description='アドオン名'),
            'is_enabled': GraphQLField(GraphQLBoolean, description='有効フラグ')
        }
    )
    
    # アップデート情報型
    addon_update_info_type = GraphQLObjectType(
        name='AddonUpdateInfo',
        fields={
            'name': GraphQLField(GraphQLString, description='アドオン名'),
            'current_version': GraphQLField(GraphQLString, description='現在のバージョン'),
            'available_version': GraphQLField(GraphQLString, description='利用可能なバージョン'),
            'has_update': GraphQLField(GraphQLBoolean, description='更新あり')
        }
    )
    
    # すべてのアドオン情報型
    all_addons_type = GraphQLObjectType(
        name='AllAddonsResponse',
        fields={
            'supported_addons': GraphQLField(
                GraphQLList(GraphQLString), 
                description='サポートされているアドオンリスト'
            ),
            'categorized_addons': GraphQLField(
                GraphQLObjectType(
                    name='CategorizedAddons',
                    fields={
                        'standard': GraphQLField(GraphQLList(GraphQLString), description='標準アドオン'),
                        'modeling': GraphQLField(GraphQLList(GraphQLString), description='モデリングアドオン'),
                        'animation': GraphQLField(GraphQLList(GraphQLString), description='アニメーションアドオン'),
                        'vtuber': GraphQLField(GraphQLList(GraphQLString), description='VTuber関連アドオン'),
                        'materials': GraphQLField(GraphQLList(GraphQLString), description='マテリアル関連アドオン'),
                        'simulation': GraphQLField(GraphQLList(GraphQLString), description='シミュレーション関連アドオン'),
                        'misc': GraphQLField(GraphQLList(GraphQLString), description='その他のアドオン')
                    }
                ),
                description='カテゴリ別アドオンリスト'
            ),
            'total_enabled': GraphQLField(GraphQLInt, description='有効なアドオン数'),
            'total_supported': GraphQLField(GraphQLInt, description='サポートされているアドオン数'),
            'addons': GraphQLField(
                GraphQLList(addon_info_type),
                description='アドオン情報リスト'
            )
        }
    )
    
    # クエリに追加するフィールド
    addon_query_fields = {
        'addonInfo': GraphQLField(
            addon_info_type,
            description='アドオン情報',
            args={
                'addon_name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='アドオン名')
            },
            resolve=lambda obj, info, addon_name: RESOLVER_MODULE.get_addon_info(obj, info, addon_name)
        ),
        'allAddons': GraphQLField(
            all_addons_type,
            description='すべてのアドオン情報',
            resolve=lambda obj, info: RESOLVER_MODULE.get_all_addons(obj, info)
        ),
        'addonUpdates': GraphQLField(
            GraphQLList(addon_update_info_type),
            description='更新可能なアドオン',
            resolve=lambda obj, info: RESOLVER_MODULE.check_addon_updates(obj, info)
        )
    }
    
    # ミューテーションに追加するフィールド
    addon_mutation_fields = {
        'enableAddon': GraphQLField(
            addon_status_type,
            description='アドオンを有効化',
            args={
                'addon_name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='アドオン名')
            },
            resolve=lambda obj, info, addon_name: RESOLVER_MODULE.enable_addon(obj, info, addon_name)
        ),
        'disableAddon': GraphQLField(
            addon_status_type,
            description='アドオンを無効化',
            args={
                'addon_name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='アドオン名')
            },
            resolve=lambda obj, info, addon_name: RESOLVER_MODULE.disable_addon(obj, info, addon_name)
        ),
        'installAddon': GraphQLField(
            addon_status_type,
            description='ファイルからアドオンをインストール',
            args={
                'file_path': GraphQLArgument(GraphQLNonNull(GraphQLString), description='アドオンZIPファイルパス')
            },
            resolve=lambda obj, info, file_path: RESOLVER_MODULE.install_addon(obj, info, file_path)
        ),
        'installAddonFromUrl': GraphQLField(
            addon_status_type,
            description='URLからアドオンをインストール',
            args={
                'url': GraphQLArgument(GraphQLNonNull(GraphQLString), description='アドオンZIPファイルのURL')
            },
            resolve=lambda obj, info, url: RESOLVER_MODULE.install_addon_from_url(obj, info, url)
        ),
        'updateAddon': GraphQLField(
            addon_status_type,
            description='アドオンを更新',
            args={
                'addon_name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='アドオン名')
            },
            resolve=lambda obj, info, addon_name: RESOLVER_MODULE.update_addon(obj, info, addon_name)
        )
    }
    
    # リゾルバモジュールを取得
    try:
        from . import resolvers
        global RESOLVER_MODULE
        RESOLVER_MODULE = resolvers
        logger.info("リゾルバモジュールをロードしました")
    except ImportError as e:
        from . import resolver
        RESOLVER_MODULE = resolver
        logger.info("代替リゾルバモジュールをロードしました")
    except Exception as e:
        logger.error(f"リゾルバモジュールのロードに失敗しました: {e}")
        return schema
    
    # 既存のクエリとマージ
    merged_query_fields = {**existing_query_fields, **addon_query_fields}
    merged_mutation_fields = {**existing_mutation_fields, **addon_mutation_fields}
    
    # 新しいクエリとミューテーションタイプを作成
    new_query_type = GraphQLObjectType(
        name='Query',
        fields=merged_query_fields
    )
    
    new_mutation_type = GraphQLObjectType(
        name='Mutation',
        fields=merged_mutation_fields
    )
    
    # 新しいスキーマを作成して返す
    return GraphQLSchema(
        query=new_query_type,
        mutation=new_mutation_type,
        directives=schema.directives,
        types=schema.type_map.values()
    )