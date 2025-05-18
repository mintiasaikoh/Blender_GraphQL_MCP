"""
Unified MCP Performance Utilities
シンプルかつ効果的なパフォーマンス計測ツール
"""

import time
import functools
import logging
from typing import Dict, Any, Callable, Optional, TypeVar, cast

# 型ヒント用
F = TypeVar('F', bound=Callable[..., Any])

# ロガー設定
logger = logging.getLogger('unified_mcp.performance')

# グローバル設定
performance_tracking_enabled = True

# 実行時間記録用の辞書
_timing_stats = {}

def enable_tracking():
    """パフォーマンス計測を有効化"""
    global performance_tracking_enabled
    performance_tracking_enabled = True
    logger.info("パフォーマンス計測が有効になりました")

def disable_tracking():
    """パフォーマンス計測を無効化"""
    global performance_tracking_enabled
    performance_tracking_enabled = False
    logger.info("パフォーマンス計測が無効になりました")

def reset_stats():
    """計測統計をリセット"""
    global _timing_stats
    _timing_stats.clear()
    logger.info("パフォーマンス統計がリセットされました")

def get_stats() -> Dict[str, Dict[str, Any]]:
    """計測統計を取得"""
    return _timing_stats.copy()

def track_time(func: F) -> F:
    """関数の実行時間を計測するデコレータ（シンプル版）"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not performance_tracking_enabled:
            return func(*args, **kwargs)
        
        # 関数名
        func_name = func.__name__
        # 開始時間
        start_time = time.time()
        
        try:
            # 関数実行
            return func(*args, **kwargs)
        finally:
            # 終了時間と処理時間の計算
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # 統計情報を更新
            if func_name not in _timing_stats:
                _timing_stats[func_name] = {
                    'count': 0,
                    'total_ms': 0,
                    'min_ms': float('inf'),
                    'max_ms': 0,
                    'avg_ms': 0
                }
            
            stats = _timing_stats[func_name]
            stats['count'] += 1
            stats['total_ms'] += duration_ms
            stats['min_ms'] = min(stats['min_ms'], duration_ms)
            stats['max_ms'] = max(stats['max_ms'], duration_ms)
            stats['avg_ms'] = stats['total_ms'] / stats['count']
            
            # ログに記録（デバッグレベル）
            logger.debug(f"{func_name}: {duration_ms:.2f}ms")
    
    return cast(F, wrapper)

def time_operation(name: Optional[str] = None):
    """コンテキストマネージャとして使用可能なタイマー
    
    Example:
        with time_operation("データ読み込み"):
            data = load_data()
    """
    class Timer:
        def __init__(self, operation_name):
            self.operation_name = operation_name
            self.start_time = None
        
        def __enter__(self):
            if performance_tracking_enabled:
                self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if not performance_tracking_enabled or self.start_time is None:
                return
            
            # 終了時間と処理時間の計算
            end_time = time.time()
            duration_ms = (end_time - self.start_time) * 1000
            
            op_name = self.operation_name
            
            # 統計情報を更新
            if op_name not in _timing_stats:
                _timing_stats[op_name] = {
                    'count': 0,
                    'total_ms': 0,
                    'min_ms': float('inf'),
                    'max_ms': 0,
                    'avg_ms': 0
                }
            
            stats = _timing_stats[op_name]
            stats['count'] += 1
            stats['total_ms'] += duration_ms
            stats['min_ms'] = min(stats['min_ms'], duration_ms)
            stats['max_ms'] = max(stats['max_ms'], duration_ms)
            stats['avg_ms'] = stats['total_ms'] / stats['count']
            
            # ログに記録（デバッグレベル）
            logger.debug(f"{op_name}: {duration_ms:.2f}ms")
    
    return Timer(name)

def print_stats(threshold_ms: float = 0):
    """閾値以上の処理時間の統計情報を表示"""
    if not _timing_stats:
        print("パフォーマンス統計情報はありません")
        return
    
    print("\n=== パフォーマンス統計 ===")
    print(f"{'操作':<30} {'回数':>5} {'合計(ms)':>10} {'平均(ms)':>10} {'最小(ms)':>10} {'最大(ms)':>10}")
    print("-" * 80)
    
    # 平均時間でソート
    sorted_stats = sorted(
        _timing_stats.items(), 
        key=lambda x: x[1]['avg_ms'], 
        reverse=True
    )
    
    for name, stats in sorted_stats:
        if stats['avg_ms'] >= threshold_ms:
            print(f"{name:<30} {stats['count']:>5} {stats['total_ms']:>10.2f} {stats['avg_ms']:>10.2f} {stats['min_ms']:>10.2f} {stats['max_ms']:>10.2f}")
    
    print("=" * 80)

def register():
    """パフォーマンスモジュールを登録"""
    logger.info("パフォーマンスモジュールが登録されました")

def unregister():
    """パフォーマンスモジュールの登録解除"""
    logger.info("パフォーマンスモジュールが登録解除されました")
