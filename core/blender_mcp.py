"""
Blender MCP Core
LLMとBlenderを繋ぐメインモジュール
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .blender_context import get_context_manager
from .command_executor import get_command_executor
from .preview_generator import get_preview_generator
from .llm_integration import get_llm_integration
from .nlp_processor import get_nlp_processor

# モジュールレベルのロガー
logger = logging.getLogger('blender_mcp.core')

class BlenderMCP:
    """Blender MCPのメインクラス"""
    
    def __init__(self):
        self.context_manager = get_context_manager()
        self.command_executor = get_command_executor()
        self.preview_generator = get_preview_generator()
        self.llm_integration = get_llm_integration()
        self.nlp_processor = get_nlp_processor()
        self.session_data = {
            "start_time": datetime.now().isoformat(),
            "command_count": 0,
            "last_command": None
        }
        
    def process_natural_command(self, 
                              command: str, 
                              options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """自然言語コマンドを処理"""
        options = options or {}
        result = {
            "success": False,
            "command": command,
            "generated_code": None,
            "execution_result": None,
            "preview": None,
            "context": None,
            "suggestions": [],
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 現在のコンテキストを取得
            before_context = self.context_manager.get_complete_context()
            
            # コマンドからPythonコードを生成（ここではシンプルな例）
            python_code = self._generate_python_code(command, before_context)
            result["generated_code"] = python_code
            
            # コマンドを実行
            execution_result = self.command_executor.execute_command(
                python_code, 
                context=before_context
            )
            result["execution_result"] = execution_result
            
            if execution_result["success"]:
                # 実行後のコンテキストを取得
                after_context = self.context_manager.get_complete_context()
                result["context"] = after_context
                
                # プレビューを生成
                if options.get("generate_preview", True):
                    preview_result = self.preview_generator.capture_viewport()
                    if preview_result["success"]:
                        result["preview"] = preview_result["preview"]
                
                # 次のアクション候補を生成
                result["suggestions"] = self._generate_suggestions(command, after_context)
                
                result["success"] = True
            else:
                result["error"] = execution_result["error"]
                result["suggestions"] = self._generate_error_suggestions(
                    execution_result["error_details"]
                )
            
            # セッションデータを更新
            self.session_data["command_count"] += 1
            self.session_data["last_command"] = command
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"自然言語コマンド処理エラー: {e}")
            
        return result
    
    def execute_with_context(self, 
                           command: str,
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """コンテキスト付きでコマンドを実行"""
        # 現在のコンテキストを取得
        current_context = self.context_manager.get_complete_context()
        
        # 指定されたコンテキストとマージ
        if context:
            current_context.update(context)
        
        # コマンドを生成
        python_code = self._generate_python_code(command, current_context)
        
        # 実行
        result = self.command_executor.execute_command(python_code, context=current_context)
        
        # プレビューを生成
        if result["success"]:
            preview = self.preview_generator.capture_viewport()
            result["preview"] = preview.get("preview") if preview["success"] else None
        
        return result
    
    def iterate_on_model(self,
                        model_id: str,
                        feedback: str,
                        render_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """モデルの反復的な改善"""
        result = {
            "success": False,
            "model_id": model_id,
            "feedback": feedback,
            "changes": [],
            "preview": None,
            "error": None
        }
        
        try:
            # 現在のコンテキストを取得
            context = self.context_manager.get_complete_context()
            
            # 対象モデルを確認
            model_found = False
            for obj in context["selected_objects"]:
                if obj["id"] == model_id:
                    model_found = True
                    break
            
            if not model_found:
                result["error"] = f"モデル {model_id} が見つかりません"
                return result
            
            # フィードバックに基づいてコマンドを生成
            command = self._generate_command_from_feedback(feedback, model_id, context)
            
            # コマンドを実行
            execution_result = self.execute_with_context(command)
            
            if execution_result["success"]:
                # 変更点を記録
                result["changes"] = self._detect_changes(context, execution_result["context"])
                
                # プレビューを生成
                if render_options:
                    preview = self.preview_generator.capture_viewport(**render_options)
                else:
                    preview = self.preview_generator.capture_viewport()
                
                result["preview"] = preview.get("preview") if preview["success"] else None
                result["success"] = True
            else:
                result["error"] = execution_result["error"]
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"モデル反復処理エラー: {e}")
            
        return result
    
    def get_current_state(self) -> Dict[str, Any]:
        """現在の完全な状態を取得"""
        state = {
            "context": self.context_manager.get_complete_context(),
            "preview": None,
            "session": self.session_data,
            "statistics": self.command_executor.get_execution_stats()
        }
        
        # プレビューを生成
        preview_result = self.preview_generator.capture_viewport()
        if preview_result["success"]:
            state["preview"] = preview_result["preview"]
        
        return state
    
    def _generate_python_code(self, command: str, context: Dict[str, Any]) -> str:
        """自然言語コマンドからPythonコードを生成"""
        # まずNLPプロセッサーを使用してテンプレートベースの変換を試みる
        nlp_result = self.nlp_processor.process_natural_language(command)
        
        if nlp_result['generated_code'] and nlp_result['confidence'] > 0.6:
            # 高い信頼度でコードが生成された場合はそれを使用
            logger.info(f"Using template-based code generation with confidence: {nlp_result['confidence']}")
            return nlp_result['generated_code']
        else:
            # 信頼度が低い場合はLLM統合を使用
            logger.info(f"Falling back to LLM generation due to low confidence: {nlp_result['confidence']}")
            return self.llm_integration.generate_python_code(command, context)
    
    def _generate_command_from_feedback(self, feedback: str, model_id: str, context: Dict[str, Any]) -> str:
        """フィードバックからコマンドを生成"""
        # LLM統合を使用してフィードバックからコマンドを生成
        return self.llm_integration.generate_from_feedback(feedback, model_id, context)
    
    def _generate_suggestions(self, command: str, context: Dict[str, Any]) -> List[str]:
        """次のアクション候補を生成"""
        suggestions = []
        
        # 最近のコマンドに基づいて提案
        if "作成" in command or "create" in command.lower():
            suggestions.extend([
                "マテリアルを追加",
                "位置を調整",
                "サイズを変更",
                "複製を作成"
            ])
        
        # コンテキストに基づいて提案
        if context.get("selected_objects"):
            suggestions.extend([
                "選択オブジェクトを結合",
                "モディファイアを追加",
                "アニメーションを設定"
            ])
            
        return suggestions
    
    def _generate_error_suggestions(self, error_details: Dict[str, Any]) -> List[str]:
        """エラーに基づいて修正案を生成"""
        suggestions = []
        
        if error_details:
            error_type = error_details.get("type", "")
            if error_type == "AttributeError":
                suggestions.append("オブジェクトを選択してから再試行")
            elif error_type == "TypeError":
                suggestions.append("パラメータの型を確認")
            
            # エラーの提案があれば追加
            if error_details.get("suggestion"):
                suggestions.append(error_details["suggestion"])
                
        return suggestions
    
    def _detect_changes(self, before: Dict[str, Any], after: Dict[str, Any]) -> List[Dict[str, Any]]:
        """変更点を検出"""
        changes = []
        
        # オブジェクトの追加/削除を検出
        before_objects = {obj["id"] for obj in before.get("selected_objects", [])}
        after_objects = {obj["id"] for obj in after.get("selected_objects", [])}
        
        added = after_objects - before_objects
        removed = before_objects - after_objects
        
        for obj_id in added:
            changes.append({"type": "added", "object": obj_id})
        for obj_id in removed:
            changes.append({"type": "removed", "object": obj_id})
        
        # 既存オブジェクトの変更を検出
        for obj_id in before_objects & after_objects:
            before_obj = next((o for o in before["selected_objects"] if o["id"] == obj_id), None)
            after_obj = next((o for o in after["selected_objects"] if o["id"] == obj_id), None)
            
            if before_obj and after_obj:
                if before_obj["location"] != after_obj["location"]:
                    changes.append({
                        "type": "moved",
                        "object": obj_id,
                        "from": before_obj["location"],
                        "to": after_obj["location"]
                    })
                    
        return changes

# グローバルインスタンス
_blender_mcp = None

def get_blender_mcp() -> BlenderMCP:
    """Blender MCPのシングルトンインスタンスを取得"""
    global _blender_mcp
    if _blender_mcp is None:
        _blender_mcp = BlenderMCP()
    return _blender_mcp