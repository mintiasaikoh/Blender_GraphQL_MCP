"""
GraphQLエラー処理ユーティリティ
"""

import logging
import traceback
import time
from typing import Dict, Any, List, Union, Optional

logger = logging.getLogger("blender_graphql_mcp.tools.error_utils")

def format_error_for_response(
    error: Exception,
    path: Optional[List[str]] = None,
    extensions: Optional[Dict[str, Any]] = None,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    GraphQLエラーレスポンス用にエラーをフォーマット
    
    Args:
        error: 例外オブジェクト
        path: エラーが発生したGraphQLクエリのパス
        extensions: 追加のエラーコンテキスト情報
        include_traceback: デバッグモードの場合、トレースバックを含めるか
        
    Returns:
        GraphQL形式のエラーオブジェクト
    """
    # 基本的なエラー情報
    error_obj = {
        "message": str(error),
        "extensions": {
            "code": error.__class__.__name__.upper(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    # パスが提供されている場合は追加
    if path:
        error_obj["path"] = path
    
    # 追加の拡張情報がある場合はマージ
    if extensions:
        error_obj["extensions"].update(extensions)
    
    # デバッグモードの場合はトレースバックを含める
    if include_traceback:
        error_obj["extensions"]["exception"] = {
            "type": error.__class__.__name__,
            "stacktrace": traceback.format_exc().split('\n')
        }
    
    # ログに記録
    log_message = f"GraphQLエラー: {error}"
    if path:
        log_message += f" (パス: {'.'.join(path)})"
    
    logger.error(log_message)
    if include_traceback:
        logger.debug(traceback.format_exc())
    
    return error_obj

def format_graphql_errors(
    errors: List[Exception],
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    GraphQLエラーのリストを標準レスポンス形式にフォーマット
    
    Args:
        errors: 例外オブジェクトのリスト
        include_traceback: デバッグモードの場合、トレースバックを含めるか
        
    Returns:
        GraphQL標準エラーレスポンス
    """
    formatted_errors = [
        format_error_for_response(error, include_traceback=include_traceback)
        for error in errors
    ]
    
    return {
        "errors": formatted_errors
    }

def graphql_exception_handler(func):
    """
    GraphQL操作のための例外ハンドラデコレータ
    
    関数の例外をキャッチし、適切にフォーマットされたGraphQLエラーレスポンスを返す
    
    Returns:
        装飾された関数
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"GraphQL操作エラー: {e}")
            logger.debug(traceback.format_exc())
            
            # GraphQLエラーレスポンスを返す
            return {
                "errors": [
                    format_error_for_response(
                        e, 
                        extensions={"context": "operation_execution"},
                        include_traceback=True
                    )
                ]
            }
    
    return wrapper