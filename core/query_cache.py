"""
クエリキャッシュモジュール
高速なクエリ処理のためのキャッシュシステム
"""

import hashlib
import time
import json
import logging
from typing import Dict, Any, Optional, Union, Tuple
import threading

logger = logging.getLogger("blender_graphql_mcp.query_cache")

class QueryCache:
    """GraphQLクエリ結果をキャッシュするシステム"""
    
    def __init__(self, max_size: int = 100, ttl: int = 60):
        """
        Args:
            max_size: キャッシュの最大エントリ数（デフォルト: 100）
            ttl: キャッシュエントリの有効期間（秒単位、デフォルト: 60秒）
        """
        self.cache: Dict[str, Tuple[float, Any]] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.stats = {'hits': 0, 'misses': 0, 'sets': 0, 'evictions': 0}
        self.lock = threading.RLock()  # スレッドセーフにするためのロック
    
    def _generate_key(self, query: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """クエリとその変数からキャッシュキーを生成
        
        Args:
            query: GraphQLクエリ文字列
            variables: クエリ変数
            
        Returns:
            str: ハッシュ化されたキー
        """
        if variables:
            # 変数を安定したJSON文字列に変換（キーの順序を保証）
            sorted_vars = json.dumps(variables, sort_keys=True)
            key_data = f"{query}:{sorted_vars}"
        else:
            key_data = f"{query}"
            
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def get(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """キャッシュからクエリ結果を取得
        
        Args:
            query: GraphQLクエリ文字列
            variables: クエリ変数
            
        Returns:
            Optional[Any]: キャッシュされた結果、または存在しない場合はNone
        """
        with self.lock:
            key = self._generate_key(query, variables)
            cache_entry = self.cache.get(key)
            
            if cache_entry is None:
                self.stats['misses'] += 1
                return None
            
            timestamp, result = cache_entry
            
            # TTLチェック
            if time.time() - timestamp > self.ttl:
                # TTL切れ - キャッシュから削除
                del self.cache[key]
                self.stats['misses'] += 1
                return None
            
            self.stats['hits'] += 1
            logger.debug(f"キャッシュヒット: {key[:8]}... (ヒット率: {self.hit_rate():.2f}%)")
            return result
    
    def set(self, query: str, result: Any, variables: Optional[Dict[str, Any]] = None) -> bool:
        """クエリ結果をキャッシュに保存
        
        Args:
            query: GraphQLクエリ文字列
            result: キャッシュする結果
            variables: クエリ変数
            
        Returns:
            bool: 成功した場合はTrue
        """
        with self.lock:
            key = self._generate_key(query, variables)
            
            # キャッシュが最大サイズに達した場合、最も古いエントリを削除
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.items(), key=lambda x: x[1][0])[0]
                del self.cache[oldest_key]
                self.stats['evictions'] += 1
                logger.debug(f"キャッシュ古いエントリを削除: {oldest_key[:8]}...")
            
            # キャッシュに保存
            self.cache[key] = (time.time(), result)
            self.stats['sets'] += 1
            logger.debug(f"キャッシュ保存: {key[:8]}... (サイズ: {len(self.cache)})")
            return True
    
    def invalidate(self, pattern: Optional[str] = None) -> int:
        """キャッシュを無効化（全体またはパターンに基づく）
        
        Args:
            pattern: 無効化するキーに含まれるパターン（Noneで全体）
            
        Returns:
            int: 無効化されたエントリ数
        """
        with self.lock:
            if pattern is None:
                count = len(self.cache)
                self.cache.clear()
                logger.info(f"キャッシュ全体をクリア: {count}エントリ")
                return count
            
            # パターンに一致するキーを探して削除
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for k in keys_to_delete:
                del self.cache[k]
            
            logger.info(f"パターンによりキャッシュ削除: '{pattern}', {len(keys_to_delete)}エントリ")
            return len(keys_to_delete)
    
    def hit_rate(self) -> float:
        """キャッシュヒット率を計算
        
        Returns:
            float: ヒット率（パーセント）
        """
        total = self.stats['hits'] + self.stats['misses']
        if total == 0:
            return 0.0
        return (self.stats['hits'] / total) * 100
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計情報を取得
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        with self.lock:
            stats = dict(self.stats)
            stats.update({
                'entries': len(self.cache),
                'hit_rate': self.hit_rate(),
                'max_size': self.max_size,
                'ttl': self.ttl
            })
            return stats
    
    def cleanup(self) -> int:
        """期限切れのキャッシュエントリをクリーンアップ
        
        Returns:
            int: クリーンアップされたエントリ数
        """
        with self.lock:
            current_time = time.time()
            keys_to_delete = [
                k for k, v in self.cache.items() 
                if current_time - v[0] > self.ttl
            ]
            
            for k in keys_to_delete:
                del self.cache[k]
            
            if keys_to_delete:
                logger.info(f"期限切れキャッシュをクリーンアップ: {len(keys_to_delete)}エントリ")
            
            return len(keys_to_delete)


class GraphQLQueryCache(QueryCache):
    """GraphQL特化のクエリキャッシュ"""
    
    def __init__(self, max_size: int = 100, ttl: int = 60):
        super().__init__(max_size, ttl)
        # ミューテーションの追跡（キャッシュ無効化に使用）
        self.tracked_types = {}
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """クエリを分析して情報を抽出
        
        Args:
            query: GraphQLクエリ文字列
            
        Returns:
            Dict[str, Any]: クエリ分析情報
        """
        # 簡易的なクエリ解析
        is_mutation = "mutation" in query.lower()
        
        # 影響を受けるタイプを抽出（単純な例）
        affected_types = []
        
        if "Object" in query:
            affected_types.append("Object")
        if "Material" in query:
            affected_types.append("Material")
        if "Scene" in query:
            affected_types.append("Scene")
        
        return {
            'is_mutation': is_mutation,
            'affected_types': affected_types
        }
    
    def set_with_analysis(self, query: str, result: Any, variables: Optional[Dict[str, Any]] = None) -> bool:
        """クエリを分析しながらキャッシュ設定
        
        Args:
            query: GraphQLクエリ文字列
            result: キャッシュする結果
            variables: クエリ変数
            
        Returns:
            bool: 成功した場合はTrue
        """
        analysis = self.analyze_query(query)
        
        # ミューテーションはキャッシュしない
        if analysis['is_mutation']:
            logger.debug(f"ミューテーションはキャッシュしません: {query[:50]}...")
            
            # 関連タイプのキャッシュを無効化
            for affected_type in analysis['affected_types']:
                self.invalidate_type(affected_type)
                
            return False
        
        # 影響を受けるタイプを追跡
        key = self._generate_key(query, variables)
        self.tracked_types[key] = analysis['affected_types']
        
        # 通常のキャッシュ設定を実行
        return super().set(query, result, variables)
    
    def invalidate_type(self, type_name: str) -> int:
        """特定のタイプに関連するすべてのキャッシュを無効化
        
        Args:
            type_name: 無効化するタイプ名
            
        Returns:
            int: 無効化されたエントリ数
        """
        with self.lock:
            # そのタイプを含むキーを探す
            keys_to_delete = []
            
            for key, types in self.tracked_types.items():
                if type_name in types:
                    keys_to_delete.append(key)
            
            # キャッシュから削除
            for key in keys_to_delete:
                if key in self.cache:
                    del self.cache[key]
                if key in self.tracked_types:
                    del self.tracked_types[key]
            
            logger.info(f"タイプ '{type_name}' に関連するキャッシュを無効化: {len(keys_to_delete)}エントリ")
            return len(keys_to_delete)