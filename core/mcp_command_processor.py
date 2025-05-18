"""
MCP Command Processor
MCPクライアント（LLM）からのコマンドを処理するモジュール
"""

import logging
import json
import bpy
from typing import Dict, Any, List, Optional
from datetime import datetime

from .blender_context import get_context_manager
from .command_executor import get_command_executor
from .preview_generator import get_preview_generator

logger = logging.getLogger('blender_mcp.command_processor')

class MCPCommandProcessor:
    """MCPコマンドプロセッサー - LLMからのコマンドを処理"""
    
    def __init__(self):
        self.context_manager = get_context_manager()
        self.command_executor = get_command_executor()
        self.preview_generator = get_preview_generator()
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def process_raw_command(self, python_code: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        LLMが生成したPythonコードを直接実行
        
        Args:
            python_code: 実行するPythonコード
            metadata: 追加のメタデータ（LLMからの情報）
            
        Returns:
            実行結果
        """
        result = {
            "success": False,
            "executed_code": python_code,
            "result": None,
            "error": None,
            "context_before": None,
            "context_after": None,
            "preview": None,
            "suggestions": [],
            "metadata": metadata or {}
        }
        
        try:
            # 実行前のコンテキストを取得
            result["context_before"] = self.context_manager.get_complete_context()
            
            # Pythonコードを実行
            execution_result = self.command_executor.execute_command(
                python_code, 
                context=result["context_before"]
            )
            
            result["result"] = execution_result
            result["success"] = execution_result.get("success", False)
            
            if result["success"]:
                # 実行後のコンテキストを取得
                result["context_after"] = self.context_manager.get_complete_context()
                
                # プレビューを生成
                preview_result = self.preview_generator.capture_viewport()
                if preview_result["success"]:
                    result["preview"] = preview_result["preview"]
                
                # 変更を検出
                result["changes"] = self._detect_changes(
                    result["context_before"], 
                    result["context_after"]
                )
                
                # 次のアクション候補を提示
                result["suggestions"] = self.context_manager.suggest_next_actions()
            else:
                result["error"] = execution_result.get("error", "Unknown error")
                result["error_details"] = execution_result.get("error_details", {})
                
                # エラーに基づく提案
                result["suggestions"] = self._generate_error_recovery_suggestions(
                    result["error_details"]
                )
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"コマンド処理エラー: {e}")
            
        return result
    
    def get_available_operations(self, context_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        現在のコンテキストで利用可能な操作を返す
        
        Args:
            context_filter: 特定のコンテキストでフィルタリング
            
        Returns:
            利用可能な操作のリスト
        """
        operations = []
        current_context = self.context_manager.get_complete_context()
        mode = current_context.get("mode", "OBJECT")
        
        # モード別の操作
        if mode == "OBJECT":
            operations.extend([
                {
                    "id": "create_primitive",
                    "description": "プリミティブオブジェクトを作成",
                    "example_code": "bpy.ops.mesh.primitive_cube_add()",
                    "parameters": ["type", "location", "size"]
                },
                {
                    "id": "transform",
                    "description": "オブジェクトを変形（移動/回転/スケール）",
                    "example_code": "bpy.context.active_object.location = (1, 0, 0)",
                    "parameters": ["transform_type", "values"]
                },
                {
                    "id": "apply_material",
                    "description": "マテリアルを適用",
                    "example_code": "mat = bpy.data.materials.new('Material')",
                    "parameters": ["color", "roughness", "metallic"]
                }
            ])
        elif mode == "EDIT":
            operations.extend([
                {
                    "id": "extrude",
                    "description": "面を押し出し",
                    "example_code": "bpy.ops.mesh.extrude_region_move()",
                    "parameters": ["direction", "distance"]
                },
                {
                    "id": "subdivide",
                    "description": "メッシュを細分化",
                    "example_code": "bpy.ops.mesh.subdivide()",
                    "parameters": ["cuts"]
                }
            ])
        
        # 共通操作
        operations.extend([
            {
                "id": "select",
                "description": "オブジェクトを選択",
                "example_code": "bpy.data.objects['Object'].select_set(True)",
                "parameters": ["object_name"]
            },
            {
                "id": "delete",
                "description": "選択オブジェクトを削除",
                "example_code": "bpy.ops.object.delete()",
                "parameters": []
            },
            {
                "id": "set_mode",
                "description": "モードを変更",
                "example_code": "bpy.ops.object.mode_set(mode='EDIT')",
                "parameters": ["mode"]
            }
        ])
        
        return operations
    
    def get_object_properties(self, object_id: str) -> Dict[str, Any]:
        """
        特定のオブジェクトのプロパティを取得
        
        Args:
            object_id: オブジェクトのID/名前
            
        Returns:
            オブジェクトのプロパティ
        """
        try:
            obj = bpy.data.objects.get(object_id)
            if not obj:
                return {"error": f"Object '{object_id}' not found"}
            
            properties = {
                "id": obj.name,
                "type": obj.type,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "scale": list(obj.scale),
                "dimensions": list(obj.dimensions),
                "visible": obj.visible_get(),
                "selected": obj.select_get(),
                "parent": obj.parent.name if obj.parent else None,
                "children": [child.name for child in obj.children],
                "modifiers": [mod.name for mod in obj.modifiers],
                "materials": []
            }
            
            # マテリアル情報
            if hasattr(obj.data, 'materials'):
                for mat in obj.data.materials:
                    if mat:
                        mat_info = {
                            "name": mat.name,
                            "use_nodes": mat.use_nodes
                        }
                        if mat.use_nodes:
                            bsdf = mat.node_tree.nodes.get("Principled BSDF")
                            if bsdf:
                                mat_info["base_color"] = list(bsdf.inputs[0].default_value)[:3]
                                mat_info["metallic"] = bsdf.inputs[4].default_value
                                mat_info["roughness"] = bsdf.inputs[7].default_value
                        properties["materials"].append(mat_info)
            
            # メッシュ情報
            if obj.type == 'MESH' and obj.data:
                properties["mesh"] = {
                    "vertices": len(obj.data.vertices),
                    "edges": len(obj.data.edges),
                    "faces": len(obj.data.polygons)
                }
            
            return properties
            
        except Exception as e:
            logger.error(f"プロパティ取得エラー: {e}")
            return {"error": str(e)}
    
    def create_checkpoint(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        現在の状態のチェックポイントを作成
        
        Args:
            name: チェックポイント名
            description: 説明
            
        Returns:
            チェックポイント情報
        """
        try:
            checkpoint = {
                "id": f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "name": name,
                "description": description,
                "timestamp": datetime.now().isoformat(),
                "context": self.context_manager.get_complete_context(),
                "preview": None
            }
            
            # プレビューを生成
            preview_result = self.preview_generator.capture_viewport()
            if preview_result["success"]:
                checkpoint["preview"] = preview_result["preview"]
            
            # .blendファイルとして保存（オプション）
            # bpy.ops.wm.save_as_mainfile(filepath=f"{checkpoint['id']}.blend")
            
            return checkpoint
            
        except Exception as e:
            logger.error(f"チェックポイント作成エラー: {e}")
            return {"error": str(e)}
    
    def _detect_changes(self, before: Dict[str, Any], after: Dict[str, Any]) -> List[Dict[str, Any]]:
        """コンテキストの変更を検出"""
        changes = []
        
        # オブジェクト数の変化
        before_objects = set(obj["id"] for obj in before.get("selected_objects", []))
        after_objects = set(obj["id"] for obj in after.get("selected_objects", []))
        
        added = after_objects - before_objects
        removed = before_objects - after_objects
        
        for obj_id in added:
            changes.append({
                "type": "object_added",
                "object_id": obj_id,
                "description": f"新しいオブジェクト '{obj_id}' が追加されました"
            })
        
        for obj_id in removed:
            changes.append({
                "type": "object_removed",
                "object_id": obj_id,
                "description": f"オブジェクト '{obj_id}' が削除されました"
            })
        
        # 位置の変化などをチェック
        for obj_id in before_objects & after_objects:
            before_obj = next((o for o in before["selected_objects"] if o["id"] == obj_id), None)
            after_obj = next((o for o in after["selected_objects"] if o["id"] == obj_id), None)
            
            if before_obj and after_obj:
                if before_obj.get("location") != after_obj.get("location"):
                    changes.append({
                        "type": "object_moved",
                        "object_id": obj_id,
                        "description": f"オブジェクト '{obj_id}' が移動しました"
                    })
        
        return changes
    
    def _generate_error_recovery_suggestions(self, error_details: Dict[str, Any]) -> List[str]:
        """エラーからのリカバリー提案を生成"""
        suggestions = []
        error_type = error_details.get("type", "")
        error_message = error_details.get("message", "")
        
        if error_type == "AttributeError":
            if "NoneType" in error_message:
                suggestions.append("オブジェクトが選択されていません。先にオブジェクトを選択してください。")
                suggestions.append("bpy.context.view_layer.objects.active = bpy.data.objects['ObjectName']")
        
        elif error_type == "RuntimeError":
            if "context is incorrect" in error_message:
                suggestions.append("現在のモードが正しくありません。適切なモードに変更してください。")
                suggestions.append("bpy.ops.object.mode_set(mode='OBJECT')")
        
        # 一般的な提案
        suggestions.append("bpy.context.view_layer.update() を実行してビューレイヤーを更新")
        suggestions.append("現在のコンテキストを確認: bpy.context.mode")
        
        return suggestions

# シングルトンインスタンス
_processor = None

def get_mcp_processor() -> MCPCommandProcessor:
    """MCPコマンドプロセッサーのシングルトンインスタンスを取得"""
    global _processor
    if _processor is None:
        _processor = MCPCommandProcessor()
    return _processor