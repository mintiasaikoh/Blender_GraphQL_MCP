"""トランザクション処理モジュール
複数のコマンドをアトミックに実行するための機能を提供
"""

import bpy
import json
import logging
import time
import uuid
from typing import List, Dict, Any, Optional, Callable

# ロギング設定
logger = logging.getLogger('unified_mcp.transaction')

class Transaction:
    """
    複数のコマンドをまとめて実行するトランザクションクラス
    """
    
    def __init__(self, name: Optional[str] = None):
        """トランザクションを初期化"""
        self.id = str(uuid.uuid4())
        self.name = name or f"Transaction_{self.id[:8]}"
        self.commands = []
        self.state = "initialized"
        self.results = []
        self.start_time = None
        self.end_time = None
        self.snapshot = None  # 実行前の状態スナップショット
        
        logger.info(f"トランザクション '{self.name}' ({self.id}) を初期化しました")
    
    def add_command(self, command_type: str, params: Dict[str, Any]) -> None:
        """コマンドをトランザクションに追加"""
        if self.state != "initialized":
            raise ValueError(f"トランザクションは '{self.state}' 状態です。コマンドを追加できません。")
            
        self.commands.append({
            "type": command_type,
            "params": params,
            "added_at": time.time()
        })
        
        logger.debug(f"トランザクション '{self.name}' にコマンド '{command_type}' を追加しました")
    
    def create_snapshot(self) -> Dict[str, Any]:
        """現在のBlender状態のスナップショットを作成"""
        snapshot = {
            "objects": {},
            "scene": {
                "name": bpy.context.scene.name,
                "frame_current": bpy.context.scene.frame_current
            }
        }
        
        # 主要なオブジェクト情報を保存
        for obj in bpy.data.objects:
            snapshot["objects"][obj.name] = {
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
                "hide": obj.hide_get()
            }
        
        return snapshot
    
    def restore_from_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """スナップショットからBlenderの状態を復元"""
        try:
            # シーン設定を復元
            if "scene" in snapshot:
                scene = bpy.context.scene
                scene.frame_current = snapshot["scene"].get("frame_current", scene.frame_current)
            
            # オブジェクト状態を復元
            if "objects" in snapshot:
                for obj_name, obj_data in snapshot["objects"].items():
                    obj = bpy.data.objects.get(obj_name)
                    if obj:
                        if "location" in obj_data:
                            obj.location = obj_data["location"]
                        if "rotation" in obj_data:
                            obj.rotation_euler = obj_data["rotation"]
                        if "scale" in obj_data:
                            obj.scale = obj_data["scale"]
                        if "hide" in obj_data:
                            obj.hide_set(obj_data["hide"])
            
            logger.info(f"トランザクション '{self.name}' のスナップショットから状態を復元しました")
            return True
            
        except Exception as e:
            logger.error(f"スナップショット復元エラー: {str(e)}")
            return False
    
    def execute(self, create_snapshot: bool = True) -> Dict[str, Any]:
        """トランザクション内のすべてのコマンドを実行"""
        if self.state == "executed":
            return {
                "success": False,
                "message": f"トランザクション '{self.name}' は既に実行されています",
                "transaction_id": self.id
            }
        
        if len(self.commands) == 0:
            return {
                "success": False,
                "message": f"トランザクション '{self.name}' にコマンドがありません",
                "transaction_id": self.id
            }
        
        self.start_time = time.time()
        self.state = "executing"
        success = True
        error_message = None
        
        try:
            # スナップショットを作成（オプション）
            if create_snapshot:
                self.snapshot = self.create_snapshot()
                logger.info(f"トランザクション '{self.name}' の実行前スナップショットを作成しました")
            
            # 各コマンドを実行
            for i, command in enumerate(self.commands):
                cmd_type = command["type"]
                cmd_params = command["params"]
                
                logger.debug(f"コマンド {i+1}/{len(self.commands)} を実行中: {cmd_type}")
                
                # コマンド実行ロジックをここに実装
                # 実装例: 適切なハンドラーを呼び出す
                from .commands.base import execute_command
                
                cmd_data = {
                    "command": cmd_type,
                    **cmd_params
                }
                
                result = execute_command(cmd_data)
                self.results.append(result)
                
                # コマンドが失敗した場合はトランザクションを中止
                if not result.get("success", False):
                    success = False
                    error_message = result.get("message", f"コマンド '{cmd_type}' の実行に失敗しました")
                    logger.error(f"トランザクション '{self.name}' のコマンド {i+1} が失敗しました: {error_message}")
                    break
            
            # 失敗した場合はロールバック
            if not success and create_snapshot and self.snapshot:
                logger.info(f"トランザクション '{self.name}' が失敗したため、スナップショットから復元します")
                self.restore_from_snapshot(self.snapshot)
            
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"トランザクション '{self.name}' の実行中にエラーが発生しました: {error_message}")
            
            # 例外発生時もロールバック
            if create_snapshot and self.snapshot:
                logger.info(f"トランザクション '{self.name}' で例外が発生したため、スナップショットから復元します")
                self.restore_from_snapshot(self.snapshot)
        
        self.end_time = time.time()
        self.state = "executed"
        
        execution_time = (self.end_time - self.start_time) * 1000  # ミリ秒単位
        
        result = {
            "success": success,
            "message": "トランザクションが正常に実行されました" if success else error_message,
            "transaction_id": self.id,
            "transaction_name": self.name,
            "command_count": len(self.commands),
            "executed_commands": len(self.results),
            "execution_time_ms": round(execution_time, 2),
            "results": self.results if success else []
        }
        
        logger.info(f"トランザクション '{self.name}' の実行が完了しました: 成功={success}, 実行時間={round(execution_time, 2)}ms")
        return result

# トランザクション管理用のグローバルレジストリ
_transaction_registry = {}

def create_transaction(name: Optional[str] = None) -> Transaction:
    """新しいトランザクションを作成"""
    transaction = Transaction(name)
    _transaction_registry[transaction.id] = transaction
    return transaction

def get_transaction(transaction_id: str) -> Optional[Transaction]:
    """IDからトランザクションを取得"""
    return _transaction_registry.get(transaction_id)

def delete_transaction(transaction_id: str) -> bool:
    """トランザクションをレジストリから削除"""
    if transaction_id in _transaction_registry:
        del _transaction_registry[transaction_id]
        return True
    return False

def cleanup_old_transactions(max_age_seconds: int = 3600) -> int:
    """古いトランザクションをクリーンアップ"""
    current_time = time.time()
    to_remove = []
    
    for tx_id, transaction in _transaction_registry.items():
        if transaction.end_time and (current_time - transaction.end_time) > max_age_seconds:
            to_remove.append(tx_id)
    
    for tx_id in to_remove:
        delete_transaction(tx_id)
    
    return len(to_remove)