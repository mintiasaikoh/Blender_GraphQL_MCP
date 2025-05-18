"""
Blender MCP GraphQL Schema - 改善版
標準化されたスキーマコンポーネントを使用したMCPの機能をGraphQLで公開するスキーマ定義
"""

import json
import logging
from typing import Dict, Any, List, Optional

from tools import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLBoolean,
    GraphQLInt,
    GraphQLFloat,
    GraphQLList,
    GraphQLNonNull,
    GraphQLArgument
)

# スキーマレジストリをインポート
from tools.schema_registry import schema_registry

# 基本スキーマコンポーネントをインポート
from tools.schema_base import (
    operation_result_interface,
    create_operation_result_type
)

# 入力型コンポーネントをインポート
from tools.schema_inputs import (
    execution_options_input,
    render_params_input,
    vector3_input
)

# リゾルバをインポート
from tools.handlers.improved_mcp import (
    resolve_scene_context,
    resolve_selected_objects,
    resolve_available_operations,
    resolve_execution_stats,
    resolve_execute_natural_command,
    resolve_execute_with_context,
    resolve_iterate_on_model,
    resolve_capture_preview,
    resolve_execute_raw_command
)

logger = logging.getLogger('blender_mcp.tools.schema_improved_mcp')

# コンテキスト入力型の定義（既存との互換性のため）
context_input = GraphQLInputObjectType(
    "ContextInput",
    fields={
        "mode": GraphQLInputField(GraphQLString),
        "selectedObjects": GraphQLInputField(GraphQLList(GraphQLString)),
        "activeObject": GraphQLInputField(GraphQLString),
        "viewportSettings": GraphQLInputField(GraphQLString)
    }
)

# 出力型の定義
location_type = GraphQLObjectType(
    "Location",
    fields={
        "x": GraphQLField(GraphQLFloat),
        "y": GraphQLField(GraphQLFloat),
        "z": GraphQLField(GraphQLFloat)
    }
)

object_info_type = GraphQLObjectType(
    "ObjectInfo",
    fields={
        "id": GraphQLField(GraphQLString),
        "name": GraphQLField(GraphQLString),
        "type": GraphQLField(GraphQLString),
        "location": GraphQLField(location_type),
        "selected": GraphQLField(GraphQLBoolean)
    }
)

scene_context_type = GraphQLObjectType(
    "SceneContext",
    fields={
        "name": GraphQLField(GraphQLString),
        "framesCurrent": GraphQLField(GraphQLInt),
        "objectCount": GraphQLField(GraphQLInt),
        "selectedObjects": GraphQLField(GraphQLList(object_info_type)),
        "activeObject": GraphQLField(object_info_type),
        "mode": GraphQLField(GraphQLString)
    }
)

preview_type = GraphQLObjectType(
    "Preview",
    fields={
        "imageUrl": GraphQLField(GraphQLString),
        "format": GraphQLField(GraphQLString),
        "resolution": GraphQLField(GraphQLList(GraphQLInt)),
        "viewport": GraphQLField(GraphQLString)
    }
)

execution_result_type = GraphQLObjectType(
    "ExecutionResult",
    fields={
        "success": GraphQLField(GraphQLBoolean),
        "command": GraphQLField(GraphQLString),
        "result": GraphQLField(GraphQLString),
        "error": GraphQLField(GraphQLString),
        "executionTime": GraphQLField(GraphQLFloat)
    }
)

iteration_change_type = GraphQLObjectType(
    "IterationChange",
    fields={
        "type": GraphQLField(GraphQLString),
        "object": GraphQLField(GraphQLString),
        "description": GraphQLField(GraphQLString)
    }
)

# 操作結果型の定義（OperationResultインターフェースを実装）
command_result_type = create_operation_result_type(
    "CommandResult",
    "コマンド実行結果",
    {
        "generatedCode": GraphQLField(GraphQLString, description="生成されたコード"),
        "executedCode": GraphQLField(GraphQLString, description="実行されたコード"),
        "executionResult": GraphQLField(execution_result_type, description="実行結果詳細"),
        "preview": GraphQLField(preview_type, description="プレビュー画像"),
        "context": GraphQLField(scene_context_type, description="現在のコンテキスト"),
        "contextBefore": GraphQLField(scene_context_type, description="実行前のコンテキスト"),
        "contextAfter": GraphQLField(scene_context_type, description="実行後のコンテキスト"),
        "suggestions": GraphQLField(GraphQLList(GraphQLString), description="提案"),
        "changes": GraphQLField(GraphQLList(iteration_change_type), description="変更点"),
        "result": GraphQLField(GraphQLString, description="実行結果")
    }
)

iteration_result_type = create_operation_result_type(
    "IterationResult",
    "モデル反復改善結果",
    {
        "modelId": GraphQLField(GraphQLString, description="モデルID"),
        "changes": GraphQLField(GraphQLList(iteration_change_type), description="変更点"),
        "preview": GraphQLField(GraphQLString, description="プレビュー画像")
    }
)

scene_context_result_type = create_operation_result_type(
    "SceneContextResult",
    "シーンコンテキスト取得結果",
    {
        "name": GraphQLField(GraphQLString, description="シーン名"),
        "framesCurrent": GraphQLField(GraphQLInt, description="現在のフレーム番号"),
        "objectCount": GraphQLField(GraphQLInt, description="オブジェクト数"),
        "selectedObjects": GraphQLField(GraphQLList(object_info_type), description="選択されたオブジェクト"),
        "activeObject": GraphQLField(object_info_type, description="アクティブなオブジェクト"),
        "mode": GraphQLField(GraphQLString, description="現在のモード")
    }
)

objects_result_type = create_operation_result_type(
    "ObjectsResult",
    "オブジェクト取得結果",
    {
        "objects": GraphQLField(GraphQLList(object_info_type), description="オブジェクトリスト")
    }
)

operations_result_type = create_operation_result_type(
    "OperationsResult",
    "利用可能な操作取得結果",
    {
        "operations": GraphQLField(GraphQLList(GraphQLString), description="利用可能な操作リスト")
    }
)

stats_result_type = create_operation_result_type(
    "StatsResult",
    "実行統計取得結果",
    {
        "stats": GraphQLField(GraphQLString, description="実行統計JSON")
    }
)

capture_preview_result_type = create_operation_result_type(
    "CapturePreviewResult",
    "プレビューキャプチャ結果",
    {
        "preview": GraphQLField(preview_type, description="プレビュー画像情報")
    }
)

# ドメイン.操作形式のフィールド名で定義されたクエリとミューテーション
query_fields = {
    "scene.context": GraphQLField(
        scene_context_result_type,
        description="現在のシーンコンテキストを取得",
        resolve=resolve_scene_context
    ),
    "scene.selectedObjects": GraphQLField(
        objects_result_type,
        description="選択されたオブジェクトを取得",
        resolve=resolve_selected_objects
    ),
    "scene.availableOperations": GraphQLField(
        operations_result_type,
        args={
            "context": GraphQLArgument(GraphQLString, description="コンテキスト情報")
        },
        description="利用可能な操作リストを取得",
        resolve=resolve_available_operations
    ),
    "execution.stats": GraphQLField(
        stats_result_type,
        description="実行統計を取得",
        resolve=resolve_execution_stats
    )
}

mutation_fields = {
    "command.executeNatural": GraphQLField(
        command_result_type,
        args={
            "command": GraphQLArgument(GraphQLNonNull(GraphQLString), description="自然言語コマンド"),
            "options": GraphQLArgument(execution_options_input, description="実行オプション")
        },
        description="自然言語コマンドを実行",
        resolve=resolve_execute_natural_command
    ),
    "command.executeWithContext": GraphQLField(
        command_result_type,
        args={
            "command": GraphQLArgument(GraphQLNonNull(GraphQLString), description="コマンド"),
            "context": GraphQLArgument(context_input, description="コンテキスト情報")
        },
        description="コンテキスト付きでコマンドを実行",
        resolve=resolve_execute_with_context
    ),
    "model.iterate": GraphQLField(
        iteration_result_type,
        args={
            "modelId": GraphQLArgument(GraphQLNonNull(GraphQLString), description="モデルID"),
            "feedback": GraphQLArgument(GraphQLNonNull(GraphQLString), description="フィードバック"),
            "renderOptions": GraphQLArgument(render_params_input, description="レンダリングオプション")
        },
        description="モデルの反復的改善",
        resolve=resolve_iterate_on_model
    ),
    "scene.capturePreview": GraphQLField(
        capture_preview_result_type,
        args={
            "width": GraphQLArgument(GraphQLInt, description="幅"),
            "height": GraphQLArgument(GraphQLInt, description="高さ"),
            "view": GraphQLArgument(GraphQLString, description="ビュー")
        },
        description="プレビューをキャプチャ",
        resolve=resolve_capture_preview
    ),
    "command.executeRaw": GraphQLField(
        command_result_type,
        args={
            "pythonCode": GraphQLArgument(GraphQLNonNull(GraphQLString), description="Pythonコード"),
            "metadata": GraphQLArgument(GraphQLString, description="メタデータ（JSON）")
        },
        description="Pythonコードを直接実行",
        resolve=resolve_execute_raw_command
    )
}

# 非推奨の従来命名形式のフィールド（互換性のため）
deprecated_query_fields = {
    "sceneContext": GraphQLField(
        scene_context_result_type,
        description="現在のシーンコンテキストを取得（非推奨: 代わりに scene.context を使用してください）",
        deprecation_reason="非推奨: 代わりに scene.context を使用してください",
        resolve=resolve_scene_context
    ),
    "selectedObjects": GraphQLField(
        objects_result_type,
        description="選択されたオブジェクトを取得（非推奨: 代わりに scene.selectedObjects を使用してください）",
        deprecation_reason="非推奨: 代わりに scene.selectedObjects を使用してください",
        resolve=resolve_selected_objects
    )
}

deprecated_mutation_fields = {
    "executeNaturalCommand": GraphQLField(
        command_result_type,
        args={
            "command": GraphQLArgument(GraphQLNonNull(GraphQLString), description="自然言語コマンド"),
            "options": GraphQLArgument(execution_options_input, description="実行オプション")
        },
        description="自然言語コマンドを実行（非推奨: 代わりに command.executeNatural を使用してください）",
        deprecation_reason="非推奨: 代わりに command.executeNatural を使用してください",
        resolve=resolve_execute_natural_command
    ),
    "executeWithContext": GraphQLField(
        command_result_type,
        args={
            "command": GraphQLArgument(GraphQLNonNull(GraphQLString), description="コマンド"),
            "context": GraphQLArgument(context_input, description="コンテキスト情報")
        },
        description="コンテキスト付きでコマンドを実行（非推奨: 代わりに command.executeWithContext を使用してください）",
        deprecation_reason="非推奨: 代わりに command.executeWithContext を使用してください",
        resolve=resolve_execute_with_context
    ),
    "executeRawCommand": GraphQLField(
        command_result_type,
        args={
            "pythonCode": GraphQLArgument(GraphQLNonNull(GraphQLString), description="Pythonコード"),
            "metadata": GraphQLArgument(GraphQLString, description="メタデータ（JSON）")
        },
        description="Pythonコードを直接実行（非推奨: 代わりに command.executeRaw を使用してください）",
        deprecation_reason="非推奨: 代わりに command.executeRaw を使用してください",
        resolve=resolve_execute_raw_command
    )
}

# スキーマレジストリに型を登録
def register_improved_mcp_types():
    """改善されたMCP型をスキーマレジストリに登録"""
    # 入力型
    schema_registry.register_type("ContextInput", context_input)
    
    # 出力型
    schema_registry.register_type("Location", location_type)
    schema_registry.register_type("ObjectInfo", object_info_type)
    schema_registry.register_type("SceneContext", scene_context_type)
    schema_registry.register_type("Preview", preview_type)
    schema_registry.register_type("ExecutionResult", execution_result_type)
    schema_registry.register_type("IterationChange", iteration_change_type)
    
    # 結果型
    schema_registry.register_type("CommandResult", command_result_type)
    schema_registry.register_type("IterationResult", iteration_result_type)
    schema_registry.register_type("SceneContextResult", scene_context_result_type)
    schema_registry.register_type("ObjectsResult", objects_result_type)
    schema_registry.register_type("OperationsResult", operations_result_type)
    schema_registry.register_type("StatsResult", stats_result_type)
    schema_registry.register_type("CapturePreviewResult", capture_preview_result_type)
    
    # クエリとミューテーションフィールドを登録
    for name, field in query_fields.items():
        schema_registry.register_query(name, field)
        
    for name, field in mutation_fields.items():
        schema_registry.register_mutation(name, field)
    
    # 非推奨フィールドも登録
    for name, field in deprecated_query_fields.items():
        schema_registry.register_query(name, field)
        
    for name, field in deprecated_mutation_fields.items():
        schema_registry.register_mutation(name, field)
    
    # コンポーネント登録
    schema_registry.register_component("schema_improved_mcp")
    
    logger.info("改善されたMCPスキーマを登録しました")

# スキーマレジストリに登録
register_improved_mcp_types()