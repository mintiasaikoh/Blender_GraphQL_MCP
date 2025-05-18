"""
Blender Unified MCP UI Error Handler
ビジュアルなエラー通知と表示のためのユーティリティ
"""

import os
import sys
import bpy
import logging
import json
import time
import traceback
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum

# モジュールレベルのロガー
logger = logging.getLogger('unified_mcp.utils.ui_error_handler')

# デバッグモード設定（環境変数から取得）
DEBUG_MODE = os.environ.get('UNIFIED_MCP_DEBUG', '0').lower() in ('1', 'true', 'yes')

# 既存のエラーハンドラーをインポート
try:
    from .error_handler import log_error, save_error_log, get_error_type, format_user_friendly_error
    ERROR_HANDLER_AVAILABLE = True
except ImportError:
    ERROR_HANDLER_AVAILABLE = False
    logger.warning("error_handlerモジュールがインポートできません。基本実装を使用します。")

# ファイルユーティリティをインポート
try:
    from .fileutils import normalize_path, ensure_directory
    FILE_UTILS_AVAILABLE = True
except ImportError:
    FILE_UTILS_AVAILABLE = False
    logger.warning("fileutilsモジュールがインポートできません。基本実装を使用します。")


# エラーの重大度
class ErrorSeverity(Enum):
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


# エラーログフォルダの設定
home_dir = os.path.expanduser("~")
logs_dir = os.path.join(home_dir, "blender_graphql_mcp_logs")
error_logs_dir = os.path.join(logs_dir, "errors")

# ディレクトリ作成
for dir_path in [logs_dir, error_logs_dir]:
    try:
        if not os.path.exists(dir_path):
            if FILE_UTILS_AVAILABLE:
                ensure_directory(dir_path)
            else:
                os.makedirs(dir_path, exist_ok=True)
    except:
        pass


# エラータイプの分類（エラーハンドラーモジュールが無い場合の基本実装）
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
    "FileError": {
        "title": "ファイル操作エラー",
        "message": "ファイルの読み書き中にエラーが発生しました",
        "solution": "ファイルのパスと権限を確認してください。"
    },
    "PathError": {
        "title": "パス解決エラー",
        "message": "ファイルパスの解決中にエラーが発生しました",
        "solution": "パスが正しいことを確認し、相対パスの場合は基準ディレクトリを確認してください。"
    },
    "default": {
        "title": "エラーが発生しました",
        "message": "操作の実行中にエラーが発生しました",
        "solution": "ログファイルで詳細を確認してください。"
    }
}


def _get_error_type_fallback(error_obj, error_msg):
    """エラーオブジェクトとメッセージからエラー種別を判定（フォールバック実装）"""
    error_type = "default"
    
    # エラーオブジェクトがある場合はクラス名を使用
    if error_obj is not None:
        error_class = error_obj.__class__.__name__
        if error_class in ERROR_TYPES:
            return error_class
    
    # エラーメッセージからエラー種別を推測
    error_msg_lower = error_msg.lower()
    
    # 特定のエラーパターンを検出
    if "file" in error_msg_lower and ("read" in error_msg_lower or "write" in error_msg_lower or "open" in error_msg_lower):
        return "FileError"
    elif "path" in error_msg_lower or "directory" in error_msg_lower:
        return "PathError"
    elif "import" in error_msg_lower or "module" in error_msg_lower and "not found" in error_msg_lower:
        return "ImportError"
    elif "connect" in error_msg_lower or "connection" in error_msg_lower:
        return "ConnectionError"
    elif "port" in error_msg_lower and ("in use" in error_msg_lower or "already" in error_msg_lower):
        return "PortInUseError"
    
    return error_type


def _format_user_friendly_error_fallback(error_title, error_message, error_obj=None):
    """ユーザーフレンドリーなエラーメッセージを生成（フォールバック実装）"""
    # エラー種別の判定
    error_type = _get_error_type_fallback(error_obj, error_message)
    error_info = ERROR_TYPES.get(error_type, ERROR_TYPES["default"])
    
    # エラーメッセージの構築
    friendly_message = f"{error_info['title']}: {error_info['message']}\n\n"
    friendly_message += f"対処方法: {error_info['solution']}\n\n"
    
    # 技術的なエラー情報を追加（詳細表示向け）
    friendly_message += f"技術情報: {error_title}: {error_message}"
    
    return friendly_message


def _save_error_log_fallback(error_title, error_message, error_obj=None, include_traceback=True, 
                           context_info=None, error_type=None):
    """エラーログをJSONファイルとして保存（フォールバック実装）"""
    from datetime import datetime
    
    # エラー種別が指定されていなければ判定
    if error_type is None:
        error_type = _get_error_type_fallback(error_obj, error_message)
    
    # 現在の時刻を取得
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # エラーログファイルのパス
    error_id = f"{error_type}_{timestamp}"
    error_log_file = os.path.join(error_logs_dir, f"{error_id}.json")
    
    # ディレクトリを確保
    if not os.path.exists(error_logs_dir):
        try:
            os.makedirs(error_logs_dir, exist_ok=True)
        except:
            return None
    
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


def _get_normalized_path(path):
    """パスを正規化する（フォールバック実装）"""
    if FILE_UTILS_AVAILABLE:
        return normalize_path(path)
    else:
        return os.path.normpath(path)


def display_error_message(title, message, severity=ErrorSeverity.ERROR, display_method='POPUP'):
    """
    エラーメッセージを表示する
    
    Args:
        title: エラータイトル
        message: エラーメッセージ本文
        severity: エラーの重大度
        display_method: 表示方法 ('POPUP', 'REPORT', 'BOTH')
    """
    # 重大度に応じてアイコンを設定
    icon_map = {
        ErrorSeverity.INFO: 'INFO',
        ErrorSeverity.WARNING: 'ERROR',
        ErrorSeverity.ERROR: 'ERROR',
        ErrorSeverity.CRITICAL: 'CANCEL'
    }
    
    # 文字列型の重大度をEnumに変換
    if isinstance(severity, str):
        try:
            severity = ErrorSeverity(severity.upper())
        except:
            severity = ErrorSeverity.ERROR
    
    icon = icon_map.get(severity, 'ERROR')
    
    # コンテキストを取得
    context = bpy.context
    
    # ReportからのメッセージをWindowManagerに表示
    if display_method in ('REPORT', 'BOTH'):
        # bpy.ops.mcp.report_error('INVOKE_DEFAULT', title=title, message=message, severity=severity.value)
        
        # まだオペレータが登録されていない場合は単純なレポートを使用
        for line in message.split('\n'):
            if line.strip():
                bpy.ops.ui.reports_to_textblock()
                # 重大度に応じてレポートタイプを変更
                report_type = severity.value
                bpy.context.window_manager.popup_menu(lambda self, ctx: self.layout.label(text=line), title=title, icon=icon)
    
    # ポップアップダイアログを表示
    if display_method in ('POPUP', 'BOTH'):
        def draw_popup(self, context):
            layout = self.layout
            layout.label(text=title, icon=icon)
            
            for i, line in enumerate(message.split('\n')):
                if line.strip():
                    layout.label(text=line)
                    
                    # 多すぎる行数は省略
                    if i > 15:
                        layout.label(text="...")
                        break
        
        context.window_manager.popup_menu(draw_popup, title=f"MCP {severity.value}", icon=icon)


def show_error_dialog(title, message, error_obj=None, context_info=None):
    """
    エラーダイアログを表示し、ログファイルに記録する
    
    Args:
        title: エラータイトル
        message: エラーメッセージ本文
        error_obj: 例外オブジェクト（あれば）
        context_info: コンテキスト情報（オプション）
    
    Returns:
        エラーログファイルのパス（記録された場合）
    """
    # エラーをログに記録
    error_log_file = None
    if ERROR_HANDLER_AVAILABLE:
        error_log_file = save_error_log(title, message, error_obj, True, context_info)
        user_message = format_user_friendly_error(title, message, error_obj)
    else:
        error_log_file = _save_error_log_fallback(title, message, error_obj, True, context_info)
        user_message = _format_user_friendly_error_fallback(title, message, error_obj)
    
    # ユーザーへの通知
    severity = ErrorSeverity.ERROR
    if "警告" in title or "warning" in title.lower():
        severity = ErrorSeverity.WARNING
    elif "致命的" in title or "critical" in title.lower():
        severity = ErrorSeverity.CRITICAL
    
    # エラーダイアログを表示
    display_error_message(title, user_message, severity)
    
    # エラーログファイルのパスを返す
    return error_log_file


def show_error_report_panel(error_data):
    """
    エラーレポートパネルを表示する
    
    Args:
        error_data: エラー情報の辞書（エラーメッセージ、ログファイルパスなど）
    """
    # オペレータを呼び出し
    try:
        bpy.ops.mcp.show_error_report('INVOKE_DEFAULT', 
                                      error_message=error_data.get('error_message', '不明なエラー'),
                                      error_log_file=error_data.get('error_log_file', ''))
    except Exception as e:
        logger.error(f"エラーレポートパネルの表示に失敗しました: {e}")
        # 代替手段としてポップアップを表示
        display_error_message("エラーレポート", error_data.get('error_message', '不明なエラー'))


def register_ui_operators():
    """UI関連のオペレータを登録する"""
    
    # エラーレポート表示オペレータ
    class MCP_OT_show_error_report(bpy.types.Operator):
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
                box.label(text=os.path.basename(self.error_log_file))
                
                # ログファイルを開くボタン
                row = box.row()
                row.operator("mcp.open_error_log", text="エラーログを開く", icon='TEXT')
                
                # 最新のログファイルへのパスを設定
                context.window_manager.clipboard = self.error_log_file
                box.label(text="パスがクリップボードにコピーされました", icon='COPYDOWN')
    
    # エラーログファイルを開くオペレータ
    class MCP_OT_open_error_log(bpy.types.Operator):
        """エラーログファイルを開くオペレータ"""
        bl_idname = "mcp.open_error_log"
        bl_label = "エラーログを開く"
        bl_description = "システムのデフォルトアプリケーションでエラーログファイルを開きます"
        
        filepath: bpy.props.StringProperty(
            name="ファイルパス",
            description="開くログファイルのパス",
            default="",
            subtype='FILE_PATH'
        )

        def execute(self, context):
            # ファイルパスの取得
            filepath = self.filepath
            if not filepath:
                # クリップボードからパスを取得
                filepath = context.window_manager.clipboard
            
            # パスの正規化
            filepath = _get_normalized_path(filepath)
            
            if not filepath or not os.path.exists(filepath):
                # ファイルが指定されていない場合はログディレクトリを開く
                filepath = error_logs_dir
                if not os.path.exists(filepath):
                    self.report({'ERROR'}, "エラーログディレクトリが存在しません")
                    return {'CANCELLED'}
            
            try:
                # OSに応じたファイルを開くコマンド
                if sys.platform == 'win32':
                    os.startfile(filepath)
                elif sys.platform == 'darwin':  # macOS
                    import subprocess
                    subprocess.Popen(['open', filepath], shell=False)
                else:  # linux
                    import subprocess
                    subprocess.Popen(['xdg-open', filepath], shell=False)
                
                self.report({'INFO'}, f"ファイルを開きました: {os.path.basename(filepath)}")
                return {'FINISHED'}
            except Exception as e:
                self.report({'ERROR'}, f"ファイルを開けませんでした: {e}")
                return {'CANCELLED'}
    
    # レポートエラーオペレータ
    class MCP_OT_report_error(bpy.types.Operator):
        """エラーメッセージをレポートするオペレータ"""
        bl_idname = "mcp.report_error"
        bl_label = "エラーを報告"
        bl_description = "エラーメッセージをBlenderのレポートシステムに表示します"
        bl_options = {'REGISTER', 'INTERNAL'}
        
        title: bpy.props.StringProperty(name="タイトル", default="エラー")
        message: bpy.props.StringProperty(name="メッセージ", default="エラーが発生しました")
        severity: bpy.props.EnumProperty(
            name="重大度",
            items=[
                ('INFO', "情報", "情報メッセージ"),
                ('WARNING', "警告", "警告メッセージ"),
                ('ERROR', "エラー", "エラーメッセージ"),
                ('CRITICAL', "重大", "重大なエラーメッセージ")
            ],
            default='ERROR'
        )
        
        def execute(self, context):
            # 重大度に応じてレポートタイプを変更
            report_type = {'INFO': 'INFO', 'WARNING': 'WARNING',
                          'ERROR': 'ERROR', 'CRITICAL': 'ERROR'}.get(self.severity, 'ERROR')
            
            # メッセージを分割して報告
            for line in self.message.split('\n'):
                if line.strip():
                    self.report({report_type}, f"{self.title}: {line}")
            
            return {'FINISHED'}
    
    # クラスを登録
    classes = [
        MCP_OT_show_error_report,
        MCP_OT_open_error_log,
        MCP_OT_report_error
    ]
    
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            logger.error(f"オペレータ登録エラー ({cls.__name__}): {e}")


def unregister_ui_operators():
    """UI関連のオペレータの登録を解除する"""
    classes = [
        bpy.types.MCP_OT_show_error_report,
        bpy.types.MCP_OT_open_error_log,
        bpy.types.MCP_OT_report_error
    ]
    
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


def register():
    """UI関連のモジュールを登録する"""
    register_ui_operators()
    logger.info("UIエラーハンドラモジュールを登録しました")


def unregister():
    """UI関連のモジュールの登録を解除する"""
    unregister_ui_operators()
    logger.info("UIエラーハンドラモジュールを登録解除しました")