"""
オブジェクト関連のGraphQLリゾルバを提供
"""

import bpy
import math
import logging
from typing import Dict, List, Any, Optional, Union
from .base import ResolverBase, handle_exceptions, dict_to_vector, vector_to_dict, ensure_object_exists

# 定数定義
BOOLEAN_OPERATION_UNION = 'UNION'
BOOLEAN_OPERATION_DIFFERENCE = 'DIFFERENCE'
BOOLEAN_OPERATION_INTERSECT = 'INTERSECT'

class ObjectResolver(ResolverBase):
    """オブジェクト関連のGraphQLリゾルバクラス"""
    
    def __init__(self):
        super().__init__()
    
    @handle_exceptions
    def get(self, obj, info, name: str) -> Dict[str, Any]:
        """
        指定された名前のオブジェクト情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: オブジェクト名
            
        Returns:
            Dict: オブジェクト情報
        """
        self.logger.debug(f"object リゾルバが呼び出されました: name={name}")
        
        # オブジェクトの検索
        blender_obj = ensure_object_exists(name)
        if not blender_obj:
            return self.error_response(f"オブジェクト '{name}' が見つかりません")
        
        # オブジェクト情報の構築
        return self._get_object_data(blender_obj)
    
    def _get_object_data(self, blender_obj) -> Dict[str, Any]:
        """
        Blenderオブジェクトのデータを辞書形式で取得
        
        Args:
            blender_obj: Blenderオブジェクト
            
        Returns:
            Dict: オブジェクトデータ
        """
        data = {
            'name': blender_obj.name,
            'type': blender_obj.type,
            'location': self.vector_to_dict(blender_obj.location),
            'rotation': self.vector_to_dict([
                round(math.degrees(angle), 4) for angle in blender_obj.rotation_euler
            ]),
            'scale': self.vector_to_dict(blender_obj.scale),
            'dimensions': self.vector_to_dict(blender_obj.dimensions),
            'parent': blender_obj.parent.name if blender_obj.parent else None,
            'visible': not blender_obj.hide_viewport and not blender_obj.hide_render,
            'modifiers': [mod.name for mod in blender_obj.modifiers]
        }
        
        # マテリアル情報の追加
        if blender_obj.material_slots:
            data['materials'] = []
            for slot in blender_obj.material_slots:
                if slot.material:
                    data['materials'].append(slot.material.name)
        
        return data
    
    @handle_exceptions
    def get_all(self, obj, info, type_name: Optional[str] = None, name_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        オブジェクト一覧を取得（オプションでフィルタリング）
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            type_name: フィルタリングするオブジェクトタイプ
            name_pattern: 名前の一部でフィルタリング
            
        Returns:
            List[Dict]: オブジェクト情報のリスト
        """
        self.logger.debug(f"objects リゾルバが呼び出されました: type={type_name}, name_pattern={name_pattern}")
        
        # フィルタ条件に基づいてオブジェクトをフィルタリング
        filtered_objects = []
        for blender_obj in bpy.data.objects:
            if type_name and blender_obj.type != type_name:
                continue
            
            if name_pattern and name_pattern.lower() not in blender_obj.name.lower():
                continue
            
            filtered_objects.append(self._get_object_data(blender_obj))
        
        return filtered_objects
    
    @handle_exceptions
    def create(self, obj, info, type: str = 'CUBE', name: Optional[str] = None, location = None) -> Dict[str, Any]:
        """
        新しいオブジェクトを作成
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            type: オブジェクトタイプ (CUBE, SPHERE, PLANE等)
            name: オブジェクト名（省略時は自動生成）
            location: 配置位置
            
        Returns:
            Dict: 作成結果
        """
        self.logger.debug(f"create_object リゾルバが呼び出されました: type={type}, name={name}")
        
        # オブジェクトタイプの標準化
        obj_type = type.upper() if type else 'CUBE'
        
        # 許可されたタイプかチェック
        allowed_types = ['CUBE', 'SPHERE', 'CYLINDER', 'CONE', 'PLANE', 'EMPTY', 'LIGHT', 'CAMERA']
        if obj_type not in allowed_types:
            return self.error_response(f"無効なオブジェクトタイプ: {obj_type}。許可されるタイプ: {', '.join(allowed_types)}")
        
        # 名前の重複チェック
        if name and name in bpy.data.objects:
            return self.error_response(f"オブジェクト名 '{name}' は既に使用されています")
        
        # オブジェクト作成
        try:
            # プリミティブの作成
            if obj_type == 'CUBE':
                bpy.ops.mesh.primitive_cube_add()
            elif obj_type == 'SPHERE':
                bpy.ops.mesh.primitive_uv_sphere_add()
            elif obj_type == 'CYLINDER':
                bpy.ops.mesh.primitive_cylinder_add()
            elif obj_type == 'CONE':
                bpy.ops.mesh.primitive_cone_add()
            elif obj_type == 'PLANE':
                bpy.ops.mesh.primitive_plane_add()
            elif obj_type == 'EMPTY':
                bpy.ops.object.empty_add(type='PLAIN_AXES')
            elif obj_type == 'LIGHT':
                bpy.ops.object.light_add(type='POINT')
            elif obj_type == 'CAMERA':
                bpy.ops.object.camera_add()
            
            # 作成されたオブジェクトを取得
            created_obj = bpy.context.active_object
            
            # 名前設定
            if name:
                created_obj.name = name
            
            # 位置設定
            if location:
                loc_vector = self.dict_to_vector(location)
                if loc_vector:
                    created_obj.location = loc_vector
            
            # 結果を返す
            return self.success_response(
                f"オブジェクト '{created_obj.name}' を作成しました",
                {'object': self._get_object_data(created_obj)}
            )
            
        except Exception as e:
            self.logger.error(f"オブジェクト作成エラー: {str(e)}")
            return self.error_response(f"オブジェクト作成中にエラーが発生しました: {str(e)}")
    
    @handle_exceptions
    def transform(self, obj, info, name: str, location = None, rotation = None, scale = None) -> Dict[str, Any]:
        """
        オブジェクトを変換（移動・回転・スケール）
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: オブジェクト名
            location: 新しい位置
            rotation: 新しい回転（度数法）
            scale: 新しいスケール
            
        Returns:
            Dict: 変換結果
        """
        self.logger.debug(f"transform_object リゾルバが呼び出されました: name={name}")
        
        # オブジェクト検索
        blender_obj = ensure_object_exists(name)
        if not blender_obj:
            return self.error_response(f"オブジェクト '{name}' が見つかりません")
        
        # 変換を適用
        changed = False
        
        if location:
            loc_vector = self.dict_to_vector(location)
            if loc_vector:
                blender_obj.location = loc_vector
                changed = True
        
        if rotation:
            rot_vector = self.dict_to_vector(rotation)
            if rot_vector:
                blender_obj.rotation_euler = [math.radians(angle) for angle in rot_vector]
                changed = True
        
        if scale:
            scale_vector = self.dict_to_vector(scale)
            if scale_vector:
                blender_obj.scale = scale_vector
                changed = True
        
        if not changed:
            return self.error_response("変換パラメータが指定されていません")
        
        # シーン更新を要求
        bpy.context.view_layer.update()
        
        return self.success_response(
            f"オブジェクト '{name}' を変換しました",
            {'object': self._get_object_data(blender_obj)}
        )
    
    @handle_exceptions
    def delete(self, obj, info, name: str) -> Dict[str, Any]:
        """
        オブジェクトを削除
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: 削除するオブジェクト名
            
        Returns:
            Dict: 削除結果
        """
        self.logger.debug(f"delete_object リゾルバが呼び出されました: name={name}")
        
        # オブジェクト検索
        blender_obj = ensure_object_exists(name)
        if not blender_obj:
            return self.error_response(f"オブジェクト '{name}' が見つかりません")
        
        # オブジェクト削除
        bpy.data.objects.remove(blender_obj, do_unlink=True)
        
        return self.success_response(f"オブジェクト '{name}' を削除しました")
    
    @handle_exceptions
    def boolean_operation(self, obj, info, operation: str, objectName: str, targetName: str, resultName: Optional[str] = None) -> Dict[str, Any]:
        """
        ブーリアン操作を実行
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            operation: 操作タイプ (UNION, DIFFERENCE, INTERSECT)
            objectName: 対象オブジェクト名
            targetName: 操作相手オブジェクト名
            resultName: 結果オブジェクト名（省略時は自動生成）
            
        Returns:
            Dict: 操作結果
        """
        self.logger.debug(f"boolean_operation リゾルバが呼び出されました: operation={operation}, object={objectName}, target={targetName}")
        
        # 操作タイプの検証
        valid_operations = [BOOLEAN_OPERATION_UNION, BOOLEAN_OPERATION_DIFFERENCE, BOOLEAN_OPERATION_INTERSECT]
        if operation not in valid_operations:
            return self.error_response(f"無効なブーリアン操作: {operation}。許可される操作: {', '.join(valid_operations)}")
        
        # オブジェクト検索
        obj1 = ensure_object_exists(objectName)
        if not obj1:
            return self.error_response(f"オブジェクト '{objectName}' が見つかりません")
        
        obj2 = ensure_object_exists(targetName)
        if not obj2:
            return self.error_response(f"オブジェクト '{targetName}' が見つかりません")
        
        # メッシュオブジェクトかチェック
        if obj1.type != 'MESH' or obj2.type != 'MESH':
            return self.error_response("ブーリアン操作はメッシュオブジェクトのみで実行できます")
        
        # 結果オブジェクト名の決定
        if not resultName:
            resultName = f"{objectName}_{operation.lower()}_{targetName}"
        
        # 既存の結果オブジェクトを削除（上書き）
        existing_result = ensure_object_exists(resultName)
        if existing_result:
            bpy.data.objects.remove(existing_result, do_unlink=True)
        
        # 元のオブジェクトを複製
        bpy.ops.object.select_all(action='DESELECT')
        obj1.select_set(True)
        bpy.context.view_layer.objects.active = obj1
        bpy.ops.object.duplicate()
        result_obj = bpy.context.active_object
        result_obj.name = resultName
        
        # ブーリアンモディファイア追加
        bool_mod = result_obj.modifiers.new(name="Boolean", type='BOOLEAN')
        bool_mod.object = obj2
        
        # 操作タイプ設定
        if operation == BOOLEAN_OPERATION_UNION:
            bool_mod.operation = 'UNION'
        elif operation == BOOLEAN_OPERATION_DIFFERENCE:
            bool_mod.operation = 'DIFFERENCE'
        elif operation == BOOLEAN_OPERATION_INTERSECT:
            bool_mod.operation = 'INTERSECT'
        
        # モディファイア適用
        bpy.ops.object.modifier_apply(modifier=bool_mod.name)
        
        return self.success_response(
            f"ブーリアン操作 '{operation}' を実行しました",
            {'object': self._get_object_data(result_obj)}
        )
    
    @handle_exceptions
    def get_mesh_data(self, obj, info, name: str) -> Dict[str, Any]:
        """
        メッシュデータを取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: メッシュオブジェクト名
            
        Returns:
            Dict: メッシュデータ
        """
        self.logger.debug(f"mesh_data リゾルバが呼び出されました: name={name}")
        
        # オブジェクト検索
        blender_obj = ensure_object_exists(name)
        if not blender_obj:
            return self.error_response(f"オブジェクト '{name}' が見つかりません")
        
        # メッシュオブジェクトかチェック
        if blender_obj.type != 'MESH':
            return self.error_response(f"オブジェクト '{name}' はメッシュではありません")
        
        # メッシュデータ取得
        mesh = blender_obj.data
        
        # 頂点データ収集
        vertices = []
        for i, v in enumerate(mesh.vertices):
            vertices.append({
                'index': i,
                'position': self.vector_to_dict(v.co),
                'normal': self.vector_to_dict(v.normal)
            })
        
        # エッジデータ収集
        edges = []
        for i, e in enumerate(mesh.edges):
            edges.append({
                'index': i,
                'vertices': list(e.vertices)
            })
        
        # フェイスデータ収集
        faces = []
        for i, p in enumerate(mesh.polygons):
            faces.append({
                'index': i,
                'vertices': list(p.vertices),
                'material_index': p.material_index
            })
        
        # マテリアルデータ収集
        materials = []
        for slot in blender_obj.material_slots:
            if slot.material:
                materials.append({
                    'name': slot.material.name
                })
        
        return {
            'name': mesh.name,
            'vertices': vertices,
            'edges': edges,
            'faces': faces,
            'materials': materials
        }
