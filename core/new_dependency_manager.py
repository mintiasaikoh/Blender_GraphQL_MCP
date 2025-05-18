"""
依存関係管理モジュール
Blender 4.2以降のExtensionsシステムを使用した依存関係管理を提供します
"""

import os
import sys
import importlib
import logging
import traceback
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("blender_graphql_mcp.dependency_manager")

def get_extension_toml_path():
    """extension.tomlファイルの絶対パスを取得します
    
    Returns:
        str: extension.tomlファイルの絶対パス
    """
    import os
    addon_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(addon_path, "extension.toml")

def ensure_extension_toml_exists() -> bool:
    """extension.tomlファイルが存在することを確認し、なければ作成します
    
    Returns:
        bool: ファイルが存在するか作成されたらTrue
    """
    extension_toml_path = get_extension_toml_path()
    
    if os.path.exists(extension_toml_path):
        logger.info(f"extension.tomlファイルが見つかりました: {extension_toml_path}")
        return True
    
    # ファイルが存在しない場合は作成
    logger.info(f"extension.tomlファイルが見つかりません。作成します: {extension_toml_path}")
    try:
        with open(extension_toml_path, 'w') as f:
            f.write("""\
[extension]
id = "blender_graphql_mcp"
version = "1.0.0"
name = "Blender GraphQL MCP"
tagline = "GraphQL APIでBlenderを操作"
maintainer = "Blender GraphQL MCP Team"
license = "GPL-3.0"
blender_version_min = "4.2.0"

[requirements]
pip = [
    "fastapi>=0.95.0",
    "uvicorn>=0.21.1",
    "pydantic>=1.10.7",
    "graphql-core>=3.2.3",
    "numpy>=1.22.0",
    "pandas>=1.4.0"
]
""")
        logger.info(f"extension.tomlファイルを作成しました: {extension_toml_path}")
        return True
    except Exception as e:
        logger.error(f"extension.tomlファイルの作成に失敗しました: {e}")
        logger.error(traceback.format_exc())
        return False

def check_dependencies() -> Tuple[bool, List[str]]:
    """依存関係が正しくインストールされているか確認します
    
    Returns:
        Tuple[bool, List[str]]: (全ての依存関係が揃っているか, 不足している依存関係のリスト)
    """
    required_modules = ["fastapi", "uvicorn", "pydantic", "graphql_core", "numpy", "pandas"]
    missing_modules = []
    
    for module_name in required_modules:
        try:
            module = importlib.import_module(module_name.replace('-', '_'))
            logger.info(f"モジュール {module_name} は正常にインポートされました")

            # バージョンチェック（可能な場合）
            if hasattr(module, '__version__'):
                current_version = module.__version__
                logger.info(f"モジュール {module_name} のバージョン: {current_version}")
        except ImportError:
            logger.warning(f"モジュール {module_name} が見つかりません")
            missing_modules.append(module_name)
    
    return len(missing_modules) == 0, missing_modules

def install_dependencies_via_extensions_system() -> bool:
    """Blender Extensionsシステムを使用して依存関係をインストールします

    Returns:
        bool: インストールに成功したらTrue
    """
    # extension.tomlファイルの存在を確認
    if not ensure_extension_toml_exists():
        logger.warning("extension.tomlファイルの確認に失敗しました")
        return False

    # 依存関係を確認して、不足しているものがなければ成功
    all_dependencies_installed, missing_modules = check_dependencies()
    if all_dependencies_installed:
        logger.info("すべての依存関係が既にインストールされています")
        return True

    # Blender Extensions APIを使用する実装
    try:
        import bpy

        # ユーザーに確認を求めるメッセージ表示（バックグラウンドモードでなければ）
        if not bpy.app.background:
            missing_modules_str = ", ".join(missing_modules)
            message = f"必要な依存ライブラリ ({missing_modules_str}) をインストールする必要があります。インストールしますか？"

            def show_message_box(message, title="依存関係インストール", icon='INFO'):
                def draw(self, context):
                    self.layout.label(text=message)
                bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

            show_message_box(message)

            # Blender 4.2+のExtensions APIを使用して依存関係をインストール
            extension_toml_path = get_extension_toml_path()
            logger.info(f"Extensions APIを使用して依存関係をインストールします: {extension_toml_path}")

            # 拡張機能の管理操作をAtomicに実行
            installation_success = False

            if hasattr(bpy.ops.preferences, "extension_install"):
                # Blender 4.2+のExtensions APIでインストール
                try:
                    result = bpy.ops.preferences.extension_install(filepath=extension_toml_path)
                    if result == {'FINISHED'}:
                        logger.info("拡張機能のインストールに成功しました")
                        installation_success = True
                    else:
                        logger.warning(f"拡張機能のインストールが完了しましたが、結果: {result}")
                except Exception as install_error:
                    logger.error(f"拡張機能のインストール中にエラーが発生: {install_error}")
            else:
                # このケースは起こり得ない（Blender 4.2以降のみサポートのため）
                logger.error("Blender拡張機能APIが見つかりません。(これは起こり得ません)")
                return False

            # インストール後に、再度依存関係をチェック
            importlib.invalidate_caches()  # キャッシュをリセット
            all_dependencies_installed, missing_modules = check_dependencies()

            if all_dependencies_installed:
                logger.info("すべての依存関係のインストールに成功しました")
                return True
            else:
                logger.warning(f"依存関係のインストールを試みましたが、まだ不足しているものがあります: {missing_modules}")
                return installation_success  # インストールプロセスが成功したかどうかを返す
        else:
            logger.warning("バックグラウンドモードでは依存関係のインストールを確認できません")
            return False

    except Exception as e:
        logger.error(f"Extensions APIを使用した依存関係のインストールに失敗しました: {e}")
        logger.error(traceback.format_exc())
        return False

def ensure_dependencies() -> bool:
    """依存関係が利用可能であることを確認し、必要に応じてインストールします
    
    Returns:
        bool: 依存関係のセットアップに成功したらTrue
    """
    logger.info("Extensionsシステムを使用して依存関係をセットアップします")
    
    # extension.tomlの存在確認
    if not ensure_extension_toml_exists():
        logger.warning("extension.tomlファイルの作成に失敗しました")
        return False
    
    # 依存関係のチェック
    all_dependencies_installed, missing_modules = check_dependencies()
    
    # 不足している依存関係があればインストールを試みる
    if not all_dependencies_installed:
        logger.info(f"不足している依存関係があります: {missing_modules}")
        return install_dependencies_via_extensions_system()
    else:
        logger.info("依存関係は既にインストールされています")
        return True