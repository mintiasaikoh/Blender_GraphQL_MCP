"""
コマンド基底クラス
すべてのBlender操作コマンドの基底となるクラスとコマンド登録システム
"""

import bpy
import traceback
import json
import time
from typing import Dict, Any, List, Optional, Callable, Type

# コマンド登録用の辞書
COMMAND_REGISTRY = {}

# プラグインコマンド登録用の辞書
PLUGIN_COMMAND_REGISTRY = {}

class BlenderCommand:
    """
    すべてのBlenderコマンドの基底クラス
    
    コマンドの実行フロー:
    1. validate: パラメータの検証
    2. pre_execute: 実行前の準備（状態の記録など）
    3. execute: 実際のコマンド実行
    4. post_execute: 実行後の処理（結果検証など）
    """
    
    # コマンド名（サブクラスでオーバーライド）
    command_name = None
    
    # コマンドの説明（サブクラスでオーバーライド）
    description = "基本Blenderコマンド"
    
    # パラメータのJSONスキーマ（サブクラスでオーバーライド）
    parameters_schema = {}
    
    def __init__(self):
        """初期化"""
        if not self.command_name:
            raise ValueError("コマンド名が指定されていません")
    
    def validate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        パラメータのバリデーション
        
        Args:
            params: コマンドパラメータ
            
        Returns:
            検証結果: {"valid": bool, "errors": List[str]}
        """
        return {"valid": True, "errors": []}
    
    def pre_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        実行前処理（オプション）
        
        Args:
            params: 検証済みパラメータ
            
        Returns:
            前処理の状態情報
        """
        # デフォルトでは何もしない
        return {"before_state": None}
    
    def execute(self, params: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        コマンド実行（サブクラスで実装必須）
        
        Args:
            params: 検証済みパラメータ
            pre_state: 前処理の状態情報
            
        Returns:
            実行結果
        """
        raise NotImplementedError("サブクラスで実装する必要があります")
    
    def post_execute(self, params: Dict[str, Any], result: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        実行後処理（オプション）
        
        Args:
            params: 検証済みパラメータ
            result: 実行結果
            pre_state: 前処理の状態情報
            
        Returns:
            最終結果
        """
        # デフォルトでは結果をそのまま返す
        return result
    
    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        コマンドの実行（メインエントリポイント）
        
        Args:
            params: コマンドパラメータ
            
        Returns:
            コマンド実行結果
        """
        try:
            # パラメータ検証
            validation = self.validate(params)
            if not validation.get("valid", False):
                return {
                    "success": False,
                    "command": self.command_name,
                    "errors": validation.get("errors", ["パラメータ検証エラー"]),
                    "result": None
                }
            
            # 前処理
            pre_state = self.pre_execute(params)
            
            # 実行
            result = self.execute(params, pre_state)
            
            # 後処理
            final_result = self.post_execute(params, result, pre_state)
            
            # 結果をラップ
            return {
                "success": True,
                "command": self.command_name,
                "result": final_result
            }
            
        except Exception as e:
            # エラーハンドリング
            error_msg = str(e)
            stack_trace = traceback.format_exc()
            
            return {
                "success": False,
                "command": self.command_name,
                "errors": [error_msg],
                "stack_trace": stack_trace,
                "result": None
            }


def register_command(command_class: Type[BlenderCommand]) -> None:
    """
    コマンドをレジストリに登録
    
    Args:
        command_class: 登録するコマンドクラス
    """
    instance = command_class()
    COMMAND_REGISTRY[instance.command_name] = command_class


def register_plugin_commands(commands: List[Dict[str, Any]]) -> None:
    """
    プラグインからのコマンドをレジストリに登録
    
    Args:
        commands: コマンド定義のリスト
    """
    for cmd_def in commands:
        # 必須フィールドのチェック
        if not all(key in cmd_def for key in ['name', 'callback']):
            print(f"プラグインコマンド登録エラー: 必須フィールドがありません {cmd_def.get('name', 'unknown')}")
            continue
        
        # 既存コマンドとの名前衝突をチェック
        cmd_name = cmd_def['name']
        if cmd_name in COMMAND_REGISTRY:
            print(f"プラグインコマンド登録警告: コマンド名 '{cmd_name}' は既に登録されています")
            continue
        
        # プラグインコマンドを登録
        PLUGIN_COMMAND_REGISTRY[cmd_name] = cmd_def
        print(f"プラグインコマンド '{cmd_name}' を登録しました")


def unregister_plugin_commands(commands: List[Dict[str, Any]]) -> None:
    """
    プラグインからのコマンドを登録解除
    
    Args:
        commands: コマンド定義のリスト
    """
    for cmd_def in commands:
        cmd_name = cmd_def.get('name')
        if cmd_name and cmd_name in PLUGIN_COMMAND_REGISTRY:
            del PLUGIN_COMMAND_REGISTRY[cmd_name]
            print(f"プラグインコマンド '{cmd_name}' を登録解除しました")


def get_command(command_name: str) -> Optional[Type[BlenderCommand]]:
    """
    名前からコマンドクラスを取得
    
    Args:
        command_name: コマンド名
        
    Returns:
        コマンドクラスまたはNone
    """
    return COMMAND_REGISTRY.get(command_name)


def get_plugin_command(command_name: str) -> Optional[Dict[str, Any]]:
    """
    名前からプラグインコマンドを取得
    
    Args:
        command_name: コマンド名
        
    Returns:
        プラグインコマンド定義またはNone
    """
    return PLUGIN_COMMAND_REGISTRY.get(command_name)


def execute_command(command_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    コマンドを実行
    
    Args:
        command_data: コマンドデータ {"command": "コマンド名", "params": {...}}
        
    Returns:
        実行結果
    """
    start_time = time.time()
    command_name = command_data.get("command")
    params = command_data.get("params", {})
    
    if not command_name:
        return {
            "success": False,
            "errors": ["コマンド名が指定されていません"],
            "result": None,
            "execution_time_ms": round((time.time() - start_time) * 1000, 2)
        }
    
    # 標準コマンドを確認
    command_class = get_command(command_name)
    if command_class:
        command = command_class()
        result = command.run(params)
        # 実行時間を追加
        result["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return result
    
    # プラグインコマンドを確認
    plugin_command = get_plugin_command(command_name)
    if plugin_command:
        try:
            # プラグインコマンドのコールバックを実行
            callback = plugin_command['callback']
            result = callback(params)
            
            # 結果が辞書でない場合はラップする
            if not isinstance(result, dict):
                result = {"data": result}
            
            # 成功情報を追加
            if "success" not in result:
                result["success"] = True
            
            # 実行時間を追加
            result["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return result
        except Exception as e:
            error_msg = f"プラグインコマンド '{command_name}' の実行中にエラーが発生: {str(e)}"
            stack_trace = traceback.format_exc()
            
            return {
                "success": False,
                "command": command_name,
                "errors": [error_msg],
                "stack_trace": stack_trace,
                "result": None
            }
    
    # コマンドが見つからない
    return {
        "success": False,
        "errors": [f"コマンド '{command_name}' は登録されていません"],
        "result": None,
        "execution_time_ms": round((time.time() - start_time) * 1000, 2)
    }


def register_commands():
    """
    すべてのコマンドを登録
    この関数は、すべてのコマンドモジュールがインポートされた後に呼び出す必要があります
    
    Returns:
        List: 登録されたモジュールのリスト（登録解除に使用）
    """
    import importlib
    import logging
    import traceback
    from pathlib import Path
    
    # ロギング設定
    logger = logging.getLogger('unified_mcp.commands')
    logger.info("コマンドシステムを登録しています...")
    
    # コマンドディレクトリのパスを取得
    cmd_dir = Path(__file__).parent
    
    # インポートされたモジュールを追跡
    imported_modules = []
    
    # コマンドモジュールを動的にインポート
    for cmd_file in cmd_dir.glob("*.py"):
        if cmd_file.name == "__init__.py" or cmd_file.name == "base.py":
            continue
            
        module_name = cmd_file.stem
        try:
            # モジュールをインポート
            module = importlib.import_module(f".{module_name}", package="blender_json_mcp.core.commands")
            logger.info(f"コマンドモジュール '{module_name}' をインポートしました")
            imported_modules.append(module)
            
            # 明示的に登録関数があれば呼び出し
            if hasattr(module, 'register'):
                try:
                    module.register()
                    logger.info(f"コマンドモジュール '{module_name}' の登録関数を実行しました")
                except Exception as e:
                    logger.error(f"コマンドモジュール '{module_name}' の登録処理に失敗しました: {str(e)}")
                    logger.debug(traceback.format_exc())
                
        except ImportError as e:
            logger.error(f"コマンドモジュール '{module_name}' のインポートに失敗しました: {str(e)}")
        except Exception as e:
            logger.error(f"コマンドモジュール '{module_name}' の処理中に予期しないエラーが発生しました: {str(e)}")
            logger.debug(traceback.format_exc())
    
    # 登録結果を記録
    standard_commands = len(COMMAND_REGISTRY)
    plugin_commands = len(PLUGIN_COMMAND_REGISTRY)
    logger.info(f"コマンド登録完了: 標準コマンド {standard_commands}個、プラグインコマンド {plugin_commands}個")
    
    return imported_modules  # 後の登録解除のためにモジュールリストを返す


def unregister_commands(imported_modules=None):
    """
    登録されたコマンドを登録解除
    
    Args:
        imported_modules: register_commandsから返されたモジュールリスト。
                         Noneの場合、全てのコマンドレジストリをクリアするのみ。
    """
    import logging
    import traceback
    
    # ロギング設定
    logger = logging.getLogger('unified_mcp.commands')
    logger.info("コマンドシステムを登録解除しています...")
    
    # モジュールの登録解除関数を呼び出す
    if imported_modules is not None:
        for module in reversed(imported_modules):  # 登録と逆順に解除
            if hasattr(module, 'unregister'):
                try:
                    module.unregister()
                    logger.info(f"コマンドモジュール '{module.__name__.split('.')[-1]}' の登録解除関数を実行しました")
                except Exception as e:
                    logger.error(f"コマンドモジュールの登録解除処理に失敗しました: {str(e)}")
                    logger.debug(traceback.format_exc())
    
    # コマンドレジストリをクリア
    global COMMAND_REGISTRY, PLUGIN_COMMAND_REGISTRY
    cmd_count = len(COMMAND_REGISTRY)
    plugin_cmd_count = len(PLUGIN_COMMAND_REGISTRY)
    
    COMMAND_REGISTRY.clear()
    PLUGIN_COMMAND_REGISTRY.clear()
    
    logger.info(f"コマンド登録解除完了: 標準コマンド {cmd_count}個、プラグインコマンド {plugin_cmd_count}個を解除しました")


def get_all_commands() -> Dict[str, Dict[str, Any]]:
    """
    すべての利用可能なコマンド情報を取得
    
    Returns:
        コマンド情報を含む辞書
    """
    commands = {}
    
    # 標準コマンド
    for cmd_name, cmd_class in COMMAND_REGISTRY.items():
        instance = cmd_class()
        commands[cmd_name] = {
            "name": cmd_name,
            "description": instance.description,
            "schema": instance.parameters_schema,
            "plugin": False
        }
    
    # プラグインコマンド
    for cmd_name, cmd_def in PLUGIN_COMMAND_REGISTRY.items():
        commands[cmd_name] = {
            "name": cmd_name,
            "description": cmd_def.get("description", "プラグインコマンド"),
            "schema": cmd_def.get("schema", {}),
            "plugin": True,
            "plugin_name": cmd_def.get("plugin_name", "不明")
        }
    
    return commands
