"""
Blenderバージョン互換性ユーティリティ
Blender 4.2以降の機能を提供します
"""

import bpy
import logging

logger = logging.getLogger("blender_graphql_mcp.version_utils")

def get_blender_version():
    """Blenderのバージョンを取得します
    
    Returns:
        tuple: (メジャー, マイナー, パッチ)
    """
    return bpy.app.version

def check_minimum_blender_version():
    """Blender 4.2以降が実行されているか確認します

    Returns:
        bool: Blender 4.2以上の場合はTrue
    """
    version = get_blender_version()
    is_supported = (version[0] > 4) or (version[0] == 4 and version[1] >= 2)
    
    if not is_supported:
        logger.error(f"サポートされていないBlenderバージョン: {version[0]}.{version[1]}.{version[2]}")
        logger.error("Blender GraphQL MCPはBlender 4.2以降のみをサポートしています")
    
    return is_supported

def is_extensions_system_available():
    """Extensionsシステムが利用可能かどうかを判定します

    Returns:
        bool: Extensionsシステムが利用可能な場合はTrue
    """
    # Blender 4.2+のExtensionsシステムの適切なチェック
    try:
        return hasattr(bpy.utils, "register_extension")
    except (ImportError, AttributeError):
        logger.warning("Extensionsシステムが見つかりません")
        return False

def get_extension_toml_path():
    """extension.tomlファイルの絶対パスを取得します
    
    Returns:
        str: extension.tomlファイルの絶対パス
    """
    import os
    addon_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(addon_path, "extension.toml")