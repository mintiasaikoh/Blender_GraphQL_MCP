"""
Blender MCP Tools
LLM（AI）がBlenderを操作するためのツールセット
"""

bl_info = {
    "name": "Blender MCP Tools",
    "author": "Blender MCP Tools Team",
    "version": (1, 2, 0),
    "blender": (4, 2, 0),  # Blender 4.2以降互換性
    "location": "View3D > Sidebar > MCP",
    "description": "AI-powered Blender control through Model Context Protocol",
    "warning": "",
    "doc_url": "https://github.com/user/blender-mcp-tools",
    "category": "Development",
    "support": "COMMUNITY"
}

import bpy
import os
import sys
import importlib
import importlib.util
import logging
import traceback
from datetime import datetime

# ロギング設定
# ユーザーホームディレクトリにログファイルを作成
home_dir = os.path.expanduser("~")
logs_dir = os.path.join(home_dir, "blender_graphql_mcp_logs")

# ログディレクトリが存在しない場合は作成
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir, exist_ok=True)

# 現在の日時をログファイル名に使用
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(logs_dir, f"blender_graphql_mcp_{current_time}.log")

# 最新のログファイルへのシンボリックリンク（相対パスでアクセスするため）
latest_log_file = os.path.join(logs_dir, "latest.log")

# シンボリックリンクを更新（可能な場合）
try:
    if os.path.exists(latest_log_file):
        os.remove(latest_log_file)
    
    # Windowsの場合はsymlinkの代わりにハードリンク（またはコピー）を使用
    if sys.platform == 'win32':
        # Windowsではハードリンクが失敗する可能性があるためコピーで対応
        import shutil
        def update_latest_log():
            if os.path.exists(log_file):
                if os.path.exists(latest_log_file):
                    os.remove(latest_log_file)
                shutil.copy2(log_file, latest_log_file)
        
        # 遅延実行（ファイル作成後）
        import threading
        threading.Timer(1.0, update_latest_log).start()
    else:
        # Unix系OSではシンボリックリンクを使用
        os.symlink(os.path.basename(log_file), latest_log_file)
except Exception as e:
    print(f"最新ログファイルのリンク作成に失敗: {e}")

# ログローテーション（古いログファイルを削除）
def cleanup_old_logs(logs_dir, max_logs=10):
    try:
        log_files = [f for f in os.listdir(logs_dir) 
                    if f.startswith("blender_graphql_mcp_") and f.endswith(".log")]
        
        # 日付順にソートして古いものを特定
        log_files.sort(reverse=True)  # 最新のログが先頭
        
        # 最大数を超えるログファイルを削除
        if len(log_files) > max_logs:
            for old_file in log_files[max_logs:]:
                try:
                    old_path = os.path.join(logs_dir, old_file)
                    os.remove(old_path)
                    print(f"古いログファイルを削除: {old_path}")
                except:
                    pass
    except Exception as e:
        print(f"ログクリーンアップエラー: {e}")

# 古いログを掃除
cleanup_old_logs(logs_dir)

# ロガー設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("blender_graphql_mcp.init")

# ログファイルの場所を記録
logger.info(f"ログファイルディレクトリ: {logs_dir}")
logger.info(f"現在のログファイル: {log_file}")
logger.info(f"アドオン起動: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# サードパーティ依存関係の管理
def ensure_dependencies():
    """必要な依存関係が入っているか確認し、なければインストールする"""
    import bpy
    import os
    import sys

    logger.info("\n" + "="*50)
    logger.info(f"依存関係チェック開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Blenderバージョン: {bpy.app.version_string}")
    logger.info(f"Pythonバージョン: {sys.version}")
    logger.info("="*50)

    # Blender 4.2以降のバージョンチェック
    from core.blender_version_utils import check_minimum_blender_version
    if not check_minimum_blender_version():
        logger.error("Blender GraphQL MCPはBlender 4.2以降のみをサポートしています")
        return False

    # Extensionsシステム利用可能性の確認
    from core.blender_version_utils import is_extensions_system_available
    if not is_extensions_system_available():
        logger.error("Blender ExtensionsシステムがBlender 4.2で利用できません。これは予期しないエラーです。")
        return False

    # 依存関係管理モジュールをインポート
    try:
        # 依存関係管理システムをインポート
        from core.dependency_manager import ensure_dependencies as ensure_deps
        logger.info("Extensions依存関係管理システムを使用します")
        result = ensure_deps()
        if result:
            logger.info("依存関係管理が正常に完了しました")
            # アドオンディレクトリをPythonパスに追加
            addon_path = os.path.dirname(os.path.abspath(__file__))
            if addon_path not in sys.path:
                sys.path.insert(0, addon_path)
                logger.info(f"アドオンパスをPythonパスに追加: {addon_path}")
                importlib.invalidate_caches()
        else:
            logger.warning("依存関係管理で問題が発生しました")
        return result
    except ImportError as e:
        logger.error(f"依存関係管理システムをインポートできません: {e}")
        return False

# 依存関係を確認
DEPENDENCIES_AVAILABLE = ensure_dependencies()

# サーバーモジュール（条件付きインポート）
if DEPENDENCIES_AVAILABLE:
    from .core import server_adapter
else:
    logger.error("依存関係が不足しているため、MCPサーバーは起動できません")

# BlenderにMCP設定を登録
class MCPAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    server_port: bpy.props.IntProperty(
        name="サーバーポート",
        description="サーバーが使用するポート番号",
        default=8000,
        min=1024,
        max=65535
    )
    
    server_host: bpy.props.StringProperty(
        name="サーバーホスト",
        description="サーバーがバインドするホストアドレス",
        default="0.0.0.0",
        maxlen=15 # 最大長の制限を追加
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "server_port")
        
        # サーバーホスト設定の表示を改善
        host_row = layout.row()
        host_row.label(text="サーバーホスト:")
        host_row.prop(self, "server_host", text="")
        
        # 推奨設定とステータス表示
        if self.server_host != "0.0.0.0":
            layout.label(text="リモート接続を受け付けるには '0.0.0.0' をお勧めします", icon='INFO')
        else:
            layout.label(text="現在の設定: 全てのインターフェースでリッスン (推奨)", icon='CHECKMARK')

# UI定義
class MCP_PT_server_panel(bpy.types.Panel):
    """GraphQL APIサーバーパネル"""
    bl_label = "GraphQL Server"
    bl_idname = "MCP_PT_server_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MCP'
    
    def draw(self, context):
        layout = self.layout
        prefs = context.preferences.addons[__name__].preferences
        
        # サーバー設定と制御
        # 強制的に状態を再取得する - 複数の方法で状態を確認
        is_running = False
        
        # サーバーアダプタからの状態取得を試行
        if 'server_adapter' in globals() and hasattr(server_adapter, 'is_server_running'):
            # サーバー状態を明示的に確認
            is_running = server_adapter.is_server_running()
            
            # 直接アダプターのrunning変数も確認
            adapter_instance = server_adapter.get_server_instance()
            if adapter_instance:
                if hasattr(adapter_instance, 'running') and adapter_instance.running:
                    is_running = True
                elif hasattr(adapter_instance, 'server_instance') and adapter_instance.server_instance:
                    # サーバーインスタンスの状態も確認
                    if hasattr(adapter_instance.server_instance, 'server_running') and adapter_instance.server_instance.server_running:
                        is_running = True
            
            # デバッグ情報を追加
            status_text = "実行中" if is_running else "停止中"
            logger.info(f"UI更新: サーバー状態 = {status_text}")
        
        box = layout.box()
        box.label(text="サーバーステータス", icon='INFO')
        status_row = box.row()
        if is_running:
            status_row.label(text="実行中", icon='CHECKMARK')
        else:
            status_row.label(text="停止中", icon='X')
            
        # ポートとホスト設定を表示
        port_row = box.row()
        port_row.label(text=f"ポート: {prefs.server_port}")
        port_row.operator("mcp.open_preferences", text="", icon='PREFERENCES')
        
        # ホスト設定を表示
        host_row = box.row()
        host_row.label(text=f"ホスト: {prefs.server_host}")
        
        # サーバーコントロール
        row = layout.row()
        row.operator("mcp.start_server", text="サーバー起動", icon='PLAY')
        row.operator("mcp.stop_server", text="サーバー停止", icon='PAUSE')

class MCP_OT_start_server(bpy.types.Operator):
    """GraphQL APIサーバーを起動"""
    bl_idname = "mcp.start_server"
    bl_label = "GraphQL APIサーバー起動"
    
    def execute(self, context):
        # エラーハンドラをインポート（存在すれば）
        error_handler = None
        try:
            from .utils import error_handler
        except ImportError:
            logger.warning("エラーハンドラモジュールをインポートできません")
        
        # 依存関係チェック
        deps_result = ensure_dependencies()
        if not deps_result:
            logger.warning("依存関係が不足していますが、サーバー起動を試みます")
            # エラーハンドラを使用してエラーログを記録（オプション）
            if 'error_handler' in locals() and error_handler:
                error_handler.log_error(
                    "依存関係エラー", 
                    "一部の依存関係が不足しています。サーバー機能が制限される可能性があります。",
                    context_info={"dependencies_check": "failed"}
                )
        
        # アドオン設定からポートとホストを取得
        prefs = context.preferences.addons[__name__].preferences
        port = prefs.server_port
        host = prefs.server_host
        
        try:
            # サーバーが既に起動しているか確認
            if server_adapter.is_server_running():
                self.report({'WARNING'}, "サーバーは既に起動しています")
                # UIの更新を強制する
                for area in context.screen.areas:
                    area.tag_redraw()
                return {'FINISHED'}
            
            # ポートが使用可能か確認
            port_available = True
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                result = s.connect_ex(("127.0.0.1", port))
                s.close()
                
                if result == 0:  # ポートが既に使用中
                    port_available = False
                    
                    # 自動ポート割り当て機能
                    # 10個のポートを順番に試す
                    available_port = None
                    for test_port in range(port + 1, port + 11):
                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(1)
                            result = s.connect_ex(("127.0.0.1", test_port))
                            s.close()
                            if result != 0:  # ポートが使用可能
                                available_port = test_port
                                break
                        except:
                            continue
                    
                    if available_port:
                        # 利用可能なポートがあれば使用
                        port = available_port
                        logger.info(f"ポート {port - 1} は既に使用中です。代わりにポート {port} を使用します。")
                        # 設定もアップデート
                        prefs.server_port = port
                    else:
                        # 適切なポートが見つからない場合
                        if 'error_handler' in locals() and error_handler:
                            error_handler.handle_error(
                                "ポート使用中エラー",
                                f"ポート {port} は既に使用中で、利用可能なポートが見つかりませんでした。",
                                context_info={"port": port, "host": host}
                            )
                        
                        self.report({'ERROR'}, f"ポート {port} は既に使用中で、代替ポートが見つかりませんでした。設定から別のポートを指定してください。")
                        return {'CANCELLED'}
            except Exception as port_check_error:
                # ポートチェックエラーはログに記録するが、処理は継続
                logger.warning(f"ポート確認中にエラーが発生しました: {port_check_error}")
            
            # 指定されたポートとホストでサーバー起動
            logger.info(f"サーバーを起動します: {host}:{port}")
            success = server_adapter.start_server(host=host, port=port)
            
            if success:
                # 成功を報告
                self.report({'INFO'}, f"サーバーを起動しました: {host}:{port}")
                
                # UIの更新を強制する
                for area in context.screen.areas:
                    area.tag_redraw()
                    
                # ヘルスチェックタイマーを設定（サーバーの状態監視）
                def health_check_timer():
                    """サーバー状態を定期的に確認し、必要であれば回復する"""
                    try:
                        if 'server_adapter' in globals():
                            # サーバーが実行中フラグだが、接続テストに失敗する場合は再起動を試みる
                            is_running_flag = server_adapter.is_server_running()
                            
                            # 実際の接続テスト
                            connection_alive = False
                            try:
                                import socket
                                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                s.settimeout(1)
                                s.connect(("127.0.0.1", port))
                                s.close()
                                connection_alive = True
                            except:
                                connection_alive = False
                            
                            # 不一致の検出と回復
                            if is_running_flag and not connection_alive:
                                logger.warning("サーバーが予期せず停止しています。再起動を試みます...")
                                server_adapter.stop_server()  # 一旦停止処理
                                import time
                                time.sleep(1)
                                # 再起動
                                success = server_adapter.start_server(host=host, port=port)
                                if success:
                                    logger.info("サーバーの自動再起動に成功しました")
                                else:
                                    logger.error("サーバーの自動再起動に失敗しました")
                                    # エラーログを記録
                                    if 'error_handler' in locals() and error_handler:
                                        error_handler.log_error(
                                            "サーバー再起動エラー", 
                                            "サーバーの自動再起動に失敗しました",
                                            context_info={"port": port, "host": host}
                                        )
                    except Exception as e:
                        logger.error(f"ヘルスチェックエラー: {e}")
                    
                    return 30.0  # 30秒ごとに実行
                
                # ヘルスチェックタイマーを登録（既存のタイマーがあれば削除）
                if hasattr(bpy.app, 'timers'):
                    for timer in bpy.app.timers.get_list():
                        if timer.__name__ == health_check_timer.__name__:
                            bpy.app.timers.unregister(timer)
                    bpy.app.timers.register(health_check_timer)
                
                return {'FINISHED'}
            else:
                # エラーハンドラがある場合は使用
                if 'error_handler' in locals() and error_handler:
                    error_info = error_handler.handle_error(
                        "サーバー起動エラー", 
                        "GraphQL APIサーバーの起動に失敗しました。",
                        context_info={"port": port, "host": host}
                    )
                    self.report({'ERROR'}, error_info["error_message"].split('\n')[0])
                else:
                    # エラーハンドラがない場合のフォールバック
                    self.report({'ERROR'}, "サーバーの起動に失敗しました。ログを確認してください。")
                
                return {'CANCELLED'}
                
        except Exception as e:
            import traceback
            error_message = str(e)
            logger.error(f"サーバー起動エラー: {error_message}")
            logger.error(traceback.format_exc())
            
            # エラーハンドラがある場合は使用
            if 'error_handler' in locals() and error_handler:
                error_info = error_handler.handle_error(
                    "サーバー起動エラー", 
                    error_message,
                    error_obj=e,
                    context_info={"port": port, "host": host}
                )
                self.report({'ERROR'}, error_info["error_message"].split('\n')[0])
            else:
                # エラーハンドラがない場合のフォールバック
                self.report({'ERROR'}, f"サーバー起動エラー: {error_message}")
            
            return {'CANCELLED'}

class MCP_OT_stop_server(bpy.types.Operator):
    """GraphQL APIサーバーを停止"""
    bl_idname = "mcp.stop_server"
    bl_label = "GraphQL APIサーバー停止"
    
    def execute(self, context):
        # エラーハンドラをインポート（存在すれば）
        error_handler = None
        try:
            from .utils import error_handler
        except ImportError:
            logger.warning("エラーハンドラモジュールをインポートできません")
        
        try:
            # サーバーが起動しているか確認
            if not server_adapter.is_server_running():
                self.report({'WARNING'}, "サーバーは既に停止しています")
                return {'FINISHED'}
            
            # ヘルスチェックタイマーを停止（存在する場合）
            if hasattr(bpy.app, 'timers'):
                for timer in bpy.app.timers.get_list():
                    if timer.__name__ == 'health_check_timer':
                        try:
                            bpy.app.timers.unregister(timer)
                            logger.info("ヘルスチェックタイマーを停止しました")
                        except:
                            pass
            
            logger.info("サーバーを停止します...")
            
            # サーバーを停止
            stop_result = server_adapter.stop_server()
            
            if stop_result:
                self.report({'INFO'}, "サーバーを停止しました")
                
                # UIの更新を強制する
                for area in context.screen.areas:
                    area.tag_redraw()
                
                # サーバーが本当に停止したか確認
                import socket
                import time
                
                # サーバーが完全に停止するまで少し待機
                time.sleep(1.0)
                
                # 接続テスト（ポートが解放されたことを確認）
                try:
                    # アドオン設定からポートを取得
                    prefs = context.preferences.addons[__name__].preferences
                    port = prefs.server_port
                    
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    s.connect(("127.0.0.1", port))
                    s.close()
                    
                    # まだ接続できる場合はサーバーが停止していない可能性
                    logger.warning(f"サーバーが停止指示を受けましたが、ポート {port} への接続がまだ可能です")
                    
                    # エラーハンドラで記録（深刻なエラーではないので処理は続行）
                    if 'error_handler' in locals() and error_handler:
                        error_handler.log_error(
                            "サーバー停止警告", 
                            f"サーバーが停止指示を受けましたが、ポート {port} への接続がまだ可能です",
                            context_info={"port": port}
                        )
                except:
                    # 接続できない = 正常に停止している
                    logger.info("サーバーが正常に停止したことを確認しました")
                
                return {'FINISHED'}
            else:
                # 停止に失敗
                error_message = "サーバーの停止に失敗しました"
                
                # エラーハンドラで記録
                if 'error_handler' in locals() and error_handler:
                    error_info = error_handler.handle_error(
                        "サーバー停止エラー", 
                        error_message
                    )
                    self.report({'ERROR'}, error_info["error_message"].split('\n')[0])
                else:
                    self.report({'ERROR'}, error_message)
                
                return {'CANCELLED'}
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"サーバー停止エラー: {error_message}")
            logger.error(traceback.format_exc())
            
            # エラーハンドラで記録
            if 'error_handler' in locals() and error_handler:
                error_info = error_handler.handle_error(
                    "サーバー停止エラー", 
                    error_message,
                    error_obj=e
                )
                self.report({'ERROR'}, error_info["error_message"].split('\n')[0])
            else:
                self.report({'ERROR'}, f"サーバー停止エラー: {error_message}")
            
            return {'CANCELLED'}

class MCP_OT_install_dependencies(bpy.types.Operator):
    """依存関係のインストール手順を表示"""
    bl_idname = "mcp.install_dependencies"
    bl_label = "依存関係のインストール"
    
    def execute(self, context):
        self.report({'INFO'}, "依存関係を手動でインストールします")
        return {'FINISHED'}

class MCP_OT_open_preferences(bpy.types.Operator):
    """アドオンの設定画面を開く"""
    bl_idname = "mcp.open_preferences"
    bl_label = "設定画面を開く"
    
    def execute(self, context):
        bpy.ops.preferences.addon_show(module=__name__)
        return {'FINISHED'}

# クラス一覧
classes = (
    MCPAddonPreferences,
    MCP_PT_server_panel,  # GraphQL APIサーバーパネル
    MCP_OT_start_server,  # GraphQL APIサーバー起動
    MCP_OT_stop_server,   # GraphQL APIサーバー停止
    MCP_OT_install_dependencies,
    MCP_OT_open_preferences,
)

# アドオン登録
def register():
    # 各クラスを登録
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # 標準MCP対応を登録
    try:
        from blender_mcp.tools.mcp_standard_integration import register as register_mcp_standard
        register_mcp_standard()
        logger.info("標準MCP対応を登録しました")
    except ImportError as e:
        logger.warning(f"標準MCP対応の登録ができませんでした: {str(e)}")
    except Exception as e:
        logger.error(f"標準MCP対応の登録でエラーが発生しました: {str(e)}")
    
    # ハンドラを登録
    if hasattr(bpy.app, 'handlers') and hasattr(bpy.app.handlers, 'save_pre'):
        # save_pre ハンドラが存在する場合のみ追加
        
        # 既存のハンドラをチェックして重複を避ける
        for handler in bpy.app.handlers.save_pre:
            if 'mcp_save_handler' in str(handler):
                bpy.app.handlers.save_pre.remove(handler)
        
        # 保存前にサーバーを停止する関数
        def mcp_save_handler(dummy):
            # server_adapterが存在するか確認
            if 'server_adapter' in globals():
                # サーバーが起動しているか確認
                if hasattr(server_adapter, 'is_server_running') and server_adapter.is_server_running():
                    # サーバーを停止
                    server_adapter.stop_server()
                    print("MCPサーバーを保存前に停止しました")
            
            # 標準MCPサーバーも停止
            try:
                from blender_mcp.tools.mcp_server_manager import stop_mcp_server
                stop_mcp_server()
                print("標準MCPサーバーを保存前に停止しました")
            except ImportError:
                pass
            except Exception as e:
                print(f"標準MCPサーバーの停止中にエラーが発生しました: {str(e)}")
        
        # ハンドラを追加
        bpy.app.handlers.save_pre.append(mcp_save_handler)
    
    logger.info("Blender JSON MCP アドオンを登録しました")

# アドオン登録解除
def unregister():
    # ハンドラを削除
    if hasattr(bpy.app, 'handlers') and hasattr(bpy.app.handlers, 'save_pre'):
        # save_pre ハンドラが存在する場合のみ処理
        for handler in bpy.app.handlers.save_pre[:]:  # リストをコピーしてイテレート
            if 'mcp_save_handler' in str(handler):
                try:
                    bpy.app.handlers.save_pre.remove(handler)
                    print("MCPサーバーの保存ハンドラを削除しました")
                except ValueError:
                    pass
    
    # 標準MCPサーバーを停止
    try:
        from blender_mcp.tools.mcp_server_manager import stop_mcp_server
        stop_mcp_server()
        print("標準MCPサーバーを停止しました")
    except ImportError:
        pass
    except Exception as e:
        print(f"標準MCPサーバーの停止中にエラーが発生しました: {str(e)}")
    
    # 標準MCP対応の登録解除
    try:
        from blender_mcp.tools.mcp_standard_integration import unregister as unregister_mcp_standard
        unregister_mcp_standard()
        logger.info("標準MCP対応の登録を解除しました")
    except ImportError as e:
        logger.warning(f"標準MCP対応の登録解除ができませんでした: {str(e)}")
    except Exception as e:
        logger.error(f"標準MCP対応の登録解除でエラーが発生しました: {str(e)}")
    
    # GraphQLサーバーが起動している場合は停止
    try:
        if 'server_adapter' in globals() and hasattr(server_adapter, 'is_server_running') and server_adapter.is_server_running():
            server_adapter.stop_server()
            print("GraphQL MCPサーバーを停止しました")
    except:
        print("GraphQL MCPサーバーの停止中にエラーが発生しました")
    
    # 各クラスの登録を解除
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
    
    logger.info("Blender JSON MCP アドオンの登録を解除しました")

# モジュールが直接実行された場合
if __name__ == "__main__":
    register()