"""
Blender GraphQL MCP - スキーマ統一モジュール
既存のスキーマを新しいスキーマ構造に完全統合
"""

import logging
import importlib
from typing import Dict, Any, Optional, List, Union
from tools import GraphQLSchema

# スキーマ検証モジュールをインポート
try:
    from . import schema_validation
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_unification")

def unify_schema() -> Optional[GraphQLSchema]:
    """
    既存システムを新しいスキーマ構造に完全統合
    古いスキーマ構造を使用せず、完全に新スキーマで再構築
    
    Returns:
        統一されたGraphQLスキーマ（エラー時はNone）
    """
    try:
        # 新しい構造でスキーマ構築
        from .schema_builder import build_schema as build_new_schema
        from .schema_registry import schema_registry
        
        # リゾルバモジュールのインポート
        resolver_modules = [
            'graphql.resolver',
            'graphql.resolver_compatibility'
        ]
        
        # 使用可能なリゾルバモジュールを検出
        resolver_module = None
        for module_name in resolver_modules:
            try:
                resolver_module = importlib.import_module(module_name)
                logger.info(f"リゾルバモジュールを読み込みました: {module_name}")
                break
            except ImportError:
                continue
        
        if not resolver_module:
            logger.error("リゾルバモジュールをロードできませんでした")
            return None
        
        # グローバル変数としてリゾルバモジュールを設定
        import sys
        sys.modules['RESOLVER_MODULE'] = resolver_module
        
        # スキーマを構築
        schema = build_new_schema()
        
        if schema:
            # 整合性チェックを実行
            if VALIDATION_AVAILABLE:
                try:
                    validation_result = schema_validation.validate_schema(schema)
                    
                    if validation_result["valid"]:
                        logger.info("スキーマの整合性が確認されました")
                    else:
                        # 問題があってもスキーマは使用するが、ログに問題を記録
                        if validation_result.get("missing_resolvers"):
                            logger.warning(f"欠落しているリゾルバ: {', '.join(validation_result['missing_resolvers'])}")
                        
                        if validation_result.get("naming_issues"):
                            logger.warning(f"命名規則の問題: {', '.join(validation_result['naming_issues'][:5])}{'...' if len(validation_result['naming_issues']) > 5 else ''}")
                        
                        if validation_result.get("type_issues"):
                            logger.warning(f"型定義の問題: {', '.join(validation_result['type_issues'][:5])}{'...' if len(validation_result['type_issues']) > 5 else ''}")
                        
                        if validation_result.get("potential_duplicates"):
                            logger.warning(f"潜在的な重複: {', '.join(validation_result['potential_duplicates'][:5])}{'...' if len(validation_result['potential_duplicates']) > 5 else ''}")
                except Exception as e:
                    logger.error(f"スキーマ検証中にエラーが発生しました: {e}")
            
            logger.info("統合されたスキーマ構造の構築に成功しました")
            return schema
        else:
            logger.error("統合されたスキーマの構築に失敗しました")
            return None
    
    except Exception as e:
        logger.error(f"スキーマ統合中にエラーが発生しました: {e}", exc_info=True)
        return None
