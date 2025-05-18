"""
カメラ関連のGraphQLリゾルバを提供
"""

import bpy
import math
import logging
from typing import Dict, List, Any, Optional, Union
from .base import ResolverBase, handle_exceptions, dict_to_vector, vector_to_dict, ensure_object_exists

class CameraResolver(ResolverBase):
    """カメラ関連のGraphQLリゾルバクラス"""
    
    def __init__(self):
        super().__init__()
    
    @handle_exceptions
    def get_all(self, obj, info) -> List[Dict[str, Any]]:
        """
        すべてのカメラ情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            
        Returns:
            List[Dict]: カメラ情報のリスト
        """
        self.logger.debug("cameras リゾルバが呼び出されました")
        
        cameras = []
        for camera_obj in [o for o in bpy.data.objects if o.type == 'CAMERA']:
            cameras.append(self._get_camera_data(camera_obj))
        
        return cameras
    
    @handle_exceptions
    def get(self, obj, info, name: str) -> Dict[str, Any]:
        """
        指定された名前のカメラ情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: カメラ名
            
        Returns:
            Dict: カメラ情報
        """
        self.logger.debug(f"camera リゾルバが呼び出されました: name={name}")
        
        # カメラオブジェクトの検索
        camera_obj = ensure_object_exists(name)
        if not camera_obj:
            return self.error_response(f"カメラ '{name}' が見つかりません")
        
        # カメラタイプのチェック
        if camera_obj.type != 'CAMERA':
            return self.error_response(f"オブジェクト '{name}' はカメラではありません")
        
        return self._get_camera_data(camera_obj)
    
    def _get_camera_data(self, camera_obj) -> Dict[str, Any]:
        """
        カメラデータを辞書形式で取得
        
        Args:
            camera_obj: カメラオブジェクト
            
        Returns:
            Dict: カメラデータ
        """
        camera = camera_obj.data
        
        # 基本情報の収集
        data = {
            'name': camera_obj.name,
            'location': self.vector_to_dict(camera_obj.location),
            'rotation': self.vector_to_dict([
                round(math.degrees(angle), 4) for angle in camera_obj.rotation_euler
            ]),
            'type': camera.type,
            'lens': camera.lens,
            'sensor_width': camera.sensor_width,
            'sensor_height': camera.sensor_height,
            'clip_start': camera.clip_start,
            'clip_end': camera.clip_end,
            'is_active': camera_obj == bpy.context.scene.camera
        }
        
        # パースペクティブ情報の追加
        if camera.type == 'PERSP':
            data['perspective_type'] = 'PERSP'
            data['fov'] = math.degrees(camera.angle)
        elif camera.type == 'ORTHO':
            data['perspective_type'] = 'ORTHO'
            data['ortho_scale'] = camera.ortho_scale
        elif camera.type == 'PANO':
            data['perspective_type'] = 'PANO'
            data['fov'] = math.degrees(camera.angle)
        
        return data
    
    @handle_exceptions
    def create(self, obj, info, name: Optional[str] = None, location = None, rotation = None, 
              type: str = "PERSP", lens: float = 50.0, clip_start: float = 0.1, 
              clip_end: float = 100.0, fov: Optional[float] = None) -> Dict[str, Any]:
        """
        新しいカメラを作成
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: カメラ名（省略時は自動生成）
            location: 配置位置
            rotation: 回転（度数法）
            type: カメラタイプ (PERSP, ORTHO, PANO)
            lens: 焦点距離
            clip_start: クリップ開始距離
            clip_end: クリップ終了距離
            fov: 視野角（度数法）
            
        Returns:
            Dict: 作成結果
        """
        self.logger.debug(f"create_camera リゾルバが呼び出されました: name={name}, type={type}")
        
        # 名前の重複チェック
        if name and name in bpy.data.objects:
            return self.error_response(f"オブジェクト名 '{name}' は既に使用されています")
        
        # カメラタイプの標準化と検証
        camera_type = type.upper() if type else 'PERSP'
        valid_types = ['PERSP', 'ORTHO', 'PANO']
        if camera_type not in valid_types:
            return self.error_response(f"無効なカメラタイプ: {camera_type}。許可されるタイプ: {', '.join(valid_types)}")
        
        # カメラの作成
        camera_data = bpy.data.cameras.new(name=name or "Camera")
        camera_obj = bpy.data.objects.new(name or "Camera", camera_data)
        bpy.context.collection.objects.link(camera_obj)
        
        # カメラタイプの設定
        camera_data.type = camera_type
        
        # 基本設定の適用
        camera_data.lens = lens
        camera_data.clip_start = clip_start
        camera_data.clip_end = clip_end
        
        # 視野角の設定（指定がある場合）
        if fov is not None:
            camera_data.angle = math.radians(fov)
        
        # 位置の設定
        if location:
            loc_vector = self.dict_to_vector(location)
            if loc_vector:
                camera_obj.location = loc_vector
        
        # 回転の設定
        if rotation:
            rot_vector = self.dict_to_vector(rotation)
            if rot_vector:
                camera_obj.rotation_euler = [math.radians(angle) for angle in rot_vector]
        
        return self.success_response(
            f"カメラ '{camera_obj.name}' を作成しました",
            {'camera': self._get_camera_data(camera_obj)}
        )
    
    @handle_exceptions
    def update(self, obj, info, name: str, location = None, rotation = None, 
              lens: Optional[float] = None, clip_start: Optional[float] = None, 
              clip_end: Optional[float] = None, fov: Optional[float] = None) -> Dict[str, Any]:
        """
        カメラ設定を更新
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: カメラ名
            location: 新しい位置
            rotation: 新しい回転（度数法）
            lens: 新しい焦点距離
            clip_start: 新しいクリップ開始距離
            clip_end: 新しいクリップ終了距離
            fov: 新しい視野角（度数法）
            
        Returns:
            Dict: 更新結果
        """
        self.logger.debug(f"update_camera リゾルバが呼び出されました: name={name}")
        
        # カメラオブジェクトの検索
        camera_obj = ensure_object_exists(name)
        if not camera_obj:
            return self.error_response(f"カメラ '{name}' が見つかりません")
        
        # カメラタイプのチェック
        if camera_obj.type != 'CAMERA':
            return self.error_response(f"オブジェクト '{name}' はカメラではありません")
        
        # カメラデータ取得
        camera = camera_obj.data
        
        # 更新を適用
        changed = False
        
        if location:
            loc_vector = self.dict_to_vector(location)
            if loc_vector:
                camera_obj.location = loc_vector
                changed = True
        
        if rotation:
            rot_vector = self.dict_to_vector(rotation)
            if rot_vector:
                camera_obj.rotation_euler = [math.radians(angle) for angle in rot_vector]
                changed = True
        
        if lens is not None:
            camera.lens = lens
            changed = True
        
        if clip_start is not None:
            camera.clip_start = clip_start
            changed = True
        
        if clip_end is not None:
            camera.clip_end = clip_end
            changed = True
        
        if fov is not None:
            camera.angle = math.radians(fov)
            changed = True
        
        if not changed:
            return self.error_response("更新するパラメータが指定されていません")
        
        return self.success_response(
            f"カメラ '{name}' を更新しました",
            {'camera': self._get_camera_data(camera_obj)}
        )
    
    @handle_exceptions
    def delete(self, obj, info, name: str) -> Dict[str, Any]:
        """
        カメラを削除
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: 削除するカメラ名
            
        Returns:
            Dict: 削除結果
        """
        self.logger.debug(f"delete_camera リゾルバが呼び出されました: name={name}")
        
        # カメラオブジェクトの検索
        camera_obj = ensure_object_exists(name)
        if not camera_obj:
            return self.error_response(f"カメラ '{name}' が見つかりません")
        
        # カメラタイプのチェック
        if camera_obj.type != 'CAMERA':
            return self.error_response(f"オブジェクト '{name}' はカメラではありません")
        
        # アクティブカメラの場合は警告
        if bpy.context.scene.camera == camera_obj:
            bpy.context.scene.camera = None
        
        # カメラデータを取得（返却用）
        camera_data = self._get_camera_data(camera_obj)
        
        # カメラを削除
        camera = camera_obj.data
        bpy.data.objects.remove(camera_obj, do_unlink=True)
        bpy.data.cameras.remove(camera)
        
        return self.success_response(
            f"カメラ '{name}' を削除しました",
            {'camera': camera_data}
        )
        
    @handle_exceptions
    def set_active(self, obj, info, name: str) -> Dict[str, Any]:
        """
        指定したカメラをアクティブに設定
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: カメラ名
            
        Returns:
            Dict: 設定結果
        """
        self.logger.debug(f"set_active_camera リゾルバが呼び出されました: name={name}")
        
        # カメラオブジェクトの検索
        camera_obj = ensure_object_exists(name)
        if not camera_obj:
            return self.error_response(f"カメラ '{name}' が見つかりません")
        
        # カメラタイプのチェック
        if camera_obj.type != 'CAMERA':
            return self.error_response(f"オブジェクト '{name}' はカメラではありません")
        
        # アクティブカメラとして設定
        bpy.context.scene.camera = camera_obj
        
        return self.success_response(
            f"カメラ '{name}' をアクティブに設定しました",
            {'camera': self._get_camera_data(camera_obj)}
        )
