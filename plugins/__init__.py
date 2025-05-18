"""
Unified MCP プラグインシステム
拡張機能のためのプラグインアーキテクチャを提供

このモジュールは、Blender Unified MCPのコア機能を拡張するための
プラグインシステムを提供します。各プラグインは、特定のインターフェースに
従って実装され、動的に検出・読み込みされます。

Example:
    プラグインを作成するには、plugins/ ディレクトリに新しいPythonモジュールを
    追加し、以下の関数を実装します：
    
    def register_plugin():
        # プラグイン初期化コード
        return {
            'name': 'プラグイン名',
            'version': '1.0.0',
            'commands': [...],  # コマンドリスト
            'schema_extensions': [...],  # GraphQL拡張スキーマ
            'ui_components': [...],  # UIコンポーネント
        }
    
    def unregister_plugin():
        # プラグイン終了時のクリーンアップコード
        pass
"""

import os
import sys
import importlib
import logging
import traceback
from typing import Dict, List, Any, Optional, Callable

# ロギング設定
logger = logging.getLogger('unified_mcp.plugins')

# ユーザーのサイトパッケージを確実に参照できるようにする
user_site_packages = os.path.expanduser("~/.local/lib/python3.11/site-packages")
if os.path.exists(user_site_packages) and user_site_packages not in sys.path:
    sys.path.insert(0, user_site_packages)
    logger.info(f"プラグインシステム: ユーザーサイトパッケージを追加しました: {user_site_packages}")

# プラグイン管理用のグローバル辞書
registered_plugins = {}
plugin_commands = {}
plugin_schema_extensions = {}
plugin_ui_components = {}

class PluginManager:
    """プラグイン管理クラス"""
    
    @classmethod
    def discover_plugins(cls) -> List[str]:
        """
        plugins/ ディレクトリ内のプラグインを検出
        
        Returns:
            検出されたプラグインモジュール名のリスト
        """
        # プラグインディレクトリのパス
        addon_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plugin_dir = os.path.join(addon_path, "plugins")
        
        # 結果のリスト
        plugin_modules = []
        
        try:
            # ディレクトリ内のすべてのPythonファイルを検索
            for filename in os.listdir(plugin_dir):
                # プラグイン候補のみを処理（__init__.pyや_で始まるものは除く）
                if (filename.endswith(".py") and 
                    not filename.startswith("_") and 
                    filename != "__init__.py"):
                    module_name = filename[:-3]
                    plugin_modules.append(module_name)
                    
            logger.info(f"検出されたプラグイン: {', '.join(plugin_modules) if plugin_modules else 'なし'}")
            return plugin_modules
        except Exception as e:
            logger.error(f"プラグイン検索中にエラーが発生: {e}")
            return []
    
    @classmethod
    def load_plugin(cls, module_name: str) -> bool:
        """
        プラグインモジュールをロードして登録
        
        Args:
            module_name: プラグインのモジュール名
            
        Returns:
            ロードと登録が成功したかどうか
        """
        global registered_plugins
        
        try:
            # モジュールをインポート
            module = importlib.import_module(f".{module_name}", package="blender_json_mcp.plugins")
            
            # 必要な関数が実装されているか確認
            if not hasattr(module, "register_plugin"):
                logger.warning(f"プラグイン '{module_name}' には register_plugin() 関数がありません")
                return False
            
            # プラグインを登録
            plugin_info = module.register_plugin()
            
            # プラグイン情報の検証
            if not isinstance(plugin_info, dict):
                logger.warning(f"プラグイン '{module_name}' の register_plugin() が辞書を返しませんでした")
                return False
            
            # 登録プラグインに追加
            plugin_info['module'] = module
            plugin_info['module_name'] = module_name
            registered_plugins[module_name] = plugin_info
            
            # プラグインの各種機能を登録
            if 'commands' in plugin_info:
                cls._register_plugin_commands(module_name, plugin_info['commands'])
            
            if 'schema_extensions' in plugin_info:
                cls._register_plugin_schema_extensions(module_name, plugin_info['schema_extensions'])
            
            if 'ui_components' in plugin_info:
                cls._register_plugin_ui_components(module_name, plugin_info['ui_components'])
            
            logger.info(f"プラグイン '{module_name}' を登録しました (バージョン: {plugin_info.get('version', '不明')})")
            return True
        except Exception as e:
            logger.error(f"プラグイン '{module_name}' のロード中にエラーが発生: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    @classmethod
    def unload_plugin(cls, module_name: str) -> bool:
        """
        プラグインをアンロード
        
        Args:
            module_name: プラグインのモジュール名
            
        Returns:
            アンロードが成功したかどうか
        """
        global registered_plugins
        
        if module_name not in registered_plugins:
            logger.warning(f"プラグイン '{module_name}' は登録されていません")
            return False
        
        try:
            # プラグイン情報を取得
            plugin_info = registered_plugins[module_name]
            module = plugin_info['module']
            
            # アンロード関数が実装されていれば呼び出す
            if hasattr(module, "unregister_plugin"):
                module.unregister_plugin()
            
            # プラグインの各種機能を登録解除
            if 'commands' in plugin_info:
                cls._unregister_plugin_commands(module_name)
            
            if 'schema_extensions' in plugin_info:
                cls._unregister_plugin_schema_extensions(module_name)
            
            if 'ui_components' in plugin_info:
                cls._unregister_plugin_ui_components(module_name)
            
            # 登録プラグインから削除
            del registered_plugins[module_name]
            
            logger.info(f"プラグイン '{module_name}' を登録解除しました")
            return True
        except Exception as e:
            logger.error(f"プラグイン '{module_name}' のアンロード中にエラーが発生: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    @classmethod
    def _register_plugin_commands(cls, module_name: str, commands: List[Dict[str, Any]]):
        """プラグインのコマンドを登録"""
        global plugin_commands
        
        if not commands:
            return
        
        plugin_commands[module_name] = commands
        
        # コマンドシステムに登録
        try:
            from ..core.commands.base import register_plugin_commands
            register_plugin_commands(commands)
            logger.debug(f"プラグイン '{module_name}' のコマンド {len(commands)} 個を登録しました")
        except ImportError as e:
            logger.warning(f"コマンドシステムにアクセスできません: {e}")
    
    @classmethod
    def _unregister_plugin_commands(cls, module_name: str):
        """プラグインのコマンドを登録解除"""
        global plugin_commands
        
        if module_name not in plugin_commands:
            return
        
        # コマンドシステムから登録解除
        try:
            from ..core.commands.base import unregister_plugin_commands
            unregister_plugin_commands(plugin_commands[module_name])
            logger.debug(f"プラグイン '{module_name}' のコマンドを登録解除しました")
        except ImportError as e:
            logger.warning(f"コマンドシステムにアクセスできません: {e}")
        
        # プラグインコマンドから削除
        del plugin_commands[module_name]
    
    @classmethod
    def _register_plugin_schema_extensions(cls, module_name: str, schema_extensions: List[Dict[str, Any]]):
        """プラグインのGraphQLスキーマ拡張を登録"""
        global plugin_schema_extensions
        
        if not schema_extensions:
            return
        
        plugin_schema_extensions[module_name] = schema_extensions
        
        # GraphQLシステムに登録
        try:
            from ..tools.definitions import register_schema_extensions
            register_schema_extensions(schema_extensions)
            logger.debug(f"プラグイン '{module_name}' のスキーマ拡張 {len(schema_extensions)} 個を登録しました")
        except ImportError as e:
            logger.warning(f"GraphQLシステムにアクセスできません: {e}")
    
    @classmethod
    def _unregister_plugin_schema_extensions(cls, module_name: str):
        """プラグインのGraphQLスキーマ拡張を登録解除"""
        global plugin_schema_extensions
        
        if module_name not in plugin_schema_extensions:
            return
        
        # GraphQLシステムから登録解除
        try:
            from ..tools.definitions import unregister_schema_extensions
            unregister_schema_extensions(plugin_schema_extensions[module_name])
            logger.debug(f"プラグイン '{module_name}' のスキーマ拡張を登録解除しました")
        except ImportError as e:
            logger.warning(f"GraphQLシステムにアクセスできません: {e}")
        
        # プラグインスキーマ拡張から削除
        del plugin_schema_extensions[module_name]
    
    @classmethod
    def _register_plugin_ui_components(cls, module_name: str, ui_components: List[Dict[str, Any]]):
        """プラグインのUIコンポーネントを登録"""
        global plugin_ui_components
        
        if not ui_components:
            return
        
        plugin_ui_components[module_name] = ui_components
        
        # UIシステムに登録
        try:
            from ..ui.components import register_ui_components
            register_ui_components(ui_components)
            logger.debug(f"プラグイン '{module_name}' のUIコンポーネント {len(ui_components)} 個を登録しました")
        except ImportError as e:
            logger.warning(f"UIシステムにアクセスできません: {e}")
    
    @classmethod
    def _unregister_plugin_ui_components(cls, module_name: str):
        """プラグインのUIコンポーネントを登録解除"""
        global plugin_ui_components
        
        if module_name not in plugin_ui_components:
            return
        
        # UIシステムから登録解除
        try:
            from ..ui.components import unregister_ui_components
            unregister_ui_components(plugin_ui_components[module_name])
            logger.debug(f"プラグイン '{module_name}' のUIコンポーネントを登録解除しました")
        except ImportError as e:
            logger.warning(f"UIシステムにアクセスできません: {e}")
        
        # プラグインUIコンポーネントから削除
        del plugin_ui_components[module_name]
    
    @classmethod
    def get_plugin_info(cls, module_name: str = None) -> Dict[str, Any]:
        """
        プラグイン情報を取得
        
        Args:
            module_name: プラグインのモジュール名（Noneの場合はすべて）
            
        Returns:
            プラグイン情報の辞書
        """
        if module_name:
            return registered_plugins.get(module_name, {})
        else:
            # すべてのプラグイン情報を返す（モジュールオブジェクトを除く）
            result = {}
            for name, info in registered_plugins.items():
                info_copy = info.copy()
                info_copy.pop('module', None)  # モジュールオブジェクトは除外
                result[name] = info_copy
            return result


def register():
    """モジュールを登録"""
    logger.info("プラグインシステムを登録しています...")
    
    try:
        # 利用可能なプラグインを検出してロード
        for plugin_name in PluginManager.discover_plugins():
            PluginManager.load_plugin(plugin_name)
        
        logger.info(f"プラグインシステムの登録が完了しました（プラグイン数: {len(registered_plugins)}）")
    except Exception as e:
        logger.error(f"プラグインシステム登録中にエラーが発生: {e}")
        logger.debug(traceback.format_exc())


def unregister():
    """モジュールを登録解除"""
    logger.info("プラグインシステムを登録解除しています...")
    
    try:
        # 登録されたプラグインをすべてアンロード
        plugin_names = list(registered_plugins.keys())
        for plugin_name in plugin_names:
            PluginManager.unload_plugin(plugin_name)
        
        logger.info("プラグインシステムの登録解除が完了しました")
    except Exception as e:
        logger.error(f"プラグインシステム登録解除中にエラーが発生: {e}")
        logger.debug(traceback.format_exc())


# APIをエクスポート
__all__ = ['PluginManager', 'register', 'unregister']