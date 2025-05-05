# Blender JSON MCP

Blender用JSON APIサーバー - FastAPI/GraphQLを使用したBlenderのプログラムによる操作を可能にするアドオンです。Pythonコードの実行なしで、JSONリクエストのみでBlenderを操作できます。

## 機能

- **JSON APIによるBlender操作**
  - 簡単なJSONリクエストでオブジェクトの作成・編集・削除
  - Pythonコードの直接実行が不要

- **高度なメッシュ編集**
  - ブーリアン操作
  - 面の押し出し
  - カスタムメッシュ生成
  - サブディビジョン

- **ご自身のWebアプリと細密に統合**
  - REST APIまたはGraphQLクエリで操作可能
  - ネットワーク経由でBlenderをリモート操作

- **Blender 4.4互換**
  - 最新のBlender拡張機能システムに対応

## インストール方法

1. このリポジトリをダウンロードまたはクローン
2. ファイルを`{Blenderユーザーディレクトリ}/scripts/addons/blender_json_mcp`に配置
3. Blenderを起動し、設定からアドオンを有効化

### 依存関係のインストール

アドオンは以下の外部ライブラリに依存しています：

- FastAPI
- Uvicorn
- Pydantic

これらをBlenderのPython環境にインストールするには：

```bash
/Applications/Blender.app/Contents/Resources/4.4/python/bin/python -m pip install fastapi uvicorn pydantic
```

または、`vendor`ディレクトリにインストールすることもできます：

```bash
/Applications/Blender.app/Contents/Resources/4.4/python/bin/python -m pip install --target="/Users/mymac/Library/Application Support/Blender/4.4/scripts/addons/blender_json_mcp/vendor" fastapi uvicorn pydantic
```

## 使用方法

1. Blenderのサイドバーから「MCP」タブを開く
2. 「サーバー設定」でポート番号を確認（デフォルト: 8765）
3. 「サーバー起動」ボタンをクリック
4. APIエンドポイントにHTTPリクエストを送信

### APIリクエスト例

#### キューブの作成

```bash
curl -X POST http://localhost:8765/json/create \
  -H "Content-Type: application/json" \
  -d '{
    "primitive_type": "cube", 
    "params": {
      "location": [0, 0, 0], 
      "size": 2.0, 
      "name": "MyCube", 
      "color": [1.0, 0.0, 0.0, 1.0]
    }
  }'
```

#### ブーリアン操作

```bash
curl -X POST http://localhost:8765/json/boolean \
  -H "Content-Type: application/json" \
  -d '{
    "target": "Cube", 
    "cutter": "Sphere", 
    "operation": "difference", 
    "delete_cutter": true
  }'
```

## APIエンドポイント

### 基本操作
- `/json/create` - オブジェクト作成
- `/json/delete` - オブジェクト削除
- `/json/transform` - オブジェクト変換
- `/json/scene` - シーン情報取得

### 高度なメッシュ操作
- `/json/boolean` - ブーリアン操作
- `/json/extrude` - 面の押し出し
- `/json/create_mesh` - カスタムメッシュ生成
- `/json/subdivide` - サブディビジョン

### 診断・ログ
- `/status` - サーバー状態取得
- `/api/v1/logs/detailed` - 詳細ログ取得
- `/api/v1/logs/set_level` - ログレベル設定

## ライセンス

GPL-3.0
