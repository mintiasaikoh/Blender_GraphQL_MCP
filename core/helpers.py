"""
Unified MCP Helpers Module
ユーティリティ関数と補助機能を提供
"""

import bpy
import os
import json
import traceback
import logging
from typing import Any, Dict, List, Optional, Union

# ロガー設定
logger = logging.getLogger('unified_mcp.core.helpers')

def get_blender_version() -> str:
    """Blenderのバージョン情報を取得"""
    return ".".join(map(str, bpy.app.version))

def get_scene_stats() -> Dict[str, Any]:
    """シーンの統計情報を取得"""
    scene = bpy.context.scene
    
    # オブジェクト数をタイプ別に集計
    object_counts = {}
    for obj in bpy.data.objects:
        if obj.type not in object_counts:
            object_counts[obj.type] = 0
        object_counts[obj.type] += 1
    
    # マテリアル数
    materials_count = len(bpy.data.materials)
    
    # 頂点と面の数をカウント
    vertices_count = 0
    faces_count = 0
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data:
            vertices_count += len(obj.data.vertices)
            faces_count += len(obj.data.polygons)
    
    return {
        "objects_total": len(bpy.data.objects),
        "objects_selected": len(bpy.context.selected_objects),
        "objects_by_type": object_counts,
        "materials": materials_count,
        "vertices": vertices_count,
        "faces": faces_count,
        "collections": len(bpy.data.collections),
        "active_object": bpy.context.active_object.name if bpy.context.active_object else None
    }

def save_json(data: Any, filepath: str) -> bool:
    """JSONデータをファイルに保存"""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"JSON保存エラー: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def load_json(filepath: str) -> Optional[Any]:
    """JSONデータをファイルから読み込み"""
    try:
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON読み込みエラー: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

def get_addon_path() -> str:
    """アドオンのルートパスを取得"""
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def get_user_preferences_path() -> str:
    """ユーザー設定の保存パスを取得"""
    return os.path.join(bpy.utils.resource_path('USER'), 'config', 'unified_mcp')

def find_objects_by_name_pattern(pattern: str) -> List[bpy.types.Object]:
    """名前パターンでオブジェクトを検索"""
    pattern = pattern.lower()
    return [obj for obj in bpy.data.objects if pattern in obj.name.lower()]

def find_objects_by_type(type_name: str) -> List[bpy.types.Object]:
    """タイプでオブジェクトを検索"""
    return [obj for obj in bpy.data.objects if obj.type == type_name]

def ensure_object_exists(name: str) -> Optional[bpy.types.Object]:
    """オブジェクトの存在を確認し、存在しない場合はNoneを返す"""
    return bpy.data.objects.get(name)

def check_dependencies() -> Dict[str, bool]:
    """必要な依存関係の利用可否をチェック"""
    dependencies = {
        "fastapi": False,
        "uvicorn": False,
        "pydantic": False,
        "graphql": False
    }
    
    # FastAPI
    try:
        import fastapi
        dependencies["fastapi"] = True
        logger.info(f"FastAPI利用可: バージョン {fastapi.__version__}")
    except ImportError:
        logger.warning("FastAPIが見つかりません")
    
    # uvicorn
    try:
        import uvicorn
        dependencies["uvicorn"] = True
        logger.info(f"uvicorn利用可: バージョン {uvicorn.__version__}")
    except ImportError:
        logger.warning("uvicornが見つかりません")
    
    # pydantic
    try:
        import pydantic
        dependencies["pydantic"] = True
        logger.info(f"pydantic利用可: バージョン {pydantic.__version__}")
    except ImportError:
        logger.warning("pydanticが見つかりません")
    
    # graphql
    try:
        import graphql
        dependencies["graphql"] = True
        logger.info(f"graphql-core利用可: バージョン {graphql.__version__}")
    except ImportError:
        logger.warning("graphql-coreが見つかりません")
    
    return dependencies

def install_dependency_instructions() -> Dict[str, str]:
    """依存関係のインストール手順を取得"""
    try:
        # Blender 2.8x ~ 3.x 用
        blender_python = os.path.join(bpy.app.binary_path_python)
    except AttributeError:
        # Blender 4.x 用
        # システムのPythonを使用
        blender_python = sys.executable
    
    return {
        "fastapi": f"{blender_python} -m pip install fastapi",
        "uvicorn": f"{blender_python} -m pip install uvicorn",
        "pydantic": f"{blender_python} -m pip install pydantic",
        "graphql": f"{blender_python} -m pip install graphql-core"
    }

def register():
    """ヘルパーモジュールの登録処理"""
    # 依存関係チェック
    dependencies = check_dependencies()
    all_available = all(dependencies.values())
    
    if not all_available:
        missing = [dep for dep, available in dependencies.items() if not available]
        logger.warning(f"一部の依存関係が見つかりません: {', '.join(missing)}")
        
        instructions = install_dependency_instructions()
        for dep in missing:
            logger.info(f"{dep}のインストール方法: {instructions[dep]}")
    else:
        logger.info("すべての依存関係が利用可能です")

def unregister():
    """ヘルパーモジュールの登録解除処理"""
    pass  # クリーンアップが必要な場合に記述