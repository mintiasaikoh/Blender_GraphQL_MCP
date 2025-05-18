"""
Unified MCP UI コンポーネントシステム
プラグインからのUI拡張をサポート
"""

import bpy
import logging
import importlib
import traceback
from typing import Dict, List, Any, Optional, Callable, Type, Tuple

# ロガー設定
logger = logging.getLogger('unified_mcp.ui.components')

# 登録されたコンポーネント
ui_components = []

# 生成されたクラス
generated_classes = []


class DynamicPanelFactory:
    """動的パネル生成ファクトリ"""
    
    @staticmethod
    def create_panel(component: Dict[str, Any]) -> Type[bpy.types.Panel]:
        """
        プラグイン設定からパネルクラスを動的生成
        
        Args:
            component: パネル定義辞書
            
        Returns:
            生成されたパネルクラス
        """
        if not all(key in component for key in ['label', 'space_type', 'region_type']):
            logger.error(f"パネル定義に必須フィールドがありません: {component.get('name', 'Unknown')}")
            return None
        
        # クラス属性を設定
        attrs = {
            "bl_label": component.get("label", "Custom Panel"),
            "bl_idname": f"VIEW3D_PT_{component.get('name', 'CustomPanel')}",
            "bl_space_type": component.get("space_type", "VIEW_3D"),
            "bl_region_type": component.get("region_type", "UI"),
            "bl_category": component.get("category", "Tool"),
            "bl_options": component.get("options", {'DEFAULT_CLOSED'}),
            "_component_def": component,  # 元の定義を保存
        }
        
        # draw関数を作成
        def draw(self, context):
            layout = self.layout
            items = self._component_def.get("items", [])
            
            for item in items:
                item_type = item.get("type", "")
                
                if item_type == "operator":
                    # オペレータボタン
                    op_name = item.get("operator", "")
                    if not op_name:
                        continue
                        
                    props = item.get("properties", {})
                    text = item.get("text", "")
                    icon = item.get("icon", "NONE")
                    
                    if text:
                        op = layout.operator(op_name, text=text, icon=icon)
                    else:
                        op = layout.operator(op_name, icon=icon)
                    
                    # オペレータのプロパティを設定
                    for prop_name, prop_value in props.items():
                        if hasattr(op, prop_name):
                            setattr(op, prop_name, prop_value)
                
                elif item_type == "label":
                    # ラベル
                    text = item.get("text", "")
                    icon = item.get("icon", "NONE")
                    layout.label(text=text, icon=icon)
                
                elif item_type == "separator":
                    # 区切り線
                    layout.separator()
                
                elif item_type == "prop":
                    # プロパティ
                    data_path = item.get("data_path", "")
                    prop_name = item.get("property", "")
                    text = item.get("text", "")
                    icon = item.get("icon", "NONE")
                    
                    if data_path and prop_name:
                        try:
                            data = eval(f"context.{data_path}")
                            if text:
                                layout.prop(data, prop_name, text=text, icon=icon)
                            else:
                                layout.prop(data, prop_name, icon=icon)
                        except Exception as e:
                            logger.error(f"プロパティアクセスエラー: {e}")
                
                elif item_type == "box":
                    # ボックス
                    box = layout.box()
                    box_items = item.get("items", [])
                    
                    for box_item in box_items:
                        # 再帰的にアイテムを処理（シンプルにするため一部のみ対応）
                        if box_item.get("type") == "label":
                            box.label(text=box_item.get("text", ""), icon=box_item.get("icon", "NONE"))
                        elif box_item.get("type") == "operator":
                            op_name = box_item.get("operator", "")
                            if op_name:
                                box.operator(op_name, text=box_item.get("text", ""), icon=box_item.get("icon", "NONE"))
                        elif box_item.get("type") == "separator":
                            box.separator()
        
        # カスタムドロー関数がある場合は実行
        custom_draw = component.get("draw_callback")
        if custom_draw and callable(custom_draw):
            try:
                custom_draw(self, context, layout)
            except Exception as e:
                logger.error(f"カスタムドロー関数でエラー: {e}")
                logger.debug(traceback.format_exc())
    
    # draw関数を属性に設定
    attrs["draw"] = draw
    
    # 動的クラス作成
    panel_name = f"DYNAMIC_PT_{component.get('name', 'Custom')}_{len(generated_classes)}"
    panel_class = type(panel_name, (bpy.types.Panel,), attrs)
    
    return panel_class


class PluginOperator(bpy.types.Operator):
    """プラグインコマンドを実行するオペレータ"""
    bl_idname = "unified_mcp.execute_plugin_command"
    bl_label = "プラグインコマンドを実行"
    bl_description = "プラグインで定義されたコマンドを実行します"
    bl_options = {'REGISTER', 'UNDO'}
    
    command_name: bpy.props.StringProperty(
        name="コマンド名",
        description="実行するコマンドの名前",
        default=""
    )
    
    command_params: bpy.props.StringProperty(
        name="パラメータ",
        description="コマンドのパラメータ（JSON形式）",
        default="{}"
    )
    
    def execute(self, context):
        import json
        from ...core.commands.base import execute_command
        
        try:
            # パラメータをJSONからデコード
            params = json.loads(self.command_params)
            
            # コマンドを実行
            command_data = {
                "command": self.command_name,
                "params": params
            }
            
            result = execute_command(command_data)
            
            if result.get("success", False):
                self.report({'INFO'}, f"コマンド実行成功: {self.command_name}")
                return {'FINISHED'}
            else:
                errors = result.get("errors", ["不明なエラー"])
                self.report({'ERROR'}, f"コマンドエラー: {', '.join(errors)}")
                return {'CANCELLED'}
                
        except json.JSONDecodeError as e:
            self.report({'ERROR'}, f"JSONパース失敗: {e}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"コマンド実行エラー: {e}")
            logger.error(f"プラグインコマンド実行エラー: {e}")
            logger.debug(traceback.format_exc())
            return {'CANCELLED'}

# オペレータなどの基本コンポーネント
base_components = [
    PluginOperator
]

def register_ui_components(components: List[Dict[str, Any]]):
    """
    プラグインUIコンポーネントを登録
    
    Args:
        components: UIコンポーネント定義のリスト
    """
    global ui_components, generated_classes
    
    for component in components:
        component_type = component.get("type", "")
        component_name = component.get("name", f"Component_{len(ui_components)}")
        
        # 既存のコンポーネントを確認
        existing_idx = next((i for i, c in enumerate(ui_components) 
                            if c.get("name") == component_name), None)
        
        if existing_idx is not None:
            # 既存のコンポーネントを更新
            ui_components[existing_idx] = component
            logger.info(f"UIコンポーネント '{component_name}' を更新しました")
        else:
            # 新しいコンポーネントを追加
            ui_components.append(component)
            logger.info(f"UIコンポーネント '{component_name}' を登録しました")
        
        # コンポーネントタイプに応じた処理
        if component_type == "panel":
            # パネルを動的生成して登録
            panel_class = DynamicPanelFactory.create_panel(component)
            if panel_class:
                try:
                    # 既存のクラスを登録解除
                    for cls in generated_classes[:]:
                        if hasattr(cls, "_component_def") and cls._component_def.get("name") == component_name:
                            if hasattr(bpy.utils, "unregister_class"):
                                try:
                                    bpy.utils.unregister_class(cls)
                                    generated_classes.remove(cls)
                                except:
                                    pass
                    
                    # 新しいクラスを登録
                    bpy.utils.register_class(panel_class)
                    generated_classes.append(panel_class)
                    logger.info(f"動的パネル '{panel_class.__name__}' を登録しました")
                except Exception as e:
                    logger.error(f"パネル登録エラー: {e}")
                    logger.debug(traceback.format_exc())


def unregister_ui_components(components: List[Dict[str, Any]]):
    """
    プラグインUIコンポーネントを登録解除
    
    Args:
        components: UIコンポーネント定義のリスト
    """
    global ui_components, generated_classes
    
    for component in components:
        component_name = component.get("name", "")
        if not component_name:
            continue
            
        # コンポーネントを削除
        ui_components = [c for c in ui_components if c.get("name") != component_name]
        
        # 生成されたクラスを登録解除
        for cls in generated_classes[:]:
            if hasattr(cls, "_component_def") and cls._component_def.get("name") == component_name:
                try:
                    bpy.utils.unregister_class(cls)
                    generated_classes.remove(cls)
                    logger.info(f"動的UIコンポーネント '{cls.__name__}' を登録解除しました")
                except Exception as e:
                    logger.error(f"UIコンポーネント登録解除エラー: {e}")


def register():
    """モジュールを登録"""
    logger.info("UIコンポーネントシステムを登録しています...")
    
    # 基本コンポーネントを登録
    for cls in base_components:
        try:
            bpy.utils.register_class(cls)
            logger.info(f"基本UIコンポーネント '{cls.__name__}' を登録しました")
        except Exception as e:
            logger.error(f"基本UIコンポーネント登録エラー: {e}")
    
    # すでに登録されているコンポーネントを登録
    if ui_components:
        register_ui_components(ui_components)
    
    logger.info("UIコンポーネントシステムの登録が完了しました")


def unregister():
    """モジュールを登録解除"""
    global generated_classes
    
    logger.info("UIコンポーネントシステムを登録解除しています...")
    
    # 動的生成したクラスを登録解除
    for cls in generated_classes[:]:
        try:
            bpy.utils.unregister_class(cls)
            logger.info(f"動的UIコンポーネント '{cls.__name__}' を登録解除しました")
        except Exception as e:
            logger.error(f"動的UIコンポーネント登録解除エラー: {e}")
    
    # 基本コンポーネントを登録解除
    for cls in reversed(base_components):
        try:
            bpy.utils.unregister_class(cls)
            logger.info(f"基本UIコンポーネント '{cls.__name__}' を登録解除しました")
        except Exception as e:
            logger.error(f"基本UIコンポーネント登録解除エラー: {e}")
    
    # リストをクリア
    generated_classes = []
    
    logger.info("UIコンポーネントシステムの登録解除が完了しました")