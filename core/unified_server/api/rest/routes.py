"""
REST API ルート定義
Unified MCPサーバーのREST APIエンドポイントを定義
"""

import logging
import time
import uuid
import json
import asyncio
from typing import Dict, List, Any, Optional, Callable

# FastAPIのインポートを試みる
try:
    from fastapi import APIRouter, HTTPException, Depends, Header, Request, Response, Body, Path, Query
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # FastAPIが利用できない環境でもエラーが発生しないようにダミークラスを定義
    class APIRouter:
        def __init__(self, **kwargs):
            pass
        
        def get(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        
        def post(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    
    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code = status_code
            self.detail = detail
    
    class JSONResponse:
        def __init__(self, content, status_code=200):
            self.content = content
            self.status_code = status_code
    
    def Depends(dependency):
        return dependency
    
    def Body(*args, **kwargs):
        return None
    
    def Path(*args, **kwargs):
        return None
    
    def Query(*args, **kwargs):
        return None

from .models import (
    APIResponse, CommandStatus, CommandRequest, CommandResult, 
    BatchRequest, ErrorDetail
)

# コマンドレジストリをインポート
try:
    from ....adapters.command_registry import command_registry
    from ....adapters.command_registry import execute_command
except ImportError:
    # コマンドレジストリが利用できない場合はダミーを作成
    command_registry = {}
    async def execute_command(command_name, params=None):
        return {"error": "Command registry not available"}

# ロガー設定
logger = logging.getLogger("unified_mcp.api.rest")

# APIルーターを作成
router = APIRouter(prefix="/api/v1")

# 非同期タスクの管理用辞書
task_registry = {}  # タスクID -> CommandResult
session_registry = {}  # セッションID -> セッション情報


# エラーハンドリング用のデコレータ
def handle_errors():
    """エラーハンドリングデコレータ"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException as e:
                # FastAPIのHTTPExceptionはそのまま再発生させる
                raise e
            except Exception as e:
                logger.error(f"APIルート実行中のエラー: {str(e)}")
                # エラーレスポンスの作成
                error_details = {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal server error: {str(e)}",
                }
                return JSONResponse(
                    content=APIResponse.error_response(
                        errors=[error_details]
                    ).to_dict(),
                    status_code=500
                )
        return wrapper
    return decorator


#------------------------------------------------------------------------------
# メタデータAPI
#------------------------------------------------------------------------------

@router.get("/", tags=["metadata"])
@handle_errors()
async def get_api_info():
    """
    API情報を取得
    
    Returns:
        APIの基本情報
    """
    logger.info("API情報リクエスト")
    
    # APIの基本情報を返す
    return APIResponse.success_response(data={
        "name": "Blender Unified MCP REST API",
        "version": "1.0.0",
        "description": "Blender制御用の統合MCPサーバーRESTインターフェース",
        "endpoints": [
            {"path": "/api/v1", "description": "APIのルート"},
            {"path": "/api/v1/commands", "description": "利用可能なコマンド一覧"},
            {"path": "/api/v1/commands/{command_name}", "description": "特定コマンドの詳細"},
            {"path": "/api/v1/command", "method": "POST", "description": "コマンド実行"},
            {"path": "/api/v1/batch", "method": "POST", "description": "バッチコマンド実行"},
            {"path": "/api/v1/addons", "description": "アドオン一覧"},
        ],
        "documentation": "/docs",
    }).to_dict()


@router.get("/commands", tags=["metadata"])
@handle_errors()
async def get_commands_catalog():
    """
    利用可能なすべてのコマンドとそのスキーマを取得
    
    Returns:
        すべてのコマンドのカタログ
    """
    logger.info("コマンドカタログをリクエストされました")
    
    # 登録されたすべてのコマンドを取得
    command_schemas = []
    
    for command_name, command_info in command_registry.items():
        schema = {
            "name": command_name,
            "description": command_info.get("description", "説明なし"),
            "parameters": command_info.get("schema", {}),
            "returns": command_info.get("returns", {}),
            "group": command_info.get("group", "default"),
            "tags": command_info.get("tags", []),
        }
        command_schemas.append(schema)
    
    # グループ別に整理
    grouped_commands = {}
    for schema in command_schemas:
        group = schema.get("group", "default")
        if group not in grouped_commands:
            grouped_commands[group] = []
        grouped_commands[group].append(schema)
    
    # レスポンス生成
    return APIResponse.success_response(data={
        "command_count": len(command_schemas),
        "groups": list(grouped_commands.keys()),
        "commands": command_schemas,
        "grouped_commands": grouped_commands
    }).to_dict()


@router.get("/commands/{command_name}", tags=["metadata"])
@handle_errors()
async def get_command_schema(command_name: str = Path(..., description="スキーマを取得するコマンド名")):
    """
    特定のコマンドのスキーマを取得
    
    Args:
        command_name: スキーマを取得するコマンド名
        
    Returns:
        コマンドのスキーマ
    """
    logger.info(f"コマンド '{command_name}' のスキーマをリクエストされました")
    
    # コマンドを検索
    if command_name not in command_registry:
        error_detail = ErrorDetail(
            code="COMMAND_NOT_FOUND",
            message=f"Command '{command_name}' not found",
            context={"available_commands": list(command_registry.keys())},
            suggestion="Available commands can be obtained from /api/v1/commands"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()
    
    command_info = command_registry[command_name]
    
    # コマンドスキーマを生成
    schema = {
        "name": command_name,
        "description": command_info.get("description", "説明なし"),
        "parameters": command_info.get("schema", {}),
        "returns": command_info.get("returns", {}),
        "group": command_info.get("group", "default"),
        "tags": command_info.get("tags", []),
        "examples": command_info.get("examples", [])
    }
    
    # レスポンス生成
    return APIResponse.success_response(data=schema).to_dict()


#------------------------------------------------------------------------------
# アドオン操作API
#------------------------------------------------------------------------------

@router.get("/addons", tags=["addons"])
@handle_errors()
async def get_all_addons():
    """
    すべてのアドオン情報を取得
    
    Returns:
        すべてのアドオン情報
    """
    logger.info("すべてのアドオン情報をリクエストされました")
    
    try:
        # get_all_addons コマンドを実行
        result = await execute_command("get_all_addons", {})
        
        if isinstance(result, dict) and result.get("error"):
            # エラーが含まれている場合
            error_detail = ErrorDetail(
                code="ADDON_OPERATION_FAILED",
                message="Failed to get addons information",
                context={"error": result.get("error")}
            )
            return APIResponse.error_response(
                errors=[error_detail.to_dict()]
            ).to_dict()
        
        return APIResponse.success_response(data=result).to_dict()
        
    except Exception as e:
        logger.error(f"アドオン情報の取得に失敗しました: {str(e)}")
        error_detail = ErrorDetail(
            code="INTERNAL_ERROR",
            message=f"Failed to get addons information: {str(e)}"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()


@router.get("/addons/{addon_name}", tags=["addons"])
@handle_errors()
async def get_addon_info(addon_name: str = Path(..., description="情報を取得するアドオン名")):
    """
    特定のアドオン情報を取得
    
    Args:
        addon_name: 情報を取得するアドオン名
        
    Returns:
        アドオン情報
    """
    logger.info(f"アドオン '{addon_name}' の情報をリクエストされました")
    
    try:
        # get_addon_info コマンドを実行
        result = await execute_command("get_addon_info", {"addon_name": addon_name})
        
        if isinstance(result, dict) and result.get("error"):
            # エラーが含まれている場合
            error_detail = ErrorDetail(
                code="ADDON_INFO_FAILED",
                message=f"Failed to get information for addon '{addon_name}'",
                context={"addon_name": addon_name, "error": result.get("error")}
            )
            return APIResponse.error_response(
                errors=[error_detail.to_dict()]
            ).to_dict()
        
        return APIResponse.success_response(data=result).to_dict()
        
    except Exception as e:
        logger.error(f"アドオン情報の取得に失敗しました: {str(e)}")
        error_detail = ErrorDetail(
            code="INTERNAL_ERROR",
            message=f"Failed to get addon information: {str(e)}"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()


@router.post("/addons/{addon_name}/enable", tags=["addons"])
@handle_errors()
async def enable_addon(addon_name: str = Path(..., description="有効化するアドオン名")):
    """
    アドオンを有効化
    
    Args:
        addon_name: 有効化するアドオン名
        
    Returns:
        操作結果
    """
    logger.info(f"アドオン '{addon_name}' の有効化をリクエストされました")
    
    try:
        # enable_addon コマンドを実行
        result = await execute_command("enable_addon", {"addon_name": addon_name})
        
        if isinstance(result, dict) and result.get("error"):
            # エラーが含まれている場合
            error_detail = ErrorDetail(
                code="ADDON_OPERATION_FAILED",
                message=f"Failed to enable addon '{addon_name}'",
                context={"addon_name": addon_name, "error": result.get("error")}
            )
            return APIResponse.error_response(
                errors=[error_detail.to_dict()]
            ).to_dict()
        
        return APIResponse.success_response(data=result).to_dict()
        
    except Exception as e:
        logger.error(f"アドオン有効化に失敗しました: {str(e)}")
        error_detail = ErrorDetail(
            code="INTERNAL_ERROR",
            message=f"Failed to enable addon: {str(e)}"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()


@router.post("/addons/{addon_name}/disable", tags=["addons"])
@handle_errors()
async def disable_addon(addon_name: str = Path(..., description="無効化するアドオン名")):
    """
    アドオンを無効化
    
    Args:
        addon_name: 無効化するアドオン名
        
    Returns:
        操作結果
    """
    logger.info(f"アドオン '{addon_name}' の無効化をリクエストされました")
    
    try:
        # disable_addon コマンドを実行
        result = await execute_command("disable_addon", {"addon_name": addon_name})
        
        if isinstance(result, dict) and result.get("error"):
            # エラーが含まれている場合
            error_detail = ErrorDetail(
                code="ADDON_OPERATION_FAILED",
                message=f"Failed to disable addon '{addon_name}'",
                context={"addon_name": addon_name, "error": result.get("error")}
            )
            return APIResponse.error_response(
                errors=[error_detail.to_dict()]
            ).to_dict()
        
        return APIResponse.success_response(data=result).to_dict()
        
    except Exception as e:
        logger.error(f"アドオン無効化に失敗しました: {str(e)}")
        error_detail = ErrorDetail(
            code="INTERNAL_ERROR",
            message=f"Failed to disable addon: {str(e)}"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()


@router.post("/addons/install", tags=["addons"])
@handle_errors()
async def install_addon(file_path: str = Body(..., embed=True, description="インストールするアドオンZIPファイルのパス")):
    """
    ファイルからアドオンをインストール
    
    Args:
        file_path: インストールするアドオンZIPファイルのパス
        
    Returns:
        操作結果
    """
    logger.info(f"アドオンのインストールをリクエストされました: {file_path}")
    
    try:
        # install_addon_from_file コマンドを実行
        result = await execute_command("install_addon_from_file", {"file_path": file_path})
        
        if isinstance(result, dict) and result.get("error"):
            # エラーが含まれている場合
            error_detail = ErrorDetail(
                code="ADDON_OPERATION_FAILED",
                message="Failed to install addon from file",
                context={"file_path": file_path, "error": result.get("error")}
            )
            return APIResponse.error_response(
                errors=[error_detail.to_dict()]
            ).to_dict()
        
        return APIResponse.success_response(data=result).to_dict()
        
    except Exception as e:
        logger.error(f"アドオンインストールに失敗しました: {str(e)}")
        error_detail = ErrorDetail(
            code="INTERNAL_ERROR",
            message=f"Failed to install addon: {str(e)}"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()


@router.post("/addons/install-from-url", tags=["addons"])
@handle_errors()
async def install_addon_from_url(url: str = Body(..., embed=True, description="インストールするアドオンZIPファイルのURL")):
    """
    URLからアドオンをインストール
    
    Args:
        url: インストールするアドオンZIPファイルのURL
        
    Returns:
        操作結果
    """
    logger.info(f"URLからアドオンのインストールをリクエストされました: {url}")
    
    try:
        # install_addon_from_url コマンドを実行
        result = await execute_command("install_addon_from_url", {"url": url})
        
        if isinstance(result, dict) and result.get("error"):
            # エラーが含まれている場合
            error_detail = ErrorDetail(
                code="ADDON_OPERATION_FAILED",
                message="Failed to install addon from URL",
                context={"url": url, "error": result.get("error")}
            )
            return APIResponse.error_response(
                errors=[error_detail.to_dict()]
            ).to_dict()
        
        return APIResponse.success_response(data=result).to_dict()
        
    except Exception as e:
        logger.error(f"URLからのアドオンインストールに失敗しました: {str(e)}")
        error_detail = ErrorDetail(
            code="INTERNAL_ERROR",
            message=f"Failed to install addon from URL: {str(e)}"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()


@router.get("/addons/updates", tags=["addons"])
@handle_errors()
async def check_addon_updates():
    """
    アドオンの更新を確認
    
    Returns:
        更新可能なアドオンの情報
    """
    logger.info("アドオンの更新確認をリクエストされました")
    
    try:
        # check_addon_updates コマンドを実行
        result = await execute_command("check_addon_updates", {})
        
        if isinstance(result, dict) and result.get("error"):
            # エラーが含まれている場合
            error_detail = ErrorDetail(
                code="ADDON_OPERATION_FAILED",
                message="Failed to check addon updates",
                context={"error": result.get("error")}
            )
            return APIResponse.error_response(
                errors=[error_detail.to_dict()]
            ).to_dict()
        
        return APIResponse.success_response(data=result).to_dict()
        
    except Exception as e:
        logger.error(f"アドオン更新確認に失敗しました: {str(e)}")
        error_detail = ErrorDetail(
            code="INTERNAL_ERROR",
            message=f"Failed to check addon updates: {str(e)}"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()


#------------------------------------------------------------------------------
# コマンド実行API
#------------------------------------------------------------------------------

@router.post("/command", tags=["commands"])
@handle_errors()
async def execute_command_api(command_data: Dict[str, Any] = Body(..., description="実行するコマンドのデータ")):
    """
    コマンドを実行する
    
    Args:
        command_data: 実行するコマンドのデータ（名前とパラメータを含む）
        
    Returns:
        コマンド実行の結果
    """
    command_name = command_data.get("command")
    parameters = command_data.get("params", {})
    
    if not command_name:
        error_detail = ErrorDetail(
            code="MISSING_PARAMETER",
            message="Command name is missing",
            context={"provided_data": command_data},
            suggestion="Please provide a 'command' field with the command name"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()
    
    logger.info(f"コマンド実行リクエスト: {command_name}")
    logger.debug(f"パラメータ: {parameters}")
    
    # コマンドを実行
    start_time = time.time()
    try:
        result = await execute_command(command_name, parameters)
        execution_time = time.time() - start_time
        
        # エラーチェック
        if isinstance(result, dict) and result.get("error"):
            error_detail = ErrorDetail(
                code="COMMAND_EXECUTION_FAILED",
                message=f"Command '{command_name}' execution failed",
                context={"command": command_name, "error": result.get("error")}
            )
            return APIResponse.error_response(
                errors=[error_detail.to_dict()]
            ).to_dict()
        
        # 実行結果をログに記録
        logger.info(f"コマンド '{command_name}' を実行しました (実行時間: {execution_time:.3f}s)")
        
        return APIResponse.success_response(data={
            "command": command_name,
            "result": result,
            "execution_time": execution_time
        }).to_dict()
        
    except Exception as e:
        # その他のエラー
        logger.error(f"コマンド '{command_name}' の実行中にエラーが発生しました: {str(e)}")
        error_detail = ErrorDetail(
            code="COMMAND_EXECUTION_FAILED",
            message=f"Command '{command_name}' execution failed: {str(e)}",
            context={"command": command_name, "parameters": parameters}
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()


@router.post("/async/command", tags=["commands"])
@handle_errors()
async def start_async_command(command_data: Dict[str, Any] = Body(..., description="実行するコマンドのデータ")):
    """
    コマンドを非同期で実行を開始する
    
    Args:
        command_data: 実行するコマンドのデータ（名前とパラメータを含む）
        
    Returns:
        タスクIDと初期ステータス
    """
    command_name = command_data.get("command")
    parameters = command_data.get("params", {})
    
    if not command_name:
        error_detail = ErrorDetail(
            code="MISSING_PARAMETER",
            message="Command name is missing",
            context={"provided_data": command_data},
            suggestion="Please provide a 'command' field with the command name"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()
    
    # タスクIDを生成
    task_id = str(uuid.uuid4())
    
    # コマンド実行結果を初期化
    command_result = CommandResult(
        command_id=task_id,
        command_name=command_name,
        status=CommandStatus.PENDING
    )
    
    # 実行タスクを登録
    task_registry[task_id] = command_result
    
    # 非同期タスクを作成
    async def run_command_task():
        start_time = time.time()
        
        # ステータスを実行中に更新
        command_result.update_status(CommandStatus.RUNNING)
        
        try:
            # コマンドを実行
            result = await execute_command(command_name, parameters)
            execution_time = time.time() - start_time
            
            # エラーチェック
            if isinstance(result, dict) and result.get("error"):
                # エラーが含まれている場合
                error_detail = ErrorDetail(
                    code="COMMAND_EXECUTION_FAILED",
                    message=f"Command '{command_name}' execution failed",
                    context={"command": command_name, "error": result.get("error")}
                ).to_dict()
                command_result.fail(error_detail, execution_time)
                return
            
            # 成功結果を設定
            command_result.complete(result, execution_time)
            logger.info(f"非同期コマンド '{command_name}' を完了しました (タスクID: {task_id}, 実行時間: {execution_time:.3f}s)")
            
        except Exception as e:
            # エラー結果を設定
            execution_time = time.time() - start_time
            error_detail = ErrorDetail(
                code="COMMAND_EXECUTION_FAILED",
                message=f"Command '{command_name}' execution failed: {str(e)}",
                context={"command": command_name, "parameters": parameters}
            ).to_dict()
            command_result.fail(error_detail, execution_time)
            logger.error(f"非同期コマンド '{command_name}' が失敗しました (タスクID: {task_id}): {str(e)}")
    
    # 非同期タスクを開始（直ちに返す）
    asyncio.create_task(run_command_task())
    
    logger.info(f"非同期コマンド '{command_name}' を開始しました (タスクID: {task_id})")
    
    # タスク情報を返す
    return APIResponse.success_response(data={
        "task_id": task_id,
        "command": command_name,
        "status": CommandStatus.PENDING.value
    }).to_dict()


@router.get("/task/{task_id}", tags=["commands"])
@handle_errors()
async def get_task_status(task_id: str = Path(..., description="ステータスを取得するタスクID")):
    """
    非同期タスクのステータスを取得
    
    Args:
        task_id: ステータスを取得するタスクID
        
    Returns:
        タスクの現在のステータスと結果（完了している場合）
    """
    if task_id not in task_registry:
        error_detail = ErrorDetail(
            code="TASK_NOT_FOUND",
            message=f"Task ID '{task_id}' not found",
            suggestion="Please provide a valid task ID"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()
    
    # タスクの状態を取得
    command_result = task_registry[task_id]
    
    logger.debug(f"タスクステータス取得: {task_id} (現在のステータス: {command_result.status.value})")
    
    # レスポンス生成
    return APIResponse.success_response(data=command_result.to_dict()).to_dict()


#------------------------------------------------------------------------------
# バッチ処理API
#------------------------------------------------------------------------------

@router.post("/batch", tags=["commands"])
@handle_errors()
async def execute_batch(batch_data: Dict[str, Any] = Body(..., description="バッチコマンドのデータ")):
    """
    複数のコマンドをバッチで実行
    
    Args:
        batch_data: バッチコマンドのデータ
        
    Returns:
        すべてのコマンド実行の結果
    """
    commands_list = batch_data.get("commands", [])
    stop_on_error = batch_data.get("stop_on_error", False)
    
    if not commands_list:
        error_detail = ErrorDetail(
            code="INVALID_REQUEST",
            message="Batch command list is empty",
            suggestion="Please provide a 'commands' field with a list of commands to execute"
        )
        return APIResponse.error_response(
            errors=[error_detail.to_dict()]
        ).to_dict()
    
    logger.info(f"バッチ実行リクエスト: {len(commands_list)}個のコマンド")
    
    # 結果リスト
    results = []
    success_count = 0
    
    # 各コマンドを実行
    for i, command_data in enumerate(commands_list):
        command_name = command_data.get("command")
        parameters = command_data.get("params", {})
        
        if not command_name:
            # コマンド名がない場合はスキップ
            results.append({
                "index": i,
                "success": False,
                "error": ErrorDetail(
                    code="MISSING_PARAMETER",
                    message="Command name is missing"
                ).to_dict()
            })
            
            if stop_on_error:
                break
                
            continue
        
        try:
            # コマンドを実行
            start_time = time.time()
            result = await execute_command(command_name, parameters)
            execution_time = time.time() - start_time
            
            # エラーチェック
            if isinstance(result, dict) and result.get("error"):
                # エラーが含まれている場合
                error_detail = ErrorDetail(
                    code="COMMAND_EXECUTION_FAILED",
                    message=f"Command '{command_name}' execution failed",
                    context={"command": command_name, "error": result.get("error")}
                ).to_dict()
                
                results.append({
                    "index": i,
                    "command": command_name,
                    "success": False,
                    "error": error_detail
                })
                
                if stop_on_error:
                    break
                    
                continue
            
            # 成功結果を追加
            results.append({
                "index": i,
                "command": command_name,
                "success": True,
                "result": result,
                "execution_time": execution_time
            })
            
            success_count += 1
            logger.info(f"バッチコマンド {i+1}/{len(commands_list)} '{command_name}' を実行しました")
            
        except Exception as e:
            # エラー結果を追加
            error_detail = ErrorDetail(
                code="COMMAND_EXECUTION_FAILED",
                message=f"Command '{command_name}' execution failed: {str(e)}",
                context={"command": command_name, "parameters": parameters}
            ).to_dict()
            
            results.append({
                "index": i,
                "command": command_name,
                "success": False,
                "error": error_detail
            })
            
            logger.error(f"バッチコマンド {i+1}/{len(commands_list)} '{command_name}' が失敗しました: {str(e)}")
            
            if stop_on_error:
                logger.info("stop_on_errorが有効なため、バッチ処理を中断します")
                break
    
    # 全体の結果
    batch_success = success_count == len(commands_list)
    partial_success = success_count > 0 and success_count < len(commands_list)
    
    response_data = {
        "success": batch_success,
        "total_commands": len(commands_list),
        "success_count": success_count,
        "results": results
    }
    
    if partial_success:
        return APIResponse(
            success=False,
            data=response_data,
            partial_success={
                "success_count": success_count,
                "total_count": len(commands_list),
                "completed": success_count / len(commands_list)
            }
        ).to_dict()
    else:
        return APIResponse.success_response(data=response_data).to_dict()


# FastAPIが利用可能な場合に限り、エラーハンドラを定義する関数
def register_error_handlers(app):
    """
    FastAPIアプリケーションにエラーハンドラを登録
    
    Args:
        app: FastAPIアプリケーションインスタンス
    """
    if FASTAPI_AVAILABLE:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        
        # カスタムエラーハンドラ
        @app.exception_handler(Exception)
        async def general_exception_handler(request: Request, error: Exception):
            """一般的な例外のハンドラ"""
            logger.error(f"予期しないエラーが発生しました: {str(error)}")
            error_detail = ErrorDetail(
                code="INTERNAL_ERROR",
                message=f"Internal server error: {str(error)}"
            )
            return JSONResponse(
                status_code=500,
                content=APIResponse.error_response(
                    errors=[error_detail.to_dict()]
                ).to_dict()
            )
        
        # HTTPExceptionハンドラ
        @app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, error: HTTPException):
            """HTTPExceptionのハンドラ"""
            error_detail = ErrorDetail(
                code="HTTP_ERROR",
                message=error.detail
            )
            return JSONResponse(
                status_code=error.status_code,
                content=APIResponse.error_response(
                    errors=[error_detail.to_dict()]
                ).to_dict()
            )