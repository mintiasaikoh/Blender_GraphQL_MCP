# Blender GraphQL MCP - 正しいアーキテクチャ

## MCP (Model Context Protocol) の基本原則

```
LLM (Claude等) → MCP Server → Blender
```

### 1. LLM（クライアント）
- 自然言語でユーザーの意図を理解
- MCP ServerにGraphQLクエリを送信
- レスポンスを解釈してユーザーに返答

### 2. MCP Server（仲介役）
- LLMからのリクエストを受信
- GraphQL APIを提供
- Blenderとの通信を管理
- 結果をLLMに返す

### 3. Blender（実行環境）
- MCPアドオンを実行
- GraphQLクエリを処理
- 3D操作を実行
- 結果を返す

## 実装の詳細

### GraphQLフロー

```
1. LLMがユーザーのリクエストを解釈
   "赤い立方体を作成して"
   ↓
2. LLMがGraphQLクエリを生成
   mutation {
     executeNaturalCommand(command: "赤い立方体を作成") {
       success
       preview
     }
   }
   ↓
3. MCP ServerがBlenderに転送
   ↓
4. BlenderのMCPアドオンが処理
   - NLPProcessor: 自然言語解析
   - CommandExecutor: Blender操作実行
   - PreviewGenerator: 結果の可視化
   ↓
5. 結果をLLMに返却
   {
     "success": true,
     "preview": "base64_image"
   }
   ↓
6. LLMがユーザーに応答
   "赤い立方体を作成しました。[プレビュー画像]"
```

## MCPの役割

### LLMに対して
- 使いやすいGraphQL API
- 自然言語コマンドのサポート
- エラーハンドリングと提案
- ビジュアルフィードバック

### Blenderに対して
- コマンドの解釈と実行
- 状態管理
- 安全な実行環境
- 結果の構造化

## ディレクトリ構造（MCP準拠）

```
Blender_GraphQL_MCP/
├── mcp/                    # MCP実装
│   ├── server.py          # MCPサーバー
│   └── protocol.py        # MCPプロトコル
│
├── blender/               # Blenderアドオン
│   ├── __init__.py       # アドオンエントリ
│   ├── core/             # コア機能
│   ├── graphql/          # GraphQL実装
│   └── ui/               # Blender UI
│
└── llm/                   # LLM向けツール
    ├── config/           # MCP設定
    └── examples/         # 使用例
```

## 正しい使用方法

### 1. LLM（Claude）の設定

```json
{
  "mcpServers": {
    "blender": {
      "command": "python",
      "args": ["/path/to/mcp/server.py"],
      "env": {
        "BLENDER_PATH": "/path/to/blender"
      }
    }
  }
}
```

### 2. LLMからの使用

```typescript
// LLMがユーザーリクエストを処理
async function handleUserRequest(request: string) {
  // MCPサーバーにGraphQLクエリを送信
  const response = await mcp.query(`
    mutation {
      executeNaturalCommand(command: "${request}") {
        success
        result
        preview
      }
    }
  `);
  
  // 結果をユーザーに返す
  return formatResponse(response);
}
```

### 3. Blender側の処理

```python
# Blenderアドオン内
class MCPCommandHandler:
    def handle_natural_command(self, command: str):
        # 1. 自然言語を解析
        intent = self.nlp.analyze(command)
        
        # 2. Blender操作に変換
        operations = self.translator.to_operations(intent)
        
        # 3. 実行
        for op in operations:
            self.executor.execute(op)
        
        # 4. 結果を返す
        return self.formatter.format_result()
```

## まとめ

MCPは「Model Context Protocol」であり、LLMがツール（この場合Blender）を操作するためのプロトコルです。

- LLMは直接Blenderを操作しない
- MCPサーバーが仲介役
- GraphQLは通信プロトコル
- Blenderアドオンが実際の処理を担当

この構造により、LLMは複雑なBlender APIを知らなくても、自然言語で3Dモデリングができるようになります。