"""
MCP Server for Blender Addon
キューイングシステムを使用したMCPサーバー
"""

import bpy
import threading
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from .queue_handler import get_queue_handler

class MCPHTTPHandler(BaseHTTPRequestHandler):
    """MCP HTTPリクエストハンドラー"""
    
    def do_POST(self):
        """POSTリクエストを処理"""
        if self.path == '/mcp':
            self._handle_mcp_request()
        elif self.path == '/mcp/status':
            self._handle_status_request()
        else:
            self.send_error(404)
    
    def _handle_mcp_request(self):
        """MCPリクエストを処理"""
        try:
            # リクエストを読み取り
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request = json.loads(post_data.decode('utf-8'))
            
            # キューハンドラーを取得
            queue_handler = get_queue_handler()
            
            # タスクをキューに追加
            task_id = queue_handler.submit_task(
                command=request.get('command', ''),
                task_type=request.get('type', 'execute'),
                metadata=request.get('metadata', {})
            )
            
            # 非同期モードか同期モードか判別
            if request.get('async', False):
                # 非同期モード：すぐにタスクIDを返す
                response = {
                    'task_id': task_id,
                    'status': 'queued'
                }
                
                self.send_response(202)  # Accepted
                self.send_header('Content-type', 'application/json')
                self.send_header('X-Task-ID', task_id)
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            else:
                # 同期モード：結果を待つ
                result = queue_handler.wait_for_result(task_id, timeout=30.0)
                
                if result:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                else:
                    self.send_error(504, "Gateway Timeout")
                    
        except Exception as e:
            self.send_error(500, str(e))
    
    def _handle_status_request(self):
        """ステータスリクエストを処理"""
        try:
            queue_handler = get_queue_handler()
            status = queue_handler.get_queue_status()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_GET(self):
        """GETリクエストを処理"""
        if self.path.startswith('/mcp/task/'):
            # タスクステータスを取得
            task_id = self.path.split('/')[-1]
            self._get_task_status(task_id)
        elif self.path == '/mcp/health':
            # ヘルスチェック
            self._health_check()
        else:
            self.send_error(404)
    
    def _get_task_status(self, task_id: str):
        """タスクのステータスを取得"""
        try:
            queue_handler = get_queue_handler()
            task = queue_handler.get_task_status(task_id)
            
            if task:
                response = {
                    'id': task.id,
                    'status': task.status,
                    'type': task.type,
                    'created_at': task.created_at.isoformat(),
                    'result': task.result,
                    'error': task.error
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_error(404, "Task not found")
                
        except Exception as e:
            self.send_error(500, str(e))
    
    def _health_check(self):
        """ヘルスチェック"""
        response = {
            'status': 'healthy',
            'timestamp': time.time()
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

class MCPServer(threading.Thread):
    """MCPサーバースレッド"""
    
    def __init__(self, port: int = 3000):
        super().__init__(daemon=True)
        self.port = port
        self.server = None
        self.running = False
    
    def run(self):
        """サーバーを起動"""
        self.server = HTTPServer(('localhost', self.port), MCPHTTPHandler)
        self.running = True
        
        print(f"MCP Server started on port {self.port}")
        
        while self.running:
            self.server.handle_request()
    
    def stop(self):
        """サーバーを停止"""
        self.running = False
        if self.server:
            self.server.server_close()
        print("MCP Server stopped")

# Blenderオペレーター
class MCP_OT_start_server(bpy.types.Operator):
    """MCPサーバーを起動"""
    bl_idname = "mcp.start_server"
    bl_label = "Start MCP Server"
    
    port: bpy.props.IntProperty(
        name="Port",
        default=3000,
        min=1024,
        max=65535
    )
    
    def execute(self, context):
        # サーバーを起動
        addon = context.preferences.addons[__package__]
        
        if addon.mcp_server is None:
            addon.mcp_server = MCPServer(port=self.port)
            addon.mcp_server.start()
            
            # キューハンドラーを開始
            queue_handler = get_queue_handler()
            queue_handler.start_processing()
            
            self.report({'INFO'}, f"MCP Server started on port {self.port}")
        else:
            self.report({'WARNING'}, "MCP Server is already running")
        
        return {'FINISHED'}

class MCP_OT_stop_server(bpy.types.Operator):
    """MCPサーバーを停止"""
    bl_idname = "mcp.stop_server"
    bl_label = "Stop MCP Server"
    
    def execute(self, context):
        addon = context.preferences.addons[__package__]
        
        if addon.mcp_server:
            # キューハンドラーを停止
            queue_handler = get_queue_handler()
            queue_handler.stop_processing()
            
            # サーバーを停止
            addon.mcp_server.stop()
            addon.mcp_server = None
            
            self.report({'INFO'}, "MCP Server stopped")
        else:
            self.report({'WARNING'}, "MCP Server is not running")
        
        return {'FINISHED'}

class MCP_OT_queue_status(bpy.types.Operator):
    """キューの状態を表示"""
    bl_idname = "mcp.queue_status"
    bl_label = "Queue Status"
    
    def execute(self, context):
        queue_handler = get_queue_handler()
        status = queue_handler.get_queue_status()
        
        self.report({'INFO'}, f"Queue size: {status['queue_size']}, "
                             f"Pending: {status['pending']}, "
                             f"Processing: {status['processing']}, "
                             f"Completed: {status['completed']}, "
                             f"Failed: {status['failed']}")
        
        return {'FINISHED'}

# 登録
classes = [
    MCP_OT_start_server,
    MCP_OT_stop_server,
    MCP_OT_queue_status,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)