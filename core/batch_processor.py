"""
バッチ処理モジュール
複数のコマンドを効率的にバッチ処理するための機能を提供
"""

import time
import logging
import json
from typing import List, Dict, Any, Optional, Union

# ロギング設定
logger = logging.getLogger('unified_mcp.batch_processor')

class BatchProcessor:
    """
    複数のコマンドを効率的に処理するバッチプロセッサ
    """
    
    def __init__(self):
        """バッチプロセッサを初期化"""
        self.commands = []
        self.results = []
    
    def add_command(self, command_type: str, params: Dict[str, Any]) -> None:
        """コマンドをバッチに追加"""
        self.commands.append({
            "type": command_type,
            "params": params
        })
        
        logger.debug(f"バッチにコマンド '{command_type}' を追加しました")
    
    def process(self) -> Dict[str, Any]:
        """バッチ内のすべてのコマンドを処理"""
        if len(self.commands) == 0:
            return {
                "success": False,
                "message": "バッチにコマンドがありません"
            }
        
        start_time = time.time()
        self.results = []
        
        # 各コマンドを処理
        for i, command in enumerate(self.commands):
            cmd_type = command["type"]
            cmd_params = command["params"]
            
            logger.debug(f"コマンド {i+1}/{len(self.commands)} を処理中: {cmd_type}")
            
            # コマンド実行ロジックをここに実装
            # 適切なハンドラーを呼び出す
            from .commands.base import execute_command
            
            cmd_data = {
                "command": cmd_type,
                **cmd_params
            }
            
            # メインスレッドでの実行や非同期実行はexecute_command内で処理される
            result = execute_command(cmd_data)
            self.results.append({
                "command": cmd_type,
                "result": result
            })
        
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # ミリ秒単位
        
        # すべての結果をまとめる
        successful_commands = sum(1 for r in self.results if r["result"].get("success", False))
        
        result = {
            "success": successful_commands == len(self.commands),
            "message": f"{successful_commands}/{len(self.commands)} コマンドが正常に実行されました",
            "command_count": len(self.commands),
            "successful_commands": successful_commands,
            "execution_time_ms": round(execution_time, 2),
            "results": self.results
        }
        
        logger.info(f"バッチ処理が完了しました: 成功={result['success']}, 実行時間={round(execution_time, 2)}ms")
        return result