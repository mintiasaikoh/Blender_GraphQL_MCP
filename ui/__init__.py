"""Blender GraphQL MCP UI モジュール
BlenderのインターフェースにGraphQL APIサーバーのパネルとコントロールを追加する

このモジュールは以下の要素を含みます：
- コアUIパネル（サイドバー、設定パネルなど）
- プラグインコンポーネントシステム（プラグインからのUI拡張）
- オペレータとコマンドのトリガー
"""

import bpy
import os
import logging
from bpy.types import Panel, Operator
from .. import core

# ロギング設定
logger = logging.getLogger('blender_graphql_mcp.ui')

# パネルとコンポーネントをインポート
from . import panels
from . import components

# モジュールのクラスを登録
def register():
    """クラスを登録"""
    logger.info("UIモジュールを登録しています...")
    
    # プラグインコンポーネントシステムを登録
    try:
        components.register()
        logger.info("UIコンポーネントシステムを登録しました")
    except Exception as e:
        logger.error(f"UIコンポーネントシステムの登録に失敗しました: {e}")
    
    # コアパネルを登録
    try:
        panels.register()
        logger.info("UIパネルを登録しました")
    except Exception as e:
        logger.error(f"UIパネルの登録に失敗しました: {e}")
    
    logger.info("UIモジュールの登録が完了しました")

# モジュールのクラスを登録解除
def unregister():
    """クラスを登録解除"""
    logger.info("UIモジュールを登録解除しています...")
    
    # コアパネルを登録解除
    try:
        panels.unregister()
        logger.info("UIパネルを登録解除しました")
    except Exception as e:
        logger.error(f"UIパネルの登録解除に失敗しました: {e}")
    
    # プラグインコンポーネントシステムを登録解除
    try:
        components.unregister()
        logger.info("UIコンポーネントシステムを登録解除しました")
    except Exception as e:
        logger.error(f"UIコンポーネントシステムの登録解除に失敗しました: {e}")
    
    logger.info("UIモジュールの登録解除が完了しました")

# モジュールが直接実行された場合
if __name__ == "__main__":
    register()
