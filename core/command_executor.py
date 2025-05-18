"""
Blender Command Executor
LLMが生成したコマンドを安全に実行するエンジン
"""

import bpy
import ast
import traceback
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# モジュールレベルのロガー
logger = logging.getLogger('blender_mcp.core.executor')

class CommandExecutor:
    """Blenderコマンドの実行と管理を行うクラス"""
    
    def __init__(self):
        self.execution_history = []
        self.error_patterns = {}
        self.safe_commands = self._define_safe_commands()
        
    def execute_command(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Blenderコマンドを安全に実行"""
        start_time = time.time()
        result = {
            "success": False,
            "command": command,
            "result": None,
            "error": None,
            "execution_time": 0,
            "context_before": context,
            "context_after": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # コマンドの検証
            validation = self._validate_command(command)
            if not validation["is_valid"]:
                result["error"] = validation["error"]
                return result
            
            # コマンドの前処理
            processed_command = self._preprocess_command(command, context)
            
            # 実行環境の準備
            exec_namespace = self._prepare_namespace()
            
            # コマンド実行
            logger.info(f"実行中: {processed_command}")
            exec_result = exec(processed_command, exec_namespace)
            
            # 結果の取得
            result["success"] = True
            result["result"] = exec_namespace.get("__result__", exec_result)
            
        except Exception as e:
            # エラー処理
            error_info = self._handle_error(e, command, context)
            result["error"] = error_info["message"]
            result["error_details"] = error_info
            
            # エラーパターンの学習
            self._learn_error_pattern(e, command, context)
            
            logger.error(f"コマンド実行エラー: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(traceback.format_exc())
        
        finally:
            # 実行時間の記録
            result["execution_time"] = time.time() - start_time
            
            # 実行後のコンテキスト取得
            if context:
                from .blender_context import get_context_manager
                result["context_after"] = get_context_manager().get_complete_context()
            
            # 履歴に記録
            self._record_execution(result)
            
        return result
    
    def execute_safe_command(self, command_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """事前定義された安全なコマンドを実行"""
        if command_type not in self.safe_commands:
            return {
                "success": False,
                "error": f"未定義のコマンドタイプ: {command_type}"
            }
        
        command_template = self.safe_commands[command_type]
        command = command_template.format(**params)
        
        return self.execute_command(command)
    
    def _define_safe_commands(self) -> Dict[str, str]:
        """安全なコマンドテンプレートを定義"""
        return {
            "create_cube": "bpy.ops.mesh.primitive_cube_add(location=({x}, {y}, {z}))",
            "create_sphere": "bpy.ops.mesh.primitive_uv_sphere_add(location=({x}, {y}, {z}), radius={radius})",
            "create_cylinder": "bpy.ops.mesh.primitive_cylinder_add(location=({x}, {y}, {z}), radius={radius}, depth={depth})",
            "create_plane": "bpy.ops.mesh.primitive_plane_add(location=({x}, {y}, {z}), size={size})",
            "move_object": "bpy.context.active_object.location = ({x}, {y}, {z})",
            "rotate_object": "bpy.context.active_object.rotation_euler = ({x}, {y}, {z})",
            "scale_object": "bpy.context.active_object.scale = ({x}, {y}, {z})",
            "delete_selected": "bpy.ops.object.delete()",
            "duplicate": "bpy.ops.object.duplicate()",
            "select_all": "bpy.ops.object.select_all(action='SELECT')",
            "deselect_all": "bpy.ops.object.select_all(action='DESELECT')",
            "set_mode": "bpy.ops.object.mode_set(mode='{mode}')",
            "add_modifier": "bpy.context.active_object.modifiers.new(name='{name}', type='{type}')",
            "apply_modifier": "bpy.ops.object.modifier_apply(modifier='{name}')",
            "add_material": """
mat = bpy.data.materials.new(name='{name}')
mat.use_nodes = True
bpy.context.active_object.data.materials.append(mat)
            """,
            "set_material_color": """
mat = bpy.data.materials['{material_name}']
mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = ({r}, {g}, {b}, 1.0)
            """
        }
    
    def _validate_command(self, command: str) -> Dict[str, Any]:
        """コマンドの安全性を検証"""
        validation = {"is_valid": True, "error": None}
        
        # 危険なキーワードのチェック
        dangerous_keywords = [
            "import os",
            "import sys", 
            "__import__",
            "eval",
            "exec",
            "open(",
            "file(",
            "input(",
            "raw_input",
            "compile"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in command:
                validation["is_valid"] = False
                validation["error"] = f"危険なキーワードが含まれています: {keyword}"
                return validation
        
        # 構文チェック
        try:
            ast.parse(command)
        except SyntaxError as e:
            validation["is_valid"] = False
            validation["error"] = f"構文エラー: {e}"
        
        return validation
    
    def _preprocess_command(self, command: str, context: Optional[Dict] = None) -> str:
        """コマンドの前処理"""
        processed = command
        
        # コンテキストに基づく置換
        if context:
            active_object = context.get("active_object")
            if active_object and "active_object" in command:
                processed = processed.replace("active_object", f"'{active_object['id']}'")
        
        # 結果を取得するためのラッパー
        if not processed.strip().startswith("__result__"):
            lines = processed.strip().split('\n')
            if len(lines) == 1 and '=' not in lines[0]:
                processed = f"__result__ = {processed}"
        
        return processed
    
    def _prepare_namespace(self) -> Dict[str, Any]:
        """実行環境の名前空間を準備"""
        namespace = {
            "bpy": bpy,
            "__result__": None,
            "Vector": None,
            "Quaternion": None,
            "Matrix": None
        }
        
        # mathutilsをインポート
        try:
            from mathutils import Vector, Quaternion, Matrix
            namespace.update({
                "Vector": Vector,
                "Quaternion": Quaternion,
                "Matrix": Matrix
            })
        except ImportError:
            pass
        
        return namespace
    
    def _handle_error(self, error: Exception, command: str, context: Optional[Dict]) -> Dict[str, Any]:
        """エラーの詳細情報を生成"""
        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "command": command,
            "traceback": traceback.format_exc(),
            "context": context,
            "suggestion": self._suggest_fix(error, command, context)
        }
        
        return error_info
    
    def _suggest_fix(self, error: Exception, command: str, context: Optional[Dict]) -> Optional[str]:
        """エラーに基づいて修正案を提示"""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        suggestions = {
            "AttributeError": {
                "'nonetype' object has no attribute": "オブジェクトが選択されていません。先にオブジェクトを選択してください。",
                "object has no attribute": "指定された属性が存在しません。属性名を確認してください。"
            },
            "TypeError": {
                "expected float": "数値が必要な場所に文字列が使用されています。",
                "missing required positional argument": "必要な引数が不足しています。"
            },
            "ValueError": {
                "invalid value": "無効な値が指定されています。",
                "out of range": "値が有効な範囲外です。"
            },
            "RuntimeError": {
                "context is incorrect": "現在のコンテキストでは実行できません。モードを変更してください。"
            }
        }
        
        # エラータイプ別の提案
        if error_type in suggestions:
            for pattern, suggestion in suggestions[error_type].items():
                if pattern in error_msg:
                    return suggestion
        
        # 一般的な提案
        return "エラーが発生しました。コマンドの構文と引数を確認してください。"
    
    def _learn_error_pattern(self, error: Exception, command: str, context: Optional[Dict]):
        """エラーパターンを学習して将来の予防に活用"""
        error_key = f"{type(error).__name__}:{str(error)[:50]}"
        
        if error_key not in self.error_patterns:
            self.error_patterns[error_key] = {
                "count": 0,
                "commands": [],
                "contexts": [],
                "first_seen": datetime.now().isoformat()
            }
        
        pattern = self.error_patterns[error_key]
        pattern["count"] += 1
        pattern["commands"].append(command)
        if context:
            pattern["contexts"].append(context)
        pattern["last_seen"] = datetime.now().isoformat()
        
        # 頻出エラーの警告
        if pattern["count"] % 5 == 0:
            logger.warning(f"頻出エラー検出: {error_key} ({pattern['count']}回)")
    
    def _record_execution(self, result: Dict[str, Any]):
        """実行履歴を記録"""
        self.execution_history.append(result)
        
        # 履歴は最新1000件に制限
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """実行統計を取得"""
        if not self.execution_history:
            return {"total": 0, "successful": 0, "failed": 0}
        
        total = len(self.execution_history)
        successful = sum(1 for h in self.execution_history if h["success"])
        failed = total - successful
        
        avg_time = sum(h["execution_time"] for h in self.execution_history) / total
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "average_execution_time": avg_time,
            "error_patterns": len(self.error_patterns),
            "frequent_errors": [
                {"error": k, "count": v["count"]} 
                for k, v in sorted(
                    self.error_patterns.items(), 
                    key=lambda x: x[1]["count"], 
                    reverse=True
                )[:5]
            ]
        }
    
    def can_undo(self) -> bool:
        """アンドゥが可能かどうか"""
        return len(self.execution_history) > 0
    
    def undo_last_command(self) -> bool:
        """最後のコマンドをアンドゥ"""
        try:
            bpy.ops.ed.undo()
            return True
        except Exception as e:
            logger.error(f"アンドゥエラー: {e}")
            return False

# グローバルインスタンス
_executor = None

def get_command_executor() -> CommandExecutor:
    """コマンドエグゼキューターのシングルトンインスタンスを取得"""
    global _executor
    if _executor is None:
        _executor = CommandExecutor()
    return _executor