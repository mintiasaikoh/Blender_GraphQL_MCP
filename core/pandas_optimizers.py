"""
Pandas最適化モジュール
データ処理とバッチ操作を高速化するためのPandasベースの関数
"""

import pandas as pd
import numpy as np
import bpy
import time
import logging
import json
from collections import defaultdict

logger = logging.getLogger("blender_graphql_mcp.pandas_optimizers")

def batch_object_properties(query_params=None):
    """複数オブジェクトのプロパティを効率的に取得
    
    Args:
        query_params: クエリパラメータ (dict)
    
    Returns:
        dict: DataFrameから変換されたオブジェクトプロパティと統計情報
    """
    start_time = time.time()
    try:
        # オブジェクト情報をDataFrameに収集
        objects_data = []
        
        for obj in bpy.data.objects:
            obj_data = {
                'name': obj.name,
                'type': obj.type,
                'hide': obj.hide_get(),
                'location_x': float(obj.location.x),
                'location_y': float(obj.location.y),
                'location_z': float(obj.location.z),
                'scale_x': float(obj.scale.x),
                'scale_y': float(obj.scale.y),
                'scale_z': float(obj.scale.z),
                'rotation_x': float(obj.rotation_euler.x),
                'rotation_y': float(obj.rotation_euler.y),
                'rotation_z': float(obj.rotation_euler.z),
                'material_count': len(obj.material_slots),
                'parent': obj.parent.name if obj.parent else None
            }
            
            # メッシュタイプの場合は追加データを収集
            if obj.type == 'MESH' and obj.data:
                mesh_data = {
                    'vertices': len(obj.data.vertices),
                    'edges': len(obj.data.edges),
                    'faces': len(obj.data.polygons),
                    'has_custom_normals': obj.data.has_custom_normals
                }
                obj_data.update(mesh_data)
            else:
                # 非メッシュオブジェクトの場合はゼロで埋める
                obj_data.update({
                    'vertices': 0,
                    'edges': 0,
                    'faces': 0,
                    'has_custom_normals': False
                })
                
            objects_data.append(obj_data)
        
        # DataFrameに変換
        df = pd.DataFrame(objects_data)
        
        # クエリパラメータが提供されている場合はフィルタリング
        if query_params:
            # オブジェクトタイプでフィルタリング
            if 'type' in query_params:
                df = df[df['type'] == query_params['type']]
            
            # 頂点数でフィルタリング
            if 'min_vertices' in query_params:
                df = df[df['vertices'] >= query_params['min_vertices']]
                
            if 'max_vertices' in query_params:
                df = df[df['vertices'] <= query_params['max_vertices']]
            
            # マテリアルでフィルタリング
            if 'has_materials' in query_params and query_params['has_materials']:
                df = df[df['material_count'] > 0]
                
            # 位置でフィルタリング
            if 'location_range' in query_params:
                range_data = query_params['location_range']
                if 'x_min' in range_data:
                    df = df[df['location_x'] >= range_data['x_min']]
                if 'x_max' in range_data:
                    df = df[df['location_x'] <= range_data['x_max']]
                if 'y_min' in range_data:
                    df = df[df['location_y'] >= range_data['y_min']]
                if 'y_max' in range_data:
                    df = df[df['location_y'] <= range_data['y_max']]
                if 'z_min' in range_data:
                    df = df[df['location_z'] >= range_data['z_min']]
                if 'z_max' in range_data:
                    df = df[df['location_z'] <= range_data['z_max']]
        
        # 統計情報を計算
        stats = {
            'total_objects': len(df),
            'total_vertices': int(df['vertices'].sum()),
            'total_faces': int(df['faces'].sum()),
            'avg_vertices_per_object': float(df['vertices'].mean()) if len(df) > 0 else 0,
            'max_vertices': int(df['vertices'].max()) if len(df) > 0 else 0,
            'median_vertices': float(df['vertices'].median()) if len(df) > 0 else 0,
            'objects_by_type': df['type'].value_counts().to_dict(),
            'processing_time_ms': (time.time() - start_time) * 1000
        }
        
        # 最大頂点数を持つオブジェクト
        if not df.empty and df['vertices'].max() > 0:
            largest_obj_idx = df['vertices'].idxmax()
            stats['largest_object'] = {
                'name': df.loc[largest_obj_idx, 'name'],
                'vertices': int(df.loc[largest_obj_idx, 'vertices']),
                'faces': int(df.loc[largest_obj_idx, 'faces'])
            }
        
        # 位置の分布
        if len(df) > 0:
            location_stats = {
                'x': {
                    'min': float(df['location_x'].min()), 
                    'max': float(df['location_x'].max()),
                    'mean': float(df['location_x'].mean())
                },
                'y': {
                    'min': float(df['location_y'].min()), 
                    'max': float(df['location_y'].max()),
                    'mean': float(df['location_y'].mean())
                },
                'z': {
                    'min': float(df['location_z'].min()), 
                    'max': float(df['location_z'].max()),
                    'mean': float(df['location_z'].mean())
                }
            }
            stats['location_stats'] = location_stats
        
        # DataFrameから辞書リストに変換
        # Pythonネイティブ型に変換して戻す
        objects_result = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            
            # 位置、回転、スケールを再構成
            obj_transformed = {
                'name': row_dict['name'],
                'type': row_dict['type'],
                'hidden': bool(row_dict['hide']),
                'location': {
                    'x': row_dict['location_x'],
                    'y': row_dict['location_y'],
                    'z': row_dict['location_z']
                },
                'rotation': {
                    'x': row_dict['rotation_x'],
                    'y': row_dict['rotation_y'],
                    'z': row_dict['rotation_z']
                },
                'scale': {
                    'x': row_dict['scale_x'],
                    'y': row_dict['scale_y'],
                    'z': row_dict['scale_z']
                },
                'material_count': int(row_dict['material_count']),
                'parent': row_dict['parent']
            }
            
            # メッシュ情報があれば追加
            if row_dict.get('vertices', 0) > 0:
                obj_transformed['mesh'] = {
                    'vertices': int(row_dict['vertices']),
                    'edges': int(row_dict['edges']),
                    'faces': int(row_dict['faces']),
                    'has_custom_normals': bool(row_dict['has_custom_normals'])
                }
                
            objects_result.append(obj_transformed)
        
        # クエリパラメータで統計情報の有無を指定
        include_stats = query_params.get('include_stats', True) if query_params else True
        
        result = {
            'objects': objects_result,
            'processing_time_ms': (time.time() - start_time) * 1000
        }
        
        if include_stats:
            result['stats'] = stats
            
        logger.info(f"バッチオブジェクトプロパティ取得: {len(objects_result)}件, 処理時間: {time.time() - start_time:.4f}秒")
        return result
        
    except Exception as e:
        logger.error(f"バッチオブジェクトプロパティ取得中にエラー発生: {str(e)}")
        return {'error': str(e), 'objects': []}

def material_analysis():
    """マテリアル情報の高速分析
    
    Returns:
        dict: マテリアル分析結果
    """
    start_time = time.time()
    try:
        # マテリアルデータ収集
        materials_data = []
        
        for mat in bpy.data.materials:
            mat_data = {
                'name': mat.name,
                'is_grease_pencil': mat.is_grease_pencil,
                'use_nodes': mat.use_nodes,
                'use_backface_culling': mat.use_backface_culling,
                'blend_method': mat.blend_method,
                'shadow_method': mat.shadow_method,
                'alpha': float(mat.alpha),
                'diffuse_color': [float(c) for c in mat.diffuse_color],
                'metallic': float(mat.metallic),
                'roughness': float(mat.roughness),
                'users': mat.users,
                'node_tree_type': mat.node_tree.type if mat.node_tree else None,
                'node_count': len(mat.node_tree.nodes) if mat.node_tree else 0
            }
            materials_data.append(mat_data)
        
        # DataFrameに変換
        df = pd.DataFrame(materials_data)
        
        # マテリアルノード統計
        node_stats = defaultdict(int)
        input_output_stats = defaultdict(int)
        
        for mat in bpy.data.materials:
            if mat.node_tree and mat.use_nodes:
                for node in mat.node_tree.nodes:
                    node_stats[node.type] += 1
                    
                    # 入出力ソケット数も記録
                    n_inputs = len(node.inputs)
                    n_outputs = len(node.outputs)
                    input_output_stats[f"{node.type}_{n_inputs}in_{n_outputs}out"] += 1
        
        # 結果を生成
        result = {
            'total_materials': len(df),
            'unused_materials': int(df[df['users'] == 0].shape[0]),
            'node_based_materials': int(df[df['use_nodes'] == True].shape[0]),
            'avg_nodes_per_material': float(df['node_count'].mean()),
            'material_types': {
                'grease_pencil': int(df[df['is_grease_pencil'] == True].shape[0]),
                'regular': int(df[df['is_grease_pencil'] == False].shape[0])
            },
            'blend_methods': df['blend_method'].value_counts().to_dict(),
            'shadow_methods': df['shadow_method'].value_counts().to_dict(),
            'node_statistics': dict(node_stats),
            'materials': df.to_dict('records'),
            'processing_time_ms': (time.time() - start_time) * 1000
        }
        
        logger.info(f"マテリアル分析完了: {len(df)}マテリアル, 処理時間: {time.time() - start_time:.4f}秒")
        return result
        
    except Exception as e:
        logger.error(f"マテリアル分析中にエラー発生: {str(e)}")
        return {'error': str(e)}

def scene_hierarchy_analysis():
    """シーンの階層構造の高速分析
    
    Returns:
        dict: 階層構造分析結果
    """
    start_time = time.time()
    try:
        # オブジェクト情報収集
        objects_data = []
        
        for obj in bpy.data.objects:
            parent_name = obj.parent.name if obj.parent else None
            children_names = [child.name for child in obj.children]
            
            obj_data = {
                'name': obj.name,
                'type': obj.type,
                'parent': parent_name,
                'children_count': len(children_names),
                'collection_names': [coll.name for coll in obj.users_collection],
                'visible': obj.visible_get(),
                'depth': 0  # 後で計算
            }
            objects_data.append(obj_data)
        
        # DataFrameに変換
        df = pd.DataFrame(objects_data)
        
        # 階層の深さを計算
        # 親→子の関係辞書を作成
        parent_dict = df.set_index('name')['parent'].to_dict()
        
        # 各オブジェクトの階層深さを計算
        for i, row in df.iterrows():
            depth = 0
            current = row['name']
            
            # 親を辿って深さを計算
            while parent_dict.get(current) is not None:
                depth += 1
                current = parent_dict[current]
                
                # 循環参照の防止
                if depth > 100:  # 安全策
                    break
                    
            df.at[i, 'depth'] = depth
        
        # コレクション情報を収集
        collections_data = []
        
        for coll in bpy.data.collections:
            coll_data = {
                'name': coll.name,
                'objects_count': len(coll.objects),
                'children_count': len(coll.children),
                'parent_names': [parent.name for parent in coll.users_collection]
            }
            collections_data.append(coll_data)
            
        coll_df = pd.DataFrame(collections_data)
        
        # 階層統計情報を計算
        hierarchy_stats = {
            'max_depth': int(df['depth'].max()),
            'avg_depth': float(df['depth'].mean()),
            'depth_distribution': df['depth'].value_counts().to_dict(),
            'top_level_objects': int(df[df['parent'].isna()].shape[0]),
            'avg_children_per_object': float(df['children_count'].mean()),
            'max_children': int(df['children_count'].max()) if len(df) > 0 else 0
        }
        
        # 最も子オブジェクトが多いオブジェクト
        if not df.empty and df['children_count'].max() > 0:
            most_children_idx = df['children_count'].idxmax()
            hierarchy_stats['most_children_object'] = {
                'name': df.loc[most_children_idx, 'name'],
                'children_count': int(df.loc[most_children_idx, 'children_count'])
            }
        
        # コレクション統計
        collection_stats = {
            'total_collections': len(coll_df),
            'avg_objects_per_collection': float(coll_df['objects_count'].mean()) if len(coll_df) > 0 else 0,
            'max_objects_in_collection': int(coll_df['objects_count'].max()) if len(coll_df) > 0 else 0,
            'empty_collections': int(coll_df[coll_df['objects_count'] == 0].shape[0])
        }
        
        # 最もオブジェクトが多いコレクション
        if not coll_df.empty and coll_df['objects_count'].max() > 0:
            largest_coll_idx = coll_df['objects_count'].idxmax()
            collection_stats['largest_collection'] = {
                'name': coll_df.loc[largest_coll_idx, 'name'],
                'objects_count': int(coll_df.loc[largest_coll_idx, 'objects_count'])
            }
        
        # 結果を生成
        result = {
            'objects_count': len(df),
            'collections_count': len(coll_df),
            'hierarchy_stats': hierarchy_stats,
            'collection_stats': collection_stats,
            'objects_by_depth': df.groupby('depth').size().to_dict(),
            'objects_by_type': df['type'].value_counts().to_dict(),
            'processing_time_ms': (time.time() - start_time) * 1000
        }
        
        logger.info(f"シーン階層分析完了: {len(df)}オブジェクト, {len(coll_df)}コレクション, 処理時間: {time.time() - start_time:.4f}秒")
        return result
        
    except Exception as e:
        logger.error(f"シーン階層分析中にエラー発生: {str(e)}")
        return {'error': str(e)}

class BatchProcessor:
    """複数のオブジェクトに対する操作をバッチ処理する"""
    
    @staticmethod
    def batch_transform(transform_list):
        """複数オブジェクトの変換をバッチ処理
        
        Args:
            transform_list: 変換情報のリスト
                各項目は {'name': 'obj_name', 'location': [x,y,z], 'rotation': [x,y,z], 'scale': [x,y,z]}
                
        Returns:
            dict: 処理結果
        """
        start_time = time.time()
        try:
            # DataFrameに変換
            df = pd.DataFrame(transform_list)
            
            results = []
            success_count = 0
            error_count = 0
            
            # バッチ内の各オブジェクトを処理
            for _, row in df.iterrows():
                obj_name = row['name']
                try:
                    obj = bpy.data.objects.get(obj_name)
                    if not obj:
                        results.append({
                            'name': obj_name,
                            'success': False,
                            'error': 'Object not found'
                        })
                        error_count += 1
                        continue
                    
                    # 位置を設定
                    if 'location' in row and row['location'] is not None:
                        if isinstance(row['location'], list) and len(row['location']) == 3:
                            obj.location = row['location']
                    
                    # 回転を設定
                    if 'rotation' in row and row['rotation'] is not None:
                        if isinstance(row['rotation'], list) and len(row['rotation']) == 3:
                            obj.rotation_euler = row['rotation']
                    
                    # スケールを設定
                    if 'scale' in row and row['scale'] is not None:
                        if isinstance(row['scale'], list) and len(row['scale']) == 3:
                            obj.scale = row['scale']
                    
                    results.append({
                        'name': obj_name,
                        'success': True
                    })
                    success_count += 1
                    
                except Exception as e:
                    results.append({
                        'name': obj_name,
                        'success': False,
                        'error': str(e)
                    })
                    error_count += 1
            
            logger.info(f"バッチ変換完了: 成功={success_count}, 失敗={error_count}, 処理時間: {time.time() - start_time:.4f}秒")
            return {
                'success': error_count == 0,
                'results': results,
                'success_count': success_count,
                'error_count': error_count,
                'processing_time_ms': (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            logger.error(f"バッチ変換中にエラー発生: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    @staticmethod
    def batch_material_assign(material_assignments):
        """複数オブジェクトへのマテリアル割り当てをバッチ処理
        
        Args:
            material_assignments: 割り当て情報のリスト
                各項目は {'object': 'obj_name', 'material': 'mat_name', 'slot_index': 0}
                
        Returns:
            dict: 処理結果
        """
        start_time = time.time()
        try:
            # DataFrameに変換
            df = pd.DataFrame(material_assignments)
            
            results = []
            success_count = 0
            error_count = 0
            
            # バッチ内の各割り当てを処理
            for _, row in df.iterrows():
                obj_name = row['object']
                mat_name = row['material']
                slot_index = row.get('slot_index', 0)
                
                try:
                    obj = bpy.data.objects.get(obj_name)
                    if not obj:
                        results.append({
                            'object': obj_name,
                            'material': mat_name,
                            'success': False,
                            'error': 'Object not found'
                        })
                        error_count += 1
                        continue
                    
                    material = bpy.data.materials.get(mat_name)
                    if not material:
                        results.append({
                            'object': obj_name,
                            'material': mat_name,
                            'success': False,
                            'error': 'Material not found'
                        })
                        error_count += 1
                        continue
                    
                    # スロット数を確保
                    while len(obj.material_slots) <= slot_index:
                        obj.data.materials.append(None)
                    
                    # マテリアルを割り当て
                    obj.material_slots[slot_index].material = material
                    
                    results.append({
                        'object': obj_name,
                        'material': mat_name,
                        'success': True
                    })
                    success_count += 1
                    
                except Exception as e:
                    results.append({
                        'object': obj_name,
                        'material': mat_name,
                        'success': False,
                        'error': str(e)
                    })
                    error_count += 1
            
            logger.info(f"バッチマテリアル割り当て完了: 成功={success_count}, 失敗={error_count}, 処理時間: {time.time() - start_time:.4f}秒")
            return {
                'success': error_count == 0,
                'results': results,
                'success_count': success_count,
                'error_count': error_count,
                'processing_time_ms': (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            logger.error(f"バッチマテリアル割り当て中にエラー発生: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }