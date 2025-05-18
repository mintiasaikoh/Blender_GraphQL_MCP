"""
Blender MCP GraphQL Schema
MCPの機能をGraphQLで公開するスキーマ定義
"""

import json

from tools import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLBoolean,
    GraphQLInt,
    GraphQLFloat,
    GraphQLList,
    GraphQLInputObjectType,
    GraphQLInputField,
    GraphQLNonNull,
    GraphQLArgument
)

from .resolvers.mcp import resolve_execute_raw_command

# 入力型の定義
CommandOptionsInput = GraphQLInputObjectType(
    "CommandOptionsInput",
    fields={
        "generatePreview": GraphQLInputField(GraphQLBoolean),
        "trackHistory": GraphQLInputField(GraphQLBoolean),
        "maxRetries": GraphQLInputField(GraphQLInt),
        "timeout": GraphQLInputField(GraphQLFloat)
    }
)

ContextInput = GraphQLInputObjectType(
    "ContextInput",
    fields={
        "mode": GraphQLInputField(GraphQLString),
        "selectedObjects": GraphQLInputField(GraphQLList(GraphQLString)),
        "activeObject": GraphQLInputField(GraphQLString),
        "viewportSettings": GraphQLInputField(GraphQLString)
    }
)

RenderOptionsInput = GraphQLInputObjectType(
    "RenderOptionsInput",
    fields={
        "width": GraphQLInputField(GraphQLInt),
        "height": GraphQLInputField(GraphQLInt),
        "format": GraphQLInputField(GraphQLString),
        "view": GraphQLInputField(GraphQLString)
    }
)

# 出力型の定義
LocationType = GraphQLObjectType(
    "Location",
    fields={
        "x": GraphQLField(GraphQLFloat),
        "y": GraphQLField(GraphQLFloat),
        "z": GraphQLField(GraphQLFloat)
    }
)

ObjectInfoType = GraphQLObjectType(
    "ObjectInfo",
    fields={
        "id": GraphQLField(GraphQLString),
        "name": GraphQLField(GraphQLString),
        "type": GraphQLField(GraphQLString),
        "location": GraphQLField(LocationType),
        "selected": GraphQLField(GraphQLBoolean)
    }
)

SceneContextType = GraphQLObjectType(
    "SceneContext",
    fields={
        "name": GraphQLField(GraphQLString),
        "framesCurrent": GraphQLField(GraphQLInt),
        "objectCount": GraphQLField(GraphQLInt),
        "selectedObjects": GraphQLField(GraphQLList(ObjectInfoType)),
        "activeObject": GraphQLField(ObjectInfoType),
        "mode": GraphQLField(GraphQLString)
    }
)

PreviewType = GraphQLObjectType(
    "Preview",
    fields={
        "imageUrl": GraphQLField(GraphQLString),
        "format": GraphQLField(GraphQLString),
        "resolution": GraphQLField(GraphQLList(GraphQLInt)),
        "viewport": GraphQLField(GraphQLString)
    }
)

ExecutionResultType = GraphQLObjectType(
    "ExecutionResult",
    fields={
        "success": GraphQLField(GraphQLBoolean),
        "command": GraphQLField(GraphQLString),
        "result": GraphQLField(GraphQLString),
        "error": GraphQLField(GraphQLString),
        "executionTime": GraphQLField(GraphQLFloat)
    }
)

CommandResultType = GraphQLObjectType(
    "CommandResult",
    fields={
        "success": GraphQLField(GraphQLBoolean),
        "generatedCode": GraphQLField(GraphQLString),
        "executedCode": GraphQLField(GraphQLString),
        "executionResult": GraphQLField(ExecutionResultType),
        "preview": GraphQLField(PreviewType),
        "context": GraphQLField(SceneContextType),
        "contextBefore": GraphQLField(SceneContextType),
        "contextAfter": GraphQLField(SceneContextType),
        "suggestions": GraphQLField(GraphQLList(GraphQLString)),
        "changes": GraphQLField(GraphQLList(IterationChangeType)),
        "error": GraphQLField(GraphQLString),
        "result": GraphQLField(GraphQLString)
    }
)

IterationChangeType = GraphQLObjectType(
    "IterationChange",
    fields={
        "type": GraphQLField(GraphQLString),
        "object": GraphQLField(GraphQLString),
        "description": GraphQLField(GraphQLString)
    }
)

IterationResultType = GraphQLObjectType(
    "IterationResult",
    fields={
        "success": GraphQLField(GraphQLBoolean),
        "modelId": GraphQLField(GraphQLString),
        "changes": GraphQLField(GraphQLList(IterationChangeType)),
        "preview": GraphQLField(GraphQLString),
        "error": GraphQLField(GraphQLString)
    }
)

# クエリ型
MCPQueryType = GraphQLObjectType(
    "MCPQuery",
    fields={
        "sceneContext": GraphQLField(
            SceneContextType,
            resolve=lambda root, info: info.context["mcp"].context_manager.get_complete_context()
        ),
        "selectedObjects": GraphQLField(
            GraphQLList(ObjectInfoType),
            resolve=lambda root, info: info.context["mcp"].context_manager.get_selected_objects()
        ),
        "availableOperations": GraphQLField(
            GraphQLList(GraphQLString),
            args={
                "context": GraphQLArgument(GraphQLString)
            },
            resolve=lambda root, info, context=None: 
                info.context["mcp"].context_manager._get_available_operations()
        ),
        "executionStats": GraphQLField(
            GraphQLString,
            resolve=lambda root, info: 
                info.context["mcp"].command_executor.get_execution_stats()
        )
    }
)

# ミューテーション型
MCPMutationType = GraphQLObjectType(
    "MCPMutation",
    fields={
        "executeNaturalCommand": GraphQLField(
            CommandResultType,
            args={
                "command": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                "options": GraphQLArgument(CommandOptionsInput)
            },
            resolve=lambda root, info, command, options=None:
                info.context["mcp"].process_natural_command(command, options)
        ),
        "executeWithContext": GraphQLField(
            CommandResultType,
            args={
                "command": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                "context": GraphQLArgument(ContextInput)
            },
            resolve=lambda root, info, command, context=None:
                info.context["mcp"].execute_with_context(command, context)
        ),
        "iterateOnModel": GraphQLField(
            IterationResultType,
            args={
                "modelId": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                "feedback": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                "renderOptions": GraphQLArgument(RenderOptionsInput)
            },
            resolve=lambda root, info, modelId, feedback, renderOptions=None:
                info.context["mcp"].iterate_on_model(modelId, feedback, renderOptions)
        ),
        "capturePreview": GraphQLField(
            PreviewType,
            args={
                "width": GraphQLArgument(GraphQLInt),
                "height": GraphQLArgument(GraphQLInt),
                "view": GraphQLArgument(GraphQLString)
            },
            resolve=lambda root, info, width=512, height=512, view="current":
                info.context["mcp"].preview_generator.capture_viewport(
                    resolution=(width, height),
                    view=view
                )
        ),
        "executeRawCommand": GraphQLField(
            CommandResultType,
            args={
                "pythonCode": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                "metadata": GraphQLArgument(GraphQLString)
            },
            resolve=resolve_execute_raw_command
        )
    }
)

# MCPスキーマの作成
def create_mcp_schema():
    """MCP用のGraphQLスキーマを作成"""
    return GraphQLSchema(
        query=MCPQueryType,
        mutation=MCPMutationType
    )

# 既存のスキーマと統合するヘルパー関数
def integrate_mcp_schema(existing_schema):
    """既存のスキーマにMCP機能を統合"""
    # 既存のクエリとミューテーションフィールドを取得
    existing_query_fields = existing_schema.query_type.fields if existing_schema.query_type else {}
    existing_mutation_fields = existing_schema.mutation_type.fields if existing_schema.mutation_type else {}
    
    # MCPフィールドを追加
    mcp_query_fields = MCPQueryType.fields
    mcp_mutation_fields = MCPMutationType.fields
    
    # 統合されたクエリタイプ
    integrated_query = GraphQLObjectType(
        "Query",
        fields={**existing_query_fields, **mcp_query_fields}
    )
    
    # 統合されたミューテーションタイプ
    integrated_mutation = GraphQLObjectType(
        "Mutation",
        fields={**existing_mutation_fields, **mcp_mutation_fields}
    )
    
    return GraphQLSchema(
        query=integrated_query,
        mutation=integrated_mutation
    )