"""
Blender GraphQL MCP - スキーマビルダー
新しい体系的なスキーマ構築機能を提供
"""

import logging
from tools import GraphQLSchema
from typing import Optional

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_builder")

# レジストリのインポート
from .schema_registry import schema_registry

def build_schema() -> Optional[GraphQLSchema]:
    """
    新しい方法でGraphQLスキーマを構築
    
    Returns:
        構築されたGraphQLスキーマ（エラー時はNone）
    """
    try:
        # 各モジュールのスキーマ登録関数をインポート
        from .schema_types import register_base_types
        from .schema_mesh import register_mesh_schema
        from .schema_boolean import register_boolean_schema
        from .schema_llm_discovery import register_llm_discovery_schema
        
        # 基本型の登録
        register_base_types()
        logger.info("基本型定義を登録しました")
        
        # 各ドメイン別スキーマの登録
        register_mesh_schema()
        logger.info("メッシュスキーマを登録しました")
        
        register_boolean_schema()
        logger.info("ブーリアンスキーマを登録しました")
        
        # LLM向け機能発見スキーマの登録
        register_llm_discovery_schema()
        logger.info("LLM向け機能発見スキーマを登録しました")
        
        # 最終的なスキーマ構築
        schema = schema_registry.build_schema()
        logger.info("GraphQLスキーマ構築完了")
        
        return schema
        
    except Exception as e:
        logger.error(f"スキーマ構築中にエラーが発生しました: {e}", exc_info=True)
        return None
