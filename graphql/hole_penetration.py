"""
穴の貫通チェック機能のGraphQL拡張（最適化・エラーハンドリング強化版）
"""

import bpy
import logging
import mathutils
import time
import threading
import random
import math
import concurrent.futures
from typing import List, Dict, Any, Tuple, Optional, Callable

# グローバル変数
_hole_penetration_thread_pool = None
_cache = {}
_cache_lock = threading.RLock()

# ロギング設定
logger = logging.getLogger("blender.mcp.graphql.hole_penetration")

# タイムアウト管理クラス
class ExecutionTimeout:
    """処理のタイムアウトを管理するクラス
    withステートメントまたはcheck_timeout()メソッドで使用
    """
    
    def __init__(self, timeout_seconds, message=None):
        """
        Args:
            timeout_seconds: タイムアウト秒数
            message: タイムアウト時のエラーメッセージ
        """
        self.timeout_seconds = timeout_seconds
        self.message = message or f"処理が{timeout_seconds}秒を超えました"
        self.start_time = time.time()
        self.active = True
    
    def __enter__(self):
        """withステートメントの開始時に呼び出される"""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """withステートメントの終了時に呼び出される"""
        self.active = False
        return False  # 例外をキャッチしない
    
    def check_timeout(self):
        """タイムアウト確認を行うメソッド
        タイムアウト時にはTimeoutErrorを発生させる
        """
        if not self.active:
            return
            
        elapsed = time.time() - self.start_time
        if elapsed > self.timeout_seconds:
            logger.warning(f"処理がタイムアウトしました: {elapsed:.2f}秒 > {self.timeout_seconds}秒")
            self.active = False
            raise TimeoutError(self.message)
        return False
    
    @property
    def elapsed_time(self) -> float:
        """経過時間を取得
        
        Returns:
            経過時間（秒）
        """
        return time.time() - self.start_time

# キャッシュとスレッド管理
def clear_cache():
    """穴の貫通チェックの結果キャッシュをクリアする関数"""
    global _cache
    with _cache_lock:
        _cache.clear()
    logger.info("穴の貫通チェック用キャッシュをクリアしました")

def init_thread_pool(max_workers=4):
    """穴の貫通チェック用のスレッドプールを初期化する関数
    
    Args:
        max_workers: 最大スレッド数
    """
    global _hole_penetration_thread_pool
    if _hole_penetration_thread_pool is None:
        try:
            _hole_penetration_thread_pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="hole_penetration_worker"
            )
            logger.info(f"穴の貫通チェック用スレッドプールを初期化しました (最大スレッド数: {max_workers})")
        except Exception as e:
            logger.error(f"スレッドプールの初期化に失敗しました: {e}")
            _hole_penetration_thread_pool = None

# スキーマ拡張定義（より堅牢な型構造）
SCHEMA_EXTENSION = {
    'name': 'hole_penetration',
    'type_defs': """
    extend type Query {
        checkHolePenetration(
            objectName: String!, 
            positions: [Vector3Input!]!, 
            radius: Float = 0.5, 
            samples: Int = 10,
            timeout: Int = 30
        ): HolePenetrationResult!
    }
    
    input Vector3Input {
        x: Float!
        y: Float!
        z: Float!
    }
    
    type HolePenetrationResult {
        results: [PenetrationResult!]!
        success: Boolean!
        message: String
        executionTime: Float
    }
    
    type PenetrationResult {
        position: Vector3!
        isPenetrating: Boolean!
        penetrationRatio: Float!
        message: String
    }
    
    type Vector3 {
        x: Float!
        y: Float!
        z: Float!
    }
    """
}

def check_hole_penetration(
    object_name: str, 
    positions: List[Dict[str, float]], 
    radius: float = 0.5, 
    samples: int = 10,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    指定されたオブジェクトの特定位置で穴の貫通状態をチェック
    タイムアウト機能とエラーハンドリング強化版
    
    Args:
        object_name: 検査対象のオブジェクト名
        positions: チェック位置のリスト（x, y, z座標）
        radius: チェック円の半径
        samples: サンプリング数（多いほど精度が高い）
        timeout: 処理タイムアウト秒数
        
    Returns:
        貫通チェック結果を含むレスポンスオブジェクト
    """
    # 処理開始時間記録
    start_time = time.time()
    
    try:
        # タイムアウト監視付き処理
        with ExecutionTimeout(timeout, f"穴貫通チェック処理が{timeout}秒を超えました"):
            # 結果リスト
            results = []
            
            # エラーチェック: 入力制限
            if samples > 50:
                logger.warning(f"サンプル数が多すぎます。{samples} → 50に制限します")
                samples = 50
            
            if len(positions) > 20:
                logger.warning(f"チェック位置数が多すぎます。{len(positions)} → 20に制限します")
                positions = positions[:20]
            
            # オブジェクトの取得
            obj = bpy.data.objects.get(object_name)
            if not obj:
                logger.warning(f"オブジェクト '{object_name}' が見つかりません")
                return {
                    "results": [],
                    "success": False,
                    "message": f"オブジェクト '{object_name}' が見つかりません",
                    "executionTime": time.time() - start_time
                }
    
            # オブジェクトの境界ボックスから厚みを推定
            dimensions = obj.dimensions
            thickness_estimate = min(dimensions) / 4  # 最小寸法の1/4を厚みの推定値とする
            
            # サンプル点をずらす最大距離
            max_offset = radius * 0.8
            
            # 効率的なサンプリング用のオフセットを事前計算（球面分布）
            sample_offsets = []
            for _ in range(samples):
                # 球面上の均等分布サンプリング
                phi = random.uniform(0, 2 * 3.14159)  # 球面座標の方位角（地球の経度に相当）
                theta = random.uniform(0, 3.14159)  # 天頂角（地球の緯度に相当）
                
                # 球面座標からカーテシアン座標へ変換
                x = max_offset * math.sin(theta) * math.cos(phi)
                y = max_offset * math.sin(theta) * math.sin(phi)
                z = max_offset * math.cos(theta)
                
                sample_offsets.append((x, y, z))
    
            # 各位置ごとの処理を関数化
            def process_position(pos_idx):
                # タイムアウト確認
                timeout_ctx.check_timeout()
                
                pos = positions[pos_idx]
                position = mathutils.Vector((pos['x'], pos['y'], pos['z']))
                
                # チェック方向を決定
                center = obj.location
                direction_to_center = (center - position).normalized()
                direction_from_center = -direction_to_center
                
                # 貫通チェック用の変数
                penetration_count = 0
                issues = set()
                
                # サンプリング実行（バッチサイズを小さくして途中チェックを入れる）
                batch_size = 5  # バッチサイズを少なくして途中チェックを入れやすくする
                for batch_start in range(0, samples, batch_size):
                    # タイムアウト確認（バッチ毎）
                    timeout_ctx.check_timeout()
                    
                    batch_end = min(batch_start + batch_size, samples)
                    for i in range(batch_start, batch_end):
                        # サンプル位置へのオフセット適用
                        offset_vec = mathutils.Vector(sample_offsets[i])
                        sample_position = position + offset_vec
                        
                        # 内側から外側へのレイキャスト
                        hit_inside_out, _, _, _ = obj.ray_cast(sample_position, direction_from_center)
                        
                        # 外側から内側へのレイキャスト
                        outside_point = sample_position + direction_from_center * (thickness_estimate * 2)
                        hit_outside_in, _, _, _ = obj.ray_cast(outside_point, direction_to_center)
                        
                        # 両方のレイキャストがヒットしない = 穴が貫通している
                        if not hit_inside_out and not hit_outside_in:
                            penetration_count += 1
                        else:
                            if hit_inside_out:
                                issues.add("内側から外側")
                            if hit_outside_in:
                                issues.add("外側から内側")
                
                # 貫通率の計算
                penetration_ratio = penetration_count / samples if samples > 0 else 0
                
                # 結果を返す
                return {
                    'position': {
                        'x': position.x,
                        'y': position.y,
                        'z': position.z
                    },
                    'isPenetrating': penetration_ratio > 0.8,  # 80%以上のサンプルが貫通していれば穴とみなす
                    'penetrationRatio': penetration_ratio,
                    'message': ("完全に貫通しています" if penetration_ratio > 0.9 else
                              "ほぼ貫通しています" if penetration_ratio > 0.7 else
                              "部分的に貫通しています" if penetration_ratio > 0.3 else
                              f"貫通していません。問題: {', '.join(issues)}")
                }
            
            # タイムアウトコンテキストを保存
            timeout_ctx = ExecutionTimeout(timeout, f"穴貫通チェック処理が{timeout}秒を超えました")
            
            # 直列処理（マルチスレッドだとタイムアウト制御が難しいため）
            results = []
            for i in range(len(positions)):
                # 各位置での処理
                result = process_position(i)
                results.append(result)
                
                # 進捗ログ（4つずつ処理したらログ出力）
                if (i + 1) % 4 == 0 or i == len(positions) - 1:
                    logger.debug(f"穴貫通チェック進捗: {i+1}/{len(positions)} 位置完了")
            
            # 処理時間を計測
            end_time = time.time()
            execution_time = end_time - start_time
            logger.debug(f"穴貫通チェック処理時間: {execution_time:.4f}秒 ({len(positions)}位置, {samples}サンプル)")
            
            # 成功レスポンスを返す
            return {
                "results": results,
                "success": True,
                "message": f"穴貫通チェック処理が完了しました。{len(positions)}位置, {samples}サンプル",
                "executionTime": execution_time
            }
    
    except TimeoutError as e:
        # タイムアウトの場合
        logger.warning(f"穴貫通チェックタイムアウト: {str(e)}")
        return {
            "results": [],
            "success": False,
            "message": str(e),
            "executionTime": time.time() - start_time
        }
        
    except Exception as e:
        # その他の例外をキャッチ
        logger.error(f"穴貫通チェックエラー: {str(e)}")
        return {
            "results": [],
            "success": False,
            "message": f"エラーが発生しました: {str(e)}",
            "executionTime": time.time() - start_time
        }

# リゾルバ関数
def resolve_check_hole_penetration(root, info, **kwargs):
    """
    GraphQLリゾルバ: 穴の貫通チェック
    
    Args:
        root: 解決のルートオブジェクト
        info: GraphQLリクエスト情報オブジェクト
        **kwargs: クエリからの引数
            - objectName: チェック対象のオブジェクト名 (必須)
            - positions: チェック位置のリスト (必須)
            - radius: チェック円の半径 (デフォルト: 0.5)
            - samples: サンプリング数 (デフォルト: 10)
            - timeout: タイムアウト秒数 (デフォルト: 30)
    
    Returns:
        貫通チェック結果を含むレスポンスオブジェクト
    """
    try:
        # パラメータを取得
        object_name = kwargs.get('objectName')
        positions = kwargs.get('positions', [])
        radius = kwargs.get('radius', 0.5)
        samples = kwargs.get('samples', 10)
        timeout = kwargs.get('timeout', 30)
        
        # 入力パラメータのバリデーション
        if not object_name or not positions:
            logger.warning("無効な入力パラメータ")
            return {
                "results": [],
                "success": False,
                "message": "無効な入力パラメータが指定されました",
                "executionTime": 0
            }
        
        # Blenderコンテキスト情報を取得（必要な場合）
        context = getattr(info, 'context', {})
        blender_context = context.get('blender_context') if context else None
        
        # リクエスト情報をログに記録
        logger.info(f"穴の貫通チェックリクエスト: {object_name}, 位置数: {len(positions)}, サンプル数: {samples}, タイムアウト: {timeout}秒")
        
        # 穴貫通チェック実行
        return check_hole_penetration(object_name, positions, radius, samples, timeout)
    
    except Exception as e:
        # 予期しないエラーのハンドリング
        import traceback
        logger.error(f"穴貫通チェックリゾルバエラー: {str(e)}")
        logger.debug(traceback.format_exc())
        return {
            "results": [],
            "success": False,
            "message": f"リゾルバ実行中にエラーが発生しました: {str(e)}",
            "executionTime": 0
        }

# リゾルバマップ
RESOLVERS = {
    'Query': {
        'checkHolePenetration': resolve_check_hole_penetration
    }
}

def register():
    """穴の貫通チェック拡張を登録"""
    try:
        from ..graphql.schema import register_schema_extensions, build_schema, resolvers as schema_resolvers
        
        logger.info("穴の貫通チェックGraphQL拡張を登録しています...")
        
        # キャッシュの初期化
        clear_cache()
        
        # スレッドプールの初期化 (パフォーマンス品質を向上)
        init_thread_pool(max_workers=6)  # CPU数に応じて調整するのが良い
        
        # スキーマ拡張を登録
        register_schema_extensions([SCHEMA_EXTENSION])
        
        # リゾルバを登録 (グローバル変数resolversに追加)
        for type_name, type_resolvers in RESOLVERS.items():
            if type_name not in schema_resolvers:
                schema_resolvers[type_name] = {}
            for field_name, resolver_func in type_resolvers.items():
                schema_resolvers[type_name][field_name] = resolver_func
                logger.info(f"リゾルバ登録: {type_name}.{field_name}")
        
        # スキーマ再構築
        schema = build_schema()
        if schema:
            logger.info("スキーマ再構築に成功しました")
        else:
            logger.warning("スキーマ再構築後もNoneのままです")
        
        logger.info("穴の貫通チェックGraphQL拡張の登録が完了しました")
    except ImportError as ie:
        logger.warning(f"GraphQLスキーマモジュールのインポートに失敗しました: {ie}")
    except Exception as e:
        logger.error(f"穴の貫通チェックGraphQL拡張の登録に失敗しました: {e}")
        import traceback
        logger.debug(traceback.format_exc())

def unregister():
    """穴の貫通チェック拡張の登録解除"""
    try:
        from ..graphql.schema import unregister_schema_extensions, build_schema, resolvers as schema_resolvers
        
        logger.info("穴の貫通チェックGraphQL拡張を登録解除しています...")
        
        # スキーマ拡張を登録解除
        unregister_schema_extensions([SCHEMA_EXTENSION])
        
        # リゾルバも削除
        for type_name, type_resolvers in RESOLVERS.items():
            if type_name in schema_resolvers:
                for field_name in type_resolvers.keys():
                    if field_name in schema_resolvers[type_name]:
                        del schema_resolvers[type_name][field_name]
                        logger.info(f"リゾルバ削除: {type_name}.{field_name}")
        
        # スキーマ再構築
        schema = build_schema()
        if schema:
            logger.info("登録解除後のスキーマ再構築に成功しました")
        else:
            logger.warning("登録解除後のスキーマ再構築に失敗、スキーマがNoneのままです")
        
        # キャッシュをクリア
        clear_cache()
        
        # スレッドプールのクリーンアップ
        try:
            if '_hole_penetration_thread_pool' in globals():
                global _hole_penetration_thread_pool
                if _hole_penetration_thread_pool is not None:
                    _hole_penetration_thread_pool.shutdown(wait=False)
                    _hole_penetration_thread_pool = None
                    logger.info("穴の貫通チェック用スレッドプールをシャットダウンしました")
        except Exception as thread_err:
            logger.warning(f"スレッドプールのシャットダウン中にエラーが発生しました: {thread_err}")
        
        logger.info("穴の貫通チェックGraphQL拡張の登録解除が完了しました")
    except ImportError as ie:
        logger.warning(f"GraphQLスキーマモジュールのインポートに失敗しました: {ie}")
    except Exception as e:
        logger.error(f"穴の貫通チェックGraphQL拡張の登録解除に失敗しました: {e}")
        import traceback
        logger.debug(traceback.format_exc())