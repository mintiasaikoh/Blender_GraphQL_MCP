# Blender GraphQL MCP - 開発ガイドライン

> **重要**: 回答は日本語でのみ行う
>
> **重要**: 疑似コード禁止 - 実際の実装コードのみを使用すること

## 現在の開発優先事項

1. **Blender状態管理の実装**
   - シーンコンテキストの完全な取得機能
   - 選択オブジェクトの詳細情報の収集
   - ビューポート状態の把握と伝達

2. **コマンド実行エンジンの改善**
   - LLM生成コードの安全な実行機構
   - エラーハンドリングと自動リカバリーの強化
   - 実行前後の状態比較による変更検出

3. **視覚的フィードバックの充実**
   - ビューポートキャプチャの高品質化
   - 操作前後の比較画像生成
   - カメラ視点からのレンダリング

4. **GraphQLスキーマの最適化**
   - 型定義の明確化と一貫性の確保
   - エラー応答の標準化
   - ドキュメント自動生成の改善

5. **MCP対応の標準化**
   - JSON-RPC 2.0準拠の実装
   - トランスポート層の抽象化（HTTP/WebSocket）
   - セッション管理の改善

## GraphQLスキーマ改善計画

現在のスキーマ調査に基づき、以下の改善を実施します：

1. **統一された結果型インターフェースの導入**
   ```python
   def create_operation_result_interface():
       return GraphQLInterfaceType(
           name="OperationResult",
           fields={
               "success": GraphQLField(GraphQLNonNull(GraphQLBoolean), 
                                      description="操作が成功したかどうか"),
               "message": GraphQLField(GraphQLString, 
                                      description="操作の結果メッセージ"),
               "error": GraphQLField(GraphQLObjectType(
                   name="Error",
                   fields={
                       "code": GraphQLField(GraphQLNonNull(GraphQLString)),
                       "message": GraphQLField(GraphQLNonNull(GraphQLString)),
                       "details": GraphQLField(GraphQLString),
                       "path": GraphQLField(GraphQLList(GraphQLString))
                   },
                   description="エラー情報"
               )),
               "executionTimeMs": GraphQLField(GraphQLFloat, 
                                             description="実行時間（ミリ秒）")
           },
           resolve_type=lambda obj, *_: obj.get("__typename")
       )
   ```

2. **入力型の細分化**
   - ParamsInput型を分割し、目的別に特化した複数の入力型を作成
   - GeometryParams, MaterialParams, TransformParamsなどの専用型を定義
   - 冗長なフィールドを排除し、型の安全性を向上

3. **エラー処理の標準化**
   - エラーコード列挙型の導入
   - すべての結果型にError型フィールドを追加
   - エラーカテゴリ分類の実装

4. **命名規則の統一**
   - すべてのミューテーションをdomain.operation形式に統一
   - リゾルバ名とスキーマ名の一貫性確保
   - 古い命名形式は非推奨化して段階的に移行

5. **ドキュメント強化**
   - すべての型とフィールドに日本語と英語の説明を追加
   - 使用例の追加とエラーケースの文書化
   - リゾルバのドキュメント標準化

## MCP標準実装計画

JSON-RPC 2.0に準拠したModel Context Protocol (MCP)の実装を行います：

1. **標準エンドポイント実装**
   ```python
   def initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
       """クライアント機能のネゴシエーション"""
       return {
           'serverName': 'Blender GraphQL MCP',
           'serverVersion': '1.0.0',
           'capabilities': {
               'tools': True,
               'resources': True,
               'prompts': True,
               'complete': True
           }
       }
   
   def list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
       """利用可能なツール一覧"""
       return {
           'tools': [
               {
                   'name': 'command.executeNatural',
                   'description': 'Blenderで自然言語コマンドを実行',
                   'inputSchema': {
                       'type': 'object',
                       'properties': {
                           'command': {
                               'type': 'string',
                               'description': '実行するコマンド'
                           }
                       },
                       'required': ['command']
                   }
               }
           ]
       }
   ```

2. **JSON-RPC 2.0対応**
   - リクエスト/レスポンス形式の標準化
   - エラーコードの統一
   - バッチリクエストのサポート
   - 通知（一方向メッセージ）のサポート

3. **リソース管理の標準化**
   - URIベースのリソースアクセス
   - リソーステンプレートの実装
   - 複合リソースのサポート

4. **ツール実行の標準インターフェース**
   - JSON Schemaによるパラメータバリデーション
   - 実行結果の標準形式
   - エラー情報の詳細化

5. **セキュリティ対策**
   - 入力値の適切なバリデーション
   - 安全でない操作の制限
   - アクセス制御の実装

## 実装ステップ

1. **共通インターフェース実装**
   - `tools/schema_base.py`に基本インターフェース定義
   - 既存の結果型をインターフェース実装に変更
   - リゾルバの戻り値型を統一

2. **エラー処理モジュール実装**
   - `tools/schema_error.py`にエラー型と列挙型を定義
   - エラーユーティリティ関数の実装
   - リゾルバへのエラー処理組み込み

3. **入力型再設計**
   - 各ドメイン別の入力型設計と実装
   - 既存コードの新しい入力型への移行
   - 型変換ヘルパー関数の実装

4. **命名統一とリファクタリング**
   - 命名規則のリファクタリングスクリプト作成
   - 変更に伴うテストの更新
   - 非推奨インターフェースの提供

5. **ドキュメント生成改善**
   - 日英両対応のドキュメント生成
   - GraphQL IDEへの説明統合
   - 使用例の自動生成機能実装

6. **MCP標準サーバー実装**
   - `tools/mcp_standard_server.py`でJSON-RPC 2.0準拠のサーバー実装
   - GraphQLリゾルバと連携
   - Blender UI統合

## MCP標準サーバーアーキテクチャ

1. **コアコンポーネント**
   - JSON-RPC 2.0リクエストハンドラー
   - メソッド登録・実行機構
   - エラー処理システム
   - 非同期実行サポート

2. **ツール実装**
   - リゾルバ連携によるツール実行
   - パラメータマッピング
   - 結果形式変換

3. **リソース管理**
   - シーンコンテキスト・オブジェクト情報提供
   - プレビュー画像生成
   - URIルーティング

4. **プロンプトテンプレート**
   - 汎用コマンドテンプレート
   - カスタマイズ可能なパラメータ
   - 多言語サポート

5. **UIとオペレーター**
   - サーバー起動・停止制御
   - ステータス表示
   - 設定管理

## テンプレートシステムの見直し

現在のテンプレートシステムには課題があります：

1. **課題**
   - テンプレート管理の複雑さ
   - マッチング処理のオーバーヘッド
   - 柔軟性の制限

2. **改善方針**
   - 最小限の基本テンプレートのみ保持
   - 高度な操作はLLMの直接コード生成に依存
   - 実行前の安全性検証と修正提案

3. **実装ステップ**
   - `command_templates.py`の簡素化
   - LLMフォールバック機能の強化
   - コード検証とサニタイズの強化

## パフォーマンス最適化

1. **応答速度の改善**
   - GraphQLクエリ処理の最適化
   - キャッシング機構の導入
   - 不要なフィールド取得の排除

2. **大規模メッシュ処理**
   - NumPyベースのベクトル演算
   - バッチ処理によるAPIコール削減
   - インクリメンタル更新の最適化

## エラー処理の改善

1. **エラーメッセージの標準化**
   - 一貫したエラーフォーマット
   - 明確なエラーコードとメッセージ
   - 解決策の提案

2. **リカバリーメカニズム**
   - 失敗した操作の自動リトライ
   - 代替アプローチの提案
   - クリーンアップと状態復元

## 開発ガイドライン

1. **コード品質**
   - 明確な関数とクラスの命名
   - 適切なドキュメント化
   - ユニットテストの追加

2. **GraphQL開発**
   - スキーマ先行設計
   - リゾルバの適切な分割
   - バッチ処理の活用

3. **MCP対応**
   - 標準プロトコルの厳守
   - エラー応答の適切な形式
   - 非同期処理のサポート

## MCP実装の詳細仕様

1. **JSON-RPC 2.0リクエスト形式**
   ```json
   {
     "jsonrpc": "2.0",
     "id": "任意のID文字列",
     "method": "メソッド名",
     "params": {
       "パラメータ名": "値"
     }
   }
   ```

2. **JSON-RPC 2.0レスポンス形式（成功時）**
   ```json
   {
     "jsonrpc": "2.0",
     "id": "リクエストと同じID",
     "result": {
       "結果フィールド": "値"
     }
   }
   ```

3. **JSON-RPC 2.0レスポンス形式（エラー時）**
   ```json
   {
     "jsonrpc": "2.0",
     "id": "リクエストと同じID",
     "error": {
       "code": -32600,
       "message": "エラーメッセージ",
       "data": {
         "詳細情報": "値"
       }
     }
   }
   ```

4. **標準エラーコード一覧**
   - `-32700`: Parse error - 不正なJSON
   - `-32600`: Invalid Request - リクエスト形式不正
   - `-32601`: Method not found - 存在しないメソッド
   - `-32602`: Invalid params - パラメータ不正
   - `-32603`: Internal error - 内部エラー
   - `-32000`: Server error - サーバーエラー

5. **主要エンドポイント**
   - `initialize`: クライアント機能のネゴシエーション
   - `tools/list`: 利用可能なツール一覧
   - `tools/call`: ツール実行
   - `resources/list`: 利用可能なリソース一覧
   - `resources/read`: リソース取得
   - `prompts/list`: 利用可能なプロンプト一覧
   - `prompts/get`: プロンプト取得
   - `complete`: オートコンプリート機能

## テスト計画

1. **ユニットテスト**
   - 各コンポーネントの独立テスト
   - エッジケースの検証
   - メモリリークの検出

2. **統合テスト**
   - エンドツーエンドの操作シナリオ
   - 異常系テスト
   - パフォーマンステスト

## 参考ドキュメント

- [README.md](./README.md) - 基本情報と使用方法
- [DEPENDENCY_GUIDE.md](./DEPENDENCY_GUIDE.md) - 依存関係管理の詳細ガイド
- [LLM_INTEGRATION_GUIDE.md](./LLM_INTEGRATION_GUIDE.md) - LLMクライアント設定方法
- [API_ARCHITECTURE.md](./API_ARCHITECTURE.md) - アーキテクチャの詳細(使用例とアドオン統合ガイド含む)