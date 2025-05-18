"""
Blender GraphQL MCP - エラー処理
標準化されたエラー処理システム
"""

import logging
import time
import traceback
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, TypeVar, Generic, Union, Tuple

# スキーマベースのインポート
from tools.schema_base import (
    create_error,
    create_error_result,
    create_success_result
)

logger = logging.getLogger("blender_graphql_mcp.tools.schema_error")

# エラーコード定義
class ErrorCode:
    # 入力検証エラー
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_VALUE = "INVALID_VALUE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # リソース関連エラー
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
    MATERIAL_NOT_FOUND = "MATERIAL_NOT_FOUND"
    SCENE_NOT_FOUND = "SCENE_NOT_FOUND"
    MODIFIER_NOT_FOUND = "MODIFIER_NOT_FOUND"
    
    # 操作関連エラー
    OPERATION_FAILED = "OPERATION_FAILED"
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    OPERATION_UNSUPPORTED = "OPERATION_UNSUPPORTED"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    
    # システムエラー
    SYSTEM_ERROR = "SYSTEM_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    
    # 権限・認証エラー
    PERMISSION_DENIED = "PERMISSION_DENIED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    
    # MCP特有エラー
    COMMAND_EXECUTION_FAILED = "COMMAND_EXECUTION_FAILED"
    CODE_VALIDATION_FAILED = "CODE_VALIDATION_FAILED"
    DANGEROUS_OPERATION = "DANGEROUS_OPERATION"

# エラーカテゴリ定義
class ErrorCategory:
    USER_INPUT = "USER_INPUT"
    PERMISSION = "PERMISSION"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    SYSTEM = "SYSTEM"
    OPERATION_FAILED = "OPERATION_FAILED"

# 一般的なエラーメッセージのテンプレート
ERROR_MESSAGES = {
    ErrorCode.INVALID_INPUT: "無効な入力パラメータです",
    ErrorCode.MISSING_FIELD: "必須フィールドが不足しています",
    ErrorCode.INVALID_VALUE: "無効な値が指定されています",
    ErrorCode.VALIDATION_ERROR: "入力値の検証に失敗しました",
    
    ErrorCode.RESOURCE_NOT_FOUND: "リソースが見つかりません",
    ErrorCode.OBJECT_NOT_FOUND: "指定されたオブジェクトが見つかりません",
    ErrorCode.MATERIAL_NOT_FOUND: "指定されたマテリアルが見つかりません",
    ErrorCode.SCENE_NOT_FOUND: "指定されたシーンが見つかりません",
    
    ErrorCode.OPERATION_FAILED: "操作に失敗しました",
    ErrorCode.OPERATION_TIMEOUT: "操作がタイムアウトしました",
    ErrorCode.OPERATION_UNSUPPORTED: "この操作はサポートされていません",
    
    ErrorCode.SYSTEM_ERROR: "システムエラーが発生しました",
    ErrorCode.INTERNAL_SERVER_ERROR: "内部サーバーエラーが発生しました",
    
    ErrorCode.COMMAND_EXECUTION_FAILED: "コマンドの実行に失敗しました",
    ErrorCode.CODE_VALIDATION_FAILED: "コードの検証に失敗しました",
    ErrorCode.DANGEROUS_OPERATION: "危険な操作が検出されました"
}

# エラーコードとカテゴリのマッピング
ERROR_CATEGORIES = {
    ErrorCode.INVALID_INPUT: ErrorCategory.USER_INPUT,
    ErrorCode.MISSING_FIELD: ErrorCategory.USER_INPUT,
    ErrorCode.INVALID_VALUE: ErrorCategory.USER_INPUT,
    ErrorCode.VALIDATION_ERROR: ErrorCategory.USER_INPUT,
    
    ErrorCode.RESOURCE_NOT_FOUND: ErrorCategory.RESOURCE_NOT_FOUND,
    ErrorCode.OBJECT_NOT_FOUND: ErrorCategory.RESOURCE_NOT_FOUND,
    ErrorCode.MATERIAL_NOT_FOUND: ErrorCategory.RESOURCE_NOT_FOUND,
    ErrorCode.SCENE_NOT_FOUND: ErrorCategory.RESOURCE_NOT_FOUND,
    
    ErrorCode.OPERATION_FAILED: ErrorCategory.OPERATION_FAILED,
    ErrorCode.OPERATION_TIMEOUT: ErrorCategory.OPERATION_FAILED,
    ErrorCode.OPERATION_UNSUPPORTED: ErrorCategory.OPERATION_FAILED,
    ErrorCode.EXECUTION_ERROR: ErrorCategory.OPERATION_FAILED,
    
    ErrorCode.SYSTEM_ERROR: ErrorCategory.SYSTEM,
    ErrorCode.INTERNAL_SERVER_ERROR: ErrorCategory.SYSTEM,
    ErrorCode.UNEXPECTED_ERROR: ErrorCategory.SYSTEM,
    
    ErrorCode.PERMISSION_DENIED: ErrorCategory.PERMISSION,
    ErrorCode.AUTHENTICATION_FAILED: ErrorCategory.PERMISSION,
    
    ErrorCode.COMMAND_EXECUTION_FAILED: ErrorCategory.OPERATION_FAILED,
    ErrorCode.CODE_VALIDATION_FAILED: ErrorCategory.USER_INPUT,
    ErrorCode.DANGEROUS_OPERATION: ErrorCategory.PERMISSION
}

# 特定エラーコードに対する解決提案
ERROR_SUGGESTIONS = {
    ErrorCode.OBJECT_NOT_FOUND: [
        "正確なオブジェクト名を指定してください",
        "先にオブジェクトを作成してください",
        "scene.objectsでオブジェクト一覧を確認してください"
    ],
    ErrorCode.MATERIAL_NOT_FOUND: [
        "正確なマテリアル名を指定してください",
        "先にマテリアルを作成してください"
    ],
    ErrorCode.OPERATION_TIMEOUT: [
        "操作を簡略化してください",
        "複雑な処理は複数のステップに分けてください"
    ],
    ErrorCode.CODE_VALIDATION_FAILED: [
        "コードに潜在的な問題があります",
        "安全なBlender API関数のみを使用してください"
    ]
}

def get_default_error_message(code: str) -> str:
    """エラーコードからデフォルトのエラーメッセージを取得

    Args:
        code: エラーコード

    Returns:
        デフォルトのエラーメッセージ
    """
    return ERROR_MESSAGES.get(code, "未知のエラーが発生しました")

def get_error_category(code: str) -> str:
    """エラーコードからカテゴリを取得

    Args:
        code: エラーコード

    Returns:
        エラーカテゴリ
    """
    return ERROR_CATEGORIES.get(code, ErrorCategory.SYSTEM)

def get_error_suggestions(code: str) -> List[str]:
    """エラーコードから解決提案を取得

    Args:
        code: エラーコード

    Returns:
        解決提案のリスト
    """
    return ERROR_SUGGESTIONS.get(code, [])

def create_standard_error(
    code: str,
    message: Optional[str] = None,
    details: Optional[str] = None,
    path: Optional[List[str]] = None
) -> Dict[str, Any]:
    """標準化されたエラーオブジェクトを生成

    Args:
        code: エラーコード
        message: エラーメッセージ（省略時はデフォルトメッセージ）
        details: エラーの詳細情報
        path: エラーが発生した場所のパス

    Returns:
        エラーオブジェクト
    """
    # メッセージが指定されていない場合はデフォルトを使用
    if message is None:
        message = get_default_error_message(code)
    
    # カテゴリを取得
    category = get_error_category(code)
    
    # 解決提案を取得
    suggestions = get_error_suggestions(code)
    
    # エラーオブジェクトを作成
    return create_error(
        code=code,
        message=message,
        category=category,
        details=details,
        path=path,
        suggestions=suggestions
    )

def create_standard_error_result(
    code: str,
    message: Optional[str] = None,
    details: Optional[str] = None,
    path: Optional[List[str]] = None,
    execution_time_ms: Optional[float] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """標準化されたエラー結果を生成

    Args:
        code: エラーコード
        message: エラーメッセージ（省略時はデフォルトメッセージ）
        details: エラーの詳細情報
        path: エラーが発生した場所のパス
        execution_time_ms: 実行時間（ミリ秒）
        additional_data: 追加データ

    Returns:
        エラー結果オブジェクト
    """
    # メッセージが指定されていない場合はデフォルトを使用
    if message is None:
        message = get_default_error_message(code)
    
    # カテゴリとメッセージを取得
    category = get_error_category(code)
    suggestions = get_error_suggestions(code)
    
    # エラー結果を作成
    return create_error_result(
        code=code,
        message=message,
        category=category,
        details=details,
        path=path,
        suggestions=suggestions,
        execution_time_ms=execution_time_ms,
        additional_data=additional_data
    )

# 型変数の定義
T = TypeVar('T')

def with_error_handling(
    func: Callable[..., T],
    error_message: str = "操作の実行中にエラーが発生しました",
    log_errors: bool = True
) -> Callable[..., Dict[str, Any]]:
    """関数をエラーハンドリングで装飾するデコレータ

    Args:
        func: 対象の関数
        error_message: エラー時の基本メッセージ
        log_errors: エラーをログに記録するかどうか

    Returns:
        装飾された関数
    """
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            # 関数を実行
            result = func(*args, **kwargs)
            
            # 実行時間の計算
            execution_time_ms = (time.time() - start_time) * 1000
            
            # 結果が辞書でない場合は成功結果として包む
            if not isinstance(result, dict):
                return create_success_result(
                    message="操作が成功しました",
                    execution_time_ms=execution_time_ms,
                    additional_data={"result": result}
                )
            
            # すでに辞書の場合は実行時間を追加して返す
            if "executionTimeMs" not in result:
                result["executionTimeMs"] = execution_time_ms
                
            return result
            
        except Exception as e:
            # 実行時間の計算
            execution_time_ms = (time.time() - start_time) * 1000
            
            # エラー情報の取得
            error_type = type(e).__name__
            error_detail = str(e)
            stack_trace = traceback.format_exc()
            
            # ログ出力
            if log_errors:
                logger.error(f"{error_message}: {error_type} - {error_detail}")
                logger.debug(f"スタックトレース: {stack_trace}")
            
            # エラー結果の生成
            return create_standard_error_result(
                code=ErrorCode.OPERATION_FAILED,
                message=f"{error_message}: {error_detail}",
                details=stack_trace,
                execution_time_ms=execution_time_ms
            )
    
    return wrapper