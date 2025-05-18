# ディレクトリ構造

## 現在の構造

```
Blender_MCP_Tools/
├── __init__.py              # Blenderアドオンエントリポイント
├── README.md                # プロジェクト概要
├── DOCUMENTATION.md         # ドキュメントインデックス
├── extension.toml           # 依存関係設定
├── install_to_blender.py    # インストーラー
│
├── core/                    # コア機能
│   ├── unified_server/      # 統一サーバー
│   ├── mcp/                 # MCPサーバー関連
│   ├── commands/            # コマンドシステム
│   ├── context/             # Blenderコンテキスト管理
│   └── utils/               # ユーティリティ
│
├── tools/                   # LLM用ツール（旧GraphQL）
│   ├── handlers/            # ツールハンドラー（旧resolvers）
│   ├── definitions/         # ツール定義（旧schema）
│   └── constants.py         # 定数定義
│
├── ui/                      # UI関連
│   ├── panels.py            # Blenderパネル
│   └── components/          # UIコンポーネント
│
├── docs/                    # ドキュメント
│   ├── architecture/        # アーキテクチャ
│   ├── development/         # 開発ガイド
│   ├── features/            # 機能別
│   └── performance/         # パフォーマンス
│
└── tests/                   # テスト
```

## ツールセットの説明

`tools/`ディレクトリには、LLMがBlenderを操作するためのツールが含まれています：

- **handlers/**: 各ツールの実際の処理を行うハンドラー
- **definitions/**: ツールのインターフェース定義
- **constants.py**: 共通で使用する定数

これらは旧GraphQL APIをより分かりやすく再構成したものです。
