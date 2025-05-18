"""
GraphQL Error Handler
GraphQLエラーの拡張処理とフォーマット機能を提供します
"""

import logging
import traceback
import json
from typing import Dict, Any, List, Optional

# ロガー初期化 - 名前空間を統一
logger = logging.getLogger("blender_graphql_mcp.tools.error_handler")

class GraphQLError:
    """拡張GraphQLエラーハンドラー"""
    
    @staticmethod
    def format_error(error: Exception, path: Optional[List[str]] = None, additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        例外をGraphQL標準エラーフォーマットに変換
        
        Args:
            error: 元の例外
            path: エラーが発生したGraphQLクエリのパス
            additional_info: 追加のデバッグ情報
            
        Returns:
            GraphQL標準形式のエラー辞書
        """
        error_message = str(error)
        
        # エラーをログに記録
        logger.error(f"GraphQLエラー発生: {error_message}")
        logger.debug(traceback.format_exc())
        
        # 基本エラー情報
        error_response = {
            "message": error_message
        }
        
        # エラーが発生したパスがあれば追加
        if path:
            error_response["path"] = path
        
        # エラーの詳細情報を追加
        error_details = {}
        
        # 例外型の情報
        error_details["type"] = error.__class__.__name__
        
        # スタックトレース（デバッグモードのみ）
        error_details["stacktrace"] = traceback.format_exc().split("\n")
        
        # 追加情報があれば追加
        if additional_info:
            error_details.update(additional_info)
        
        # 拡張情報を追加
        error_response["extensions"] = {
            "code": "BLENDER_GRAPHQL_ERROR",
            "details": error_details
        }
        
        return error_response
    
    @staticmethod
    def format_graphql_errors(errors: List[Any]) -> List[Dict[str, Any]]:
        """
        GraphQLライブラリから返されたエラーリストを整形
        
        Args:
            errors: GraphQL実行時に発生したエラーリスト
            
        Returns:
            整形されたエラーリスト
        """
        formatted_errors = []
        
        for error in errors:
            # 基本メッセージの取得
            error_message = str(error)
            
            # エラーをログに記録
            logger.error(f"GraphQLエラー: {error_message}")
            
            # エラー情報を構築
            formatted_error = {"message": error_message}
            
            # パスとロケーション情報があれば追加
            if hasattr(error, "path") and error.path:
                formatted_error["path"] = error.path
            
            if hasattr(error, "locations") and error.locations:
                formatted_error["locations"] = [
                    {"line": loc.line, "column": loc.column}
                    for loc in error.locations
                ]
            
            # エラー拡張情報を追加
            formatted_error["extensions"] = {
                "code": "GRAPHQL_VALIDATION_ERROR",
                "classification": "GraphQLError"
            }
            
            formatted_errors.append(formatted_error)
        
        return formatted_errors