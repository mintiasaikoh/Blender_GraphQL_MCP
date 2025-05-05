"""
Blender GraphQL API
GraphQLクエリを処理するAPIモジュール
"""

import logging
import traceback
import sys
import datetime
from typing import Dict, Any, Optional, List, Union

# グラフQLライブラリの有無をチェック
try:
    from graphql import graphql_sync, GraphQLError as GraphQLLibError
    GRAPHQL_AVAILABLE = True
except ImportError as e:
    logger.error(f"GraphQLライブラリのインポートエラー: {e}")
    GRAPHQL_AVAILABLE = False

# Schema依存関係
from . import schema
# エラーハンドリング機能
try:
    from .error_handler import GraphQLError
    ERROR_HANDLER_AVAILABLE = True
except ImportError:
    ERROR_HANDLER_AVAILABLE = False

SCHEMA_LOADED = False

# ロガー設定
logger = logging.getLogger("blender_graphql_mcp.graphql.api")

def register():
    """GraphQLモジュールを登録"""
    global SCHEMA_LOADED
    
    # スキーマ構築を試みる
    if GRAPHQL_AVAILABLE:
        try:
            graphql_schema = schema.build_schema()
            if graphql_schema is not None:
                SCHEMA_LOADED = True
                logger.info("GraphQLスキーマを正常に登録しました")
            else:
                SCHEMA_LOADED = False
                logger.error("GraphQLスキーマの構築に失敗しました")
        except Exception as e:
            SCHEMA_LOADED = False
            logger.error(f"GraphQLスキーマ登録エラー: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    else:
        logger.error("GraphQLライブラリがインストールされていないため、スキーマを登録できません")
        SCHEMA_LOADED = False
        
    return SCHEMA_LOADED

def query_blender(query_string: str, variables: Optional[Dict[str, Any]] = None, operation_name: Optional[str] = None):
    """
    GraphQLクエリを実行
    
    Args:
        query_string: GraphQLクエリ文字列
        variables: クエリ変数（オプション）
        operation_name: 操作名（オプション）
        
    Returns:
        クエリ結果
    """
    # 依存性・スキーマの検証
    if not GRAPHQL_AVAILABLE:
        error_msg = "GraphQLライブラリが利用できません。インストールが必要です。"
        logger.error(error_msg)
        return {
            "errors": [{
                "message": error_msg,
                "extensions": {
                    "code": "GRAPHQL_LIBRARY_MISSING",
                    "classification": "DependencyError"
                }
            }]
        }
    
    if not SCHEMA_LOADED:
        error_msg = "GraphQLスキーマがロードされていません。"
        logger.error(error_msg)
        return {
            "errors": [{
                "message": error_msg,
                "extensions": {
                    "code": "SCHEMA_NOT_LOADED",
                    "classification": "ConfigurationError",
                    "details": {
                        "debug_info": "スキーマの登録を確認してください。register()関数が実行されているか確認してください。"
                    }
                }
            }]
        }
    
    try:
        # クエリログ
        operation_info = f", operation: {operation_name}" if operation_name else ""
        logger.info(f"GraphQLクエリを実行{operation_info}: {query_string[:50]}...")
        if variables:
            logger.debug(f"変数: {variables}")
        
        # スキーマを取得
        graphql_schema = schema.schema
        if graphql_schema is None:
            logger.warning("スキーマがNoneです。再ロードを試みます。")
            graphql_schema = schema.build_schema()
            if graphql_schema is None:
                error_msg = "GraphQLスキーマを構築できませんでした"
                logger.error(error_msg)
                return {
                    "errors": [{
                        "message": error_msg,
                        "extensions": {
                            "code": "SCHEMA_BUILD_FAILED",
                            "classification": "ServerError"
                        }
                    }]
                }
        
        # クエリ実行
        result = graphql_sync(
            graphql_schema,
            query_string,
            variable_values=variables,
            operation_name=operation_name
        )
        
        # 結果を辞書に変換
        serialized_result = {}
        
        # データがあれば追加
        if result.data is not None:
            serialized_result["data"] = result.data
        
        # エラーがあれば拡張エラーフォーマットで追加
        if result.errors:
            # 拡張エラーハンドラーが利用可能な場合
            if ERROR_HANDLER_AVAILABLE:
                serialized_result["errors"] = GraphQLError.format_graphql_errors(result.errors)
            else:
                # 基本形式のエラーメッセージ
                serialized_result["errors"] = [
                    {
                        "message": str(error),
                        "extensions": {
                            "code": "GRAPHQL_ERROR",
                            "classification": "GraphQLError"
                        }
                    } for error in result.errors
                ]
                
            # エラーログ
            for error in result.errors:
                logger.error(f"GraphQLエラー: {error}")
        
        return serialized_result
        
    except Exception as e:
        logger.error(f"GraphQLクエリ実行中に例外が発生: {e}")
        logger.error(traceback.format_exc())
        
        # 拡張エラーハンドラーが利用可能な場合
        if ERROR_HANDLER_AVAILABLE:
            error_data = GraphQLError.format_error(
                e,
                additional_info={
                    "query": query_string[:100] + "..." if len(query_string) > 100 else query_string,
                    "python_version": sys.version,
                    "timestamp": str(datetime.datetime.now()),
                }
            )
            return {"errors": [error_data]}
        else:
            # 基本的なエラーレスポンス
            return {
                "errors": [{
                    "message": f"GraphQLクエリ実行中にエラーが発生しました: {str(e)}",
                    "extensions": {
                        "code": "SERVER_ERROR",
                        "classification": "ServerError",
                        "exception": {
                            "type": e.__class__.__name__
                        }
                    }
                }]
            }