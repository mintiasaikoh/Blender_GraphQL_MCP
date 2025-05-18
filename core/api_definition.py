"""
Blender GraphQL MCP - API定義
全APIコンポーネントの概要と相互関係を定義
"""

# -----------------------------
# API構造の概要
# -----------------------------

"""
Blender GraphQL MCP APIは以下の構造で設計されています：

1. コマンドレイヤー（/core/commands/）
   - 基本コマンド：Blenderの標準機能を実行するコマンド
   - アドオン管理コマンド：アドオンの有効化/無効化/インストールなどを行うコマンド
   - アドオン機能コマンド：個別アドオンの機能を実行するコマンド
   - 統合コマンド：基本機能とアドオン機能を連携させるコマンド

2. GraphQLレイヤー（/tools/）
   - スキーマ定義：GraphQL型とフィールドの定義
   - リゾルバ：GraphQLクエリとミューテーションの処理関数
   - 拡張スキーマ：基本スキーマを拡張する機能別モジュール

3. アドオンブリッジ（/addons_bridge/）
   - アドオン検出：利用可能なアドオンの検出と管理
   - 機能ブリッジ：各アドオンの機能にアクセスするインターフェース
   - 互換性管理：アドオンバージョンの違いを吸収する互換レイヤー

4. MCP対応レイヤー（各モジュールに分散）
   - エラーハンドリング：統一されたエラー表現と処理
   - セキュリティ：安全なコマンド実行とバリデーション
   - ドキュメント：APIの自己記述とヘルプ機能
"""

# -----------------------------
# コンポーネント間の依存関係
# -----------------------------

"""
コンポーネント間の依存関係は以下の通りです：

1. 基本依存パス
   GraphQLクエリ/ミューテーション → リゾルバ → コマンド → Blender API

2. アドオン関連の依存パス
   GraphQLクエリ/ミューテーション → リゾルバ → アドオンコマンド → アドオンブリッジ → Blenderアドオン

3. 統合APIの依存パス
   GraphQLクエリ/ミューテーション → リゾルバ → 統合コマンド 
                                                  ↓
                            基本コマンド ← → アドオンコマンド → アドオンブリッジ
"""

# -----------------------------
# API構造のクラス図（テキスト形式）
# -----------------------------

"""
+------------------+     +------------------+     +------------------+
| GraphQLスキーマ   |     |    リゾルバ      |     |    コマンド      |
+------------------+     +------------------+     +------------------+
| - クエリ型        |     | - クエリ処理関数  |     | - 標準コマンド  |
| - ミューテーション型|    | - ミューテーション|     | - アドオンコマンド|
| - オブジェクト型   |     |   処理関数       |     | - 統合コマンド  |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         |                        |                        |
         v                        v                        v
+------------------+     +------------------+     +------------------+
|  スキーマ拡張    |     |   拡張リゾルバ   |     |  アドオンブリッジ |
+------------------+     +------------------+     +------------------+
| - アドオン型     |     | - アドオン操作   |     | - アドオン検出   |
| - 統合API型      |     | - 統合API処理    |     | - 機能ブリッジ   |
| - その他拡張     |     | - その他処理     |     | - 互換性管理     |
+------------------+     +------------------+     +------------------+
"""

# -----------------------------
# モジュール一覧と役割
# -----------------------------

API_MODULES = {
    # コアコマンド
    "/core/commands/base.py": "コマンドシステムの基本クラスと登録機能",
    "/core/commands/registry.py": "コマンド登録と管理のためのレジストリ",
    "/core/commands/addon_commands.py": "アドオン管理（有効化/無効化/インストール）コマンド",
    "/core/commands/addon_feature_commands.py": "アドオン機能実行コマンド",
    "/core/commands/integrated_commands.py": "基本機能とアドオン機能を統合したコマンド",
    
    # GraphQLモジュール
    "/tools/schema.py": "GraphQLスキーマの基本定義とビルド処理",
    "/tools/resolvers/__init__.py": "すべてのリゾルバ関数のエントリポイント",
    "/tools/resolvers/addon.py": "アドオン操作のリゾルバ",
    "/tools/schema_addon.py": "アドオン操作のGraphQLスキーマ拡張",
    "/tools/schema_addon_features.py": "アドオン機能実行のGraphQLスキーマ拡張",
    "/tools/schema_integrated.py": "統合APIのGraphQLスキーマ拡張",
    
    # アドオンブリッジ
    "/addons_bridge/__init__.py": "アドオンブリッジのメインモジュール",
    
    # その他
    "/core/api_handlers.py": "HTTP APIハンドラー",
    "/core/api_routes.py": "HTTP APIルート定義"
}

# -----------------------------
# 主要なAPI呼び出しフロー
# -----------------------------

API_FLOWS = {
    "アドオン管理フロー": [
        "GraphQL: mutation { enableAddon(addon_name: 'node_wrangler') {...} }",
        "リゾルバ: addon_resolver.enable_addon_resolver",
        "コマンド: addon_commands.enable_addon",
        "Blender API: bpy.ops.preferences.addon_enable"
    ],
    
    "アドオン機能実行フロー": [
        "GraphQL: mutation { createGeometryNodeGroup(...) {...} }",
        "リゾルバ: addon_features_resolver.create_geometry_node_group",
        "コマンド: addon_feature_commands.create_geometry_node_group",
        "アドオンブリッジ: アドオン状態確認とBlender API呼び出し"
    ],
    
    "統合APIフロー": [
        "GraphQL: mutation { createProceduralObject(...) {...} }",
        "リゾルバ: integrated_resolver.create_procedural_object",
        "コマンド: integrated_commands.create_procedural_object",
        "自動選択: 標準コマンドかアドオンコマンドか最適なものを選択",
        "実行: 選択されたコマンドを適切なパラメータで実行"
    ]
}

# -----------------------------
# APIの主要な拡張ポイント
# -----------------------------

EXTENSION_POINTS = [
    "新しいアドオン対応: addons_bridge/__init__.py のSUPPORTED_ADDONSに追加し、setup_XXX_bridge関数を実装",
    "新しいアドオン機能: core/commands/addon_feature_commands.py に機能コマンドを追加",
    "統合コマンド拡張: core/commands/integrated_commands.py に新しい統合パターンを追加",
    "GraphQLスキーマ拡張: tools/schema_addon_features.py に新しい型とミューテーションを追加"
]

# -----------------------------
# APIのバージョン情報
# -----------------------------

API_VERSION = {
    "major": 1,
    "minor": 2,
    "patch": 0,
    "description": "統合API機能を含むリリース"
}

# -----------------------------
# ドキュメントリソース
# -----------------------------

DOCUMENTATION_RESOURCES = {
    "アーキテクチャ概要": "/API_ARCHITECTURE.md",
    "使用例とチュートリアル": "/EXAMPLES.md",
    "アドオン統合ガイド": "/ADDON_INTEGRATION_GUIDE.md",
    "セキュリティと実装": "/CLAUDE.md",
    "MCPサーバーセットアップ": "/MCP_REMOTE_SETUP.md"
}

# エクスポートするコンポーネント
__all__ = ['API_MODULES', 'API_FLOWS', 'EXTENSION_POINTS', 'API_VERSION', 'DOCUMENTATION_RESOURCES']