"""
Blender Unified MCP コマンドモジュール
LLMから送信された操作をBlenderで実行するためのコマンドシステム
"""

import logging

# 基本コマンドシステム
from .base import BlenderCommand, register_commands, unregister_commands, get_all_commands
from .registry import get_registry

logger = logging.getLogger('unified_mcp.commands')

def register():
    """コマンドモジュールを登録"""
    logger.info("コマンドモジュールを登録しています...")
    
    # コマンドクラスを登録
    try:
        register_commands()
        logger.info("コマンドクラスを登録しました")
    except Exception as e:
        logger.error(f"コマンドクラスの登録に失敗しました: {str(e)}")
    
    # コマンドレジストリを初期化して登録
    try:
        from .registry import register as register_registry
        register_registry()
        logger.info("コマンドレジストリを登録しました")
    except Exception as e:
        logger.error(f"コマンドレジストリの登録に失敗しました: {str(e)}")
    
    logger.info("コマンドモジュールの登録が完了しました")

def unregister():
    """コマンドモジュールの登録を解除"""
    logger.info("コマンドモジュールの登録を解除しています...")
    
    # コマンドレジストリの登録を解除
    try:
        from .registry import unregister as unregister_registry
        unregister_registry()
        logger.info("コマンドレジストリの登録を解除しました")
    except Exception as e:
        logger.error(f"コマンドレジストリの登録解除に失敗しました: {str(e)}")
    
    # コマンドクラスの登録を解除
    try:
        unregister_commands()
        logger.info("コマンドクラスの登録を解除しました")
    except Exception as e:
        logger.error(f"コマンドクラスの登録解除に失敗しました: {str(e)}")
    
    logger.info("コマンドモジュールの登録解除が完了しました")
