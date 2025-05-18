# Blender GraphQL MCP 依存関係管理の改善

CLAUDE.mdの指示に基づき、Blender GraphQL MCPの依存関係管理コードを改善しました。

## 主な変更点

1. **古いバージョン対応コードの削除**
   - レガシーモードおよびBlender 4.2未満へのサポートコードを完全に削除
   - バージョンチェック機能を追加し、4.2未満のバージョンでは明示的にエラーメッセージを表示

2. **vendorディレクトリ方式の完全削除**
   - vendor関連のコード（setup_vendor_environment関数等）を削除
   - vendorディレクトリにパッケージをインストールするコードを削除
   - `__init__.py`内のレガシーコード（ensure_dependencies_legacy）を削除

3. **Extensionsシステムへの完全移行**
   - Blender 4.2から導入されたExtensionsシステムのみを使用
   - bpy.utils.register_extension APIを活用
   - extension.tomlを使った依存関係宣言に一本化

4. **新しい依存関係管理の仕組み**
   - 簡潔でクリーンなコードに書き換え
   - 不要な互換性コードを削除し、シンプルな構造に
   - エラーハンドリングとログ機能を強化

5. **設定ファイルの強化**
   - extension.tomlに新たな依存関係（numpy, pandas）を追加
   - すべての依存関係情報を一ヶ所に集約
   - NumPyとPandasを使用した最適化機能への対応

## 修正したファイル

1. **core/dependency_manager.py**
   - 完全に書き直し、純粋にExtensionsシステムのみを使用するように変更
   - 古いvendor方式のコードを削除

2. **core/blender_version_utils.py**
   - 古いバージョン互換機能を削除
   - 明示的なバージョンチェック機能を追加（check_minimum_blender_version）

3. **__init__.py**
   - 古い依存関係管理コード（ensure_dependencies_legacy）を削除
   - 新しいExtensionsベースのコードのみを使用するように変更

4. **extension.toml**
   - numpy, pandasへの依存関係を追加（既に対応済み）

## 削除されたファイル

1. **core/extensions_manager.py**
   - その機能はcore/dependency_manager.pyに統合され、不要になった
   - 依存関係管理が単一のファイルにシンプル化された

## この変更の利点

1. **コードの簡素化**
   - 複雑な互換性コードが削除され、コードがシンプルに
   - 依存関係管理のロジックが明確で理解しやすい

2. **メンテナンスの容易さ**
   - 依存関係に関するコードが一ヶ所に集約
   - バージョン依存のロジックが少なくなり、将来の更新が容易に

3. **最新Blender APIの活用**
   - Blender 4.2+の最新機能（Extensionsシステム）を活用
   - 公式な依存関係管理方法に準拠

4. **ユーザーエクスペリエンスの向上**
   - より確実な依存関係のインストール
   - 明確なエラーメッセージによる問題診断の容易さ

## 今後の課題

1. **ドキュメントの更新**
   - ユーザーガイドやインストールガイドを更新し、Blender 4.2+が必要であることを明記

2. **テスト**
   - 新しい依存関係管理システムのテストを様々なBlender 4.2+バージョンで実施

3. **エラーハンドリングの強化**
   - より詳細なエラーメッセージとトラブルシューティングガイドの提供