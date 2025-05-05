"""
Blender GraphQL MCP Addon
GraphQLを使用したBlender APIサーバーを提供します
"""

bl_info = {
    "name": "Blender GraphQL MCP",
    "author": "User",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),  # Blender 4.x互換性
    "location": "View3D > Sidebar > MCP",
    "description": "GraphQL APIサーバー",
    "warning": "",
    "doc_url": "",
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
log_file = os.path.join(home_dir, "blender_graphql_mcp_server.log")

# ロガー設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ログファイルの場所を記録
logger.info(f"ログファイル: {log_file}")
logger.info(f"アドオン起動: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# サードパーティ依存関係の管理
def ensure_dependencies():
    """必要な依存関係が入っているか確認し、なければインストールする"""
    import bpy
    import os
    import sys
    import subprocess
    
    logger.info("\n" + "="*50)
    logger.info(f"依存関係チェック開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Blenderバージョン: {bpy.app.version_string}")
    logger.info(f"Pythonバージョン: {sys.version}")
    logger.info("="*50)
    
    # 依存ライブラリのインポート確認
    dependencies = {
        'graphql-core': None
    }
    
    # Pythonパッケージ・インストール用の関数
    def ensurepip():
        """必要ならpipをインストールする"""
        try:
            import pip
            logger.info("pipは既に利用可能です")
            return True
        except ImportError as e:
            logger.warning(f"pipのインポートに失敗しました: {e}")
            try:
                logger.info("ensurepipを使用してpipをインストールしています...")
                import ensurepip
                ensurepip.bootstrap()
                os.environ.pop("PIP_REQ_TRACKER", None)  # Reset the pip internal trackers
                logger.info("pipのインストールに成功しました")
                return True
            except Exception as e:
                logger.error(f"pipのインストールに失敗しました: {e}")
                logger.error(traceback.format_exc())
                return False
    
    # アドオンパスとvendorパスを追加
    addon_path = os.path.dirname(os.path.abspath(__file__))
    vendor_path = os.path.join(addon_path, "vendor")
    if not os.path.exists(vendor_path):
        os.makedirs(vendor_path)
        logger.info(f"vendorディレクトリを作成しました: {vendor_path}")
    
    # パスをPythonパスに追加
    for path in [addon_path, vendor_path]:
        if path not in sys.path:
            sys.path.insert(0, path)
            logger.info(f"パスをPythonパスに追加: {path}")
    
    # importlibのキャッシュをリセット
    importlib.invalidate_caches()
    
    # 依存関係のチェック
    missing = []
    for package, version in dependencies.items():
        try:
            module_name = package.replace('-', '_')
            module = __import__(module_name)
            logger.info(f"{package} は正常にインポートされました。バージョン: {getattr(module, '__version__', '不明')}")
        except ImportError as e:
            logger.warning(f"{package} のインポートに失敗しました: {e}")
            missing.append((package, version))
        except Exception as e:
            logger.error(f"{package} のインポート中に予期しないエラーが発生しました: {e}")
            logger.error(traceback.format_exc())
            missing.append((package, version))
    
    # 依存関係のインストール
    if missing:
        logger.info(f"\n{len(missing)}個の依存関係が不足しています：{missing}")
        
        # pip確認
        if ensurepip():
            import pip
            logger.info("pipが利用可能です。必要な依存関係をインストールします...")
            
            # 各パッケージをインストール
            for package, version in missing:
                package_spec = f"{package}=={version}" if version else package
                
                try:
                    logger.info(f"{package}をインストール中...")
                    cmd = [sys.executable, "-m", "pip", "install", f"--target={vendor_path}", package_spec]
                    logger.debug(f"実行コマンド: {' '.join(cmd)}")
                    
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"{package}のインストールに成功しました")
                        logger.debug(f"stdout: {result.stdout}")
                    else:
                        logger.error(f"{package}のインストールに失敗しました。リターンコード: {result.returncode}")
                        logger.error(f"stdout: {result.stdout}")
                        logger.error(f"stderr: {result.stderr}")
                except Exception as e:
                    logger.error(f"{package}のインストール中に例外が発生しました: {e}")
                    logger.error(traceback.format_exc())
            
            # 再度インポートキャッシュをクリア
            importlib.invalidate_caches()
        else:
            logger.error("pipがインストールされていません。手動で依存関係をインストールしてください。")
            return False
    
    # 再度依存関係をチェック
    logger.info("再度依存関係をチェックしています...")
    missing_after = []
    for package, version in dependencies.items():
        try:
            module_name = package.replace('-', '_')
            module = __import__(module_name)
            logger.info(f"{package} は正常にインポートされました。バージョン: {getattr(module, '__version__', '不明')}")
        except ImportError as e:
            logger.warning(f"{package} の再インポートに失敗しました: {e}")
            missing_after.append(package)
        except Exception as e:
            logger.error(f"{package} の再インポート中に予期しないエラーが発生しました: {e}")
            logger.error(traceback.format_exc())
            missing_after.append(package)
    
    if missing_after:
        logger.error(f"依然として{len(missing_after)}個の依存関係が不足しています: {missing_after}")
        # 不足している依存関係があっても進めることを許可
        logger.warning("不足している依存関係がありますが、進行を試みます...")
        return True
    
    logger.info("すべての依存関係が正常にインストールされています。")
    return True

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
        default=8765,
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
        # 依存関係チェックを実行するが、失敗してもサーバー起動を試みる
        ensure_dependencies()
        
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
            
            # 指定されたポートとホストでサーバー起動
            success = server_adapter.start_server(host=host, port=port)
            
            if success:
                self.report({'INFO'}, f"サーバーを起動しました: {host}:{port}")
                # UIの更新を強制する
                for area in context.screen.areas:
                    area.tag_redraw()
                return {'FINISHED'}
            else:
                # エラーメッセージをログから取得する
                self.report({'ERROR'}, "サーバーの起動に失敗しました。ログを確認してください。")
                return {'CANCELLED'}
                
        except Exception as e:
            import traceback
            error_message = str(e)
            logger.error(f"サーバー起動エラー: {error_message}")
            logger.error(traceback.format_exc())
            self.report({'ERROR'}, f"サーバー起動エラー: {error_message}")
            return {'CANCELLED'}

class MCP_OT_stop_server(bpy.types.Operator):
    """GraphQL APIサーバーを停止"""
    bl_idname = "mcp.stop_server"
    bl_label = "GraphQL APIサーバー停止"
    
    def execute(self, context):
        try:
            # サーバーが起動しているか確認
            if not server_adapter.is_server_running():
                self.report({'WARNING'}, "サーバーは既に停止しています")
                return {'FINISHED'}
            
            # サーバーを停止
            server_adapter.stop_server()
            self.report({'INFO'}, "サーバーを停止しました")
            
            # UIの更新を強制する
            for area in context.screen.areas:
                area.tag_redraw()
                
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"サーバー停止エラー: {str(e)}")
            logger.error(f"サーバー停止エラー: {str(e)}")
            logger.error(traceback.format_exc())
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
    
    # サーバーが起動している場合は停止
    try:
        if 'server_adapter' in globals() and hasattr(server_adapter, 'is_server_running') and server_adapter.is_server_running():
            server_adapter.stop_server()
            print("MCPサーバーを停止しました")
    except:
        print("MCPサーバーの停止中にエラーが発生しました")
    
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