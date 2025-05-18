# Blender GraphQL MCP インストールガイド

このガイドでは、Blender GraphQL MCPアドオンを様々なプラットフォームにインストールする方法を説明します。

## 自動インストール（推奨）

Blender GraphQL MCPは、各プラットフォーム向けの自動インストールスクリプトを提供しています。

### Windows

1. このリポジトリをダウンロードまたはクローンします
2. PowerShellを管理者として実行します
3. リポジトリのフォルダに移動し、以下のコマンドを実行します：

```powershell
# PowerShellの実行ポリシーを一時的に変更し、スクリプトの実行を許可
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# アドオンをインストール
.\scripts\install_blender_addon.ps1
```

4. 画面の指示に従ってインストールを完了します
5. Blenderを起動し、設定からアドオンを有効化します

### macOS / Linux

1. このリポジトリをダウンロードまたはクローンします
2. ターミナルを開きます
3. リポジトリのフォルダに移動し、以下のコマンドを実行します：

```bash
# スクリプトに実行権限を付与
chmod +x scripts/install_blender_addon.sh
# アドオンをインストール
./scripts/install_blender_addon.sh
```

4. 画面の指示に従ってインストールを完了します
5. Blenderを起動し、設定からアドオンを有効化します

## 手動インストール

インストールスクリプトが動作しない場合は、以下の手順で手動インストールすることもできます：

### 全プラットフォーム共通

1. このリポジトリをダウンロードまたはクローンします
2. フォルダ名を「blender_graphql_mcp」に変更します
3. このフォルダをBlenderのアドオンディレクトリにコピーします：

   - **Windows**: `C:\Users\[ユーザー名]\AppData\Roaming\Blender Foundation\Blender\[バージョン]\scripts\addons\`
   - **macOS**: `/Users/[ユーザー名]/Library/Application Support/Blender/[バージョン]/scripts/addons/`
   - **Linux**: `~/.config/blender/[バージョン]/scripts/addons/`

4. Blenderを起動し、設定からアドオンを有効化します

## アドオンの有効化

1. Blenderを起動します
2. メニューから [編集] > [プリファレンス] を選択します
3. [アドオン] タブをクリックします
4. 検索欄に「GraphQL」または「MCP」と入力します
5. 「Blender GraphQL MCP」アドオンのチェックボックスをオンにします

## Claude Desktopとの接続設定

インストール後、Claude Desktop用の接続設定が必要です：

### Windows

```powershell
# PowerShellの実行ポリシーを一時的に変更し、スクリプトの実行を許可
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# Claude Desktop接続設定
.\scripts\setup_mcp_remote.ps1
```

### macOS / Linux

```bash
# スクリプトに実行権限を付与
chmod +x scripts/setup_mcp_remote.sh
# Claude Desktop接続設定
./scripts/setup_mcp_remote.sh
```

## トラブルシューティング

### Blenderがアドオンを認識しない

- アドオンが正しいディレクトリにインストールされているか確認してください
- `__init__.py`ファイルが存在することを確認してください
- Blenderを再起動してみてください

### 依存関係のエラー

アドオンは初回起動時に必要な依存関係を自動的にインストールしようとしますが、失敗する場合は以下の方法を試してください：

#### 方法1: アドオン設定から依存関係をインストール

1. アドオン一覧で「Blender GraphQL MCP」を見つけます
2. 展開アイコンをクリックして詳細を表示します
3. 「依存関係をインストール」ボタンをクリックします

#### 方法2: 手動で依存関係をインストール

Blenderの内蔵Pythonを使用して依存関係をインストールします：

**Windows**:
```
"C:\Program Files\Blender Foundation\Blender [バージョン]\[バージョン]\python\bin\python.exe" -m pip install --target="[アドオンディレクトリ]\blender_graphql_mcp\vendor" fastapi uvicorn pydantic graphql-core
```

**macOS**:
```
/Applications/Blender.app/Contents/Resources/[バージョン]/python/bin/python -m pip install --target="[アドオンディレクトリ]/blender_graphql_mcp/vendor" fastapi uvicorn pydantic graphql-core
```

**Linux**:
```
[Blenderインストールパス]/[バージョン]/python/bin/python -m pip install --target="[アドオンディレクトリ]/blender_graphql_mcp/vendor" fastapi uvicorn pydantic graphql-core
```

## 詳細情報

詳細な設定方法や使用方法については以下のドキュメントを参照してください：

- [README.md](README.md) - 基本的な使用方法
- [DEPENDENCY_GUIDE.md](DEPENDENCY_GUIDE.md) - 依存関係管理の詳細
- [LLM_CLIENT_SETUP.md](LLM_CLIENT_SETUP.md) - LLMクライアント接続方法
- [MCP_REMOTE_SETUP.md](MCP_REMOTE_SETUP.md) - MCP Remote設定の詳細