"""
Unified MCP Command Registry
統合コマンドレジストリシステム

このモジュールは、Blender Unified MCPの全コマンドを管理するための中央レジストリを提供します。
異なるコマンドタイプを統一的に管理し、APIエンドポイントやUIからのアクセスを簡素化します。
"""

import logging
import inspect
from typing import Dict, List, Type, Any, Optional, Callable, Union

# ロギング設定
logger = logging.getLogger('unified_mcp.core.commands')

# シングルトンレジストリインスタンス
_registry = None

class CommandRegistry:
    """コマンドレジストリクラス - 全コマンドの登録と管理を行う"""
    
    def __init__(self):
        """初期化"""
        self.commands = {}  # 登録されたコマンド
        self.command_groups = {}  # グループ別コマンド
        self.validators = {}  # コマンドバリデータ
        
    def register(self, command_class: Type[Any], group: str = "general") -> bool:
        """コマンドクラスを登録"""
        try:
            # コマンド名を取得
            command_name = getattr(command_class, "name", command_class.__name__)
            
            # コマンドがすでに登録されている場合はスキップ
            if command_name in self.commands:
                logger.warning(f"コマンド '{command_name}' は既に登録されています")
                return False
            
            # グループが存在しない場合は作成
            if group not in self.command_groups:
                self.command_groups[group] = []
            
            # コマンドを登録
            self.commands[command_name] = command_class
            self.command_groups[group].append(command_name)
            
            logger.debug(f"コマンド '{command_name}' をグループ '{group}' に登録しました")
            return True
            
        except Exception as e:
            logger.error(f"コマンド登録中にエラーが発生しました: {str(e)}")
            return False
    
    def unregister(self, command_name: str) -> bool:
        """コマンドの登録を解除"""
        if command_name not in self.commands:
            logger.warning(f"コマンド '{command_name}' は登録されていません")
            return False
            
        # コマンドを登録解除
        command_class = self.commands.pop(command_name)
        
        # グループからも削除
        for group, commands in self.command_groups.items():
            if command_name in commands:
                commands.remove(command_name)
                
        logger.debug(f"コマンド '{command_name}' の登録を解除しました")
        return True
    
    def get_command(self, command_name: str) -> Optional[Type[Any]]:
        """コマンドを名前で取得"""
        return self.commands.get(command_name)
    
    def get_all_commands(self) -> Dict[str, Type[Any]]:
        """すべてのコマンドを取得"""
        return self.commands.copy()
    
    def get_command_groups(self) -> Dict[str, List[str]]:
        """すべてのコマンドグループを取得"""
        return self.command_groups.copy()
    
    def get_command_schema(self, command_name: str) -> Dict[str, Any]:
        """コマンドのスキーマを取得"""
        command_class = self.get_command(command_name)
        if not command_class:
            return {}
            
        # スキーマ情報を収集
        schema = {
            "name": command_name,
            "description": getattr(command_class, "description", ""),
            "group": self._find_command_group(command_name),
            "parameters": {}
        }
        
        # パラメータ情報を収集（可能であれば）
        if hasattr(command_class, "execute"):
            sig = inspect.signature(command_class.execute)
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                    
                param_info = {
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "any",
                    "required": param.default == inspect.Parameter.empty,
                }
                
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default
                    
                schema["parameters"][param_name] = param_info
                
        return schema
    
    def _find_command_group(self, command_name: str) -> str:
        """コマンドが属するグループを検索"""
        for group, commands in self.command_groups.items():
            if command_name in commands:
                return group
        return "general"
    
    def execute_command(self, command_name: str, **kwargs) -> Any:
        """コマンドを実行"""
        command_class = self.get_command(command_name)
        if not command_class:
            raise ValueError(f"コマンド '{command_name}' は登録されていません")
            
        # コマンドインスタンスを作成して実行
        try:
            command_instance = command_class()
            return command_instance.execute(**kwargs)
        except Exception as e:
            logger.error(f"コマンド '{command_name}' の実行中にエラーが発生しました: {str(e)}")
            raise

def get_registry() -> CommandRegistry:
    """コマンドレジストリのシングルトンインスタンスを取得"""
    global _registry
    if _registry is None:
        _registry = CommandRegistry()
    return _registry
