"""
Meta and Analysis Commands Module - メタコマンドと分析コマンド
"""

import bpy
import math
import json
import logging
import mathutils
from typing import Dict, List, Any, Optional, Union, Tuple

# ロギング設定
logger = logging.getLogger(__name__)

#-------------------------------------------------------------------------
# 分析コマンド
#-------------------------------------------------------------------------

def handle_analyze_scene_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    シーン分析コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "analyze_scene",
                "details": true|false (オプション)
            }
        
    Returns:
        Dict: 分析結果
    """
    # オプションパラメータ
    details = data.get("details", False)
    
    try:
        # アクティブシーンの取得
        scene = bpy.context.scene
        
        # 基本情報の収集
        basic_info = {
            "name": scene.name,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "fps": scene.render.fps,
            "objects_count": len(scene.objects),
            "cameras_count": len([obj for obj in scene.objects if obj.type == 'CAMERA']),
            "lights_count": len([obj for obj in scene.objects if obj.type == 'LIGHT']),
            "meshes_count": len([obj for obj in scene.objects if obj.type == 'MESH']),
            "collections_count": len(bpy.data.collections),
            "materials_count": len(bpy.data.materials),
            "active_camera": scene.camera.name if scene.camera else None
        }
        
        # 詳細情報
        if details:
            # オブジェクトリスト
            objects_info = []
            for obj in scene.objects:
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [round(v, 6) for v in obj.location],
                    "visible": not obj.hide_viewport and not obj.hide_render,
                    "parent": obj.parent.name if obj.parent else None,
                    "vertices": len(obj.data.vertices) if obj.type == 'MESH' and hasattr(obj.data, 'vertices') else None,
                    "polygons": len(obj.data.polygons) if obj.type == 'MESH' and hasattr(obj.data, 'polygons') else None,
                    "materials": [mat.name for mat in obj.data.materials] if obj.data and hasattr(obj.data, 'materials') else None
                }
                objects_info.append(obj_info)
            
            # コレクションリスト
            collections_info = []
            for coll in bpy.data.collections:
                coll_info = {
                    "name": coll.name,
                    "objects": [obj.name for obj in coll.objects]
                }
                collections_info.append(coll_info)
            
            # 材質リスト
            materials_info = []
            for mat in bpy.data.materials:
                mat_info = {
                    "name": mat.name,
                    "users": mat.users
                }
                materials_info.append(mat_info)
            
            return {
                "status": "success",
                "message": "Scene analysis completed",
                "scene": basic_info,
                "objects": objects_info,
                "collections": collections_info,
                "materials": materials_info
            }
        else:
            return {
                "status": "success",
                "message": "Scene analysis completed",
                "scene": basic_info
            }
    except Exception as e:
        logger.error(f"Error analyzing scene: {str(e)}")
        return {
            "status": "error",
            "message": f"Scene analysis failed: {str(e)}",
            "details": {
                "exception": str(e)
            }
        }

def handle_analyze_object_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクト分析コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "analyze_object",
                "target": "対象オブジェクト名",
                "details": true|false (オプション)
            }
        
    Returns:
        Dict: 分析結果
    """
    # 必須パラメータの確認
    target_name = data.get("target")
    
    if not target_name:
        return {
            "status": "error",
            "message": "Missing 'target' parameter for analyze_object command",
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
    details = data.get("details", False)
    
    try:
        # 基本情報の収集
        basic_info = {
            "name": target_obj.name,
            "type": target_obj.type,
            "location": [round(v, 6) for v in target_obj.location],
            "rotation": [round(v, 6) for v in target_obj.rotation_euler],
            "scale": [round(v, 6) for v in target_obj.scale],
            "dimensions": [round(v, 6) for v in target_obj.dimensions],
            "parent": target_obj.parent.name if target_obj.parent else None,
            "visible_viewport": not target_obj.hide_viewport,
            "visible_render": not target_obj.hide_render,
            "selected": target_obj.select_get(),
            "collections": [coll.name for coll in bpy.data.collections if target_obj.name in coll.objects]
        }
        
        # オブジェクトタイプ別の情報
        type_specific_info = {}
        
        # メッシュの場合
        if target_obj.type == 'MESH' and target_obj.data:
            mesh = target_obj.data
            type_specific_info = {
                "vertices_count": len(mesh.vertices),
                "edges_count": len(mesh.edges),
                "polygons_count": len(mesh.polygons),
                "materials": [mat.name for mat in mesh.materials] if mesh.materials else [],
                "has_custom_normals": mesh.has_custom_normals,
                "is_editmode": mesh.is_editmode
            }
            
            # 詳細情報
            if details:
                # メッシュ境界情報
                bounds = {
                    "x_min": min(v.co[0] for v in mesh.vertices),
                    "y_min": min(v.co[1] for v in mesh.vertices),
                    "z_min": min(v.co[2] for v in mesh.vertices),
                    "x_max": max(v.co[0] for v in mesh.vertices),
                    "y_max": max(v.co[1] for v in mesh.vertices),
                    "z_max": max(v.co[2] for v in mesh.vertices)
                }
                
                # メッシュの品質指標
                quality = calculate_mesh_quality(mesh)
                
                type_specific_info.update({
                    "bounds": bounds,
                    "quality": quality
                })
        
        # カメラの場合
        elif target_obj.type == 'CAMERA' and target_obj.data:
            camera = target_obj.data
            type_specific_info = {
                "lens": camera.lens,
                "sensor_width": camera.sensor_width,
                "sensor_height": camera.sensor_height,
                "clip_start": camera.clip_start,
                "clip_end": camera.clip_end,
                "is_perspective": camera.type == 'PERSP'
            }
        
        # ライトの場合
        elif target_obj.type == 'LIGHT' and target_obj.data:
            light = target_obj.data
            type_specific_info = {
                "type": light.type,
                "color": [round(v, 6) for v in light.color],
                "energy": light.energy,
                "shadow": light.use_shadow
            }
            
            # ライトタイプ別の情報
            if light.type == 'SPOT':
                type_specific_info.update({
                    "spot_size": light.spot_size,
                    "spot_blend": light.spot_blend
                })
            elif light.type == 'AREA':
                type_specific_info.update({
                    "size": light.size,
                    "size_y": light.size_y
                })
        
        # 結果を返す
        return {
            "status": "success",
            "message": f"Object analysis completed: {target_name}",
            "basic_info": basic_info,
            "specific_info": type_specific_info
        }
    except Exception as e:
        logger.error(f"Error analyzing object {target_name}: {str(e)}")
        return {
            "status": "error",
            "message": f"Object analysis failed: {str(e)}",
            "details": {
                "name": target_name,
                "exception": str(e)
            }
        }

def calculate_mesh_quality(mesh) -> Dict[str, Any]:
    """
    メッシュの品質を計算
    
    Args:
        mesh: メッシュデータ
        
    Returns:
        Dict: 品質指標
    """
    # トライアングル数
    triangles_count = sum(len(p.vertices) - 2 for p in mesh.polygons)
    
    # N角形の数をカウント
    ngons_count = sum(1 for p in mesh.polygons if len(p.vertices) > 4)
    
    # 四角形の数をカウント
    quads_count = sum(1 for p in mesh.polygons if len(p.vertices) == 4)
    
    # 三角形の数をカウント
    triangles_only_count = sum(1 for p in mesh.polygons if len(p.vertices) == 3)
    
    # 非多様体エッジの検出（簡易版）
    edge_face_count = {}
    for poly in mesh.polygons:
        for edge_key in poly.edge_keys:
            if edge_key not in edge_face_count:
                edge_face_count[edge_key] = 0
            edge_face_count[edge_key] += 1
    
    non_manifold_edges = sum(1 for count in edge_face_count.values() if count > 2)
    
    return {
        "triangles_count": triangles_count,
        "ngons_count": ngons_count,
        "quads_count": quads_count,
        "triangles_only_count": triangles_only_count,
        "non_manifold_edges": non_manifold_edges,
        "manifold_percentage": round(100 * (1 - non_manifold_edges / len(edge_face_count)) if edge_face_count else 100, 2)
    }

def handle_compare_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    オブジェクト比較コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "compare",
                "target_a": "比較対象オブジェクト名A",
                "target_b": "比較対象オブジェクト名B",
                "properties": ["location", "rotation", ...] (オプション)
            }
        
    Returns:
        Dict: 比較結果
    """
    # 必須パラメータの確認
    target_a_name = data.get("target_a")
    target_b_name = data.get("target_b")
    
    if not target_a_name:
        return {
            "status": "error",
            "message": "Missing 'target_a' parameter for compare command",
            "details": {
                "required_parameters": ["target_a"]
            }
        }
    
    if not target_b_name:
        return {
            "status": "error",
            "message": "Missing 'target_b' parameter for compare command",
            "details": {
                "required_parameters": ["target_b"]
            }
        }
    
    # ターゲットオブジェクトの取得
    target_a = bpy.data.objects.get(target_a_name)
    target_b = bpy.data.objects.get(target_b_name)
    
    if not target_a:
        return {
            "status": "error",
            "message": f"Target A object not found: {target_a_name}",
            "details": {
                "available_objects": [o.name for o in bpy.data.objects]
            }
        }
    
    if not target_b:
        return {
            "status": "error",
            "message": f"Target B object not found: {target_b_name}",
            "details": {
                "available_objects": [o.name for o in bpy.data.objects]
            }
        }
    
    # オプションパラメータ
    properties = data.get("properties", ["type", "location", "rotation", "scale", "dimensions"])
    
    try:
        # 比較結果
        comparison = {}
        differences = []
        
        # プロパティを比較
        if "type" in properties:
            comparison["type"] = {
                "a": target_a.type,
                "b": target_b.type,
                "equal": target_a.type == target_b.type
            }
            if not comparison["type"]["equal"]:
                differences.append("type")
        
        if "location" in properties:
            loc_a = [round(v, 6) for v in target_a.location]
            loc_b = [round(v, 6) for v in target_b.location]
            comparison["location"] = {
                "a": loc_a,
                "b": loc_b,
                "equal": loc_a == loc_b,
                "difference": [(loc_a[i] - loc_b[i]) for i in range(3)] if loc_a != loc_b else None
            }
            if not comparison["location"]["equal"]:
                differences.append("location")
        
        if "rotation" in properties:
            rot_a = [round(v, 6) for v in target_a.rotation_euler]
            rot_b = [round(v, 6) for v in target_b.rotation_euler]
            comparison["rotation"] = {
                "a": rot_a,
                "b": rot_b,
                "equal": rot_a == rot_b,
                "difference": [(rot_a[i] - rot_b[i]) for i in range(3)] if rot_a != rot_b else None
            }
            if not comparison["rotation"]["equal"]:
                differences.append("rotation")
        
        if "scale" in properties:
            scale_a = [round(v, 6) for v in target_a.scale]
            scale_b = [round(v, 6) for v in target_b.scale]
            comparison["scale"] = {
                "a": scale_a,
                "b": scale_b,
                "equal": scale_a == scale_b,
                "difference": [(scale_a[i] / scale_b[i]) if scale_b[i] != 0 else float('inf') for i in range(3)] if scale_a != scale_b else None
            }
            if not comparison["scale"]["equal"]:
                differences.append("scale")
        
        if "dimensions" in properties:
            dim_a = [round(v, 6) for v in target_a.dimensions]
            dim_b = [round(v, 6) for v in target_b.dimensions]
            comparison["dimensions"] = {
                "a": dim_a,
                "b": dim_b,
                "equal": dim_a == dim_b,
                "difference": [(dim_a[i] - dim_b[i]) for i in range(3)] if dim_a != dim_b else None
            }
            if not comparison["dimensions"]["equal"]:
                differences.append("dimensions")
        
        # メッシュの場合のみ追加比較
        if "mesh_details" in properties and target_a.type == 'MESH' and target_b.type == 'MESH':
            mesh_a = target_a.data
            mesh_b = target_b.data
            
            comparison["mesh_details"] = {
                "vertices_count": {
                    "a": len(mesh_a.vertices),
                    "b": len(mesh_b.vertices),
                    "equal": len(mesh_a.vertices) == len(mesh_b.vertices),
                    "difference": len(mesh_a.vertices) - len(mesh_b.vertices)
                },
                "polygons_count": {
                    "a": len(mesh_a.polygons),
                    "b": len(mesh_b.polygons),
                    "equal": len(mesh_a.polygons) == len(mesh_b.polygons),
                    "difference": len(mesh_a.polygons) - len(mesh_b.polygons)
                }
            }
            
            if not comparison["mesh_details"]["vertices_count"]["equal"]:
                differences.append("vertices_count")
            
            if not comparison["mesh_details"]["polygons_count"]["equal"]:
                differences.append("polygons_count")
        
        return {
            "status": "success",
            "message": f"Objects comparison completed",
            "equal": len(differences) == 0,
            "differences": differences,
            "comparison": comparison
        }
    except Exception as e:
        logger.error(f"Error comparing objects: {str(e)}")
        return {
            "status": "error",
            "message": f"Objects comparison failed: {str(e)}",
            "details": {
                "target_a": target_a_name,
                "target_b": target_b_name,
                "exception": str(e)
            }
        }

#-------------------------------------------------------------------------
# メタコマンド
#-------------------------------------------------------------------------

def handle_batch_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    バッチコマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "batch",
                "commands": [
                    {コマンド1},
                    {コマンド2},
                    ...
                ]
            }
        
    Returns:
        Dict: 実行結果
    """
    # 必須パラメータの確認
    commands = data.get("commands")
    
    if not commands:
        return {
            "status": "error",
            "message": "Missing 'commands' parameter for batch command",
            "details": {
                "required_parameters": ["commands"]
            }
        }
    
    if not isinstance(commands, list):
        return {
            "status": "error",
            "message": "Invalid 'commands' parameter: must be a list",
            "details": {
                "type": type(commands).__name__
            }
        }
    
    # コマンドを順番に実行
    results = []
    success_count = 0
    error_count = 0
    
    try:
        # コマンドハンドラーの動的インポート（サーキュラーインポート回避）
        from . import command_handler
        
        for i, cmd in enumerate(commands):
            try:
                # コマンドの実行
                result = command_handler.handle_command(cmd)
                results.append(result)
                
                # 成功・エラーカウント
                if result.get("status") == "success":
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                # コマンド実行中のエラー
                error_result = {
                    "status": "error",
                    "message": f"Error executing command {i+1}: {str(e)}",
                    "details": {
                        "command_index": i,
                        "exception": str(e)
                    }
                }
                results.append(error_result)
                error_count += 1
        
        return {
            "status": "success" if error_count == 0 else "partial",
            "message": f"Batch execution completed: {success_count} succeeded, {error_count} failed",
            "details": {
                "total": len(commands),
                "success_count": success_count,
                "error_count": error_count
            },
            "results": results
        }
    except Exception as e:
        logger.error(f"Error in batch command: {str(e)}")
        return {
            "status": "error",
            "message": f"Batch execution failed: {str(e)}",
            "details": {
                "exception": str(e),
                "results": results
            }
        }

def handle_undo_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Undoコマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "undo",
                "steps": 整数 (オプション)
            }
        
    Returns:
        Dict: 実行結果
    """
    # オプションパラメータ
    steps = data.get("steps", 1)
    
    try:
        # 指定されたステップ数だけUndoを実行
        steps_done = 0
        for _ in range(steps):
            if bpy.ops.ed.undo.poll():
                bpy.ops.ed.undo()
                steps_done += 1
            else:
                break
        
        return {
            "status": "success",
            "message": f"Undo executed: {steps_done} step(s)",
            "details": {
                "requested_steps": steps,
                "executed_steps": steps_done
            }
        }
    except Exception as e:
        logger.error(f"Error executing undo: {str(e)}")
        return {
            "status": "error",
            "message": f"Undo failed: {str(e)}",
            "details": {
                "exception": str(e)
            }
        }

def handle_redo_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redoコマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "redo",
                "steps": 整数 (オプション)
            }
        
    Returns:
        Dict: 実行結果
    """
    # オプションパラメータ
    steps = data.get("steps", 1)
    
    try:
        # 指定されたステップ数だけRedoを実行
        steps_done = 0
        for _ in range(steps):
            if bpy.ops.ed.redo.poll():
                bpy.ops.ed.redo()
                steps_done += 1
            else:
                break
        
        return {
            "status": "success",
            "message": f"Redo executed: {steps_done} step(s)",
            "details": {
                "requested_steps": steps,
                "executed_steps": steps_done
            }
        }
    except Exception as e:
        logger.error(f"Error executing redo: {str(e)}")
        return {
            "status": "error",
            "message": f"Redo failed: {str(e)}",
            "details": {
                "exception": str(e)
            }
        }

def handle_save_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    保存コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "save",
                "filepath": "保存先パス" (オプション)
            }
        
    Returns:
        Dict: 実行結果
    """
    # オプションパラメータ
    filepath = data.get("filepath")
    
    try:
        if filepath:
            # 指定されたパスに保存
            bpy.ops.wm.save_as_mainfile(filepath=filepath)
            message = f"File saved to: {filepath}"
        else:
            # 現在のファイルに上書き保存
            bpy.ops.wm.save_mainfile()
            message = f"File saved to: {bpy.data.filepath}"
        
        return {
            "status": "success",
            "message": message,
            "details": {
                "filepath": filepath if filepath else bpy.data.filepath
            }
        }
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        return {
            "status": "error",
            "message": f"Save failed: {str(e)}",
            "details": {
                "exception": str(e)
            }
        }

def handle_execute_code_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pythonコード実行コマンドを処理
    
    Args:
        data: コマンドデータ
            {
                "command": "execute_code",
                "code": "実行するPythonコード"
            }
        
    Returns:
        Dict: 実行結果
    """
    # 必須パラメータの確認
    code = data.get("code")
    
    if not code:
        return {
            "status": "error",
            "message": "Missing 'code' parameter for execute_code command",
            "details": {
                "required_parameters": ["code"]
            }
        }
    
    try:
        # コードの実行結果を捕捉するために辞書を用意
        locals_dict = {}
        
        # コードを実行
        exec(code, {"bpy": bpy, "mathutils": mathutils}, locals_dict)
        
        # 実行結果（返り値）の取得
        result_value = locals_dict.get("result")
        
        # JSON変換可能かチェック
        if result_value is not None:
            try:
                # 結果のJSON変換テスト
                json.dumps(result_value)
                result_json_compatible = True
            except (TypeError, OverflowError):
                result_json_compatible = False
                result_value = str(result_value)
        else:
            result_json_compatible = True
        
        return {
            "status": "success",
            "message": "Code executed successfully",
            "details": {
                "result": result_value,
                "result_json_compatible": result_json_compatible
            }
        }
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        return {
            "status": "error",
            "message": f"Code execution failed: {str(e)}",
            "details": {
                "exception": str(e),
                "code": code
            }
        }

# サーバーへの関数登録
def register_meta_commands_to_server():
    """
    メタコマンド関数をHTTPサーバーに登録
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
        
        # 分析コマンドの登録
        server.register_function(
            handle_analyze_scene_command,
            "analyze_scene",
            examples=[
                {"command": "analyze_scene", "details": True}
            ],
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["analyze_scene"]},
                    "details": {"type": "boolean"}
                },
                "required": ["command"]
            }
        )
        
        server.register_function(
            handle_analyze_object_command,
            "analyze_object",
            examples=[
                {"command": "analyze_object", "target": "Cube", "details": True}
            ],
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["analyze_object"]},
                    "target": {"type": "string"},
                    "details": {"type": "boolean"}
                },
                "required": ["command", "target"]
            }
        )
        
        # オブジェクト比較コマンドの登録
        server.register_function(
            handle_compare_command,
            "compare",
            examples=[
                {"command": "compare", "target_a": "Cube", "target_b": "Cube.001"}
            ],
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["compare"]},
                    "target_a": {"type": "string"},
                    "target_b": {"type": "string"}
                },
                "required": ["command", "target_a", "target_b"]
            }
        )
        
        # バッチ処理コマンドの登録
        server.register_function(
            handle_batch_command,
            "batch",
            examples=[
                {
                    "command": "batch",
                    "commands": [
                        {"command": "create", "type": "cube", "name": "BatchCube1"},
                        {"command": "create", "type": "sphere", "name": "BatchSphere1"}
                    ]
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["batch"]},
                    "commands": {"type": "array", "items": {"type": "object"}}
                },
                "required": ["command", "commands"]
            }
        )
        
        logger.info("メタコマンド関数がHTTPサーバーに登録されました")
        return True
        
    except Exception as e:
        logger.error(f"メタコマンド関数の登録に失敗: {str(e)}")
        return False
