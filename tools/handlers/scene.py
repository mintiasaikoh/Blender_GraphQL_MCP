"""
シーン関連のGraphQLリゾルバを提供
"""

import bpy
import logging
from typing import Dict, List, Any, Optional, Union
from .base import ResolverBase, handle_exceptions

class SceneResolver(ResolverBase):
    """シーン関連のGraphQLリゾルバクラス"""
    
    def __init__(self):
        super().__init__()
    
    @handle_exceptions
    def hello(self, obj, info) -> str:
        """
        テスト用の挨拶関数
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            
        Returns:
            str: 挨拶メッセージ
        """
        self.logger.debug("hello リゾルバが呼び出されました")
        return "Hello from Blender GraphQL API!"
    
    @handle_exceptions
    def info(self, obj, info) -> Dict[str, Any]:
        """
        現在のシーン情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            
        Returns:
            Dict: シーン情報を含む辞書
        """
        self.logger.debug("scene_info リゾルバが呼び出されました")
        return self.get(obj, info)
    
    @handle_exceptions
    def get(self, obj, info, name: Optional[str] = None) -> Dict[str, Any]:
        """
        指定された名前またはアクティブなシーンの情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: シーン名（指定がない場合はアクティブシーン）
            
        Returns:
            Dict: シーン情報を含む辞書
        """
        self.logger.debug(f"scene リゾルバが呼び出されました: name={name}")
        
        # シーンの取得
        if name:
            if name in bpy.data.scenes:
                scene = bpy.data.scenes[name]
            else:
                return self.error_response(f"シーン '{name}' が見つかりません")
        else:
            scene = bpy.context.scene
        
        # オブジェクト情報の収集
        objects = []
        for obj in scene.objects:
            objects.append({
                'name': obj.name,
                'type': obj.type,
                'location': self.vector_to_dict(obj.location),
                'rotation': self.vector_to_dict([
                    round(angle, 4) for angle in obj.rotation_euler
                ]),
                'scale': self.vector_to_dict(obj.scale),
                'visible': not obj.hide_viewport and not obj.hide_render
            })
        
        # シーン情報を構築
        return {
            'name': scene.name,
            'objects': objects,
            'frame_current': scene.frame_current,
            'frame_start': scene.frame_start,
            'frame_end': scene.frame_end,
            'render': {
                'engine': scene.render.engine,
                'resolution_x': scene.render.resolution_x,
                'resolution_y': scene.render.resolution_y,
                'resolution_percentage': scene.render.resolution_percentage,
                'filepath': scene.render.filepath
            }
        }
    
    @handle_exceptions
    def get_all(self, obj, info) -> List[Dict[str, Any]]:
        """
        すべてのシーン情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            
        Returns:
            List[Dict]: すべてのシーン情報
        """
        self.logger.debug("get_all_scenes リゾルバが呼び出されました")
        
        scenes = []
        for scene in bpy.data.scenes:
            scenes.append(self.get(obj, info, scene.name))
        
        return scenes
