"""
GraphQLクエリとリゾルバの最適化ユーティリティ
"""

import logging
import time
import functools
from typing import Dict, Any, Callable, List, Optional, TypeVar, cast

logger = logging.getLogger("blender_graphql_mcp.tools.optimizer")

# 型変数
F = TypeVar('F', bound=Callable[..., Any])

# クエリ処理のパフォーマンスを測定
def measure_performance(func: F) -> F:
    """
    関数の実行時間を測定するデコレータ
    
    Args:
        func: 測定対象の関数
        
    Returns:
        デコレートされた関数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        # 実行時間をミリ秒で計算
        execution_time_ms = (end_time - start_time) * 1000
        
        # 実行時間をログ記録
        logger.debug(f"{func.__name__} の実行時間: {execution_time_ms:.2f} ms")
        
        # 結果がdictで特定の条件を満たす場合、パフォーマンス情報を追加
        if isinstance(result, dict) and "extensions" not in result:
            # 新しいdictを作成（元のdictは変更しない）
            result_with_perf = dict(result)
            # 拡張情報を追加
            if "extensions" not in result_with_perf:
                result_with_perf["extensions"] = {}
            # パフォーマンス情報を追加
            result_with_perf["extensions"]["performance"] = {
                "executionMs": round(execution_time_ms, 2)
            }
            return result_with_perf
        
        return result
    
    return cast(F, wrapper)

# キャッシュシステム
_query_cache: Dict[str, Dict[str, Any]] = {}
_cache_hits = 0
_cache_misses = 0
_max_cache_size = 100  # デフォルトキャッシュサイズ

def set_max_cache_size(size: int):
    """
    クエリキャッシュの最大サイズを設定
    
    Args:
        size: キャッシュエントリの最大数
    """
    global _max_cache_size
    _max_cache_size = size
    
    # キャッシュが最大サイズを超えている場合、古いエントリを削除
    if len(_query_cache) > _max_cache_size:
        # キャッシュを最大サイズまで減らす
        entries_to_remove = len(_query_cache) - _max_cache_size
        keys_to_remove = list(_query_cache.keys())[:entries_to_remove]
        
        for key in keys_to_remove:
            del _query_cache[key]
            
        logger.debug(f"{entries_to_remove}個の古いキャッシュエントリを削除しました")

def clear_cache():
    """クエリキャッシュをクリア"""
    global _query_cache, _cache_hits, _cache_misses
    _query_cache.clear()
    _cache_hits = 0
    _cache_misses = 0
    logger.info("クエリキャッシュをクリアしました")

def get_cache_stats() -> Dict[str, Any]:
    """
    キャッシュ統計情報を取得
    
    Returns:
        キャッシュ統計を含む辞書
    """
    total_requests = _cache_hits + _cache_misses
    hit_rate = (_cache_hits / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "size": len(_query_cache),
        "max_size": _max_cache_size,
        "hits": _cache_hits,
        "misses": _cache_misses,
        "hit_rate_percent": round(hit_rate, 2),
        "total_requests": total_requests
    }

def cache_query(ttl_seconds: int = 60):
    """
    GraphQLクエリ結果をキャッシュするデコレータ
    
    Args:
        ttl_seconds: キャッシュの有効期間（秒）
        
    Returns:
        デコレータ関数
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(query: str, variables: Optional[Dict[str, Any]] = None, operation_name: Optional[str] = None):
            global _cache_hits, _cache_misses
            
            # 変数がNoneの場合は空の辞書を使用
            if variables is None:
                variables = {}
                
            # キャッシュキーを生成
            # 注：正確なキャッシュのためには、変数やオペレーション名も考慮する必要がある
            cache_key = f"{query}:{str(variables)}:{operation_name or ''}"
            
            # 現在の時間
            current_time = time.time()
            
            # キャッシュにエントリが存在し、有効期限内かチェック
            if cache_key in _query_cache:
                cache_entry = _query_cache[cache_key]
                
                # 有効期限をチェック
                if current_time < cache_entry.get("expires_at", 0):
                    _cache_hits += 1
                    logger.debug(f"キャッシュヒット: {cache_key[:50]}...")
                    return cache_entry["result"]
            
            # キャッシュミス - 関数を実行
            _cache_misses += 1
            logger.debug(f"キャッシュミス: {cache_key[:50]}...")
            
            result = func(query, variables, operation_name)
            
            # キャッシュにエラーがある場合は保存しない
            if isinstance(result, dict) and "errors" not in result:
                # 有効期限を計算
                expires_at = current_time + ttl_seconds
                
                # 結果をキャッシュに保存
                _query_cache[cache_key] = {
                    "result": result,
                    "expires_at": expires_at,
                    "created_at": current_time
                }
                
                # キャッシュが最大サイズを超えている場合、最も古いエントリを削除
                if len(_query_cache) > _max_cache_size:
                    oldest_key = min(_query_cache.keys(), key=lambda k: _query_cache[k]["created_at"])
                    del _query_cache[oldest_key]
                    logger.debug(f"キャッシュが最大サイズを超えたため、最も古いエントリを削除: {oldest_key[:50]}...")
            
            return result
        
        return cast(F, wrapper)
    
    return decorator

# パフォーマンスメトリクス
_performance_counters = {
    "total_queries": 0,
    "slow_queries": 0,   # 500ms以上のクエリ
    "very_slow_queries": 0,  # 1000ms以上のクエリ
    "total_execution_time": 0.0,
    "peak_execution_time": 0.0,
    "peak_query": ""
}

def get_performance_metrics() -> Dict[str, Any]:
    """
    パフォーマンスメトリクスを取得
    
    Returns:
        パフォーマンスメトリクスの詳細情報
    """
    metrics = dict(_performance_counters)
    
    # 平均実行時間を計算
    if metrics["total_queries"] > 0:
        metrics["avg_execution_time"] = metrics["total_execution_time"] / metrics["total_queries"]
        metrics["slow_query_percent"] = (metrics["slow_queries"] / metrics["total_queries"]) * 100
    else:
        metrics["avg_execution_time"] = 0.0
        metrics["slow_query_percent"] = 0.0
        
    # キャッシュ統計を追加
    metrics["cache"] = get_cache_stats()
    
    return metrics

def reset_performance_metrics():
    """パフォーマンスメトリクスをリセット"""
    global _performance_counters
    _performance_counters = {
        "total_queries": 0,
        "slow_queries": 0,
        "very_slow_queries": 0,
        "total_execution_time": 0.0,
        "peak_execution_time": 0.0,
        "peak_query": ""
    }
    logger.info("パフォーマンスメトリクスをリセットしました")

# 以前のパフォーマンス測定関数を拡張
def measure_performance(func: F) -> F:
    """
    関数の実行時間を測定するデコレータ（修正版）
    
    Args:
        func: 測定対象の関数
        
    Returns:
        デコレートされた関数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global _performance_counters
        
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        # 実行時間をミリ秒で計算
        execution_time_ms = (end_time - start_time) * 1000
        
        # パフォーマンスメトリクスを更新
        _performance_counters["total_queries"] += 1
        _performance_counters["total_execution_time"] += execution_time_ms
        
        # 遅いクエリをカウント
        if execution_time_ms >= 1000:
            _performance_counters["very_slow_queries"] += 1
            logger.warning(f"非常に遅いクエリ検出: {func.__name__}, {execution_time_ms:.2f}ms")
        elif execution_time_ms >= 500:
            _performance_counters["slow_queries"] += 1
            logger.info(f"遅いクエリ検出: {func.__name__}, {execution_time_ms:.2f}ms")
        
        # ピーク時間の更新
        if execution_time_ms > _performance_counters["peak_execution_time"]:
            _performance_counters["peak_execution_time"] = execution_time_ms
            # クエリの先頭100文字だけを記録
            query_sample = "?"
            if len(args) > 0 and isinstance(args[0], str):
                query_sample = args[0][:100] + "..." if len(args[0]) > 100 else args[0]
            _performance_counters["peak_query"] = query_sample
        
        # 実行時間をログ記録
        logger.debug(f"{func.__name__} の実行時間: {execution_time_ms:.2f} ms")
        
        # 結果がdictで特定の条件を満たす場合、パフォーマンス情報を追加
        if isinstance(result, dict):
            # 新しいdictを作成（元のdictは変更しない）
            result_with_perf = dict(result)
            # 拡張情報がない場合は作成
            if "extensions" not in result_with_perf:
                result_with_perf["extensions"] = {}
            # パフォーマンス情報を追加
            result_with_perf["extensions"]["performance"] = {
                "executionMs": round(execution_time_ms, 2),
                "cached": getattr(result, "_cached", False) if hasattr(result, "_cached") else False
            }
            return result_with_perf
        
        return result
    
    return cast(F, wrapper)

# バッチ処理最適化
def optimize_batch_execution(queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    バッチクエリ実行を最適化（拡張版）
    
    Args:
        queries: 実行するクエリのリスト
        
    Returns:
        最適化されたクエリリスト
    """
    # 同一クエリの重複排除
    optimized_queries = []
    processed_queries = {}
    
    for i, query in enumerate(queries):
        # クエリ、変数、オペレーション名からキーを生成
        query_str = query.get("query", "")
        variables = str(query.get("variables", {}))
        operation = query.get("operationName", "")
        
        key = f"{query_str}:{variables}:{operation}"
        
        if key not in processed_queries:
            processed_queries[key] = i
            optimized_queries.append(query)
    
    reduction = len(queries) - len(optimized_queries)
    if reduction > 0:
        logger.info(f"バッチクエリを最適化: {len(queries)} -> {len(optimized_queries)} (重複{reduction}件を削除)")
    
    # 注意: 実际の本番環境では、より高度な最適化を実装する可能性があります
    # 例: クエリの依存関係分析、フィールドマージ、並列実行など
    
    return optimized_queries

# クエリ分析と最適化ヒント
def analyze_query(query_string: str) -> Dict[str, Any]:
    """
    GraphQLクエリを分析して最適化のヒントを提供
    
    Args:
        query_string: 分析するGraphQLクエリ文字列
        
    Returns:
        分析結果と最適化ヒント
    """
    hints = []
    
    # 大きな集合のリクエストをチェック
    if "all" in query_string.lower() and "objects" in query_string:
        hints.append("大量のオブジェクトを一度に取得しています。ページネーションやフィルタを検討してください。")
    
    # 深いネストをチェック
    nesting_level = query_string.count('{')
    if nesting_level > 5:
        hints.append(f"クエリのネストが深すぎます ({nesting_level} レベル)。クエリを分割することを検討してください。")
    
    # バッチクエリの表現を推奨
    if "query" in query_string.lower() and query_string.count('query') > 2:
        hints.append("複数のクエリが見つかりました。バッチクエリを使用して、ネットワークリクエストを削減することを検討してください。")
    
    # 不要なフィールドをチェック
    potential_expensive_fields = ["vertices", "faces", "edges", "materials", "modifiers"]
    for field in potential_expensive_fields:
        if field in query_string:
            hints.append(f""{field}" フィールドは処理が重い場合があります。必要なフィールドのみをリクエストしてください。")
    
    # 結果を返す
    return {
        "query_length": len(query_string),
        "nesting_level": nesting_level,
        "optimization_hints": hints
    }