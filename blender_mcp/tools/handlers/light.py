"""
ライト関連のGraphQLリゾルバを提供
"""

import bpy
import math
import logging
from typing import Dict, List, Any, Optional, Union
from .base import ResolverBase, handle_exceptions, dict_to_vector, vector_to_dict, ensure_object_exists

class LightResolver(ResolverBase):
    """ライト関連のGraphQLリゾルバクラス"""
    
    def __init__(self):
        super().__init__()
    
    @handle_exceptions
    def get_all(self, obj, info) -> List[Dict[str, Any]]:
        """
        すべてのライト情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            
        Returns:
            List[Dict]: ライト情報のリスト
        """
        self.logger.debug("lights リゾルバが呼び出されました")
        
        lights = []
        for light_obj in [o for o in bpy.data.objects if o.type == 'LIGHT']:
            lights.append(self._get_light_data(light_obj))
        
        return lights
    
    @handle_exceptions
    def get(self, obj, info, name: str) -> Dict[str, Any]:
        """
        指定された名前のライト情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: ライト名
            
        Returns:
            Dict: ライト情報
        """
        self.logger.debug(f"light リゾルバが呼び出されました: name={name}")
        
        # ライトオブジェクトの検索
        light_obj = ensure_object_exists(name)
        if not light_obj:
            return self.error_response(f"ライト '{name}' が見つかりません")
        
        # ライトタイプのチェック
        if light_obj.type != 'LIGHT':
            return self.error_response(f"オブジェクト '{name}' はライトではありません")
        
        return self._get_light_data(light_obj)
    
    def _get_light_data(self, light_obj) -> Dict[str, Any]:
        """
        ライトデータを辞書形式で取得
        
        Args:
            light_obj: ライトオブジェクト
            
        Returns:
            Dict: ライトデータ
        """
        light = light_obj.data
        
        # 基本情報の収集
        data = {
            'name': light_obj.name,
            'location': self.vector_to_dict(light_obj.location),
            'rotation': self.vector_to_dict([
                round(math.degrees(angle), 4) for angle in light_obj.rotation_euler
            ]),
            'type': light.type,
            'color': self.vector_to_dict(light.color),
            'energy': light.energy,
            'shadow': light.use_shadow,
            'size': light.shadow_soft_size
        }
        
        # ライトタイプ別の情報追加
        if light.type == 'SPOT':
            data['spot_size'] = math.degrees(light.spot_size)
            data['spot_blend'] = light.spot_blend
            data['show_cone'] = light.show_cone
        elif light.type == 'AREA':
            data['shape'] = light.shape
            data['size'] = light.size
            data['size_y'] = light.size_y if hasattr(light, 'size_y') else None
        elif light.type == 'SUN':
            data['angle'] = light.angle
        
        return data
    
    @handle_exceptions
    def create(self, obj, info, name: Optional[str] = None, type: str = "POINT", 
              location = None, rotation = None, color = None, 
              energy: float = 10.0, shadow: bool = True) -> Dict[str, Any]:
        """
        新しいライトを作成
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: ライト名（省略時は自動生成）
            type: ライトタイプ (POINT, SUN, SPOT, AREA)
            location: 配置位置
            rotation: 回転（度数法）
            color: 光の色
            energy: 光量
            shadow: シャドウを有効にするか
            
        Returns:
            Dict: 作成結果
        """
        self.logger.debug(f"create_light リゾルバが呼び出されました: name={name}, type={type}")
        
        # 名前の重複チェック
        if name and name in bpy.data.objects:
            return self.error_response(f"オブジェクト名 '{name}' は既に使用されています")
        
        # ライトタイプの標準化と検証
        light_type = type.upper() if type else 'POINT'
        valid_types = ['POINT', 'SUN', 'SPOT', 'AREA']
        if light_type not in valid_types:
            return self.error_response(f"無効なライトタイプ: {light_type}。許可されるタイプ: {', '.join(valid_types)}")
        
        # ライトの作成
        light_data = bpy.data.lights.new(name=name or "Light", type=light_type)
        light_obj = bpy.data.objects.new(name or "Light", light_data)
        bpy.context.collection.objects.link(light_obj)
        
        # 基本設定の適用
        light_data.energy = energy
        light_data.use_shadow = shadow
        
        # 色の設定
        if color:
            col_vector = self.dict_to_vector(color)
            if col_vector and len(col_vector) >= 3:
                light_data.color = col_vector
        
        # 位置の設定
        if location:
            loc_vector = self.dict_to_vector(location)
            if loc_vector:
                light_obj.location = loc_vector
        
        # 回転の設定
        if rotation:
            rot_vector = self.dict_to_vector(rotation)
            if rot_vector:
                light_obj.rotation_euler = [math.radians(angle) for angle in rot_vector]
        
        return self.success_response(
            f"ライト '{light_obj.name}' を作成しました",
            {'light': self._get_light_data(light_obj)}
        )
    
    @handle_exceptions
    def update(self, obj, info, name: str, location = None, rotation = None, 
              color = None, energy: Optional[float] = None, shadow: Optional[bool] = None) -> Dict[str, Any]:
        """
        ライト設定を更新
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: ライト名
            location: 新しい位置
            rotation: 新しい回転（度数法）
            color: 新しい色
            energy: 新しい光量
            shadow: シャドウを有効にするか
            
        Returns:
            Dict: 更新結果
        """
        self.logger.debug(f"update_light リゾルバが呼び出されました: name={name}")
        
        # ライトオブジェクトの検索
        light_obj = ensure_object_exists(name)
        if not light_obj:
            return self.error_response(f"ライト '{name}' が見つかりません")
        
        # ライトタイプのチェック
        if light_obj.type != 'LIGHT':
            return self.error_response(f"オブジェクト '{name}' はライトではありません")
        
        # ライトデータ取得
        light = light_obj.data
        
        # 更新を適用
        changed = False
        
        if location:
            loc_vector = self.dict_to_vector(location)
            if loc_vector:
                light_obj.location = loc_vector
                changed = True
        
        if rotation:
            rot_vector = self.dict_to_vector(rotation)
            if rot_vector:
                light_obj.rotation_euler = [math.radians(angle) for angle in rot_vector]
                changed = True
        
        if color:
            col_vector = self.dict_to_vector(color)
            if col_vector and len(col_vector) >= 3:
                light.color = col_vector
                changed = True
        
        if energy is not None:
            light.energy = energy
            changed = True
        
        if shadow is not None:
            light.use_shadow = shadow
            changed = True
        
        if not changed:
            return self.error_response("更新するパラメータが指定されていません")
        
        return self.success_response(
            f"ライト '{name}' を更新しました",
            {'light': self._get_light_data(light_obj)}
        )
    
    @handle_exceptions
    def delete(self, obj, info, name: str) -> Dict[str, Any]:
        """
        ライトを削除
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: 削除するライト名
            
        Returns:
            Dict: 削除結果
        """
        self.logger.debug(f"delete_light リゾルバが呼び出されました: name={name}")
        
        # ライトオブジェクトの検索
        light_obj = ensure_object_exists(name)
        if not light_obj:
            return self.error_response(f"ライト '{name}' が見つかりません")
        
        # ライトタイプのチェック
        if light_obj.type != 'LIGHT':
            return self.error_response(f"オブジェクト '{name}' はライトではありません")
        
        # ライトデータを取得（返却用）
        light_data = self._get_light_data(light_obj)
        
        # ライトを削除
        light = light_obj.data
        bpy.data.objects.remove(light_obj, do_unlink=True)
        bpy.data.lights.remove(light)
        
        return self.success_response(
            f"ライト '{name}' を削除しました",
            {'light': light_data}
        )
