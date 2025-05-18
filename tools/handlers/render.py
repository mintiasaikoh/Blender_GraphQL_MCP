"""
レンダリング関連のGraphQLリゾルバを提供
"""

import bpy
import os
import logging
import tempfile
from typing import Dict, List, Any, Optional, Union
from .base import ResolverBase, handle_exceptions

class RenderResolver(ResolverBase):
    """レンダリング関連のGraphQLリゾルバクラス"""
    
    def __init__(self):
        super().__init__()
    
    @handle_exceptions
    def get_settings(self, obj, info) -> Dict[str, Any]:
        """
        現在のレンダリング設定を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            
        Returns:
            Dict: レンダリング設定情報
        """
        self.logger.debug("render_settings リゾルバが呼び出されました")
        
        render = bpy.context.scene.render
        
        # レンダリング設定情報を構築
        return {
            'engine': render.engine,
            'resolution_x': render.resolution_x,
            'resolution_y': render.resolution_y,
            'resolution_percentage': render.resolution_percentage,
            'file_format': render.image_settings.file_format,
            'color_mode': render.image_settings.color_mode,
            'color_depth': render.image_settings.color_depth,
            'filepath': render.filepath,
            'use_motion_blur': render.use_motion_blur,
            'samples': getattr(bpy.context.scene.cycles, 'samples', 0) if hasattr(bpy.context.scene, 'cycles') else 0,
            'film_transparent': render.film_transparent
        }
    
    @handle_exceptions
    def update_settings(self, obj, info, engine: Optional[str] = None, 
                       resolution_x: Optional[int] = None, resolution_y: Optional[int] = None, 
                       resolution_percentage: Optional[int] = None, file_format: Optional[str] = None, 
                       filepath: Optional[str] = None, samples: Optional[int] = None) -> Dict[str, Any]:
        """
        レンダリング設定を更新
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            engine: レンダリングエンジン
            resolution_x: X解像度
            resolution_y: Y解像度
            resolution_percentage: 解像度パーセンテージ
            file_format: ファイルフォーマット
            filepath: 保存パス
            samples: サンプル数
            
        Returns:
            Dict: 更新結果
        """
        self.logger.debug("update_render_settings リゾルバが呼び出されました")
        
        render = bpy.context.scene.render
        
        # 更新を適用
        changed = False
        
        if engine:
            valid_engines = ['BLENDER_EEVEE', 'CYCLES', 'BLENDER_WORKBENCH']
            if engine.upper() in valid_engines:
                render.engine = engine.upper()
                changed = True
            else:
                return self.error_response(f"無効なレンダリングエンジン: {engine}。許可されるエンジン: {', '.join(valid_engines)}")
        
        if resolution_x is not None:
            if resolution_x > 0:
                render.resolution_x = resolution_x
                changed = True
            else:
                return self.error_response("解像度は正の値である必要があります")
        
        if resolution_y is not None:
            if resolution_y > 0:
                render.resolution_y = resolution_y
                changed = True
            else:
                return self.error_response("解像度は正の値である必要があります")
        
        if resolution_percentage is not None:
            if 1 <= resolution_percentage <= 100:
                render.resolution_percentage = resolution_percentage
                changed = True
            else:
                return self.error_response("解像度パーセンテージは1〜100の範囲内である必要があります")
        
        if file_format:
            valid_formats = ['PNG', 'JPEG', 'TIFF', 'OPEN_EXR', 'BMP']
            if file_format.upper() in valid_formats:
                render.image_settings.file_format = file_format.upper()
                changed = True
            else:
                return self.error_response(f"無効なファイルフォーマット: {file_format}。許可されるフォーマット: {', '.join(valid_formats)}")
        
        if filepath:
            # ディレクトリが存在するか確認
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                except Exception as e:
                    return self.error_response(f"出力ディレクトリの作成に失敗しました: {str(e)}")
            
            render.filepath = filepath
            changed = True
        
        if samples is not None:
            if hasattr(bpy.context.scene, 'cycles'):
                if samples > 0:
                    bpy.context.scene.cycles.samples = samples
                    changed = True
                else:
                    return self.error_response("サンプル数は正の値である必要があります")
        
        if not changed:
            return self.error_response("更新するパラメータが指定されていません")
        
        return self.success_response(
            "レンダリング設定を更新しました",
            {'settings': self.get_settings(obj, info)}
        )
    
    @handle_exceptions
    def render(self, obj, info, filepath: Optional[str] = None, frame: Optional[int] = None) -> Dict[str, Any]:
        """
        レンダリングを実行
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            filepath: 出力ファイルパス
            frame: レンダリングするフレーム番号
            
        Returns:
            Dict: レンダリング結果
        """
        self.logger.debug(f"render_frame リゾルバが呼び出されました: filepath={filepath}, frame={frame}")
        
        # 現在の設定を保存
        original_filepath = bpy.context.scene.render.filepath
        original_frame = bpy.context.scene.frame_current
        
        # 一時ファイルパスの設定
        temp_filepath = filepath
        if not temp_filepath:
            temp_dir = tempfile.gettempdir()
            temp_filepath = os.path.join(temp_dir, f"blender_render_{bpy.context.scene.render.image_settings.file_format.lower()}")
        
        # ディレクトリが存在するか確認
        directory = os.path.dirname(temp_filepath)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                return self.error_response(f"出力ディレクトリの作成に失敗しました: {str(e)}")
        
        # レンダリング設定を変更
        bpy.context.scene.render.filepath = temp_filepath
        
        # フレームを設定
        if frame is not None:
            bpy.context.scene.frame_set(frame)
        
        try:
            # レンダリングを実行
            bpy.ops.render.render(write_still=True)
            
            # 結果を取得
            result = {
                'success': True,
                'message': f"レンダリングが完了しました。ファイル: {temp_filepath}",
                'filepath': temp_filepath,
                'settings': self.get_settings(obj, info)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"レンダリングエラー: {str(e)}")
            return self.error_response(f"レンダリング中にエラーが発生しました: {str(e)}")
            
        finally:
            # 元の設定を復元
            bpy.context.scene.render.filepath = original_filepath
            bpy.context.scene.frame_set(original_frame)
