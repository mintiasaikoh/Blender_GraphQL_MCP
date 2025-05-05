"""
Unified MCP エラー処理モジュール
構造化されたエラー定義と処理を提供
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Type
import traceback

# ロガー設定
logger = logging.getLogger("unified_mcp.errors")

# エラーコード定義
class ErrorCodes:
    """エラーコード定数"""
    # 一般エラー (1000-1999)
    GENERAL_ERROR = "E1000"
    INVALID_REQUEST = "E1001"
    MISSING_PARAMETER = "E1002"
    INVALID_PARAMETER = "E1003"
    NOT_IMPLEMENTED = "E1004"
    TIMEOUT = "E1005"
    
    # 認証/認可エラー (2000-2999)
    AUTH_REQUIRED = "E2000"
    INVALID_CREDENTIALS = "E2001"
    ACCESS_DENIED = "E2002"
    SESSION_EXPIRED = "E2003"
    
    # Blenderオブジェクトエラー (3000-3999)
    OBJECT_NOT_FOUND = "E3000"
    MATERIAL_NOT_FOUND = "E3001"
    SCENE_NOT_FOUND = "E3002"
    INVALID_OBJECT_TYPE = "E3003"
    OBJECT_LOCKED = "E3004"
    
    # コマンドエラー (4000-4999)
    COMMAND_NOT_FOUND = "E4000"
    COMMAND_EXECUTION_FAILED = "E4001"
    COMMAND_VALIDATION_FAILED = "E4002"
    
    # サーバーエラー (5000-5999)
    SERVER_ERROR = "E5000"
    SERVER_UNAVAILABLE = "E5001"
    DATABASE_ERROR = "E5002"


class MCPError(Exception):
    """Unified MCP基本エラークラス"""
    
    def __init__(
        self, 
        message: str, 
        code: str = ErrorCodes.GENERAL_ERROR,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ):
        """
        エラーを初期化
        
        Args:
            message: エラーメッセージ
            code: エラーコード (ErrorCodes参照)
            context: エラーコンテキスト情報
            suggestion: ユーザーへの提案
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context or {}
        self.suggestion = suggestion
        
        # エラーをログに記録
        logger.error(f"エラー発生 [{code}]: {message}")
        if context:
            logger.debug(f"エラーコンテキスト: {context}")
    
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
            
        return error_dict


# 特定エラークラス - オブジェクト関連
class ObjectNotFoundError(MCPError):
    """オブジェクトが見つからない場合のエラー"""
    
    def __init__(
        self, 
        object_name: str,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ):
        """
        オブジェクト未検出エラーを初期化
        
        Args:
            object_name: 見つからなかったオブジェクトの名前
            message: カスタムエラーメッセージ (省略可)
            context: 追加のコンテキスト情報
            suggestion: ユーザーへの提案
        """
        self.object_name = object_name
        
        if message is None:
            message = f"オブジェクト '{object_name}' が見つかりません"
            
        # コンテキスト情報をマージ
        error_context = {"requested_object": object_name}
        if context:
            error_context.update(context)
            
        # デフォルトの提案
        if suggestion is None:
            suggestion = "scene.objects で利用可能なオブジェクトを確認してください"
            
        super().__init__(
            message=message,
            code=ErrorCodes.OBJECT_NOT_FOUND,
            context=error_context,
            suggestion=suggestion
        )


class MaterialNotFoundError(MCPError):
    """マテリアルが見つからない場合のエラー"""
    
    def __init__(
        self, 
        material_name: str,
        object_name: Optional[str] = None,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ):
        """
        マテリアル未検出エラーを初期化
        
        Args:
            material_name: 見つからなかったマテリアルの名前
            object_name: 関連するオブジェクト名 (省略可)
            message: カスタムエラーメッセージ (省略可)
            context: 追加のコンテキスト情報
            suggestion: ユーザーへの提案
        """
        self.material_name = material_name
        self.object_name = object_name
        
        if message is None:
            if object_name:
                message = f"マテリアル '{material_name}' がオブジェクト '{object_name}' に見つかりません"
            else:
                message = f"マテリアル '{material_name}' が見つかりません"
            
        # コンテキスト情報をマージ
        error_context = {"requested_material": material_name}
        if object_name:
            error_context["object_name"] = object_name
        if context:
            error_context.update(context)
            
        # デフォルトの提案
        if suggestion is None:
            suggestion = "bpy.data.materials で利用可能なマテリアルを確認してください"
            
        super().__init__(
            message=message,
            code=ErrorCodes.MATERIAL_NOT_FOUND,
            context=error_context,
            suggestion=suggestion
        )


# 特定エラークラス - コマンド関連
class CommandNotFoundError(MCPError):
    """コマンドが見つからない場合のエラー"""
    
    def __init__(
        self, 
        command_name: str,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ):
        """
        コマンド未検出エラーを初期化
        
        Args:
            command_name: 見つからなかったコマンドの名前
            message: カスタムエラーメッセージ (省略可)
            context: 追加のコンテキスト情報
            suggestion: ユーザーへの提案
        """
        self.command_name = command_name
        
        if message is None:
            message = f"コマンド '{command_name}' が見つかりません"
            
        # コンテキスト情報をマージ
        error_context = {"requested_command": command_name}
        if context:
            error_context.update(context)
            
        # デフォルトの提案
        if suggestion is None:
            suggestion = "/api/commands エンドポイントで利用可能なコマンドを確認してください"
            
        super().__init__(
            message=message,
            code=ErrorCodes.COMMAND_NOT_FOUND,
            context=error_context,
            suggestion=suggestion
        )


class CommandValidationError(MCPError):
    """コマンドパラメータのバリデーションエラー"""
    
    def __init__(
        self, 
        command_name: str,
        validation_errors: List[str],
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ):
        """
        コマンドバリデーションエラーを初期化
        
        Args:
            command_name: コマンド名
            validation_errors: バリデーションエラーメッセージのリスト
            message: カスタムエラーメッセージ (省略可)
            context: 追加のコンテキスト情報
            suggestion: ユーザーへの提案
        """
        self.command_name = command_name
        self.validation_errors = validation_errors
        
        if message is None:
            message = f"コマンド '{command_name}' のパラメータが無効です"
            
        # コンテキスト情報をマージ
        error_context = {
            "command": command_name,
            "validation_errors": validation_errors
        }
        if context:
            error_context.update(context)
            
        # デフォルトの提案
        if suggestion is None:
            suggestion = "コマンドスキーマを確認して、必要なパラメータを正しく指定してください"
            
        super().__init__(
            message=message,
            code=ErrorCodes.COMMAND_VALIDATION_FAILED,
            context=error_context,
            suggestion=suggestion
        )


# 特定エラークラス - 認証関連
class AuthRequiredError(MCPError):
    """認証が必要なリソースへのアクセス時のエラー"""
    
    def __init__(
        self,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ):
        """
        認証要求エラーを初期化
        
        Args:
            message: カスタムエラーメッセージ (省略可)
            context: 追加のコンテキスト情報
            suggestion: ユーザーへの提案
        """
        if message is None:
            message = "このリソースにアクセスするには認証が必要です"
            
        # デフォルトの提案
        if suggestion is None:
            suggestion = "APIキーを取得して、X-API-Key ヘッダーに設定してください"
            
        super().__init__(
            message=message,
            code=ErrorCodes.AUTH_REQUIRED,
            context=context,
            suggestion=suggestion
        )


# エラー応答生成ヘルパー
def create_error_response(
    error: Union[MCPError, Exception],
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    エラーオブジェクトからAPIレスポンス辞書を生成
    
    Args:
        error: エラーオブジェクト
        include_traceback: トレースバックを含めるかどうか
        
    Returns:
        エラーレスポンス辞書
    """
    if isinstance(error, MCPError):
        # カスタムMCPエラー
        error_detail = error.to_dict()
    else:
        # 標準例外
        error_detail = {
            "code": ErrorCodes.GENERAL_ERROR,
            "message": str(error)
        }
    
    # トレースバックを含める（デバッグ用）
    if include_traceback:
        error_detail["traceback"] = traceback.format_exc()
    
    return {
        "success": False,
        "errors": [error_detail]
    }


# エラーハンドリングデコレータ
def handle_errors(include_traceback: bool = False):
    """
    関数のエラーを捕捉して構造化レスポンスを生成するデコレータ
    
    Args:
        include_traceback: トレースバックを含めるかどうか
        
    Returns:
        デコレータ関数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return create_error_response(e, include_traceback)
        return wrapper
    return decorator