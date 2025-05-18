# ディレクトリ構造

## 現在の構造

```
Blender_GraphQL_MCP/
├── __init__.py              # Blenderアドオンエントリポイント
├── README.md                # プロジェクト概要
├── INSTALL.md               # インストール手順
├── LLM_INTEGRATION_GUIDE.md # LLM連携ガイド
├── STRUCTURE.md             # ディレクトリ構造（このファイル）
├── TOOLS.md                 # ツール一覧
├── CLAUDE.md                # 開発ガイドライン
├── blender_manifest.toml    # Blenderアドオン設定
├── extension.toml           # 依存関係設定
├── LICENSE                  # ライセンスファイル
├── easy_install.py          # Pythonインストーラースクリプト
├── easy_install.bat         # Windowsインストーラー
├── easy_install.sh          # macOS/Linuxインストーラー
│
├── blender_mcp/             # 主要なパッケージディレクトリ（インストール時のルート）
│   ├── __init__.py          # パッケージ初期化
│   │
│   ├── core/                # コア機能
│   │   ├── __init__.py      # コアパッケージ初期化
│   │   ├── blender_mcp.py   # Blender MCPメインクラス 
│   │   ├── blender_context.py # Blenderコンテキスト管理
│   │   ├── command_executor.py # コマンド実行
│   │   └── mcp_command_processor.py # MCP処理
│   │
│   ├── tools/               # MCP用ツール
│   │   ├── __init__.py      # ツールパッケージ初期化
│   │   ├── handlers/        # 各種ハンドラー
│   │   │   ├── __init__.py  # ハンドラーパッケージ初期化
│   │   │   ├── improved_mcp.py # 改善版MCPハンドラー
│   │   │   └── mcp.py       # 標準MCPハンドラー
│   │   │
│   │   ├── schema_base.py   # スキーマの基本定義
│   │   ├── schema_error.py  # エラー処理定義
│   │   ├── schema_inputs.py # 入力型定義
│   │   ├── schema_improved_mcp.py # 改善版MCPスキーマ
│   │   ├── mcp_standard_server.py # 標準MCP準拠サーバー
│   │   ├── mcp_server_manager.py # サーバー管理
│   │   └── mcp_standard_integration.py # 標準MCP統合
│   │
│   ├── ui/                  # UI関連
│   │   ├── __init__.py      # UIパッケージ初期化
│   │   ├── components/      # UIコンポーネント
│   │   ├── panels.py        # Blenderパネル
│   │   └── mcp_server_panel.py # MCP専用パネル
│   │
│   ├── operators/           # Blenderオペレーター
│   │   ├── __init__.py      # オペレーターパッケージ初期化
│   │   ├── mcp_server_operators.py # MCP関連
│   │   └── execute_script.py # スクリプト実行
│   │
│   └── utils/               # ユーティリティ関数
│       ├── __init__.py      # ユーティリティパッケージ初期化
│       ├── error_handler.py # エラー処理
│       └── fileutils.py     # ファイル操作
│
└── docs/                    # ドキュメント
    ├── main/                # メインドキュメント（README.mdなどのコピー）
    ├── architecture/        # アーキテクチャ関連
    ├── development/         # 開発関連
    ├── features/            # 機能説明
    └── performance/         # パフォーマンス関連
```

## 主要コンポーネント説明

### 1. コアモジュール (`blender_mcp/core/`)

Blenderとの連携やMCPの基本処理を担当する中核部分です。

- **blender_mcp.py**: BlenderMCPクラスと連携機能の主実装
- **blender_context.py**: Blenderの状態やコンテキスト情報の管理
- **command_executor.py**: LLMから受け取ったコマンドの実行処理
- **mcp_command_processor.py**: MCP形式のコマンド処理

### 2. ツールモジュール (`blender_mcp/tools/`)

MCPとGraphQLスキーマの実装を含むツール群です。

- **handlers/**: 各種操作のハンドラー実装
- **schema_*.py**: GraphQLスキーマの定義
- **mcp_*.py**: MCP標準対応の実装

### 3. UI・オペレーター (`blender_mcp/ui/`, `blender_mcp/operators/`)

Blender内のユーザーインターフェースとオペレーターです。

- **panels.py**: Blenderのサイドパネル実装
- **mcp_server_panel.py**: MCP専用パネル
- **mcp_server_operators.py**: MCPサーバー操作オペレーター

### 4. ユーティリティ (`blender_mcp/utils/`)

共通で使われるユーティリティ関数です。

- **error_handler.py**: エラー処理と表示
- **fileutils.py**: ファイル操作処理