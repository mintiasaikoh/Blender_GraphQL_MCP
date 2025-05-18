"""
Unified MCP API ルート定義
拡張されたAPIエンドポイントと機能を提供
"""

import logging
import time
import uuid
import json
from typing import Dict, List, Any, Optional, Callable
import asyncio

from fastapi import APIRouter, HTTPException, Depends, Header, Request, Response
from fastapi.responses import JSONResponse

from . import commands
from .commands import base as cmd_base
from .models import APIResponse, CommandSchema, CommandStatus, CommandResult
from .errors import (
    MCPError, ErrorCodes, CommandNotFoundError, CommandValidationError,
    create_error_response, handle_errors
)

# ロガー設定
logger = logging.getLogger("unified_mcp.api")

# APIルーター
router = APIRouter(prefix="/api/v1")

# コマンド実行メモリ（非永続的）
task_registry = {}  # タスクID -> CommandResult
session_registry = {}  # セッションID -> SessionState


#------------------------------------------------------------------------------
# メタデータAPI
#------------------------------------------------------------------------------

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
    all_commands = cmd_base.get_all_commands()
    command_schemas = []

    for command_name, command_class in all_commands.items():
        # コマンドスキーマを生成
        schema = CommandSchema(
            name=command_name,
            description=command_class.__doc__ or "説明なし",
            parameters=command_class.get_parameter_schema(),
            returns=command_class.get_return_schema(),
            examples=getattr(command_class, "examples", []),
            group=getattr(command_class, "group", "default"),
            tags=getattr(command_class, "tags", []),
            is_dangerous=getattr(command_class, "is_dangerous", False)
        )
        command_schemas.append(schema.to_dict())

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

@router.get("/supported_addons", tags=["metadata"])
@handle_errors()
async def get_supported_addons():
    """
    サポートされているBlenderアドオンの一覧を取得

    Returns:
        サポートされているアドオンの情報
    """
    logger.info("サポートされているアドオン情報をリクエストされました")

    try:
        # サポートされているアドオンリストをインポート
        from ..addons_bridge import SUPPORTED_ADDONS

        # Blender Extensions Marketplaceのアドオン情報
        extensions_info = {
            "marketplace_url": "https://extensions.blender.org/",
            "description": "Blender Extensions Marketplaceは、Blender用の公式アドオン配布プラットフォームです。",
            "supported_version": "Blender 4.2以降",
            "installation_method": "Blender 4.2以降では、Blenderの設定から直接Extensionsタブを使用してインストールできます。"
        }

        # アドオンのカテゴリ別リスト
        categorized_addons = {
            "standard": [addon for addon in SUPPORTED_ADDONS if not addon.startswith("VRM_") and not "_" in addon],
            "modeling": ["simple_deform_helper", "orient_and_origin", "place_helper"],
            "animation": ["animation_nodes"],
            "vtuber": ["VRM_Addon_for_Blender", "mmd_tools"],
            "materials": ["TexTools"],
            "simulation": ["molecular_nodes"],
            "misc": ["quick_groups"]
        }

        # レスポンス生成
        return APIResponse.success_response(data={
            "supported_addons": SUPPORTED_ADDONS,
            "extensions_marketplace": extensions_info,
            "categorized_addons": categorized_addons,
            "blender_version_support": "4.2以降"
        }).to_dict()

    except ImportError as e:
        logger.error(f"サポートされているアドオン情報の取得に失敗しました: {str(e)}")
        raise MCPError(
            message="サポートされているアドオン情報の取得に失敗しました",
            code=ErrorCodes.INTERNAL_ERROR,
            context={"error": str(e)}
        )


@router.get("/commands/{command_name}", tags=["metadata"])
@handle_errors()
async def get_command_schema(command_name: str):
    """
    特定のコマンドのスキーマを取得
    
    Args:
        command_name: スキーマを取得するコマンド名
        
    Returns:
        コマンドのスキーマ
    """
    logger.info(f"コマンド '{command_name}' のスキーマをリクエストされました")
    
    # コマンドを検索
    all_commands = cmd_base.get_all_commands()
    if command_name not in all_commands:
        raise CommandNotFoundError(
            command_name=command_name,
            context={"available_commands": list(all_commands.keys())}
        )
    
    command_class = all_commands[command_name]
    
    # コマンドスキーマを生成
    schema = CommandSchema(
        name=command_name,
        description=command_class.__doc__ or "説明なし",
        parameters=command_class.get_parameter_schema(),
        returns=command_class.get_return_schema(),
        examples=getattr(command_class, "examples", []),
        group=getattr(command_class, "group", "default"),
        tags=getattr(command_class, "tags", []),
        is_dangerous=getattr(command_class, "is_dangerous", False)
    )
    
    # レスポンス生成
    return APIResponse.success_response(data=schema.to_dict()).to_dict()


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
        # アドオンコマンドをインポート
        from .commands.addon_commands import get_all_addons as get_addons_command
        
        # コマンドを実行
        result = get_addons_command()
        
        if result.get("status") != "success":
            raise MCPError(
                message=result.get("message", "アドオン情報の取得に失敗しました"),
                code=ErrorCodes.INTERNAL_ERROR,
                context={"error": result.get("error")}
            )
        
        return APIResponse.success_response(data=result).to_dict()
        
    except ImportError as e:
        logger.error(f"アドオン情報の取得に失敗しました: {str(e)}")
        raise MCPError(
            message="アドオン情報の取得に失敗しました",
            code=ErrorCodes.INTERNAL_ERROR,
            context={"error": str(e)}
        )

@router.get("/addons/{addon_name}", tags=["addons"])
@handle_errors()
async def get_addon_info(addon_name: str):
    """
    特定のアドオン情報を取得
    
    Args:
        addon_name: 情報を取得するアドオン名
        
    Returns:
        アドオン情報
    """
    logger.info(f"アドオン '{addon_name}' の情報をリクエストされました")
    
    try:
        # アドオンコマンドをインポート
        from .commands.addon_commands import get_addon_info as get_addon_command
        
        # コマンドを実行
        result = get_addon_command(addon_name)
        
        if result.get("status") == "error":
            raise MCPError(
                message=result.get("message", f"アドオン '{addon_name}' の情報取得に失敗しました"),
                code=ErrorCodes.NOT_FOUND,
                context={"addon_name": addon_name, "error": result.get("error")}
            )
        
        return APIResponse.success_response(data=result).to_dict()
        
    except ImportError as e:
        logger.error(f"アドオン情報の取得に失敗しました: {str(e)}")
        raise MCPError(
            message="アドオン情報の取得に失敗しました",
            code=ErrorCodes.INTERNAL_ERROR,
            context={"error": str(e)}
        )

@router.post("/addons/{addon_name}/enable", tags=["addons"])
@handle_errors()
async def enable_addon(addon_name: str):
    """
    アドオンを有効化
    
    Args:
        addon_name: 有効化するアドオン名
        
    Returns:
        操作結果
    """
    logger.info(f"アドオン '{addon_name}' の有効化をリクエストされました")
    
    try:
        # アドオンコマンドをインポート
        from .commands.addon_commands import enable_addon as enable_addon_command
        
        # コマンドを実行
        result = enable_addon_command(addon_name)
        
        if result.get("status") == "error":
            raise MCPError(
                message=result.get("message", f"アドオン '{addon_name}' の有効化に失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"addon_name": addon_name, "error": result.get("error")}
            )
        
        return APIResponse.success_response(data=result).to_dict()
        
    except ImportError as e:
        logger.error(f"アドオン操作に失敗しました: {str(e)}")
        raise MCPError(
            message="アドオン操作に失敗しました",
            code=ErrorCodes.INTERNAL_ERROR,
            context={"error": str(e)}
        )

@router.post("/addons/{addon_name}/disable", tags=["addons"])
@handle_errors()
async def disable_addon(addon_name: str):
    """
    アドオンを無効化
    
    Args:
        addon_name: 無効化するアドオン名
        
    Returns:
        操作結果
    """
    logger.info(f"アドオン '{addon_name}' の無効化をリクエストされました")
    
    try:
        # アドオンコマンドをインポート
        from .commands.addon_commands import disable_addon as disable_addon_command
        
        # コマンドを実行
        result = disable_addon_command(addon_name)
        
        if result.get("status") == "error":
            raise MCPError(
                message=result.get("message", f"アドオン '{addon_name}' の無効化に失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"addon_name": addon_name, "error": result.get("error")}
            )
        
        return APIResponse.success_response(data=result).to_dict()
        
    except ImportError as e:
        logger.error(f"アドオン操作に失敗しました: {str(e)}")
        raise MCPError(
            message="アドオン操作に失敗しました",
            code=ErrorCodes.INTERNAL_ERROR,
            context={"error": str(e)}
        )

@router.post("/addons/{addon_name}/update", tags=["addons"])
@handle_errors()
async def update_addon(addon_name: str):
    """
    アドオンを更新
    
    Args:
        addon_name: 更新するアドオン名
        
    Returns:
        操作結果
    """
    logger.info(f"アドオン '{addon_name}' の更新をリクエストされました")
    
    try:
        # アドオンコマンドをインポート
        from .commands.addon_commands import update_addon as update_addon_command
        
        # コマンドを実行
        result = update_addon_command(addon_name)
        
        if result.get("status") == "error":
            raise MCPError(
                message=result.get("message", f"アドオン '{addon_name}' の更新に失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"addon_name": addon_name, "error": result.get("error")}
            )
        
        return APIResponse.success_response(data=result).to_dict()
        
    except ImportError as e:
        logger.error(f"アドオン操作に失敗しました: {str(e)}")
        raise MCPError(
            message="アドオン操作に失敗しました",
            code=ErrorCodes.INTERNAL_ERROR,
            context={"error": str(e)}
        )

@router.post("/addons/install", tags=["addons"])
@handle_errors()
async def install_addon(file_path: str):
    """
    ファイルからアドオンをインストール
    
    Args:
        file_path: インストールするアドオンZIPファイルのパス
        
    Returns:
        操作結果
    """
    logger.info(f"アドオンのインストールをリクエストされました: {file_path}")
    
    try:
        # アドオンコマンドをインポート
        from .commands.addon_commands import install_addon_from_file
        
        # コマンドを実行
        result = install_addon_from_file(file_path)
        
        if result.get("status") == "error":
            raise MCPError(
                message=result.get("message", "アドオンのインストールに失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"file_path": file_path, "error": result.get("error")}
            )
        
        return APIResponse.success_response(data=result).to_dict()
        
    except ImportError as e:
        logger.error(f"アドオン操作に失敗しました: {str(e)}")
        raise MCPError(
            message="アドオン操作に失敗しました",
            code=ErrorCodes.INTERNAL_ERROR,
            context={"error": str(e)}
        )

@router.post("/addons/install-from-url", tags=["addons"])
@handle_errors()
async def install_addon_from_url(url: str):
    """
    URLからアドオンをインストール
    
    Args:
        url: インストールするアドオンZIPファイルのURL
        
    Returns:
        操作結果
    """
    logger.info(f"URLからアドオンのインストールをリクエストされました: {url}")
    
    try:
        # アドオンコマンドをインポート
        from .commands.addon_commands import install_addon_from_url as install_url_command
        
        # コマンドを実行
        result = install_url_command(url)
        
        if result.get("status") == "error":
            raise MCPError(
                message=result.get("message", "URLからのアドオンインストールに失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"url": url, "error": result.get("error")}
            )
        
        return APIResponse.success_response(data=result).to_dict()
        
    except ImportError as e:
        logger.error(f"アドオン操作に失敗しました: {str(e)}")
        raise MCPError(
            message="アドオン操作に失敗しました",
            code=ErrorCodes.INTERNAL_ERROR,
            context={"error": str(e)}
        )

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
        # アドオンコマンドをインポート
        from .commands.addon_commands import check_addon_updates as check_updates_command
        
        # コマンドを実行
        result = check_updates_command()
        
        if result.get("status") == "error":
            raise MCPError(
                message=result.get("message", "アドオン更新の確認に失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"error": result.get("error")}
            )
        
        return APIResponse.success_response(data=result).to_dict()
        
    except ImportError as e:
        logger.error(f"アドオン操作に失敗しました: {str(e)}")
        raise MCPError(
            message="アドオン操作に失敗しました",
            code=ErrorCodes.INTERNAL_ERROR,
            context={"error": str(e)}
        )


#------------------------------------------------------------------------------
# コマンド実行API
#------------------------------------------------------------------------------

@router.post("/command", tags=["commands"])
@handle_errors()
async def execute_command(command_data: Dict[str, Any]):
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
        raise MCPError(
            message="コマンド名が指定されていません",
            code=ErrorCodes.MISSING_PARAMETER,
            context={"provided_data": command_data},
            suggestion="'command'フィールドにコマンド名を指定してください"
        )
    
    logger.info(f"コマンド実行リクエスト: {command_name}")
    logger.debug(f"パラメータ: {parameters}")
    
    # コマンドを実行
    start_time = time.time()
    try:
        result = await cmd_base.execute_command(command_name, parameters)
        execution_time = time.time() - start_time
        
        # 実行結果をログに記録
        logger.info(f"コマンド '{command_name}' を実行しました (実行時間: {execution_time:.3f}s)")
        
        return APIResponse.success_response(data={
            "command": command_name,
            "result": result,
            "execution_time": execution_time
        }).to_dict()
        
    except CommandNotFoundError as e:
        # コマンドが見つからない
        raise e
    
    except Exception as e:
        # その他のエラー
        logger.error(f"コマンド '{command_name}' の実行中にエラーが発生しました: {str(e)}")
        raise MCPError(
            message=f"コマンド '{command_name}' の実行に失敗しました: {str(e)}",
            code=ErrorCodes.COMMAND_EXECUTION_FAILED,
            context={"command": command_name, "parameters": parameters}
        )


@router.post("/async/command", tags=["commands"])
@handle_errors()
async def start_async_command(command_data: Dict[str, Any]):
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
        raise MCPError(
            message="コマンド名が指定されていません",
            code=ErrorCodes.MISSING_PARAMETER,
            context={"provided_data": command_data},
            suggestion="'command'フィールドにコマンド名を指定してください"
        )
    
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
            result = await cmd_base.execute_command(command_name, parameters)
            execution_time = time.time() - start_time
            
            # 成功結果を設定
            command_result.complete(result, execution_time)
            logger.info(f"非同期コマンド '{command_name}' を完了しました (タスクID: {task_id}, 実行時間: {execution_time:.3f}s)")
            
        except Exception as e:
            # エラー結果を設定
            execution_time = time.time() - start_time
            error_info = create_error_response(e)
            command_result.fail(error_info, execution_time)
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
async def get_task_status(task_id: str):
    """
    非同期タスクのステータスを取得
    
    Args:
        task_id: ステータスを取得するタスクID
        
    Returns:
        タスクの現在のステータスと結果（完了している場合）
    """
    if task_id not in task_registry:
        raise MCPError(
            message=f"タスクID '{task_id}' が見つかりません",
            code=ErrorCodes.INVALID_REQUEST,
            suggestion="有効なタスクIDを指定してください"
        )
    
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
async def execute_batch(batch_data: Dict[str, Any]):
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
        raise MCPError(
            message="バッチコマンドリストが空です",
            code=ErrorCodes.INVALID_REQUEST,
            suggestion="'commands'フィールドに実行するコマンドのリストを指定してください"
        )
    
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
                "error": {
                    "code": ErrorCodes.MISSING_PARAMETER,
                    "message": "コマンド名が指定されていません"
                }
            })
            
            if stop_on_error:
                break
                
            continue
        
        try:
            # コマンドを実行
            start_time = time.time()
            result = await cmd_base.execute_command(command_name, parameters)
            execution_time = time.time() - start_time
            
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
            error_info = create_error_response(e)
            results.append({
                "index": i,
                "command": command_name,
                "success": False,
                "error": error_info.get("errors", [{}])[0]
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


#------------------------------------------------------------------------------
# エラーハンドラ
#------------------------------------------------------------------------------

# 注意: エラーハンドラはここでは定義せず、代わりにhttp_server.pyのFastAPIアプリケーションで定義するべきです

# MCPErrorハンドラ関数定義
async def mcp_error_handler(request: Request, error: MCPError):
    """カスタムMCPエラーのハンドラ"""
    return JSONResponse(
        status_code=400,
        content=create_error_response(error)
    )

# 一般例外ハンドラ関数定義
async def general_exception_handler(request: Request, error: Exception):
    """一般的な例外のハンドラ"""
    logger.error(f"予期しないエラーが発生しました: {str(error)}")
    return JSONResponse(
        status_code=500,
        content=create_error_response(error)
    )