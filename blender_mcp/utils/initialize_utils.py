"""
Blender Unified MCP Utilities Initialization
ユーティリティモジュールの初期化と登録を行う
"""

import bpy
import logging
import os
import sys
from typing import List, Dict, Any, Optional

# モジュールレベルのロガー
logger = logging.getLogger('unified_mcp.utils.initializer')

# ユーティリティモジュールリスト
UTILITY_MODULES = [
    "fileutils",
    "ui_error_handler",
    "async_file_handler",
    "demo_utils"  # デモモジュールも含む
]

# モジュールの状態を追跡
module_status = {}

def initialize_utils():
    """すべてのユーティリティモジュールを初期化"""
    # モジュールインポート
    modules = import_utility_modules()
    
    # モジュール登録
    register_utility_modules(modules)
    
    return modules

def import_utility_modules():
    """ユーティリティモジュールをインポート"""
    modules = {}
    
    for module_name in UTILITY_MODULES:
        try:
            # 完全修飾名でインポート
            full_name = f"Blender_GraphQL_MCP.utils.{module_name}"
            
            # すでにインポート済みならそれを使用
            if full_name in sys.modules:
                module = sys.modules[full_name]
            else:
                # 相対インポートで試行
                module_path = f".{module_name}"
                module = __import__(module_path, globals(), locals(), [''], level=1)
            
            # モジュールを記録
            modules[module_name] = module
            module_status[module_name] = "imported"
            logger.info(f"ユーティリティモジュールをインポート: {module_name}")
            
        except ImportError as e:
            logger.error(f"ユーティリティモジュールのインポートに失敗: {module_name}: {e}")
            module_status[module_name] = f"import_failed: {str(e)}"
    
    return modules

def register_utility_modules(modules: Dict[str, Any]):
    """インポートされたモジュールを登録"""
    # 優先順位を設定: 基本的なユーティリティが先、依存するものは後
    priority_order = [
        "fileutils",       # 最初に登録（他が依存）
        "ui_error_handler", # 2番目（fileutils依存）
        "async_file_handler", # 3番目（fileutils依存）
        "demo_utils"        # 最後（すべてに依存）
    ]
    
    # 優先順位に従って登録
    for module_name in priority_order:
        if module_name in modules:
            module = modules[module_name]
            try:
                # register関数があれば呼び出し
                if hasattr(module, 'register'):
                    module.register()
                    module_status[module_name] = "registered"
                    logger.info(f"ユーティリティモジュールを登録: {module_name}")
                else:
                    module_status[module_name] = "no_register_function"
                    logger.warning(f"モジュールに登録関数がありません: {module_name}")
            except Exception as e:
                module_status[module_name] = f"register_failed: {str(e)}"
                logger.error(f"ユーティリティモジュールの登録に失敗: {module_name}: {e}")
    
    return True

def unregister_utility_modules():
    """登録済みユーティリティモジュールの登録を解除"""
    # 逆順に登録解除
    for module_name in reversed(UTILITY_MODULES):
        full_name = f"Blender_GraphQL_MCP.utils.{module_name}"
        
        if full_name in sys.modules:
            module = sys.modules[full_name]
            try:
                # unregister関数があれば呼び出し
                if hasattr(module, 'unregister'):
                    module.unregister()
                    module_status[module_name] = "unregistered"
                    logger.info(f"ユーティリティモジュールの登録を解除: {module_name}")
                else:
                    module_status[module_name] = "no_unregister_function"
            except Exception as e:
                module_status[module_name] = f"unregister_failed: {str(e)}"
                logger.error(f"ユーティリティモジュールの登録解除に失敗: {module_name}: {e}")
    
    return True

def get_module_status():
    """モジュールの状態を返す"""
    return module_status.copy()

def register():
    """初期化モジュールの登録"""
    # ユーティリティモジュールを初期化
    initialize_utils()
    logger.info("ユーティリティ初期化モジュールを登録しました")

def unregister():
    """初期化モジュールの登録解除"""
    # ユーティリティモジュールの登録を解除
    unregister_utility_modules()
    logger.info("ユーティリティ初期化モジュールの登録を解除しました")

# アドオン初期化時に登録
if __name__ == "__main__":
    register()