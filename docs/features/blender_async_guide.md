# Blender非同期処理ガイド

## Blenderの制約

Blenderは基本的にシングルスレッドアプリケーションです：

1. **メインスレッドのみがBlender APIにアクセス可能**
   - `bpy`モジュールは別スレッドから使用不可
   - UIの更新はメインスレッドのみ

2. **Pythonの非同期処理の制限**
   - `async/await`は使用可能だが、Blenderのイベントループとの統合が必要
   - 標準的な`asyncio`はそのままでは動作しない

## 実装戦略

### 1. HTTPサーバー + スレッド

```python
# BlenderアドオンでのMCPサーバー実装
class MCPServer(threading.Thread):
    def run(self):
        # 別スレッドでHTTPサーバーを実行
        self.server = HTTPServer(('localhost', 3000), MCPHandler)
        self.server.serve_forever()
```

### 2. キューベースの通信

```python
# スレッド間通信
command_queue = queue.Queue()  # コマンド用
result_queue = queue.Queue()   # 結果用

# HTTPハンドラー（別スレッド）
class MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # リクエストをキューに入れる
        command_queue.put(request)
        
        # 結果を待つ
        result = result_queue.get(timeout=10.0)
        
        # レスポンスを返す
        self.send_response(200)
        self.wfile.write(json.dumps(result).encode())
```

### 3. タイマーベースの処理

```python
# メインスレッドでの処理
class MCPProcessor:
    def start(self):
        # 定期的にキューをチェック
        bpy.app.timers.register(self.process_commands, persistent=True)
    
    def process_commands(self):
        if not command_queue.empty():
            request = command_queue.get()
            result = self.execute_command(request)
            result_queue.put(result)
        
        return 0.1  # 100ms後に再実行
```

### 4. 疑似非同期デコレーター

```python
@async_execute(callback=lambda result: print(result))
def long_running_task():
    # 別スレッドで実行される
    time.sleep(5)
    return "Task completed"
```

## ベストプラクティス

### 1. Blender APIは必ずメインスレッドで

```python
def execute_command(self, request):
    # これはメインスレッドで実行される
    if request["type"] == "create_cube":
        bpy.ops.mesh.primitive_cube_add()  # OK
```

### 2. 重い処理は別スレッドで

```python
def heavy_computation(self):
    # 別スレッドで実行
    result = complex_calculation()
    
    # 結果はキューで返す
    result_queue.put(result)
```

### 3. UIの更新はタイマーで

```python
def update_ui(self):
    # 定期的にUIを更新
    if self.has_updates:
        for area in bpy.context.screen.areas:
            area.tag_redraw()
    
    return 0.1  # 継続
```

### 4. エラーハンドリング

```python
try:
    result = command_queue.get(timeout=10.0)
except queue.Empty:
    result = {"error": "Timeout"}
except Exception as e:
    result = {"error": str(e)}
```

## 制限事項

1. **真の非同期処理は不可能**
   - `async/await`構文は使えるが、Blenderのイベントループとの統合が複雑

2. **パフォーマンスの考慮**
   - タイマーの頻度は適切に設定（100ms程度）
   - 重い処理は別スレッドへ

3. **スレッドセーフティ**
   - Blender APIは別スレッドから呼び出さない
   - 共有データへのアクセスは慎重に

## 代替アプローチ

### 1. モーダルオペレーター

```python
class MCPModalOperator(bpy.types.Operator):
    def modal(self, context, event):
        if event.type == 'TIMER':
            # 定期的に処理
            self.process_commands()
        
        return {'PASS_THROUGH'}
```

### 2. アプリケーションハンドラー

```python
def frame_change_handler(scene):
    # フレーム変更時に処理
    process_pending_commands()

bpy.app.handlers.frame_change_post.append(frame_change_handler)
```

### 3. 外部プロセス

```python
# 完全に別プロセスでMCPサーバーを実行
subprocess.Popen([sys.executable, "mcp_server.py"])
```

## まとめ

BlenderでのMCPサーバー実装は：

1. HTTPサーバーは別スレッドで実行
2. Blender APIへのアクセスはメインスレッドのみ
3. キューとタイマーでスレッド間通信
4. 重い処理は別スレッドに委譲

この設計により、Blenderの制約内で効率的なMCPサーバーを実装できます。