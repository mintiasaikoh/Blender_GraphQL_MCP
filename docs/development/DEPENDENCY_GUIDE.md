# Blender GraphQL MCP 依存関係管理ガイド

このガイドでは、Blender GraphQL MCPアドオンの依存関係管理に関する詳細情報と、最新のBlenderバージョンに合わせた最適なアプローチを説明します。

## 依存関係管理の重要性

BlenderアドオンがPython依存ライブラリを必要とする場合、それらを適切に管理することは以下の理由で重要です：

1. **ユーザーエクスペリエンス**: 依存関係がなくてもアドオンをインストールでき、必要なときに自動的にインストールされるべき
2. **バージョン管理**: Blenderの内蔵Pythonバージョンと互換性のあるライブラリバージョンを確保する必要がある
3. **競合防止**: 他のアドオンとの依存関係の競合を避ける
4. **ポータビリティ**: 異なるOSやBlenderバージョンでも動作する必要がある

## Blender依存関係管理の進化

### 従来の方法（Blender 2.8x～3.x）

初期のBlenderアドオンでは、以下の方法が使用されていました：

1. **手動インストール**: ユーザーにBlenderのPythonで依存関係をインストールするよう指示
2. **サブプロセス実行**: アドオン自体が`subprocess`でpipを実行し依存関係をインストール
3. **モジュールのバンドル**: アドオンと一緒にモジュールを直接含める（最も単純だが、メンテナンスが難しい）

### 現代的なアプローチ（Blender 4.0〜4.1）

Blender 4.0〜4.1では、以下の方法が推奨されていました：

#### 1. vendorディレクトリアプローチ（旧世代の方法）

アドオンディレクトリ内に`vendor`ディレクトリを作成し、そこにすべての依存ライブラリをインストールする方法です。

```python
# アドオンの__init__.pyで使用されるパターン
addon_path = os.path.dirname(os.path.abspath(__file__))
vendor_path = os.path.join(addon_path, "vendor")
if not os.path.exists(vendor_path):
    os.makedirs(vendor_path)

# vendorディレクトリをPythonパスに追加
if vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)
```

**メリット**:
- アドオン内で自己完結
- Blenderのシステム環境に影響しない
- アドオン間の依存関係競合を防止
- ポータブル（異なるOSでも動作）

**デメリット**:
- 各アドオンがライブラリの独自コピーを持つため、ディスク使用量が増加
- 同じライブラリの複数バージョンがメモリにロードされる可能性

#### 2. Blender 4.2以降のExtensionsシステム

Blender 4.2からは「Extensions」と呼ばれる新しいシステムが導入され、依存関係管理が大幅に改善されました。

**主な特徴**:
- TOMLファイルによるマニフェスト定義
- Python Wheelファイル（.whl）によるライブラリのバンドル
- Blenderのエクステンションマネージャーとの統合

**マニフェストファイル例（extension.toml）**:
```toml
[extension]
id = "blender_graphql_mcp"
version = "1.0.0"
name = "Blender GraphQL MCP"
tagline = "GraphQL APIでBlenderを操作"
maintainer = "Blender GraphQL MCP Team"
license = "GPL-3.0"
blender_version_min = "4.2.0"

[requirements]
pip = [
    "fastapi>=0.95.0",
    "uvicorn>=0.21.1",
    "pydantic>=1.10.7",
    "graphql-core>=3.2.3"
]
```

## Blender GraphQL MCPにおける依存関係管理

Blender GraphQL MCPは、以下の複数のアプローチをサポートしています：

### 1. Extensionsシステム（Blender 4.2以降の標準方法）

Blender 4.2以降では、`extension.toml`マニフェストとWheelファイルを使用する方法が標準です。

```toml
[extension]
id = "blender_graphql_mcp"
version = "1.0.0"
name = "Blender GraphQL MCP"
tagline = "GraphQL APIでBlenderを操作"
blender_version_min = "4.2.0"

[requirements]
pip = [
    "fastapi>=0.95.0",
    "uvicorn>=0.21.1",
    "pydantic>=1.10.7",
    "graphql-core>=3.2.3"
]
```

### 2. vendorディレクトリ（旧バージョン互換方法）

古いBlenderバージョンや、互換性のために、アドオンディレクトリ内の`vendor`ディレクトリに依存ライブラリをインストールする方法もサポートしています。

```bash
# macOS
/Applications/Blender.app/Contents/Resources/4.4/python/bin/python -m pip install --target="PATH_TO_ADDON/vendor" fastapi uvicorn pydantic graphql-core

# Windows
"C:\Program Files\Blender Foundation\Blender 4.4\4.4\python\bin\python.exe" -m pip install --target="PATH_TO_ADDON\vendor" fastapi uvicorn pydantic graphql-core

# Linux
/usr/local/blender/4.4/python/bin/python -m pip install --target="PATH_TO_ADDON/vendor" fastapi uvicorn pydantic graphql-core
```

### 2. 自動インストールシステム

アドオンには初回起動時に必要な依存関係を検出し、不足している場合は自動的にvendorディレクトリにインストールする機能があります。

```python
def ensure_dependencies():
    """必要な依存関係が入っているか確認し、なければインストールする"""
    # 依存ライブラリのインポート確認
    dependencies = {
        'graphql-core': None,
        'fastapi': None,
        'uvicorn': None,
        'pydantic': None
    }
    
    # 各パッケージをインストール（vendorディレクトリに）
    for package, version in missing:
        package_spec = f"{package}=={version}" if version else package
        cmd = [sys.executable, "-m", "pip", "install", f"--target={vendor_path}", package_spec]
        # インストール実行...
```

この機能はアドオン設定パネルの「依存関係をインストール」ボタンからも手動で実行できます。

### 3. pyproject.toml（開発者向け）

開発環境では、`pyproject.toml`を使用して依存関係を宣言することができます。

```toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "blender_graphql_mcp"
version = "1.0.0"
dependencies = [
    "fastapi>=0.95.0",
    "uvicorn>=0.21.1",
    "pydantic>=1.10.7",
    "graphql-core>=3.2.3",
]
```

開発者はこのファイルを使用して、依存関係を管理できます：

```bash
# アドオンのディレクトリで実行（開発環境用）
cd path/to/blender_graphql_mcp
/Applications/Blender.app/Contents/Resources/4.4/python/bin/python -m pip install -e .
```

### 注意点

TOMLとvendorディレクトリは相互排他的ではありません。TOMLは依存関係を宣言する形式であり、vendorディレクトリはそれらをインストールする場所です。理想的なアプローチは：

1. `pyproject.toml`で依存関係を宣言（開発者向け）
2. 実際のインストールは自動的に`vendor`ディレクトリに行う（エンドユーザー向け）
3. Blender 4.2以降では、将来的に`extension.toml`をサポートし、Extensions APIを活用

## Blender 4.4での最適な依存関係管理

Blender 4.4を含む4.2以降では、公式にExtensionsシステムが導入され、これが推奨される依存関係管理方法です。TOMLファイルを使用したマニフェスト形式での依存関係宣言が標準となりました。

### ベストプラクティス

1. **Extensionsシステムを使用する**: Blender 4.2以降では、公式のExtensionsシステムを使用する
2. **TOMLマニフェスト**: `extension.toml`で依存関係を宣言する
3. **Wheelファイル**: 依存ライブラリをWheelファイルとしてバンドルする
4. **依存関係チェック**: 起動時に依存関係が利用可能かチェックする
5. **エラーロギング**: 依存関係問題を明確に記録し、トラブルシューティング情報を提供する

## まとめ

Blender GraphQL MCPは、依存関係管理に関して複数のアプローチをサポートしていますが、Blender 4.2以降（現在の4.4を含む）では、公式のExtensionsシステムを使用することが最も推奨される方法です。

- **Blender 4.2以降**: Extensionsシステムと`extension.toml`マニフェストを使用
- **Blender 4.0〜4.1**: vendorディレクトリ方式（下位互換性のためサポート）
- **開発環境**: `pyproject.toml`を使った依存関係宣言

ExtensionsシステムはBlenderの公式機能として提供されており、アドオンの依存関係管理を簡素化し、信頼性を高めます。Blender 4.4では、このExtensionsシステムを最大限に活用することをお勧めします。