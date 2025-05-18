"""
Blender Unified MCP File Utilities
ファイル操作およびパス処理のためのユーティリティ
"""

import os
import sys
import logging
import tempfile
import shutil
import json
import time
import platform
import re
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple, Set, BinaryIO, TextIO
from functools import wraps
from contextlib import contextmanager

# モジュールレベルのロガー
logger = logging.getLogger('unified_mcp.utils.fileutils')

# デバッグモード設定（環境変数から取得）
DEBUG_MODE = os.environ.get('UNIFIED_MCP_DEBUG', '0').lower() in ('1', 'true', 'yes')

# ファイルシステム定数
IS_WINDOWS = platform.system() == 'Windows'
IS_MACOS = platform.system() == 'Darwin'
IS_LINUX = platform.system() == 'Linux'
PATH_SEP = os.path.sep
ALTERNATIVE_PATH_SEP = '/' if IS_WINDOWS else '\\'

# パスの最大長（OSによって異なる）
MAX_PATH_LENGTH = 260 if IS_WINDOWS else 4096  # Linuxとmacの一般的な制限

# 一時ディレクトリとキャッシュディレクトリ
TEMP_DIR = tempfile.gettempdir()
USER_HOME = os.path.expanduser("~")
CACHE_DIR = os.path.join(USER_HOME, ".mcp_cache")

# 安全でないファイル名文字のパターン
UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')

# ---------------------------------------------------------
# パス操作ユーティリティ
# ---------------------------------------------------------

def normalize_path(path: str) -> str:
    """
    パスを正規化する（セパレータの統一、冗長な要素の削除など）
    
    Args:
        path: 正規化するパス
        
    Returns:
        正規化されたパス
    """
    if not path:
        return ""
    
    # 全てのバックスラッシュをスラッシュに変換（一時的に）
    normalized = path.replace('\\', '/')
    
    # 二重スラッシュを単一に
    while '//' in normalized:
        normalized = normalized.replace('//', '/')
    
    # 末尾のスラッシュを削除（ルートディレクトリの場合を除く）
    if len(normalized) > 1 and normalized.endswith('/'):
        normalized = normalized[:-1]
    
    # Windowsのドライブレターを処理
    if IS_WINDOWS and len(normalized) >= 2 and normalized[1] == ':':
        # ドライブレター部分を大文字に
        normalized = normalized[0].upper() + normalized[1:]
    
    # OSごとのパス区切り文字に変換
    if PATH_SEP != '/':
        normalized = normalized.replace('/', PATH_SEP)
    
    # os.path.normpath で冗長なセグメントを削除
    normalized = os.path.normpath(normalized)
    
    return normalized


def is_absolute_path(path: str) -> bool:
    """
    パスが絶対パスかどうかを判定
    
    Args:
        path: チェックするパス
        
    Returns:
        絶対パスならTrue
    """
    if not path:
        return False
    
    # os.path.isabs に任せる前にWindowsのUNCパスをチェック
    if IS_WINDOWS and path.startswith('\\\\'):
        return True
        
    return os.path.isabs(path)


def join_paths(*paths: str) -> str:
    """
    複数のパスセグメントを結合する
    
    Args:
        *paths: 結合するパスの可変引数
        
    Returns:
        結合された正規化パス
    """
    # None や空文字列を除外
    valid_paths = [p for p in paths if p]
    
    if not valid_paths:
        return ""
    
    # os.path.join で結合
    result = os.path.join(*valid_paths)
    
    # 正規化
    return normalize_path(result)


def get_file_extension(path: str) -> str:
    """
    ファイルの拡張子を取得（小文字に変換）
    
    Args:
        path: ファイルパス
        
    Returns:
        拡張子（先頭のドットを除く、小文字）
    """
    if not path:
        return ""
    
    # 正規化
    norm_path = normalize_path(path)
    
    # 拡張子を抽出（小文字に変換）
    return os.path.splitext(norm_path)[1].lower().lstrip('.')


def get_filename(path: str, with_extension: bool = True) -> str:
    """
    パスからファイル名部分を抽出
    
    Args:
        path: ファイルパス
        with_extension: 拡張子を含めるかどうか
        
    Returns:
        ファイル名
    """
    if not path:
        return ""
    
    filename = os.path.basename(normalize_path(path))
    
    if not with_extension:
        filename = os.path.splitext(filename)[0]
        
    return filename


def get_directory(path: str) -> str:
    """
    パスからディレクトリ部分を抽出
    
    Args:
        path: ファイルパス
        
    Returns:
        ディレクトリパス
    """
    if not path:
        return ""
    
    return os.path.dirname(normalize_path(path))


def get_relative_path(path: str, base_path: str) -> str:
    """
    基準パスからの相対パスを取得
    
    Args:
        path: 対象パス
        base_path: 基準パス
        
    Returns:
        相対パス（パスが無関係の場合は元のパスを返す）
    """
    try:
        # 両方を正規化
        norm_path = normalize_path(path)
        norm_base = normalize_path(base_path)
        
        # os.path.relpath を使用
        return os.path.relpath(norm_path, norm_base)
    except ValueError:
        # パスが無関係（異なるドライブなど）の場合は元のパスを返す
        return path


def resolve_path(path: str, base_path: Optional[str] = None) -> str:
    """
    相対パスを絶対パスに解決する
    
    Args:
        path: 解決する相対パス
        base_path: 基準ディレクトリ（省略時はカレントディレクトリ）
        
    Returns:
        解決された絶対パス
    """
    if not path:
        return ""
    
    # すでに絶対パスなら変更なし
    if is_absolute_path(path):
        return normalize_path(path)
    
    # 基準パスを設定
    base = normalize_path(base_path) if base_path else os.getcwd()
    
    # 結合
    resolved = os.path.join(base, path)
    
    # 正規化と絶対パス変換
    return os.path.abspath(normalized_path(resolved))


def is_path_within(path: str, parent_path: str) -> bool:
    """
    パスが親ディレクトリ内にあるかを安全に確認
    
    Args:
        path: チェックするパス
        parent_path: 親ディレクトリパス
        
    Returns:
        親ディレクトリ内にあればTrue
    """
    try:
        # 両方をPath型に変換（正規化済み）
        path_obj = Path(normalize_path(path)).resolve()
        parent_obj = Path(normalize_path(parent_path)).resolve()
        
        # 親子関係をチェック
        return str(path_obj).startswith(str(parent_obj))
    except Exception:
        return False


def make_safe_filename(filename: str, replacement: str = '_') -> str:
    """
    安全なファイル名に変換する
    
    Args:
        filename: 元のファイル名
        replacement: 不正な文字の置換文字
        
    Returns:
        安全なファイル名
    """
    if not filename:
        return ""
    
    # 拡張子を保存
    base, ext = os.path.splitext(filename)
    
    # 不正な文字を置換
    safe_base = UNSAFE_FILENAME_CHARS.sub(replacement, base)
    
    # 空白の連続を1つに置換
    safe_base = re.sub(r'\s+', ' ', safe_base).strip()
    
    # 先頭と末尾のピリオドや空白を削除
    safe_base = safe_base.strip('. ')
    
    # 拡張子の不正な文字も置換
    safe_ext = UNSAFE_FILENAME_CHARS.sub(replacement, ext)
    
    # 結合
    safe_name = safe_base + safe_ext
    
    # 文字数制限（拡張子を含む）
    if IS_WINDOWS and len(safe_name) > 240:  # Windows では最大パス長に余裕を持たせる
        name_len = 240 - len(safe_ext)
        safe_name = safe_base[:name_len] + safe_ext
    
    return safe_name if safe_name else "unnamed"


def resolve_resource_path(relative_path: str, base_paths: Optional[List[str]] = None) -> str:
    """
    リソースファイルのパスを解決する（複数の基準ディレクトリから検索）
    
    Args:
        relative_path: 検索する相対パス
        base_paths: 検索するベースパスのリスト（省略時は標準的なパスを使用）
        
    Returns:
        見つかったファイルの絶対パス（見つからなければ空文字列）
    """
    if not relative_path:
        return ""
    
    # リソースファイル検索パス
    if base_paths is None:
        script_path = os.path.abspath(os.path.dirname(__file__))
        user_path = os.path.join(USER_HOME, ".mcp", "resources")
        
        base_paths = [
            os.path.join(script_path, '..', 'resources'),  # スクリプトの隣
            os.path.join(script_path, '..', '..', 'resources'),  # 1つ上の階層
            user_path,  # ユーザーのホームディレクトリ
            os.path.join(TEMP_DIR, 'mcp_resources')  # 一時ディレクトリ
        ]
    
    # 正規化
    norm_path = normalize_path(relative_path)
    
    # 絶対パスが指定された場合はそのまま返す
    if is_absolute_path(norm_path) and os.path.exists(norm_path):
        return norm_path
    
    # 各基準パスから検索
    for base_path in base_paths:
        test_path = os.path.join(normalize_path(base_path), norm_path)
        if os.path.exists(test_path):
            return test_path
    
    # 見つからなかった場合
    logger.warning(f"リソースファイルが見つかりません: {relative_path}")
    return ""


# ---------------------------------------------------------
# ファイル操作ユーティリティ
# ---------------------------------------------------------

def ensure_directory(directory_path: str) -> bool:
    """
    ディレクトリが存在することを確認し、なければ作成する
    
    Args:
        directory_path: 作成するディレクトリのパス
        
    Returns:
        成功したかどうか
    """
    if not directory_path:
        return False
    
    try:
        # 存在チェック
        if os.path.exists(directory_path):
            # ディレクトリであることを確認
            if os.path.isdir(directory_path):
                return True
            else:
                logger.error(f"パスはディレクトリではありません: {directory_path}")
                return False
        
        # ディレクトリを作成
        os.makedirs(directory_path, exist_ok=True)
        logger.debug(f"ディレクトリを作成しました: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"ディレクトリ作成エラー: {e}")
        return False


def safe_delete(path: str, validate_path: bool = True) -> bool:
    """
    ファイルまたはディレクトリを安全に削除する
    
    Args:
        path: 削除するパス
        validate_path: パスの安全性を検証するかどうか
        
    Returns:
        成功したかどうか
    """
    if not path:
        return False
    
    norm_path = normalize_path(path)
    
    # 存在チェック
    if not os.path.exists(norm_path):
        return True  # すでに存在しない
    
    # 安全性検証
    if validate_path:
        # 重要なシステムディレクトリを保護
        protected_dirs = [
            os.path.normpath("/"),
            os.path.normpath("/etc"),
            os.path.normpath("/bin"),
            os.path.normpath("/sbin"),
            os.path.normpath("/usr"),
            os.path.normpath("/var"),
            os.path.normpath("/boot"),
            os.path.normpath("/lib"),
            os.path.normpath("/lib64"),
            os.path.normpath("/dev"),
            os.path.normpath("/proc"),
            os.path.normpath("/sys"),
            os.path.normpath("/etc/blender"),
            os.path.normpath(r"C:\Windows"),
            os.path.normpath(r"C:\Program Files"),
            os.path.normpath(r"C:\Program Files (x86)")
        ]
        
        abs_path = os.path.abspath(norm_path)
        for protected in protected_dirs:
            if abs_path == protected or (IS_WINDOWS and abs_path.lower() == protected.lower()):
                logger.error(f"保護されたパスの削除は許可されていません: {path}")
                return False
            
            # パスが保護ディレクトリの下にあるかチェック
            if is_path_within(abs_path, protected):
                logger.error(f"保護されたディレクトリ内のファイル削除は許可されていません: {path}")
                return False
    
    try:
        # ファイルとディレクトリで処理を分ける
        if os.path.isdir(norm_path):
            shutil.rmtree(norm_path)
        else:
            os.remove(norm_path)
        
        logger.debug(f"パスを削除しました: {norm_path}")
        return True
    except Exception as e:
        logger.error(f"削除エラー: {e}")
        if DEBUG_MODE:
            logger.debug(traceback.format_exc())
        return False


def safe_copy(src_path: str, dst_path: str, overwrite: bool = False) -> bool:
    """
    ファイルを安全にコピーする
    
    Args:
        src_path: コピー元ファイルパス
        dst_path: コピー先ファイルパス
        overwrite: 既存ファイルを上書きするかどうか
        
    Returns:
        成功したかどうか
    """
    if not src_path or not dst_path:
        return False
    
    src_norm = normalize_path(src_path)
    dst_norm = normalize_path(dst_path)
    
    # 存在チェック
    if not os.path.exists(src_norm):
        logger.error(f"コピー元ファイルが存在しません: {src_norm}")
        return False
    
    # 同じファイルかチェック
    if os.path.normcase(os.path.abspath(src_norm)) == os.path.normcase(os.path.abspath(dst_norm)):
        logger.warning(f"コピー元とコピー先が同じです: {src_norm}")
        return True  # すでに完了している
    
    # 上書き確認
    if os.path.exists(dst_norm) and not overwrite:
        logger.warning(f"コピー先ファイルが既に存在します: {dst_norm}")
        return False
    
    try:
        # 送信先ディレクトリの作成
        dst_dir = os.path.dirname(dst_norm)
        if dst_dir:
            ensure_directory(dst_dir)
        
        # 一時ファイルにコピー
        temp_dst = dst_norm + ".tmp"
        
        # ファイルとディレクトリで処理を分ける
        if os.path.isdir(src_norm):
            if os.path.exists(temp_dst):
                shutil.rmtree(temp_dst)
            shutil.copytree(src_norm, temp_dst)
        else:
            shutil.copy2(src_norm, temp_dst)
        
        # 既存のファイルがあれば削除
        if os.path.exists(dst_norm):
            safe_delete(dst_norm, validate_path=False)
        
        # 一時ファイルを正式な名前に変更
        os.rename(temp_dst, dst_norm)
        
        logger.debug(f"ファイルをコピーしました: {src_norm} → {dst_norm}")
        return True
    except Exception as e:
        logger.error(f"コピーエラー: {e}")
        if DEBUG_MODE:
            logger.debug(traceback.format_exc())
        
        # 不完全な一時ファイルを削除
        temp_dst = dst_norm + ".tmp"
        if os.path.exists(temp_dst):
            try:
                safe_delete(temp_dst, validate_path=False)
            except:
                pass
        
        return False


def safe_move(src_path: str, dst_path: str, overwrite: bool = False) -> bool:
    """
    ファイルを安全に移動する
    
    Args:
        src_path: 移動元ファイルパス
        dst_path: 移動先ファイルパス
        overwrite: 既存ファイルを上書きするかどうか
        
    Returns:
        成功したかどうか
    """
    if not src_path or not dst_path:
        return False
    
    src_norm = normalize_path(src_path)
    dst_norm = normalize_path(dst_path)
    
    # 存在チェック
    if not os.path.exists(src_norm):
        logger.error(f"移動元ファイルが存在しません: {src_norm}")
        return False
    
    # 同じファイルかチェック
    if os.path.normcase(os.path.abspath(src_norm)) == os.path.normcase(os.path.abspath(dst_norm)):
        logger.warning(f"移動元と移動先が同じです: {src_norm}")
        return True  # すでに完了している
    
    # 上書き確認
    if os.path.exists(dst_norm) and not overwrite:
        logger.warning(f"移動先ファイルが既に存在します: {dst_norm}")
        return False
    
    try:
        # 送信先ディレクトリの作成
        dst_dir = os.path.dirname(dst_norm)
        if dst_dir:
            ensure_directory(dst_dir)
        
        # 既存のファイルがあれば削除
        if os.path.exists(dst_norm) and overwrite:
            safe_delete(dst_norm, validate_path=False)
        
        # 移動
        shutil.move(src_norm, dst_norm)
        
        logger.debug(f"ファイルを移動しました: {src_norm} → {dst_norm}")
        return True
    except Exception as e:
        logger.error(f"移動エラー: {e}")
        if DEBUG_MODE:
            logger.debug(traceback.format_exc())
        return False


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    ファイルの詳細情報を取得
    
    Args:
        file_path: ファイルパス
        
    Returns:
        ファイル情報の辞書
    """
    if not file_path or not os.path.exists(file_path):
        return {
            'exists': False,
            'path': file_path
        }
    
    norm_path = normalize_path(file_path)
    
    try:
        # 基本情報
        stat_info = os.stat(norm_path)
        is_dir = os.path.isdir(norm_path)
        
        info = {
            'exists': True,
            'path': os.path.abspath(norm_path),
            'filename': os.path.basename(norm_path),
            'directory': os.path.dirname(norm_path),
            'is_directory': is_dir,
            'size': stat_info.st_size if not is_dir else get_directory_size(norm_path),
            'created': stat_info.st_ctime,
            'modified': stat_info.st_mtime,
            'accessed': stat_info.st_atime,
            'readable': os.access(norm_path, os.R_OK),
            'writable': os.access(norm_path, os.W_OK),
            'executable': os.access(norm_path, os.X_OK)
        }
        
        # ファイル固有の情報
        if not is_dir:
            info.update({
                'extension': get_file_extension(norm_path),
                'mime_type': guess_mime_type(norm_path)
            })
        # ディレクトリ固有の情報
        else:
            try:
                contents = os.listdir(norm_path)
                info.update({
                    'file_count': len([f for f in contents if os.path.isfile(os.path.join(norm_path, f))]),
                    'dir_count': len([f for f in contents if os.path.isdir(os.path.join(norm_path, f))]),
                    'total_items': len(contents)
                })
            except:
                info.update({
                    'file_count': 0,
                    'dir_count': 0,
                    'total_items': 0
                })
        
        return info
    except Exception as e:
        logger.error(f"ファイル情報取得エラー: {e}")
        return {
            'exists': True,
            'path': norm_path,
            'error': str(e)
        }


def get_directory_size(dir_path: str) -> int:
    """
    ディレクトリの合計サイズを取得
    
    Args:
        dir_path: ディレクトリパス
        
    Returns:
        合計サイズ（バイト）
    """
    if not os.path.isdir(dir_path):
        return 0
    
    try:
        total_size = 0
        with os.scandir(dir_path) as it:
            for entry in it:
                if entry.is_file():
                    total_size += entry.stat().st_size
                elif entry.is_dir():
                    total_size += get_directory_size(entry.path)
        return total_size
    except Exception as e:
        logger.error(f"ディレクトリサイズ計算エラー: {e}")
        return 0


def guess_mime_type(file_path: str) -> str:
    """
    ファイルのMIMEタイプを推測する
    
    Args:
        file_path: ファイルパス
        
    Returns:
        MIMEタイプ文字列
    """
    try:
        import mimetypes
        mime_type, encoding = mimetypes.guess_type(file_path)
        return mime_type if mime_type else 'application/octet-stream'
    except:
        # 拡張子ベースの簡易判定（mimetypesが利用できない場合）
        ext = get_file_extension(file_path).lower()
        
        # 一般的なMIMEタイプマッピング
        mime_map = {
            'txt': 'text/plain',
            'html': 'text/html',
            'htm': 'text/html',
            'json': 'application/json',
            'xml': 'application/xml',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'pdf': 'application/pdf',
            'zip': 'application/zip',
            'tar': 'application/x-tar',
            'gz': 'application/gzip',
            'mp3': 'audio/mpeg',
            'mp4': 'video/mp4',
            'blend': 'application/x-blender',
            'py': 'text/x-python',
            'js': 'text/javascript',
            'css': 'text/css'
        }
        
        return mime_map.get(ext, 'application/octet-stream')


# ---------------------------------------------------------
# 安全なファイル読み書き
# ---------------------------------------------------------

def safe_read_file(file_path: str, encoding: str = 'utf-8', binary: bool = False) -> Union[str, bytes, None]:
    """
    安全にファイルを読み込む
    
    Args:
        file_path: ファイルパス
        encoding: 文字エンコーディング（バイナリモードでは無視）
        binary: バイナリモードで読み込むかどうか
        
    Returns:
        ファイル内容（テキストまたはバイナリ）、エラー時はNone
    """
    if not file_path:
        return None
    
    norm_path = normalize_path(file_path)
    
    if not os.path.exists(norm_path):
        logger.error(f"ファイルが存在しません: {norm_path}")
        return None
    
    try:
        mode = 'rb' if binary else 'r'
        kwargs = {} if binary else {'encoding': encoding}
        
        with open(norm_path, mode, **kwargs) as f:
            content = f.read()
        
        return content
    except Exception as e:
        logger.error(f"ファイル読み込みエラー: {e}")
        if DEBUG_MODE:
            logger.debug(traceback.format_exc())
        return None


def safe_write_file(file_path: str, content: Union[str, bytes], encoding: str = 'utf-8', 
                   binary: bool = False, atomic: bool = True) -> bool:
    """
    安全にファイルを書き込む
    
    Args:
        file_path: ファイルパス
        content: 書き込む内容（文字列またはバイト列）
        encoding: 文字エンコーディング（バイナリモードでは無視）
        binary: バイナリモードで書き込むかどうか
        atomic: アトミック書き込みを使用するかどうか
        
    Returns:
        成功したかどうか
    """
    if not file_path:
        return False
    
    norm_path = normalize_path(file_path)
    
    try:
        # ディレクトリを作成
        directory = os.path.dirname(norm_path)
        if directory and not os.path.exists(directory):
            ensure_directory(directory)
        
        # 書き込みモード
        mode = 'wb' if binary else 'w'
        kwargs = {} if binary else {'encoding': encoding}
        
        # アトミック書き込み
        if atomic:
            temp_path = norm_path + '.tmp'
            
            with open(temp_path, mode, **kwargs) as f:
                f.write(content)
            
            # 既存ファイルがあれば削除
            if os.path.exists(norm_path):
                os.remove(norm_path)
            
            # 一時ファイルを正式な名前に変更
            os.rename(temp_path, norm_path)
        else:
            # 直接書き込み
            with open(norm_path, mode, **kwargs) as f:
                f.write(content)
        
        return True
    except Exception as e:
        logger.error(f"ファイル書き込みエラー: {e}")
        if DEBUG_MODE:
            logger.debug(traceback.format_exc())
        return False


def safe_read_json(file_path: str, default: Any = None) -> Any:
    """
    安全にJSONファイルを読み込む
    
    Args:
        file_path: JSONファイルパス
        default: エラー時のデフォルト値
        
    Returns:
        JSONデータ（エラー時はデフォルト値）
    """
    content = safe_read_file(file_path)
    
    if content is None:
        return default
    
    try:
        return json.loads(content)
    except Exception as e:
        logger.error(f"JSON解析エラー: {e}")
        return default


def safe_write_json(file_path: str, data: Any, indent: int = 2, 
                   ensure_ascii: bool = False, sort_keys: bool = False) -> bool:
    """
    安全にJSONファイルを書き込む
    
    Args:
        file_path: JSONファイルパス
        data: 書き込むデータ
        indent: インデント幅
        ensure_ascii: ASCII文字のみ使用するか
        sort_keys: キーをソートするか
        
    Returns:
        成功したかどうか
    """
    try:
        content = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, 
                            sort_keys=sort_keys)
        return safe_write_file(file_path, content)
    except Exception as e:
        logger.error(f"JSON書き込みエラー: {e}")
        if DEBUG_MODE:
            logger.debug(traceback.format_exc())
        return False


def list_files(directory_path: str, recursive: bool = False, 
              include_pattern: Optional[str] = None,
              exclude_pattern: Optional[str] = None) -> List[str]:
    """
    ディレクトリ内のファイルを列挙する
    
    Args:
        directory_path: ディレクトリパス
        recursive: サブディレクトリも検索するか
        include_pattern: 含めるファイルパターン（正規表現）
        exclude_pattern: 除外するファイルパターン（正規表現）
        
    Returns:
        ファイルパスのリスト
    """
    if not directory_path or not os.path.isdir(directory_path):
        return []
    
    # 正規表現コンパイル
    include_regex = re.compile(include_pattern) if include_pattern else None
    exclude_regex = re.compile(exclude_pattern) if exclude_pattern else None
    
    result = []
    
    try:
        if recursive:
            # 再帰的に検索
            for root, _, files in os.walk(directory_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    norm_path = normalize_path(file_path)
                    
                    # フィルタリング
                    if include_regex and not include_regex.search(norm_path):
                        continue
                    if exclude_regex and exclude_regex.search(norm_path):
                        continue
                    
                    result.append(norm_path)
        else:
            # 単一ディレクトリのみ検索
            with os.scandir(directory_path) as it:
                for entry in it:
                    if entry.is_file():
                        norm_path = normalize_path(entry.path)
                        
                        # フィルタリング
                        if include_regex and not include_regex.search(norm_path):
                            continue
                        if exclude_regex and exclude_regex.search(norm_path):
                            continue
                        
                        result.append(norm_path)
    except Exception as e:
        logger.error(f"ディレクトリ走査エラー: {e}")
    
    return result


def find_files_by_extension(directory_path: str, extensions: List[str], 
                           recursive: bool = True) -> List[str]:
    """
    指定された拡張子を持つファイルを検索
    
    Args:
        directory_path: 検索するディレクトリ
        extensions: 検索する拡張子のリスト（'png', 'jpg'など、ドットなし）
        recursive: サブディレクトリも検索するか
        
    Returns:
        見つかったファイルのパスリスト
    """
    if not extensions:
        return []
    
    # 拡張子パターンを作成
    pattern_parts = []
    for ext in extensions:
        clean_ext = ext.lower().lstrip('.')
        pattern_parts.append(r'\.{}$'.format(re.escape(clean_ext)))
    
    pattern = '|'.join(pattern_parts)
    return list_files(directory_path, recursive=recursive, include_pattern=pattern)


@contextmanager
def atomic_write_file(file_path: str, mode: str = 'w', encoding: Optional[str] = 'utf-8', **kwargs) -> TextIO:
    """
    アトミック書き込みを行うためのコンテキストマネージャ
    
    Args:
        file_path: 書き込み先ファイルパス
        mode: オープンモード ('w', 'wb'など)
        encoding: 文字エンコーディング（バイナリモードでは使用されない）
        **kwargs: open()に渡す追加の引数
        
    Yields:
        ファイルオブジェクト
    """
    norm_path = normalize_path(file_path)
    temp_path = norm_path + '.tmp'
    
    # ディレクトリを確保
    directory = os.path.dirname(norm_path)
    if directory:
        ensure_directory(directory)
    
    # ファイルオープン引数
    open_kwargs = kwargs.copy()
    if 'b' not in mode and encoding:
        open_kwargs['encoding'] = encoding
    
    file_obj = None
    try:
        # 一時ファイルに書き込み
        file_obj = open(temp_path, mode, **open_kwargs)
        yield file_obj
        file_obj.flush()
        os.fsync(file_obj.fileno())
        file_obj.close()
        file_obj = None
        
        # 既存ファイルを削除して一時ファイルを移動
        if os.path.exists(norm_path):
            os.replace(temp_path, norm_path)
        else:
            os.rename(temp_path, norm_path)
    except Exception:
        # エラー時は一時ファイルを削除
        if file_obj is not None:
            file_obj.close()
        
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        
        raise


def get_free_filename(base_path: str, extension: str = "") -> str:
    """
    存在しないファイル名を生成する
    
    Args:
        base_path: 基本となるパス
        extension: 拡張子（ドット付きでも可）
        
    Returns:
        重複しない新しいファイルパス
    """
    # 拡張子の正規化
    if extension:
        if not extension.startswith('.'):
            extension = '.' + extension
    else:
        extension = ''
    
    # パスの準備
    norm_path = normalize_path(base_path)
    dir_path = os.path.dirname(norm_path)
    filename = os.path.basename(norm_path)
    
    # 拡張子を分離
    base_filename, existing_ext = os.path.splitext(filename)
    
    # 拡張子が指定されていなければ既存の拡張子を使用
    if not extension and existing_ext:
        extension = existing_ext
    
    # 重複がなければそのまま返す
    full_path = os.path.join(dir_path, base_filename + extension)
    if not os.path.exists(full_path):
        return full_path
    
    # 重複があればインデックスを付加
    counter = 1
    while True:
        new_path = os.path.join(dir_path, f"{base_filename}_{counter}{extension}")
        if not os.path.exists(new_path):
            return new_path
        counter += 1


# ---------------------------------------------------------
# 一時ファイル管理
# ---------------------------------------------------------

def create_temp_directory(prefix: str = "mcp_") -> str:
    """
    一時ディレクトリを作成
    
    Args:
        prefix: ディレクトリ名の接頭辞
        
    Returns:
        作成された一時ディレクトリのパス、失敗時は空文字列
    """
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        return normalize_path(temp_dir)
    except Exception as e:
        logger.error(f"一時ディレクトリ作成エラー: {e}")
        return ""


def create_temp_file(suffix: str = "", prefix: str = "mcp_", 
                    directory: Optional[str] = None, text: bool = True) -> str:
    """
    一時ファイルを作成
    
    Args:
        suffix: ファイル名の接尾辞（拡張子など）
        prefix: ファイル名の接頭辞
        directory: 作成するディレクトリ
        text: テキストモードで開くかどうか
        
    Returns:
        作成された一時ファイルのパス、失敗時は空文字列
    """
    try:
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory, text=text)
        os.close(fd)  # ファイルハンドルを閉じる
        return normalize_path(temp_path)
    except Exception as e:
        logger.error(f"一時ファイル作成エラー: {e}")
        return ""


@contextmanager
def temp_directory(prefix: str = "mcp_", cleanup: bool = True) -> str:
    """
    一時ディレクトリを作成して使用するコンテキストマネージャ
    
    Args:
        prefix: ディレクトリ名の接頭辞
        cleanup: 終了時に削除するかどうか
        
    Yields:
        作成された一時ディレクトリのパス
    """
    temp_dir = create_temp_directory(prefix)
    
    try:
        yield temp_dir
    finally:
        if cleanup and temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"一時ディレクトリ削除エラー: {e}")


# ---------------------------------------------------------
# リソース管理
# ---------------------------------------------------------

def get_cache_path(cache_key: str, create_dirs: bool = True) -> str:
    """
    キャッシュファイルのパスを取得
    
    Args:
        cache_key: キャッシュキー（パスとして有効であること）
        create_dirs: ディレクトリを作成するかどうか
        
    Returns:
        キャッシュファイルのパス
    """
    # 安全なファイル名に変換
    safe_key = make_safe_filename(cache_key)
    
    # キャッシュディレクトリパス
    cache_path = os.path.join(CACHE_DIR, safe_key)
    
    if create_dirs:
        # ディレクトリを作成
        ensure_directory(os.path.dirname(cache_path))
    
    return cache_path


def clear_cache(pattern: Optional[str] = None) -> int:
    """
    キャッシュファイルをクリア
    
    Args:
        pattern: 削除するファイルのパターン（正規表現）
        
    Returns:
        削除されたファイル数
    """
    if not os.path.exists(CACHE_DIR):
        return 0
    
    count = 0
    pattern_regex = re.compile(pattern) if pattern else None
    
    try:
        # キャッシュディレクトリ内のファイルを走査
        for root, _, files in os.walk(CACHE_DIR):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                # パターンフィルタリング
                if pattern_regex and not pattern_regex.search(file_path):
                    continue
                
                # ファイル削除
                if safe_delete(file_path, validate_path=False):
                    count += 1
        
        logger.debug(f"{count}個のキャッシュファイルを削除しました")
        return count
    except Exception as e:
        logger.error(f"キャッシュクリアエラー: {e}")
        return count


# ---------------------------------------------------------
# モジュール初期化
# ---------------------------------------------------------

def register():
    """ファイルユーティリティモジュールを登録"""
    # キャッシュディレクトリの作成
    ensure_directory(CACHE_DIR)
    
    logger.info("ファイルユーティリティモジュールを登録しました")


def unregister():
    """ファイルユーティリティモジュールの登録解除"""
    logger.info("ファイルユーティリティモジュールを登録解除しました")