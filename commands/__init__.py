"""
Blender Unified MCP コマンドシステム
"""

import logging
from typing import Dict, List, Type, Any

from .blender_commands import available_commands, BlenderCommand

# ロガー設定
logger = logging.getLogger('unified_mcp.commands')

# コマンドレジストリ
class CommandRegistry:
    """コマンド登録と管理システム"""
    
    def __init__(self):
        self.commands: Dict[str, Type[BlenderCommand]] = {}
        self.command_groups: Dict[str, List[str]] = {
            "default": [],
            "objects": [],
            "scene": [],
            "camera": [],
            "blender": []
        }
    
    def register(self, command_class: Type[BlenderCommand]) -> bool:
        """新しいコマンドを登録"""
        try:
            name = getattr(command_class, 'name', command_class.__name__)
            self.commands[name] = command_class
            
            # グループによる整理
            group = getattr(command_class, 'group', 'default')
            if group not in self.command_groups:
                self.command_groups[group] = []
            
            if name not in self.command_groups[group]:
                self.command_groups[group].append(name)
            
            logger.info(f"コマンド '{name}' を登録しました (グループ: {group})")
            return True
        
        except Exception as e:
            logger.error(f"コマンド登録エラー: {str(e)}")
            return False
    
    def execute(self, command_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """コマンドを実行"""
        if not params:
            params = {}
        
        if command_name not in self.commands:
            error_message = f"コマンド '{command_name}' が見つかりません"
            logger.error(error_message)
            return {
                "success": False,
                "error": error_message
            }
            
        try:
            command_class = self.commands[command_name]
            command_instance = command_class()
            
            # コマンドを実行
            result = command_instance.execute(**params)
            
            return result
            
        except Exception as e:
            error_message = f"コマンド '{command_name}' の実行中にエラーが発生しました: {str(e)}"
            logger.error(error_message)
            return {
                "success": False,
                "error": error_message
            }
    
    def get_all_commands(self) -> Dict[str, Dict[str, Any]]:
        """すべてのコマンド情報を取得"""
        result = {}
        for name, cmd_class in self.commands.items():
            result[name] = {
                'name': name,
                'description': getattr(cmd_class, 'description', '抽象コマンド'),
                'group': getattr(cmd_class, 'group', 'default'),
                'parameters': cmd_class.get_parameter_schema()
            }
        return result
        
    def clear(self):
        """レジストリをクリア"""
        self.commands.clear()
        for group in self.command_groups:
            self.command_groups[group] = []
        logger.info("コマンドレジストリをクリアしました")

# シングルトンインスタンス
_registry = CommandRegistry()

def get_registry() -> CommandRegistry:
    """コマンドレジストリのシングルトンインスタンスを取得"""
    return _registry

def register_all_commands():
    """すべての利用可能なコマンドを登録"""
    registry = get_registry()
    
    # 登録前にクリア
    registry.clear()
    
    # すべてのコマンドを登録
    for command_class in available_commands:
        registry.register(command_class)
    
    logger.info(f"{len(available_commands)} 個のコマンドを登録しました")

# モジュール初期化時に自動登録
register_all_commands()
