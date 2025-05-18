# Blender GraphQL MCP 統合サーバー

このディレクトリには、Blender GraphQL MCPプロジェクトの統合サーバー実装が含まれています。統合サーバーは、GraphQLとRESTの両方のAPIインターフェースをサポートし、モジュラーなアーキテクチャで設計されています。

## 機能

- モジュール化された拡張可能なアーキテクチャ
- GraphQLとRESTの両方のAPIをサポート
- Blenderのメインスレッドとの安全な統合
- 包括的なエラーハンドリングとロギング
- 柔軟な設定システム

## モジュール構造

```
unified_server/
├── __init__.py             # パッケージの初期化
├── main.py                 # メインエントリポイント
├── adapters/               # アダプターモジュール
│   ├── blender_adapter.py  # Blenderとの通信アダプター
│   └── command_registry.py # コマンド登録と実行
├── api/                    # APIサブシステム
│   ├── base.py             # APIの基本クラス
│   ├── graphql/            # GraphQL API実装
│   └── rest/               # REST API実装
├── core/                   # コアコンポーネント
│   ├── config.py           # 設定管理
│   └── server.py           # サーバー実装
└── utils/                  # ユーティリティ
    ├── logging.py          # ロギングユーティリティ
    └── threading.py        # スレッド管理
```

## サーバーの使用方法

統合サーバーは、Pythonコードから直接使用するか、コマンドラインから実行することができます。

### Pythonからの使用

```python
from core.unified_server import UnifiedServer, ServerConfig

# サーバー設定を作成
config = ServerConfig(
    host="localhost",
    port=8000,
    enable_graphql=True,
    enable_rest=True,
    enable_docs=True
)

# サーバーを作成して初期化
server = UnifiedServer(config)
server.initialize()

# サーバーを起動
server.start()

# サーバーを停止
server.stop()
```

### コマンドラインからの使用

```bash
python -m core.unified_server.main --host=localhost --port=8000 --enable-graphql --enable-rest --enable-docs
```

または設定ファイルを使用:

```bash
python -m core.unified_server.main --config-file=server_config.json
```

## APIサブシステムの拡張

新しいAPIサブシステムを追加するには、`APISubsystem`クラスを継承し、`register_api`デコレータを使用します:

```python
from unified_server.api.base import APISubsystem, register_api

@register_api("my_api")
class MyAPI(APISubsystem):
    def __init__(self, server):
        super().__init__(server)
        
    def setup(self):
        # APIエンドポイントの設定
        pass
```

## コマンドの登録

コマンドレジストリを使用して、新しいコマンドを登録することができます:

```python
from unified_server.adapters.command_registry import register_command

@register_command("my_command", "My command description", category="general")
def my_command(param1, param2=None):
    # コマンドの実装
    return {"result": "success"}
```

## Blenderとの連携

Blenderのメインスレッドで実行する必要がある関数には、`in_blender_thread`デコレータを使用してください:

```python
from unified_server.adapters.blender_adapter import in_blender_thread

@in_blender_thread
def create_object(name, location=(0, 0, 0)):
    import bpy
    # Blenderのメインスレッドで安全に実行されるコード
    return {"object_name": name}
```