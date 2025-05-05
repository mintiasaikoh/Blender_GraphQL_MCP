"""
Unified MCP GraphQL Module
GraphQL APIとクエリ処理を提供
"""

import importlib
import logging

# ロガー設定
logger = logging.getLogger('unified_mcp.graphql')

# GraphQLライブラリをチェック
GRAPHQL_AVAILABLE = False
GRAPHQL_VERSION = None
REQUIRED_VERSION = (3, 0, 0)

try:
    import graphql
    
    # バージョンの取得と互換性チェック
    try:
        version_str = getattr(graphql, '__version__', '0.0.0')
        # 数字以外の文字を取り除いてバージョン文字列をクリーンアップ
        import re
        version_clean = re.sub(r'[^0-9\.]', '', version_str)
        version_parts = version_clean.split('.')
        
        # バージョン番号を整数リストに変換
        GRAPHQL_VERSION = tuple(
            int(part) for part in version_parts[:3] if part.isdigit()
        )
        
        # 足りない箇所は0で埋める
        while len(GRAPHQL_VERSION) < 3:
            GRAPHQL_VERSION = GRAPHQL_VERSION + (0,)
        
        # バージョンチェック
        if GRAPHQL_VERSION >= REQUIRED_VERSION:
            GRAPHQL_AVAILABLE = True
            logger.info(f"GraphQLライブラリが利用可能です (バージョン: {version_str})")
        else:
            logger.warning(f"GraphQLライブラリのバージョンが古すぎます: {version_str}")
            logger.warning(f"必要なバージョンは{'.'.join(map(str, REQUIRED_VERSION))}以上です")
    except Exception as e:
        logger.warning(f"GraphQLバージョンチェックエラー: {e}")
        # バージョンチェックに失敗しても使用を試みる
        GRAPHQL_AVAILABLE = True
        logger.info("GraphQLバージョン確認に失敗しましたが、使用を試みます")

except ImportError as e:
    logger.warning(f"GraphQLライブラリが見つかりません: {e}")
    logger.info("インストール方法: cd /Applications/Blender.app/Contents/Resources/4.4/python/bin && ./python3.11 -m pip install graphql-core>=3.0.0")

# 循環参照を避けるための順序付きインポート
# まずschemaを読み込み、次にresolversを読み込みます
MODULES_LOADED = False

if "schema" in locals():
    # 循環参照を避けるための順序付きリロード
    importlib.reload(schema)  # まずスキーマをリロード
    importlib.reload(resolver)  # 次にリゾルバーをリロード
    importlib.reload(hole_penetration)  # ホール調査モジュールをリロード
    importlib.reload(api)  # APIは最後にリロード（他に依存するため）
else:
    try:
        # 循環参照を避けるための順序付き初期読み込み
        logger.info("GraphQLモジュールを順序付きで読み込みます...")
        from . import schema
        logger.info("schemaモジュールを読み込みました")
        
        from . import resolver
        logger.info("resolverモジュールを読み込みました")
        
        from . import hole_penetration
        logger.info("hole_penetrationモジュールを読み込みました")
        
        from . import api
        logger.info("apiモジュールを読み込みました")
        
        MODULES_LOADED = True
    except ImportError as e:
        MODULES_LOADED = False
        logger.error(f"GraphQLモジュールインポートエラー: {e}")
        import traceback
        logger.debug(traceback.format_exc())

# APIをエクスポート
if GRAPHQL_AVAILABLE and MODULES_LOADED:
    try:
        from .api import (
            query_blender,
            set_spatial_relationship,
            create_smart_object,
            enhanced_boolean_operation
        )
        API_FUNCTIONS_LOADED = True
    except ImportError as e:
        API_FUNCTIONS_LOADED = False
        logger.error(f"GraphQL API関数のインポートエラー: {e}")
else:
    API_FUNCTIONS_LOADED = False
    if not GRAPHQL_AVAILABLE:
        logger.warning("GraphQLライブラリがないため、API関数をインポートできません")

API_REGISTERED = False

def register():
    """GraphQLモジュールの登録"""
    global API_REGISTERED
    
    if GRAPHQL_AVAILABLE:
        try:
            # リゾルバ関数のエイリアスを読み込み
            from . import resolvers_alias
            
            # API登録
            from . import api
            api.register()
            API_REGISTERED = True
            logger.info("GraphQL APIを登録しました")
        except Exception as e:
            logger.error(f"GraphQLモジュールの登録エラー: {e}")
            logger.error(traceback.format_exc())
            API_REGISTERED = False
    else:
        logger.warning("GraphQLライブラリが利用できないため、API登録をスキップします")
        API_REGISTERED = False
        logger.info("インストール方法: cd /Applications/Blender.app/Contents/Resources/4.4/python/bin && ./python3.11 -m pip install graphql-core")

def unregister():
    """GraphQLモジュールの登録解除"""
    logger.info("GraphQLモジュールを登録解除しています...")
    
    # 登録されていれば登録解除
    if MODULES_LOADED:
        try:
            hole_penetration.unregister()
            api.unregister()
            resolver.unregister()
            schema.unregister()
            logger.info("GraphQLモジュールの登録解除が完了しました")
        except Exception as e:
            logger.error(f"GraphQLモジュール登録解除エラー: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    else:
        logger.info("GraphQLモジュールは登録されていません")