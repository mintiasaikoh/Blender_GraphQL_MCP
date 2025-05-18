"""
Blender GraphQL MCP - 安全なスクリプト実行システム
execute_script.pyの安全な代替実装
"""

import bpy
import ast
import sys
import logging
import time
import traceback
from typing import Dict, Any, Optional, List, Set

logger = logging.getLogger(__name__)

class ScriptSecurityError(Exception):
    """スクリプト安全性チェックの失敗を示す例外"""
    pass

class ScriptTimeoutError(Exception):
    """スクリプト実行のタイムアウトを示す例外"""
    pass

class ScriptValidator:
    """
    安全なスクリプト実行のためのバリデータ
    
    このクラスはASTを使用して、Pythonスクリプトのコードを解析し、
    危険な操作（ファイルI/O、システムコマンド実行など）を検出します。
    """
    
    # 禁止されたモジュール
    FORBIDDEN_MODULES = {
        'os', 'subprocess', 'sys', 'shutil', 'pathlib', 
        'socket', 'urllib', 'http', 'ftplib', 'poplib', 
        'smtplib', 'telnetlib'
    }
    
    # 禁止された組み込み関数
    FORBIDDEN_BUILTINS = {
        'exec', 'eval', 'compile', '__import__', 
        'open', 'input', 'breakpoint'
    }
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.imported_modules = set()
    
    def validate(self, code: str) -> bool:
        """
        コードの安全性を検証
        
        Args:
            code: 検証するPythonコード
            
        Returns:
            bool: コードが安全であればTrue
        """
        self.errors = []
        self.warnings = []
        self.imported_modules = set()
        
        try:
            # コードをASTに解析
            tree = ast.parse(code)
            
            # 危険な構文要素のチェック
            self._check_node(tree)
            
            return len(self.errors) == 0
            
        except SyntaxError as e:
            self.errors.append(f"構文エラー: {str(e)}")
            return False
    
    def _check_node(self, node, parent_node=None):
        """ASTノードをチェック"""
        
        # Import文のチェック
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            self._check_import(node)
        
        # 組み込み関数の呼び出しチェック
        elif isinstance(node, ast.Call):
            self._check_call(node)
        
        # 属性アクセスのチェック
        elif isinstance(node, ast.Attribute):
            self._check_attribute(node)
        
        # 子ノードを再帰的にチェック
        for child in ast.iter_child_nodes(node):
            self._check_node(child, node)
    
    def _check_import(self, node):
        """Import文をチェック"""
        if isinstance(node, ast.Import):
            for name in node.names:
                module_name = name.name.split('.')[0]
                self.imported_modules.add(module_name)
                
                if module_name in self.FORBIDDEN_MODULES:
                    self.errors.append(f"禁止されたモジュール '{module_name}' がインポートされています")
        
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module.split('.')[0] if node.module else ''
            self.imported_modules.add(module_name)
            
            if module_name in self.FORBIDDEN_MODULES:
                self.errors.append(f"禁止されたモジュール '{module_name}' がインポートされています")
            
            for name in node.names:
                if name.name in self.FORBIDDEN_BUILTINS:
                    self.errors.append(f"禁止された関数 '{name.name}' がインポートされています")
    
    def _check_call(self, node):
        """関数呼び出しをチェック"""
        # 組み込み関数の直接呼び出し
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.FORBIDDEN_BUILTINS:
                self.errors.append(f"禁止された組み込み関数 '{func_name}' が使用されています")
    
    def _check_attribute(self, node):
        """属性アクセスをチェック"""
        # ファイルIOやシステム操作の検出
        attrs = []
        current = node
        
        # 属性チェーンを構築（例: os.path.unlink → ['unlink', 'path', 'os']）
        while isinstance(current, ast.Attribute):
            attrs.append(current.attr)
            current = current.value
        
        if isinstance(current, ast.Name):
            attrs.append(current.id)
            attrs.reverse()  # 元の順序に戻す
            
            # 危険な属性パターンをチェック
            self._check_dangerous_attribute_pattern(attrs)
    
    def _check_dangerous_attribute_pattern(self, attrs: List[str]):
        """危険な属性パターンをチェック"""
        if len(attrs) >= 2:
            # OSモジュールの危険なメソッド
            if attrs[0] == 'os':
                dangerous_methods = {'system', 'popen', 'spawn', 'exec', 'unlink', 'remove'}
                if len(attrs) >= 3 and attrs[1] == 'path' and attrs[2] in dangerous_methods:
                    self.errors.append(f"危険なファイル操作 'os.path.{attrs[2]}' が使用されています")
                elif len(attrs) >= 2 and attrs[1] in dangerous_methods:
                    self.errors.append(f"危険なシステム操作 'os.{attrs[1]}' が使用されています")
            
            # サブプロセス実行
            elif attrs[0] == 'subprocess' and len(attrs) >= 2:
                dangerous_methods = {'run', 'call', 'check_call', 'check_output', 'Popen'}
                if attrs[1] in dangerous_methods:
                    self.errors.append(f"危険なサブプロセス実行 'subprocess.{attrs[1]}' が使用されています")
            
            # Blender特有の危険な操作
            elif attrs[0] == 'bpy':
                if len(attrs) >= 3 and attrs[1] == 'ops' and attrs[2] == 'wm' and len(attrs) >= 4 and attrs[3] in {'save_as_mainfile', 'open_mainfile'}:
                    self.errors.append(f"ファイル操作 'bpy.ops.wm.{attrs[3]}' はセキュリティ上の理由で許可されていません")


class SafeScriptExecutor:
    """
    安全なスクリプト実行クラス
    
    このクラスは、Pythonスクリプトをセキュリティチェックした後で、
    安全性が確認できた場合にのみ制限された環境で実行します。
    """
    
    def __init__(self, max_execution_time: float = 5.0):
        """
        初期化
        
        Args:
            max_execution_time: 最大実行時間（秒）
        """
        self.validator = ScriptValidator()
        self.max_execution_time = max_execution_time
    
    def execute_script(self, script_code: str, script_name: str = "<script>") -> Dict[str, Any]:
        """
        スクリプトを安全に実行
        
        Args:
            script_code: 実行するPythonコード
            script_name: スクリプト名（エラー表示用）
            
        Returns:
            Dict: 実行結果
        """
        # スクリプトの安全性をチェック
        if not self.validator.validate(script_code):
            errors = self.validator.errors
            return {
                "success": False,
                "error": f"Security validation failed: {errors[0] if errors else 'Unknown error'}",
                "details": {
                    "errors": errors,
                    "warnings": self.validator.warnings
                }
            }
        
        # 安全な実行用の名前空間を準備
        global_namespace = self._create_safe_globals()
        local_namespace = {"__file__": script_name, "result": None}
        
        try:
            # 実行時間を計測
            start_time = time.time()
            
            # コンパイルと実行
            compiled_code = compile(script_code, script_name, 'exec')
            
            # 実行のタイムアウト監視関数
            def check_timeout():
                if time.time() - start_time > self.max_execution_time:
                    raise ScriptTimeoutError(f"スクリプトの実行が{self.max_execution_time}秒を超えました")
            
            # コード実行の監視
            original_trace = sys.gettrace()
            sys.settrace(lambda frame, event, arg: check_timeout() or original_trace(frame, event, arg) if original_trace else None)
            
            try:
                exec(compiled_code, global_namespace, local_namespace)
            finally:
                sys.settrace(original_trace)
            
            # 実行時間の確認
            execution_time = time.time() - start_time
            
            # 結果処理
            result = local_namespace.get("result", None)
            
            return {
                "success": True,
                "result": result,
                "details": {
                    "execution_time": execution_time,
                    "script_name": script_name
                }
            }
            
        except ScriptTimeoutError as e:
            return {
                "success": False,
                "error": str(e),
                "details": {
                    "timeout": self.max_execution_time,
                    "script_name": script_name
                }
            }
            
        except Exception as e:
            logger.error(f"スクリプト実行エラー: {str(e)}")
            logger.debug(traceback.format_exc())
            
            return {
                "success": False,
                "error": str(e),
                "details": {
                    "exception_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "script_name": script_name
                }
            }
    
    def execute_script_file(self, script_path: str) -> Dict[str, Any]:
        """
        スクリプトファイルを安全に実行
        
        Args:
            script_path: スクリプトファイルのパス
            
        Returns:
            Dict: 実行結果
        """
        try:
            with open(script_path, 'r') as f:
                script_code = f.read()
            
            return self.execute_script(script_code, script_path)
            
        except Exception as e:
            logger.error(f"スクリプトファイル読み込みエラー: {str(e)}")
            
            return {
                "success": False,
                "error": f"Failed to load script file: {str(e)}",
                "details": {
                    "script_path": script_path,
                    "exception_type": type(e).__name__
                }
            }
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """
        安全なグローバル名前空間を作成
        
        Returns:
            Dict: 安全なグローバル名前空間
        """
        # 安全な組み込み関数のセット
        import builtins
        safe_builtins = {}
        
        for name in dir(builtins):
            if name not in self.validator.FORBIDDEN_BUILTINS and not name.startswith('__'):
                safe_builtins[name] = getattr(builtins, name)
        
        # Blenderモジュール（読み取り専用アクセス）
        class SafeBlenderAccess:
            """安全なBlenderアクセスクラス"""
            def __init__(self):
                self.context = bpy.context
                self.data = bpy.data
                self.ops = SafeBlenderOps()
                
                # その他の必要なBlender APIにアクセス
                self.utils = bpy.utils
                self.app = SafeBlenderApp()
                self.types = bpy.types
            
            def __getattr__(self, name):
                if name not in {'context', 'data', 'ops', 'utils', 'app', 'types'}:
                    raise AttributeError(f"Access to bpy.{name} is restricted")
                return getattr(bpy, name)
        
        class SafeBlenderOps:
            """安全なBlender操作クラス"""
            def __init__(self):
                # 許可された操作のみを公開
                self.object = bpy.ops.object
                self.mesh = bpy.ops.mesh
                self.material = bpy.ops.material
                self.view3d = bpy.ops.view3d
                self.transform = bpy.ops.transform
                self.sculpt = bpy.ops.sculpt
                
                # 禁止された操作
                # wm（ファイル操作）など
            
            def __getattr__(self, name):
                if name not in {'object', 'mesh', 'material', 'view3d', 'transform', 'sculpt'}:
                    raise AttributeError(f"Access to bpy.ops.{name} may be restricted for security reasons")
                return getattr(bpy.ops, name)
        
        class SafeBlenderApp:
            """安全なBlenderアプリケーションクラス"""
            def __init__(self):
                self.version = bpy.app.version
                self.version_string = bpy.app.version_string
            
            def __getattr__(self, name):
                if name not in {'version', 'version_string'}:
                    raise AttributeError(f"Access to bpy.app.{name} is restricted")
                return getattr(bpy.app, name)
        
        # 安全なグローバル名前空間を構築
        safe_globals = {
            '__builtins__': safe_builtins,
            'bpy': SafeBlenderAccess(),
            'Vector': getattr(bpy.types, 'Vector', None),
            'Euler': getattr(bpy.types, 'Euler', None),
            'Quaternion': getattr(bpy.types, 'Quaternion', None),
            'Color': getattr(bpy.types, 'Color', None),
            'print': print,  # printは安全
            'range': range,  # rangeは安全
            'len': len,      # lenは安全
            'type': type,    # typeは安全
            'Exception': Exception,  # Exceptionは安全
        }
        
        # mathutilsがある場合は追加
        try:
            import mathutils
            safe_globals['mathutils'] = mathutils
        except ImportError:
            pass
        
        # mathモジュールは安全
        try:
            import math
            safe_globals['math'] = math
        except ImportError:
            pass
        
        return safe_globals