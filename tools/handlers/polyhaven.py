"""
Polyhaven関連のGraphQLリゾルバを提供
外部のPolyhaven APIと連携してアセットを検索・インポートする機能
"""

import bpy
import os
import json
import math
import logging
import tempfile
import shutil
from urllib import request, error
from typing import Dict, List, Any, Optional, Union
from .base import ResolverBase, handle_exceptions

class PolyhavenResolver(ResolverBase):
    """Polyhaven関連のGraphQLリゾルバクラス"""
    
    def __init__(self):
        super().__init__()
        self.base_api_url = "https://api.polyhaven.com"
        self.cdn_url = "https://cdn.polyhaven.com"
    
    @handle_exceptions
    def search(self, obj, info, query: Optional[str] = None, category: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Polyhavenアセットを検索
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            query: 検索キーワード
            category: カテゴリフィルタ (textures, hdris, models)
            limit: 取得件数制限
            
        Returns:
            Dict: 検索結果
        """
        self.logger.debug(f"search_polyhaven リゾルバが呼び出されました: query={query}, category={category}")
        
        # Polyhaven APIのURLを構築
        url = f"{self.base_api_url}/assets"
        
        # リクエストを実行
        try:
            with request.urlopen(url) as response:
                if response.status != 200:
                    return self.error_response(f"Polyhaven API エラー: ステータスコード {response.status}")
                
                # レスポンスをJSONとして解析
                data = json.loads(response.read().decode('utf-8'))
                
                # 検索結果をフィルタリング
                filtered_assets = []
                
                for asset_id, asset_info in data.items():
                    # カテゴリでフィルタリング
                    if category and asset_info.get('categories', []) and category not in asset_info.get('categories', []):
                        continue
                    
                    # キーワードでフィルタリング
                    if query:
                        query_lower = query.lower()
                        name_match = query_lower in asset_id.lower()
                        tag_match = any(query_lower in tag.lower() for tag in asset_info.get('tags', []))
                        category_match = any(query_lower in cat.lower() for cat in asset_info.get('categories', []))
                        
                        if not (name_match or tag_match or category_match):
                            continue
                    
                    # アセットタイプを決定
                    asset_type = None
                    if 'hdri' in asset_info.get('categories', []):
                        asset_type = 'hdri'
                    elif 'model' in asset_info.get('categories', []):
                        asset_type = 'model'
                    elif 'texture' in asset_info.get('categories', []):
                        asset_type = 'texture'
                    else:
                        asset_type = 'other'
                    
                    # サムネイルURLを構築
                    thumbnail_url = f"{self.cdn_url}/asset_img/thumbs/{asset_id}.png?height=256"
                    
                    # 結果に追加
                    filtered_assets.append({
                        'id': asset_id,
                        'name': asset_id.replace('_', ' ').title(),
                        'type': asset_type,
                        'categories': asset_info.get('categories', []),
                        'tags': asset_info.get('tags', []),
                        'downloadUrl': f"{self.base_api_url}/files/{asset_id}",
                        'thumbnailUrl': thumbnail_url
                    })
                    
                    # 制限に達したら終了
                    if len(filtered_assets) >= limit:
                        break
                
                # 結果を返す
                return {
                    'assets': filtered_assets,
                    'total': len(filtered_assets)
                }
                
        except error.HTTPError as e:
            self.logger.error(f"HTTP エラー: {e}")
            return self.error_response(f"Polyhaven API HTTPエラー: {e}")
        except error.URLError as e:
            self.logger.error(f"URL エラー: {e}")
            return self.error_response(f"Polyhaven API 接続エラー: {e}")
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析エラー: {e}")
            return self.error_response(f"Polyhaven API レスポンス解析エラー: {e}")
        except Exception as e:
            self.logger.error(f"Polyhaven API エラー: {e}")
            return self.error_response(f"Polyhavenアセット検索中にエラーが発生しました: {e}")
    
    @handle_exceptions
    def import_asset(self, obj, info, assetId: str, assetType: str, resolution: str = '2k') -> Dict[str, Any]:
        """
        Polyhavenアセットをインポート
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            assetId: アセットID
            assetType: アセットタイプ (texture, hdri, model)
            resolution: 解像度 (1k, 2k, 4k, 8k等)
            
        Returns:
            Dict: インポート結果
        """
        self.logger.debug(f"import_polyhaven_asset リゾルバが呼び出されました: id={assetId}, type={assetType}, resolution={resolution}")
        
        # アセットタイプの検証
        valid_types = ['texture', 'hdri', 'model']
        if assetType.lower() not in valid_types:
            return self.error_response(f"無効なアセットタイプ: {assetType}。許可されるタイプ: {', '.join(valid_types)}")
        
        # 解像度の検証
        valid_resolutions = ['1k', '2k', '4k', '8k']
        if resolution.lower() not in valid_resolutions:
            return self.error_response(f"無効な解像度: {resolution}。許可される解像度: {', '.join(valid_resolutions)}")
        
        # 一時ディレクトリを作成
        temp_dir = tempfile.mkdtemp()
        
        try:
            # アセット情報を取得
            asset_info_url = f"{self.base_api_url}/assets/{assetId}"
            with request.urlopen(asset_info_url) as response:
                if response.status != 200:
                    return self.error_response(f"アセット情報取得エラー: ステータスコード {response.status}")
                
                asset_info = json.loads(response.read().decode('utf-8'))
            
            # アセットタイプに応じたインポート処理
            if assetType.lower() == 'hdri':
                return self._import_hdri(asset_info, assetId, resolution, temp_dir)
            elif assetType.lower() == 'model':
                return self._import_model(asset_info, assetId, resolution, temp_dir)
            elif assetType.lower() == 'texture':
                return self._import_texture(asset_info, assetId, resolution, temp_dir)
            
        except Exception as e:
            self.logger.error(f"Polyhavenアセットインポートエラー: {e}")
            return self.error_response(f"Polyhavenアセットをインポート中にエラーが発生しました: {e}")
        
        finally:
            # 一時ディレクトリを削除
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                self.logger.warning(f"一時ディレクトリ削除エラー: {e}")
    
    def _import_hdri(self, asset_info: Dict[str, Any], asset_id: str, resolution: str, temp_dir: str) -> Dict[str, Any]:
        """
        PolyhavenからHDRIをインポート
        
        Args:
            asset_info: アセット情報
            asset_id: アセットID
            resolution: 解像度
            temp_dir: 一時ディレクトリパス
            
        Returns:
            Dict: インポート結果
        """
        # HDRIファイルのURLを取得
        files_url = f"{self.base_api_url}/files/{asset_id}"
        with request.urlopen(files_url) as response:
            files_info = json.loads(response.read().decode('utf-8'))
        
        # HDRIファイルの選択（指定解像度または利用可能な最高解像度）
        hdri_url = None
        hdri_res = None
        
        if 'hdri' in files_info:
            hdri_files = files_info['hdri']
            
            # 指定解像度が利用可能かチェック
            if resolution in hdri_files:
                hdri_url = hdri_files[resolution]['url']
                hdri_res = resolution
            else:
                # 利用可能な解像度を数値順にソート
                avail_res = sorted(hdri_files.keys(), key=lambda x: int(x[:-1]), reverse=True)
                if avail_res:
                    hdri_res = avail_res[0]
                    hdri_url = hdri_files[hdri_res]['url']
        
        if not hdri_url:
            return self.error_response(f"HDRI '{asset_id}' の利用可能なファイルが見つかりません")
        
        # HDRIファイルをダウンロード
        hdri_path = os.path.join(temp_dir, f"{asset_id}_{hdri_res}.hdr")
        try:
            request.urlretrieve(hdri_url, hdri_path)
        except Exception as e:
            return self.error_response(f"HDRIファイルのダウンロードに失敗しました: {e}")
        
        # Blenderにインポート
        try:
            # 既存のHDRIを検索
            hdri_name = f"{asset_id}_{hdri_res}"
            existing_img = None
            for img in bpy.data.images:
                if img.name == hdri_name or img.name == f"{hdri_name}.hdr":
                    existing_img = img
                    break
            
            # 既存のHDRIがなければロード
            if not existing_img:
                hdri_img = bpy.data.images.load(hdri_path)
                hdri_img.name = hdri_name
            else:
                # 既存のHDRIを更新
                existing_img.filepath = hdri_path
                existing_img.reload()
                hdri_img = existing_img
            
            # World設定を更新
            if not bpy.context.scene.world:
                bpy.context.scene.world = bpy.data.worlds.new("World")
            
            world = bpy.context.scene.world
            world.use_nodes = True
            nodes = world.node_tree.nodes
            links = world.node_tree.links
            
            # ノードをクリア
            nodes.clear()
            
            # 環境テクスチャノードを追加
            env_tex = nodes.new(type='ShaderNodeTexEnvironment')
            env_tex.image = hdri_img
            env_tex.location = (-300, 0)
            
            # バックグラウンドノードを追加
            background = nodes.new(type='ShaderNodeBackground')
            background.location = (0, 0)
            
            # ワールドアウトプットノードを追加
            output = nodes.new(type='ShaderNodeOutputWorld')
            output.location = (300, 0)
            
            # ノードを接続
            links.new(env_tex.outputs['Color'], background.inputs['Color'])
            links.new(background.outputs['Background'], output.inputs['Surface'])
            
            # 結果を返す
            return self.success_response(
                f"HDRI '{asset_id}' をインポートしました（解像度: {hdri_res}）",
                {
                    'assetInfo': {
                        'name': asset_id,
                        'type': 'hdri',
                        'resolution': hdri_res,
                        'path': hdri_path
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"HDRIインポートエラー: {e}")
            return self.error_response(f"HDRIのインポート中にエラーが発生しました: {e}")
    
    def _import_texture(self, asset_info: Dict[str, Any], asset_id: str, resolution: str, temp_dir: str) -> Dict[str, Any]:
        """
        Polyhavenからテクスチャをインポート
        
        Args:
            asset_info: アセット情報
            asset_id: アセットID
            resolution: 解像度
            temp_dir: 一時ディレクトリパス
            
        Returns:
            Dict: インポート結果
        """
        # テクスチャファイルのURLを取得
        texture_files_url = f"{self.base_api_url}/files/{asset_id}"
        with request.urlopen(texture_files_url) as response:
            files_info = json.loads(response.read().decode('utf-8'))
        
        # テクスチャマップの種類
        map_types = ['diffuse', 'albedo', 'ao', 'bump', 'displacement', 
                     'normal', 'normal_gl', 'roughness', 'metalness', 'specular']
        
        # テクスチャマップをダウンロード
        texture_maps = {}
        
        for map_type in map_types:
            if map_type in files_info:
                map_files = files_info[map_type]
                
                # 指定解像度が利用可能かチェック
                map_url = None
                map_res = None
                
                if resolution in map_files:
                    map_url = map_files[resolution]['url']
                    map_res = resolution
                else:
                    # 利用可能な解像度を数値順にソート
                    avail_res = sorted(map_files.keys(), key=lambda x: int(x[:-1]), reverse=True)
                    if avail_res:
                        map_res = avail_res[0]
                        map_url = map_files[map_res]['url']
                
                if map_url:
                    # テクスチャファイルをダウンロード
                    map_path = os.path.join(temp_dir, f"{asset_id}_{map_type}_{map_res}.jpg")
                    try:
                        request.urlretrieve(map_url, map_path)
                        texture_maps[map_type] = {
                            'path': map_path,
                            'resolution': map_res
                        }
                    except Exception as e:
                        self.logger.warning(f"{map_type}マップのダウンロードに失敗しました: {e}")
        
        if not texture_maps:
            return self.error_response(f"テクスチャ '{asset_id}' の利用可能なマップが見つかりません")
        
        # Blenderにインポート
        try:
            # 新しいマテリアルを作成
            material_name = f"PH_{asset_id}".replace(" ", "_")
            
            # 既存のマテリアルをチェック
            if material_name in bpy.data.materials:
                material = bpy.data.materials[material_name]
            else:
                material = bpy.data.materials.new(name=material_name)
            
            material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            
            # 既存のノードをクリア
            nodes.clear()
            
            # プリンシプルBSDFノードを作成
            principled = nodes.new(type='ShaderNodeBsdfPrincipled')
            principled.location = (0, 0)
            
            # マテリアル出力ノードを作成
            output = nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (300, 0)
            
            # プリンシプルBSDFとマテリアル出力を接続
            links.new(principled.outputs[0], output.inputs[0])
            
            # テクスチャマップをロードして接続
            loaded_maps = {}
            node_offset = -300
            
            # 優先順位に基づいてテクスチャマップを処理
            # まずベースカラー（アルベド/ディフューズ）
            base_color_map = None
            if 'albedo' in texture_maps:
                base_color_map = 'albedo'
            elif 'diffuse' in texture_maps:
                base_color_map = 'diffuse'
            
            if base_color_map:
                map_info = texture_maps[base_color_map]
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (-600, node_offset)
                node_offset -= 300
                
                # 画像をロード
                map_name = f"{asset_id}_{base_color_map}_{map_info['resolution']}"
                img = bpy.data.images.load(map_info['path'])
                img.name = map_name
                tex_node.image = img
                
                # ノードを接続
                links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                
                loaded_maps[base_color_map] = tex_node
            
            # 法線マップ
            normal_map_type = None
            if 'normal' in texture_maps:
                normal_map_type = 'normal'
            elif 'normal_gl' in texture_maps:
                normal_map_type = 'normal_gl'
            
            if normal_map_type:
                map_info = texture_maps[normal_map_type]
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (-600, node_offset)
                node_offset -= 300
                
                # 画像をロード
                map_name = f"{asset_id}_{normal_map_type}_{map_info['resolution']}"
                img = bpy.data.images.load(map_info['path'])
                img.name = map_name
                tex_node.image = img
                
                # 法線マップノードを作成
                normal_map_node = nodes.new(type='ShaderNodeNormalMap')
                normal_map_node.location = (-300, node_offset + 150)
                
                # ノードを接続
                links.new(tex_node.outputs['Color'], normal_map_node.inputs['Color'])
                links.new(normal_map_node.outputs['Normal'], principled.inputs['Normal'])
                
                loaded_maps[normal_map_type] = tex_node
            
            # 粗さマップ
            if 'roughness' in texture_maps:
                map_info = texture_maps['roughness']
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (-600, node_offset)
                node_offset -= 300
                
                # 画像をロード
                map_name = f"{asset_id}_roughness_{map_info['resolution']}"
                img = bpy.data.images.load(map_info['path'])
                img.name = map_name
                tex_node.image = img
                
                # カラースペース設定
                tex_node.image.colorspace_settings.name = 'Non-Color'
                
                # ノードを接続
                links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
                
                loaded_maps['roughness'] = tex_node
            
            # 金属度マップ
            if 'metalness' in texture_maps:
                map_info = texture_maps['metalness']
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (-600, node_offset)
                node_offset -= 300
                
                # 画像をロード
                map_name = f"{asset_id}_metalness_{map_info['resolution']}"
                img = bpy.data.images.load(map_info['path'])
                img.name = map_name
                tex_node.image = img
                
                # カラースペース設定
                tex_node.image.colorspace_settings.name = 'Non-Color'
                
                # ノードを接続
                links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
                
                loaded_maps['metalness'] = tex_node
            
            # ディスプレイスメントマップ
            displacement_map_type = None
            if 'displacement' in texture_maps:
                displacement_map_type = 'displacement'
            elif 'bump' in texture_maps:
                displacement_map_type = 'bump'
            
            if displacement_map_type:
                map_info = texture_maps[displacement_map_type]
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (-600, node_offset)
                
                # 画像をロード
                map_name = f"{asset_id}_{displacement_map_type}_{map_info['resolution']}"
                img = bpy.data.images.load(map_info['path'])
                img.name = map_name
                tex_node.image = img
                
                # カラースペース設定
                tex_node.image.colorspace_settings.name = 'Non-Color'
                
                # ディスプレイスメントまたはバンプノードを作成
                if displacement_map_type == 'displacement':
                    disp_node = nodes.new(type='ShaderNodeDisplacement')
                    disp_node.location = (-300, node_offset)
                    
                    # ノードを接続
                    links.new(tex_node.outputs['Color'], disp_node.inputs['Height'])
                    links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])
                else:  # bump
                    bump_node = nodes.new(type='ShaderNodeBump')
                    bump_node.location = (-300, node_offset)
                    
                    # ノードを接続
                    links.new(tex_node.outputs['Color'], bump_node.inputs['Height'])
                    links.new(bump_node.outputs['Normal'], principled.inputs['Normal'])
                
                loaded_maps[displacement_map_type] = tex_node
            
            # テクスチャマッピングノードを追加
            mapping_node = nodes.new(type='ShaderNodeMapping')
            mapping_node.location = (-900, 0)
            
            tex_coord_node = nodes.new(type='ShaderNodeTexCoord')
            tex_coord_node.location = (-1100, 0)
            
            # すべてのテクスチャノードをマッピングノードに接続
            for tex_node in loaded_maps.values():
                links.new(mapping_node.outputs['Vector'], tex_node.inputs['Vector'])
                links.new(tex_coord_node.outputs['UV'], mapping_node.inputs['Vector'])
            
            # 結果を返す
            return self.success_response(
                f"テクスチャ '{asset_id}' をマテリアル '{material_name}' としてインポートしました",
                {
                    'assetInfo': {
                        'name': asset_id,
                        'type': 'texture',
                        'material': material_name,
                        'maps': list(loaded_maps.keys())
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"テクスチャインポートエラー: {e}")
            return self.error_response(f"テクスチャのインポート中にエラーが発生しました: {e}")
    
    def _import_model(self, asset_info: Dict[str, Any], asset_id: str, resolution: str, temp_dir: str) -> Dict[str, Any]:
        """
        Polyhavenからモデルをインポート
        
        Args:
            asset_info: アセット情報
            asset_id: アセットID
            resolution: 解像度
            temp_dir: 一時ディレクトリパス
            
        Returns:
            Dict: インポート結果
        """
        # モデルファイルのURLを取得
        files_url = f"{self.base_api_url}/files/{asset_id}"
        with request.urlopen(files_url) as response:
            files_info = json.loads(response.read().decode('utf-8'))
        
        # OBJファイルを検索
        obj_url = None
        if 'blend' in files_info:
            # .blendファイルが優先
            if 'blend' in files_info['blend']:
                obj_url = files_info['blend']['blend']['url']
                model_format = 'blend'
        
        if not obj_url and 'obj' in files_info:
            # OBJファイル
            if 'obj' in files_info['obj']:
                obj_url = files_info['obj']['obj']['url']
                model_format = 'obj'
        
        if not obj_url:
            return self.error_response(f"モデル '{asset_id}' の利用可能なファイルが見つかりません")
        
        # モデルファイルをダウンロード
        model_path = os.path.join(temp_dir, f"{asset_id}.{model_format}")
        try:
            request.urlretrieve(obj_url, model_path)
        except Exception as e:
            return self.error_response(f"モデルファイルのダウンロードに失敗しました: {e}")
        
        # テクスチャもある場合はそれも取得
        texture_result = None
        if 'has_textures' in asset_info and asset_info['has_textures']:
            texture_result = self._import_texture(asset_info, asset_id, resolution, temp_dir)
        
        # Blenderにインポート
        try:
            if model_format == 'blend':
                # .blendファイルの場合
                with bpy.data.libraries.load(model_path, link=False) as (data_from, data_to):
                    data_to.objects = data_from.objects
                
                # インポートしたオブジェクトをシーンに追加
                for obj in data_to.objects:
                    if obj is not None:
                        bpy.context.collection.objects.link(obj)
                
            elif model_format == 'obj':
                # OBJファイルの場合
                bpy.ops.import_scene.obj(filepath=model_path)
            
            # インポートしたオブジェクトの検索
            imported_objects = []
            for obj in bpy.context.selected_objects:
                if obj.type == 'MESH':
                    imported_objects.append(obj.name)
            
            # マテリアルが取得できていれば、オブジェクトに割り当て
            if texture_result and 'assetInfo' in texture_result and texture_result['assetInfo'].get('material'):
                material_name = texture_result['assetInfo']['material']
                if material_name in bpy.data.materials:
                    material = bpy.data.materials[material_name]
                    
                    for obj_name in imported_objects:
                        obj = bpy.data.objects[obj_name]
                        if len(obj.material_slots) == 0:
                            obj.data.materials.append(material)
                        else:
                            obj.material_slots[0].material = material
            
            # 結果を返す
            return self.success_response(
                f"モデル '{asset_id}' をインポートしました",
                {
                    'assetInfo': {
                        'name': asset_id,
                        'type': 'model',
                        'format': model_format,
                        'path': model_path,
                        'objects': imported_objects
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"モデルインポートエラー: {e}")
            return self.error_response(f"モデルのインポート中にエラーが発生しました: {e}")
