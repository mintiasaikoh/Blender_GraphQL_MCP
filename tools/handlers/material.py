"""
マテリアル関連のGraphQLリゾルバを提供
"""

import bpy
import os
import logging
from typing import Dict, List, Any, Optional, Union
from .base import ResolverBase, handle_exceptions, ensure_material_exists, ensure_object_exists

class MaterialResolver(ResolverBase):
    """マテリアル関連のGraphQLリゾルバクラス"""
    
    def __init__(self):
        super().__init__()
    
    @handle_exceptions
    def get(self, obj, info, name: str) -> Dict[str, Any]:
        """
        指定された名前のマテリアル情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: マテリアル名
            
        Returns:
            Dict: マテリアル情報
        """
        self.logger.debug(f"material リゾルバが呼び出されました: name={name}")
        
        # マテリアルの検索
        material = ensure_material_exists(name)
        if not material:
            return self.error_response(f"マテリアル '{name}' が見つかりません")
        
        # マテリアル情報を構築
        return self._get_material_data(material)
    
    def _get_material_data(self, material) -> Dict[str, Any]:
        """
        Blenderマテリアルのデータを辞書形式で取得
        
        Args:
            material: Blenderマテリアル
            
        Returns:
            Dict: マテリアルデータ
        """
        data = {
            'name': material.name,
            'use_nodes': material.use_nodes,
        }
        
        # プリンシプルBSDFのデータを取得（存在する場合）
        if material.use_nodes and material.node_tree:
            principled = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled:
                data['baseColor'] = self.vector_to_dict(principled.inputs['Base Color'].default_value)
                data['metallic'] = principled.inputs['Metallic'].default_value
                data['roughness'] = principled.inputs['Roughness'].default_value
                data['specular'] = principled.inputs['Specular'].default_value
                data['emission'] = self.vector_to_dict(principled.inputs['Emission'].default_value)
        
        # 使用テクスチャを確認
        data['textures'] = self._get_material_textures(material)
        
        return data
    
    def _get_material_textures(self, material) -> List[Dict[str, Any]]:
        """
        マテリアルのテクスチャ情報を取得
        
        Args:
            material: Blenderマテリアル
            
        Returns:
            List[Dict]: テクスチャ情報のリスト
        """
        textures = []
        
        if not material.use_nodes or not material.node_tree:
            return textures
        
        # テクスチャノードを検索
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                texture_type = "unknown"
                
                # テクスチャタイプを推測
                for link in material.node_tree.links:
                    if link.from_node == node:
                        input_name = link.to_socket.name.lower()
                        if "color" in input_name or "base" in input_name:
                            texture_type = "color"
                        elif "normal" in input_name:
                            texture_type = "normal"
                        elif "rough" in input_name:
                            texture_type = "roughness"
                        elif "metal" in input_name:
                            texture_type = "metallic"
                        elif "spec" in input_name:
                            texture_type = "specular"
                        elif "bump" in input_name or "displace" in input_name:
                            texture_type = "bump"
                        break
                
                textures.append({
                    'name': node.image.name,
                    'type': texture_type,
                    'path': node.image.filepath,
                    'resolution': [node.image.size[0], node.image.size[1]]
                })
        
        return textures
    
    @handle_exceptions
    def get_all(self, obj, info) -> List[Dict[str, Any]]:
        """
        すべてのマテリアル情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            
        Returns:
            List[Dict]: マテリアル情報のリスト
        """
        self.logger.debug("materials リゾルバが呼び出されました")
        
        materials = []
        for material in bpy.data.materials:
            materials.append(self._get_material_data(material))
        
        return materials
    
    @handle_exceptions
    def create(self, obj, info, name: Optional[str] = None, baseColor = None, 
              metallic: float = 0.0, roughness: float = 0.5, useNodes: bool = True) -> Dict[str, Any]:
        """
        新しいマテリアルを作成
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: マテリアル名（省略時は自動生成）
            baseColor: 基本色
            metallic: 金属度
            roughness: 粗さ
            useNodes: ノード使用フラグ
            
        Returns:
            Dict: 作成結果
        """
        self.logger.debug(f"create_material リゾルバが呼び出されました: name={name}")
        
        # 名前の重複チェック
        if name and name in bpy.data.materials:
            return self.error_response(f"マテリアル名 '{name}' は既に使用されています")
        
        # 新しいマテリアルを作成
        material = bpy.data.materials.new(name=name or "Material")
        material.use_nodes = useNodes
        
        # プリンシプルBSDFのプロパティを設定
        if useNodes and material.node_tree:
            principled = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled:
                # ベースカラー設定
                if baseColor:
                    color = self.dict_to_vector(baseColor)
                    if color and len(color) >= 3:
                        principled.inputs['Base Color'].default_value = (
                            color[0], color[1], color[2], 1.0
                        )
                
                # 金属度と粗さの設定
                principled.inputs['Metallic'].default_value = metallic
                principled.inputs['Roughness'].default_value = roughness
        
        return self.success_response(
            f"マテリアル '{material.name}' を作成しました",
            {'material': self._get_material_data(material)}
        )
    
    @handle_exceptions
    def assign(self, obj, info, objectName: str, materialName: str) -> Dict[str, Any]:
        """
        オブジェクトにマテリアルを割り当て
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            objectName: オブジェクト名
            materialName: マテリアル名
            
        Returns:
            Dict: 割り当て結果
        """
        self.logger.debug(f"assign_material リゾルバが呼び出されました: object={objectName}, material={materialName}")
        
        # オブジェクト検索
        blender_obj = ensure_object_exists(objectName)
        if not blender_obj:
            return self.error_response(f"オブジェクト '{objectName}' が見つかりません")
        
        # マテリアル検索
        material = ensure_material_exists(materialName)
        if not material:
            return self.error_response(f"マテリアル '{materialName}' が見つかりません")
        
        # オブジェクトにマテリアルを割り当て
        if len(blender_obj.material_slots) == 0:
            blender_obj.data.materials.append(material)
        else:
            blender_obj.material_slots[0].material = material
        
        return self.success_response(
            f"マテリアル '{materialName}' をオブジェクト '{objectName}' に割り当てました",
            {'material': self._get_material_data(material)}
        )
    
    @handle_exceptions
    def get_textures(self, obj, info) -> List[Dict[str, Any]]:
        """
        すべてのテクスチャ情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            
        Returns:
            List[Dict]: テクスチャ情報のリスト
        """
        self.logger.debug("textures リゾルバが呼び出されました")
        
        textures = []
        for image in bpy.data.images:
            if not image.has_data:
                continue
                
            textures.append({
                'name': image.name,
                'filepath': image.filepath,
                'size': [image.size[0], image.size[1]],
                'channels': image.channels,
                'is_dirty': image.is_dirty,
                'file_format': image.file_format
            })
        
        return textures
    
    @handle_exceptions
    def add_texture(self, obj, info, materialName: str, texturePath: str, textureType: str = 'color') -> Dict[str, Any]:
        """
        マテリアルにテクスチャを追加
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            materialName: マテリアル名
            texturePath: テクスチャのファイルパス
            textureType: テクスチャのタイプ (color, normal, roughness等)
            
        Returns:
            Dict: テクスチャ追加結果
        """
        self.logger.debug(f"add_texture リゾルバが呼び出されました: material={materialName}, path={texturePath}, type={textureType}")
        
        # マテリアル検索
        material = ensure_material_exists(materialName)
        if not material:
            return self.error_response(f"マテリアル '{materialName}' が見つかりません")
        
        # ファイルパスの確認
        if not os.path.exists(texturePath):
            return self.error_response(f"テクスチャファイル '{texturePath}' が見つかりません")
        
        # テクスチャタイプの確認
        valid_types = ['color', 'normal', 'roughness', 'metallic', 'specular', 'bump', 'displacement']
        if textureType.lower() not in valid_types:
            return self.error_response(f"無効なテクスチャタイプ: {textureType}。許可されるタイプ: {', '.join(valid_types)}")
        
        # ノード使用を有効化
        if not material.use_nodes:
            material.use_nodes = True
        
        # ノードツリーの取得
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        # 既存の画像をロードするか新しい画像をロード
        img_name = os.path.basename(texturePath)
        image = None
        
        # 同じパスの既存画像を検索
        for img in bpy.data.images:
            if img.filepath == texturePath:
                image = img
                break
        
        # 見つからなければ新しくロード
        if not image:
            image = bpy.data.images.load(texturePath)
        
        # テクスチャノードを作成
        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.image = image
        tex_node.location = (-300, 300)
        
        # プリンシプルBSDFノードを検索
        principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not principled:
            return self.error_response("マテリアルにプリンシプルBSDFノードが見つかりません")
        
        # テクスチャタイプに基づいて接続
        if textureType.lower() == 'color':
            links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
        elif textureType.lower() == 'normal':
            # 法線マップノードを作成
            normal_map = nodes.new(type='ShaderNodeNormalMap')
            normal_map.location = (-100, 200)
            links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
        elif textureType.lower() == 'roughness':
            links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
        elif textureType.lower() == 'metallic':
            links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
        elif textureType.lower() == 'specular':
            links.new(tex_node.outputs['Color'], principled.inputs['Specular'])
        elif textureType.lower() in ['bump', 'displacement']:
            # バンプマップノードを作成
            bump = nodes.new(type='ShaderNodeBump')
            bump.location = (-100, 100)
            links.new(tex_node.outputs['Color'], bump.inputs['Height'])
            links.new(bump.outputs['Normal'], principled.inputs['Normal'])
        
        return self.success_response(
            f"テクスチャ '{img_name}' をマテリアル '{materialName}' に追加しました",
            {'material': self._get_material_data(material)}
        )
