"""
Blender Unified MCP - サーバー起動と管理ハンドラ
"""

import bpy
import logging
import os
import sys
import importlib
from typing import Any, Dict, Optional

from . import enhanced_integration
from ..commands import get_registry, register_all_commands

# ロガー設定
logger = logging.getLogger('unified_mcp.server')

class ServerHandler:
    """サーバー管理ハンドラ"""
    
    def __init__(self):
        self.server = None
        self.server_running = False
        self.host = "0.0.0.0"
        self.port = 8000
        self.auto_register_commands = True
    
    def ensure_dependencies(self):
        """必要な依存関係が利用可能か確認"""
        addon_path = os.path.dirname(os.path.dirname(__file__))
        vendor_dir = os.path.join(addon_path, "vendor")
        
        if os.path.exists(vendor_dir) and vendor_dir not in sys.path:
            sys.path.insert(0, vendor_dir)
            logger.info(f"vendorディレクトリをPythonパスに追加しました: {vendor_dir}")
        
        # モジュールの可用性確認
        dependencies = ["fastapi", "uvicorn", "pydantic"]
        missing = []
        
        for dep in dependencies:
            try:
                importlib.import_module(dep)
                logger.info(f"依存関係 '{dep}' が利用可能です")
            except ImportError:
                missing.append(dep)
                logger.warning(f"依存関係 '{dep}' が見つかりません")
        
        if missing:
            logger.error(f"次の依存関係が不足しています: {', '.join(missing)}")
            return False
        
        return True
    
    def register_commands(self):
        """すべての利用可能なコマンドをレジストリに登録"""
        try:
            # コマンドレジストリに登録
            register_all_commands()
            
            # サーバーにコマンドレジストリを接続（サーバーが初期化されている場合）
            if self.server:
                from . import fastapi_server
                server_instance = fastapi_server.get_instance()
                command_registry = get_registry()
                
                # コマンドレジストリを接続
                for name, command_class in command_registry.commands.items():
                    server_instance.register_command(command_class)
                
                logger.info(f"{len(command_registry.commands)} 個のコマンドをサーバーに登録しました")
            
            return True
        except Exception as e:
            logger.error(f"コマンド登録中にエラーが発生しました: {str(e)}")
            return False
    
    def start_server(self, host: str = None, port: int = None):
        """サーバーを起動"""
        if self.server_running:
            logger.info("サーバーは既に実行中です")
            return True
        
        # パラメータ設定
        if host:
            self.host = host
        if port:
            self.port = port
        
        # 依存関係の確認
        if not self.ensure_dependencies():
            logger.error("必要な依存関係が不足しているためサーバーを起動できません")
            return False
        
        try:
            # サーバー統合システムを初期化
            if not enhanced_integration.initialize():
                logger.error("サーバー統合システムの初期化に失敗しました")
                return False
            
            # FastAPIサーバーのインスタンスを取得
            from . import fastapi_server
            self.server = fastapi_server.get_instance()
            
            # コマンドを登録
            if self.auto_register_commands:
                self.register_commands()
            
            # サーバーを起動
            success = self.server.start(host=self.host, port=self.port)
            
            if success:
                self.server_running = True
                logger.info(f"サーバーが起動しました (host: {self.host}, port: {self.server.port})")
                # 実際に使用されたポートを記録（自動的に別のポートが選択された可能性があるため）
                self.port = self.server.port
                return True
            else:
                logger.error("サーバーの起動に失敗しました")
                return False
                
        except Exception as e:
            logger.error(f"サーバー起動中にエラーが発生しました: {str(e)}")
            return False
    
    def stop_server(self):
        """サーバーを停止"""
        if not self.server_running:
            logger.info("サーバーは実行されていません")
            return True
        
        try:
            if self.server:
                success = self.server.stop()
                if success:
                    self.server_running = False
                    logger.info("サーバーを停止しました")
                    return True
                else:
                    logger.error("サーバーの停止に失敗しました")
                    return False
            else:
                logger.warning("サーバーインスタンスが見つかりません")
                self.server_running = False
                return True
                
        except Exception as e:
            logger.error(f"サーバー停止中にエラーが発生しました: {str(e)}")
            return False
    
    def is_running(self):
        """サーバーが実行中かどうかを確認"""
        return self.server_running
    
    def get_server_url(self):
        """サーバーのURLを取得"""
        if not self.server_running:
            return None
        
        return f"http://{self.host if self.host != '0.0.0.0' else 'localhost'}:{self.port}"

# シングルトンインスタンス
_instance = None

def get_instance():
    """ServerHandlerのシングルトンインスタンスを取得"""
    global _instance
    if _instance is None:
        _instance = ServerHandler()
    return _instance
