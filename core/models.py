"""
Unified MCP データモデル
API応答とデータモデルの定義
"""

from typing import Dict, List, Any, Optional, Union, TypeVar, Generic
from enum import Enum
import json
import time

# Pydanticをインポート
try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Pydanticが利用できない場合に互換用クラスを定義
    class BaseModel:
        """Pydantic BaseModelの互換用クラス"""
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    def Field(*args, **kwargs):
        return None
    
    PYDANTIC_AVAILABLE = False

# 型変数
T = TypeVar('T')


class APIResponse(Generic[T]):
    """標準API応答モデル"""
    
    def __init__(
        self,
        success: bool = True,
        data: Optional[T] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        partial_success: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        APIレスポンスを初期化
        
        Args:
            success: リクエストが成功したかどうか
            data: レスポンスデータ
            errors: エラー情報のリスト
            partial_success: 部分的に成功した操作の情報
            metadata: レスポンスに関するメタデータ
        """
        self.success = success
        self.data = data
        self.errors = errors or []
        self.partial_success = partial_success
        self.metadata = metadata or {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """応答を辞書形式に変換"""
        response = {
            "success": self.success,
            "metadata": self.metadata
        }
        
        if self.data is not None:
            response["data"] = self.data
            
        if self.errors:
            response["errors"] = self.errors
            
        if self.partial_success is not None:
            response["partial_success"] = self.partial_success
            
        return response
    
    @classmethod
    def success_response(
        cls, 
        data: Optional[T] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'APIResponse[T]':
        """成功応答を作成するファクトリメソッド"""
        return cls(success=True, data=data, metadata=metadata)
    
    @classmethod
    def error_response(
        cls,
        errors: List[Dict[str, Any]],
        data: Optional[T] = None,
        partial_success: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'APIResponse[T]':
        """エラー応答を作成するファクトリメソッド"""
        return cls(
            success=False,
            data=data,
            errors=errors,
            partial_success=partial_success,
            metadata=metadata
        )


class CommandStatus(str, Enum):
    """コマンド実行ステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommandResult:
    """コマンド実行結果モデル"""
    
    def __init__(
        self,
        command_id: str,
        command_name: str,
        status: CommandStatus,
        result: Optional[Any] = None,
        error: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None
    ):
        """
        コマンド結果を初期化
        
        Args:
            command_id: コマンド実行の一意識別子
            command_name: 実行されたコマンドの名前
            status: 現在の実行ステータス
            result: 成功した場合の結果データ
            error: 失敗した場合のエラー情報
            execution_time: 実行時間（秒）
            created_at: 作成タイムスタンプ
            updated_at: 最終更新タイムスタンプ
        """
        self.command_id = command_id
        self.command_name = command_name
        self.status = status
        self.result = result
        self.error = error
        self.execution_time = execution_time
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """結果を辞書形式に変換"""
        result_dict = {
            "command_id": self.command_id,
            "command_name": self.command_name,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
        if self.execution_time is not None:
            result_dict["execution_time"] = self.execution_time
            
        if self.result is not None:
            result_dict["result"] = self.result
            
        if self.error is not None:
            result_dict["error"] = self.error
            
        return result_dict
    
    def update_status(self, status: CommandStatus) -> None:
        """ステータスを更新"""
        self.status = status
        self.updated_at = time.time()
    
    def complete(self, result: Any, execution_time: Optional[float] = None) -> None:
        """コマンドを成功完了としてマーク"""
        self.status = CommandStatus.COMPLETED
        self.result = result
        self.execution_time = execution_time
        self.updated_at = time.time()
    
    def fail(self, error: Dict[str, Any], execution_time: Optional[float] = None) -> None:
        """コマンドを失敗としてマーク"""
        self.status = CommandStatus.FAILED
        self.error = error
        self.execution_time = execution_time
        self.updated_at = time.time()
    
    def cancel(self) -> None:
        """コマンドをキャンセルとしてマーク"""
        self.status = CommandStatus.CANCELLED
        self.updated_at = time.time()


class CommandSchema:
    """コマンドスキーマモデル"""
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        returns: Dict[str, Any],
        examples: Optional[List[Dict[str, Any]]] = None,
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_dangerous: bool = False
    ):
        """
        コマンドスキーマを初期化
        
        Args:
            name: コマンド名
            description: コマンドの説明
            parameters: パラメータスキーマ（JSONスキーマ形式）
            returns: 戻り値スキーマ（JSONスキーマ形式）
            examples: 使用例のリスト
            group: コマンドのグループ/カテゴリ
            tags: 関連タグのリスト
            is_dangerous: 危険な操作かどうか（確認が必要）
        """
        self.name = name
        self.description = description
        self.parameters = parameters
        self.returns = returns
        self.examples = examples or []
        self.group = group
        self.tags = tags or []
        self.is_dangerous = is_dangerous
    
    def to_dict(self) -> Dict[str, Any]:
        """スキーマを辞書形式に変換"""
        schema_dict = {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "returns": self.returns,
            "is_dangerous": self.is_dangerous
        }
        
        if self.examples:
            schema_dict["examples"] = self.examples
            
        if self.group:
            schema_dict["group"] = self.group
            
        if self.tags:
            schema_dict["tags"] = self.tags
            
        return schema_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandSchema':
        """辞書からスキーマを生成"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            returns=data.get("returns", {}),
            examples=data.get("examples", []),
            group=data.get("group"),
            tags=data.get("tags", []),
            is_dangerous=data.get("is_dangerous", False)
        )


class SessionState:
    """セッション状態モデル"""
    
    def __init__(
        self,
        session_id: str,
        created_at: Optional[float] = None,
        last_access: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        command_history: Optional[List[Dict[str, Any]]] = None
    ):
        """
        セッション状態を初期化
        
        Args:
            session_id: セッションの一意識別子
            created_at: 作成タイムスタンプ
            last_access: 最終アクセスタイムスタンプ
            context: セッションコンテキストデータ
            command_history: コマンド実行履歴
        """
        self.session_id = session_id
        self.created_at = created_at or time.time()
        self.last_access = last_access or time.time()
        self.context = context or {}
        self.command_history = command_history or []
    
    def to_dict(self) -> Dict[str, Any]:
        """セッションを辞書形式に変換"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_access": self.last_access,
            "context": self.context,
            "command_history": self.command_history
        }
    
    def update_last_access(self) -> None:
        """最終アクセス時間を更新"""
        self.last_access = time.time()
    
    def add_command_history(self, command: Dict[str, Any], result: Dict[str, Any]) -> None:
        """コマンド履歴に追加"""
        self.command_history.append({
            "timestamp": time.time(),
            "command": command,
            "result": result
        })
        self.update_last_access()
    
    def set_context_value(self, key: str, value: Any) -> None:
        """コンテキスト値を設定"""
        self.context[key] = value
        self.update_last_access()
    
    def get_context_value(self, key: str, default: Any = None) -> Any:
        """コンテキスト値を取得"""
        return self.context.get(key, default)