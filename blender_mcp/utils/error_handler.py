"""
Unified MCP Error Handling
標準化されたエラー処理とロギング機能を提供
エラーログの保存・管理機能を含む
"""

import traceback
import functools
import logging
import sys
import os
import json
from datetime import datetime
import importlib
from typing import Any, Callable, Dict, Optional, TypeVar, cast, List, Tuple, Union

# 型ヒント用の定義
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# ロギング設定
# ユーザーホームディレクトリにログディレクトリを作成
home_dir = os.path.expanduser("~")
logs_dir = os.path.join(home_dir, "blender_graphql_mcp_logs")
error_logs_dir = os.path.join(logs_dir, "errors")

# ディレクトリ作成
for dir_path in [logs_dir, error_logs_dir]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

# 現在の日時をログファイル名に使用
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(logs_dir, f"error_handler_{current_time}.log")

# モジュールレベルのロガー
logger = logging.getLogger('blender_graphql_mcp.utils.error_handler')

# ファイルハンドラ追加（まだ設定されていない場合）
if not logger.handlers:
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

# エラー種別情報
ERROR_TYPES = {
    "ImportError": {
        "title": "依存ライブラリ不足",
        "message": "必要なパッケージがインストールされていません",
        "solution": "必要なパッケージをインストールしてください。詳細はログを確認してください。"
    },
    "ConnectionError": {
        "title": "接続エラー",
        "message": "サーバーに接続できません",
        "solution": "ファイアウォール設定を確認するか、別のポートを試してください。"
    },
    "PortInUseError": {
        "title": "ポート使用中",
        "message": "指定されたポートは既に他のアプリケーションが使用しています",
        "solution": "設定から別のポート番号を指定してください。"
    },
    "ServerStartError": {
        "title": "サーバー起動エラー",
        "message": "サーバーの起動に失敗しました",
        "solution": "ログファイルを確認し、依存関係が正しくインストールされているか確認してください。"
    },
    "DependencyError": {
        "title": "依存関係エラー",
        "message": "必要な依存関係が不足しています",
        "solution": "Blenderのコンソールで `pip install` コマンドを実行してください。"
    },
    "ConfigurationError": {
        "title": "設定エラー",
        "message": "設定が不正または不足しています",
        "solution": "アドオン設定を確認してください。"
    },
    "GraphQLError": {
        "title": "GraphQLエラー",
        "message": "GraphQLクエリの実行中にエラーが発生しました",
        "solution": "クエリ構文を確認してください。詳細はログに記録されています。"
    },
    "default": {
        "title": "エラーが発生しました",
        "message": "操作の実行中にエラーが発生しました",
        "solution": "ログファイルで詳細を確認してください。"
    }
}

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

def get_error_type(error_obj, error_msg):
    """エラーオブジェクトとメッセージからエラー種別を判定"""
    error_type = "default"
    
    # エラーオブジェクトがある場合はクラス名を使用
    if error_obj is not None:
        error_class = error_obj.__class__.__name__
        if error_class in ERROR_TYPES:
            return error_class
    
    # エラーメッセージからエラー種別を推測
    error_msg_lower = error_msg.lower()
    
    # 特定のエラーパターンを検出
    if "port" in error_msg_lower and ("in use" in error_msg_lower or "already" in error_msg_lower):
        return "PortInUseError"
    elif "import" in error_msg_lower or "module" in error_msg_lower and "not found" in error_msg_lower:
        return "ImportError"
    elif "connect" in error_msg_lower or "connection" in error_msg_lower:
        return "ConnectionError"
    elif "server" in error_msg_lower and "start" in error_msg_lower:
        return "ServerStartError"
    elif "dependenc" in error_msg_lower:
        return "DependencyError"
    elif "graphql" in error_msg_lower:
        return "GraphQLError"
    elif "config" in error_msg_lower:
        return "ConfigurationError"
    
    return error_type

def format_user_friendly_error(error_title, error_message, error_obj=None):
    """ユーザーフレンドリーなエラーメッセージを生成"""
    # エラー種別の判定
    error_type = get_error_type(error_obj, error_message)
    error_info = ERROR_TYPES.get(error_type, ERROR_TYPES["default"])
    
    # エラーメッセージの構築
    friendly_message = f"{error_info['title']}: {error_info['message']}\n\n"
    friendly_message += f"対処方法: {error_info['solution']}\n\n"
    
    # 技術的なエラー情報を追加（詳細表示向け）
    friendly_message += f"技術情報: {error_title}: {error_message}"
    
    return friendly_message

def save_error_log(error_title, error_message, error_obj=None, include_traceback=True, 
                   context_info=None, error_type=None):
    """エラーログをJSONファイルとして保存"""
    # エラー種別が指定されていなければ判定
    if error_type is None:
        error_type = get_error_type(error_obj, error_message)
    
    # 現在の時刻を取得
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # エラーログファイルのパス
    error_id = f"{error_type}_{timestamp}"
    error_log_file = os.path.join(error_logs_dir, f"{error_id}.json")
    
    # エラー情報の構造化
    error_data = {
        "error_id": error_id,
        "timestamp": datetime.now().isoformat(),
        "title": error_title,
        "message": error_message,
        "type": error_type,
        "traceback": traceback.format_exc() if include_traceback else "Not included"
    }
    
    # コンテキスト情報があれば追加
    if context_info:
        error_data["context"] = context_info
    
    # エラーデータをJSONファイルに保存
    try:
        with open(error_log_file, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"エラーログを保存しました: {error_log_file}")
        return error_log_file
    except Exception as e:
        logger.error(f"エラーログの保存に失敗しました: {e}")
        return None

def log_error(error_title, error_message, error_obj=None, include_traceback=True,
               context_info=None):
    """エラーをログに記録し、エラーログファイルにも保存"""
    # 標準ロガーを使ってログに記録
    logger.error(f"{error_title}: {error_message}")
    
    # トレースバック情報を記録
    if include_traceback:
        if error_obj:
            tb_str = "".join(traceback.format_exception(type(error_obj), error_obj, error_obj.__traceback__))
            logger.error(f"トレースバック:\n{tb_str}")
        else:
            tb_str = traceback.format_exc()
            logger.error(f"トレースバック:\n{tb_str}")
    
    # エラーログファイルに保存
    return save_error_log(
        error_title, 
        error_message, 
        error_obj, 
        include_traceback, 
        context_info
    )

def handle_error(error_title, error_message, error_obj=None, include_traceback=True, 
                 context_info=None, show_dialog=True):
    """エラーを完全に処理（ログ記録、ファイル保存、ユーザー通知）"""
    # エラーをログに記録し、ファイルに保存
    error_log_file = log_error(error_title, error_message, error_obj, include_traceback, context_info)
    
    # ユーザーフレンドリーなメッセージを生成
    user_message = format_user_friendly_error(error_title, error_message, error_obj)
    
    # 必要に応じてダイアログを表示
    if show_dialog:
        try:
            # bpyが利用可能か確認
            import bpy
            
            # エラーレポートオペレータを実行
            def show_error_report():
                # OperatorPropertiesを取得
                op = bpy.ops.mcp.show_error_report
                if hasattr(op, 'get_instance'):
                    # オペレータインスタンスを取得
                    op_instance = op.get_instance()
                    op_instance.error_message = user_message
                    op_instance.error_log_file = error_log_file or ""
                
                # オペレータを呼び出し
                bpy.ops.mcp.show_error_report('INVOKE_DEFAULT')
            
            # Blenderのタイマーでオペレータを呼び出し
            if hasattr(bpy.app, 'timers'):
                bpy.app.timers.register(show_error_report, first_interval=0.1)
        except Exception as dialog_error:
            logger.error(f"エラーダイアログの表示に失敗: {dialog_error}")
    
    return {
        "error_message": user_message,
        "error_log_file": error_log_file,
        "error_type": get_error_type(error_obj, error_message)
    }

# 古いログファイルを整理する関数
def cleanup_old_logs(max_logs=50, max_age_days=30):
    """古いエラーログファイルを削除"""
    try:
        # 今日の日付
        today = datetime.now()
        
        # ログファイルを列挙
        error_logs = []
        for filename in os.listdir(error_logs_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(error_logs_dir, filename)
                # ファイルの修正日時を取得
                mtime = os.path.getmtime(filepath)
                mtime_date = datetime.fromtimestamp(mtime)
                
                # 日数差を計算
                days_old = (today - mtime_date).days
                
                error_logs.append({
                    'path': filepath,
                    'mtime': mtime,
                    'days_old': days_old
                })
        
        # 古い順にソート
        error_logs.sort(key=lambda x: x['mtime'])
        
        # 最大数を超えるか、指定日数より古いログを削除
        deleted_count = 0
        for log in error_logs:
            delete = False
            
            # 最大数を超える場合（ただし最新のmax_logs個は常に保持）
            if len(error_logs) - deleted_count > max_logs:
                delete = True
            
            # 指定日数より古い場合
            if log['days_old'] > max_age_days:
                delete = True
            
            if delete:
                try:
                    os.remove(log['path'])
                    deleted_count += 1
                    logger.debug(f"古いエラーログを削除: {log['path']}")
                except Exception as e:
                    logger.error(f"ログファイル削除エラー: {e}")
        
        if deleted_count > 0:
            logger.info(f"{deleted_count}個の古いエラーログファイルを削除しました")
        
        return deleted_count
    except Exception as e:
        logger.error(f"ログクリーンアップエラー: {e}")
        return 0

# 指定されたタイプのエラーログを取得
def get_error_logs_by_type(error_type=None, max_count=10):
    """指定されたタイプのエラーログを取得"""
    try:
        # エラーログファイルを列挙
        error_logs = []
        for filename in os.listdir(error_logs_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(error_logs_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)
                        
                        # タイプが指定されていない、または一致する場合
                        if error_type is None or log_data.get('type') == error_type:
                            # 修正日時を追加
                            log_data['file_mtime'] = os.path.getmtime(filepath)
                            log_data['file_path'] = filepath
                            error_logs.append(log_data)
                except Exception as e:
                    logger.error(f"エラーログ読み込みエラー ({filepath}): {e}")
        
        # 新しい順にソート
        error_logs.sort(key=lambda x: x.get('file_mtime', 0), reverse=True)
        
        # 最大数を制限
        return error_logs[:max_count]
    except Exception as e:
        logger.error(f"エラーログ取得エラー: {e}")
        return []

# エラーログファイルを開く
def open_error_log_file(file_path):
    """エラーログファイルをシステムのデフォルトアプリケーションで開く"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"エラーログファイルが存在しません: {file_path}")
            return False
        
        # OSに応じたファイルを開くコマンド - 安全な実装に改善
        if sys.platform == 'win32':
            # Windowsのos.startfileは安全(シェルコマンドを使用しない)
            os.startfile(file_path)
        elif sys.platform == 'darwin':  # macOS
            import subprocess
            import shlex
            # パスを検証して存在するファイルか確認
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                logger.error(f"無効なファイルパス: {file_path}")
                return False
            # 安全な実行 - shell=False と明示的に指定
            subprocess.Popen(['open', file_path], shell=False)
        else:  # linux
            import subprocess
            import shlex
            # パスを検証して存在するファイルか確認
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                logger.error(f"無効なファイルパス: {file_path}")
                return False
            # 安全な実行 - shell=False と明示的に指定
            subprocess.Popen(['xdg-open', file_path], shell=False)
        
        logger.info(f"エラーログファイルを開きました: {file_path}")
        return True
    except Exception as e:
        logger.error(f"エラーログファイルを開けませんでした: {e}")
        return False

# Blenderのオペレータクラス定義
# 注: 直接bpyをインポートするとエラーになる可能性があるため、
# 動的にロードし、存在しない場合は無視

def register_operators():
    """エラーハンドリング関連のオペレータを登録"""
    try:
        import bpy
        
        # エラーレポート表示オペレータ
        class ErrorReportOperator(bpy.types.Operator):
            """エラーレポートを表示するオペレータ"""
            bl_idname = "mcp.show_error_report"
            bl_label = "GraphQL MCPエラーレポート"
            bl_description = "詳細なエラー情報を表示します"
            bl_options = {'REGISTER', 'INTERNAL'}
            
            error_message: bpy.props.StringProperty(default="不明なエラーが発生しました")
            error_log_file: bpy.props.StringProperty(default="")
            
            def execute(self, context):
                self.report({'ERROR'}, self.error_message.split('\n')[0])
                return {'FINISHED'}
            
            def invoke(self, context, event):
                return context.window_manager.invoke_props_dialog(self, width=400)
            
            def draw(self, context):
                layout = self.layout
                layout.label(text="エラーが発生しました", icon='ERROR')
                
                # 複数行のエラーメッセージを表示
                for i, line in enumerate(self.error_message.split('\n')):
                    if line.strip():
                        layout.label(text=line)
                    
                    # 多すぎる行数は省略
                    if i > 10:
                        layout.label(text="...")
                        break
                
                # ログファイルへのリンク
                if self.error_log_file and os.path.exists(self.error_log_file):
                    box = layout.box()
                    box.label(text="詳細なエラーログ:")
                    box.label(text=self.error_log_file)
                    
                    # ログファイルを開くボタン
                    row = box.row()
                    row.operator("mcp.open_error_log", text="エラーログを開く", icon='TEXT')
                    
                    # 最新のログファイルへのパスを設定
                    context.window_manager.clipboard = self.error_log_file
                    box.label(text="パスがクリップボードにコピーされました", icon='COPYDOWN')
        
        # エラーログファイルを開くオペレータ
        class OpenErrorLogOperator(bpy.types.Operator):
            """エラーログファイルを開くオペレータ"""
            bl_idname = "mcp.open_error_log"
            bl_label = "エラーログを開く"
            bl_description = "システムのデフォルトアプリケーションでエラーログファイルを開きます"

            def execute(self, context):
                try:
                    # 安全性チェック - ディレクトリが存在するか確認
                    if not os.path.exists(error_logs_dir) or not os.path.isdir(error_logs_dir):
                        self.report({'ERROR'}, "エラーログディレクトリが存在しません")
                        return {'CANCELLED'}

                    # エラーログディレクトリを開く - 安全な実装を呼び出す
                    open_error_log_file(error_logs_dir)
                    self.report({'INFO'}, "エラーログディレクトリを開きました")
                except Exception as e:
                    self.report({'ERROR'}, "エラーログを開けませんでした: " + str(e))

                return {'FINISHED'}
        
        # すべてのエラーログを表示するオペレータ
        class ViewAllErrorLogsOperator(bpy.types.Operator):
            """すべてのエラーログを表示するオペレータ"""
            bl_idname = "mcp.view_all_error_logs"
            bl_label = "すべてのエラーログを表示"
            bl_description = "記録されているすべてのエラーログを表示します"

            def execute(self, context):
                try:
                    # 安全性チェック - ディレクトリが存在するか確認
                    if not os.path.exists(error_logs_dir) or not os.path.isdir(error_logs_dir):
                        self.report({'ERROR'}, "エラーログディレクトリが存在しません")
                        return {'CANCELLED'}

                    # エラーログディレクトリを開く - 安全な実装を呼び出す
                    open_error_log_file(error_logs_dir)
                    self.report({'INFO'}, "エラーログディレクトリを開きました")
                except Exception as e:
                    self.report({'ERROR'}, "エラーログディレクトリを開けませんでした: " + str(e))

                return {'FINISHED'}
        
        # エラーログ管理パネル
        class MCP_PT_error_management(bpy.types.Panel):
            """エラーログ管理パネル"""
            bl_label = "エラーログ管理"
            bl_idname = "MCP_PT_error_management"
            bl_space_type = 'VIEW_3D'
            bl_region_type = 'UI'
            bl_category = 'MCP'
            bl_parent_id = "MCP_PT_server_panel"  # 親パネルIDを設定（存在する場合）
            bl_options = {'DEFAULT_CLOSED'}
            
            def draw(self, context):
                layout = self.layout
                
                # エラーログディレクトリ情報
                box = layout.box()
                box.label(text="エラーログ情報", icon='INFO')
                
                # エラーログディレクトリパス
                # 安全な方法でパスを表示
                box.label(text="ログディレクトリ: " + os.path.basename(logs_dir))

                # エラーログファイル数
                try:
                    error_log_count = len([f for f in os.listdir(error_logs_dir) if f.endswith('.json')])
                    box.label(text="エラーログ数: " + str(error_log_count))
                except:
                    box.label(text="エラーログ数: 不明")
                
                # エラーログ管理ボタン
                row = layout.row()
                row.operator("mcp.view_all_error_logs", text="エラーログを表示", icon='TEXT')
                
                # クリーンアップボタン
                sub_row = layout.row()
                cleanup_op = sub_row.operator("mcp.cleanup_error_logs", text="古いログを削除", icon='TRASH')
        
        # エラーログクリーンアップオペレータ
        class CleanupErrorLogsOperator(bpy.types.Operator):
            """古いエラーログを削除するオペレータ"""
            bl_idname = "mcp.cleanup_error_logs"
            bl_label = "古いエラーログを削除"
            bl_description = "30日以上経過した古いエラーログファイルを削除します"
            
            def execute(self, context):
                try:
                    # クリーンアップを実行
                    deleted_count = cleanup_old_logs(max_logs=50, max_age_days=30)
                    self.report({'INFO'}, f"{deleted_count}個の古いエラーログを削除しました")
                except Exception as e:
                    self.report({'ERROR'}, f"エラーログのクリーンアップに失敗しました: {e}")
                
                return {'FINISHED'}
        
        # 登録するクラス
        classes = [
            ErrorReportOperator,
            OpenErrorLogOperator,
            ViewAllErrorLogsOperator,
            CleanupErrorLogsOperator,
            MCP_PT_error_management
        ]
        
        # クラスを登録
        for cls in classes:
            try:
                bpy.utils.register_class(cls)
            except Exception as e:
                logger.error(f"オペレータ登録エラー ({cls.__name__}): {e}")
        
        logger.info("エラーハンドリングオペレータを登録しました")
        return True
    
    except ImportError:
        # bpyが利用できない環境（Blender外での実行など）
        logger.warning("bpyモジュールが利用できないため、Blenderオペレータは登録されません")
        return False
    except Exception as e:
        logger.error(f"オペレータ登録エラー: {e}")
        return False

def register():
    """エラーハンドリングモジュールを登録"""
    logger.info("エラーハンドリングモジュールを登録しました")
    
    # 古いログをクリーンアップ
    cleanup_old_logs()
    
    # オペレータを登録
    register_operators()

def unregister():
    """エラーハンドリングモジュールの登録解除"""
    logger.info("エラーハンドリングモジュールを登録解除しました")
    
    try:
        import bpy
        # 登録したクラスを登録解除
        classes = [
            "ErrorReportOperator",
            "OpenErrorLogOperator",
            "ViewAllErrorLogsOperator",
            "CleanupErrorLogsOperator",
            "MCP_PT_error_management"
        ]
        
        for cls_name in classes:
            try:
                # クラス名からクラスを取得
                cls = getattr(bpy.types, f"MCP_OT_{cls_name}" if not cls_name.startswith("MCP_PT_") else cls_name)
                bpy.utils.unregister_class(cls)
            except Exception:
                pass
    except ImportError:
        # bpyが利用できない環境
        pass
