"""
Blender Unified MCP Preferences
アドオン設定と環境設定を管理
"""

import bpy
import os
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import (
    StringProperty, 
    IntProperty, 
    BoolProperty,
    EnumProperty, 
    FloatProperty, 
    PointerProperty
)

# アドオン設定クラス
class UnifiedMCPPreferences(AddonPreferences):
    """統合版MCPアドオンの環境設定"""
    bl_idname = "blender_json_mcp"  # アドオンの名前と一致させる
    
    # WebSocketサーバー設定
    websocket_port: IntProperty(
        name="WebSocketポート",
        description="WebSocketサーバーが使用するポート番号",
        default=9876,
        min=1024,
        max=65535
    )
    
    # HTTP APIサーバー設定
    http_port: IntProperty(
        name="HTTP APIポート",
        description="FastAPI HTTPサーバーが使用するポート番号",
        default=8000,
        min=1024,
        max=65535
    )
    
    # サーバーホスト設定
    host: StringProperty(
        name="ホスト",
        description="サーバーがバインドするホストアドレス",
        default="localhost"
    )
    
    # 自動起動設定
    auto_start_server: BoolProperty(
        name="自動起動",
        description="Blender起動時にサーバーを自動的に開始",
        default=False
    )
    
    # セキュリティ設定
    require_authentication: BoolProperty(
        name="認証を要求",
        description="APIリクエストに認証を要求",
        default=False
    )
    
    api_key: StringProperty(
        name="APIキー",
        description="クライアントの認証に使用するAPIキー",
        default="",
        subtype='PASSWORD'
    )
    
    # 実行制限設定
    restrict_code_execution: BoolProperty(
        name="コード実行を制限",
        description="任意のコード実行関数へのアクセスを制限",
        default=True
    )
    
    # デバッグ設定
    debug_mode: BoolProperty(
        name="デバッグモード",
        description="詳細なログ出力とデバッグ情報を有効化",
        default=False
    )
    
    log_to_file: BoolProperty(
        name="ファイルにログ",
        description="ログをファイルに出力",
        default=True
    )
    
    log_file_path: StringProperty(
        name="ログファイルパス",
        description="ログファイルの保存先",
        default="~/.blender_json_mcp.log",
        subtype='FILE_PATH'
    )
    
    # GraphQL設定
    enable_graphql: BoolProperty(
        name="GraphQLを有効化",
        description="GraphQL APIを有効化",
        default=True
    )
    
    # UI関連設定
    ui_theme: EnumProperty(
        name="UIテーマ",
        description="インターフェースのテーマ",
        items=[
            ('DEFAULT', 'デフォルト', 'Blenderのデフォルトテーマに合わせる'),
            ('DARK', 'ダーク', '暗いテーマ'),
            ('LIGHT', 'ライト', '明るいテーマ')
        ],
        default='DEFAULT'
    )
    
    # パネル表示設定
    show_advanced_options: BoolProperty(
        name="詳細オプションを表示",
        description="UIパネルに詳細オプションを表示",
        default=False
    )
    
    def draw(self, context):
        """設定パネルのUI表示"""
        layout = self.layout
        
        # サーバー設定セクション
        box = layout.box()
        box.label(text="サーバー設定:", icon='NETWORK_DRIVE')
        
        row = box.row()
        row.prop(self, "host")
        
        row = box.row(align=True)
        row.prop(self, "websocket_port")
        row.prop(self, "http_port")
        
        row = box.row()
        row.prop(self, "auto_start_server")
        
        # セキュリティ設定セクション
        box = layout.box()
        box.label(text="セキュリティ設定:", icon='LOCKED')
        
        row = box.row()
        row.prop(self, "require_authentication")
        
        if self.require_authentication:
            row = box.row()
            row.prop(self, "api_key")
        
        row = box.row()
        row.prop(self, "restrict_code_execution")
        
        # GraphQL設定
        box = layout.box()
        box.label(text="GraphQL設定:", icon='CONSTRAINT')
        
        row = box.row()
        row.prop(self, "enable_graphql")
        
        # デバッグ設定セクション
        box = layout.box()
        box.label(text="デバッグ設定:", icon='CONSOLE')
        
        row = box.row()
        row.prop(self, "debug_mode")
        
        row = box.row()
        row.prop(self, "log_to_file")
        
        if self.log_to_file:
            row = box.row()
            row.prop(self, "log_file_path")
        
        # UI設定セクション
        box = layout.box()
        box.label(text="UI設定:", icon='PREFERENCES')
        
        row = box.row()
        row.prop(self, "ui_theme")
        
        row = box.row()
        row.prop(self, "show_advanced_options")
        
        # ヘルプリンクセクション
        box = layout.box()
        box.label(text="ヘルプとリソース:", icon='HELP')
        
        row = box.row()
        row.operator("wm.url_open", text="ドキュメントを開く").url = "https://github.com/user/unified-mcp/wiki"
        
        row = box.row()
        row.operator("wm.url_open", text="問題を報告").url = "https://github.com/user/unified-mcp/issues"

# グローバル設定の取得
def get_preferences(context=None):
    """アドオン設定を取得"""
    if context is None:
        context = bpy.context
    
    prefs = context.preferences.addons.get("blender_json_mcp")
    if prefs:
        return prefs.preferences
    
    # 設定が見つからない場合はデフォルト値
    return UnifiedMCPPreferences.bl_rna.properties

# モジュール登録関数
def register():
    """設定モジュールを登録"""
    bpy.utils.register_class(UnifiedMCPPreferences)
    print("Unified MCP: 設定モジュールを登録しました")

def unregister():
    """設定モジュールの登録解除"""
    bpy.utils.unregister_class(UnifiedMCPPreferences)
    print("Unified MCP: 設定モジュールを登録解除しました")
