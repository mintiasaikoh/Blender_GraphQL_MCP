"""
Blender Unified MCP オペレータモジュール
"""

import importlib
import logging

# ロギング設定
logger = logging.getLogger(__name__)

# サブモジュールのインポート
try:
    from . import execute_script_secure as execute_script
    logger.info("セキュアなスクリプト実行モジュールを読み込みました")
except ImportError as e:
    from . import execute_script
    logger.warning(f"従来のスクリプト実行モジュールを読み込みました: {str(e)}")

# モジュールのリスト
modules = (
    execute_script,
)

def register():
    """モジュールを登録"""
    for mod in modules:
        mod.register()

def unregister():
    """モジュールの登録を解除"""
    for mod in reversed(modules):
        mod.unregister()

# インポート後に自動的に登録
register()
