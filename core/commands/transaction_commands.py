"""
トランザクション関連のコマンドモジュール
トランザクション作成、実行、情報取得などの機能を提供
"""

import logging
import json
from typing import Dict, Any, List, Optional

# トランザクションモジュールをインポート
from ..transaction import (
    create_transaction, get_transaction, delete_transaction,
    cleanup_old_transactions
)

# ロギング設定
logger = logging.getLogger("unified_mcp.commands.transaction")

def create_transaction_command(name: Optional[str] = None, 
                              commands: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    新しいトランザクションを作成し、オプションでコマンドを追加
    
    Args:
        name: トランザクション名（オプション）
        commands: 実行するコマンドのリスト（オプション）
        
    Returns:
        作成結果
    """
    try:
        # トランザクションを作成
        transaction = create_transaction(name)
        
        # コマンドがあれば追加
        if commands:
            try:
                for cmd in commands:
                    if not isinstance(cmd, dict):
                        continue
                        
                    cmd_type = cmd.get("type")
                    cmd_params = cmd.get("params", {})
                    
                    if cmd_type:
                        transaction.add_command(cmd_type, cmd_params)
            except Exception as cmd_error:
                logger.error(f"コマンド追加エラー: {str(cmd_error)}")
                return {
                    "success": False,
                    "message": f"コマンド追加エラー: {str(cmd_error)}",
                    "transaction_id": transaction.id
                }
        
        return {
            "success": True,
            "message": f"トランザクション '{transaction.name}' を作成しました",
            "transaction_id": transaction.id,
            "transaction_name": transaction.name,
            "command_count": len(transaction.commands)
        }
        
    except Exception as e:
        logger.error(f"トランザクション作成エラー: {str(e)}")
        return {
            "success": False,
            "message": f"トランザクション作成エラー: {str(e)}"
        }

def execute_transaction_command(transaction_id: str, 
                                create_snapshot: bool = True) -> Dict[str, Any]:
    """
    トランザクションを実行
    
    Args:
        transaction_id: 実行するトランザクションのID
        create_snapshot: スナップショットを作成するかどうか
        
    Returns:
        実行結果
    """
    try:
        # トランザクションを取得
        transaction = get_transaction(transaction_id)
        
        if not transaction:
            return {
                "success": False,
                "message": f"トランザクション ID '{transaction_id}' が見つかりません"
            }
        
        # トランザクションを実行
        result = transaction.execute(create_snapshot=create_snapshot)
        return result
        
    except Exception as e:
        logger.error(f"トランザクション実行エラー: {str(e)}")
        return {
            "success": False,
            "message": f"トランザクション実行エラー: {str(e)}",
            "transaction_id": transaction_id
        }

def get_transaction_info_command(transaction_id: str) -> Dict[str, Any]:
    """
    トランザクション情報を取得
    
    Args:
        transaction_id: 情報を取得するトランザクションのID
        
    Returns:
        トランザクション情報
    """
    try:
        # トランザクションを取得
        transaction = get_transaction(transaction_id)
        
        if not transaction:
            return {
                "success": False,
                "message": f"トランザクション ID '{transaction_id}' が見つかりません"
            }
        
        # トランザクション情報を返す
        return {
            "success": True,
            "transaction_id": transaction.id,
            "transaction_name": transaction.name,
            "state": transaction.state,
            "command_count": len(transaction.commands),
            "results_count": len(transaction.results),
            "has_snapshot": transaction.snapshot is not None,
            "start_time": transaction.start_time,
            "end_time": transaction.end_time,
            "execution_time_ms": round((transaction.end_time - transaction.start_time) * 1000, 2) if transaction.end_time and transaction.start_time else None
        }
        
    except Exception as e:
        logger.error(f"トランザクション情報取得エラー: {str(e)}")
        return {
            "success": False,
            "message": f"トランザクション情報取得エラー: {str(e)}",
            "transaction_id": transaction_id
        }

def delete_transaction_command(transaction_id: str) -> Dict[str, Any]:
    """
    トランザクションを削除
    
    Args:
        transaction_id: 削除するトランザクションのID
        
    Returns:
        削除結果
    """
    try:
        # トランザクションを削除
        success = delete_transaction(transaction_id)
        
        if success:
            return {
                "success": True,
                "message": f"トランザクション ID '{transaction_id}' を削除しました"
            }
        else:
            return {
                "success": False,
                "message": f"トランザクション ID '{transaction_id}' が見つかりません"
            }
        
    except Exception as e:
        logger.error(f"トランザクション削除エラー: {str(e)}")
        return {
            "success": False,
            "message": f"トランザクション削除エラー: {str(e)}",
            "transaction_id": transaction_id
        }

def cleanup_transactions_command(max_age_seconds: int = 3600) -> Dict[str, Any]:
    """
    古いトランザクションをクリーンアップ
    
    Args:
        max_age_seconds: この秒数より古いトランザクションを削除
        
    Returns:
        クリーンアップ結果
    """
    try:
        # 古いトランザクションをクリーンアップ
        count = cleanup_old_transactions(max_age_seconds)
        
        return {
            "success": True,
            "message": f"{count} 個のトランザクションをクリーンアップしました",
            "cleaned_count": count
        }
        
    except Exception as e:
        logger.error(f"トランザクションクリーンアップエラー: {str(e)}")
        return {
            "success": False,
            "message": f"トランザクションクリーンアップエラー: {str(e)}"
        }