"""
コマンドレジストリマネージャー
サーバーとコマンド間の連携を管理するためのモジュール
"""

import logging
import traceback
import importlib
from typing import Dict, Any, List, Optional, Callable, Type, Tuple, Union

from .base import COMMAND_REGISTRY, PLUGIN_COMMAND_REGISTRY, BlenderCommand
# 循環参照を避けるために直接インポートしない
# from .. import server  # 循環参照リスク
# 代わりに必要な時に動的にインポートする
from .. import threading as mcp_threading
from .. import errors

logger = logging.getLogger('unified_mcp.commands.registry')

class CommandRegistry:
    """
    サーバーとコマンドを連携させるためのレジストリマネージャー
    """
    
    def __init__(self):
        """初期化"""
        self.registered_commands = {}
        self.server_instance = None
    
    def initialize(self):
        """レジストリを初期化してサーバーに接続"""
        logger.info("コマンドレジストリを初期化しています...")
        
        # サーバーモジュールを動的にインポート
        try:
            # 循環参照を避けるために必要な時にインポート
            server_module = importlib.import_module('..server', package=__name__)
            
            # サーバーインスタンスを取得
            self.server_instance = server_module.get_server_instance()
            logger.info("サーバーインスタンスに接続しました")
        except ImportError as ie:
            logger.error(f"サーバーモジュールのインポートに失敗しました: {str(ie)}")
            return False
        except Exception as e:
            logger.error(f"サーバーインスタンスへの接続に失敗しました: {str(e)}")
            return False
        
        return True
    
    def register_all_commands(self):
        """すべてのコマンドをサーバーに登録"""
        logger.info("すべてのコマンドをサーバーに登録しています...")
        
        if not self.server_instance:
            logger.error("サーバーインスタンスが初期化されていません")
            return False
        
        # 標準コマンドを登録
        for cmd_name, cmd_class in COMMAND_REGISTRY.items():
            self.register_command(cmd_name, cmd_class)
        
        # プラグインコマンドを登録
        for cmd_name, cmd_def in PLUGIN_COMMAND_REGISTRY.items():
            self.register_plugin_command(cmd_name, cmd_def)
        
        logger.info(f"合計 {len(self.registered_commands)} 個のコマンドを登録しました")
        return True
    
    def register_command(self, cmd_name: str, cmd_class: Type[BlenderCommand]) -> bool:
        """
        標準コマンドをサーバーに登録
        
        Args:
            cmd_name: コマンド名
            cmd_class: コマンドクラス
            
        Returns:
            登録が成功したかどうか
        """
        if not self.server_instance:
            logger.error(f"コマンド '{cmd_name}' の登録に失敗: サーバーインスタンスが初期化されていません")
            return False
            
        try:
            # コマンドインスタンスを作成
            cmd_instance = cmd_class()
            
            # サーバーにコマンドハンドラを登録
            handler = self._create_handler_for_command(cmd_instance)
            self.server_instance.register_command(
                cmd_name,
                handler,
                description=cmd_instance.description,
                schema=cmd_instance.parameters_schema
            )
            
            # 登録済みコマンドに追加
            self.registered_commands[cmd_name] = {
                "instance": cmd_instance,
                "handler": handler,
                "type": "standard"
            }
            
            logger.info(f"コマンド '{cmd_name}' を登録しました")
            return True
            
        except Exception as e:
            logger.error(f"コマンド '{cmd_name}' の登録に失敗しました: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def register_plugin_command(self, cmd_name: str, cmd_def: Dict[str, Any]) -> bool:
        """
        プラグインコマンドをサーバーに登録
        
        Args:
            cmd_name: コマンド名
            cmd_def: プラグインコマンド定義
            
        Returns:
            登録が成功したかどうか
        """
        if not self.server_instance:
            logger.error(f"プラグインコマンド '{cmd_name}' の登録に失敗: サーバーインスタンスが初期化されていません")
            return False
            
        try:
            # プラグインハンドラを取得
            handler = cmd_def.get("handler")
            if not handler:
                logger.error(f"プラグインコマンド '{cmd_name}' には有効なハンドラがありません")
                return False
            
            # プラグイン情報
            description = cmd_def.get("description", f"プラグインコマンド: {cmd_name}")
            schema = cmd_def.get("schema", {})
            plugin_name = cmd_def.get("plugin_name", "不明")
            
            # サーバーにコマンドハンドラを登録
            wrapped_handler = self._create_handler_for_plugin(handler, cmd_name, plugin_name)
            self.server_instance.register_command(
                cmd_name,
                wrapped_handler,
                description=description,
                schema=schema
            )
            
            # 登録済みコマンドに追加
            self.registered_commands[cmd_name] = {
                "handler": wrapped_handler,
                "plugin_name": plugin_name,
                "type": "plugin"
            }
            
            logger.info(f"プラグインコマンド '{cmd_name}' (プラグイン: {plugin_name}) を登録しました")
            return True
            
        except Exception as e:
            logger.error(f"プラグインコマンド '{cmd_name}' の登録に失敗しました: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def unregister_all_commands(self):
        """すべてのコマンドの登録を解除"""
        logger.info("すべてのコマンドの登録を解除しています...")
        
        if not self.server_instance:
            logger.warning("サーバーインスタンスが初期化されていません")
            return False
        
        # すべてのコマンドの登録を解除
        for cmd_name in list(self.registered_commands.keys()):
            self.unregister_command(cmd_name)
        
        logger.info("すべてのコマンドの登録を解除しました")
        return True
    
    def unregister_command(self, cmd_name: str) -> bool:
        """
        コマンドの登録を解除
        
        Args:
            cmd_name: コマンド名
            
        Returns:
            登録解除が成功したかどうか
        """
        if not self.server_instance:
            logger.error(f"コマンド '{cmd_name}' の登録解除に失敗: サーバーインスタンスが初期化されていません")
            return False
            
        if cmd_name not in self.registered_commands:
            logger.warning(f"コマンド '{cmd_name}' は登録されていません")
            return False
            
        try:
            # サーバーからコマンドを登録解除
            self.server_instance.unregister_command(cmd_name)
            
            # 登録済みコマンドから削除
            cmd_type = self.registered_commands[cmd_name]["type"]
            del self.registered_commands[cmd_name]
            
            logger.info(f"{cmd_type}コマンド '{cmd_name}' の登録を解除しました")
            return True
            
        except Exception as e:
            logger.error(f"コマンド '{cmd_name}' の登録解除に失敗しました: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def _create_handler_for_command(self, cmd_instance: BlenderCommand) -> Callable:
        """
        コマンドインスタンスのハンドラ関数を作成
        
        Args:
            cmd_instance: コマンドインスタンス
            
        Returns:
            サーバーに登録するためのハンドラ関数
        """
        def handler(**params):
            """コマンド実行ハンドラ"""
            try:
                # パラメータのバリデーション
                validation = cmd_instance.validate(params)
                if not validation.get("valid", False):
                    errors_list = validation.get("errors", ["不明なバリデーションエラー"])
                    error_message = "; ".join(errors_list)
                    raise errors.ValidationError(error_message)
                
                # 実行前処理
                pre_state = cmd_instance.pre_execute(params)
                
                # コマンド実行
                result = cmd_instance.execute(params, pre_state)
                
                # 実行後処理
                post_result = cmd_instance.post_execute(params, pre_state, result)
                
                # 最終結果を返す
                return post_result
                
            except Exception as e:
                logger.error(f"コマンド '{cmd_instance.command_name}' の実行中にエラーが発生しました: {str(e)}")
                logger.debug(traceback.format_exc())
                
                # エラーを伝搬
                raise
        
        return handler
    
    def _create_handler_for_plugin(self, plugin_handler: Callable, cmd_name: str, plugin_name: str) -> Callable:
        """
        プラグインハンドラをラップする関数を作成
        
        Args:
            plugin_handler: プラグインのハンドラ関数
            cmd_name: コマンド名
            plugin_name: プラグイン名
            
        Returns:
            サーバーに登録するためのハンドラ関数
        """
        def handler(**params):
            """プラグインコマンド実行ハンドラ"""
            try:
                # プラグインハンドラを実行
                return plugin_handler(**params)
                
            except Exception as e:
                logger.error(f"プラグインコマンド '{cmd_name}' (プラグイン: {plugin_name}) の実行中にエラーが発生しました: {str(e)}")
                logger.debug(traceback.format_exc())
                
                # エラーを伝搬
                raise
        
        return handler

# グローバルレジストリインスタンス
_registry_instance = None

def get_registry():
    """コマンドレジストリのシングルトンインスタンスを取得"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CommandRegistry()
    return _registry_instance

def register():
    """コマンドレジストリを初期化して登録"""
    registry = get_registry()
    
    # レジストリを初期化
    if not registry.initialize():
        logger.error("コマンドレジストリの初期化に失敗しました")
        return False
    
    # すべてのコマンドを登録
    if not registry.register_all_commands():
        logger.error("コマンドの登録に失敗しました")
        return False
    
    return True

def unregister():
    """コマンドレジストリの登録を解除"""
    registry = get_registry()
    
    # すべてのコマンドの登録を解除
    registry.unregister_all_commands()
    
    # グローバルインスタンスをクリア
    global _registry_instance
    _registry_instance = None
