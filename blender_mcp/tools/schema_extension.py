"""
GraphQLスキーマ拡張モジュール
バッチ処理、トランザクション、タスクキュー関連の型と機能をGraphQLスキーマに追加
LLM向けの機能を統合
"""

import logging
import traceback
import json
from typing import Dict, Any, List, Optional

# ロギング設定
logger = logging.getLogger('blender_graphql_mcp.tools.definitions_extension')

def extend_schema(schema):
    """
    既存のGraphQLスキーマに拡張機能を追加
    
    Args:
        schema: 拡張する既存のGraphQLスキーマ
        
    Returns:
        拡張されたスキーマ
    """
    try:
        from tools import (
            GraphQLSchema, GraphQLObjectType, GraphQLString, GraphQLInt, GraphQLFloat,
            GraphQLBoolean, GraphQLID, GraphQLList, GraphQLNonNull, GraphQLField,
            GraphQLArgument, GraphQLInputObjectType, GraphQLInputField, GraphQLEnumType,
            GraphQLEnumValue
        )
        
        # リゾルバをインポート
        from . import batch_transaction_resolvers
        
        # タスクキュースキーマのインポートを試行
        try:
            from . import task_queue_schema
            TASK_QUEUE_AVAILABLE = True
            logger.info("タスクキュースキーマをインポートしました")
        except ImportError as e:
            logger.warning(f"タスクキュースキーマのインポートに失敗しました: {e}")
            TASK_QUEUE_AVAILABLE = False
            
        # LLMヘルパーのインポートを試行
        try:
            from . import llm_schema_helpers
            LLM_HELPERS_AVAILABLE = True
            logger.info("LLMスキーマヘルパーをインポートしました")
        except ImportError as e:
            logger.warning(f"LLMスキーマヘルパーのインポートに失敗しました: {e}")
            LLM_HELPERS_AVAILABLE = False
        
        # 既存のクエリとミューテーション型を取得
        query_type = schema.get_query_type()
        mutation_type = schema.get_mutation_type()
        
        if not mutation_type:
            logger.error("ミューテーション型が見つかりません。スキーマを拡張できません。")
            return schema
            
        # バッチ結果型
        batch_result_type = GraphQLObjectType(
            name='BatchResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='バッチ処理が成功したかどうか'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                'commandCount': GraphQLField(GraphQLInt, description='コマンド数'),
                'successfulCommands': GraphQLField(GraphQLInt, description='成功したコマンド数'),
                'executionTimeMs': GraphQLField(GraphQLFloat, description='実行時間（ミリ秒）'),
                'results': GraphQLField(GraphQLString, description='結果のJSON文字列')
            }
        )
        
        # トランザクション結果型
        transaction_result_type = GraphQLObjectType(
            name='TransactionResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='トランザクションが成功したかどうか'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                'transactionId': GraphQLField(GraphQLID, description='トランザクションID'),
                'transactionName': GraphQLField(GraphQLString, description='トランザクション名'),
                'commandCount': GraphQLField(GraphQLInt, description='コマンド数'),
                'executedCommands': GraphQLField(GraphQLInt, description='実行したコマンド数'),
                'executionTimeMs': GraphQLField(GraphQLFloat, description='実行時間（ミリ秒）'),
                'results': GraphQLField(GraphQLString, description='結果のJSON文字列')
            }
        )
        
        # 新しいフィールドを追加
        mutation_fields = dict(mutation_type.fields)
        
        # バッチ実行ミューテーション
        mutation_fields['executeBatch'] = GraphQLField(
            batch_result_type,
            description='複数のコマンドをバッチで実行',
            args={
                'commands_json': GraphQLArgument(GraphQLNonNull(GraphQLString), description='JSON形式のコマンドリスト')
            },
            resolve=batch_transaction_resolvers.resolve_execute_batch
        )
        
        # トランザクション作成ミューテーション
        mutation_fields['createTransaction'] = GraphQLField(
            transaction_result_type,
            description='新しいトランザクションを作成',
            args={
                'name': GraphQLArgument(GraphQLString, description='トランザクション名（オプション）'),
                'commands_json': GraphQLArgument(GraphQLString, description='JSON形式のコマンドリスト（オプション）')
            },
            resolve=batch_transaction_resolvers.resolve_create_transaction
        )
        
        # トランザクション実行ミューテーション
        mutation_fields['executeTransaction'] = GraphQLField(
            transaction_result_type,
            description='既存のトランザクションを実行',
            args={
                'transaction_id': GraphQLArgument(GraphQLNonNull(GraphQLID), description='トランザクションID'),
                'create_snapshot': GraphQLArgument(GraphQLBoolean, description='スナップショットを作成するかどうか', default_value=True)
            },
            resolve=batch_transaction_resolvers.resolve_execute_transaction
        )
        
        # 新しいミューテーション型を作成
        new_mutation_type = GraphQLObjectType(
            name='Mutation',
            fields=mutation_fields
        )
        
        # LLM向けのクエリフィールドを追加
        query_fields = dict(query_type.fields)
        
        if LLM_HELPERS_AVAILABLE:
            # LLM向け関数情報クエリ
            query_fields['_llmFunctionInfo'] = GraphQLField(
                GraphQLString,
                description='LLM向けの関数情報を取得します',
                args={
                    'functionName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='情報を取得する関数名')
                },
                resolve=resolve_llm_function_info
            )
            
            # LLM向け関数リストクエリ
            query_fields['_llmFunctionList'] = GraphQLField(
                GraphQLString,
                description='利用可能な関数リストをJSON形式で取得します',
                resolve=resolve_llm_function_list
            )
            
            # LLM向けスキーマドキュメントクエリ
            query_fields['_llmSchemaDoc'] = GraphQLField(
                GraphQLString,
                description='LLM向けのスキーマドキュメントをMarkdown形式で取得します',
                resolve=resolve_llm_schema_doc
            )
            
            logger.info("LLM向けクエリをスキーマに追加しました")
        
        # 新しいクエリ型を作成
        new_query_type = GraphQLObjectType(
            name='Query',
            fields=query_fields
        )
        
        # 拡張されたスキーマを作成
        extended_schema = GraphQLSchema(
            query=new_query_type,
            mutation=new_mutation_type,
            types=schema.get_type_map().values()
        )
        
        # タスクキュー機能の追加（利用可能な場合）
        if TASK_QUEUE_AVAILABLE:
            try:
                logger.info("タスクキュー機能をスキーマに追加します")
                
                # タスク状態の列挙型
                task_status_enum = GraphQLEnumType(
                    name='TaskStatus',
                    values={
                        'PENDING': GraphQLEnumValue(),
                        'RUNNING': GraphQLEnumValue(),
                        'COMPLETED': GraphQLEnumValue(),
                        'FAILED': GraphQLEnumValue(),
                        'CANCELLED': GraphQLEnumValue()
                    }
                )
                
                # タスク型
                task_type = GraphQLObjectType(
                    name='Task',
                    fields={
                        'id': GraphQLField(GraphQLID, description='タスクID'),
                        'name': GraphQLField(GraphQLString, description='タスク名'),
                        'type': GraphQLField(GraphQLString, description='タスクタイプ'),
                        'status': GraphQLField(task_status_enum, description='タスク状態'),
                        'priority': GraphQLField(GraphQLInt, description='優先度'),
                        'created_at': GraphQLField(GraphQLFloat, description='作成時刻（UNIX時間）'),
                        'started_at': GraphQLField(GraphQLFloat, description='開始時刻（UNIX時間）'),
                        'completed_at': GraphQLField(GraphQLFloat, description='完了時刻（UNIX時間）'),
                        'progress': GraphQLField(GraphQLFloat, description='進捗状況（0.0-1.0）'),
                        'message': GraphQLField(GraphQLString, description='最新メッセージ'),
                        'result': GraphQLField(GraphQLString, description='タスク結果（JSON文字列）'),
                        'error': GraphQLField(GraphQLString, description='エラーメッセージ')
                    }
                )
                
                # タスクキュー情報型
                task_queue_info_type = GraphQLObjectType(
                    name='TaskQueueInfo',
                    fields={
                        'running': GraphQLField(GraphQLBoolean, description='実行状態'),
                        'worker_count': GraphQLField(GraphQLInt, description='ワーカー数'),
                        'pending_tasks': GraphQLField(GraphQLInt, description='待機中タスク数'),
                        'running_tasks': GraphQLField(GraphQLInt, description='実行中タスク数'),
                        'completed_tasks': GraphQLField(GraphQLInt, description='完了タスク数'),
                        'failed_tasks': GraphQLField(GraphQLInt, description='失敗タスク数'),
                        'tasks': GraphQLField(GraphQLList(task_type), description='タスク一覧')
                    }
                )
                
                # タスク作成結果型
                create_task_result_type = GraphQLObjectType(
                    name='CreateTaskResult',
                    fields={
                        'success': GraphQLField(GraphQLBoolean, description='タスク作成成功フラグ'),
                        'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                        'task_id': GraphQLField(GraphQLID, description='作成されたタスクID'),
                        'task': GraphQLField(task_type, description='作成されたタスク情報')
                    }
                )
                
                # タスクキャンセル結果型
                cancel_task_result_type = GraphQLObjectType(
                    name='CancelTaskResult',
                    fields={
                        'success': GraphQLField(GraphQLBoolean, description='タスクキャンセル成功フラグ'),
                        'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                        'task': GraphQLField(task_type, description='キャンセルされたタスク情報')
                    }
                )
                
                # クエリフィールドを追加
                query_fields = dict(extended_schema.get_query_type().fields)
                
                # タスク情報取得クエリ
                query_fields['task'] = GraphQLField(
                    task_type,
                    description='タスク情報を取得',
                    args={
                        'id': GraphQLArgument(GraphQLNonNull(GraphQLID), description='タスクID')
                    },
                    resolve=task_queue_schema.task_queries.resolve_task
                )
                
                # タスク一覧取得クエリ
                query_fields['allTasks'] = GraphQLField(
                    GraphQLList(task_type),
                    description='タスク一覧を取得',
                    args={
                        'status': GraphQLArgument(GraphQLList(task_status_enum), description='フィルタするタスク状態')
                    },
                    resolve=task_queue_schema.task_queries.resolve_all_tasks
                )
                
                # タスクキュー情報取得クエリ
                query_fields['taskQueueInfo'] = GraphQLField(
                    task_queue_info_type,
                    description='タスクキュー情報を取得',
                    resolve=task_queue_schema.task_queries.resolve_task_queue_info
                )
                
                # 新しいクエリ型を作成
                new_query_type = GraphQLObjectType(
                    name='Query',
                    fields=query_fields
                )
                
                # ミューテーションフィールドを追加
                mutation_fields = dict(extended_schema.get_mutation_type().fields)
                
                # タスク作成ミューテーション
                mutation_fields['createTask'] = GraphQLField(
                    create_task_result_type,
                    description='新しいタスクを作成',
                    args={
                        'task_type': GraphQLArgument(GraphQLNonNull(GraphQLString), description='タスクタイプ'),
                        'params_json': GraphQLArgument(GraphQLString, description='タスクパラメータ（JSON文字列）'),
                        'name': GraphQLArgument(GraphQLString, description='タスク名（オプション）'),
                        'priority': GraphQLArgument(GraphQLInt, description='優先度', default_value=0)
                    },
                    resolve=task_queue_schema.task_mutations.create_task.mutate
                )
                
                # タスクキャンセルミューテーション
                mutation_fields['cancelTask'] = GraphQLField(
                    cancel_task_result_type,
                    description='タスクをキャンセル',
                    args={
                        'task_id': GraphQLArgument(GraphQLNonNull(GraphQLID), description='タスクID')
                    },
                    resolve=task_queue_schema.task_mutations.cancel_task.mutate
                )
                
                # タスククリアミューテーション
                mutation_fields['clearTasks'] = GraphQLField(
                    GraphQLObjectType(
                        name='ClearTasksResult',
                        fields={
                            'success': GraphQLField(GraphQLBoolean, description='クリア成功フラグ'),
                            'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                            'cleared_count': GraphQLField(GraphQLInt, description='クリアされたタスク数')
                        }
                    ),
                    description='完了タスクをクリア',
                    args={
                        'max_age_seconds': GraphQLArgument(GraphQLInt, description='この秒数より古いタスクのみクリア', default_value=0)
                    },
                    resolve=task_queue_schema.task_mutations.clear_tasks.mutate
                )
                
                # 新しいミューテーション型を作成
                new_mutation_type = GraphQLObjectType(
                    name='Mutation',
                    fields=mutation_fields
                )
                
                # 新しい拡張スキーマを作成
                extended_schema = GraphQLSchema(
                    query=new_query_type,
                    mutation=new_mutation_type,
                    types=list(extended_schema.get_type_map().values()) + [
                        task_status_enum, task_type, task_queue_info_type,
                        create_task_result_type, cancel_task_result_type
                    ]
                )
                
                logger.info("タスクキュー機能をスキーマに追加しました")
                
            except Exception as e:
                logger.error(f"タスクキュー機能の追加中にエラーが発生しました: {e}")
                logger.debug(traceback.format_exc())
                # タスクキュー機能の追加に失敗した場合、既存の拡張スキーマを使用
        
        # スキーマの説明を強化（LLM向け）
        if LLM_HELPERS_AVAILABLE:
            _enhance_schema_descriptions(extended_schema)
            
        logger.info("GraphQLスキーマに拡張機能を追加しました")
        return extended_schema
        
    except Exception as e:
        logger.error(f"GraphQLスキーマ拡張エラー: {str(e)}")
        logger.debug(traceback.format_exc())
        return schema

# LLM向けリゾルバ関数
def resolve_llm_function_info(root, info, functionName):
    """LLM向けに関数情報を提供するリゾルバ"""
    try:
        from . import llm_schema_helpers
        function_info = llm_schema_helpers.get_function_example(functionName)
        return json.dumps(function_info)
    except Exception as e:
        logger.error(f"関数情報取得エラー: {e}")
        return json.dumps({"error": str(e)})

def resolve_llm_function_list(root, info):
    """LLM向けに関数リストを提供するリゾルバ"""
    try:
        from . import llm_schema_helpers
        function_names = llm_schema_helpers.get_all_function_names()
        return json.dumps({"functions": function_names})
    except Exception as e:
        logger.error(f"関数リスト取得エラー: {e}")
        return json.dumps({"error": str(e)})

def resolve_llm_schema_doc(root, info):
    """LLM向けにスキーマドキュメントを提供するリゾルバ"""
    try:
        from . import llm_schema_helpers
        return llm_schema_helpers.generate_llm_schema_documentation()
    except Exception as e:
        logger.error(f"スキーマドキュメント生成エラー: {e}")
        return f"エラー: {str(e)}"

def _enhance_schema_descriptions(schema):
    """スキーマのdescriptionフィールドをLLM向けに強化"""
    try:
        from . import llm_schema_helpers
        # llm_schema_helpersモジュールのenhance_graphql_schema_descriptions関数を呼び出す
        llm_schema_helpers.enhance_graphql_schema_descriptions(schema)
        logger.info("スキーマの説明をLLM向けに強化しました")
    except Exception as e:
        logger.warning(f"スキーマ説明強化エラー: {e}")
        logger.debug(traceback.format_exc())