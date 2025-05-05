"""
Unified MCP 認証モジュール
API認証と認可の機能を提供
"""

import logging
import time
import uuid
import hashlib
import secrets
from typing import Dict, List, Any, Optional, Callable, Union
import json

import bpy
from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader, APIKeyCookie

from .errors import AuthRequiredError, MCPError, ErrorCodes

# ロガー設定
logger = logging.getLogger("unified_mcp.auth")

# APIキーヘッダー名
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# APIキーストレージ（アドオン設定に保存）
class APIKeyManager:
    """APIキー管理クラス"""
    
    @staticmethod
    def _get_addon_prefs():
        """アドオン設定を取得"""
        return bpy.context.preferences.addons["blender_json_mcp"].preferences
    
    @classmethod
    def get_master_key(cls) -> str:
        """マスターAPIキーを取得"""
        try:
            prefs = cls._get_addon_prefs()
            if hasattr(prefs, "api_master_key") and prefs.api_master_key:
                return prefs.api_master_key
        except Exception as e:
            logger.error(f"マスターキー取得エラー: {e}")
        
        # デフォルトのマスターキー生成（初回用）
        return cls.generate_api_key()
    
    @classmethod
    def set_master_key(cls, key: str) -> bool:
        """マスターAPIキーを設定"""
        try:
            prefs = cls._get_addon_prefs()
            if hasattr(prefs, "api_master_key"):
                prefs.api_master_key = key
                return True
        except Exception as e:
            logger.error(f"マスターキー設定エラー: {e}")
        return False
    
    @classmethod
    def is_auth_enabled(cls) -> bool:
        """認証が有効かどうかを確認"""
        try:
            prefs = cls._get_addon_prefs()
            if hasattr(prefs, "enable_api_auth"):
                return bool(prefs.enable_api_auth)
        except Exception as e:
            logger.error(f"認証設定取得エラー: {e}")
        return False
    
    @classmethod
    def generate_api_key(cls) -> str:
        """新しいAPIキーを生成"""
        return secrets.token_urlsafe(32)
    
    @classmethod
    def verify_api_key(cls, api_key: str) -> bool:
        """APIキーを検証"""
        if not api_key:
            return False
        
        # マスターキーとの照合
        master_key = cls.get_master_key()
        return api_key == master_key


# 認証依存関数
async def verify_api_key(
    api_key: str = Security(api_key_header),
) -> str:
    """
    APIキーを検証する依存関数
    
    Args:
        api_key: リクエストから取得したAPIキー
        
    Returns:
        検証済みのAPIキー
        
    Raises:
        AuthRequiredError: 認証が必要でAPIキーが無効な場合
    """
    # 認証が無効化されている場合はスキップ
    if not APIKeyManager.is_auth_enabled():
        return ""
    
    # APIキーが提供されていない場合
    if not api_key:
        raise AuthRequiredError(
            message="このAPIエンドポイントにアクセスするには認証が必要です",
            suggestion="X-API-KeyヘッダーにAPIキーを指定してください"
        )
    
    # APIキーの検証
    if not APIKeyManager.verify_api_key(api_key):
        logger.warning(f"無効なAPIキー: {api_key[:5]}...")
        raise AuthRequiredError(
            message="無効なAPIキーです",
            suggestion="有効なAPIキーを取得して再試行してください"
        )
    
    return api_key


# ミドルウェア
async def auth_middleware(request: Request, call_next):
    """
    認証ミドルウェア
    プライベートエンドポイントへのアクセスをチェック
    
    Args:
        request: HTTPリクエスト
        call_next: 次のミドルウェア関数
        
    Returns:
        レスポンス
    """
    # 認証が必要なパスかどうかをチェック
    path = request.url.path
    
    # 認証が不要なパス
    public_paths = [
        "/docs", 
        "/redoc", 
        "/openapi.json",
        "/api/v1/status",
        "/api/v1/health",
    ]
    
    # ドキュメント関連は常に許可
    if any(path.startswith(p) for p in public_paths):
        return await call_next(request)
    
    # 認証が無効化されている場合はスキップ
    if not APIKeyManager.is_auth_enabled():
        return await call_next(request)
    
    # APIキーを取得
    api_key = request.headers.get(API_KEY_NAME)
    
    # APIキーが提供されていない場合
    if not api_key:
        return HTTPException(
            status_code=401,
            detail="このAPIエンドポイントにアクセスするには認証が必要です",
            headers={"WWW-Authenticate": "APIKey"}
        )
    
    # APIキーの検証
    if not APIKeyManager.verify_api_key(api_key):
        logger.warning(f"無効なAPIキー: {api_key[:5]}...")
        return HTTPException(
            status_code=403,
            detail="無効なAPIキーです",
            headers={"WWW-Authenticate": "APIKey"}
        )
    
    # 認証成功、リクエスト処理を続行
    return await call_next(request)


# アドオン設定に追加するプロパティ（参照用）
"""
# __init__.pyのAddonPreferencesクラスに追加するプロパティ:

import bpy
from bpy.props import BoolProperty, StringProperty

# クラスのプロパティとして
enable_api_auth: BoolProperty(
    name="API認証を有効化",
    description="APIアクセスにキーを要求するかどうか",
    default=False
)

api_master_key: StringProperty(
    name="APIマスターキー",
    description="API呼び出しの認証に使用するキー",
    default="",
    subtype='PASSWORD'
)
"""