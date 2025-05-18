"""
REST API モデル定義
APIリクエストとレスポンスのデータモデルを定義
"""

from typing import Dict, List, Any, Optional, Union, TypeVar, Generic
from enum import Enum
import time

# 型変数
T = TypeVar('T')

# Pydanticのインポートを試みる
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


class APIResponse(Generic[T]):
    """標準REST API応答モデル"""
    
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
            "version": "1.0.0",
            "server_type": "unified_server"
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


class CommandRequest:
    """コマンド実行リクエストモデル"""
    
    def __init__(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """
        コマンドリクエストを初期化
        
        Args:
            command: 実行するコマンドの名前
            params: コマンドパラメータ
            session_id: セッションID（任意）
            timeout: 実行タイムアウト（秒）
        """
        self.command = command
        self.params = params or {}
        self.session_id = session_id
        self.timeout = timeout
    
    def to_dict(self) -> Dict[str, Any]:
        """リクエストを辞書形式に変換"""
        request_dict = {
            "command": self.command,
            "params": self.params
        }
        
        if self.session_id:
            request_dict["session_id"] = self.session_id
            
        if self.timeout:
            request_dict["timeout"] = self.timeout
            
        return request_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandRequest':
        """辞書からリクエストを生成"""
        return cls(
            command=data.get("command", ""),
            params=data.get("params", {}),
            session_id=data.get("session_id"),
            timeout=data.get("timeout")
        )


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


class BatchRequest:
    """バッチコマンド実行リクエストモデル"""
    
    def __init__(
        self,
        commands: List[Dict[str, Any]],
        stop_on_error: bool = False,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """
        バッチリクエストを初期化
        
        Args:
            commands: コマンドリクエストのリスト
            stop_on_error: エラー発生時に停止するかどうか
            session_id: セッションID（任意）
            timeout: 実行タイムアウト（秒）
        """
        self.commands = commands
        self.stop_on_error = stop_on_error
        self.session_id = session_id
        self.timeout = timeout
    
    def to_dict(self) -> Dict[str, Any]:
        """リクエストを辞書形式に変換"""
        request_dict = {
            "commands": self.commands,
            "stop_on_error": self.stop_on_error
        }
        
        if self.session_id:
            request_dict["session_id"] = self.session_id
            
        if self.timeout:
            request_dict["timeout"] = self.timeout
            
        return request_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchRequest':
        """辞書からリクエストを生成"""
        return cls(
            commands=data.get("commands", []),
            stop_on_error=data.get("stop_on_error", False),
            session_id=data.get("session_id"),
            timeout=data.get("timeout")
        )


class ErrorDetail:
    """エラー詳細モデル"""
    
    def __init__(
        self,
        code: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        stack_trace: Optional[str] = None
    ):
        """
        エラー詳細を初期化
        
        Args:
            code: エラーコード
            message: エラーメッセージ
            context: エラーコンテキスト情報
            suggestion: 修正のためのサジェスト
            stack_trace: スタックトレース（デバッグモードのみ）
        """
        self.code = code
        self.message = message
        self.context = context or {}
        self.suggestion = suggestion
        self.stack_trace = stack_trace
    
    def to_dict(self) -> Dict[str, Any]:
        """エラーを辞書形式に変換"""
        error_dict = {
            "code": self.code,
            "message": self.message
        }
        
        if self.context:
            error_dict["context"] = self.context
            
        if self.suggestion:
            error_dict["suggestion"] = self.suggestion
            
        if self.stack_trace:
            error_dict["stack_trace"] = self.stack_trace
            
        return error_dict


# Pydanticが利用可能な場合のみ定義するモデル
if PYDANTIC_AVAILABLE:
    class CommandRequestModel(BaseModel):
        """Pydanticベースのコマンドリクエストモデル"""
        command: str = Field(..., description="実行するコマンドの名前")
        params: Dict[str, Any] = Field(default_factory=dict, description="コマンドパラメータ")
        session_id: Optional[str] = Field(None, description="セッションID（任意）")
        timeout: Optional[float] = Field(None, description="実行タイムアウト（秒）")
    
    class BatchRequestModel(BaseModel):
        """Pydanticベースのバッチリクエストモデル"""
        commands: List[Dict[str, Any]] = Field(..., description="コマンドリクエストのリスト")
        stop_on_error: bool = Field(False, description="エラー発生時に停止するかどうか")
        session_id: Optional[str] = Field(None, description="セッションID（任意）")
        timeout: Optional[float] = Field(None, description="実行タイムアウト（秒）")