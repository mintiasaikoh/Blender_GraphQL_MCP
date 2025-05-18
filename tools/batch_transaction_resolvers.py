"""
GraphQLのバッチ処理とトランザクション関連のリゾルバモジュール
"""
import json
import logging
import traceback
from typing import Dict, Any, List, Optional

# 依存関係のインポートを整理
COMMANDS_AVAILABLE = False
try:
    from ..core.commands.batch_commands import execute_batch_command, parse_json_commands
    from ..core.commands.transaction_commands import (
        create_transaction_command, execute_transaction_command,
        get_transaction_info_command, delete_transaction_command
    )
    COMMANDS_AVAILABLE = True
except ImportError as e:
    # インポート失敗をキャッチするが、プログラムは継続
    pass

# ロギング設定 - 名前空間を統一
logger = logging.getLogger('blender_graphql_mcp.tools.batch_transaction_resolvers')

def resolve_execute_batch(root, info, commands_json: str = None) -> Dict[str, Any]:
    """
    バッチ実行リゾルバ
    
    Args:
        root: GraphQLのルートリゾルバオブジェクト
        info: GraphQLの実行情報
        commands_json: JSON形式のコマンドリスト
    
    Returns:
        バッチ実行結果
    """
    if not COMMANDS_AVAILABLE:
        logger.error("コマンドモジュールが利用できません")
        return {
            "success": False,
            "message": "コマンドモジュールがインポートできません",
            "commandCount": 0,
            "successfulCommands": 0,
            "executionTimeMs": 0,
            "results": "[]"
        }
    
    try:
        if not commands_json:
            return {
                "success": False,
                "message": "コマンドJSONが指定されていません",
                "commandCount": 0,
                "successfulCommands": 0,
                "executionTimeMs": 0,
                "results": "[]"
            }
        
        # コマンドJSONの解析
        commands = parse_json_commands(commands_json)
        
        if not commands:
            return {
                "success": False,
                "message": "有効なJSONコマンドリストではありません",
                "commandCount": 0,
                "successfulCommands": 0,
                "executionTimeMs": 0,
                "results": "[]"
            }
        
        # バッチ実行
        result = execute_batch_command(commands)
        
        # 実行結果をGraphQL形式に変換
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "commandCount": result.get("command_count", 0),
            "successfulCommands": result.get("successful_commands", 0),
            "executionTimeMs": result.get("execution_time_ms", 0),
            "results": json.dumps(result.get("results", []))
        }
    
    except Exception as e:
        logger.error(f"バッチ実行リゾルバエラー: {str(e)}")
        logger.debug(traceback.format_exc())  # 追加：デバッグログにスタックトレースを含める
        return {
            "success": False,
            "message": f"バッチ実行リゾルバエラー: {str(e)}",
            "commandCount": 0,
            "successfulCommands": 0,
            "executionTimeMs": 0,
            "results": "[]"
        }

def resolve_create_transaction(root, info, name: Optional[str] = None, commands_json: Optional[str] = None) -> Dict[str, Any]:
    """
    トランザクション作成リゾルバ
    
    Args:
        root: GraphQLのルートリゾルバオブジェクト
        info: GraphQLの実行情報
        name: トランザクション名
        commands_json: JSON形式のコマンドリスト
    
    Returns:
        トランザクション作成結果
    """
    if not COMMANDS_AVAILABLE:
        logger.error("コマンドモジュールが利用できません")
        return {
            "success": False,
            "message": "コマンドモジュールがインポートできません",
            "transactionId": "",
            "transactionName": "",
            "commandCount": 0,
            "executedCommands": 0,
            "executionTimeMs": 0,
            "results": "[]"
        }
    
    try:
        commands = None
        if commands_json:
            commands = parse_json_commands(commands_json)
        
        # トランザクション作成
        result = create_transaction_command(name, commands)
        
        if not result.get("success", False):
            return {
                "success": False,
                "message": result.get("message", "トランザクション作成エラー"),
                "transactionId": result.get("transaction_id", ""),
                "transactionName": result.get("transaction_name", ""),
                "commandCount": result.get("command_count", 0),
                "executedCommands": 0,
                "executionTimeMs": 0,
                "results": "[]"
            }
        
        return {
            "success": True,
            "message": result.get("message", "トランザクションを作成しました"),
            "transactionId": result.get("transaction_id", ""),
            "transactionName": result.get("transaction_name", ""),
            "commandCount": result.get("command_count", 0),
            "executedCommands": 0,
            "executionTimeMs": 0,
            "results": "[]"
        }
    
    except Exception as e:
        logger.error(f"トランザクション作成リゾルバエラー: {str(e)}")
        logger.debug(traceback.format_exc())  # 追加：デバッグログにスタックトレースを含める
        return {
            "success": False,
            "message": f"トランザクション作成リゾルバエラー: {str(e)}",
            "transactionId": "",
            "transactionName": "",
            "commandCount": 0,
            "executedCommands": 0,
            "executionTimeMs": 0,
            "results": "[]"
        }

def resolve_execute_transaction(root, info, transaction_id: str, create_snapshot: bool = True) -> Dict[str, Any]:
    """
    トランザクション実行リゾルバ
    
    Args:
        root: GraphQLのルートリゾルバオブジェクト
        info: GraphQLの実行情報
        transaction_id: トランザクションID
        create_snapshot: スナップショットを作成するかどうか
    
    Returns:
        トランザクション実行結果
    """
    if not COMMANDS_AVAILABLE:
        logger.error("コマンドモジュールが利用できません")
        return {
            "success": False,
            "message": "コマンドモジュールがインポートできません",
            "transactionId": transaction_id,
            "transactionName": "",
            "commandCount": 0,
            "executedCommands": 0,
            "executionTimeMs": 0,
            "results": "[]"
        }
    
    try:
        # トランザクション実行
        result = execute_transaction_command(transaction_id, create_snapshot)
        
        # 実行結果をGraphQL形式に変換
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "transactionId": result.get("transaction_id", ""),
            "transactionName": result.get("transaction_name", ""),
            "commandCount": result.get("command_count", 0),
            "executedCommands": result.get("executed_commands", 0),
            "executionTimeMs": result.get("execution_time_ms", 0),
            "results": json.dumps(result.get("results", []))
        }
    
    except Exception as e:
        logger.error(f"トランザクション実行リゾルバエラー: {str(e)}")
        logger.debug(traceback.format_exc())  # 追加：デバッグログにスタックトレースを含める
        return {
            "success": False,
            "message": f"トランザクション実行リゾルバエラー: {str(e)}",
            "transactionId": transaction_id,
            "transactionName": "",
            "commandCount": 0,
            "executedCommands": 0,
            "executionTimeMs": 0,
            "results": "[]"
        }

# リゾルバマップ
RESOLVERS = {
    "Mutation": {
        "executeBatch": resolve_execute_batch,
        "createTransaction": resolve_create_transaction,
        "executeTransaction": resolve_execute_transaction
    }
}