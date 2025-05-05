"""
ブーリアン操作コマンドモジュール
メッシュのブーリアン操作を実行する堅牢なコマンドを提供
"""

import bpy
import bmesh
import math
import json
from typing import Dict, List, Any, Optional, Tuple
from mathutils import Vector, Matrix

from .base import BlenderCommand, register_command
from ..validation.mesh_checker import MeshChecker
from ..validation.change_detector import ChangeDetector

class BooleanOperationCommand(BlenderCommand):
    """
    ブーリアン操作を実行するコマンド
    前処理での検証と自動修復オプションを含む
    """
    
    command_name = "boolean_operation"
    description = "2つのメッシュ間でブーリアン操作を実行"
    
    parameters_schema = {
        "target_object": {
            "type": "string",
            "description": "操作のターゲットとなるオブジェクト名"
        },
        "cutter_object": {
            "type": "string",
            "description": "カッターとして使用するオブジェクト名"
        },
        "operation": {
            "type": "string",
            "description": "実行するブーリアン操作のタイプ",
            "enum": ["union", "difference", "intersect"]
        },
        "auto_repair": {
            "type": "boolean",
            "description": "操作前にメッシュを自動修復するかどうか",
            "default": True
        },
        "validate_result": {
            "type": "boolean",
            "description": "操作後に結果を検証するかどうか",
            "default": True
        },
        "delete_cutter": {
            "type": "boolean",
            "description": "操作後にカッターオブジェクトを削除するかどうか",
            "default": False
        },
        "solver": {
            "type": "string",
            "description": "使用するブーリアンソルバー",
            "enum": ["fast", "exact"],
            "default": "exact"
        }
    }
    
    def validate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """パラメータのバリデーション"""
        errors = []
        
        # 必須パラメータのチェック
        if "target_object" not in params:
            errors.append("target_object パラメータが必要です")
        elif not bpy.data.objects.get(params["target_object"]):
            errors.append(f"ターゲットオブジェクト '{params['target_object']}' が見つかりません")
        
        if "cutter_object" not in params:
            errors.append("cutter_object パラメータが必要です")
        elif not bpy.data.objects.get(params["cutter_object"]):
            errors.append(f"カッターオブジェクト '{params['cutter_object']}' が見つかりません")
        
        # オブジェクトタイプのチェック
        if "target_object" in params and bpy.data.objects.get(params["target_object"]):
            if bpy.data.objects[params["target_object"]].type != 'MESH':
                errors.append(f"ターゲットオブジェクト '{params['target_object']}' はメッシュである必要があります")
        
        if "cutter_object" in params and bpy.data.objects.get(params["cutter_object"]):
            if bpy.data.objects[params["cutter_object"]].type != 'MESH':
                errors.append(f"カッターオブジェクト '{params['cutter_object']}' はメッシュである必要があります")
        
        # 操作タイプのチェック
        if "operation" not in params:
            errors.append("operation パラメータが必要です")
        elif params["operation"] not in ["union", "difference", "intersect"]:
            errors.append(f"無効な操作タイプ: {params['operation']}。'union', 'difference', 'intersect' のいずれかである必要があります")
        
        # ソルバーのチェック
        if "solver" in params and params["solver"] not in ["fast", "exact"]:
            errors.append(f"無効なソルバー: {params['solver']}。'fast' または 'exact' である必要があります")
        
        # 同一オブジェクトのチェック
        if ("target_object" in params and "cutter_object" in params and
            params["target_object"] == params["cutter_object"]):
            errors.append("ターゲットとカッターは異なるオブジェクトである必要があります")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def pre_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """実行前処理"""
        target_name = params["target_object"]
        cutter_name = params["cutter_object"]
        auto_repair = params.get("auto_repair", True)
        
        # 操作前の状態をキャプチャ
        before_state = ChangeDetector.capture_state("standard")
        
        # メッシュの検証
        target_check = MeshChecker.check_mesh(target_name)
        cutter_check = MeshChecker.check_mesh(cutter_name)
        
        # 交差チェック
        boolean_check = MeshChecker.check_boolean_operation(target_name, cutter_name)
        
        # 自動修復
        target_repair_result = None
        cutter_repair_result = None
        
        if auto_repair:
            # ターゲットメッシュの修復が必要な場合
            if not target_check.get("boolean_ready", False):
                target_repair_result = MeshChecker.repair_mesh(target_name)
            
            # カッターメッシュの修復が必要な場合
            if not cutter_check.get("boolean_ready", False):
                cutter_repair_result = MeshChecker.repair_mesh(cutter_name)
        
        # 前処理の結果をまとめる
        return {
            "before_state": before_state,
            "mesh_checks": {
                "target": target_check,
                "cutter": cutter_check,
                "boolean_check": boolean_check
            },
            "repairs": {
                "target_repaired": target_repair_result,
                "cutter_repaired": cutter_repair_result
            }
        }
    
    def execute(self, params: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """コマンド実行"""
        target_name = params["target_object"]
        cutter_name = params["cutter_object"]
        operation = params["operation"]
        delete_cutter = params.get("delete_cutter", False)
        solver = params.get("solver", "exact")
        
        # オブジェクトの取得
        target = bpy.data.objects.get(target_name)
        cutter = bpy.data.objects.get(cutter_name)
        
        if not target or not cutter:
            return {
                "success": False,
                "error": "ターゲットまたはカッターオブジェクトが見つかりません"
            }
        
        # 元の選択状態とアクティブオブジェクトを保存
        original_selection = [obj.name for obj in bpy.context.selected_objects]
        original_active = bpy.context.active_object
        
        try:
            # 選択をクリア
            bpy.ops.object.select_all(action='DESELECT')
            
            # ターゲットを選択してアクティブに
            target.select_set(True)
            bpy.context.view_layer.objects.active = target
            
            # ブーリアンモディファイアの作成
            boolean_mod = target.modifiers.new(name="Boolean", type='BOOLEAN')
            boolean_mod.object = cutter
            
            # 操作タイプの設定
            if operation == "union":
                boolean_mod.operation = 'UNION'
            elif operation == "difference":
                boolean_mod.operation = 'DIFFERENCE'
            elif operation == "intersect":
                boolean_mod.operation = 'INTERSECT'
            
            # ソルバーの設定
            boolean_mod.solver = 'EXACT' if solver == "exact" else 'FAST'
            
            # モディファイアの適用
            try:
                # Blender 2.90以降
                if hasattr(bpy.ops.object, 'modifier_apply'):
                    bpy.ops.object.modifier_apply(modifier=boolean_mod.name)
                # それ以前のバージョン
                else:
                    bpy.ops.object.modifier_apply(apply_as='DATA', modifier=boolean_mod.name)
                
                operation_success = True
                operation_error = None
            except Exception as e:
                operation_success = False
                operation_error = str(e)
                # エラーが発生した場合、モディファイアを削除
                target.modifiers.remove(boolean_mod)
            
            # カッターの削除（オプション）
            if delete_cutter and operation_success:
                bpy.ops.object.select_all(action='DESELECT')
                cutter.select_set(True)
                bpy.ops.object.delete()
            
            # 実行結果
            result = {
                "success": operation_success,
                "operation": operation,
                "target": target_name,
                "cutter": cutter_name
            }
            
            if not operation_success:
                result["error"] = operation_error
            
            return result
            
        finally:
            # 元の選択状態を復元
            bpy.ops.object.select_all(action='DESELECT')
            for obj_name in original_selection:
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    obj.select_set(True)
            
            if original_active:
                bpy.context.view_layer.objects.active = original_active
    
    def post_execute(self, params: Dict[str, Any], result: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """実行後処理"""
        validate_result = params.get("validate_result", True)
        
        # 操作後の状態をキャプチャ
        after_state = ChangeDetector.capture_state("standard")
        changes = ChangeDetector.compare_states(pre_state["before_state"], after_state)
        result["changes"] = changes
        
        # 操作が成功した場合のみ結果検証
        if result.get("success", False) and validate_result:
            target_name = params["target_object"]
            # ターゲットオブジェクトが存在する場合のみ検証
            if bpy.data.objects.get(target_name):
                post_check = MeshChecker.check_mesh(target_name)
                result["validation"] = {
                    "is_valid": post_check.get("valid", False),
                    "is_manifold": post_check.get("is_manifold", False),
                    "issues_count": len(post_check.get("issues", [])),
                    "quality": post_check.get("quality", "unknown")
                }
        
        # 前処理情報を追加
        result["pre_checks"] = pre_state["mesh_checks"]
        result["repairs_applied"] = pre_state["repairs"]
        
        return result


class FixBooleanIssuesCommand(BlenderCommand):
    """
    ブーリアン操作の問題を修復するコマンド
    """
    
    command_name = "fix_boolean_issues"
    description = "ブーリアン操作で問題が起きたメッシュを修復"
    
    parameters_schema = {
        "object_name": {
            "type": "string",
            "description": "修復するオブジェクト名"
        },
        "repair_options": {
            "type": "object",
            "description": "適用する修復オプション",
            "properties": {
                "remove_doubles": {
                    "type": "boolean",
                    "description": "重複頂点を削除",
                    "default": True
                },
                "recalc_normals": {
                    "type": "boolean",
                    "description": "法線を再計算",
                    "default": True
                },
                "fill_holes": {
                    "type": "boolean",
                    "description": "穴を埋める",
                    "default": True
                },
                "triangulate_ngons": {
                    "type": "boolean",
                    "description": "N-gonsを三角形化",
                    "default": False
                }
            }
        },
        "run_diagnostics": {
            "type": "boolean",
            "description": "修復前後に詳細な診断を実行",
            "default": True
        }
    }
    
    def validate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """パラメータのバリデーション"""
        errors = []
        
        # オブジェクト名のチェック
        if "object_name" not in params:
            errors.append("修復するオブジェクト名を指定してください")
        elif not bpy.data.objects.get(params["object_name"]):
            errors.append(f"オブジェクト '{params['object_name']}' が見つかりません")
        
        # オブジェクトがメッシュかどうかのチェック
        if "object_name" in params and bpy.data.objects.get(params["object_name"]):
            if bpy.data.objects[params["object_name"]].type != 'MESH':
                errors.append(f"オブジェクト '{params['object_name']}' はメッシュである必要があります")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def pre_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """実行前処理"""
        object_name = params["object_name"]
        run_diagnostics = params.get("run_diagnostics", True)
        
        pre_state = {
            "before_state": ChangeDetector.capture_state("basic")
        }
        
        # 事前診断
        if run_diagnostics:
            pre_state["diagnostics"] = MeshChecker.check_mesh(object_name)
        
        return pre_state
    
    def execute(self, params: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """コマンド実行"""
        object_name = params["object_name"]
        repair_options = params.get("repair_options", {
            "remove_doubles": True,
            "recalc_normals": True,
            "fill_holes": True,
            "triangulate_ngons": False
        })
        
        # MeshCheckerを使用して修復
        repair_result = MeshChecker.repair_mesh(object_name, repair_options)
        
        return repair_result
    
    def post_execute(self, params: Dict[str, Any], result: Dict[str, Any], pre_state: Dict[str, Any]) -> Dict[str, Any]:
        """実行後処理"""
        object_name = params["object_name"]
        run_diagnostics = params.get("run_diagnostics", True)
        
        # 操作後の状態をキャプチャ
        after_state = ChangeDetector.capture_state("basic")
        changes = ChangeDetector.compare_states(pre_state["before_state"], after_state)
        result["changes"] = changes
        
        # 事後診断
        if run_diagnostics:
            result["after_diagnostics"] = MeshChecker.check_mesh(object_name)
            
            # 診断比較
            if "diagnostics" in pre_state:
                before_issues = len(pre_state["diagnostics"].get("issues", []))
                after_issues = len(result["after_diagnostics"].get("issues", []))
                
                result["improvement"] = {
                    "issues_before": before_issues,
                    "issues_after": after_issues,
                    "issues_fixed": max(0, before_issues - after_issues),
                    "percentage_improved": round(
                        100 * (before_issues - after_issues) / before_issues 
                        if before_issues > 0 else 0, 
                        2
                    )
                }
        
        return result


# コマンドを登録
def register():
    register_command(BooleanOperationCommand)
    register_command(FixBooleanIssuesCommand)
