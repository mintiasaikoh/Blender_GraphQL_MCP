"""
Blender Unified MCP Advanced Utilities
高度なユーティリティ機能を提供するモジュール
"""

import bpy
import time
import traceback
import tempfile
import os
import logging
import json
import math
import uuid
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Set, Tuple
from functools import wraps, lru_cache
from contextlib import contextmanager
import threading

# 独自のロガーを作成
logger = logging.getLogger('unified_mcp.utils.advanced')

# 型定義
T = TypeVar('T')

# パフォーマンス計測機能
try:
    # シンプル化されたパフォーマンスモジュールをインポート
    from .performance import track_time as track_performance
    from .performance import time_operation as timed_operation
    from .performance import print_stats, get_stats, enable_tracking, disable_tracking, reset_stats
    
    PERFORMANCE_MODULE_AVAILABLE = True
    logger.info("パフォーマンス計測モジュールが利用可能です")
except ImportError:
    # パフォーマンスモジュールが利用できない場合はシンプルな実装を提供
    PERFORMANCE_MODULE_AVAILABLE = False
    logger.warning("パフォーマンス計測モジュールが読み込めないため、基本実装を使用します")
    
    # 最小限のパフォーマンス計測用デコレータ
    def track_performance(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = (time.time() - start_time) * 1000  # ミリ秒
                logger.debug(f"{func.__name__} 実行時間: {duration:.2f}ms")
        return wrapper
    
    # コンテキストマネージャ→シンプル版
    @contextmanager
    def timed_operation(name: str):
        start_time = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000  # ミリ秒
            logger.debug(f"{name} 実行時間: {duration:.2f}ms")
    
    # スタブ関数
    def print_stats(threshold_ms=0):
        logger.info("パフォーマンス統計機能は利用できません")
    
    def get_stats():
        return {}
    
    def enable_tracking():
        pass
    
    def disable_tracking():
        pass
    
    def reset_stats():
        pass

@contextmanager
def error_handling(operation_name: str, fallback_value=None, rollback_on_error=False):
    """エラーハンドリングのコンテキストマネージャ
    
    Args:
        operation_name: 実行中の操作の名前
        fallback_value: エラー時に返す値
        rollback_on_error: エラー時にBlendファイルをロールバックするかどうか
    """
    backup_path = None
    
    # バックアップの作成（ロールバックが有効な場合）
    if rollback_on_error:
        try:
            backup_fd, backup_path = tempfile.mkstemp(suffix='.blend')
            os.close(backup_fd)
            bpy.ops.wm.save_as_mainfile(filepath=backup_path, compress=True)
            logger.debug(f"バックアップを作成しました: {backup_path}")
        except Exception as e:
            logger.error(f"バックアップ作成エラー: {str(e)}")
            backup_path = None
    
    try:
        yield
    except Exception as e:
        logger.error(f"{operation_name}中にエラー発生: {str(e)}")
        logger.error(traceback.format_exc())
        
        # ロールバック処理
        if rollback_on_error and backup_path and os.path.exists(backup_path):
            try:
                logger.info(f"バックアップからロールバック中: {backup_path}")
                bpy.ops.wm.open_mainfile(filepath=backup_path)
            except Exception as rollback_err:
                logger.error(f"ロールバックエラー: {str(rollback_err)}")
        
        return fallback_value
    finally:
        # バックアップの削除
        if backup_path and os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except:
                pass

# キャッシュ機能
_memory_cache = {}
_cache_expiry = {}

def cached(expires_seconds=60):
    """関数の結果をキャッシュするデコレータ
    
    Args:
        expires_seconds: キャッシュの有効期間（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # キャッシュキーの作成
            key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # 現在時刻
            now = time.time()
            
            # キャッシュ確認
            if key in _memory_cache and key in _cache_expiry:
                if now < _cache_expiry[key]:
                    return _memory_cache[key]
            
            # 未キャッシュまたは期限切れの場合は実行
            result = func(*args, **kwargs)
            
            # 結果のキャッシュ
            _memory_cache[key] = result
            _cache_expiry[key] = now + expires_seconds
            
            return result
        return wrapper
    return decorator

def clear_all_caches():
    """すべてのキャッシュをクリア"""
    global _memory_cache, _cache_expiry
    _memory_cache.clear()
    _cache_expiry.clear()
    
    # LRUキャッシュを使用している関数のキャッシュもクリア
    for func_name in dir():
        func = globals().get(func_name)
        if hasattr(func, 'cache_clear') and callable(func.cache_clear):
            func.cache_clear()
    
    logger.info("すべてのキャッシュがクリアされました")

# 安全なファイル操作
def safe_read_json(filepath: str, default=None) -> Any:
    """安全にJSONファイルを読み込む
    
    Args:
        filepath: ファイルパス
        default: ファイルが存在しない場合やエラー時の戻り値
    
    Returns:
        JSONデータまたはデフォルト値
    """
    if not os.path.exists(filepath):
        return default
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSONファイル読み込みエラー {filepath}: {str(e)}")
        return default

def safe_write_json(filepath: str, data: Any, indent=2) -> bool:
    """安全にJSONファイルを書き込む
    
    Args:
        filepath: ファイルパス
        data: 書き込むデータ
        indent: インデント幅
    
    Returns:
        成功したかどうか
    """
    try:
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 一時ファイルに書き込み
        temp_filepath = filepath + ".tmp"
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        # 一時ファイルを正式なファイルに移動（アトミック操作）
        if os.path.exists(filepath):
            os.remove(filepath)
        os.rename(temp_filepath, filepath)
        
        return True
    except Exception as e:
        logger.error(f"JSONファイル書き込みエラー {filepath}: {str(e)}")
        return False

# 幾何学ユーティリティ
@lru_cache(maxsize=128)
def calculate_distance(point1: Tuple[float, float, float], point2: Tuple[float, float, float]) -> float:
    """二点間の距離を計算
    
    Args:
        point1: 点1の座標 (x, y, z)
        point2: 点2の座標 (x, y, z)
    
    Returns:
        二点間の距離
    """
    return math.sqrt(
        (point1[0] - point2[0]) ** 2 +
        (point1[1] - point2[1]) ** 2 +
        (point1[2] - point2[2]) ** 2
    )

@track_performance
def calculate_object_center(obj: bpy.types.Object) -> Tuple[float, float, float]:
    """オブジェクトの中心点を計算
    
    Args:
        obj: Blenderオブジェクト
    
    Returns:
        中心点の座標 (x, y, z)
    """
    if obj.type == 'MESH' and obj.data.vertices:
        # numpyなしでの実装
        verts_count = len(obj.data.vertices)
        if verts_count == 0:
            return tuple(obj.location)
        
        sum_x = sum_y = sum_z = 0.0
        for v in obj.data.vertices:
            sum_x += v.co.x
            sum_y += v.co.y
            sum_z += v.co.z
            
        return (sum_x/verts_count, sum_y/verts_count, sum_z/verts_count)
    else:
        # それ以外はオブジェクト位置を返す
        return tuple(obj.location)

@track_performance
def align_objects(target_obj: bpy.types.Object, reference_obj: bpy.types.Object, axes='XYZ') -> None:
    """ターゲットオブジェクトを参照オブジェクトに整列させる
    
    Args:
        target_obj: 移動するオブジェクト
        reference_obj: 参照するオブジェクト
        axes: 整列させる軸（'X', 'Y', 'Z'の組み合わせ）
    """
    if 'X' in axes:
        target_obj.location.x = reference_obj.location.x
    if 'Y' in axes:
        target_obj.location.y = reference_obj.location.y
    if 'Z' in axes:
        target_obj.location.z = reference_obj.location.z

# 高度なシーン情報
@cached(expires_seconds=10)
@track_performance
def analyze_scene_complexity() -> Dict[str, Any]:
    """シーンの複雑さを分析
    
    Returns:
        シーンの複雑さに関する情報
    """
    scene = bpy.context.scene
    result = {
        'object_count': len(scene.objects),
        'polygon_count': 0,
        'vertex_count': 0,
        'material_count': len(bpy.data.materials),
        'image_count': len(bpy.data.images),
        'largest_objects': [],
        'memory_usage_estimate_mb': 0
    }
    
    # オブジェクト情報を収集
    objects_data = []
    for obj in scene.objects:
        if obj.type == 'MESH' and obj.data:
            poly_count = len(obj.data.polygons)
            vert_count = len(obj.data.vertices)
            
            objects_data.append({
                'name': obj.name,
                'poly_count': poly_count,
                'vert_count': vert_count
            })
            
            result['polygon_count'] += poly_count
            result['vertex_count'] += vert_count
    
    # 最大のオブジェクトを抽出
    objects_data.sort(key=lambda x: x['poly_count'], reverse=True)
    result['largest_objects'] = objects_data[:5]  # 上位5つ
    
    # メモリ使用量の推定（非常に大雑把な見積もり）
    # 1つの頂点が約40バイト、1つのポリゴンが約60バイト程度を消費すると仮定
    vertex_memory = result['vertex_count'] * 40
    polygon_memory = result['polygon_count'] * 60
    material_memory = result['material_count'] * 10000  # マテリアルごとに約10KB
    
    # 画像メモリ
    image_memory = 0
    for img in bpy.data.images:
        if img.has_data:
            # RGBA各1バイトとして計算
            image_memory += img.size[0] * img.size[1] * 4
    
    total_memory = vertex_memory + polygon_memory + material_memory + image_memory
    result['memory_usage_estimate_mb'] = total_memory / (1024 * 1024)  # バイトからMBに変換
    
    return result

# モジュール登録関数
def register():
    """高度なユーティリティモジュールを登録"""
    logger.info("高度なユーティリティモジュールを登録しました")

def unregister():
    """高度なユーティリティモジュールの登録解除"""
    # キャッシュのクリーンアップ
    clear_all_caches()
    logger.info("高度なユーティリティモジュールを登録解除しました")
