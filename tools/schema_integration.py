"""
Schema Integration
簡易版と詳細版のスキーマを統合
"""

from tools import GraphQLSchema

from .schema_mcp import create_mcp_schema
from .schema_simplified import SimplifiedSchema
from .schema_project import create_project_schema
from .schema_registry import get_schema_registry

def create_integrated_schema(mode: str = "simplified") -> GraphQLSchema:
    """
    統合スキーマを作成
    
    Args:
        mode: "simplified" (LLM向け), "full" (全機能), "custom" (カスタム)
    
    Returns:
        GraphQLSchema
    """
    
    if mode == "simplified":
        # LLM向けのシンプルなスキーマ
        return SimplifiedSchema
    
    elif mode == "full":
        # 全機能を含むスキーマ
        registry = get_schema_registry()
        
        # MCPスキーマ
        mcp_schema = create_mcp_schema()
        
        # プロジェクトスキーマ
        project_schema = create_project_schema()
        
        # その他のスキーマを登録
        # registry.merge_schemas([mcp_schema, project_schema, ...])
        
        return registry.build_schema()
    
    elif mode == "custom":
        # カスタムスキーマ（必要に応じて拡張）
        registry = get_schema_registry()
        return registry.build_schema()
    
    else:
        # デフォルトはシンプル版
        return SimplifiedSchema

def get_schema_for_context(context: dict) -> GraphQLSchema:
    """
    コンテキストに応じて最適なスキーマを選択
    
    Args:
        context: リクエストコンテキスト
    
    Returns:
        適切なGraphQLSchema
    """
    # ユーザーエージェントやヘッダーから判断
    user_agent = context.get("user_agent", "").lower()
    
    # LLMからのリクエストを検出
    if any(keyword in user_agent for keyword in ["claude", "gpt", "llm", "ai"]):
        return create_integrated_schema("simplified")
    
    # 開発者向けのリクエスト
    if context.get("developer_mode"):
        return create_integrated_schema("full")
    
    # デフォルトはシンプル版
    return create_integrated_schema("simplified")

# スキーマドキュメント
SCHEMA_DOCS = {
    "simplified": """
# Simplified Schema (LLM向け)

最もシンプルなAPI。自然言語コマンドを送信するだけで操作可能。

## 主要エンドポイント
- execute(command): コマンド実行
- state: 現在の状態取得
- batchExecute(commands): バッチ実行

## 使用例
```graphql
mutation {
  execute(command: "赤い立方体を作成") {
    success
    preview
  }
}
```
""",
    
    "full": """
# Full Schema (開発者向け)

Blender GraphQL MCPの全機能にアクセス可能。

## 主要モジュール
- MCP: コマンド実行とコンテキスト管理
- Project: プロジェクト管理
- Objects: オブジェクト操作
- Materials: マテリアル管理
- Animation: アニメーション制御

## 高度な機能
- カスタムリゾルバー
- プラグイン統合
- パフォーマンス最適化
"""
}

def get_schema_documentation(mode: str = "simplified") -> str:
    """スキーマのドキュメントを取得"""
    return SCHEMA_DOCS.get(mode, SCHEMA_DOCS["simplified"])