"""
バッチ処理関連のコマンドモジュール
複数のコマンドを一度に実行するバッチ処理機能を提供
"""

import logging
import json
from typing import Dict, Any, List, Optional

# バッチプロセッサをインポート
from ..batch_processor import BatchProcessor

# ロギング設定
logger = logging.getLogger("unified_mcp.commands.batch")

def execute_batch_command(commands: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    複数のコマンドをバッチで実行
    
    Args:
        commands: 実行するコマンドのリスト
            各コマンドは {"type": "コマンド名", "params": {...パラメータ}} の形式
        
    Returns:
        バッチ実行結果
    """
    try:
        # コマンドリストの検証
        if not commands:
            return {
                "success": False,
                "message": "コマンドリストが空です"
            }
            
        if not isinstance(commands, list):
            return {
                "success": False,
                "message": "commands パラメータはリスト形式で指定してください"
            }
        
        # バッチプロセッサの作成
        batch = BatchProcessor()
        
        # コマンドを追加
        for i, cmd in enumerate(commands):
            if not isinstance(cmd, dict):
                logger.warning(f"無効なコマンド形式をスキップします (インデックス {i}): {cmd}")
                continue
                
            cmd_type = cmd.get("type")
            cmd_params = cmd.get("params", {})
            
            if not cmd_type:
                logger.warning(f"type フィールドのないコマンドをスキップします (インデックス {i})")
                continue
                
            batch.add_command(cmd_type, cmd_params)
        
        # バッチを実行
        if len(batch.commands) == 0:
            return {
                "success": False,
                "message": "有効なコマンドがありません"
            }
            
        result = batch.process()
        return result
        
    except Exception as e:
        logger.error(f"バッチ実行エラー: {str(e)}")
        return {
            "success": False,
            "message": f"バッチ実行エラー: {str(e)}"
        }

def parse_json_commands(commands_json: str) -> List[Dict[str, Any]]:
    """
    JSON形式のコマンドリストを解析
    
    Args:
        commands_json: JSON形式のコマンドリスト
        
    Returns:
        解析されたコマンドリスト
    """
    try:
        commands = json.loads(commands_json)
        
        if not isinstance(commands, list):
            return []
            
        return commands
        
    except json.JSONDecodeError as e:
        logger.error(f"JSONデコードエラー: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"コマンド解析エラー: {str(e)}")
        return []

def execute_batch_json_command(commands_json: str) -> Dict[str, Any]:
    """
    JSON文字列で指定された複数のコマンドをバッチで実行
    
    Args:
        commands_json: JSON形式のコマンドリスト
        
    Returns:
        バッチ実行結果
    """
    try:
        # JSONの解析
        commands = parse_json_commands(commands_json)
        
        if not commands:
            return {
                "success": False,
                "message": "有効なJSONコマンドリストではありません"
            }
        
        # バッチ実行
        return execute_batch_command(commands)
        
    except Exception as e:
        logger.error(f"JSONバッチ実行エラー: {str(e)}")
        return {
            "success": False,
            "message": f"JSONバッチ実行エラー: {str(e)}"
        }