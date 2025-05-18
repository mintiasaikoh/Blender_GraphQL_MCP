"""
Blender GraphQL MCP - スキーマ移行モジュール
既存システムから新構造への移行をサポート
"""

import logging
from typing import Optional
from tools import GraphQLSchema

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_migration")

def migrate_schema(original_schema: Optional[GraphQLSchema] = None) -> Optional[GraphQLSchema]:
    """
    既存のスキーマから新しいスキーマ構造への移行
    
    Args:
        original_schema: 既存のスキーマ（Noneの場合は新しいスキーマのみを構築）
        
    Returns:
        移行されたスキーマ（エラー時はNone）
    """
    try:
        from .schema_builder import build_schema as build_new_schema
        
        # 新しいスキーマビルダーを使用
        new_schema = build_new_schema()
        
        if new_schema:
            logger.info("新しいスキーマ構造に移行しました")
            return new_schema
        else:
            logger.warning("新しいスキーマ構築に失敗しました")
            # 元のスキーマがあれば返す
            return original_schema
            
    except Exception as e:
        logger.error(f"スキーマ移行中にエラーが発生しました: {e}", exc_info=True)
        # エラー発生時は元のスキーマを返す
        return original_schema
