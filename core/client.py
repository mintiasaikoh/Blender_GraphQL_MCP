"""
Blender Unified MCP - クライアントモジュール
APIサーバーに接続してコマンドを実行するためのクライアント機能を提供します。
"""

import requests
import logging
import json
from typing import Dict, Any, Optional, List, Union

# ロガー設定
logger = logging.getLogger(__name__)

class MCPClient:
    """
    MCPサーバーに接続するクライアントクラス
    これはBlender内部やリモートアプリケーションからMCPサーバーにアクセスするために使用します。
    """
    
    API_VERSION = "1.0.0"  # クライアントが使用するAPIバージョン
    
    def __init__(self, host: str = "localhost", port: int = 8000, timeout: int = 10):
        """クライアントの初期化
        
        Args:
            host: サーバーのホスト名
            port: サーバーのポート番号
            timeout: リクエストタイムアウト秒数
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self.api_version = self.API_VERSION
        self.server_info = None
        self.compatible_versions = []
        
    def check_server(self) -> Dict[str, Any]:
        """サーバーの状態を確認
        
        Returns:
            サーバー情報（バージョン、ステータスなど）
            
        Raises:
            ConnectionError: サーバーに接続できない場合
        """
        try:
            response = requests.get(
                f"{self.base_url}/",
                timeout=self.timeout
            )
            response.raise_for_status()
            self.server_info = response.json()
            return self.server_info
        except requests.RequestException as e:
            logger.error(f"サーバー接続エラー: {str(e)}")
            raise ConnectionError(f"MCPサーバーに接続できません: {str(e)}")
            
    def get_api_info(self) -> Dict[str, Any]:
        """APIバージョン情報を取得
        
        Returns:
            APIメタデータ（バージョン、互換性情報など）
            
        Raises:
            ConnectionError: APIメタデータを取得できない場合
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/info",
                timeout=self.timeout
            )
            response.raise_for_status()
            api_info = response.json()
            
            # 互換性のあるバージョンリストを保存
            if "compatible_versions" in api_info:
                self.compatible_versions = api_info["compatible_versions"]
                
            return api_info
        except requests.RequestException as e:
            logger.error(f"API情報取得エラー: {str(e)}")
            raise ConnectionError(f"API情報を取得できません: {str(e)}")
    
    def check_version_compatibility(self) -> bool:
        """クライアントとサーバーのAPIバージョン互換性を確認
        
        Returns:
            互換性がある場合はTrue、ない場合はFalse
            
        Raises:
            ConnectionError: APIメタデータを取得できない場合
        """
        if not self.server_info:
            self.check_server()
            
        # APIバージョン情報が必要な場合は取得
        if not self.compatible_versions:
            self.get_api_info()
            
        # サーバーのバージョンを取得
        server_version = self.server_info.get("version")
        if not server_version:
            logger.warning("サーバーからバージョン情報を取得できませんでした")
            return False
            
        # 同じバージョンならOK
        if server_version == self.api_version:
            return True
            
        # 互換性リストに含まれているか確認
        if self.api_version in self.compatible_versions:
            return True
            
        logger.warning(f"互換性のないAPIバージョン: クライアント={self.api_version}, サーバー={server_version}")
        return False
    
    def execute_command(self, command_name: str, **params) -> Any:
        """コマンドを実行
        
        Args:
            command_name: 実行するコマンド名
            **params: コマンドのパラメータ
            
        Returns:
            コマンドの実行結果
            
        Raises:
            ConnectionError: サーバーに接続できない場合
            ValueError: コマンドが見つからない、またはパラメータが無効な場合
            RuntimeError: コマンド実行中にエラーが発生した場合
        """
        # APIバージョンをパラメータに追加
        params["api_version"] = self.api_version
        
        try:
            response = requests.post(
                f"{self.base_url}/execute/{command_name}",
                json=params,
                timeout=self.timeout
            )
            
            # ステータスコードチェック
            response.raise_for_status()
            
            # レスポンスのパース
            result = response.json()
            
            # エラーチェック
            if not result.get("success", False):
                error_message = result.get("error", "不明なエラー")
                raise RuntimeError(f"コマンド '{command_name}' の実行エラー: {error_message}")
                
            return result.get("result")
        except requests.RequestException as e:
            logger.error(f"コマンド実行リクエストエラー: {str(e)}")
            raise ConnectionError(f"コマンド '{command_name}' を実行できません: {str(e)}")
    
    def get_objects(self) -> List[str]:
        """シーン内のオブジェクト一覧を取得
        
        Returns:
            オブジェクト名のリスト
            
        Raises:
            ConnectionError: サーバーに接続できない場合
        """
        try:
            response = requests.get(
                f"{self.base_url}/objects",
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            return result.get("objects", [])
        except requests.RequestException as e:
            logger.error(f"オブジェクト一覧取得エラー: {str(e)}")
            raise ConnectionError(f"オブジェクト一覧を取得できません: {str(e)}")

# クライアントのシングルトンインスタンス
_client_instance = None

def get_client_instance(host: str = "localhost", port: int = 8000) -> MCPClient:
    """クライアントのシングルトンインスタンスを取得
    
    Args:
        host: サーバーのホスト名
        port: サーバーのポート番号
        
    Returns:
        MCPClientインスタンス
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = MCPClient(host, port)
    return _client_instance
