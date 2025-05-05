"""
SimpleHttpServer - HTTP通信用のシンプルなサーバー実装
"""
import threading
import http.server
import socketserver
import json
import logging
import time
import importlib
import traceback
import urllib.parse
from typing import Dict, List, Any, Optional, Union

# ロギング設定
logger = logging.getLogger(__name__)

# シングルトンインスタンス
_server_instance = None

def get_server_instance():
    """
    シングルトンサーバーインスタンスを取得
    """
    global _server_instance
    if _server_instance is None:
        _server_instance = SimpleHttpServer()
    return _server_instance

class MCPRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    MCP用のHTTPリクエストハンドラー
    """
    def _set_response(self, content_type='application/json'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')  # CORS対応
        self.end_headers()
    
    def _load_api_handlers(self):
        """
        APIハンドラーモジュールをロード
        """
        try:
            # モジュールがインポート済みなら再ロード
            api_module = importlib.import_module('core.api_handlers')
            importlib.reload(api_module)
            return api_module
        except ImportError:
            logger.error("APIハンドラーモジュールのロードに失敗しました")
            return None
        except Exception as e:
            logger.error(f"APIハンドラーのロード中にエラーが発生しました: {str(e)}")
            traceback.print_exc()
            return None
    
    def _parse_query_params(self, query_string):
        """
        クエリパラメータをパース
        """
        if not query_string:
            return {}
        
        params = {}
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = urllib.parse.unquote(value)
        
        return params
    
    def do_GET(self):
        """
        GETリクエスト処理
        """
        # URLパスとクエリパラメータを分割
        url_parts = self.path.split('?', 1)
        path = url_parts[0]
        query_params = {}
        
        if len(url_parts) > 1:
            query_params = self._parse_query_params(url_parts[1])
        
        # 基本的なエンドポイント
        if path == "/":
            self._set_response()
            response = {"status": "success", "message": "Unified MCP API is running"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        elif path == "/status":
            self._set_response()
            response = {
                "status": "success", 
                "data": {
                    "running": True, 
                    "uptime": time.time() - self.server.start_time,
                    "endpoints": ["/", "/status", "/api/scene", "/api/objects", "/api/collections", "/api/materials"]
                }
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        # Blender APIエンドポイント
        elif path.startswith("/api/"):
            api_endpoint = path.replace("/api/", "")
            
            # APIハンドラーモジュールをロード
            api_module = self._load_api_handlers()
            
            if api_module:
                try:
                    # APIハンドラー関数を呼び出す
                    result = api_module.api_handler(api_endpoint, query_params)
                    self._set_response()
                    self.wfile.write(json.dumps(result).encode('utf-8'))
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"status": "error", "message": f"API error: {str(e)}"}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"status": "error", "message": "Failed to load API handlers"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        
        else:
            # 不明なエンドポイント
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "error", "message": f"Endpoint not found: {path}"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_POST(self):
        """
        POSTリクエスト処理
        """
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            # JSONデータのパース
            data = json.loads(post_data.decode('utf-8'))
            
            # URLパスを認識
            path = self.path
            
            # コマンド実行エンドポイント
            if path == "/api/execute":
                # APIハンドラーモジュールをロード
                api_module = self._load_api_handlers()
                
                if api_module and "command" in data:
                    try:
                        # コマンドを実行
                        result = api_module.api_handler("execute", {"command": data["command"]})
                        self._set_response()
                        self.wfile.write(json.dumps(result).encode('utf-8'))
                    except Exception as e:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        response = {"status": "error", "message": f"Command execution error: {str(e)}"}
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"status": "error", "message": "Missing 'command' parameter or API handlers not loaded"}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
            
            # オブジェクト操作エンドポイント
            elif path == "/api/object/transform":
                # APIハンドラーモジュールをロード
                api_module = self._load_api_handlers()
                
                if api_module and "name" in data:
                    # 必要なパラメータを確認
                    object_name = data["name"]
                    cmd = f"obj = bpy.data.objects.get('{object_name}')"
                    
                    if "location" in data:
                        loc = data["location"]
                        cmd += f"\nif obj: obj.location = ({loc[0]}, {loc[1]}, {loc[2]})"
                    
                    if "rotation" in data:
                        rot = data["rotation"]
                        cmd += f"\nif obj: obj.rotation_euler = ({rot[0]}, {rot[1]}, {rot[2]})"
                    
                    if "scale" in data:
                        scale = data["scale"]
                        cmd += f"\nif obj: obj.scale = ({scale[0]}, {scale[1]}, {scale[2]})"
                    
                    cmd += "\nresult = {'success': obj is not None, 'name': obj.name if obj else None}"
                    
                    try:
                        # コマンドを実行
                        result = api_module.api_handler("execute", {"command": cmd})
                        self._set_response()
                        self.wfile.write(json.dumps(result).encode('utf-8'))
                    except Exception as e:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        response = {"status": "error", "message": f"Object transform error: {str(e)}"}
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"status": "error", "message": "Missing 'name' parameter or API handlers not loaded"}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    
            # 不明なエンドポイント
            else:
                # 受信後の基本応答
                self._set_response()
                response = {"status": "success", "message": "Request received but no action taken", "data": {"received": data}}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "error", "message": "Invalid JSON data"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "error", "message": f"Server error: {str(e)}"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """ログメッセージをBlenderのロガーに出力"""
        logger.info("%s - %s" % (self.address_string(), format % args))


class SimpleHttpServer:
    """
    シンプルなHTTPサーバー実装
    """
    def __init__(self):
        self.port = 8000
        self.running = False
        self.server = None
        self.thread = None
    
    def start(self, port=8000):
        """
        サーバーを指定ポートで起動
        """
        if self.running:
            logger.warning("HTTPサーバーはすでに起動しています")
            return False
        
        self.port = port
        
        try:
            # ThreadingTCPServerでマルチスレッド対応
            socketserver.TCPServer.allow_reuse_address = True
            self.server = socketserver.ThreadingTCPServer(("", self.port), MCPRequestHandler)
            self.server.start_time = time.time()  # 起動時間を記録
            
            # 別スレッドでサーバーを実行
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True  # メインスレッド終了時に一緒に終了
            self.thread.start()
            
            self.running = True
            logger.info(f"HTTPサーバーを起動しました - ポート: {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"HTTPサーバーの起動に失敗しました: {str(e)}")
            return False
    
    def stop(self):
        """
        サーバーを停止
        """
        if not self.running:
            logger.warning("HTTPサーバーは実行していません")
            return False
        
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
            
            self.running = False
            logger.info("HTTPサーバーを停止しました")
            return True
            
        except Exception as e:
            logger.error(f"HTTPサーバー停止中にエラーが発生しました: {str(e)}")
            return False
    
    def is_running(self):
        """
        サーバーの実行状態を取得
        """
        return self.running
    
    def get_port(self):
        """
        現在のポート番号を取得
        """
        return self.port
