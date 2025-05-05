"""
Blender Unified MCP - 拡張サーバー統合モジュール
新しいFastAPIサーバーと既存のアドオン構造を統合
"""

import logging
import os
import sys
import importlib
from typing import Dict, Any, Optional

# ロギング設定
logger = logging.getLogger("mcp.enhanced")

# サーバーの種類
SERVER_TYPE_FASTAPI = "fastapi"
SERVER_TYPE_SIMPLE = "simple"

# グローバル変数
_initialized = False
_server_instance = None
_server_type = SERVER_TYPE_FASTAPI  # デフォルトはFastAPI

def initialize(server_type=SERVER_TYPE_FASTAPI):
    """拡張サーバー統合システムを初期化"""
    global _initialized, _server_type
    
    if _initialized:
        logger.info("拡張サーバー統合システムは既に初期化されています")
        return True
    
    # vendorディレクトリをPythonpathに追加
    try:
        addon_path = os.path.dirname(os.path.dirname(__file__))  # coreの親ディレクトリ
        vendor_dir = os.path.join(addon_path, "vendor")
        
        if os.path.exists(vendor_dir) and vendor_dir not in sys.path:
            sys.path.insert(0, vendor_dir)
            logger.info(f"vendorディレクトリをPythonパスに追加しました: {vendor_dir}")
    except Exception as e:
        logger.error(f"vendorディレクトリの追加中にエラーが発生しました: {str(e)}")
    
    _server_type = server_type
    logger.info(f"拡張サーバー統合システムを初期化しています (タイプ: {_server_type})")
    
    try:
        # 必要なモジュールの存在確認
        if _server_type == SERVER_TYPE_FASTAPI:
            try:
                # 明示的にモジュールをロードして確認
                import fastapi
                logger.info(f"FastAPI {fastapi.__version__} をロードしました")
                
                import uvicorn
                logger.info(f"Uvicorn {uvicorn.__version__} をロードしました")
                
                import pydantic
                logger.info(f"Pydantic {pydantic.__version__} をロードしました")
                
                # 全ての必要な依存関係が利用可能
                logger.info("FastAPI関連モジュールが全て利用可能です")
            except ImportError as e:
                # 詳細なログを出力
                logger.error(f"FastAPIモジュールインポートエラー: {str(e)}")
                logger.warning("FastAPIモジュールが利用できません。標準HTTPサーバーにフォールバックします")
                _server_type = SERVER_TYPE_SIMPLE
    
        _initialized = True
        logger.info("拡張サーバー統合システムの初期化が完了しました")
        return True
        
    except Exception as e:
        logger.error(f"拡張サーバー統合システムの初期化中にエラーが発生しました: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

def get_server_instance():
    """設定されたタイプに基づいてサーバーインスタンスを取得"""
    global _server_instance, _server_type, _initialized
    
    if not _initialized:
        initialize()
    
    if _server_instance is not None:
        return _server_instance
    
    try:
        if _server_type == SERVER_TYPE_FASTAPI:
            # FastAPIサーバーのインスタンスを取得
            try:
                from .fastapi_server import get_instance as get_fastapi_instance
                _server_instance = get_fastapi_instance()
                logger.info("FastAPIサーバーインスタンスを取得しました")
                
                # 標準コマンドを登録
                try:
                    from .standard_commands import register_standard_commands
                    register_standard_commands(_server_instance)
                    logger.info("標準コマンドセットを登録しました")
                except Exception as e:
                    logger.error(f"標準コマンドの登録中にエラーが発生しました: {str(e)}")
                
                return _server_instance
            except Exception as e:
                logger.error(f"FastAPIサーバーの初期化に失敗しました: {str(e)}")
                _server_type = SERVER_TYPE_SIMPLE
        
        # SimpltHTTPサーバーへのフォールバック
        if _server_type == SERVER_TYPE_SIMPLE:
            from .server import get_instance as get_simple_instance
            _server_instance = get_simple_instance()
            logger.info("標準HTTPサーバーインスタンスを取得しました (フォールバック)")
            return _server_instance
            
    except Exception as e:
        logger.error(f"サーバーインスタンスの取得中にエラーが発生しました: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        raise
    
    return None

def start_server(host="localhost", port=8000):
    """サーバーを開始"""
    server = get_server_instance()
    if server:
        success = server.start(host=host, port=port)
        logger.info(f"サーバー開始結果: {'成功' if success else '失敗'}")
        return success
    return False

def stop_server():
    """サーバーを停止"""
    server = get_server_instance()
    if server:
        success = server.stop()
        logger.info(f"サーバー停止結果: {'成功' if success else '失敗'}")
        return success
    return False

def is_running():
    """サーバーが実行中かどうかを確認"""
    server = get_server_instance()
    if server:
        running = getattr(server, 'running', False)
        return running
    return False

def get_server_info():
    """サーバー情報を取得"""
    server = get_server_instance()
    if server:
        server_type = _server_type
        server_class = server.__class__.__name__
        running = getattr(server, 'running', False)
        host = getattr(server, 'host', 'localhost')
        port = getattr(server, 'port', 8000)
        
        info = {
            "type": server_type,
            "class": server_class,
            "running": running,
            "host": host,
            "port": port,
            "url": f"http://{host}:{port}" if running else None
        }
        
        # FastAPIサーバーの場合、追加情報を含める
        if server_type == SERVER_TYPE_FASTAPI:
            command_registry = getattr(server, 'command_registry', None)
            if command_registry:
                commands = getattr(command_registry, 'commands', {})
                command_groups = getattr(command_registry, 'command_groups', {})
                info.update({
                    "commands_count": len(commands),
                    "command_groups": list(command_groups.keys())
                })
        
        return info
    
    return {
        "error": "サーバーインスタンスが利用できません"
    }

def register_command(command_class):
    """コマンドをサーバーに登録"""
    server = get_server_instance()
    if server and hasattr(server, 'register_command'):
        server.register_command(command_class)
        return True
    return False

def execute_command(command_name, params=None):
    """コマンドを実行"""
    server = get_server_instance()
    if server and hasattr(server, 'command_registry'):
        if hasattr(server.command_registry, 'execute_command'):
            return server.command_registry.execute_command(command_name, params)
    return None
