"""
GraphQL APIモードユーティリティ

GraphQL専用モードでの動作をサポートするヘルパー機能
"""

import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("blender_graphql_mcp.core.api_mode_utils")

# GraphQL専用モード定数
MODE_GRAPHQL_ONLY = "graphql_only"  # GraphQLのみ

def get_api_mode() -> Tuple[str, bool]:
    """
    現在のAPIモードを取得する - 常にGraphQL専用モードを返す
    
    Returns:
        Tuple[str, bool]: (モード名, GraphQL優先フラグ)
    """
    # GraphQL専用モードのみをサポート
    return MODE_GRAPHQL_ONLY, True

def get_api_mode_message(api_mode: str = None) -> str:
    """
    GraphQL APIモードのメッセージを返す
    
    Returns:
        str: ユーザー向けメッセージ
    """
    return "GraphQL APIのみがサポートされています。/graphqlエンドポイントを使用してください。"

def get_api_mode_info() -> Dict[str, Any]:
    """
    GraphQL APIモード設定の情報を取得
    
    Returns:
        Dict[str, Any]: APIモード情報を含む辞書
    """
    # GraphQL専用モードのみをサポート
    return {
        "current_mode": MODE_GRAPHQL_ONLY,
        "description": "GraphQL APIのみをサポート",
        "graphql_only": True,
        "prefer_graphql": True
    }
