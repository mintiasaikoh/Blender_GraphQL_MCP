"""
Blender Context Manager
Blenderの現在の状態を取得・管理するモジュール
"""

import bpy
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# モジュールレベルのロガー
logger = logging.getLogger('blender_mcp.core.context')

class BlenderContextManager:
    """Blenderの状態を管理するクラス"""
    
    def __init__(self):
        self.last_context = None
        self.context_history = []
        
    def get_scene_context(self) -> Dict[str, Any]:
        """現在のシーンコンテキストを取得"""
        try:
            scene = bpy.context.scene
            return {
                "name": scene.name,
                "frame_current": scene.frame_current,
                "frame_start": scene.frame_start, 
                "frame_end": scene.frame_end,
                "render_engine": scene.render.engine,
                "use_nodes": scene.use_nodes,
                "object_count": len(scene.objects),
                "active_collection": scene.collection.name,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"シーンコンテキスト取得エラー: {e}")
            return {}
    
    def get_selected_objects(self) -> List[Dict[str, Any]]:
        """選択中のオブジェクト情報を取得"""
        selected = []
        try:
            for obj in bpy.context.selected_objects:
                obj_info = {
                    "id": obj.name,
                    "type": obj.type,
                    "location": list(obj.location),
                    "rotation": list(obj.rotation_euler),
                    "scale": list(obj.scale),
                    "visible": obj.visible_get(),
                    "parent": obj.parent.name if obj.parent else None,
                    "children": [child.name for child in obj.children],
                    "modifiers": [mod.name for mod in obj.modifiers],
                    "data": self._get_object_data(obj)
                }
                
                # メッシュ特有の情報
                if obj.type == 'MESH' and obj.data:
                    obj_info["mesh"] = {
                        "vertices": len(obj.data.vertices),
                        "edges": len(obj.data.edges),
                        "faces": len(obj.data.polygons),
                        "materials": [mat.name for mat in obj.data.materials] if obj.data.materials else []
                    }
                
                selected.append(obj_info)
                
        except Exception as e:
            logger.error(f"選択オブジェクト取得エラー: {e}")
            
        return selected
    
    def get_active_object(self) -> Optional[Dict[str, Any]]:
        """アクティブオブジェクトの詳細情報を取得"""
        try:
            obj = bpy.context.active_object
            if not obj:
                return None
                
            return {
                "id": obj.name,
                "type": obj.type,
                "mode": bpy.context.mode,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "scale": list(obj.scale),
                "matrix_world": [list(row) for row in obj.matrix_world],
                "bounding_box": {
                    "min": list(obj.bound_box[0]),
                    "max": list(obj.bound_box[6])
                } if obj.bound_box else None,
                "data": self._get_object_data(obj)
            }
        except Exception as e:
            logger.error(f"アクティブオブジェクト取得エラー: {e}")
            return None
    
    def get_viewport_context(self) -> Dict[str, Any]:
        """ビューポートの状態を取得"""
        try:
            if not bpy.context.space_data:
                return {}
                
            space = bpy.context.space_data
            region_3d = None
            
            # 3Dビューの情報を取得
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            region_3d = space.region_3d
                            break
                    if region_3d:
                        break
                        
            if not region_3d:
                return {}
                
            return {
                "view_perspective": region_3d.view_perspective,
                "view_location": list(region_3d.view_location),
                "view_rotation": list(region_3d.view_rotation),
                "view_distance": region_3d.view_distance,
                "is_perspective": region_3d.is_perspective,
                "shading_type": space.shading.type if hasattr(space, 'shading') else None,
                "overlay_enabled": space.overlay.show_overlays if hasattr(space, 'overlay') else None
            }
        except Exception as e:
            logger.error(f"ビューポートコンテキスト取得エラー: {e}")
            return {}
    
    def get_complete_context(self) -> Dict[str, Any]:
        """完全なコンテキスト情報を取得"""
        context = {
            "scene": self.get_scene_context(),
            "selected_objects": self.get_selected_objects(),
            "active_object": self.get_active_object(),
            "viewport": self.get_viewport_context(),
            "mode": bpy.context.mode,
            "tool": bpy.context.workspace.tools.active.idname if bpy.context.workspace.tools.active else None,
            "preferences": {
                "units": bpy.context.scene.unit_settings.system,
                "scale_length": bpy.context.scene.unit_settings.scale_length
            },
            "available_operations": self._get_available_operations()
        }
        
        # 履歴に保存
        self.last_context = context
        self.context_history.append({
            "timestamp": datetime.now().isoformat(),
            "context": context
        })
        
        # 履歴は最新100件に制限
        if len(self.context_history) > 100:
            self.context_history = self.context_history[-100:]
            
        return context
    
    def _get_object_data(self, obj) -> Dict[str, Any]:
        """オブジェクトの詳細データを取得"""
        data = {}
        try:
            if obj.data:
                data["name"] = obj.data.name
                data["users"] = obj.data.users
                
                # タイプ別の追加情報
                if obj.type == 'MESH':
                    data["use_auto_smooth"] = obj.data.use_auto_smooth
                    data["auto_smooth_angle"] = obj.data.auto_smooth_angle
                elif obj.type == 'CAMERA':
                    data["lens"] = obj.data.lens
                    data["type"] = obj.data.type
                elif obj.type == 'LIGHT':
                    data["energy"] = obj.data.energy
                    data["color"] = list(obj.data.color)
                    data["type"] = obj.data.type
        except Exception as e:
            logger.error(f"オブジェクトデータ取得エラー: {e}")
            
        return data
    
    def _get_available_operations(self) -> List[str]:
        """現在のコンテキストで利用可能な操作を返す"""
        operations = []
        
        try:
            mode = bpy.context.mode
            if mode == 'OBJECT':
                operations.extend([
                    "create_primitive",
                    "duplicate",
                    "delete",
                    "transform",
                    "apply_modifier",
                    "parent_set",
                    "join"
                ])
            elif mode == 'EDIT':
                operations.extend([
                    "extrude",
                    "subdivide",
                    "delete",
                    "merge",
                    "separate",
                    "split"
                ])
            elif mode == 'SCULPT':
                operations.extend([
                    "sculpt_stroke",
                    "remesh",
                    "mask"
                ])
                
            # 共通操作
            operations.extend([
                "select",
                "hide",
                "show",
                "add_material",
                "mode_set"
            ])
            
        except Exception as e:
            logger.error(f"利用可能操作の取得エラー: {e}")
            
        return operations
    
    def get_context_diff(self, old_context: Dict, new_context: Dict) -> Dict[str, Any]:
        """2つのコンテキストの差分を計算"""
        diff = {
            "changes": [],
            "new_objects": [],
            "deleted_objects": [],
            "modified_objects": []
        }
        
        try:
            # オブジェクトの変更を検出
            old_objects = {obj["id"]: obj for obj in old_context.get("selected_objects", [])}
            new_objects = {obj["id"]: obj for obj in new_context.get("selected_objects", [])}
            
            # 新規オブジェクト
            for obj_id in new_objects:
                if obj_id not in old_objects:
                    diff["new_objects"].append(obj_id)
            
            # 削除されたオブジェクト
            for obj_id in old_objects:
                if obj_id not in new_objects:
                    diff["deleted_objects"].append(obj_id)
            
            # 変更されたオブジェクト
            for obj_id in new_objects:
                if obj_id in old_objects:
                    if new_objects[obj_id] != old_objects[obj_id]:
                        diff["modified_objects"].append(obj_id)
                        
        except Exception as e:
            logger.error(f"コンテキスト差分計算エラー: {e}")
            
        return diff
    
    def suggest_next_actions(self) -> List[Dict[str, str]]:
        """現在のコンテキストから次のアクションを提案"""
        suggestions = []
        
        try:
            context = self.get_complete_context()
            mode = context.get("mode", "")
            selected = context.get("selected_objects", [])
            active = context.get("active_object")
            
            if mode == "OBJECT":
                if not selected:
                    suggestions.append({
                        "action": "create_object",
                        "description": "新しいオブジェクトを作成"
                    })
                else:
                    suggestions.append({
                        "action": "transform",
                        "description": "選択オブジェクトを移動/回転/スケール"
                    })
                    if len(selected) > 1:
                        suggestions.append({
                            "action": "join",
                            "description": "選択オブジェクトを結合"
                        })
                        
            elif mode == "EDIT":
                suggestions.append({
                    "action": "extrude",
                    "description": "選択した面を押し出し"
                })
                suggestions.append({
                    "action": "subdivide",
                    "description": "メッシュを細分化"
                })
                
        except Exception as e:
            logger.error(f"アクション提案エラー: {e}")
            
        return suggestions

# グローバルインスタンス
_context_manager = None

def get_context_manager() -> BlenderContextManager:
    """コンテキストマネージャーのシングルトンインスタンスを取得"""
    global _context_manager
    if _context_manager is None:
        _context_manager = BlenderContextManager()
    return _context_manager