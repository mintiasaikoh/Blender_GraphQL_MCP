"""
MCP Tools Module - ModelContextProtocol準拠のツール定義と実行
"""

import bpy
import json
import logging
import traceback
from typing import Dict, List, Any, Optional, Union, Tuple

# 既存のモジュールをインポート
from .json_api import create_primitive, delete_objects, transform_object, get_scene_info
from .json_api_advanced import boolean_operation, extrude_face, create_from_vertices, subdivide_mesh

# ロギング設定
logger = logging.getLogger(__name__)

def get_tools_definitions() -> List[Dict[str, Any]]:
    """
    MCP準拠のツール定義リストを返す
    
    Returns:
        List[Dict]: ツール定義のリスト
    """
    tools = [
        # 基本オブジェクト作成ツール
        {
            "name": "create_object",
            "description": "Blenderで新しいオブジェクトを作成する",
            "parameters": {
                "type": "object",
                "properties": {
                    "primitive_type": {
                        "type": "string",
                        "description": "作成するプリミティブの種類",
                        "enum": ["cube", "sphere", "plane", "cylinder", "cone"],
                    },
                    "params": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "3D空間での位置 [x, y, z]"
                            },
                            "size": {
                                "type": "number",
                                "description": "オブジェクトのサイズ"
                            },
                            "name": {
                                "type": "string",
                                "description": "オブジェクトの名前"
                            },
                            "color": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "RGBA色 [r, g, b, a]"
                            }
                        }
                    }
                },
                "required": ["primitive_type"]
            }
        },
        
        # オブジェクト削除ツール
        {
            "name": "delete_object",
            "description": "Blenderからオブジェクトを削除する",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "削除するオブジェクトの名前"
                    }
                },
                "required": ["object_name"]
            }
        },
        
        # オブジェクト変換ツール
        {
            "name": "transform_object",
            "description": "Blenderのオブジェクトを変換する（移動、回転、スケール）",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "変換するオブジェクトの名前"
                    },
                    "location": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "新しい位置 [x, y, z]"
                    },
                    "rotation": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "新しい回転 [x, y, z] (ラジアン)"
                    },
                    "scale": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "新しいスケール [x, y, z]"
                    },
                    "relative": {
                        "type": "boolean",
                        "description": "相対変換かどうか (デフォルトはfalse)"
                    }
                },
                "required": ["object_name"]
            }
        },
        
        # ブーリアン操作ツール
        {
            "name": "boolean_operation",
            "description": "2つのオブジェクト間でブーリアン操作を実行する",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "メインのターゲットオブジェクト名"
                    },
                    "cutter": {
                        "type": "string",
                        "description": "カッターオブジェクト名"
                    },
                    "operation": {
                        "type": "string",
                        "description": "ブーリアン操作の種類",
                        "enum": ["union", "difference", "intersect"]
                    },
                    "delete_cutter": {
                        "type": "boolean",
                        "description": "操作後にカッターを削除するかどうか"
                    }
                },
                "required": ["target", "cutter", "operation"]
            }
        },
        
        # シーン情報取得ツール
        {
            "name": "get_scene_info",
            "description": "現在のBlenderシーンに関する情報を取得する",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_objects": {
                        "type": "boolean",
                        "description": "オブジェクト情報を含めるかどうか"
                    },
                    "include_materials": {
                        "type": "boolean",
                        "description": "マテリアル情報を含めるかどうか"
                    }
                }
            }
        }
    ]
    
    return tools

def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    指定されたMCPツールを実行する
    
    Args:
        tool_name: 実行するツールの名前
        parameters: ツールのパラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        logger.info(f"ツール '{tool_name}' を実行: {parameters}")
        
        # ツール名に基づいて適切な関数を呼び出す
        if tool_name == "create_object":
            return _execute_create_object(parameters)
        elif tool_name == "delete_object":
            return _execute_delete_object(parameters)
        elif tool_name == "transform_object":
            return _execute_transform_object(parameters)
        elif tool_name == "boolean_operation":
            return _execute_boolean_operation(parameters)
        elif tool_name == "get_scene_info":
            return _execute_get_scene_info(parameters)
        else:
            logger.error(f"不明なツール: {tool_name}")
            return {
                "error": {
                    "code": "UNKNOWN_TOOL",
                    "message": f"Unknown tool: {tool_name}",
                    "details": {
                        "available_tools": [tool["name"] for tool in get_tools_definitions()]
                    }
                }
            }
    except Exception as e:
        logger.error(f"ツール '{tool_name}' の実行中にエラーが発生: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            "error": {
                "code": "EXECUTION_ERROR",
                "message": f"Error executing tool '{tool_name}': {str(e)}",
                "details": {
                    "traceback": traceback.format_exc()
                }
            }
        }

def _execute_create_object(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    create_objectツールを実行
    
    Args:
        parameters: ツールパラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # 必須パラメータの確認
        if "primitive_type" not in parameters:
            return {
                "error": {
                    "code": "MISSING_PARAMETER",
                    "message": "Missing required parameter: primitive_type",
                    "details": {
                        "required_parameters": ["primitive_type"]
                    }
                }
            }
        
        # 既存のcreate_primitive関数を呼び出す
        primitive_type = parameters["primitive_type"]
        params = parameters.get("params", {})
        
        result = create_primitive(primitive_type, params)
        
        # MCP準拠のレスポンス形式に変換
        if result.get("success", False):
            return {
                "success": True,
                "object_name": result.get("name", ""),
                "id": result.get("id", ""),
                "details": {
                    "type": primitive_type,
                    "location": params.get("location", [0, 0, 0])
                }
            }
        else:
            return {
                "error": {
                    "code": "OBJECT_CREATION_FAILED",
                    "message": result.get("message", "Failed to create object"),
                }
            }
    except Exception as e:
        logger.error(f"オブジェクト作成エラー: {str(e)}")
        return {
            "error": {
                "code": "OBJECT_CREATION_FAILED",
                "message": f"Failed to create object: {str(e)}",
            }
        }

def _execute_delete_object(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    delete_objectツールを実行
    
    Args:
        parameters: ツールパラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # 必須パラメータの確認
        if "object_name" not in parameters:
            return {
                "error": {
                    "code": "MISSING_PARAMETER",
                    "message": "Missing required parameter: object_name",
                    "details": {
                        "required_parameters": ["object_name"]
                    }
                }
            }
        
        # 既存のdelete_objects関数を呼び出す
        object_name = parameters["object_name"]
        
        result = delete_objects({"name": object_name})
        
        # MCP準拠のレスポンス形式に変換
        if result.get("success", False):
            return {
                "success": True,
                "deleted": object_name
            }
        else:
            return {
                "error": {
                    "code": "OBJECT_DELETION_FAILED",
                    "message": result.get("message", "Failed to delete object"),
                }
            }
    except Exception as e:
        logger.error(f"オブジェクト削除エラー: {str(e)}")
        return {
            "error": {
                "code": "OBJECT_DELETION_FAILED",
                "message": f"Failed to delete object: {str(e)}",
            }
        }

def _execute_transform_object(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    transform_objectツールを実行
    
    Args:
        parameters: ツールパラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # 必須パラメータの確認
        if "object_name" not in parameters:
            return {
                "error": {
                    "code": "MISSING_PARAMETER",
                    "message": "Missing required parameter: object_name",
                    "details": {
                        "required_parameters": ["object_name"]
                    }
                }
            }
        
        # 既存のtransform_object関数を呼び出す
        result = transform_object(parameters)
        
        # MCP準拠のレスポンス形式に変換
        if result.get("success", False):
            return {
                "success": True,
                "object": parameters["object_name"],
                "details": {
                    "location": parameters.get("location"),
                    "rotation": parameters.get("rotation"),
                    "scale": parameters.get("scale")
                }
            }
        else:
            return {
                "error": {
                    "code": "TRANSFORM_FAILED",
                    "message": result.get("message", "Failed to transform object"),
                }
            }
    except Exception as e:
        logger.error(f"オブジェクト変換エラー: {str(e)}")
        return {
            "error": {
                "code": "TRANSFORM_FAILED",
                "message": f"Failed to transform object: {str(e)}",
            }
        }

def _execute_boolean_operation(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    boolean_operationツールを実行
    
    Args:
        parameters: ツールパラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # 必須パラメータの確認
        required_params = ["target", "cutter", "operation"]
        missing_params = [param for param in required_params if param not in parameters]
        
        if missing_params:
            return {
                "error": {
                    "code": "MISSING_PARAMETER",
                    "message": f"Missing required parameters: {', '.join(missing_params)}",
                    "details": {
                        "required_parameters": required_params
                    }
                }
            }
        
        # 既存のboolean_operation関数を呼び出す
        result = boolean_operation(parameters)
        
        # MCP準拠のレスポンス形式に変換
        if result.get("success", False):
            return {
                "success": True,
                "result_object": parameters["target"],
                "operation": parameters["operation"],
                "details": {
                    "cutter": parameters["cutter"],
                    "cutter_deleted": parameters.get("delete_cutter", False)
                }
            }
        else:
            return {
                "error": {
                    "code": "BOOLEAN_OPERATION_FAILED",
                    "message": result.get("message", "Failed to perform boolean operation"),
                }
            }
    except Exception as e:
        logger.error(f"ブーリアン操作エラー: {str(e)}")
        return {
            "error": {
                "code": "BOOLEAN_OPERATION_FAILED",
                "message": f"Failed to perform boolean operation: {str(e)}",
            }
        }

def _execute_get_scene_info(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    get_scene_infoツールを実行
    
    Args:
        parameters: ツールパラメータ
        
    Returns:
        Dict: 実行結果
    """
    try:
        # 既存のget_scene_info関数を呼び出す
        result = get_scene_info()
        
        # 追加パラメータに基づいて拡張情報を取得
        include_objects = parameters.get("include_objects", False)
        include_materials = parameters.get("include_materials", False)
        
        if include_objects:
            # オブジェクト情報を取得
            from . import api_handlers
            objects_list = api_handlers.get_objects_list()
            result["objects"] = objects_list
        
        if include_materials:
            # マテリアル情報を取得
            from . import api_handlers
            materials_list = api_handlers.get_materials_list()
            result["materials"] = materials_list
        
        return result
    except Exception as e:
        logger.error(f"シーン情報取得エラー: {str(e)}")
        return {
            "error": {
                "code": "SCENE_INFO_FAILED",
                "message": f"Failed to get scene information: {str(e)}",
            }
        }
