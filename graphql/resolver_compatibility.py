"""
Resolver Compatibility Layer（リゾルバ互換レイヤー）
resolver.pyをメインの実装として使用し、resolvers.pyとの互換性を提供します
"""

import logging
import traceback
from typing import Any, Dict, Optional, List, Union, Callable

# ロガー初期化
logger = logging.getLogger("blender_graphql_mcp.graphql.resolver_compatibility")

# リゾルバモジュールをインポート（resolver.pyを優先）
try:
    # まず単数形リゾルバ（resolver.py）を試す - これが主要ファイル
    from . import resolver
    _main_resolver = resolver
    logger.info("主要リゾルバモジュール (resolver.py) をロードしました")
    
    # resolvers.pyの存在確認（オプション）
    try:
        from . import resolvers
        _alt_resolver = resolvers
        logger.info("副次リゾルバモジュール (resolvers.py) も利用可能です")
    except ImportError:
        _alt_resolver = None
        logger.debug("副次リゾルバモジュール (resolvers.py) は利用できません")
        
except ImportError as e:
    logger.error(f"主要リゾルバモジュール (resolver.py) のロードに失敗: {e}")
    _main_resolver = None
    
    # フォールバックとしてresolvers.pyを試す
    try:
        from . import resolvers
        _alt_resolver = resolvers
        logger.info("フォールバック: 副次リゾルバモジュール (resolvers.py) をロードしました")
    except ImportError:
        _alt_resolver = None
        logger.error("どのリゾルバモジュールもロードできませんでした")

# 主要リゾルバ関数のリスト
REQUIRED_RESOLVERS = [
    'resolve_hello', 'resolve_scene', 'resolve_object',
    'resolve_create_smart_object', 'resolve_enhanced_boolean_operation'
]

# 互換性のためのヘルパー関数 - resolver.py関数を優先的に転送
def __getattr__(name):
    """動的属性アクセスハンドラ - リゾルバ関数を自動的に転送"""
    # まず主要モジュール（resolver.py）をチェック
    if _main_resolver and hasattr(_main_resolver, name):
        return getattr(_main_resolver, name)
    
    # 次に代替モジュール（resolvers.py）をチェック
    if _alt_resolver and hasattr(_alt_resolver, name):
        return getattr(_alt_resolver, name)
    
    # 関数が見つからない場合は明示的なエラー
    raise AttributeError(f"リゾルバ関数 '{name}' はどのモジュールにも見つかりません")

# インターフェイス互換性のための特定の関数マッピング
# resolvers.pyのresolve_scene_infoをresolve_sceneにマッピングするなど
if _alt_resolver and hasattr(_alt_resolver, 'resolve_scene_info') and not hasattr(_main_resolver, 'resolve_scene_info'):
    resolve_scene_info = _alt_resolver.resolve_scene_info

# リゾルバ利用可能フラグ
RESOLVERS_AVAILABLE = (_main_resolver is not None) or (_alt_resolver is not None)

# リゾルバモジュールの状態をログに出力
logger.info(f"リゾルバ互換レイヤーの初期化完了: 主要={_main_resolver is not None}, 代替={_alt_resolver is not None}")