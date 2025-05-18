"""
MCP GraphQL Resolvers - 改善版
標準化されたエラー処理とスキーマ型を活用したMCP機能のリゾルバー実装
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple

from core.blender_mcp import get_blender_mcp
from core.blender_context import get_context_manager
from core.command_executor import get_command_executor
from core.preview_generator import get_preview_generator
from core.mcp_command_processor import get_mcp_processor

# 新しいスキーマコンポーネントをインポート
from tools.schema_error import (
    ErrorCode,
    with_error_handling,
    create_standard_error_result,
    create_standard_error,
    create_success_result
)

logger = logging.getLogger('blender_mcp.tools.handlers.improved_mcp')

class ImprovedMCPResolvers:
    """改善されたMCP関連のリゾルバー"""
    
    def __init__(self):
        self.mcp = get_blender_mcp()
        self.context_manager = get_context_manager()
        self.command_executor = get_command_executor()
        self.preview_generator = get_preview_generator()
        self.mcp_processor = get_mcp_processor()
    
    # クエリリゾルバー
    @with_error_handling
    def resolve_scene_context(self, root, info) -> Dict[str, Any]:
        """現在のシーンコンテキストを返す"""
        context = self.context_manager.get_complete_context()
        formatted_context = self._format_scene_context(context)
        
        return create_success_result(
            additional_data=formatted_context
        )
    
    @with_error_handling
    def resolve_selected_objects(self, root, info) -> Dict[str, Any]:
        """選択中のオブジェクトリストを返す"""
        selected_objects = self.context_manager.get_selected_objects()
        formatted_objects = self._format_objects(selected_objects)
        
        return create_success_result(
            additional_data={"objects": formatted_objects}
        )
    
    @with_error_handling
    def resolve_available_operations(self, root, info, context: Optional[str] = None) -> Dict[str, Any]:
        """利用可能な操作リストを返す"""
        available_operations = self.context_manager._get_available_operations()
        
        return create_success_result(
            additional_data={"operations": available_operations}
        )
    
    @with_error_handling
    def resolve_execution_stats(self, root, info) -> Dict[str, Any]:
        """実行統計を返す"""
        stats = self.command_executor.get_execution_stats()
        
        return create_success_result(
            additional_data={"stats": stats}
        )
    
    # ミューテーションリゾルバー
    @with_error_handling
    def resolve_execute_natural_command(self, root, info, command: str, 
                                     options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """自然言語コマンドを実行"""
        start_time = time.time()
        
        # コマンド実行
        result = self.mcp.process_natural_command(command, options)
        
        # 実行時間の計算
        execution_time_ms = (time.time() - start_time) * 1000
        
        if not result.get("success", False):
            # エラーの場合
            return create_standard_error_result(
                code=ErrorCode.COMMAND_EXECUTION_FAILED,
                message=result.get("error", "コマンド実行に失敗しました"),
                details=result.get("details"),
                execution_time_ms=execution_time_ms,
                additional_data={
                    "generatedCode": result.get("generated_code"),
                    "suggestions": result.get("suggestions", [])
                }
            )
        
        # 成功の場合
        formatted_result = self._format_command_result(result)
        formatted_result["executionTimeMs"] = execution_time_ms
        
        return formatted_result
    
    @with_error_handling
    def resolve_execute_with_context(self, root, info, command: str,
                                  context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """コンテキスト付きでコマンドを実行"""
        start_time = time.time()
        
        # コマンド実行
        result = self.mcp.execute_with_context(command, context)
        
        # 実行時間の計算
        execution_time_ms = (time.time() - start_time) * 1000
        
        if not result.get("success", False):
            # エラーの場合
            return create_standard_error_result(
                code=ErrorCode.COMMAND_EXECUTION_FAILED,
                message=result.get("error", "コマンド実行に失敗しました"),
                details=result.get("details"),
                execution_time_ms=execution_time_ms,
                additional_data={
                    "generatedCode": result.get("generated_code"),
                    "suggestions": result.get("suggestions", [])
                }
            )
        
        # 成功の場合
        formatted_result = self._format_command_result(result)
        formatted_result["executionTimeMs"] = execution_time_ms
        
        return formatted_result
    
    @with_error_handling
    def resolve_iterate_on_model(self, root, info, modelId: str, feedback: str,
                              renderOptions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """モデルの反復的改善"""
        start_time = time.time()
        
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
        
        # モデル改善の実行
        result = self.mcp.iterate_on_model(modelId, feedback, render_options)
        
        # 実行時間の計算
        execution_time_ms = (time.time() - start_time) * 1000
        
        if not result.get("success", False):
            # エラーの場合
            return create_standard_error_result(
                code=ErrorCode.OPERATION_FAILED,
                message=result.get("error", "モデル改善に失敗しました"),
                execution_time_ms=execution_time_ms
            )
        
        # 成功の場合
        formatted_result = self._format_iteration_result(result)
        formatted_result["executionTimeMs"] = execution_time_ms
        
        return formatted_result
    
    @with_error_handling
    def resolve_capture_preview(self, root, info, width: int = 512, 
                             height: int = 512, view: str = "current") -> Dict[str, Any]:
        """プレビューをキャプチャ"""
        start_time = time.time()
        
        # プレビューキャプチャの実行
        result = self.preview_generator.capture_viewport(
            resolution=(width, height),
            view=view
        )
        
        # 実行時間の計算
        execution_time_ms = (time.time() - start_time) * 1000
        
        if not result.get("success", False):
            # エラーの場合
            return create_standard_error_result(
                code=ErrorCode.OPERATION_FAILED,
                message="プレビューキャプチャに失敗しました",
                details=result.get("error"),
                execution_time_ms=execution_time_ms
            )
        
        # 成功の場合
        return create_success_result(
            message="プレビューキャプチャに成功しました",
            execution_time_ms=execution_time_ms,
            additional_data={
                "preview": {
                    "imageUrl": result["preview"],
                    "format": result["metadata"]["format"] if "metadata" in result else "PNG",
                    "resolution": [width, height],
                    "viewport": view
                }
            }
        )
    
    @with_error_handling
    def resolve_execute_raw_command(self, root, info, pythonCode: str,
                                 metadata: Optional[str] = None) -> Dict[str, Any]:
        """LLMが生成したPythonコードを直接実行"""
        start_time = time.time()
        
        # メタデータをパース（JSONが渡された場合）
        parsed_metadata = None
        if metadata:
            try:
                import json
                parsed_metadata = json.loads(metadata)
            except:
                parsed_metadata = {"raw": metadata}
        
        # コマンド実行
        result = self.mcp_processor.process_raw_command(pythonCode, parsed_metadata)
        
        # 実行時間の計算
        execution_time_ms = (time.time() - start_time) * 1000
        
        if not result.get("success", False):
            # エラーの場合
            return create_standard_error_result(
                code=ErrorCode.COMMAND_EXECUTION_FAILED,
                message=result.get("error", "コマンド実行に失敗しました"),
                details=result.get("details"),
                execution_time_ms=execution_time_ms,
                additional_data={
                    "executedCode": pythonCode,
                    "suggestions": result.get("suggestions", [])
                }
            )
        
        # 成功の場合
        formatted_result = self._format_raw_command_result(result)
        formatted_result["executionTimeMs"] = execution_time_ms
        
        return formatted_result
    
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
            "message": "コマンドが正常に実行されました",
            "generatedCode": result.get("generated_code")
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
            "message": "モデル改善が正常に完了しました",
            "modelId": result.get("model_id"),
            "preview": result.get("preview")
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
            "message": "コードが正常に実行されました",
            "executedCode": result.get("executed_code", ""),
            "result": str(result.get("result", "")),
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
_improved_mcp_resolvers = None

def get_improved_mcp_resolvers() -> ImprovedMCPResolvers:
    """改善されたMCPリゾルバーのシングルトンインスタンスを取得"""
    global _improved_mcp_resolvers
    if _improved_mcp_resolvers is None:
        _improved_mcp_resolvers = ImprovedMCPResolvers()
    return _improved_mcp_resolvers

# リゾルバー関数（GraphQLスキーマから呼び出される）
def resolve_scene_context(root, info):
    return get_improved_mcp_resolvers().resolve_scene_context(root, info)

def resolve_selected_objects(root, info):
    return get_improved_mcp_resolvers().resolve_selected_objects(root, info)

def resolve_available_operations(root, info, context=None):
    return get_improved_mcp_resolvers().resolve_available_operations(root, info, context)

def resolve_execution_stats(root, info):
    return get_improved_mcp_resolvers().resolve_execution_stats(root, info)

def resolve_execute_natural_command(root, info, command, options=None):
    return get_improved_mcp_resolvers().resolve_execute_natural_command(root, info, command, options)

def resolve_execute_with_context(root, info, command, context=None):
    return get_improved_mcp_resolvers().resolve_execute_with_context(root, info, command, context)

def resolve_iterate_on_model(root, info, modelId, feedback, renderOptions=None):
    return get_improved_mcp_resolvers().resolve_iterate_on_model(root, info, modelId, feedback, renderOptions)

def resolve_capture_preview(root, info, width=512, height=512, view="current"):
    return get_improved_mcp_resolvers().resolve_capture_preview(root, info, width, height, view)

def resolve_execute_raw_command(root, info, pythonCode, metadata=None):
    return get_improved_mcp_resolvers().resolve_execute_raw_command(root, info, pythonCode, metadata)