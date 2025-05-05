"""
JSON APIルート
BlenderとJSONでやり取りするためのFastAPIルート定義
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .json_handlers import (
    create_primitive,
    create_flowerpot,
    delete_objects,
    transform_object,
    get_scene_info,
    modify_object_geometry,
    set_object_property
)

# ロガー設定
logger = logging.getLogger('unified_mcp.json_api_routes')

# APIルーター
router = APIRouter(prefix="/json", tags=["JSON API"])

# 標準レスポンスクラス
class APIResponse:
    """標準APIレスポンス"""
    @classmethod
    def success(cls, message: str = "Success", data: Optional[Dict[str, Any]] = None) -> JSONResponse:
        """成功レスポンスを生成"""
        return JSONResponse({
            "status": "success",
            "message": message,
            "data": data or {}
        })
    
    @classmethod
    def error(cls, message: str, data: Optional[Dict[str, Any]] = None) -> JSONResponse:
        """エラーレスポンスを生成"""
        return JSONResponse({
            "status": "error",
            "message": message,
            "data": data or {}
        })

# ルート定義
@router.get("/")
async def json_api_info():
    """API情報を返す"""
    return APIResponse.success("Blender JSON API", {
        "version": "1.1",
        "endpoints": [
            {"path": "/json/create", "method": "POST", "description": "3Dオブジェクトを作成"},
            {"path": "/json/flowerpot", "method": "POST", "description": "植木鉢を作成"},
            {"path": "/json/delete", "method": "POST", "description": "オブジェクトを削除"},
            {"path": "/json/transform", "method": "POST", "description": "オブジェクトを変換（移動・回転・スケール）"},
            {"path": "/json/geometry", "method": "POST", "description": "オブジェクトのジオメトリを修正"},
            {"path": "/json/property", "method": "POST", "description": "オブジェクトのプロパティを設定"},
            {"path": "/json/scene", "method": "GET", "description": "シーン情報を取得"}
        ]
    })

@router.post("/create")
async def create_object(request: Request):
    """JSONデータからオブジェクトを作成する"""
    try:
        # リクエストボディをJSONとして解析
        data = await request.json()
        result = create_primitive(data)
        
        if result.get("success", False):
            return APIResponse.success(
                result.get("message", "オブジェクトが作成されました"),
                result
            )
        else:
            return APIResponse.error(
                result.get("message", "オブジェクト作成エラー"),
                result
            )
    except Exception as e:
        logger.error(f"オブジェクト作成エラー: {str(e)}")
        return APIResponse.error(f"オブジェクト作成エラー: {str(e)}")

@router.post("/flowerpot")
async def create_flowerpot_object(request: Request):
    """JSONデータから植木鉢を作成する"""
    try:
        # リクエストボディをJSONとして解析
        data = await request.json()
        result = create_flowerpot(data)
        
        if result.get("success", False):
            return APIResponse.success(
                result.get("message", "植木鉢が作成されました"),
                result
            )
        else:
            return APIResponse.error(
                result.get("message", "植木鉢作成エラー"),
                result
            )
    except Exception as e:
        logger.error(f"植木鉢作成エラー: {str(e)}")
        return APIResponse.error(f"植木鉢作成エラー: {str(e)}")

@router.post("/delete")
async def delete_scene_objects(request: Request):
    """JSONデータからオブジェクトを削除する"""
    try:
        # リクエストボディをJSONとして解析
        data = await request.json()
        result = delete_objects(data)
        
        if result.get("success", False):
            return APIResponse.success(
                result.get("message", "オブジェクトが削除されました"),
                result
            )
        else:
            return APIResponse.error(
                result.get("message", "オブジェクト削除エラー"),
                result
            )
    except Exception as e:
        logger.error(f"オブジェクト削除エラー: {str(e)}")
        return APIResponse.error(f"オブジェクト削除エラー: {str(e)}")

@router.post("/transform")
async def transform_scene_object(request: Request):
    """JSONデータからオブジェクトを変換する"""
    try:
        # リクエストボディをJSONとして解析
        data = await request.json()
        result = transform_object(data)
        
        if result.get("success", False):
            return APIResponse.success(
                result.get("message", "オブジェクトが変換されました"),
                result
            )
        else:
            return APIResponse.error(
                result.get("message", "オブジェクト変換エラー"),
                result
            )
    except Exception as e:
        logger.error(f"オブジェクト変換エラー: {str(e)}")
        return APIResponse.error(f"オブジェクト変換エラー: {str(e)}")

@router.post("/geometry")
async def modify_object_geo(request: Request):
    """オブジェクトのジオメトリを修正する"""
    try:
        # リクエストボディをJSONとして解析
        data = await request.json()
        result = modify_object_geometry(data)
        
        if result.get("success", False):
            return APIResponse.success(
                result.get("message", "ジオメトリが修正されました"),
                result
            )
        else:
            return APIResponse.error(
                result.get("message", "ジオメトリ修正エラー"),
                result
            )
    except Exception as e:
        logger.error(f"ジオメトリ修正エラー: {str(e)}")
        return APIResponse.error(f"ジオメトリ修正エラー: {str(e)}")

@router.post("/property")
async def set_object_prop(request: Request):
    """オブジェクトのプロパティを設定する"""
    try:
        # リクエストボディをJSONとして解析
        data = await request.json()
        result = set_object_property(data)
        
        if result.get("success", False):
            return APIResponse.success(
                result.get("message", "プロパティが設定されました"),
                result
            )
        else:
            return APIResponse.error(
                result.get("message", "プロパティ設定エラー"),
                result
            )
    except Exception as e:
        logger.error(f"プロパティ設定エラー: {str(e)}")
        return APIResponse.error(f"プロパティ設定エラー: {str(e)}")

@router.get("/scene")
async def get_current_scene():
    """現在のシーン情報を返す"""
    try:
        result = get_scene_info()
        
        if result.get("success", False):
            return APIResponse.success(
                "シーン情報を取得しました",
                result
            )
        else:
            return APIResponse.error(
                result.get("message", "シーン情報取得エラー"),
                result
            )
    except Exception as e:
        logger.error(f"シーン情報取得エラー: {str(e)}")
        return APIResponse.error(f"シーン情報取得エラー: {str(e)}")
