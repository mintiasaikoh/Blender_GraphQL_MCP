# キューイングシステム

## 概要

Blender MCP アドオンは、高度なキューイングシステムを実装しています。これにより、複数のリクエストを効率的に処理できます。

## 特徴

1. **非同期/同期モード**
   - 非同期: タスクIDを即座に返し、後で結果を取得
   - 同期: 結果が出るまで待機

2. **タスク管理**
   - 一意のタスクID
   - ステータス追跡（pending, processing, completed, failed）
   - メタデータサポート

3. **キャパシティ管理**
   - 最大キューサイズ設定（デフォルト: 100）
   - キュー満杯時のエラーハンドリング

## API エンドポイント

### 1. タスク送信
```http
POST /mcp
{
    "command": "赤い立方体を作成",
    "type": "execute",
    "async": true,
    "metadata": {}
}
```

レスポンス（非同期）:
```json
{
    "task_id": "uuid-1234",
    "status": "queued"
}
```

### 2. タスクステータス取得
```http
GET /mcp/task/{task_id}
```

レスポンス:
```json
{
    "id": "uuid-1234",
    "status": "completed",
    "type": "execute",
    "created_at": "2024-01-01T00:00:00",
    "result": {
        "success": true,
        "preview": "base64_image"
    }
}
```

### 3. キューステータス
```http
POST /mcp/status
```

レスポンス:
```json
{
    "queue_size": 5,
    "pending": 3,
    "processing": 1,
    "completed": 10,
    "failed": 1,
    "current_task": "uuid-current",
    "tasks": {
        "uuid-1234": {
            "status": "completed",
            "type": "execute",
            "created_at": "2024-01-01T00:00:00"
        }
    }
}
```

## 使用例

### 非同期実行
```python
# タスクを送信
response = requests.post("http://localhost:3000/mcp", json={
    "command": "立方体を作成",
    "async": True
})

task_id = response.json()["task_id"]

# 結果をポーリング
while True:
    status = requests.get(f"http://localhost:3000/mcp/task/{task_id}")
    if status.json()["status"] in ["completed", "failed"]:
        break
    time.sleep(1)
```

### 同期実行
```python
# 結果を待つ
response = requests.post("http://localhost:3000/mcp", json={
    "command": "球体を作成",
    "async": False
})

result = response.json()
```

### バッチ処理
```python
# 複数コマンドを一度に実行
response = requests.post("http://localhost:3000/mcp", json={
    "type": "batch",
    "metadata": {
        "commands": [
            "立方体を作成",
            "球体を(1,0,0)に作成",
            "円柱を(2,0,0)に作成"
        ]
    }
})
```

## 内部実装

### QueueHandler
- タスクキューの管理
- タスク状態の追跡
- 結果の非同期取得

### 処理フロー
1. HTTPリクエスト受信（別スレッド）
2. タスクをキューに追加
3. Blenderタイマーで定期的に処理（メインスレッド）
4. 結果を保存
5. クライアントに返却

### スレッドセーフティ
- `threading.Lock`でタスク情報を保護
- `threading.Event`で結果待機を実装

## パフォーマンス考慮

1. **タイマー間隔**: 50ms
   - レスポンシブ性と負荷のバランス

2. **タイムアウト**: 30秒（同期モード）
   - 長時間タスクでのタイムアウト防止

3. **メモリ管理**
   - 完了タスクの定期的なクリーンアップ
   - キューサイズの制限

## 制限事項

1. **Blender APIアクセス**
   - メインスレッドのみ
   - タイマーコールバック内で実行

2. **キューサイズ**
   - デフォルト100タスク
   - 超過時はエラー

3. **永続性**
   - メモリ内のみ
   - Blender再起動で失われる

## まとめ

このキューイングシステムにより、Blender MCPアドオンは：
- 大量のリクエストを効率的に処理
- 非同期処理でレスポンシブなAPI
- 適切なエラーハンドリングとリトライ

を実現しています。