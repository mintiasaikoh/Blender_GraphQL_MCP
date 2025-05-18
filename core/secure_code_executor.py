"""
安全なコード実行モジュール
"""

import bpy
import json
import logging
from typing import Dict, Any

# ロギング設定
logger = logging.getLogger(__name__)

# 安全なスクリプト実行システムのインポート
try:
    from .utils.safe_script_executor import SafeScriptExecutor
    SAFE_EXECUTOR_LOADED = True
except ImportError as e:
    SAFE_EXECUTOR_LOADED = False
    logger.warning(f"安全なスクリプト実行システムをロードできませんでした: {str(e)}")

def execute_code_safely(code: str, script_name: str = "<inline_code>") -> Dict[str, Any]:
    """
    Pythonコードを安全に実行
    
    Args:
        code: 実行するPythonコード
        script_name: スクリプト名（エラー表示用）
        
    Returns:
        Dict: 実行結果
    """
    if not SAFE_EXECUTOR_LOADED:
        return {
            "success": False,
            "error": "Safe script executor is not available",
            "details": {
                "message": "安全なスクリプト実行システムがロードされていません"
            }
        }
    
    # 安全なスクリプト実行システムを初期化
    executor = SafeScriptExecutor(max_execution_time=5.0)
    
    # コードを安全に実行
    result = executor.execute_script(code, script_name)
    
    # JSON互換性を確保
    if result["success"] and "result" in result["details"]:
        result_value = result["details"]["result"]
        
        # JSON変換可能かチェック
        if result_value is not None:
            try:
                # 結果のJSON変換テスト
                json.dumps(result_value)
                result["details"]["result_json_compatible"] = True
            except (TypeError, OverflowError):
                result["details"]["result_json_compatible"] = False
                result["details"]["result"] = str(result_value)
        else:
            result["details"]["result_json_compatible"] = True
    
    return result

def handle_execute_code_command_secure(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pythonコード実行コマンドを安全に処理
    
    Args:
        data: コマンドデータ
            {
                "command": "execute_code",
                "code": "実行するPythonコード"
            }
            または
            {
                "command": "execute_code",
                "params": {
                    "code": "実行するPythonコード"
                }
            }
        
    Returns:
        Dict: 実行結果
    """
    # パラメータ取得（新旧形式に対応）
    if "params" in data and isinstance(data["params"], dict):
        code = data["params"].get("code")
    else:
        code = data.get("code")
    
    if not code:
        return {
            "success": False,
            "error": "Missing 'code' parameter for execute_code command",
            "details": {
                "required_parameters": ["code"]
            }
        }
    
    # 安全なコード実行を実行
    return execute_code_safely(code)