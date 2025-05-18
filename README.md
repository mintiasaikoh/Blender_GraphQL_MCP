# Blender MCP Tools

AIアシスタント（Claude等）がBlenderを操作するためのツールセット

## 概要

Blender MCP Toolsは、AIアシスタントがModel Context Protocol (MCP)を通じてBlenderを制御できるようにするツールセットです。GraphQLとMCPを統合したインターフェースにより、自然言語による3Dモデリングが可能になります。

## 主な機能

- 🤖 Model Context Protocol (MCP) サーバー
- 🛠️ GraphQLベースのAPI
- 🔧 Blender 4.2+ 対応
- 🚀 高速な非同期処理
- 🎨 自然言語による3Dモデリング
- 🧠 テンプレートベースの操作処理
- 👁️ ビジュアルフィードバック
- 🔄 状態管理と変更検出

## アーキテクチャ

Blender MCP Toolsは以下のコンポーネントで構成されています：

1. **Blenderアドオン**: Blender内部で動作し、UIと基本機能を提供
2. **標準MCP対応サーバー**: JSON-RPC 2.0準拠のLLM連携
3. **GraphQL API**: 型安全なBlender操作のためのインターフェース
4. **自然言語処理**: テキスト指示をBlender操作に変換

```
ユーザー → LLM → MCPサーバー → Blenderアドオン → Blender
```

詳細なディレクトリ構造や実装については[STRUCTURE.md](STRUCTURE.md)を参照してください。

## 対応機能

Blender MCP Toolsは以下の操作をサポートしています：

### 基本操作
- **オブジェクト操作**: 作成、変形、削除、選択
- **マテリアル操作**: 作成、適用、編集
- **カメラ・ライト**: 配置、設定、制御
- **レンダリング**: プレビュー生成、最終レンダリング

### 高度な操作
- **ブーリアン演算**: 結合、差分、交差
- **モディファイア**: サブディビジョン、ベベル等
- **VRMモデル**: キャラクターテンプレート、エクスポート
- **バッチ処理**: 複数操作の一括実行

## 技術仕様

- **対応Blenderバージョン**: 4.2以降
- **依存関係管理**: Blender Extensionsシステム
- **通信プロトコル**: JSON-RPC 2.0
- **API形式**: GraphQL
- **サーバー実装**: FastAPI, Uvicorn
- **レスポンス形式**: JSON + Base64エンコード画像

## インストール

### 超簡単インストール (推奨)

**Windows**:
```
easy_install.bat をダブルクリック
```

**macOS/Linux**:
```
./easy_install.sh
```

詳細は[インストールガイド](INSTALL.md)を参照してください。

## 使用方法

1. Blenderでアドオンを有効化
2. MCPサーバーを起動（View3D > N Panel > MCP）
3. MCPクライアントを設定して接続

## MCPクライアント設定

標準的なMCPクライアント設定例：

```json
{
  "mcpServers": {
    "blender": {
      "url": "http://localhost:8000/mcp",
      "transport": "http"
    }
  }
}
```

または直接コマンドを指定する場合：

```json
{
  "mcpServers": {
    "blender": {
      "command": "mcp-server",
      "args": ["--port", "8000"]
    }
  }
}
```

この設定により、LLMクライアントはBlender MCPサーバーと通信し、BlenderをAIで操作できるようになります。

## GraphQL APIの使用例

基本的なオブジェクト作成：

```graphql
mutation {
  execute(command: "赤い立方体を作成") {
    success
    result
    preview
    objects { name type location }
  }
}
```

シーン情報の取得：

```graphql
query {
  state {
    objects { name type location }
    selected
    mode
    preview
  }
}
```

複数コマンドのバッチ実行：

```graphql
mutation {
  batchExecute(commands: [
    "立方体を作成",
    "赤色を適用",
    "右に移動"
  ]) {
    success
    result
  }
}
```

## エラー処理

エラー発生時のレスポンス例：

```json
{
  "success": false,
  "error": {
    "code": "OBJECT_NOT_FOUND",
    "message": "指定されたオブジェクト 'Cube01' が見つかりません",
    "details": {
      "available_objects": ["Cube", "Sphere", "Camera"]
    }
  },
  "suggestions": [
    "既存のオブジェクト 'Cube' を使用してください",
    "新しいオブジェクトを作成してください"
  ]
}
```

## ドキュメント

- [ドキュメント一覧](DOCUMENTATION.md)
- [開発ガイドライン](CLAUDE.md)
- [ディレクトリ構造](STRUCTURE.md)
- [ツール一覧](TOOLS.md)

## 開発

開発に参加する場合は[CLAUDE.md](CLAUDE.md)を参照してください。現在の開発優先事項や課題について記載されています。

## ライセンス

GPL-3.0-or-later