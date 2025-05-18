"""
NumPy最適化モジュール
大規模メッシュ操作とデータ処理を高速化するためのNumPyベースの関数
"""

import numpy as np
import bpy
import time
import logging

logger = logging.getLogger("blender_graphql_mcp.numpy_optimizers")

def fast_vertex_transform(obj_name, transform_matrix):
    """NumPyを使用した高速頂点変換
    
    Args:
        obj_name: 対象オブジェクト名
        transform_matrix: 4x4変換行列（16要素の配列として渡す）
    
    Returns:
        bool: 処理の成功/失敗
    """
    start_time = time.time()
    try:
        obj = bpy.data.objects[obj_name]
        if not obj or obj.type != 'MESH':
            logger.warning(f"オブジェクト {obj_name} はメッシュではありません")
            return False
            
        mesh = obj.data
        
        # 頂点データをNumPy配列に変換
        vertices = np.zeros(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", vertices)
        vertices = vertices.reshape(len(mesh.vertices), 3)
        
        # NumPyで高速変換
        transform = np.array(transform_matrix, dtype=np.float32).reshape(4, 4)
        # 頂点に同次座標(w=1)を追加
        vertices_homogeneous = np.ones((len(vertices), 4), dtype=np.float32)
        vertices_homogeneous[:, 0:3] = vertices
        
        # 行列乗算による変換（非常に高速）
        transformed_vertices = np.dot(vertices_homogeneous, transform.T)[:, 0:3]
        
        # 変換結果をBlenderに戻す
        transformed_vertices = transformed_vertices.flatten()
        mesh.vertices.foreach_set("co", transformed_vertices)
        mesh.update()
        
        logger.info(f"頂点変換完了: {obj_name}, {len(mesh.vertices)}頂点, {time.time() - start_time:.4f}秒")
        return True
        
    except Exception as e:
        logger.error(f"頂点変換中にエラー発生: {str(e)}")
        return False

def fast_mesh_analysis(obj_name):
    """NumPyを使用したメッシュ分析の高速化
    
    Args:
        obj_name: 対象オブジェクト名
    
    Returns:
        dict: メッシュ分析結果
    """
    start_time = time.time()
    try:
        obj = bpy.data.objects[obj_name]
        if not obj or obj.type != 'MESH':
            logger.warning(f"オブジェクト {obj_name} はメッシュではありません")
            return {"error": "Not a mesh object"}
            
        mesh = obj.data
        
        # 頂点座標をNumPy配列として取得
        vertices = np.zeros(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", vertices)
        vertices = vertices.reshape(len(mesh.vertices), 3)
        
        # 面情報をNumPy配列として取得
        polygons = []
        for poly in mesh.polygons:
            vertices_indices = list(poly.vertices)
            polygons.append(vertices_indices)
        
        # NumPyで高速分析
        # 境界ボックス
        min_coords = np.min(vertices, axis=0)
        max_coords = np.max(vertices, axis=0)
        
        # 中心と寸法
        center = (min_coords + max_coords) / 2
        dimensions = max_coords - min_coords
        
        # 頂点間の距離
        # すべての頂点の重心からの距離を計算
        centroid = np.mean(vertices, axis=0)
        distances = np.linalg.norm(vertices - centroid, axis=1)
        avg_distance = np.mean(distances)
        max_distance = np.max(distances)
        
        # 結果をまとめる
        result = {
            "vertex_count": len(mesh.vertices),
            "face_count": len(mesh.polygons),
            "edge_count": len(mesh.edges),
            "bounds": {
                "min": min_coords.tolist(),
                "max": max_coords.tolist(),
                "center": center.tolist(),
                "dimensions": dimensions.tolist()
            },
            "vertex_stats": {
                "average_distance_from_center": float(avg_distance),
                "max_distance_from_center": float(max_distance)
            },
            "processing_time_ms": (time.time() - start_time) * 1000
        }
        
        logger.info(f"メッシュ分析完了: {obj_name}, 処理時間: {time.time() - start_time:.4f}秒")
        return result
        
    except Exception as e:
        logger.error(f"メッシュ分析中にエラー発生: {str(e)}")
        return {"error": str(e)}

def find_nearest_objects(origin, max_distance=5.0, obj_types=None):
    """指定位置から最も近いオブジェクトを高速に検索
    
    Args:
        origin: 原点座標 [x, y, z]
        max_distance: 検索最大距離
        obj_types: 対象オブジェクトタイプのリスト（Noneですべて）
    
    Returns:
        list: 距離順にソートされたオブジェクト情報
    """
    start_time = time.time()
    try:
        origin_np = np.array(origin, dtype=np.float32)
        
        # すべてのオブジェクトの位置をNumPy配列に
        objects = []
        positions = []
        
        for obj in bpy.data.objects:
            if obj_types and obj.type not in obj_types:
                continue
                
            objects.append(obj)
            positions.append([obj.location.x, obj.location.y, obj.location.z])
        
        # 対象がなければ空のリストを返す
        if not objects:
            return []
        
        # NumPyの高速ベクトル計算で距離を算出
        positions_np = np.array(positions, dtype=np.float32)
        distances = np.linalg.norm(positions_np - origin_np, axis=1)
        
        # 距離でフィルタリングしてソート
        mask = distances <= max_distance
        filtered_indices = np.where(mask)[0]
        filtered_distances = distances[mask]
        
        # 距離でソート
        sorted_indices = np.argsort(filtered_distances)
        result = []
        
        for idx in sorted_indices:
            obj_idx = filtered_indices[idx]
            obj = objects[obj_idx]
            dist = filtered_distances[idx]
            
            result.append({
                'name': obj.name,
                'type': obj.type,
                'distance': float(dist),
                'location': [float(obj.location.x), float(obj.location.y), float(obj.location.z)]
            })
        
        logger.info(f"最近傍オブジェクト検索完了: {len(result)}件, 処理時間: {time.time() - start_time:.4f}秒")
        return result
        
    except Exception as e:
        logger.error(f"最近傍オブジェクト検索中にエラー発生: {str(e)}")
        return []

def fast_raycast(origin, direction, max_distance=100.0):
    """NumPyを使用した高速レイキャスト
    
    Args:
        origin: レイの開始点 [x, y, z]
        direction: レイの方向 [x, y, z]
        max_distance: 最大検索距離
    
    Returns:
        dict: ヒット情報
    """
    start_time = time.time()
    try:
        # 方向ベクトルを正規化
        direction_np = np.array(direction, dtype=np.float32)
        direction_np = direction_np / np.linalg.norm(direction_np)
        
        # シーンのレイキャスト（Blender内部機能を使用）
        result, obj, matrix, location, normal = bpy.context.scene.ray_cast(
            bpy.context.view_layer.depsgraph,
            bpy.data.objects["Camera"].matrix_world.inverted() @ np.array(origin, dtype=np.float32),
            direction_np
        )
        
        if result:
            hit_info = {
                'hit': True,
                'object': obj.name if obj else None,
                'location': location.tolist() if location else None,
                'normal': normal.tolist() if normal else None,
                'distance': np.linalg.norm(np.array(location) - np.array(origin)) if location else None,
                'processing_time_ms': (time.time() - start_time) * 1000
            }
        else:
            hit_info = {
                'hit': False,
                'processing_time_ms': (time.time() - start_time) * 1000
            }
        
        logger.info(f"レイキャスト完了: ヒット={result}, 処理時間: {time.time() - start_time:.4f}秒")
        return hit_info
        
    except Exception as e:
        logger.error(f"レイキャスト中にエラー発生: {str(e)}")
        return {'hit': False, 'error': str(e)}

def batch_vertex_colors(obj_name, color_data, algorithm='mean'):
    """NumPyを使用した頂点カラーの一括設定
    
    Args:
        obj_name: 対象オブジェクト名
        color_data: 色データ (dict: vertex_index -> [r,g,b])
                   または関数 (位置を受け取り色を返す)
        algorithm: 補間アルゴリズム ('nearest', 'mean', 'weighted')
    
    Returns:
        bool: 処理の成功/失敗
    """
    start_time = time.time()
    try:
        obj = bpy.data.objects[obj_name]
        if not obj or obj.type != 'MESH':
            logger.warning(f"オブジェクト {obj_name} はメッシュではありません")
            return False
            
        mesh = obj.data
        
        # 頂点カラーレイヤーを取得または作成
        if not mesh.vertex_colors:
            mesh.vertex_colors.new()
        color_layer = mesh.vertex_colors.active
        
        # 頂点データを取得
        vertices = np.zeros(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", vertices)
        vertices = vertices.reshape(len(mesh.vertices), 3)
        
        # 結果の色データを準備
        if callable(color_data):
            # 関数が与えられた場合、各頂点の位置に適用
            colors = np.zeros((len(vertices), 3), dtype=np.float32)
            for i, vertex in enumerate(vertices):
                color = color_data(vertex)
                colors[i] = color
        elif isinstance(color_data, dict):
            # 辞書が与えられた場合、指定された頂点に色を設定
            colors = np.zeros((len(vertices), 3), dtype=np.float32)
            for idx, color in color_data.items():
                if 0 <= idx < len(vertices):
                    colors[idx] = color
                    
            # 残りの頂点の補間
            if algorithm == 'nearest' and len(color_data) > 0:
                # 最近傍補間
                known_indices = list(color_data.keys())
                known_colors = np.array([color_data[idx] for idx in known_indices])
                
                for i in range(len(vertices)):
                    if i not in color_data:
                        # 最も近い既知の頂点を探す
                        distances = np.linalg.norm(vertices[known_indices] - vertices[i], axis=1)
                        nearest_idx = known_indices[np.argmin(distances)]
                        colors[i] = color_data[nearest_idx]
                        
            elif algorithm == 'weighted' and len(color_data) > 0:
                # 距離加重補間
                known_indices = list(color_data.keys())
                for i in range(len(vertices)):
                    if i not in color_data:
                        distances = np.array([
                            np.linalg.norm(vertices[i] - vertices[idx]) 
                            for idx in known_indices
                        ])
                        # ゼロ除算を防ぐ
                        distances = np.maximum(distances, 1e-6)
                        weights = 1.0 / distances
                        weights = weights / np.sum(weights)  # 正規化
                        
                        # 加重平均
                        weighted_color = np.zeros(3, dtype=np.float32)
                        for j, idx in enumerate(known_indices):
                            weighted_color += weights[j] * np.array(color_data[idx])
                        
                        colors[i] = weighted_color
        else:
            # 無効な入力
            logger.error(f"無効な色データ形式: {type(color_data)}")
            return False
            
        # メッシュの各ループに色を設定
        i = 0
        for poly in mesh.polygons:
            for loop_idx in poly.loop_indices:
                vertex_idx = mesh.loops[loop_idx].vertex_index
                color_layer.data[loop_idx].color = (*colors[vertex_idx], 1.0)  # RGBA
                i += 1
        
        mesh.update()
        logger.info(f"頂点カラー設定完了: {obj_name}, {i}ループ, 処理時間: {time.time() - start_time:.4f}秒")
        return True
        
    except Exception as e:
        logger.error(f"頂点カラー設定中にエラー発生: {str(e)}")
        return False