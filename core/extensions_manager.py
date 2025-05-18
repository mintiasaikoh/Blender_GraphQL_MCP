"""
Blender Extensionsシステム向け依存関係管理モジュール
Blender 4.2+のExtensionsシステムを使用した依存関係管理を行います
"""

import os
import sys
import logging
import traceback
import importlib
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("blender_graphql_mcp.extensions_manager")

# Blenderバージョンユーティリティをインポート
try:
    from .blender_version_utils import is_blender_42_or_higher, get_extension_toml_path
except ImportError:
    # フォールバック関数の定義
    def is_blender_42_or_higher():
        """Blender 4.2以降かどうかを判定します"""
        import bpy
        version = bpy.app.version
        return (version[0] >= 4 and version[1] >= 2) or version[0] > 4
    
    def get_extension_toml_path():
        """extension.tomlファイルの絶対パスを取得します"""
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
    "graphql-core>=3.2.3"
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
    required_modules = ["fastapi", "uvicorn", "pydantic", "graphql_core"]
    missing_modules = []
    
    for module_name in required_modules:
        try:
            importlib.import_module(module_name.replace('-', '_'))
            logger.info(f"モジュール {module_name} は正常にインポートされました")
        except ImportError:
            logger.warning(f"モジュール {module_name} が見つかりません")
            missing_modules.append(module_name)
    
    return len(missing_modules) == 0, missing_modules

def install_dependencies_via_extensions_system() -> bool:
    """Blender Extensionsシステムを使用して依存関係をインストールします

    Returns:
        bool: インストールに成功したらTrue
    """
    if not is_blender_42_or_higher():
        logger.warning("Blender 4.2以上でないため、Extensionsシステムを使用できません")
        return False

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
                # フォールバック: PIPを直接使用
                logger.warning("Blender拡張機能APIが見つかりません。PIPを直接使用します")

                import subprocess
                python_exe = sys.executable
                extension_dir = os.path.dirname(os.path.dirname(extension_toml_path))

                try:
                    # extension.tomlから依存関係をパース
                    import re
                    with open(extension_toml_path, 'r') as f:
                        content = f.read()

                    # pip要件を抽出 - 安全な正規表現パターンでフィルタリング
                    pip_requirements = []
                    for req in re.findall(r'"([^"]+)"', content):
                        # 追加の安全性チェック - 有効なパッケージ名のみを許可
                        if re.match(r'^[a-zA-Z0-9_\-\.]+(?:[>=<~!]=?[a-zA-Z0-9_\-\.]+)?$', req):
                            pip_requirements.append(req)
                        else:
                            logger.warning(f"安全でない依存関係が無視されました: {req}")

                    if pip_requirements:
                        # インストールコマンドを実行 - 各引数を個別に渡してシェルインジェクションを回避
                        cmd = [python_exe, "-m", "pip", "install"]
                        cmd.extend(pip_requirements)
                        logger.info("pipインストールコマンドを実行します")

                        result = subprocess.run(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            # shell=False を明示的に指定して安全性を高める
                            shell=False
                        )

                        if result.returncode == 0:
                            logger.info("依存関係のインストールに成功しました")
                            installation_success = True
                        else:
                            logger.error(f"依存関係のインストールに失敗しました: {result.stderr}")
                    else:
                        logger.error("extension.tomlからpip要件を抽出できませんでした")
                except Exception as pip_error:
                    logger.error(f"PIPによる依存関係インストール中にエラー: {pip_error}")

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

def setup_extension_environment() -> bool:
    """Extensionsシステムの環境をセットアップします
    
    Returns:
        bool: セットアップに成功したらTrue
    """
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