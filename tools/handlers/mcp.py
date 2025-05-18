"""
MCP GraphQL Resolvers
MCP機能のリゾルバー実装
"""

import logging
from typing import Dict, Any, List, Optional

from core.blender_mcp import get_blender_mcp
from core.blender_context import get_context_manager
from core.command_executor import get_command_executor
from core.preview_generator import get_preview_generator
from core.mcp_command_processor import get_mcp_processor

logger = logging.getLogger('blender_mcp.tools.handlers')

class MCPResolvers:
    """MCP関連のリゾルバー"""
    
    def __init__(self):
        self.mcp = get_blender_mcp()
        self.context_manager = get_context_manager()
        self.command_executor = get_command_executor()
        self.preview_generator = get_preview_generator()
        self.mcp_processor = get_mcp_processor()
    
    # クエリリゾルバー
    def resolve_scene_context(self, root, info) -> Dict[str, Any]:
        """現在のシーンコンテキストを返す"""
        try:
            context = self.context_manager.get_complete_context()
            return self._format_scene_context(context)
        except Exception as e:
            logger.error(f"シーンコンテキスト取得エラー: {e}")
            return {}
    
    def resolve_selected_objects(self, root, info) -> List[Dict[str, Any]]:
        """選択中のオブジェクトリストを返す"""
        try:
            return self.context_manager.get_selected_objects()
        except Exception as e:
            logger.error(f"選択オブジェクト取得エラー: {e}")
            return []
    
    def resolve_available_operations(self, root, info, context: Optional[str] = None) -> List[str]:
        """利用可能な操作リストを返す"""
        try:
            if context:
                # 特定のコンテキストでの操作
                return self.context_manager._get_available_operations()
            else:
                # 現在のコンテキストでの操作
                return self.context_manager._get_available_operations()
        except Exception as e:
            logger.error(f"利用可能操作取得エラー: {e}")
            return []
    
    def resolve_execution_stats(self, root, info) -> Dict[str, Any]:
        """実行統計を返す"""
        try:
            return self.command_executor.get_execution_stats()
        except Exception as e:
            logger.error(f"実行統計取得エラー: {e}")
            return {}
    
    # ミューテーションリゾルバー
    def resolve_execute_natural_command(self, root, info, command: str, 
                                      options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """自然言語コマンドを実行"""
        try:
            result = self.mcp.process_natural_command(command, options)
            return self._format_command_result(result)
        except Exception as e:
            logger.error(f"自然言語コマンド実行エラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def resolve_execute_with_context(self, root, info, command: str,
                                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """コンテキスト付きでコマンドを実行"""
        try:
            result = self.mcp.execute_with_context(command, context)
            return self._format_command_result(result)
        except Exception as e:
            logger.error(f"コンテキスト付きコマンド実行エラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def resolve_iterate_on_model(self, root, info, modelId: str, feedback: str,
                               renderOptions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """モデルの反復的改善"""
        try:
            # レンダーオプションの変換
            render_options = None
            if renderOptions:
                render_options = {
                    "resolution": (
                        renderOptions.get("width", 512),
                        renderOptions.get("height", 512)
                    ),
                    "format": renderOptions.get("format", "PNG"),
                    "view": renderOptions.get("view", "current")
                }
            
            result = self.mcp.iterate_on_model(modelId, feedback, render_options)
            return self._format_iteration_result(result)
        except Exception as e:
            logger.error(f"モデル反復処理エラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def resolve_capture_preview(self, root, info, width: int = 512, 
                              height: int = 512, view: str = "current") -> Dict[str, Any]:
        """プレビューをキャプチャ"""
        try:
            result = self.preview_generator.capture_viewport(
                resolution=(width, height),
                view=view
            )
            
            if result["success"]:
                return {
                    "imageUrl": result["preview"],
                    "format": result["metadata"]["format"],
                    "resolution": [width, height],
                    "viewport": view
                }
            else:
                return None
        except Exception as e:
            logger.error(f"プレビューキャプチャエラー: {e}")
            return None
    
    def resolve_execute_raw_command(self, root, info, pythonCode: str,
                                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """LLMが生成したPythonコードを直接実行"""
        try:
            result = self.mcp_processor.process_raw_command(pythonCode, metadata)
            return self._format_raw_command_result(result)
        except Exception as e:
            logger.error(f"Raw command execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "executedCode": pythonCode
            }
    
    # フォーマット関数
    def _format_scene_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """シーンコンテキストをGraphQL形式にフォーマット"""
        scene = context.get("scene", {})
        return {
            "name": scene.get("name", ""),
            "framesCurrent": scene.get("frame_current", 0),
            "objectCount": scene.get("object_count", 0),
            "selectedObjects": self._format_objects(context.get("selected_objects", [])),
            "activeObject": self._format_object(context.get("active_object")),
            "mode": context.get("mode", "")
        }
    
    def _format_objects(self, objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """オブジェクトリストをフォーマット"""
        return [self._format_object(obj) for obj in objects]
    
    def _format_object(self, obj: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """単一オブジェクトをフォーマット"""
        if not obj:
            return None
        
        return {
            "id": obj.get("id", ""),
            "name": obj.get("id", ""),  # IDと同じ
            "type": obj.get("type", ""),
            "location": {
                "x": obj.get("location", [0, 0, 0])[0],
                "y": obj.get("location", [0, 0, 0])[1],
                "z": obj.get("location", [0, 0, 0])[2]
            },
            "selected": True  # 選択リストに含まれているものは選択されている
        }
    
    def _format_command_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """コマンド結果をフォーマット"""
        formatted = {
            "success": result.get("success", False),
            "generatedCode": result.get("generated_code"),
            "error": result.get("error")
        }
        
        # 実行結果
        if result.get("execution_result"):
            exec_result = result["execution_result"]
            formatted["executionResult"] = {
                "success": exec_result.get("success", False),
                "command": exec_result.get("command", ""),
                "result": str(exec_result.get("result", "")),
                "error": exec_result.get("error"),
                "executionTime": exec_result.get("execution_time", 0)
            }
        
        # プレビュー
        if result.get("preview"):
            formatted["preview"] = {
                "imageUrl": result["preview"],
                "format": "PNG",
                "resolution": [512, 512],
                "viewport": "current"
            }
        
        # コンテキスト
        if result.get("context"):
            formatted["context"] = self._format_scene_context(result["context"])
        
        # 提案
        formatted["suggestions"] = result.get("suggestions", [])
        
        return formatted
    
    def _format_iteration_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """反復結果をフォーマット"""
        formatted = {
            "success": result.get("success", False),
            "modelId": result.get("model_id"),
            "preview": result.get("preview"),
            "error": result.get("error")
        }
        
        # 変更点
        if result.get("changes"):
            formatted["changes"] = [
                {
                    "type": change.get("type", ""),
                    "object": change.get("object", ""),
                    "description": self._format_change_description(change)
                }
                for change in result["changes"]
            ]
        else:
            formatted["changes"] = []
        
        return formatted
    
    def _format_change_description(self, change: Dict[str, Any]) -> str:
        """変更の説明文を生成"""
        change_type = change.get("type", "")
        
        if change_type == "added":
            return f"オブジェクト '{change.get('object', '')}' が追加されました"
        elif change_type == "removed":
            return f"オブジェクト '{change.get('object', '')}' が削除されました"
        elif change_type == "moved":
            from_pos = change.get("from", [0, 0, 0])
            to_pos = change.get("to", [0, 0, 0])
            return f"オブジェクト '{change.get('object', '')}' が移動しました"
        else:
            return "変更が検出されました"
    
    def _format_raw_command_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Raw command実行結果をフォーマット"""
        formatted = {
            "success": result.get("success", False),
            "executedCode": result.get("executed_code", ""),
            "result": str(result.get("result", "")),
            "error": result.get("error"),
            "suggestions": result.get("suggestions", [])
        }
        
        # コンテキスト
        if result.get("context_before"):
            formatted["contextBefore"] = self._format_scene_context(result["context_before"])
        if result.get("context_after"):
            formatted["contextAfter"] = self._format_scene_context(result["context_after"])
        
        # 変更点
        if result.get("changes"):
            formatted["changes"] = [
                {
                    "type": change.get("type", ""),
                    "object": change.get("object_id", ""),
                    "description": change.get("description", "")
                }
                for change in result["changes"]
            ]
        
        # プレビュー
        if result.get("preview"):
            formatted["preview"] = {
                "imageUrl": result["preview"],
                "format": "PNG",
                "resolution": [512, 512],
                "viewport": "current"
            }
            
        return formatted

# シングルトンインスタンス
_mcp_resolvers = None

def get_mcp_resolvers() -> MCPResolvers:
    """MCPリゾルバーのシングルトンインスタンスを取得"""
    global _mcp_resolvers
    if _mcp_resolvers is None:
        _mcp_resolvers = MCPResolvers()
    return _mcp_resolvers

# リゾルバー関数（GraphQLスキーマから呼び出される）
def resolve_scene_context(root, info):
    return get_mcp_resolvers().resolve_scene_context(root, info)

def resolve_selected_objects(root, info):
    return get_mcp_resolvers().resolve_selected_objects(root, info)

def resolve_available_operations(root, info, context=None):
    return get_mcp_resolvers().resolve_available_operations(root, info, context)

def resolve_execution_stats(root, info):
    return get_mcp_resolvers().resolve_execution_stats(root, info)

def resolve_execute_natural_command(root, info, command, options=None):
    return get_mcp_resolvers().resolve_execute_natural_command(root, info, command, options)

def resolve_execute_with_context(root, info, command, context=None):
    return get_mcp_resolvers().resolve_execute_with_context(root, info, command, context)

def resolve_iterate_on_model(root, info, modelId, feedback, renderOptions=None):
    return get_mcp_resolvers().resolve_iterate_on_model(root, info, modelId, feedback, renderOptions)

def resolve_capture_preview(root, info, width=512, height=512, view="current"):
    return get_mcp_resolvers().resolve_capture_preview(root, info, width, height, view)

def resolve_execute_raw_command(root, info, pythonCode, metadata=None):
    return get_mcp_resolvers().resolve_execute_raw_command(root, info, pythonCode, metadata)