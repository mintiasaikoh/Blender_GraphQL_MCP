"""
設定と依存関係管理モジュール
アドオンの設定を一元管理し、必要な依存関係をチェックします
"""

import importlib
import logging
import sys
import os
import re
import json
from typing import Dict, Optional, Tuple, Any, List, Union
import platform

logger = logging.getLogger('blender_graphql_mcp.config')

# デフォルト設定
DEFAULT_CONFIG = {
    "server": {
        "default_host": "localhost",
        "default_port": 8000,
        "timeout": 30,
        "max_connections": 10
    },
    "threading": {
        "main_thread_timeout": 30,
        "poll_interval": 0.1
    },
    "logging": {
        "level": logging.INFO,
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "api": {
        "version": "1.2.0",  # 現在のAPIバージョン
        "compatible_versions": ["1.0.0", "1.1.0", "1.2.0"],  # 互換性のあるバージョンリスト
        "check_compatibility": True,  # バージョン互換性チェックを有効にするか
        "require_version": False  # クライアントにバージョン情報の提供を必須にするか
    },
    "dependencies": {
        "auto_install": False,  # 自動インストールを有効にするか
        "check_on_startup": True,  # 起動時に依存関係をチェックするか
        "pip_path": "pip"  # pip実行ファイルのパス
    }
}

# 環境変数から設定を取得
def _load_env_config():
    """環境変数から設定を読み込む"""
    env_prefix = "MCP_"
    env_config = {}
    
    # サーバー設定
    if os.environ.get(f"{env_prefix}HOST"):
        if "server" not in env_config:
            env_config["server"] = {}
        env_config["server"]["default_host"] = os.environ.get(f"{env_prefix}HOST")
    
    if os.environ.get(f"{env_prefix}PORT"):
        if "server" not in env_config:
            env_config["server"] = {}
        try:
            env_config["server"]["default_port"] = int(os.environ.get(f"{env_prefix}PORT"))
        except ValueError:
            logger.warning(f"環境変数 {env_prefix}PORT の値が不正です")
    
    # ロギング設定
    if os.environ.get(f"{env_prefix}LOG_LEVEL"):
        if "logging" not in env_config:
            env_config["logging"] = {}
        log_level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        log_level = os.environ.get(f"{env_prefix}LOG_LEVEL").upper()
        if log_level in log_level_map:
            env_config["logging"]["level"] = log_level_map[log_level]
    
    # 依存関係設定
    if os.environ.get(f"{env_prefix}AUTO_INSTALL"):
        if "dependencies" not in env_config:
            env_config["dependencies"] = {}
        env_config["dependencies"]["auto_install"] = os.environ.get(f"{env_prefix}AUTO_INSTALL").lower() in ("true", "1", "yes")
    
    return env_config

# コンフィグファイルから設定を取得
def _load_file_config():
    """コンフィグファイルから設定を読み込む"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            logger.info(f"コンフィグファイル {config_path} から設定を読み込みました")
            return file_config
        except Exception as e:
            logger.warning(f"コンフィグファイルの読み込みに失敗しました: {e}")
    return {}

# グローバル設定
# デフォルト設定、ファイル設定、環境変数設定を統合
CONFIG = DEFAULT_CONFIG.copy()

# 設定をファイルから読み込む
_file_config = _load_file_config()

# 設定を環境変数から読み込む
_env_config = _load_env_config()

# 設定を統合する関数
def _merge_configs(base_config, new_config):
    """設定を再帰的に統合する
    
    Args:
        base_config: ベースとなる設定辞書
        new_config: 新しい設定辞書
    
    Returns:
        統合された設定辞書
    """
    result = base_config.copy()
    
    for key, value in new_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 再帰的に統合
            result[key] = _merge_configs(result[key], value)
        else:
            # 値を上書き
            result[key] = value
    
    return result

# ファイル設定を統合
if _file_config:
    CONFIG = _merge_configs(CONFIG, _file_config)
    logger.info("ファイル設定を統合しました")

# 環境変数設定を統合
if _env_config:
    CONFIG = _merge_configs(CONFIG, _env_config)
    logger.info("環境変数設定を統合しました")

# 必要な依存関係の定義
DEPENDENCIES = {
    'fastapi': {
        'package': 'fastapi',
        'module': 'fastapi',
        'min_version': '0.68.0',
        'required': True,
        'description': 'HTTP APIフレームワーク',
        'fallback': None
    },
    'uvicorn': {
        'package': 'uvicorn',
        'module': 'uvicorn',
        'min_version': '0.15.0',
        'required': True,
        'description': 'ASGIサーバー',
        'fallback': None
    },
    'pydantic': {
        'package': 'pydantic',
        'module': 'pydantic',
        'min_version': '1.8.0',
        'required': True,
        'description': 'データ検証ライブラリ',
        'fallback': None
    },
    'graphql': {
        'package': 'graphql-core',
        'module': 'graphql',
        'min_version': '3.0.0',
        'required': False,
        'description': 'GraphQL実装',
        'fallback': None  # GraphQLは必須ではない
    }
}

# 利用可能な依存関係の状態
AVAILABLE_DEPENDENCIES = {}

# PyPIパッケージをインストールする関数
def install_package(package_name: str, version: Optional[str] = None) -> bool:
    """パッケージをインストールする
    
    Args:
        package_name: パッケージ名
        version: バージョン指定（省略可）
    
    Returns:
        インストールに成功したかどうか
    """
    try:
        import subprocess
        
        # ユーザーのPython環境にインストールする
        pip_path = CONFIG.get("dependencies", {}).get("pip_path", "pip")
        
        # バージョン指定があれば追加
        package_spec = package_name
        if version:
            package_spec = f"{package_name}=={version}"
        
        logger.info(f"パッケージ {package_spec} をインストールしています...")
        
        # システムの判定
        if platform.system() == "Windows":
            # Windowsではシェル=Trueが必要
            result = subprocess.run(
                [pip_path, "install", "--user", package_spec],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )
        else:
            # macOS/Linux
            result = subprocess.run(
                [pip_path, "install", "--user", package_spec],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        if result.returncode == 0:
            logger.info(f"パッケージ {package_spec} のインストールに成功しました")
            return True
        else:
            logger.error(f"パッケージ {package_spec} のインストールに失敗しました: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"パッケージインストール中にエラーが発生しました: {str(e)}")
        return False

def initialize():
    """設定を初期化し、依存関係をチェック"""
    logger.info("設定を初期化しています...")
    
    # ログレベルの設定
    logging.basicConfig(level=CONFIG["logging"]["level"], 
                       format=CONFIG["logging"]["format"])
    
    # Pythonディレクトリをsys.pathに追加
    _add_site_packages_to_path()
    
    # 依存関係もチェック
    check_all_dependencies()

def _add_site_packages_to_path():
    """サイトパッケージディレクトリをPythonパスに追加する
    依存関係問題の解決策として、ユーザーの.local/lib/python*/site-packagesを明示的に追加
    """
    try:
        # ユーザーのホームディレクトリを取得
        home_dir = os.path.expanduser("~")
        
        # Pythonのバージョンに基づいたパスを生成 (e.g., "3.11" ではなく "3.11" のみ)
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        
        # システムに応じたsite-packagesディレクトリのパスを生成
        if platform.system() == "Windows":
            site_packages_paths = [
                os.path.join(home_dir, "AppData", "Roaming", "Python", f"Python{python_version}", "site-packages"),
                os.path.join(home_dir, "AppData", "Local", "Programs", "Python", f"Python{python_version}", "site-packages")
            ]
        else:  # macOS/Linux
            site_packages_paths = [
                os.path.join(home_dir, ".local", "lib", f"python{python_version}", "site-packages")
            ]
        
        # 存在するディレクトリをパスに追加
        for path in site_packages_paths:
            if os.path.exists(path) and path not in sys.path:
                sys.path.insert(0, path)
                logger.info(f"Pythonパスに追加しました: {path}")
                
    except Exception as e:
        logger.warning(f"Pythonパスの設定中にエラーが発生しました: {str(e)}")
    
    logger.info("設定の初期化が完了しました")

def check_all_dependencies() -> Dict[str, Tuple[bool, Optional[str]]]:
    """すべての依存関係をチェック
    
    Returns:
        各依存関係の利用可能状態とバージョンの辞書
    """
    global AVAILABLE_DEPENDENCIES
    
    results = {}
    
    for name, info in DEPENDENCIES.items():
        available, version = check_dependency(name)
        results[name] = (available, version)
        
        # 必須の依存関係が利用できない場合は警告
        if info['required'] and not available:
            logger.error(f"必須の依存関係 {name} が利用できません")
        elif not available and info['fallback']:
            logger.warning(f"依存関係 {name} が利用できないためフォールバック {info['fallback']} を使用します")
        elif available:
            logger.info(f"依存関係 {name} が利用可能です (バージョン: {version})")
    
    AVAILABLE_DEPENDENCIES = results
    return results

def check_dependency(name: str) -> Tuple[bool, Optional[str]]:
    """依存関係のチェック
    
    Args:
        name: 依存関係の名前
        
    Returns:
        (available, version): 利用可能かどうかとバージョン文字列
    """
    if name not in DEPENDENCIES:
        logger.warning(f"未知の依存関係: {name}")
        return False, None
    
    info = DEPENDENCIES[name]
    module_name = info['module']
    
    try:
        module = importlib.import_module(module_name)
        
        # バージョンの取得を試みる
        version = None
        for attr in ['__version__', 'VERSION', 'version']:
            if hasattr(module, attr):
                version = getattr(module, attr)
                break
        
        if version is None:
            logger.warning(f"依存関係 {name} のバージョンが取得できません")
        
        # 最小バージョンのチェック
        if version and 'min_version' in info:
            min_version = info['min_version']
            if _compare_versions(str(version), min_version) < 0:
                logger.warning(f"依存関係 {name} のバージョンが古すぎます: {version} < {min_version}")
                return False, str(version)
        
        return True, str(version)
    
    except ImportError:
        logger.info(f"依存関係 {name} がインポートできません")
        return False, None
    except Exception as e:
        logger.warning(f"依存関係 {name} のチェック中にエラーが発生しました: {str(e)}")
        return False, None

def _compare_versions(v1: str, v2: str) -> int:
    """バージョン文字列を比較
    
    Args:
        v1: 比較するバージョン1
        v2: 比較するバージョン2
        
    Returns:
        -1: v1 < v2
         0: v1 == v2
         1: v1 > v2
    """
    # バージョン文字列から数字部分を抽出
    def normalize(v):
        return [int(x) for x in re.sub(r'[^0-9.]', '', v).split('.')]
    
    v1_parts = normalize(v1)
    v2_parts = normalize(v2)
    
    # 長さを揃える
    while len(v1_parts) < len(v2_parts):
        v1_parts.append(0)
    while len(v2_parts) < len(v1_parts):
        v2_parts.append(0)
    
    # 比較
    for i in range(len(v1_parts)):
        if v1_parts[i] < v2_parts[i]:
            return -1
        elif v1_parts[i] > v2_parts[i]:
            return 1
    
    return 0

def get_config(section: str, key: str, default: Any = None) -> Any:
    """設定値を取得
    
    Args:
        section: 設定セクション
        key: 設定キー
        default: デフォルト値
        
    Returns:
        設定値またはデフォルト値
    """
    if section in CONFIG and key in CONFIG[section]:
        return CONFIG[section][key]
    return default

def is_dependency_available(name: str) -> bool:
    """依存関係が利用可能かどうかを確認
    
    Args:
        name: 依存関係の名前
        
    Returns:
        利用可能かどうか
    """
    if name in AVAILABLE_DEPENDENCIES:
        return AVAILABLE_DEPENDENCIES[name][0]
    return False

def get_dependency_version(name: str) -> Optional[str]:
    """依存関係のバージョンを取得
    
    Args:
        name: 依存関係の名前
        
    Returns:
        バージョン文字列または None
    """
    if name in AVAILABLE_DEPENDENCIES and AVAILABLE_DEPENDENCIES[name][0]:
        return AVAILABLE_DEPENDENCIES[name][1]
    return None
