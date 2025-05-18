# Blender GraphQL MCP ドキュメント

## 概要
このプロジェクトのドキュメントは以下のように整理されています：

## メインドキュメント
- [README.md](README.md) - プロジェクト概要とクイックスタート
- [CLAUDE.md](CLAUDE.md) - 開発ガイドラインとプロジェクト状態
- [INSTALL.md](INSTALL.md) - インストール手順

## カテゴリ別ドキュメント

### 📐 アーキテクチャ
- [API設計](docs/architecture/API_ARCHITECTURE.md)
- [システム設計](docs/architecture/architecture.md)
- [統一サーバー](docs/architecture/README.md)

### 🛠 開発ガイド
- [依存関係管理](docs/development/DEPENDENCY_GUIDE.md)
- [新依存関係システム](docs/development/README.md)

### ⚡ パフォーマンス
- [最適化ガイド](docs/performance/PERFORMANCE_OPTIMIZATION.md)
- [システム最適化](docs/performance/SYSTEM_OPTIMIZATIONS.md)

### 🎯 機能別ドキュメント
- [VRM統合](docs/features/VRM_DOCUMENTATION.md)
- [セキュリティ](docs/features/SECURITY_IMPLEMENTATION.md)
- [非同期処理](docs/features/blender_async_guide.md)
- [キューシステム](docs/features/queue_system.md)
- [ユーティリティ](docs/features/UTILITIES.md)

## ドキュメント構造

```
/
├── README.md           # プロジェクト概要
├── CLAUDE.md          # 開発ガイドライン
├── INSTALL.md         # インストール手順
└── docs/
    ├── architecture/  # アーキテクチャ設計
    ├── development/   # 開発ガイド
    ├── features/      # 機能別ドキュメント
    ├── performance/   # パフォーマンス
    └── old/          # アーカイブ（削除予定）
```
