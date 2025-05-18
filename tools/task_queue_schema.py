"""
GraphQL タスクキューの統合スキーマ
非同期タスク実行をGraphQLを通して操作するためのスキーマ定義
"""

import graphene
from typing import Dict, Any, List, Optional
import logging

# ロギング設定
logger = logging.getLogger('unified_mcp.tools.task_queue')

# タスクキューをインポート
try:
    from ..core.task_queue import get_task_queue, TaskStatus
    TASK_QUEUE_AVAILABLE = True
except ImportError as e:
    logger.error(f"タスクキューモジュールのインポートに失敗しました: {e}")
    TASK_QUEUE_AVAILABLE = False

# GraphQLオブジェクト型の定義
class TaskStatusEnum(graphene.Enum):
    """タスク状態の列挙型"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(graphene.ObjectType):
    """タスク情報型"""
    id = graphene.ID(description="タスクID")
    name = graphene.String(description="タスク名")
    type = graphene.String(description="タスクタイプ")
    status = graphene.Field(TaskStatusEnum, description="タスク状態")
    priority = graphene.Int(description="優先度")
    created_at = graphene.Float(description="作成時刻（UNIX時間）")
    started_at = graphene.Float(description="開始時刻（UNIX時間）")
    completed_at = graphene.Float(description="完了時刻（UNIX時間）")
    progress = graphene.Float(description="進捗状況（0.0-1.0）")
    message = graphene.String(description="最新メッセージ")
    result = graphene.JSONString(description="タスク結果")
    error = graphene.String(description="エラーメッセージ")
    params = graphene.JSONString(description="タスクパラメータ")

class TaskQueueInfo(graphene.ObjectType):
    """タスクキュー情報型"""
    running = graphene.Boolean(description="実行状態")
    worker_count = graphene.Int(description="ワーカー数")
    pending_tasks = graphene.Int(description="待機中タスク数")
    running_tasks = graphene.Int(description="実行中タスク数")
    completed_tasks = graphene.Int(description="完了タスク数")
    failed_tasks = graphene.Int(description="失敗タスク数")
    tasks = graphene.List(TaskType, description="タスク一覧")

# 入力型の定義
class TaskParamsInput(graphene.InputObjectType):
    """タスクパラメータ入力型"""
    params_json = graphene.String(description="タスクパラメータ（JSON形式）")

# クエリの定義
class TaskQuery(graphene.ObjectType):
    """タスク関連クエリ"""
    task = graphene.Field(
        TaskType,
        id=graphene.ID(required=True, description="タスクID"),
        description="タスク情報を取得"
    )
    
    all_tasks = graphene.List(
        TaskType,
        status=graphene.List(TaskStatusEnum, description="フィルタするタスク状態"),
        description="タスク一覧を取得"
    )
    
    task_queue_info = graphene.Field(
        TaskQueueInfo,
        description="タスクキュー情報を取得"
    )
    
    def resolve_task(self, info, id):
        """タスク情報を取得するリゾルバ"""
        if not TASK_QUEUE_AVAILABLE:
            logger.error("タスクキューが利用できません")
            return None
        
        try:
            # タスクキューからタスク情報を取得
            task_queue = get_task_queue()
            task_data = task_queue.get_task(id)
            
            if not task_data:
                logger.warning(f"タスクが見つかりません: {id}")
                return None
            
            # TaskType形式に変換して返す
            return TaskType(
                id=task_data.get("id"),
                name=task_data.get("name"),
                type=task_data.get("type"),
                status=task_data.get("status"),
                priority=task_data.get("priority"),
                created_at=task_data.get("created_at"),
                started_at=task_data.get("started_at"),
                completed_at=task_data.get("completed_at"),
                progress=task_data.get("progress"),
                message=task_data.get("message"),
                result=task_data.get("result"),
                error=task_data.get("error"),
                params=task_data.get("params")
            )
        except Exception as e:
            logger.error(f"タスク情報取得エラー: {e}")
            return None
    
    def resolve_all_tasks(self, info, status=None):
        """タスク一覧を取得するリゾルバ"""
        if not TASK_QUEUE_AVAILABLE:
            logger.error("タスクキューが利用できません")
            return []
        
        try:
            # タスクキューからタスク一覧を取得
            task_queue = get_task_queue()
            
            # ステータスフィルタ変換
            filter_statuses = None
            if status:
                filter_statuses = []
                for status_value in status:
                    try:
                        filter_statuses.append(TaskStatus(status_value))
                    except ValueError:
                        pass
            
            # タスク一覧を取得
            tasks_data = task_queue.get_all_tasks(filter_status=filter_statuses)
            
            # TaskType形式に変換して返す
            return [
                TaskType(
                    id=task.get("id"),
                    name=task.get("name"),
                    type=task.get("type"),
                    status=task.get("status"),
                    priority=task.get("priority"),
                    created_at=task.get("created_at"),
                    started_at=task.get("started_at"),
                    completed_at=task.get("completed_at"),
                    progress=task.get("progress"),
                    message=task.get("message"),
                    result=task.get("result"),
                    error=task.get("error"),
                    params=task.get("params")
                ) for task in tasks_data
            ]
        except Exception as e:
            logger.error(f"タスク一覧取得エラー: {e}")
            return []
    
    def resolve_task_queue_info(self, info):
        """タスクキュー情報を取得するリゾルバ"""
        if not TASK_QUEUE_AVAILABLE:
            logger.error("タスクキューが利用できません")
            return None
        
        try:
            # タスクキューからタスク一覧を取得
            task_queue = get_task_queue()
            tasks_data = task_queue.get_all_tasks()
            
            # 状態ごとのタスク数をカウント
            pending_count = 0
            running_count = 0
            completed_count = 0
            failed_count = 0
            
            for task in tasks_data:
                status = task.get("status")
                if status == TaskStatus.PENDING.value:
                    pending_count += 1
                elif status == TaskStatus.RUNNING.value:
                    running_count += 1
                elif status == TaskStatus.COMPLETED.value:
                    completed_count += 1
                elif status == TaskStatus.FAILED.value:
                    failed_count += 1
            
            # TaskQueueInfo形式に変換して返す
            return TaskQueueInfo(
                running=task_queue.running,
                worker_count=task_queue.num_workers,
                pending_tasks=pending_count,
                running_tasks=running_count,
                completed_tasks=completed_count,
                failed_tasks=failed_count,
                tasks=[
                    TaskType(
                        id=task.get("id"),
                        name=task.get("name"),
                        type=task.get("type"),
                        status=task.get("status"),
                        priority=task.get("priority"),
                        created_at=task.get("created_at"),
                        started_at=task.get("started_at"),
                        completed_at=task.get("completed_at"),
                        progress=task.get("progress"),
                        message=task.get("message"),
                        result=task.get("result"),
                        error=task.get("error"),
                        params=task.get("params")
                    ) for task in tasks_data
                ]
            )
        except Exception as e:
            logger.error(f"タスクキュー情報取得エラー: {e}")
            return None

# ミューテーションの定義
class CreateTaskMutation(graphene.Mutation):
    """タスク作成ミューテーション"""
    class Arguments:
        task_type = graphene.String(required=True, description="タスクタイプ")
        params_json = graphene.String(description="タスクパラメータ（JSON形式）")
        name = graphene.String(description="タスク名")
        priority = graphene.Int(description="優先度")
    
    # 返り値の定義
    success = graphene.Boolean()
    message = graphene.String()
    task_id = graphene.ID()
    task = graphene.Field(lambda: TaskType)
    
    def mutate(self, info, task_type, params_json=None, name=None, priority=0):
        """タスクを作成するミューテーション実装"""
        if not TASK_QUEUE_AVAILABLE:
            return CreateTaskMutation(
                success=False,
                message="タスクキューが利用できません",
                task_id=None,
                task=None
            )
        
        try:
            import json
            
            # パラメータの解析
            params = {}
            if params_json:
                try:
                    params = json.loads(params_json)
                except json.JSONDecodeError as e:
                    return CreateTaskMutation(
                        success=False,
                        message=f"パラメータのJSONパースエラー: {str(e)}",
                        task_id=None,
                        task=None
                    )
            
            # タスクキューにタスクを追加
            task_queue = get_task_queue()
            task_id = task_queue.create_and_add_task(
                task_type=task_type,
                params=params,
                priority=priority,
                name=name
            )
            
            # 作成したタスク情報を取得
            task_data = task_queue.get_task(task_id)
            
            if not task_data:
                return CreateTaskMutation(
                    success=False,
                    message="タスク作成後の情報取得に失敗しました",
                    task_id=task_id,
                    task=None
                )
            
            # TaskType形式に変換
            task = TaskType(
                id=task_data.get("id"),
                name=task_data.get("name"),
                type=task_data.get("type"),
                status=task_data.get("status"),
                priority=task_data.get("priority"),
                created_at=task_data.get("created_at"),
                started_at=task_data.get("started_at"),
                completed_at=task_data.get("completed_at"),
                progress=task_data.get("progress"),
                message=task_data.get("message"),
                result=task_data.get("result"),
                error=task_data.get("error"),
                params=task_data.get("params")
            )
            
            return CreateTaskMutation(
                success=True,
                message=f"タスクを作成しました: {task_id}",
                task_id=task_id,
                task=task
            )
        except Exception as e:
            logger.error(f"タスク作成エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return CreateTaskMutation(
                success=False,
                message=f"タスク作成エラー: {str(e)}",
                task_id=None,
                task=None
            )

class CancelTaskMutation(graphene.Mutation):
    """タスクキャンセルミューテーション"""
    class Arguments:
        task_id = graphene.ID(required=True, description="タスクID")
    
    # 返り値の定義
    success = graphene.Boolean()
    message = graphene.String()
    task = graphene.Field(lambda: TaskType)
    
    def mutate(self, info, task_id):
        """タスクをキャンセルするミューテーション実装"""
        if not TASK_QUEUE_AVAILABLE:
            return CancelTaskMutation(
                success=False,
                message="タスクキューが利用できません",
                task=None
            )
        
        try:
            # タスクキューからタスクをキャンセル
            task_queue = get_task_queue()
            success = task_queue.cancel_task(task_id)
            
            if not success:
                return CancelTaskMutation(
                    success=False,
                    message="タスクのキャンセルに失敗しました（既に実行中または完了している可能性があります）",
                    task=None
                )
            
            # キャンセルしたタスク情報を取得
            task_data = task_queue.get_task(task_id)
            
            if not task_data:
                return CancelTaskMutation(
                    success=True,
                    message="タスクをキャンセルしましたが、情報取得に失敗しました",
                    task=None
                )
            
            # TaskType形式に変換
            task = TaskType(
                id=task_data.get("id"),
                name=task_data.get("name"),
                type=task_data.get("type"),
                status=task_data.get("status"),
                priority=task_data.get("priority"),
                created_at=task_data.get("created_at"),
                started_at=task_data.get("started_at"),
                completed_at=task_data.get("completed_at"),
                progress=task_data.get("progress"),
                message=task_data.get("message"),
                result=task_data.get("result"),
                error=task_data.get("error"),
                params=task_data.get("params")
            )
            
            return CancelTaskMutation(
                success=True,
                message=f"タスクをキャンセルしました: {task_id}",
                task=task
            )
        except Exception as e:
            logger.error(f"タスクキャンセルエラー: {e}")
            
            return CancelTaskMutation(
                success=False,
                message=f"タスクキャンセルエラー: {str(e)}",
                task=None
            )

class ClearTasksMutation(graphene.Mutation):
    """完了タスククリアミューテーション"""
    class Arguments:
        max_age_seconds = graphene.Int(description="この秒数より古いタスクのみクリア（デフォルト: 0 = すべて）")
    
    # 返り値の定義
    success = graphene.Boolean()
    message = graphene.String()
    cleared_count = graphene.Int()
    
    def mutate(self, info, max_age_seconds=0):
        """完了タスクをクリアするミューテーション実装"""
        if not TASK_QUEUE_AVAILABLE:
            return ClearTasksMutation(
                success=False,
                message="タスクキューが利用できません",
                cleared_count=0
            )
        
        try:
            # タスクキューから完了タスクをクリア
            task_queue = get_task_queue()
            cleared_count = task_queue.clear_completed_tasks(max_age_seconds)
            
            return ClearTasksMutation(
                success=True,
                message=f"{cleared_count}個のタスクをクリアしました",
                cleared_count=cleared_count
            )
        except Exception as e:
            logger.error(f"タスククリアエラー: {e}")
            
            return ClearTasksMutation(
                success=False,
                message=f"タスククリアエラー: {str(e)}",
                cleared_count=0
            )

class TaskMutation(graphene.ObjectType):
    """タスク関連ミューテーション"""
    create_task = CreateTaskMutation.Field(description="タスクを作成")
    cancel_task = CancelTaskMutation.Field(description="タスクをキャンセル")
    clear_tasks = ClearTasksMutation.Field(description="完了タスクをクリア")

# スキーマをエクスポート
task_queries = TaskQuery
task_mutations = TaskMutation