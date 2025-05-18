# LLM Integration Guide for Blender GraphQL MCP

## 概要

このガイドではBlender GraphQL MCPアドオンをさまざまなLLM（大規模言語モデル）クライアントと連携する方法を説明します。現在、GraphQLインターフェースと標準MCP（Model Context Protocol）の2つの主要な統合方法をサポートしています。

## 1. GraphQL API経由の連携

GraphQL APIは柔軟なクエリ機能を提供し、必要なデータのみを効率的に取得できます。

### 設定手順

1. Blender内でGraphQLサーバーを起動します
   - Blenderのサイドパネルで「GraphQL」タブを開きます
   - 「サーバー開始」ボタンをクリックします
   - デフォルトではHTTPサーバーはポート8000で起動します

2. LLMクライアントから接続します
   - エンドポイント: `http://localhost:8000/graphql`
   - メソッド: POST
   - ヘッダー: `Content-Type: application/json`
   - ボディ: GraphQLクエリ（下記参照）

### 主要なGraphQLクエリ例

#### シーンコンテキストの取得

```graphql
query {
  scene.context {
    success
    message
    name
    framesCurrent
    objectCount
    selectedObjects {
      id
      name
      type
      location { x y z }
    }
    activeObject {
      name
      type
    }
    mode
  }
}
```

#### 自然言語コマンドの実行

```graphql
mutation {
  command.executeNatural(command: "赤い立方体を作成して") {
    success
    message
    generatedCode
    executionResult {
      success
      result
    }
    preview {
      imageUrl
    }
  }
}
```

#### Pythonコードの直接実行

```graphql
mutation {
  command.executeRaw(pythonCode: """
    import bpy
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = 'MyCube'
    if obj.data.materials:
        obj.data.materials[0].diffuse_color = (1, 0, 0, 1)
    else:
        mat = bpy.data.materials.new(name="Red")
        mat.diffuse_color = (1, 0, 0, 1)
        obj.data.materials.append(mat)
  """) {
    success
    message
    result
    contextAfter {
      objectCount
    }
  }
}
```

## 2. 標準MCP（Model Context Protocol）連携

MCPは標準化されたJSONベースのプロトコルでLLMとツールの連携を効率化します。JSON-RPC 2.0に準拠しています。

### 設定手順

1. Blender内でMCPサーバーを起動します
   - Blenderのサイドパネルで「MCP」タブを開きます
   - 「Start Server」ボタンをクリックします
   - デフォルトではMCPサーバーはポート3000で起動します

2. LLMクライアントから接続します
   - エンドポイント: `http://localhost:3000/`
   - メソッド: POST
   - ヘッダー: `Content-Type: application/json`
   - ボディ: JSON-RPC 2.0リクエスト（下記参照）

### 主要なJSON-RPC 2.0リクエスト例

#### 初期化とケイパビリティのネゴシエーション

```json
{
  "jsonrpc": "2.0",
  "id": "init-1",
  "method": "initialize",
  "params": {
    "clientName": "MyLLMClient",
    "clientVersion": "1.0.0",
    "capabilities": {
      "tools": true,
      "resources": true,
      "prompts": true
    }
  }
}
```

#### 利用可能なツールのリスト取得

```json
{
  "jsonrpc": "2.0",
  "id": "tools-1",
  "method": "tools/list",
  "params": {}
}
```

#### ツールの実行（自然言語コマンド）

```json
{
  "jsonrpc": "2.0",
  "id": "call-1",
  "method": "tools/call",
  "params": {
    "name": "command.executeNatural",
    "arguments": {
      "command": "赤い立方体を作成して",
      "options": {
        "capturePreview": true
      }
    }
  }
}
```

#### リソースの取得（シーンコンテキスト）

```json
{
  "jsonrpc": "2.0",
  "id": "resource-1",
  "method": "resources/read",
  "params": {
    "uri": "blender://scene/context"
  }
}
```

## 3. LLMクライアント別設定ガイド

### Claude（Anthropic）

Claude AIとの接続には標準のMCPプロトコルが推奨されます。

#### Claude MCPツール定義例

```json
{
  "name": "blender",
  "description": "Blender 3Dモデリングソフトウェアを操作するためのツール",
  "endpoint": {
    "url": "http://localhost:3000/"
  }
}
```

### ChatGPT / GPT-4（OpenAI）

OpenAIのモデルとの連携にはJSON形式のプラグイン定義が使用できます。

#### OpenAI Plugin Manifest 例

```json
{
  "schema_version": "v1",
  "name_for_model": "blender_3d",
  "name_for_human": "Blender 3D Tool",
  "description_for_model": "Control Blender 3D modeling software to create and manipulate 3D objects and scenes.",
  "description_for_human": "Create and modify 3D objects in Blender through natural language commands.",
  "auth": {
    "type": "none"
  },
  "api": {
    "type": "openapi",
    "url": "http://localhost:8000/openapi.json"
  },
  "logo_url": "http://localhost:8000/logo.png",
  "contact_email": "support@example.com",
  "legal_info_url": "http://example.com/legal"
}
```

### Gemini（Google）

Gemini APIとの連携には標準のMCPインターフェースまたはREST API拡張を使用できます。

#### Gemini拡張ツール定義例

```json
{
  "auth": {
    "type": "none"
  },
  "endpoints": [
    {
      "name": "executeCommand",
      "description": "Execute a natural language command in Blender",
      "method": "POST",
      "url": "http://localhost:8000/graphql",
      "request": {
        "content_type": "application/json",
        "body": {
          "query": "mutation($cmd: String!) { command.executeNatural(command: $cmd) { success message generatedCode preview { imageUrl } } }",
          "variables": {
            "cmd": "{command}"
          }
        }
      }
    }
  ]
}
```

## 4. エラー処理とトラブルシューティング

### 共通エラーコード

標準MCPサーバーは以下のエラーコードを返します：

- `-32700`: Parse error - 不正なJSON
- `-32600`: Invalid Request - リクエスト形式不正
- `-32601`: Method not found - 存在しないメソッド
- `-32602`: Invalid params - パラメータ不正
- `-32603`: Internal error - 内部エラー
- `-32000`: Server error - サーバーエラー（Blender内部エラーを含む）

GraphQLエンドポイントは以下のエラー形式で返答します：

```json
{
  "data": {
    "command.executeNatural": {
      "success": false,
      "message": "コマンド実行に失敗しました",
      "error": {
        "code": "COMMAND_EXECUTION_FAILED",
        "message": "エラーメッセージ",
        "details": "詳細なエラー情報"
      }
    }
  }
}
```

### よくある問題と解決策

1. **接続エラー**
   - Blenderが実行中でサーバーが起動していることを確認
   - ファイアウォール設定を確認
   - ポート番号が正しいことを確認

2. **コマンド実行エラー**
   - より具体的なコマンドを試す
   - 現在のBlenderの状態と互換性のあるコマンドを使用する
   - エラーメッセージを確認して指示を修正する

3. **パフォーマンスの問題**
   - 複雑な操作は複数のシンプルなコマンドに分割する
   - 大きなメッシュ操作ではバッチ処理を使用する
   - プレビュー解像度を下げる

## 5. 高度な設定

### カスタムツールの追加

独自のツールを追加するには、`tools/mcp_standard_server.py`を拡張します：

```python
async def list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
    tools = await super().list_tools(params)
    # カスタムツールを追加
    tools['tools'].append({
        'name': 'my.customTool',
        'description': 'カスタムの機能を実行',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'parameter': {
                    'type': 'string',
                    'description': 'パラメータの説明'
                }
            }
        }
    })
    return tools

# カスタムツールのハンドラを実装
async def _execute_custom_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
    # 実装内容
    # ...
    return result
```

### セキュリティ設定

リモートアクセスを許可する場合は、適切な認証を設定することが重要です：

```python
# 認証設定例
def __init__(self, host='localhost', port=3000, 
           auth_enabled=False, api_key=None):
    self.host = host
    self.port = port
    self.auth_enabled = auth_enabled
    self.api_key = api_key
    # ...

async def handle_jsonrpc(self, request):
    # 認証チェック
    if self.auth_enabled:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return web.json_response({
                'jsonrpc': '2.0',
                'error': {
                    'code': ErrorCodes.AUTHENTICATION_ERROR,
                    'message': '認証が必要です'
                },
                'id': None
            }, status=401)
            
        token = auth_header.split(' ')[1]
        if token != self.api_key:
            return web.json_response({
                'jsonrpc': '2.0',
                'error': {
                    'code': ErrorCodes.AUTHENTICATION_ERROR,
                    'message': '無効な認証トークン'
                },
                'id': None
            }, status=401)
    
    # 通常の処理を継続
    # ...
```

## 6. オフラインモードでの使用

インターネット接続のない環境でローカルのLLMエンジンと接続する場合：

1. ローカルLLMの起動
   - llama.cpp、ggml、Ollama等のローカルLLMサーバーを起動
   
2. MCPサーバーの設定
   - `localhost`とデフォルトポートを使用
   - 認証を無効化（ローカル接続のみの場合）

3. ローカルLLMクライアントの設定
   - MCPプロトコルをサポートするクライアントを使用
   - localhost:3000を指定して接続

## 7. パフォーマンスに関する推奨事項

1. **効率的なクエリ**
   - GraphQLでは必要なフィールドのみをリクエスト
   - MCPでは適切なツールを選択して必要最小限の処理を実行

2. **バッチ処理**
   - 複数のシンプルな操作より単一の最適化された操作を使用
   - 大量のオブジェクト操作は一括処理する

3. **プレビュー最適化**
   - 開発中は低解像度プレビューを使用（256x256など）
   - 最終結果のみ高解像度で取得

4. **キャッシュの活用**
   - 繰り返しアクセスするコンテキスト情報はクライアント側でキャッシュ
   - 変更がない限りリソースを再取得しない

## 8. アップデートと互換性

BlenderGraphQL MCPは継続的に開発が進められています。将来のバージョンでの互換性を確保するために：

1. **非推奨の通知**
   - 古いエンドポイントは非推奨化された後も一定期間は動作継続
   - GraphQLスキーマの非推奨フィールドに注意

2. **バージョンチェック**
   - 初期化時にサーバーバージョンを確認
   - 機能に依存する前にケイパビリティをチェック

3. **フォールバックメカニズム**
   - 新機能が利用できない場合は基本機能にフォールバック
   - クライアント側でバージョン分岐ロジックを実装