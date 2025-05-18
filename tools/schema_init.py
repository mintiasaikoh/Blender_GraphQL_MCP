"""
Blender GraphQL MCP - スキーマ初期化
標準化された改善スキーマの初期化を行う
"""

import logging
import importlib

logger = logging.getLogger("blender_graphql_mcp.tools.schema_init")

def initialize_improved_schema():
    """改善されたスキーマコンポーネントを初期化する"""
    try:
        # 基本コンポーネントのインポート
        import tools.schema_base
        logger.info("基本スキーマコンポーネントを読み込みました")
        
        # 入力型のインポート
        import tools.schema_inputs
        logger.info("入力型コンポーネントを読み込みました")
        
        # エラー処理コンポーネントのインポート
        import tools.schema_error
        logger.info("エラー処理コンポーネントを読み込みました")
        
        # 命名規則コンポーネントのインポート
        import tools.schema_naming
        logger.info("命名規則コンポーネントを読み込みました")
        
        # 改善されたMCPスキーマのインポート
        import tools.schema_improved_mcp
        logger.info("改善されたMCPスキーマを読み込みました")
        
        # スキーマレジストリからスキーマを取得
        from tools.schema_registry import schema_registry
        schema = schema_registry.build_schema()
        
        logger.info(f"改善されたスキーマの初期化が完了しました")
        logger.info(f"登録された型: {len(schema_registry.types)}")
        logger.info(f"登録されたクエリ: {len(schema_registry.query_fields)}")
        logger.info(f"登録されたミューテーション: {len(schema_registry.mutation_fields)}")
        
        return schema
    
    except ImportError as e:
        logger.error(f"スキーマコンポーネントのインポートエラー: {e}")
        return None
    except Exception as e:
        logger.error(f"スキーマ初期化エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def reload_schema_components():
    """スキーマコンポーネントをリロードする"""
    try:
        modules = [
            "tools.schema_base",
            "tools.schema_inputs",
            "tools.schema_error",
            "tools.schema_naming",
            "tools.schema_improved_mcp",
            "tools.schema_registry"
        ]
        
        for module_name in modules:
            if module_name in globals():
                importlib.reload(globals()[module_name])
                logger.info(f"モジュール {module_name} をリロードしました")
        
        return True
    except Exception as e:
        logger.error(f"スキーマコンポーネントのリロードエラー: {e}")
        return False

# 初期化時に自動的にスキーマを読み込む
improved_schema = initialize_improved_schema()