"""
Unified MCP コンテキスト認識モジュール
シーンとオブジェクトの状態を分析するコンテキスト機能
"""

import bpy
import logging
from .scene_context import SceneContext
from .object_context import ObjectContext

# ロガー設定
logger = logging.getLogger('unified_mcp.context')

def get_scene_context(detail_level: str = "standard"):
    """シーンコンテキストを取得"""
    try:
        return SceneContext.get_context(detail_level)
    except Exception as e:
        logger.error(f"シーンコンテキスト取得エラー: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return {"error": str(e)}

def get_object_context(object_name: str, detail_level: str = "standard"):
    """特定のオブジェクトコンテキストを取得"""
    try:
        return ObjectContext.get_object_info(object_name, detail_level)
    except Exception as e:
        logger.error(f"オブジェクトコンテキスト取得エラー: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return {"error": str(e)}

def register():
    """コンテキストモジュールを登録"""
    logger.info("コンテキスト認識モジュールを登録しています...")
    logger.info("コンテキスト認識モジュールの登録が完了しました")

def unregister():
    """コンテキストモジュールの登録解除"""
    logger.info("コンテキスト認識モジュールを登録解除しました")