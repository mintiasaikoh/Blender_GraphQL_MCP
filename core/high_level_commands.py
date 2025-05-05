"""
High Level Commands Module - 高レベル操作コマンド実装
"""

import bpy
import math
import logging
import mathutils
from typing import Dict, List, Any, Optional, Union, Tuple

# ロギング設定
logger = logging.getLogger(__name__)

def handle_boolean_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ブーリアン操作コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "boolean",
                "target": "対象オブジェクト名",
                "tool": "ツールオブジェクト名",
                "operation": "UNION|DIFFERENCE|INTERSECT",
                "solver": "FAST|EXACT" (オプション),
                "keep_tool": true|false (オプション)
            }
        
    Returns:
        Dict: 実行結果
    """
    # 必須パラメータの確認
    target_name = data.get("target")
    tool_name = data.get("tool")
    operation = data.get("operation")
    
    if not target_name:
        return {
            "status": "error",
            "message": "Missing 'target' parameter for boolean command",
            "details": {
                "required_parameters": ["target"]
            }
        }
    
    if not tool_name:
        return {
            "status": "error",
            "message": "Missing 'tool' parameter for boolean command",
            "details": {
                "required_parameters": ["tool"]
            }
        }
    
    if not operation:
        return {
            "status": "error",
            "message": "Missing 'operation' parameter for boolean command",
            "details": {
                "required_parameters": ["operation"],
                "available_operations": ["UNION", "DIFFERENCE", "INTERSECT"]
            }
        }
    
    # オプションパラメータ
    solver = data.get("solver", "EXACT").upper()
    keep_tool = data.get("keep_tool", False)
    
    # ターゲットオブジェクトの取得
    target_obj = bpy.data.objects.get(target_name)
    tool_obj = bpy.data.objects.get(tool_name)
    
    if not target_obj:
        return {
            "status": "error",
            "message": f"Target object not found: {target_name}",
            "details": {
                "available_objects": [o.name for o in bpy.data.objects]
            }
        }
    
    if not tool_obj:
        return {
            "status": "error",
            "message": f"Tool object not found: {tool_name}",
            "details": {
                "available_objects": [o.name for o in bpy.data.objects]
            }
        }
    
    # 操作の検証
    valid_operations = ["UNION", "DIFFERENCE", "INTERSECT"]
    operation = operation.upper()
    
    if operation not in valid_operations:
        return {
            "status": "error",
            "message": f"Invalid boolean operation: {operation}",
            "details": {
                "available_operations": valid_operations
            }
        }
    
    # ソルバーの検証
    valid_solvers = ["FAST", "EXACT"]
    solver = solver.upper()
    
    if solver not in valid_solvers:
        return {
            "status": "error",
            "message": f"Invalid boolean solver: {solver}",
            "details": {
                "available_solvers": valid_solvers
            }
        }
    
    try:
        # 対象オブジェクトを選択してアクティブに設定
        bpy.ops.object.select_all(action='DESELECT')
        target_obj.select_set(True)
        bpy.context.view_layer.objects.active = target_obj
        
        # ブーリアンモディファイアを追加
        boolean_mod = target_obj.modifiers.new(name="Boolean", type='BOOLEAN')
        boolean_mod.operation = operation
        boolean_mod.solver = solver
        boolean_mod.object = tool_obj
        
        # モディファイアを適用
        bpy.ops.object.modifier_apply(modifier=boolean_mod.name)
        
        # ツールオブジェクトを削除（オプション）
        if not keep_tool:
            bpy.data.objects.remove(tool_obj)
        
        return {
            "status": "success",
            "message": f"Applied boolean operation: {operation}",
            "details": {
                "target": target_name,
                "tool": tool_name,
                "operation": operation,
                "solver": solver,
                "tool_kept": keep_tool
            }
        }
    except Exception as e:
        logger.error(f"Error applying boolean operation: {str(e)}")
        return {
            "status": "error",
            "message": f"Boolean operation failed: {str(e)}",
            "details": {
                "target": target_name,
                "tool": tool_name,
                "operation": operation,
                "exception": str(e)
            }
        }

def handle_array_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    配列モディファイアコマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "array",
                "target": "対象オブジェクト名",
                "count": 整数,
                "relative_offset": [x, y, z] (オプション),
                "constant_offset": [x, y, z] (オプション),
                "use_relative": true|false (オプション),
                "use_constant": true|false (オプション),
                "merge": true|false (オプション),
                "apply": true|false (オプション)
            }
        
    Returns:
        Dict: 実行結果
    """
    # 必須パラメータの確認
    target_name = data.get("target")
    count = data.get("count")
    
    if not target_name:
        return {
            "status": "error",
            "message": "Missing 'target' parameter for array command",
            "details": {
                "required_parameters": ["target"]
            }
        }
    
    if not count:
        return {
            "status": "error",
            "message": "Missing 'count' parameter for array command",
            "details": {
                "required_parameters": ["count"]
            }
        }
    
    # ターゲットオブジェクトの取得
    target_obj = bpy.data.objects.get(target_name)
    
    if not target_obj:
        return {
            "status": "error",
            "message": f"Target object not found: {target_name}",
            "details": {
                "available_objects": [o.name for o in bpy.data.objects]
            }
        }
    
    # オプションパラメータ
    relative_offset = data.get("relative_offset", [1.0, 0.0, 0.0])
    constant_offset = data.get("constant_offset", [0.0, 0.0, 0.0])
    use_relative = data.get("use_relative", True)
    use_constant = data.get("use_constant", False)
    merge = data.get("merge", False)
    apply = data.get("apply", False)
    
    try:
        # 対象オブジェクトを選択してアクティブに設定
        bpy.ops.object.select_all(action='DESELECT')
        target_obj.select_set(True)
        bpy.context.view_layer.objects.active = target_obj
        
        # 配列モディファイアを追加
        array_mod = target_obj.modifiers.new(name="Array", type='ARRAY')
        array_mod.count = count
        
        # 相対オフセットの設定
        if use_relative:
            array_mod.use_relative_offset = True
            for i in range(min(3, len(relative_offset))):
                array_mod.relative_offset_displace[i] = relative_offset[i]
        else:
            array_mod.use_relative_offset = False
        
        # 固定オフセットの設定
        if use_constant:
            array_mod.use_constant_offset = True
            for i in range(min(3, len(constant_offset))):
                array_mod.constant_offset_displace[i] = constant_offset[i]
        else:
            array_mod.use_constant_offset = False
        
        # マージの設定
        array_mod.use_merge_vertices = merge
        
        # モディファイアを適用（オプション）
        if apply:
            bpy.ops.object.modifier_apply(modifier=array_mod.name)
            modifier_applied = True
        else:
            modifier_applied = False
        
        return {
            "status": "success",
            "message": f"Applied array modifier with count: {count}",
            "details": {
                "target": target_name,
                "count": count,
                "use_relative": use_relative,
                "use_constant": use_constant,
                "merge": merge,
                "modifier_applied": modifier_applied
            }
        }
    except Exception as e:
        logger.error(f"Error applying array modifier: {str(e)}")
        return {
            "status": "error",
            "message": f"Array operation failed: {str(e)}",
            "details": {
                "target": target_name,
                "count": count,
                "exception": str(e)
            }
        }

def handle_mirror_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ミラーモディファイアコマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "mirror",
                "target": "対象オブジェクト名",
                "axes": ["X", "Y", "Z"] (オプション),
                "mirror_object": "ミラーオブジェクト名" (オプション),
                "merge": true|false (オプション),
                "apply": true|false (オプション)
            }
        
    Returns:
        Dict: 実行結果
    """
    # 必須パラメータの確認
    target_name = data.get("target")
    
    if not target_name:
        return {
            "status": "error",
            "message": "Missing 'target' parameter for mirror command",
            "details": {
                "required_parameters": ["target"]
            }
        }
    
    # ターゲットオブジェクトの取得
    target_obj = bpy.data.objects.get(target_name)
    
    if not target_obj:
        return {
            "status": "error",
            "message": f"Target object not found: {target_name}",
            "details": {
                "available_objects": [o.name for o in bpy.data.objects]
            }
        }
    
    # オプションパラメータ
    axes = data.get("axes", ["X"])
    mirror_object_name = data.get("mirror_object")
    merge = data.get("merge", True)
    apply = data.get("apply", False)
    
    # ミラーオブジェクトの取得（指定されている場合）
    mirror_object = None
    if mirror_object_name:
        mirror_object = bpy.data.objects.get(mirror_object_name)
        if not mirror_object:
            return {
                "status": "error",
                "message": f"Mirror object not found: {mirror_object_name}",
                "details": {
                    "available_objects": [o.name for o in bpy.data.objects]
                }
            }
    
    try:
        # 対象オブジェクトを選択してアクティブに設定
        bpy.ops.object.select_all(action='DESELECT')
        target_obj.select_set(True)
        bpy.context.view_layer.objects.active = target_obj
        
        # ミラーモディファイアを追加
        mirror_mod = target_obj.modifiers.new(name="Mirror", type='MIRROR')
        
        # 軸の設定
        mirror_mod.use_axis[0] = "X" in axes
        mirror_mod.use_axis[1] = "Y" in axes
        mirror_mod.use_axis[2] = "Z" in axes
        
        # ミラーオブジェクトの設定
        if mirror_object:
            mirror_mod.mirror_object = mirror_object
        
        # マージの設定
        mirror_mod.use_clip = merge
        
        # モディファイアを適用（オプション）
        if apply:
            bpy.ops.object.modifier_apply(modifier=mirror_mod.name)
            modifier_applied = True
        else:
            modifier_applied = False
        
        return {
            "status": "success",
            "message": f"Applied mirror modifier on axes: {', '.join(axes)}",
            "details": {
                "target": target_name,
                "axes": axes,
                "mirror_object": mirror_object_name if mirror_object else None,
                "merge": merge,
                "modifier_applied": modifier_applied
            }
        }
    except Exception as e:
        logger.error(f"Error applying mirror modifier: {str(e)}")
        return {
            "status": "error",
            "message": f"Mirror operation failed: {str(e)}",
            "details": {
                "target": target_name,
                "axes": axes,
                "exception": str(e)
            }
        }

def handle_extrude_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    押し出し操作コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "extrude",
                "target": "対象オブジェクト名",
                "direction": [x, y, z],
                "amount": 浮動小数点数,
                "selection": "vertex|edge|face" (オプション),
                "select_all": true|false (オプション)
            }
        
    Returns:
        Dict: 実行結果
    """
    # 必須パラメータの確認
    target_name = data.get("target")
    direction = data.get("direction")
    amount = data.get("amount")
    
    if not target_name:
        return {
            "status": "error",
            "message": "Missing 'target' parameter for extrude command",
            "details": {
                "required_parameters": ["target"]
            }
        }
    
    if not direction:
        return {
            "status": "error",
            "message": "Missing 'direction' parameter for extrude command",
            "details": {
                "required_parameters": ["direction"]
            }
        }
    
    if amount is None:
        return {
            "status": "error",
            "message": "Missing 'amount' parameter for extrude command",
            "details": {
                "required_parameters": ["amount"]
            }
        }
    
    # ターゲットオブジェクトの取得
    target_obj = bpy.data.objects.get(target_name)
    
    if not target_obj:
        return {
            "status": "error",
            "message": f"Target object not found: {target_name}",
            "details": {
                "available_objects": [o.name for o in bpy.data.objects]
            }
        }
    
    # メッシュオブジェクトでない場合はエラー
    if target_obj.type != 'MESH':
        return {
            "status": "error",
            "message": f"Object is not a mesh: {target_name}",
            "details": {
                "object_type": target_obj.type
            }
        }
    
    # オプションパラメータ
    selection_type = data.get("selection", "face").lower()
    select_all = data.get("select_all", True)
    
    # 選択タイプの検証
    valid_selection_types = ["vertex", "edge", "face"]
    if selection_type not in valid_selection_types:
        return {
            "status": "error",
            "message": f"Invalid selection type: {selection_type}",
            "details": {
                "available_types": valid_selection_types
            }
        }
    
    try:
        # 対象オブジェクトを選択してアクティブに設定
        bpy.ops.object.select_all(action='DESELECT')
        target_obj.select_set(True)
        bpy.context.view_layer.objects.active = target_obj
        
        # 編集モードに入る
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 選択タイプを設定
        if selection_type == "vertex":
            bpy.ops.mesh.select_mode(type='VERT')
        elif selection_type == "edge":
            bpy.ops.mesh.select_mode(type='EDGE')
        else:  # face
            bpy.ops.mesh.select_mode(type='FACE')
        
        # すべての要素を選択または選択解除
        if select_all:
            bpy.ops.mesh.select_all(action='SELECT')
        else:
            bpy.ops.mesh.select_all(action='DESELECT')
        
        # 方向ベクトルを正規化して距離を設定
        dir_vector = mathutils.Vector(direction).normalized()
        dir_vector *= amount
        
        # 押し出し操作を実行
        bpy.ops.mesh.extrude_region_move(
            TRANSFORM_OT_translate={
                "value": (dir_vector.x, dir_vector.y, dir_vector.z)
            }
        )
        
        # オブジェクトモードに戻る
        bpy.ops.object.mode_set(mode='OBJECT')
        
        return {
            "status": "success",
            "message": f"Extruded {selection_type}(s) by {amount} units",
            "details": {
                "target": target_name,
                "selection_type": selection_type,
                "direction": [round(v, 6) for v in direction],
                "amount": amount,
                "selected_all": select_all
            }
        }
    except Exception as e:
        # エラー時はオブジェクトモードに戻す
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        
        logger.error(f"Error extruding {selection_type}(s): {str(e)}")
        return {
            "status": "error",
            "message": f"Extrude operation failed: {str(e)}",
            "details": {
                "target": target_name,
                "selection_type": selection_type,
                "exception": str(e)
            }
        }

def handle_subdivide_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    サブディビジョンモディファイアコマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "subdivide",
                "target": "対象オブジェクト名",
                "levels": 整数 (オプション),
                "catmull_clark": true|false (オプション),
                "simple": true|false (オプション),
                "apply": true|false (オプション)
            }
        
    Returns:
        Dict: 実行結果
    """
    # 必須パラメータの確認
    target_name = data.get("target")
    
    if not target_name:
        return {
            "status": "error",
            "message": "Missing 'target' parameter for subdivide command",
            "details": {
                "required_parameters": ["target"]
            }
        }
    
    # ターゲットオブジェクトの取得
    target_obj = bpy.data.objects.get(target_name)
    
    if not target_obj:
        return {
            "status": "error",
            "message": f"Target object not found: {target_name}",
            "details": {
                "available_objects": [o.name for o in bpy.data.objects]
            }
        }
    
    # メッシュオブジェクトでない場合はエラー
    if target_obj.type != 'MESH':
        return {
            "status": "error",
            "message": f"Object is not a mesh: {target_name}",
            "details": {
                "object_type": target_obj.type
            }
        }
    
    # オプションパラメータ
    levels = data.get("levels", 1)
    catmull_clark = data.get("catmull_clark", True)
    simple = data.get("simple", False)
    apply = data.get("apply", False)
    
    # サブディビジョンタイプの設定
    subdivision_type = 'CATMULL_CLARK' if catmull_clark else 'SIMPLE'
    
    try:
        # 対象オブジェクトを選択してアクティブに設定
        bpy.ops.object.select_all(action='DESELECT')
        target_obj.select_set(True)
        bpy.context.view_layer.objects.active = target_obj
        
        # サブディビジョンモディファイアを追加
        subdiv_mod = target_obj.modifiers.new(name="Subdivision", type='SUBSURF')
        subdiv_mod.levels = levels
        subdiv_mod.subdivision_type = subdivision_type
        
        # モディファイアを適用（オプション）
        if apply:
            bpy.ops.object.modifier_apply(modifier=subdiv_mod.name)
            modifier_applied = True
        else:
            modifier_applied = False
        
        return {
            "status": "success",
            "message": f"Applied subdivision modifier with {levels} level(s)",
            "details": {
                "target": target_name,
                "levels": levels,
                "subdivision_type": subdivision_type,
                "modifier_applied": modifier_applied
            }
        }
    except Exception as e:
        logger.error(f"Error applying subdivision modifier: {str(e)}")
        return {
            "status": "error",
            "message": f"Subdivision operation failed: {str(e)}",
            "details": {
                "target": target_name,
                "levels": levels,
                "exception": str(e)
            }
        }

# サーバーへの関数登録
def register_high_level_commands_to_server():
    """
    高レベル操作コマンド関数をHTTPサーバーに登録
    """
    try:
        # パッケージ情報を取得
        import os
        import importlib
        import sys
        
        # 現在のモジュールのパスからパッケージ名を取得
        current_dir = os.path.dirname(os.path.abspath(__file__))
        addon_dir = os.path.dirname(current_dir)
        package_name = os.path.basename(addon_dir)
        
        # HTTPサーバーモジュールのインポート
        http_server_module = importlib.import_module(f'{package_name}.core.http_server')
        MCPHttpServer = getattr(http_server_module, 'MCPHttpServer')
        
        # サーバーインスタンスの取得
        server = MCPHttpServer.get_instance()
        
        # ブーリアン操作コマンドの登録
        server.register_function(
            handle_boolean_command,
            "boolean",
            examples=[
                {
                    "command": "boolean",
                    "target": "Cube",
                    "tool": "Sphere",
                    "operation": "DIFFERENCE"
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["boolean"]},
                    "target": {"type": "string"},
                    "tool": {"type": "string"},
                    "operation": {"type": "string", "enum": ["UNION", "DIFFERENCE", "INTERSECT"]}
                },
                "required": ["command", "target", "tool", "operation"]
            }
        )
        
        # 配列操作コマンドの登録
        server.register_function(
            handle_array_command,
            "array",
            examples=[
                {
                    "command": "array",
                    "target": "Cube",
                    "count": 3,
                    "relative_offset": [1.5, 0, 0]
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["array"]},
                    "target": {"type": "string"},
                    "count": {"type": "integer", "minimum": 1}
                },
                "required": ["command", "target", "count"]
            }
        )
        
        # ミラー操作コマンドの登録
        server.register_function(
            handle_mirror_command,
            "mirror",
            examples=[
                {
                    "command": "mirror",
                    "target": "Cube",
                    "axes": ["X", "Y"]
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["mirror"]},
                    "target": {"type": "string"},
                    "axes": {"type": "array", "items": {"type": "string", "enum": ["X", "Y", "Z"]}}
                },
                "required": ["command", "target"]
            }
        )
        
        # 押し出し操作コマンドの登録
        server.register_function(
            handle_extrude_command,
            "extrude",
            examples=[
                {
                    "command": "extrude",
                    "target": "Cube",
                    "direction": [0, 0, 1],
                    "amount": 2.0
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["extrude"]},
                    "target": {"type": "string"},
                    "direction": {"type": "array", "items": {"type": "number"}},
                    "amount": {"type": "number", "minimum": 0}
                },
                "required": ["command", "target", "direction", "amount"]
            }
        )
        
        # サブディビジョン操作コマンドの登録
        server.register_function(
            handle_subdivide_command,
            "subdivide",
            examples=[
                {
                    "command": "subdivide",
                    "target": "Cube",
                    "levels": 2
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["subdivide"]},
                    "target": {"type": "string"},
                    "levels": {"type": "integer", "minimum": 1}
                },
                "required": ["command", "target"]
            }
        )
        
        logger.info("高レベル操作コマンド関数がHTTPサーバーに登録されました")
        return True
        
    except Exception as e:
        logger.error(f"高レベル操作コマンド関数の登録に失敗: {str(e)}")
        return False
