"""
Blender GraphQL MCP - 基本スキーマ定義
GraphQLスキーマのコア型と共通インターフェース
"""

import logging
from enum import Enum
from typing import Dict, Any, Optional, List, Callable

# GraphQL関連のインポート
from tools import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLInterfaceType,
    GraphQLEnumType,
    GraphQLField,
    GraphQLString,
    GraphQLBoolean,
    GraphQLFloat,
    GraphQLList,
    GraphQLNonNull,
    GraphQLArgument
)

# スキーマレジストリのインポート
from tools.schema_registry import schema_registry

logger = logging.getLogger("blender_graphql_mcp.tools.schema_base")

# エラーカテゴリの定義
error_category_enum = GraphQLEnumType(
    name="ErrorCategory",
    values={
        "USER_INPUT": {
            "value": "USER_INPUT",
            "description": "ユーザー入力に関するエラー（バリデーションエラーなど）"
        },
        "PERMISSION": {
            "value": "PERMISSION",
            "description": "権限に関するエラー"
        },
        "RESOURCE_NOT_FOUND": {
            "value": "RESOURCE_NOT_FOUND",
            "description": "リソースが見つからないエラー"
        },
        "SYSTEM": {
            "value": "SYSTEM",
            "description": "システム内部エラー"
        },
        "OPERATION_FAILED": {
            "value": "OPERATION_FAILED",
            "description": "操作が失敗したエラー"
        }
    }
)

# エラー型の定義
error_type = GraphQLObjectType(
    name="Error",
    fields={
        "code": GraphQLField(
            GraphQLNonNull(GraphQLString),
            description="エラーコード"
        ),
        "message": GraphQLField(
            GraphQLNonNull(GraphQLString),
            description="エラーメッセージ"
        ),
        "category": GraphQLField(
            error_category_enum,
            description="エラーカテゴリ"
        ),
        "details": GraphQLField(
            GraphQLString,
            description="エラーの詳細情報"
        ),
        "path": GraphQLField(
            GraphQLList(GraphQLString),
            description="エラーが発生した場所のパス"
        ),
        "suggestions": GraphQLField(
            GraphQLList(GraphQLString),
            description="解決のための提案"
        )
    }
)

# 操作結果インターフェースの定義
operation_result_interface = GraphQLInterfaceType(
    name="OperationResult",
    fields={
        "success": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            description="操作が成功したかどうか"
        ),
        "message": GraphQLField(
            GraphQLString,
            description="操作の結果メッセージ"
        ),
        "error": GraphQLField(
            error_type,
            description="エラー情報（エラー発生時のみ）"
        ),
        "executionTimeMs": GraphQLField(
            GraphQLFloat,
            description="実行時間（ミリ秒）"
        )
    },
    resolve_type=lambda obj, *_: obj.get("__typename", "GenericOperationResult")
)

# 基本的な操作結果型の定義
basic_operation_result = GraphQLObjectType(
    name="BasicOperationResult",
    fields={
        "success": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            description="操作が成功したかどうか"
        ),
        "message": GraphQLField(
            GraphQLString,
            description="操作の結果メッセージ"
        ),
        "error": GraphQLField(
            error_type,
            description="エラー情報（エラー発生時のみ）"
        ),
        "executionTimeMs": GraphQLField(
            GraphQLFloat,
            description="実行時間（ミリ秒）"
        )
    },
    interfaces=[operation_result_interface]
)

def create_operation_result_type(
    name: str,
    description: str,
    additional_fields: Dict[str, GraphQLField] = None
) -> GraphQLObjectType:
    """操作結果型を生成するヘルパー関数

    Args:
        name: 型名
        description: 型の説明
        additional_fields: 追加のフィールド定義

    Returns:
        GraphQLObjectType: 生成された操作結果型
    """
    fields = {
        "success": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            description="操作が成功したかどうか"
        ),
        "message": GraphQLField(
            GraphQLString,
            description="操作の結果メッセージ"
        ),
        "error": GraphQLField(
            error_type,
            description="エラー情報（エラー発生時のみ）"
        ),
        "executionTimeMs": GraphQLField(
            GraphQLFloat,
            description="実行時間（ミリ秒）"
        )
    }

    # 追加フィールドがあれば統合
    if additional_fields:
        fields.update(additional_fields)

    return GraphQLObjectType(
        name=name,
        description=description,
        fields=fields,
        interfaces=[operation_result_interface]
    )

def create_error(
    code: str,
    message: str,
    category: str = "SYSTEM",
    details: Optional[str] = None,
    path: Optional[List[str]] = None,
    suggestions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """エラーオブジェクトを生成するヘルパー関数

    Args:
        code: エラーコード
        message: エラーメッセージ
        category: エラーカテゴリ（ErrorCategory列挙型の値）
        details: エラーの詳細情報
        path: エラーが発生した場所のパス
        suggestions: 解決のための提案

    Returns:
        Dict[str, Any]: エラーオブジェクト
    """
    error = {
        "code": code,
        "message": message,
        "category": category
    }

    if details:
        error["details"] = details

    if path:
        error["path"] = path

    if suggestions:
        error["suggestions"] = suggestions

    return error

def create_success_result(
    message: Optional[str] = None,
    execution_time_ms: Optional[float] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """成功結果を生成するヘルパー関数

    Args:
        message: 結果メッセージ
        execution_time_ms: 実行時間（ミリ秒）
        additional_data: 追加データ

    Returns:
        Dict[str, Any]: 成功結果オブジェクト
    """
    result = {
        "success": True
    }

    if message:
        result["message"] = message

    if execution_time_ms:
        result["executionTimeMs"] = execution_time_ms

    # 追加データがあれば統合
    if additional_data:
        result.update(additional_data)

    return result

def create_error_result(
    code: str,
    message: str,
    category: str = "SYSTEM",
    details: Optional[str] = None,
    path: Optional[List[str]] = None,
    suggestions: Optional[List[str]] = None,
    execution_time_ms: Optional[float] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """エラー結果を生成するヘルパー関数

    Args:
        code: エラーコード
        message: エラーメッセージ
        category: エラーカテゴリ
        details: 詳細情報
        path: エラーパス
        suggestions: 解決提案
        execution_time_ms: 実行時間（ミリ秒）
        additional_data: 追加データ

    Returns:
        Dict[str, Any]: エラー結果オブジェクト
    """
    error = create_error(
        code=code,
        message=message,
        category=category,
        details=details,
        path=path,
        suggestions=suggestions
    )

    result = {
        "success": False,
        "message": message,
        "error": error
    }

    if execution_time_ms:
        result["executionTimeMs"] = execution_time_ms

    # 追加データがあれば統合
    if additional_data:
        result.update(additional_data)

    return result

def register_base_types():
    """基本型をスキーマレジストリに登録"""
    schema_registry.register_type("ErrorCategory", error_category_enum)
    schema_registry.register_type("Error", error_type)
    schema_registry.register_type("OperationResult", operation_result_interface)
    schema_registry.register_type("BasicOperationResult", basic_operation_result)
    schema_registry.register_component("schema_base")
    logger.info("基本スキーマ型を登録しました")

# スキーマレジストリへの登録
register_base_types()