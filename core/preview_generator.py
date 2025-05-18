"""
Blender Preview Generator
ビューポートのプレビュー画像を生成するモジュール
"""

import bpy
import os
import base64
import tempfile
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# モジュールレベルのロガー
logger = logging.getLogger('blender_mcp.core.preview')

class PreviewGenerator:
    """ビューポートプレビューを生成するクラス"""
    
    def __init__(self):
        self.preview_cache = {}
        self.temp_dir = tempfile.mkdtemp(prefix="blender_mcp_preview_")
        
    def capture_viewport(self, 
                        resolution: Tuple[int, int] = (512, 512),
                        format: str = "PNG",
                        view: str = "current") -> Dict[str, Any]:
        """現在のビューポートをキャプチャ"""
        result = {
            "success": False,
            "preview": None,
            "error": None,
            "metadata": {}
        }
        
        try:
            # 一時ファイルパスを生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"preview_{view}_{timestamp}.{format.lower()}"
            filepath = os.path.join(self.temp_dir, filename)
            
            # レンダリング設定を保存
            original_settings = self._save_render_settings()
            
            # プレビュー用の設定
            scene = bpy.context.scene
            scene.render.resolution_x = resolution[0]
            scene.render.resolution_y = resolution[1]
            scene.render.resolution_percentage = 100
            scene.render.image_settings.file_format = format
            scene.render.filepath = filepath
            
            # ビューポートレンダリング
            if view == "current":
                bpy.ops.render.opengl(write_still=True, view_context=True)
            else:
                # 特定のビューをレンダリング
                self._render_specific_view(view, filepath)
            
            # 画像をbase64エンコード
            if os.path.exists(filepath):
                with open(filepath, "rb") as image_file:
                    encoded = base64.b64encode(image_file.read()).decode()
                
                result["success"] = True
                result["preview"] = f"data:image/{format.lower()};base64,{encoded}"
                result["metadata"] = {
                    "resolution": resolution,
                    "format": format,
                    "view": view,
                    "timestamp": timestamp,
                    "size": os.path.getsize(filepath)
                }
                
                # キャッシュに保存
                cache_key = f"{view}_{resolution}"
                self.preview_cache[cache_key] = result["preview"]
                
                # 一時ファイルを削除
                os.remove(filepath)
            else:
                result["error"] = "プレビュー画像の生成に失敗しました"
            
            # 設定を復元
            self._restore_render_settings(original_settings)
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"ビューポートキャプチャエラー: {e}")
            
        return result
    
    def capture_multiple_views(self, resolution: Tuple[int, int] = (512, 512)) -> Dict[str, Any]:
        """複数のビューをキャプチャ"""
        views = ["front", "right", "top", "perspective"]
        results = {}
        
        for view in views:
            result = self.capture_viewport(resolution=resolution, view=view)
            results[view] = result
        
        # 結合結果を作成
        return {
            "success": all(r["success"] for r in results.values()),
            "previews": {v: r["preview"] for v, r in results.items() if r["success"]},
            "errors": {v: r["error"] for v, r in results.items() if not r["success"]},
            "metadata": {
                "views": views,
                "resolution": resolution,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def create_turntable_animation(self, frames: int = 24, resolution: Tuple[int, int] = (512, 512)) -> Dict[str, Any]:
        """ターンテーブルアニメーションを作成"""
        result = {
            "success": False,
            "frames": [],
            "error": None
        }
        
        try:
            # カメラがなければ作成
            if not bpy.context.scene.camera:
                bpy.ops.object.camera_add(location=(5, -5, 5))
                camera = bpy.context.active_object
                camera.rotation_euler = (1.2, 0, 0.785)
                bpy.context.scene.camera = camera
            
            camera = bpy.context.scene.camera
            original_rotation = camera.rotation_euler.copy()
            
            # 各フレームをレンダリング
            for i in range(frames):
                angle = (i / frames) * 2 * 3.14159  # 360度回転
                camera.rotation_euler.z = original_rotation.z + angle
                
                # フレームをキャプチャ
                frame_result = self.capture_viewport(resolution=resolution)
                if frame_result["success"]:
                    result["frames"].append(frame_result["preview"])
                else:
                    result["error"] = f"フレーム {i} のキャプチャに失敗: {frame_result['error']}"
                    break
            
            # 元の回転を復元
            camera.rotation_euler = original_rotation
            
            if not result["error"]:
                result["success"] = True
                result["metadata"] = {
                    "frames": frames,
                    "resolution": resolution,
                    "fps": 24
                }
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"ターンテーブルアニメーションエラー: {e}")
            
        return result
    
    def compare_before_after(self, 
                           before_context: Dict[str, Any],
                           after_context: Dict[str, Any],
                           resolution: Tuple[int, int] = (512, 512)) -> Dict[str, Any]:
        """操作前後の比較画像を生成"""
        result = {
            "success": False,
            "comparison": None,
            "error": None
        }
        
        try:
            # 現在の状態をキャプチャ（after）
            after_preview = self.capture_viewport(resolution=resolution)
            
            if after_preview["success"]:
                result["success"] = True
                result["comparison"] = {
                    "before": before_context.get("preview", None),
                    "after": after_preview["preview"],
                    "changes": self._detect_visual_changes(before_context, after_context)
                }
            else:
                result["error"] = after_preview["error"]
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"比較画像生成エラー: {e}")
            
        return result
    
    def _render_specific_view(self, view: str, filepath: str):
        """特定のビューをレンダリング"""
        # 一時的にビューを変更
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # ビューの設定
                        if view == "front":
                            space.region_3d.view_rotation = (0.7071, 0.7071, 0, 0)
                        elif view == "right":
                            space.region_3d.view_rotation = (0.5, 0.5, 0.5, 0.5)
                        elif view == "top":
                            space.region_3d.view_rotation = (1, 0, 0, 0)
                        elif view == "perspective":
                            space.region_3d.view_perspective = 'PERSP'
                        
                        # レンダリング
                        override = bpy.context.copy()
                        override['area'] = area
                        override['space_data'] = space
                        override['region'] = area.regions[-1]
                        
                        with bpy.context.temp_override(**override):
                            bpy.ops.render.opengl(write_still=True)
                        
                        break
                break
    
    def _save_render_settings(self) -> Dict[str, Any]:
        """レンダリング設定を保存"""
        scene = bpy.context.scene
        return {
            "resolution_x": scene.render.resolution_x,
            "resolution_y": scene.render.resolution_y,
            "resolution_percentage": scene.render.resolution_percentage,
            "file_format": scene.render.image_settings.file_format,
            "filepath": scene.render.filepath
        }
    
    def _restore_render_settings(self, settings: Dict[str, Any]):
        """レンダリング設定を復元"""
        scene = bpy.context.scene
        scene.render.resolution_x = settings["resolution_x"]
        scene.render.resolution_y = settings["resolution_y"]
        scene.render.resolution_percentage = settings["resolution_percentage"]
        scene.render.image_settings.file_format = settings["file_format"]
        scene.render.filepath = settings["filepath"]
    
    def _detect_visual_changes(self, before: Dict[str, Any], after: Dict[str, Any]) -> List[str]:
        """視覚的な変更を検出"""
        changes = []
        
        try:
            # オブジェクト数の変化
            before_count = len(before.get("selected_objects", []))
            after_count = len(after.get("selected_objects", []))
            
            if after_count > before_count:
                changes.append(f"新しいオブジェクトが追加されました (+{after_count - before_count})")
            elif after_count < before_count:
                changes.append(f"オブジェクトが削除されました (-{before_count - after_count})")
            
            # 位置の変化
            if before.get("active_object") and after.get("active_object"):
                before_loc = before["active_object"].get("location", [0, 0, 0])
                after_loc = after["active_object"].get("location", [0, 0, 0])
                
                if before_loc != after_loc:
                    changes.append("オブジェクトの位置が変更されました")
            
        except Exception as e:
            logger.error(f"変更検出エラー: {e}")
            
        return changes
    
    def cleanup(self):
        """一時ファイルをクリーンアップ"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.info(f"一時ディレクトリを削除しました: {self.temp_dir}")
        except Exception as e:
            logger.error(f"クリーンアップエラー: {e}")

# グローバルインスタンス
_preview_generator = None

def get_preview_generator() -> PreviewGenerator:
    """プレビュージェネレーターのシングルトンインスタンスを取得"""
    global _preview_generator
    if _preview_generator is None:
        _preview_generator = PreviewGenerator()
    return _preview_generator