"""
Unified MCP Core Module
MCPの中核機能を提供するモジュール - 再構築版 v1.4

統合されたアーキテクチャに基づき、以下のコンポーネントを統合しました：
- 統合サーバー基盤 (FastAPI/標準HTTPの両方をサポート)
- スレッド処理システム
- エラー処理システム
- 統一コマンドレジストリ

モジュール整理の一環として、既存のコードとの互換性を維持しながら、より整理された構造を実現しています。
"""

import importlib
import logging
import traceback
import sys
import os
import inspect

# サイトパッケージの確認と追加
def _ensure_dependencies():
    """Pythonサーバーで使用する依存関係が確実に利用可能か確認"""
    try:
        # アドオンのルートディレクトリを取得
        addon_root = os.path.dirname(os.path.dirname(__file__))
        
        # vendorディレクトリを確認
        vendor_dir = os.path.join(addon_root, "vendor")
        if os.path.exists(vendor_dir) and vendor_dir not in sys.path:
            sys.path.insert(0, vendor_dir)
            logging.getLogger('unified_mcp.core').info(f"Pythonパスに追加: {vendor_dir}")
        
        # ユーザーのサイトパッケージを確認
        user_site = os.path.expanduser("~/.local/lib/python3.11/site-packages")
        if os.path.exists(user_site) and user_site not in sys.path:
            sys.path.insert(0, user_site)
            logging.getLogger('unified_mcp.core').info(f"Pythonパスに追加: {user_site}")
        
        # pydanticが使えるか確認
        try:
            import pydantic
            logging.getLogger('unified_mcp.core').info(f"Pydantic v{pydantic.__version__} をロードしました")
        except ImportError as e:
            logging.getLogger('unified_mcp.core').warning(f"Pydanticのインポートに失敗しました: {str(e)}")
    
    except Exception as e:
        logging.getLogger('unified_mcp.core').error(f"依存関係確認中にエラーが発生しました: {str(e)}")

# 依存関係の確認を実行
_ensure_dependencies()

# ロギング設定
logger = logging.getLogger('unified_mcp.core')

# モジュール再読込時の処理
if "errors" in locals():
    importlib.reload(errors)
    importlib.reload(threading)
    importlib.reload(server)
    importlib.reload(commands)
    
    # コマンドモジュールの再読込
    if "standard_commands" in locals():
        importlib.reload(standard_commands)
    if "object_commands" in locals():
        importlib.reload(object_commands)
    if "high_level_commands" in locals():
        importlib.reload(high_level_commands)
    
    # 統合モジュールの再読込
    if "enhanced_integration" in locals():
        importlib.reload(enhanced_integration)
    
    # 互換性のためのレガシーモジュールの再読込
    if "helpers" in locals():
        importlib.reload(helpers)
    if "api" in locals():
        importlib.reload(api)
    if "http_server" in locals():
        importlib.reload(http_server)
    if "command_handler" in locals():
        importlib.reload(command_handler)

# コアサブモジュール
from . import errors                # エラー処理
from . import threading             # スレッド処理
from . import server                # 統合サーバー
from . import commands              # コマンドシステム
from . import enhanced_integration  # 統合インターフェース

# コマンド登録統一関数
def register_commands():
    """すべてのコマンドを登録"""
    registry = commands.get_registry()
    
    # 標準コマンドを登録
    try:
        from .standard_commands import register_standard_commands
        register_standard_commands(registry)
        logger.info("標準コマンドを登録しました")
    except ImportError as e:
        logger.debug(f"標準コマンドを登録できませんでした: {str(e)}")
    
    # オブジェクトコマンドを登録
    try:
        from .object_commands import register_object_commands
        register_object_commands(registry)
        logger.info("オブジェクトコマンドを登録しました")
    except ImportError as e:
        logger.debug(f"オブジェクトコマンドを登録できませんでした: {str(e)}")
    
    # 高レベルコマンドを登録
    try:
        from .high_level_commands import register_high_level_commands
        register_high_level_commands(registry)
        logger.info("高レベルコマンドを登録しました")
    except ImportError as e:
        logger.debug(f"高レベルコマンドを登録できませんでした: {str(e)}")
    
    # レガシーコマンドを互換性のために登録
    try:
        from .command_handler import register_legacy_commands
        register_legacy_commands(registry)
        logger.info("レガシーコマンドを登録しました")
    except ImportError as e:
        logger.debug(f"レガシーコマンドを登録できませんでした: {str(e)}")
    
    return registry

# コマンドのサブモジュール（利用可能であれば）
try:
    from . import standard_commands  # 標準コマンド
except ImportError as e:
    logger.debug(f"標準コマンドモジュールをロードできませんでした: {str(e)}")
    
# 互換性のためのレガシーモジュール（利用可能であれば）
try:
    try:
        from . import helpers
        HELPERS_LOADED = True
    except ImportError:
        HELPERS_LOADED = False
        logger.debug("ヘルパーモジュールをロードできませんでした")
    
    # セキュアなAPIモジュールを優先的に使用
    try:
        from . import api_handlers_secure as api
        logger.info("セキュアなAPIモジュールを読み込みました")
    except ImportError:
        from . import api
        logger.warning("従来のAPIモジュールを読み込みました")
    
    from . import http_server
    
    # セキュアなメタコマンドモジュールを優先的に使用
    try:
        from . import meta_commands_secure
        logger.info("セキュアなメタコマンドモジュールを読み込みました")
    except ImportError:
        from . import meta_commands
        logger.warning("従来のメタコマンドモジュールを読み込みました")
    
    from . import command_handler
    LEGACY_MODULES_LOADED = True
    API_LOADED = True
    HTTP_SERVER_LOADED = True
except ImportError as e:
    HELPERS_LOADED = False
    LEGACY_MODULES_LOADED = False
    API_LOADED = False
    HTTP_SERVER_LOADED = False
    logger.debug(f"レガシーモジュールの一部をロードできませんでした: {str(e)}")

def register():
    """コアモジュールの登録"""
    logger.info("=== 統合MCPコアモジュールを登録中... ===")
    
    # エラーモジュールを登録
    try:
        # errorsモジュールに登録関数があれば実行
        if hasattr(errors, 'register'):
            errors.register()
        logger.info("エラー処理モジュールを初期化しました")
    except Exception as e:
        logger.error(f"エラー処理モジュールの初期化に失敗しました: {str(e)}")
    
    # 既存のヘルパーモジュールを登録 (必要なら)
    if HELPERS_LOADED:
        try:
            helpers.register()
            logger.info("ヘルパーモジュールを登録しました")
        except Exception as e:
            logger.error(f"ヘルパーモジュールの登録に失敗しました: {str(e)}")
    
    # スレッド処理モジュールを登録
    try:
        threading.initialize()
        logger.info("スレッド処理モジュールを初期化しました")
    except Exception as e:
        logger.error(f"スレッド処理モジュールの初期化に失敗しました: {str(e)}")
        logger.debug(traceback.format_exc())
    
    # 統合サーバーモジュールを登録
    try:
        server.register()
        logger.info("統合サーバーモジュールを登録しました")
    except Exception as e:
        logger.error(f"統合サーバーモジュールの登録に失敗しました: {str(e)}")
        logger.debug(traceback.format_exc())
    
    # コマンドモジュールを登録
    try:
        commands.register()
        logger.info("コマンドモジュールを登録しました")
    except Exception as e:
        logger.error(f"コマンドモジュールの登録に失敗しました: {str(e)}")
        logger.debug(traceback.format_exc())
    
    # 互換性のための既存APIモジュールを登録 (必要なら)
    if API_LOADED:
        try:
            api.register()
            logger.info("APIモジュールを登録しました")
        except Exception as e:
            logger.error(f"APIモジュールの登録に失敗しました: {str(e)}")
    
    # 互換性のための既存HTTPサーバーモジュールを登録 (使用しないが互換性のために登録)
    if HTTP_SERVER_LOADED and False:  # 必要な場合はFalseを外す
        try:
            http_server.register()
            logger.info("既存HTTPサーバーモジュールを登録しました")
        except Exception as e:
            logger.error(f"既存HTTPサーバーモジュールの登録に失敗しました: {str(e)}")
    
    logger.info("=== 統合MCPコアモジュールの登録完了 ===")

def unregister():
    """コアモジュールの登録解除"""
    logger.info("=== 統合MCPコアモジュールの登録解除中... ===")
    
    # 逆順で登録解除
    
    # 互換性のための既存HTTPサーバーモジュールの登録解除 (必要なら)
    if HTTP_SERVER_LOADED and False:  # 必要な場合はFalseを外す
        try:
            http_server.unregister()
            logger.info("既存HTTPサーバーモジュールの登録を解除しました")
        except Exception as e:
            logger.error(f"既存HTTPサーバーモジュールの登録解除に失敗しました: {str(e)}")
    
    # 互換性のための既存APIモジュールの登録解除 (必要なら)
    if API_LOADED:
        try:
            api.unregister()
            logger.info("APIモジュールの登録を解除しました")
        except Exception as e:
            logger.error(f"APIモジュールの登録解除に失敗しました: {str(e)}")
    
    # コマンドモジュールの登録解除
    try:
        commands.unregister()
        logger.info("コマンドモジュールの登録を解除しました")
    except Exception as e:
        logger.error(f"コマンドモジュールの登録解除に失敗しました: {str(e)}")
        logger.debug(traceback.format_exc())
    
    # 統合サーバーモジュールの登録解除
    try:
        server.unregister()
        logger.info("統合サーバーモジュールの登録を解除しました")
    except Exception as e:
        logger.error(f"統合サーバーモジュールの登録解除に失敗しました: {str(e)}")
        logger.debug(traceback.format_exc())
    
    # スレッド処理モジュールの登録解除
    try:
        threading.shutdown()
        logger.info("スレッド処理モジュールをシャットダウンしました")
    except Exception as e:
        logger.error(f"スレッド処理モジュールのシャットダウンに失敗しました: {str(e)}")
        logger.debug(traceback.format_exc())
    
    # 既存のヘルパーモジュールの登録解除 (必要なら)
    if HELPERS_LOADED:
        try:
            helpers.unregister()
            logger.info("ヘルパーモジュールの登録を解除しました")
        except Exception as e:
            logger.error(f"ヘルパーモジュールの登録解除に失敗しました: {str(e)}")
    
    # エラー処理モジュールの登録解除
    try:
        # errorsモジュールにunregister関数があれば実行
        if hasattr(errors, 'unregister'):
            errors.unregister()
        logger.info("エラー処理モジュールの登録を解除しました")
    except Exception as e:
        logger.error(f"エラー処理モジュールの登録解除に失敗しました: {str(e)}")
    
    logger.info("=== 統合MCPコアモジュールの登録解除完了 ===")