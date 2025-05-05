"""
Unified MCP Error Handling
標準化されたエラー処理とロギング機能を提供
"""

import traceback
import functools
import logging
import sys
import os
from typing import Any, Callable, Dict, Optional, TypeVar, cast

# 型ヒント用の定義
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# ロギング設定
log_file = os.path.expanduser('~/.blender_json_mcp.log')
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# モジュールレベルのロガー
logger = logging.getLogger('unified_mcp.error_handler')

# デバッグモード設定（環境変数から取得）
DEBUG_MODE = os.environ.get('UNIFIED_MCP_DEBUG', '0').lower() in ('1', 'true', 'yes')

def configure_logging(debug_mode: bool = False):
    """ロギングレベルを設定"""
    global DEBUG_MODE
    DEBUG_MODE = debug_mode
    
    if debug_mode:
        logging.getLogger('unified_mcp').setLevel(logging.DEBUG)
        logger.debug("デバッグモードが有効になりました")
    else:
        logging.getLogger('unified_mcp').setLevel(logging.INFO)

# エラー応答の標準形式
def format_error_response(error: Exception, operation: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """エラー応答を標準形式でフォーマット"""
    response = {
        'status': 'error',
        'message': f"{operation}エラー: {str(error)}",
        'error_type': error.__class__.__name__
    }
    
    if details:
        response['details'] = details
    
    # デバッグモードの場合はスタックトレースも含める
    if DEBUG_MODE:
        response['traceback'] = traceback.format_exc()
    
    return response

# 成功応答の標準形式
def format_success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """成功応答を標準形式でフォーマット"""
    response = {
        'status': 'success',
        'data': data
    }
    
    if message:
        response['message'] = message
    
    return response

# デコレータ: 例外処理
def handle_exceptions(operation: str, fallback_value: Any = None):
    """関数の例外を捕捉して標準形式のレスポンスを返すデコレータ"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{operation}中にエラーが発生: {str(e)}")
                if DEBUG_MODE:
                    logger.debug(traceback.format_exc())
                
                # エラー応答を返すか、フォールバック値を返す
                if fallback_value is None:
                    return format_error_response(e, operation)
                return fallback_value
        return cast(F, wrapper)
    return decorator

# ロギングとエラー処理を統合したデコレータ
def log_and_handle_exceptions(operation: str, level: str = 'info', fallback_value: Any = None):
    """関数の実行を記録し、例外を捕捉するデコレータ"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # ロギング（引数を省略）
            log_args = kwargs.copy()
            # パスワードなど機密情報を含む可能性のある引数をマスク
            for sensitive in ['password', 'token', 'secret', 'auth']:
                if sensitive in log_args:
                    log_args[sensitive] = '***'
            
            # ログメッセージ
            log_msg = f"{operation}開始 - 引数: {log_args}"
            
            # ロギングレベルに応じたログ出力
            log_func = getattr(logger, level.lower())
            log_func(log_msg)
            
            try:
                # 関数実行
                result = func(*args, **kwargs)
                
                # 成功ログ（結果は大きい可能性があるので省略）
                logger.debug(f"{operation}成功")
                return result
            
            except Exception as e:
                # エラー記録
                logger.error(f"{operation}失敗: {str(e)}")
                if DEBUG_MODE:
                    logger.debug(traceback.format_exc())
                
                # エラー応答を返すか、フォールバック値を返す
                if fallback_value is None:
                    return format_error_response(e, operation)
                return fallback_value
        
        return cast(F, wrapper)
    return decorator

def register():
    """エラーハンドリングモジュールを登録"""
    logger.info("エラーハンドリングモジュールを登録しました")

def unregister():
    """エラーハンドリングモジュールの登録解除"""
    logger.info("エラーハンドリングモジュールを登録解除しました")
