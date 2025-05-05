"""
Unified MCPのAPIモジュール
JSON形式のコマンドとクエリを処理する主要なインターフェース
"""

import bpy
import json
import logging
import traceback
from typing import Dict, List, Any, Optional, Union

from .commands.base import execute_command, get_command
from .context.scene_context import SceneContext
from .context.object_context import ObjectContext

logger = logging.getLogger(__name__)

class UnifiedMCPAPI:
    """
    Blender Unified MCP APIのメインクラス
    コマンドとコンテキストクエリのディスパッチを担当
    """
    
    def __init__(self):
        """初期化"""
        logger.info("Unified MCP API initialized")
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        APIリクエストを処理
        
        Args:
            request_data: リクエストデータ（JSONから変換）
            
        Returns:
            レスポンスデータ（JSONに変換可能）
        """
        try:
            request_type = request_data.get("type", "")
            
            if not request_type:
                return {
                    "success": False,
                    "error": "リクエストタイプが指定されていません"
                }
            
            # リクエストタイプに基づいてディスパッチ
            if request_type == "command":
                return self._process_command(request_data)
            elif request_type == "query":
                return self._process_query(request_data)
            else:
                return {
                    "success": False,
                    "error": f"不明なリクエストタイプ: {request_type}"
                }
                
        except Exception as e:
            logger.error(f"APIリクエスト処理中にエラーが発生: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _process_command(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        コマンドリクエストを処理
        
        Args:
            request_data: コマンドリクエストデータ
            
        Returns:
            コマンド実行結果
        """
        command_data = request_data.get("command", {})
        
        if not command_data or not isinstance(command_data, dict):
            return {
                "success": False,
                "error": "有効なコマンドデータがありません"
            }
        
        # コマンド実行
        result = execute_command(command_data)
        return result
    
    def _process_query(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        クエリリクエストを処理
        
        Args:
            request_data: クエリリクエストデータ
            
        Returns:
            クエリ結果
        """
        query_data = request_data.get("query", {})
        
        if not query_data or not isinstance(query_data, dict):
            return {
                "success": False,
                "error": "有効なクエリデータがありません"
            }
        
        query_type = query_data.get("type", "")
        
        if not query_type:
            return {
                "success": False,
                "error": "クエリタイプが指定されていません"
            }
        
        # クエリタイプに基づいてディスパッチ
        if query_type == "scene":
            return self._query_scene(query_data)
        elif query_type == "object":
            return self._query_object(query_data)
        elif query_type == "commands":
            return self._query_available_commands()
        else:
            return {
                "success": False,
                "error": f"不明なクエリタイプ: {query_type}"
            }
    
    def _query_scene(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        シーンコンテキストを取得
        
        Args:
            query_data: シーンクエリデータ
            
        Returns:
            シーン情報
        """
        detail_level = query_data.get("detail_level", "standard")
        
        # 詳細レベルの検証
        if detail_level not in ["basic", "standard", "detailed"]:
            detail_level = "standard"
        
        try:
            scene_data = SceneContext.get_context(detail_level)
            
            return {
                "success": True,
                "query_type": "scene",
                "detail_level": detail_level,
                "data": scene_data
            }
            
        except Exception as e:
            logger.error(f"シーンクエリ処理中にエラーが発生: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "query_type": "scene",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _query_object(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        オブジェクト情報を取得
        
        Args:
            query_data: オブジェクトクエリデータ
            
        Returns:
            オブジェクト情報
        """
        object_name = query_data.get("object_name", "")
        detail_level = query_data.get("detail_level", "standard")
        
        # パラメータの検証
        if not object_name:
            return {
                "success": False,
                "query_type": "object",
                "error": "オブジェクト名が指定されていません"
            }
        
        if detail_level not in ["basic", "standard", "detailed"]:
            detail_level = "standard"
        
        try:
            object_data = ObjectContext.get_object_info(object_name, detail_level)
            
            return {
                "success": True,
                "query_type": "object",
                "object_name": object_name,
                "detail_level": detail_level,
                "data": object_data
            }
            
        except Exception as e:
            logger.error(f"オブジェクトクエリ処理中にエラーが発生: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "query_type": "object",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _query_available_commands(self) -> Dict[str, Any]:
        """
        利用可能なコマンドとそのスキーマを取得
        
        Returns:
            コマンド情報
        """
        from .commands.base import COMMAND_REGISTRY
        
        commands_info = {}
        
        for cmd_name, cmd_class in COMMAND_REGISTRY.items():
            cmd_instance = cmd_class()
            commands_info[cmd_name] = {
                "description": cmd_instance.description,
                "parameters": cmd_instance.parameters_schema
            }
        
        return {
            "success": True,
            "query_type": "commands",
            "commands": commands_info
        }
