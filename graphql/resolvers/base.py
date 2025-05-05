"""
リゾルバの基本クラスと共通ユーティリティを提供するモジュール
"""

import bpy
import logging
import traceback
import functools
from typing import Dict, List, Any, Optional, Union, Callable
import math

# ロガー初期化
logger = logging.getLogger("blender_json_mcp.graphql.resolvers.base")

def create_success_response(message: str = None, data: Any = None) -> Dict[str, Any]:
    """
    成功レスポンスを生成
    
    Args:
        message: 成功メッセージ
        data: 付加データ
    
    Returns:
        Dict: 成功レスポンス
    """
    response = {'success': True}
    
    if message:
        response['message'] = message
    
    if data:
        if isinstance(data, dict):
            response.update(data)
        else:
            response['data'] = data
    
    return response

def create_error_response(message: str, details: Any = None) -> Dict[str, Any]:
    """
    エラーレスポンスを生成
    
    Args:
        message: エラーメッセージ
        details: 詳細情報
        
    Returns:
        Dict: エラーレスポンス
    """
    response = {
        'success': False,
        'message': message
    }
    
    if details:
        response['details'] = details
    
    return response

def handle_exceptions(func: Callable) -> Callable:
    """
    例外を適切に処理するデコレータ
    
    Args:
        func: デコレートする関数
        
    Returns:
        Callable: 例外ハンドリングされた関数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"リゾルバエラー {func.__name__}: {str(e)}")
            logger.debug(traceback.format_exc())
            return create_error_response(f"処理エラー: {str(e)}")
    return wrapper

def vector_to_dict(vec) -> Dict[str, float]:
    """
    Blenderベクトルを辞書に変換
    
    Args:
        vec: ベクトル
        
    Returns:
        Dict: {x, y, z} 形式の辞書
    """
    return {'x': vec[0], 'y': vec[1], 'z': vec[2] if len(vec) > 2 else 0.0}

def dict_to_vector(vec_dict) -> List[float]:
    """
    辞書をベクトルリストに変換
    
    Args:
        vec_dict: ベクトル辞書
        
    Returns:
        List[float]: [x, y, z] 形式のリスト
    """
    if not vec_dict:
        return None
    return [vec_dict.get('x', 0.0), vec_dict.get('y', 0.0), vec_dict.get('z', 0.0)]

def degrees_to_radians(degrees: List[float]) -> List[float]:
    """
    度数法から弧度法へ変換
    
    Args:
        degrees: 度数法の角度リスト
        
    Returns:
        List[float]: 弧度法の角度リスト
    """
    return [math.radians(deg) for deg in degrees]

def radians_to_degrees(radians: List[float]) -> List[float]:
    """
    弧度法から度数法へ変換
    
    Args:
        radians: 弧度法の角度リスト
        
    Returns:
        List[float]: 度数法の角度リスト
    """
    return [math.degrees(rad) for rad in radians]

def ensure_object_exists(name: str) -> Optional[bpy.types.Object]:
    """
    指定された名前のオブジェクトが存在するか確認
    
    Args:
        name: オブジェクト名
        
    Returns:
        bpy.types.Object or None: 見つかったオブジェクトまたはNone
    """
    return bpy.data.objects.get(name)

def ensure_material_exists(name: str) -> Optional[bpy.types.Material]:
    """
    指定された名前のマテリアルが存在するか確認
    
    Args:
        name: マテリアル名
        
    Returns:
        bpy.types.Material or None: 見つかったマテリアルまたはNone
    """
    return bpy.data.materials.get(name)

class ResolverBase:
    """
    全リゾルバの基本クラス
    リゾルバ共通の基本機能を提供
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"blender_json_mcp.graphql.resolvers.{self.__class__.__name__}")
        self.logger.debug(f"リゾルバ初期化: {self.__class__.__name__}")
    
    @staticmethod
    def success_response(message: str = None, data: Any = None) -> Dict[str, Any]:
        """成功レスポンスを生成"""
        return create_success_response(message, data)
    
    @staticmethod
    def error_response(message: str, details: Any = None) -> Dict[str, Any]:
        """エラーレスポンスを生成"""
        return create_error_response(message, details)
    
    @staticmethod
    def vector_to_dict(vec) -> Dict[str, float]:
        """ベクトルを辞書に変換"""
        return vector_to_dict(vec)
    
    @staticmethod
    def dict_to_vector(vec_dict) -> List[float]:
        """辞書をベクトルに変換"""
        return dict_to_vector(vec_dict)
