"""
スクリプト実行演算子モジュール
BlenderのメインスレッドでPythonスクリプトを安全に実行する
"""

import bpy
import os
import logging
import traceback
from bpy.props import StringProperty

# ロガー設定
logger = logging.getLogger('unified_mcp.executor')

class MCP_OT_ExecuteScript(bpy.types.Operator):
    """スクリプトを安全に実行するオペレータ"""
    bl_idname = "mcp.execute_script"
    bl_label = "Execute Script"
    
    script_path: StringProperty(
        name="Script Path",
        description="実行するスクリプトファイルのパス",
        default="",
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        if not self.script_path or not os.path.exists(self.script_path):
            self.report({'ERROR'}, f"ファイルが見つかりません: {self.script_path}")
            return {'CANCELLED'}
        
        try:
            # スクリプトファイルを実行
            logger.info(f"スクリプトを実行: {self.script_path}")
            
            # バックアップオブジェクト名を記録
            before_objects = set(bpy.data.objects.keys())
            
            # スクリプトを実行
            with open(self.script_path, 'r') as f:
                script_code = f.read()
            
            # スクリプトのコンテキストを設定
            namespace = {"__file__": self.script_path}
            exec(script_code, namespace)
            
            # 新しく作成されたオブジェクトを特定
            after_objects = set(bpy.data.objects.keys())
            new_objects = after_objects - before_objects
            
            # 結果を報告
            self.report({'INFO'}, f"スクリプト実行成功: {len(new_objects)}個のオブジェクトが作成されました")
            
            return {'FINISHED'}
        
        except Exception as e:
            error_message = str(e)
            tb_str = traceback.format_exc()
            logger.error(f"スクリプト実行エラー: {error_message}")
            logger.debug(tb_str)
            self.report({'ERROR'}, f"スクリプト実行エラー: {error_message}")
            return {'CANCELLED'}


class MCP_OT_CreateFlowerpot(bpy.types.Operator):
    """植木鉢を作成するオペレータ"""
    bl_idname = "mcp.create_flowerpot"
    bl_label = "Create Flowerpot"
    
    def execute(self, context):
        try:
            # シーン内のメッシュオブジェクトをクリア（カメラとライト以外）
            for obj in list(bpy.data.objects):
                if obj.type not in ["CAMERA", "LIGHT"]:
                    bpy.data.objects.remove(obj)

            # 植木鉢の作成（円柱からスタート）
            bpy.ops.mesh.primitive_cylinder_add(
                radius=1.0, 
                depth=1.5, 
                vertices=32, 
                location=(0, 0, 0.75)
            )
            pot_base = context.active_object
            pot_base.name = "FlowerPot_Base"
            
            # マテリアルを作成（テラコッタ風の赤茶色）
            pot_material = bpy.data.materials.new(name="PotMaterial")
            pot_material.diffuse_color = (0.8, 0.4, 0.3, 1.0)
            pot_base.data.materials.append(pot_material)
            
            # 内側を削る（植木鉢の内部空間）
            bpy.ops.mesh.primitive_cylinder_add(
                radius=0.85,
                depth=1.4,
                vertices=32,
                location=(0, 0, 0.85)
            )
            pot_inner = context.active_object
            pot_inner.name = "FlowerPot_Inner"
            
            # ブーリアン演算で内側を削る
            bool_mod = pot_base.modifiers.new(name="Boolean", type='BOOLEAN')
            bool_mod.operation = 'DIFFERENCE'
            bool_mod.object = pot_inner
            
            # モディファイアを適用
            bpy.ops.object.select_all(action='DESELECT')
            pot_base.select_set(True)
            context.view_layer.objects.active = pot_base
            bpy.ops.object.modifier_apply(modifier="Boolean")
            
            # 不要なインナーオブジェクトを削除
            bpy.data.objects.remove(pot_inner)
            
            # 植木鉢の縁の装飾を追加（トーラス）
            bpy.ops.mesh.primitive_torus_add(
                major_radius=1.0,
                minor_radius=0.1,
                major_segments=32,
                minor_segments=12,
                location=(0, 0, 1.5)
            )
            pot_rim = context.active_object
            pot_rim.name = "FlowerPot_Rim"
            
            # 縁に同じマテリアルを適用
            pot_rim.data.materials.append(pot_material)
            
            # 植木鉢の中の土を作成
            bpy.ops.mesh.primitive_cylinder_add(
                radius=0.8,
                depth=0.2,
                vertices=32,
                location=(0, 0, 1.35)
            )
            soil = context.active_object
            soil.name = "Soil"
            
            # 土のマテリアルを作成（茶色）
            soil_material = bpy.data.materials.new(name="SoilMaterial")
            soil_material.diffuse_color = (0.3, 0.2, 0.1, 1.0)
            soil.data.materials.append(soil_material)
            
            # カメラを植木鉢に向ける
            camera = bpy.data.objects.get("Camera")
            if camera:
                camera.location = (3, -3, 3)
                # カメラを植木鉢に向ける（既存のコンストレイントをクリア）
                for c in camera.constraints:
                    camera.constraints.remove(c)
                
                constraint = camera.constraints.new('TRACK_TO')
                constraint.target = pot_base
                constraint.track_axis = 'TRACK_NEGATIVE_Z'
                constraint.up_axis = 'UP_Y'
            
            self.report({'INFO'}, "植木鉢の作成が完了しました！")
            return {'FINISHED'}
            
        except Exception as e:
            error_message = str(e)
            self.report({'ERROR'}, f"植木鉢作成エラー: {error_message}")
            logger.error(f"植木鉢作成エラー: {error_message}")
            logger.debug(traceback.format_exc())
            return {'CANCELLED'}


# オペレータクラスのリスト
classes = (
    MCP_OT_ExecuteScript,
    MCP_OT_CreateFlowerpot,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
