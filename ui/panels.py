"""
Blender GraphQL MCP UI Panels
Blender GraphQL APIのUI要素を定義
"""

import bpy
import json
import logging
from bpy.types import Panel, Operator
from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty

# サーバークラスをインポート
from ..core.http_server import MCPHttpServer

# ロギング設定
logger = logging.getLogger('blender_graphql_mcp.ui.panels')

# GraphQL関連のインポート
try:
    from ..graphql.api import query_blender, set_spatial_relationship, create_smart_object, enhanced_boolean_operation
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False

# デバッグメッセージ
print("\n=== Unified MCPパネルクラス読み込み中 ===\n")

# ------------------------
# メインパネル
# ------------------------
class VIEW3D_PT_blender_graphql_mcp_main(Panel):
    """Blender GraphQL MCPのメインパネル"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MCP"
    bl_label = "GraphQL MCP"
    bl_idname = "VIEW3D_PT_blender_graphql_mcp_main"
    
    def draw(self, context):
        if not hasattr(context, "scene"):
            return
        
        layout = self.layout
        
        # サーバーステータスセクション
        box = layout.box()
        row = box.row()
        row.label(text="サーバーステータス:")
        
        scene = context.scene
        if getattr(scene, 'blendermcp_server_running', False):
            row.label(text="実行中", icon='PLAY')
            
            # サーバー情報を表示
            server = MCPHttpServer.get_instance()
            if server:
                row = box.row()
                row.label(text=f"WebSocket: {server.ws_port}")
                row = box.row()
                row.label(text=f"HTTP API: {server.http_port}")
                row = box.row()
                row.operator("unified_mcp.open_docs", text="API ドキュメント", icon='URL')
            
            row = box.row()
            row.operator("unified_mcp.stop_server", text="サーバー停止", icon='PAUSE')
        else:
            row.label(text="停止中", icon='PAUSE')
            row = box.row()
            row.label(text=f"WebSocket ポート: {scene.blendermcp_port}")
            row = box.row()
            row.label(text=f"HTTP ポート: {scene.blendermcp_port + 1}")
            row = box.row()
            row.operator("unified_mcp.start_server", text="サーバー開始", icon='PLAY')
        
        # 基本機能セクション
        box = layout.box()
        box.label(text="利用可能なサービス:")
        
        # WebSocket JSON-RPC
        row = box.row()
        row.label(text="WebSocket API", icon='PLUGIN')
        
        # HTTP REST API
        row = box.row()
        row.label(text="HTTP REST API", icon='NETWORK_DRIVE')
        
        # GraphQL API
        row = box.row()
        if GRAPHQL_AVAILABLE:
            row.label(text="GraphQL API: 有効", icon='CHECKMARK')
            row.operator("unified_mcp.open_graphql", text="GraphQLパネル", icon='PREFERENCES')
        else:
            row.label(text="GraphQL API: 無効", icon='X')
        
        # コードエディター
        box = layout.box()
        box.label(text="Blenderコード実行:")
        row = box.row()
        row.operator("unified_mcp.open_code_editor", text="コードエディタを開く", icon='TEXT')

# ------------------------
# GraphQLパネル
# ------------------------
class VIEW3D_PT_blender_graphql_mcp_graphql(Panel):
    """Blender GraphQL MCP APIパネル"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MCP"
    bl_label = "GraphQL API"
    bl_idname = "VIEW3D_PT_blender_graphql_mcp_graphql"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        # GraphQLが利用可能な場合のみ表示
        return GRAPHQL_AVAILABLE
    
    def draw(self, context):
        layout = self.layout
        
        # クエリエディタ
        box = layout.box()
        box.label(text="クエリエディタ:")
        
        # クエリ入力フィールド
        box.prop(context.scene, "blendermcp_graphql_query", text="")
        
        # 実行ボタン
        row = box.row()
        row.operator("unified_mcp.execute_graphql_query", text="クエリ実行", icon='PLAY')
        
        # 結果表示
        if hasattr(context.scene, "blendermcp_graphql_status") and context.scene.blendermcp_graphql_status:
            box = layout.box()
            box.label(text="実行結果:")
            
            # 複数行のテキストを表示するためにカラムを使用
            col = box.column()
            status_text = context.scene.blendermcp_graphql_status
            
            # 長いテキストを複数行に分割
            lines = status_text.split('\n')
            for line in lines[:10]:  # 表示行数を制限
                col.label(text=line)
            
            if len(lines) > 10:
                col.label(text=f"... 他 {len(lines) - 10} 行")
        
        # 便利な関数セクション
        box = layout.box()
        box.label(text="便利な関数:")
        
        # 空間関係設定
        col = box.column()
        col.label(text="空間関係設定:")
        
        row = col.row(align=True)
        props = row.operator("unified_mcp.set_spatial_relationship", text="上")
        props.relationship = "above"
        
        props = row.operator("unified_mcp.set_spatial_relationship", text="下")
        props.relationship = "below"
        
        props = row.operator("unified_mcp.set_spatial_relationship", text="左")
        props.relationship = "left"
        
        props = row.operator("unified_mcp.set_spatial_relationship", text="右")
        props.relationship = "right"
        
        row = col.row(align=True)
        props = row.operator("unified_mcp.set_spatial_relationship", text="前")
        props.relationship = "front"
        
        props = row.operator("unified_mcp.set_spatial_relationship", text="後")
        props.relationship = "back"
        
        props = row.operator("unified_mcp.set_spatial_relationship", text="内部")
        props.relationship = "inside"
        
        # スマートオブジェクト生成
        col = box.column()
        col.label(text="オブジェクト生成:")
        
        row = col.row(align=True)
        props = row.operator("unified_mcp.create_smart_object", text="キューブ")
        props.object_type = "cube"
        
        props = row.operator("unified_mcp.create_smart_object", text="球")
        props.object_type = "sphere"
        
        props = row.operator("unified_mcp.create_smart_object", text="円柱")
        props.object_type = "cylinder"
        
        row = col.row(align=True)
        props = row.operator("unified_mcp.create_smart_object", text="平面")
        props.object_type = "plane"
        
        props = row.operator("unified_mcp.create_smart_object", text="テキスト")
        props.object_type = "text"
        
        props = row.operator("unified_mcp.create_smart_object", text="ライト")
        props.object_type = "light"
        
        # ブーリアン操作
        col = box.column()
        col.label(text="ブーリアン操作:")
        
        row = col.row(align=True)
        props = row.operator("unified_mcp.boolean_operation", text="差分")
        props.operation = "DIFFERENCE"
        
        props = row.operator("unified_mcp.boolean_operation", text="結合")
        props.operation = "UNION"
        
        props = row.operator("unified_mcp.boolean_operation", text="交差")
        props.operation = "INTERSECT"

# ------------------------
# 内部操作のためのオペレーター
# ------------------------

# サーバー起動オペレーター
class GRAPHQLMCP_OT_start_server(Operator):
    """GraphQLサーバーを起動"""
    bl_idname = "graphql_mcp.start_server"
    bl_label = "サーバー起動"
    bl_description = "GraphQL APIサーバーを起動"
    
    def execute(self, context):
        from ..core import server
        try:
            server.register()
            context.scene.blendermcp_server_running = True
            self.report({'INFO'}, "Unified MCPサーバーを起動しました")
        except Exception as e:
            self.report({'ERROR'}, f"サーバー起動エラー: {str(e)}")
        return {'FINISHED'}

# サーバー停止オペレーター
class GRAPHQLMCP_OT_stop_server(Operator):
    """サーバーを停止"""
    bl_idname = "graphql_mcp.stop_server"
    bl_label = "サーバー停止"
    bl_description = "GraphQL APIサーバーを停止"
    
    def execute(self, context):
        from ..core import server
        try:
            server.unregister()
            context.scene.blendermcp_server_running = False
            self.report({'INFO'}, "Unified MCPサーバーを停止しました")
        except Exception as e:
            self.report({'ERROR'}, f"サーバー停止エラー: {str(e)}")
        return {'FINISHED'}

# APIドキュメントを開くオペレーター
class GRAPHQLMCP_OT_open_docs(Operator):
    """GraphQLドキュメントを開く"""
    bl_idname = "graphql_mcp.open_docs"
    bl_label = "GraphQLドキュメント"
    bl_description = "GraphQL APIドキュメントをブラウザで開く"
    
    def execute(self, context):
        server = MCPHttpServer.get_instance()
        if not server:
            self.report({'ERROR'}, "サーバーが実行されていません")
            return {'CANCELLED'}
        
        import webbrowser
        url = f"http://{server.host}:{server.http_port}/docs"
        webbrowser.open(url)
        return {'FINISHED'}

# GraphQLパネルを開くオペレーター
class GRAPHQLMCP_OT_open_graphql(Operator):
    """GraphQLパネルを開く"""
    bl_idname = "graphql_mcp.open_graphql"
    bl_label = "GraphQLパネル"
    bl_description = "GraphQLパネルを開く"
    
    def execute(self, context):
        # GraphQLパネルのIDを取得
        panel_id = VIEW3D_PT_unified_mcp_graphql.bl_idname
        
        # パネルを開くためのUI設定を変更
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # パネルを展開
                        try:
                            # パネルを開く
                            space.show_region_ui = True
                            context.preferences.view.show_navigate_ui = True
                        except:
                            pass
        
        self.report({'INFO'}, "GraphQLパネルを開きました")
        return {'FINISHED'}

# コードエディタを開くオペレーター
class GRAPHQLMCP_OT_open_code_editor(Operator):
    """コードエディタを開く"""
    bl_idname = "graphql_mcp.open_code_editor"
    bl_label = "コードエディタ"
    bl_description = "Blenderコードエディタを開く"
    
    def execute(self, context):
        # エディタを持つエリアを探す
        for area in context.screen.areas:
            if area.type == 'TEXT_EDITOR':
                break
        else:
            # テキストエディタが見つからない場合は3Dビューのエリアを分割
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    # エリアの分割はAPIが複雑なため、ユーザーに手動で行うよう指示
                    self.report({'INFO'}, "テキストエディタが見つかりません。エリアを分割して手動でテキストエディタを開いてください。")
                    return {'FINISHED'}
        
        # 新しいテキストファイルを作成
        bpy.ops.text.new()
        new_text = bpy.data.texts[-1]  # 最後に作成されたテキスト
        new_text.name = "unified_mcp_script.py"
        
        # テンプレートコードを挿入
        template = """# Unified MCP Script Template
import bpy

# シーン情報を取得する例
scene = bpy.context.scene
print(f"現在のシーン: {scene.name}")
print(f"オブジェクト数: {len(scene.objects)}")

# アクティブオブジェクトの操作例
active_obj = bpy.context.active_object
if active_obj:
    print(f"アクティブオブジェクト: {active_obj.name}")
    
    # オブジェクトを移動
    active_obj.location.z += 1
    
    # オブジェクトの情報を表示
    print(f"位置: {active_obj.location}")
    print(f"寸法: {active_obj.dimensions}")
else:
    print("アクティブオブジェクトがありません")

# 新しいオブジェクトを作成する例
# bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))

"""
        new_text.write(template)
        
        self.report({'INFO'}, "コードエディタを開きました")
        return {'FINISHED'}

# GraphQLクエリ実行オペレーター
class GRAPHQLMCP_OT_execute_graphql_query(Operator):
    """GraphQLクエリを実行"""
    bl_idname = "graphql_mcp.execute_graphql_query"
    bl_label = "クエリ実行"
    bl_description = "GraphQLクエリを実行して結果を取得"
    
    def execute(self, context):
        if not GRAPHQL_AVAILABLE:
            self.report({'ERROR'}, "GraphQLモジュールが利用できません")
            return {'CANCELLED'}
            
        query_text = context.scene.blendermcp_graphql_query
        if not query_text.strip():
            self.report({'ERROR'}, "クエリが空です")
            return {'CANCELLED'}
            
        try:
            result = query_blender(query_text)
            # 結果をプロパティとして保存
            context.scene.blendermcp_graphql_status = json.dumps(result, indent=2, ensure_ascii=False)
            self.report({'INFO'}, "クエリが正常に実行されました")
        except Exception as e:
            context.scene.blendermcp_graphql_status = f"エラー: {str(e)}"
            self.report({'ERROR'}, f"クエリ実行エラー: {str(e)}")
            
        return {'FINISHED'}

# 空間関係設定オペレーター
class GRAPHQLMCP_OT_set_spatial_relationship(Operator):
    """オブジェクト間の空間関係を設定"""
    bl_idname = "graphql_mcp.set_spatial_relationship"
    bl_label = "空間関係設定"
    bl_description = "選択した2つのオブジェクト間の空間関係を設定"
    
    relationship: StringProperty(
        name="関係",
        description="空間関係のタイプ",
        default="above"
    )
    
    distance: FloatProperty(
        name="距離",
        description="オブジェクト間の距離",
        default=0.0,
        min=0.0,
        soft_max=10.0
    )
    
    maintain_rotation: BoolProperty(
        name="回転を維持",
        description="対象オブジェクトの回転を維持するか",
        default=True
    )
    
    def execute(self, context):
        if not GRAPHQL_AVAILABLE:
            self.report({'ERROR'}, "GraphQLモジュールが利用できません")
            return {'CANCELLED'}
            
        # 選択オブジェクトのチェック
        if len(context.selected_objects) < 2:
            self.report({'ERROR'}, "2つ以上のオブジェクトを選択してください")
            return {'CANCELLED'}
            
        # 対象と参照オブジェクトを取得
        if context.active_object and context.active_object in context.selected_objects:
            reference = context.active_object
            targets = [obj for obj in context.selected_objects if obj != reference]
        else:
            reference = context.selected_objects[0]
            targets = context.selected_objects[1:]
        
        # 各ターゲットに対して関係を設定
        success_count = 0
        for target in targets:
            try:
                # 距離パラメータがデフォルト値の場合はNoneを渡す
                distance = None if self.distance == 0.0 else self.distance
                
                # 関係を設定
                result = set_spatial_relationship(
                    target_object=target.name,
                    reference_object=reference.name,
                    relationship=self.relationship,
                    distance=distance,
                    maintain_rotation=self.maintain_rotation
                )
                
                # ステータスを更新
                if result.get("status") == "success":
                    success_count += 1
                else:
                    self.report({'WARNING'}, f"{target.name}: {result.get('message', '不明なエラー')}")
                    
            except Exception as e:
                self.report({'ERROR'}, f"{target.name}: 設定エラー - {str(e)}")
        
        if success_count > 0:
            relation_names = {
                "above": "上",
                "below": "下",
                "left": "左",
                "right": "右",
                "front": "前",
                "back": "後ろ",
                "inside": "内部",
                "around": "周囲"
            }
            relation_jp = relation_names.get(self.relationship, self.relationship)
            
            if success_count == 1:
                self.report({'INFO'}, f"{targets[0].name}を{reference.name}の{relation_jp}に配置しました")
            else:
                self.report({'INFO'}, f"{success_count}個のオブジェクトを{reference.name}の{relation_jp}に配置しました")
                
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "distance")
        layout.prop(self, "maintain_rotation")

# スマートオブジェクト作成オペレーター
class GRAPHQLMCP_OT_create_smart_object(Operator):
    """スマートなオブジェクトを作成"""
    bl_idname = "graphql_mcp.create_smart_object"
    bl_label = "スマートオブジェクト作成"
    bl_description = "高度なパラメータを設定してオブジェクトを作成"
    
    object_type: StringProperty(
        name="タイプ",
        description="作成するオブジェクトのタイプ",
        default="cube"
    )
    
    size: FloatProperty(
        name="サイズ",
        description="オブジェクトのサイズ",
        default=1.0,
        min=0.01,
        soft_max=10.0
    )
    
    name: StringProperty(
        name="名前",
        description="オブジェクトの名前（空の場合は自動生成）",
        default=""
    )
    
    def execute(self, context):
        if not GRAPHQL_AVAILABLE:
            self.report({'ERROR'}, "GraphQLモジュールが利用できません")
            return {'CANCELLED'}
            
        try:
            # カーソル位置を取得
            location = context.scene.cursor.location
            
            # オプションパラメータ
            properties = {}
            
            # オブジェクトタイプごとの特殊設定
            if self.object_type == "sphere":
                properties["segments"] = 32
                properties["rings"] = 16
            elif self.object_type == "cylinder":
                properties["vertices"] = 32
            elif self.object_type == "text":
                properties["body"] = "Blender MCP"
                properties["extrude"] = 0.1
            elif self.object_type == "light":
                properties["light_type"] = "POINT"
                properties["energy"] = 1000.0
            
            # オブジェクトを作成
            result = create_smart_object(
                object_type=self.object_type,
                name=self.name if self.name else None,
                location={
                    'x': location.x,
                    'y': location.y,
                    'z': location.z
                },
                size=self.size,
                properties=properties
            )
            
            # ステータスを更新
            if result.get("status") == "success":
                obj_name = result.get("data", {}).get("name", "未知のオブジェクト")
                self.report({'INFO'}, f"{obj_name}を作成しました")
            else:
                self.report({'ERROR'}, result.get("message", "不明なエラー"))
                
        except Exception as e:
            self.report({'ERROR'}, f"オブジェクト作成エラー: {str(e)}")
            
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "name")
        layout.prop(self, "size")

# ブーリアン操作オペレーター
class GRAPHQLMCP_OT_boolean_operation(Operator):
    """強化されたブーリアン操作"""
    bl_idname = "graphql_mcp.boolean_operation"
    bl_label = "ブーリアン操作"
    bl_description = "選択した2つのオブジェクト間でブーリアン操作を実行"
    
    operation: StringProperty(
        name="操作",
        description="ブーリアン操作のタイプ",
        default="DIFFERENCE"
    )
    
    solver: EnumProperty(
        name="ソルバー",
        description="ブーリアン演算で使用するソルバー",
        items=[
            ('EXACT', '正確', '精密な結果を生成するが遅い'),
            ('FAST', '高速', '速いが精度が落ちる場合がある')
        ],
        default='EXACT'
    )
    
    auto_repair: BoolProperty(
        name="自動修復",
        description="エラー時に自動修復を試みる",
        default=True
    )
    
    def execute(self, context):
        if not GRAPHQL_AVAILABLE:
            self.report({'ERROR'}, "GraphQLモジュールが利用できません")
            return {'CANCELLED'}
            
        # 選択オブジェクトのチェック
        if len(context.selected_objects) != 2:
            self.report({'ERROR'}, "ちょうど2つのオブジェクトを選択してください")
            return {'CANCELLED'}
            
        # 対象とツールオブジェクトを取得
        target = context.active_object
        
        if target not in context.selected_objects:
            self.report({'ERROR'}, "アクティブオブジェクトが選択されていません")
            return {'CANCELLED'}
            
        tool = [obj for obj in context.selected_objects if obj != target][0]
        
        try:
            # ブーリアン操作を実行
            result = enhanced_boolean_operation(
                target_object=target.name,
                tool_object=tool.name,
                operation=self.operation,
                solver=self.solver,
                auto_repair=self.auto_repair
            )
            
            # ステータスを更新
            if result.get("status") == "success":
                operation_names = {
                    "DIFFERENCE": "差分",
                    "UNION": "結合",
                    "INTERSECT": "交差"
                }
                op_name = operation_names.get(self.operation, self.operation)
                self.report({'INFO'}, f"{target.name}と{tool.name}の間で{op_name}ブーリアン操作を実行しました")
            else:
                self.report({'ERROR'}, result.get("message", "不明なエラー"))
                
        except Exception as e:
            self.report({'ERROR'}, f"ブーリアン操作エラー: {str(e)}")
            
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "solver")
        layout.prop(self, "auto_repair")

# ヘルプパネル
class VIEW3D_PT_blender_graphql_mcp_help(Panel):
    """Blender GraphQL MCPのヘルプパネル"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MCP"
    bl_label = "ヘルプ"
    bl_idname = "VIEW3D_PT_blender_graphql_mcp_help"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        layout.label(text="使用方法:")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="1. サーバーを開始")
        col.label(text="2. LLM/AIと接続")
        col.label(text="3. コマンドを実行")
        
        layout.separator()
        
        layout.label(text="利用可能なAPIエンドポイント:")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="- WebSocket: ws://localhost:9876")
        col.label(text="- HTTP API: http://localhost:8000")
        col.label(text="- GraphQL: /graphql エンドポイント")
        
        layout.separator()
        
        layout.label(text="サポート:")
        row = layout.row()
        row.operator("wm.url_open", text="ドキュメント").url = "https://github.com/user/unified-mcp/wiki"
        row = layout.row()
        row.operator("wm.url_open", text="問題を報告").url = "https://github.com/user/unified-mcp/issues"

# パネル登録関数
classes = [
    VIEW3D_PT_blender_graphql_mcp_main,
    VIEW3D_PT_blender_graphql_mcp_graphql,
    VIEW3D_PT_blender_graphql_mcp_help,
    GRAPHQLMCP_OT_start_server,
    GRAPHQLMCP_OT_stop_server,
    GRAPHQLMCP_OT_open_docs,
    GRAPHQLMCP_OT_open_graphql,
    GRAPHQLMCP_OT_open_code_editor,
    GRAPHQLMCP_OT_execute_graphql_query,
    GRAPHQLMCP_OT_set_spatial_relationship,
    GRAPHQLMCP_OT_create_smart_object,
    GRAPHQLMCP_OT_boolean_operation
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    print("Unified MCP: UI classes registered")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("Unified MCP: UI classes unregistered")
