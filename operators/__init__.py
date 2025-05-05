"""
Blender Unified MCP オペレータモジュール
"""

import importlib

# サブモジュールのインポート
from . import execute_script

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
