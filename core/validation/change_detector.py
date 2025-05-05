"""
変更検出モジュール
Blenderの操作前後の状態を比較し、変更を検出するためのモジュール
"""

import bpy
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime

class ChangeDetector:
    """
    Blenderのシーン状態の変更を検出・記録するクラス
    """
    
    @classmethod
    def capture_state(cls, detail_level: str = "standard") -> Dict[str, Any]:
        """
        現在のシーン状態をキャプチャ
        
        Args:
            detail_level: 詳細レベル ("basic", "standard", "detailed")
            
        Returns:
            現在の状態情報
        """
        state = {
            "timestamp": datetime.now().isoformat(),
            "objects": cls._capture_objects(detail_level),
            "scene": cls._capture_scene_info(),
            "selection": cls._capture_selection()
        }
        
        if detail_level != "basic":
            state["collections"] = cls._capture_collections()
        
        return state
    
    @classmethod
    def compare_states(cls, before_state: Dict[str, Any], after_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        2つの状態を比較し、変更点を検出
        
        Args:
            before_state: 操作前の状態
            after_state: 操作後の状態
            
        Returns:
            変更点の情報
        """
        changes = {
            "timestamp": datetime.now().isoformat(),
            "has_changes": False,
            "object_changes": cls._compare_objects(
                before_state.get("objects", {}), 
                after_state.get("objects", {})
            ),
            "scene_changes": cls._compare_scene(
                before_state.get("scene", {}), 
                after_state.get("scene", {})
            ),
            "selection_changes": cls._compare_selection(
                before_state.get("selection", {}), 
                after_state.get("selection", {})
            )
        }
        
        # コレクション変更（存在する場合）
        if "collections" in before_state and "collections" in after_state:
            changes["collection_changes"] = cls._compare_collections(
                before_state["collections"], 
                after_state["collections"]
            )
        
        # 変更がある場合フラグを設定
        changes["has_changes"] = (
            changes["object_changes"]["has_changes"] or
            changes["scene_changes"]["has_changes"] or
            changes["selection_changes"]["has_changes"] or
            changes.get("collection_changes", {}).get("has_changes", False)
        )
        
        return changes
    
    @classmethod
    def _capture_objects(cls, detail_level: str) -> Dict[str, Dict[str, Any]]:
        """オブジェクト情報をキャプチャ"""
        objects = {}
        
        for obj in bpy.data.objects:
            # 基本情報（すべてのレベルで含まれる）
            obj_info = {
                "name": obj.name,
                "type": obj.type,
                "location": [round(v, 4) for v in obj.location],
                "rotation": [round(v, 4) for v in obj.rotation_euler],
                "scale": [round(v, 4) for v in obj.scale],
                "hide": obj.hide_get(),
                "selected": obj.select_get()
            }
            
            # 標準以上のレベルで追加情報
            if detail_level != "basic" and obj.type == 'MESH' and obj.data:
                obj_info.update({
                    "vertex_count": len(obj.data.vertices),
                    "edge_count": len(obj.data.edges),
                    "face_count": len(obj.data.polygons),
                    "material_count": len(obj.material_slots)
                })
            
            objects[obj.name] = obj_info
            
        return objects
    
    @classmethod
    def _capture_scene_info(cls) -> Dict[str, Any]:
        """シーン情報をキャプチャ"""
        scene = bpy.context.scene
        return {
            "name": scene.name,
            "frame_current": scene.frame_current,
            "render_engine": scene.render.engine,
            "camera": scene.camera.name if scene.camera else None
        }
    
    @classmethod
    def _capture_selection(cls) -> Dict[str, Any]:
        """選択状態をキャプチャ"""
        return {
            "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
            "selected_objects": [obj.name for obj in bpy.context.selected_objects],
            "selected_count": len(bpy.context.selected_objects),
            "mode": bpy.context.mode
        }
    
    @classmethod
    def _capture_collections(cls) -> Dict[str, Dict[str, Any]]:
        """コレクション情報をキャプチャ"""
        collections = {}
        
        for coll in bpy.data.collections:
            collections[coll.name] = {
                "objects": [obj.name for obj in coll.objects],
                "objects_count": len(coll.objects),
                "hide": coll.hide_viewport
            }
            
        return collections
    
    @classmethod
    def _compare_objects(cls, before: Dict[str, Dict[str, Any]], after: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """オブジェクト情報を比較"""
        result = {
            "has_changes": False,
            "added": [],
            "removed": [],
            "modified": []
        }
        
        # 存在チェック
        before_names = set(before.keys())
        after_names = set(after.keys())
        
        # 追加されたオブジェクト
        added = after_names - before_names
        if added:
            result["added"] = list(added)
            result["has_changes"] = True
        
        # 削除されたオブジェクト
        removed = before_names - after_names
        if removed:
            result["removed"] = list(removed)
            result["has_changes"] = True
        
        # 変更されたオブジェクト
        modified = []
        modified_details = {}
        
        for name in before_names & after_names:
            obj_before = before[name]
            obj_after = after[name]
            
            # 基本フィールドの比較
            changes = {}
            
            for field in ["location", "rotation", "scale", "hide", "selected"]:
                if field in obj_before and field in obj_after and obj_before[field] != obj_after[field]:
                    changes[field] = {
                        "before": obj_before[field],
                        "after": obj_after[field]
                    }
            
            # メッシュ特有のフィールド
            for field in ["vertex_count", "edge_count", "face_count"]:
                if field in obj_before and field in obj_after and obj_before[field] != obj_after[field]:
                    changes[field] = {
                        "before": obj_before[field],
                        "after": obj_after[field]
                    }
            
            if changes:
                modified.append(name)
                modified_details[name] = changes
        
        if modified:
            result["modified"] = modified
            result["modified_details"] = modified_details
            result["has_changes"] = True
        
        return result
    
    @classmethod
    def _compare_scene(cls, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """シーン情報を比較"""
        result = {
            "has_changes": False,
            "changes": {}
        }
        
        # フィールドの比較
        for field in ["name", "frame_current", "render_engine", "camera"]:
            if field in before and field in after and before[field] != after[field]:
                result["changes"][field] = {
                    "before": before[field],
                    "after": after[field]
                }
                result["has_changes"] = True
        
        return result
    
    @classmethod
    def _compare_selection(cls, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """選択状態を比較"""
        result = {
            "has_changes": False,
            "changes": {}
        }
        
        # アクティブオブジェクトの変更
        if before.get("active_object") != after.get("active_object"):
            result["changes"]["active_object"] = {
                "before": before.get("active_object"),
                "after": after.get("active_object")
            }
            result["has_changes"] = True
        
        # 選択オブジェクトの変更
        before_selected = set(before.get("selected_objects", []))
        after_selected = set(after.get("selected_objects", []))
        
        newly_selected = after_selected - before_selected
        newly_deselected = before_selected - after_selected
        
        if newly_selected:
            result["changes"]["newly_selected"] = list(newly_selected)
            result["has_changes"] = True
        
        if newly_deselected:
            result["changes"]["newly_deselected"] = list(newly_deselected)
            result["has_changes"] = True
        
        # モードの変更
        if before.get("mode") != after.get("mode"):
            result["changes"]["mode"] = {
                "before": before.get("mode"),
                "after": after.get("mode")
            }
            result["has_changes"] = True
        
        return result
    
    @classmethod
    def _compare_collections(cls, before: Dict[str, Dict[str, Any]], after: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """コレクション情報を比較"""
        result = {
            "has_changes": False,
            "added": [],
            "removed": [],
            "modified": []
        }
        
        # 存在チェック
        before_names = set(before.keys())
        after_names = set(after.keys())
        
        # 追加されたコレクション
        added = after_names - before_names
        if added:
            result["added"] = list(added)
            result["has_changes"] = True
        
        # 削除されたコレクション
        removed = before_names - after_names
        if removed:
            result["removed"] = list(removed)
            result["has_changes"] = True
        
        # 変更されたコレクション
        modified = []
        modified_details = {}
        
        for name in before_names & after_names:
            coll_before = before[name]
            coll_after = after[name]
            
            changes = {}
            
            # オブジェクトの比較
            before_objects = set(coll_before.get("objects", []))
            after_objects = set(coll_after.get("objects", []))
            
            added_objects = after_objects - before_objects
            removed_objects = before_objects - after_objects
            
            if added_objects:
                changes["added_objects"] = list(added_objects)
            if removed_objects:
                changes["removed_objects"] = list(removed_objects)
            
            # 可視状態の変更
            if coll_before.get("hide") != coll_after.get("hide"):
                changes["hide"] = {
                    "before": coll_before.get("hide"),
                    "after": coll_after.get("hide")
                }
            
            if changes:
                modified.append(name)
                modified_details[name] = changes
        
        if modified:
            result["modified"] = modified
            result["modified_details"] = modified_details
            result["has_changes"] = True
        
        return result
