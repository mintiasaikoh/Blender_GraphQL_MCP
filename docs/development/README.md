# 新しい依存関係管理システム

## 概要

このモジュールは、Blender GraphQL MCPの依存関係管理をBlender 4.2以降のExtensionsシステムに完全に移行するためのものです。古いvendorディレクトリ方式を廃止し、Blenderの公式な拡張機能システムのみを使用します。

## 主要コンポーネント

1. **extensions_manager.py**
   - Blender 4.2+のExtensionsシステムを利用した依存関係管理
   - extension.tomlファイルの生成と管理
   - 依存関係の確認とインストール処理

2. **dependency_manager.py**
   - 依存関係管理の統合インターフェース
   - 環境チェックとエラーハンドリング
   - ステータス情報の提供

## 主な変更点

### 削除された機能

- vendorディレクトリ方式のサポート
- Blender 4.0/4.1向けの互換性コード
- 複数の依存関係管理方法の切り替え機能

### 追加された機能

- NumPyとPandasの依存関係追加
- 拡張性の高いBlender Extensionsシステムとの統合強化
- 詳細な依存関係ステータス情報の提供

## 使用方法

```python
from core.dependency_manager import ensure_dependencies, get_dependency_status

# 依存関係を確認・インストール
success = ensure_dependencies()
if not success:
    # エラー処理

# 依存関係ステータス情報の取得
status = get_dependency_status()
print(f"依存関係ステータス: {status['status']}")
print(f"メッセージ: {status['message']}")
```

## 移行ガイド

既存のコードから新システムへの移行は、以下の手順に従ってください：

1. 古い実装（`core/dependency_manager.py`と`core/extensions_manager.py`）を削除し、新しい実装に置き換える
2. コードベース内の`vendor`ディレクトリへの参照をすべて削除
3. すべてのインポートパスを更新
4. アドオンの`bl_info`をBlender 4.2以降対応に更新

## 注意点

- このシステムはBlender 4.2以降でのみ動作します
- バックグラウンドモードでの実行時は、依存関係のインストールが制限される場合があります