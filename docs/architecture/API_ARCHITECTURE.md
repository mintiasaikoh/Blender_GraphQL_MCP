# Blender GraphQL MCP API アーキテクチャ

このドキュメントでは、Blender GraphQL MCP APIの全体的なアーキテクチャと設計方針を説明します。

## 目次

1. [設計思想](#設計思想)
2. [アーキテクチャ概要](#アーキテクチャ概要)
3. [コンポーネント詳細](#コンポーネント詳細)
4. [アドオン統合ガイド](#アドオン統合ガイド)
5. [API使用例](#api使用例)
6. [セキュリティ考慮事項](#セキュリティ考慮事項)
7. [サーバーおよびAPI統合計画](#サーバーおよびapi統合計画)

## 設計思想

Blender GraphQL MCPは、以下の原則に基づいて設計されています：

1. **一貫したインターフェース**: GraphQLを通じて全機能に一貫したアクセス方法を提供
2. **シームレスな統合**: Blenderの基本機能とアドオン機能を統合的に利用可能
3. **型安全**: 強力な型システムによるAPI利用の安全性確保
4. **拡張性**: 新しい機能やアドオンを容易に追加できる構造
5. **MCP対応**: AIとの連携を意識した設計

## アーキテクチャ概要

APIは以下の主要コンポーネントで構成されています：

```
+--------------------------+
|      GraphQL API         |
|  (クエリ・ミューテーション)  |
+--------------------------+
              |
              v
+--------------------------+
|      リゾルバ層          |
|   (GraphQL→コマンド変換)  |
+--------------------------+
              |
              v
+---------------------------------------+
|              コマンド層               |
| +-------------+ +--------+ +--------+ |
| | 基本コマンド | | アドオン | | 統合   | |
| |             | | コマンド | | コマンド| |
| +-------------+ +--------+ +--------+ |
+---------------------------------------+
        |            |          |
        v            v          v
+---------------------------------------+
|          Blender & アドオン           |
+---------------------------------------+
```

## コンポーネント詳細

### 1. GraphQL API層

この層では、GraphQLスキーマを定義し、クライアントがアクセスするエンドポイントを提供します。

**主要ファイル:**
- `/graphql/schema.py`: メインのGraphQLスキーマ定義
- `/graphql/schema_addon.py`: アドオン管理スキーマ拡張
- `/graphql/schema_addon_features.py`: アドオン機能スキーマ拡張
- `/graphql/schema_integrated.py`: 統合APIスキーマ拡張

**設計ポイント:**
- すべてのエンティティと操作を型として定義
- 拡張モジュールによる機能追加を容易にする構造
- クエリ（読み取り）とミューテーション（書き込み）を明確に分離

### 2. リゾルバ層

GraphQLクエリやミューテーションからコマンド呼び出しへの変換を担当します。

**主要ファイル:**
- `/graphql/resolvers/__init__.py`: リゾルバのエントリポイント
- `/graphql/resolvers/addon.py`: アドオン関連のリゾルバ

**設計ポイント:**
- GraphQLのコンテキストとリゾルバパターンの活用
- エラーハンドリングとステータスコードの標準化
- データ型変換と検証

### 3. コマンド層

Blender操作の実際のロジックを実装します。

**主要ファイル:**
- `/core/commands/base.py`: コマンドシステムの基盤
- `/core/commands/addon_commands.py`: アドオン管理コマンド
- `/core/commands/addon_feature_commands.py`: アドオン機能コマンド
- `/core/commands/integrated_commands.py`: 統合コマンド

**設計ポイント:**
- デコレータベースのコマンド登録システム
- 明示的なパラメータ定義と型アノテーション
- 標準化されたレスポンス形式

### 4. アドオンブリッジ

Blenderアドオンとの連携を担当します。

**主要ファイル:**
- `/addons_bridge/__init__.py`: アドオンブリッジの定義

**設計ポイント:**
- サポートアドオンのリストと検出機能
- アドオン機能への標準化されたアクセス方法
- バージョンの違いを吸収する互換レイヤー

## アドオン統合ガイド

### 新しいアドオンのサポート追加手順

#### ステップ1: アドオンブリッジへの登録

`/addons_bridge/__init__.py`の`SUPPORTED_ADDONS`リストにアドオン名を追加します：

```python
SUPPORTED_ADDONS = [
    # 既存のアドオン
    "geometry_nodes",
    "node_wrangler",
    
    # 追加するアドオン
    "your_addon_name",
]
```

次に、アドオンとの連携をセットアップする関数を実装します：

```python
def setup_your_addon_bridge():
    """Your Addon との連携をセットアップ"""
    if not AddonBridge.is_addon_enabled("your_addon_name"):
        print("Unified MCP: Your Addon が有効ではありません")
        return False
    
    try:
        # アドオンモジュールのインポート
        import your_addon_name
        
        # 関数の登録
        def create_something(params):
            """アドオンの機能を実行する関数"""
            try:
                result = your_addon_name.create_something(params)
                return result
            except Exception as e:
                print(f"Unified MCP: Your Addon 関数呼び出しエラー: {str(e)}")
                return None
        
        # ブリッジに関数を登録
        AddonBridge.register_addon_function(
            "your_addon_name", 
            "create_something", 
            create_something
        )
        
        print("Unified MCP: Your Addon ブリッジを設定しました")
        return True
    except ImportError:
        print("Unified MCP: Your Addon モジュールをインポートできません")
        return False
```

さらに、`register()`関数内でセットアップ関数を呼び出すよう追加します：

```python
def register():
    """アドオンブリッジモジュールを登録"""
    # 既存のセットアップ
    setup_geometry_nodes_bridge()
    setup_animation_nodes_bridge()
    
    # 追加するアドオンのセットアップ
    setup_your_addon_bridge()
```

#### ステップ2: アドオン機能コマンドの実装

`/core/commands/addon_feature_commands.py`にアドオンの機能を実行するコマンドを追加します：

```python
@register_command("create_your_addon_feature", "あなたのアドオン機能を実行")
def create_your_addon_feature(param1: str, param2: Optional[float] = None) -> Dict[str, Any]:
    """
    あなたのアドオン機能を実行するコマンド
    
    Args:
        param1: パラメータ1の説明
        param2: パラメータ2の説明（省略可能）
        
    Returns:
        結果を含む辞書
    """
    if "your_addon_name" not in SUPPORTED_ADDONS:
        return {
            "status": "error",
            "message": "Your Addon はサポートされていません"
        }
    
    # アドオンが有効か確認
    if not AddonBridge.is_addon_enabled("your_addon_name"):
        return {
            "status": "error",
            "message": "Your Addon が有効ではありません。有効化してから再試行してください。",
            "addon_name": "your_addon_name",
            "is_enabled": False
        }
    
    try:
        # アドオンブリッジを使用して関数呼び出し
        result = AddonBridge.call_addon_function(
            "your_addon_name", 
            "create_something",
            param1, 
            param2
        )
        
        if result is None:
            return {
                "status": "error",
                "message": "Your Addon の関数呼び出しに失敗しました",
                "success": False
            }
        
        return {
            "status": "success",
            "message": f"Your Addon 機能を実行しました: {param1}",
            "feature_result": result,
            "success": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Your Addon 機能の実行中にエラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False
        }
```

#### ステップ3: GraphQLスキーマへの統合

`/graphql/schema_addon_features.py`にアドオン機能の結果型とミューテーションを追加します：

```python
# あなたのアドオン機能結果型
your_addon_result_type = GraphQLObjectType(
    name='YourAddonResult',
    fields={
        'success': GraphQLField(GraphQLBoolean, description='成功フラグ'),
        'status': GraphQLField(GraphQLString, description='ステータス'),
        'message': GraphQLField(GraphQLString, description='メッセージ'),
        'feature_result': GraphQLField(GraphQLString, description='機能の結果'),
    }
)

# アドオン機能ミューテーション
addon_feature_mutation_fields = {
    # 既存のミューテーション
    
    # あなたのアドオン機能
    'createYourAddonFeature': GraphQLField(
        your_addon_result_type,
        description='あなたのアドオン機能を実行',
        args={
            'param1': GraphQLArgument(GraphQLNonNull(GraphQLString), description='パラメータ1'),
            'param2': GraphQLArgument(GraphQLFloat, description='パラメータ2（省略可能）')
        },
        resolve=lambda obj, info, param1, param2=None: RESOLVER_MODULE.create_your_addon_feature(
            obj, info, param1, param2
        )
    ),
}

# リゾルバ関数の追加
def create_your_addon_feature(obj, info, param1, param2=None):
    from ...core.commands.addon_feature_commands import create_your_addon_feature as cmd
    result = cmd(param1, param2)
    return result

# リゾルバモジュールにメソッドを追加
setattr(RESOLVER_MODULE, 'create_your_addon_feature', create_your_addon_feature)
```

#### ステップ4: 統合APIへの追加（オプション）

より高度な統合を行う場合は、`/core/commands/integrated_commands.py`に統合コマンドを追加し、
`/graphql/schema_integrated.py`にそれをGraphQLスキーマとして公開します。

### アドオン統合のベストプラクティス

1. **適切なエラーハンドリング**: 各レイヤーで明確なエラーメッセージと状態コードを提供する
2. **型アノテーション**: すべてのパラメータとレスポンスに明確な型を定義する
3. **自動有効化**: 統合APIでは必要に応じてアドオンを自動的に有効化する
4. **ドキュメンテーション**: 各コマンドと関数に詳細なドキュメント文字列を提供する
5. **セキュリティ**: 安全なコマンド実行パターンに従い、eval()やexec()を避ける

## API使用例

### 基本的なオブジェクト操作

#### オブジェクト情報の取得

```graphql
query {
  objectInfo(name: "Cube") {
    name
    type
    location
    rotation
    scale
    visible
  }
}
```

#### 新しいオブジェクトの作成

```graphql
mutation {
  createObject(
    type: "MESH",
    primitive: "CUBE",
    name: "MyCube",
    location: [0, 0, 0],
    scale: [1, 1, 1]
  ) {
    success
    message
    object_name
  }
}
```

### アドオン管理

#### アドオン情報の取得

```graphql
query {
  addonInfo(addon_name: "node_wrangler") {
    name
    is_enabled
    description
    version
    author
    category
  }
}
```

#### アドオンの有効化

```graphql
mutation {
  enableAddon(addon_name: "node_wrangler") {
    status
    message
    addon_name
    is_enabled
  }
}
```

### アドオン機能の使用

#### ジオメトリノードの使用

```graphql
mutation {
  createGeometryNodeGroup(
    name: "MyGeometryNodes",
    object_name: "MyCube",
    setup_type: "PROCEDURAL_LANDSCAPE"
  ) {
    success
    message
    node_group_name
    modifier_name
  }
}
```

#### PBRマテリアルの設定

```graphql
mutation {
  setupPBRMaterial(
    material_name: "MetalMaterial",
    base_color: "#8A8A8A",
    metallic: 1.0,
    roughness: 0.2
  ) {
    success
    message
    material_name
    nodes_created
  }
}
```

### 統合API

#### プロシージャルオブジェクトの作成

```graphql
mutation {
  createProceduralObject(
    object_type: "LANDSCAPE",
    name: "TerrainMountain",
    params: {
      size: 20.0,
      resolution: 64,
      height: 5.0,
      noise_scale: 1.5,
      material_color: "#7CB36B"
    }
  ) {
    success
    message
    object_name
    object_type
  }
}
```

#### 高度なマテリアル作成

```graphql
mutation {
  createAdvancedMaterial(
    material_type: "METAL",
    name: "GoldMaterial",
    params: {
      metal_type: "gold",
      roughness: 0.2,
      color: "#FFD700"
    }
  ) {
    success
    message
    material_name
    material_type
  }
}
```

### 実際のシナリオ例

#### 山岳地形の作成

```graphql
# 山岳地形の作成
mutation {
  createProceduralObject(
    object_type: "LANDSCAPE",
    name: "MountainRange",
    params: {
      size: 30.0,
      resolution: 128,
      height: 8.0,
      noise_scale: 2.0,
      seed: 42,
      material_color: "#7CB36B"
    }
  ) {
    success
    message
    object_name
  }
}
```

#### 金属球体のアニメーション

```graphql
# 1. 球体作成
mutation {
  createProceduralObject(
    object_type: "PROCEDURAL_SPHERE",
    name: "MetalBall",
    params: {
      radius: 1.5,
      subdivision: 3,
      distortion: 0.1
    }
  ) {
    object_name
  }
}

# 2. 金属マテリアル適用
mutation {
  createAdvancedMaterial(
    material_type: "METAL",
    name: "ChromeMaterial",
    params: {
      metal_type: "silver",
      roughness: 0.1
    }
  ) {
    material_name
  }
}

# 3. アニメーション設定
mutation {
  createAnimationNodeTree(
    name: "BouncingAnimation",
    setup_type: "OBJECT_WIGGLE",
    target_object: "MetalBall"
  ) {
    success
  }
}
```

## セキュリティ考慮事項

API設計では以下のセキュリティ対策を実装しています：

1. **コマンドの明示的な登録**: デコレータベースのシステムで許可されたコマンドのみ実行可能
2. **パラメータの厳格な検証**: すべての入力パラメータの検証とサニタイズ
3. **安全な関数呼び出し**: exec()やeval()の代わりにコマンドパターンを使用
4. **情報漏洩の防止**: エラーメッセージで内部詳細を露出させない
5. **型安全なAPI設計**: GraphQLの型システムを活用した安全なインターフェース

## サーバーおよびAPI統合計画

複雑さを減らし（"ごちゃごちゃ"を解消）、より整理されたコード構造を実現するため、以下のサーバーおよびAPI統合の改善を計画しています：

### 目標

1. **サーバー実装の統合**: 現在複数ある実装を単一の統一サーバーに集約
2. **API層の簡素化**: 重複するAPI層を整理し、一貫性のあるインターフェースを提供
3. **コード構造の改善**: より明確な責任分担と疎結合のアーキテクチャへの移行

### 主要な変更点

#### サーバー統合

```
【現在】
+----------------+  +----------------+  +----------------+
|  WebSocket     |  |  HTTP          |  |  Local         |
|  サーバー       |  |  サーバー       |  |  サーバー       |
+----------------+  +----------------+  +----------------+
        |                   |                   |
        v                   v                   v
+------------------------------------------------+
|               GraphQL API                       |
+------------------------------------------------+

【統合後】
+------------------------------------------------+
|               統合サーバー                        |
|  +---------------+  +----------------------+   |
|  | コア機能       |  | プロトコルアダプター    |   |
|  | (実行エンジン) |  | (HTTP/WS/Local)      |   |
|  +---------------+  +----------------------+   |
+------------------------------------------------+
                      |
                      v
+------------------------------------------------+
|               統一GraphQL API                    |
+------------------------------------------------+
```

#### API層の改良

1. **単一エントリーポイント**: すべてのクライアントが同一のエントリーポイントを使用
2. **プロトコル非依存設計**: 通信プロトコルに依存しない抽象化されたAPI設計
3. **統一されたスキーマ**: すべての機能とアドオンで一貫したスキーマ設計

#### コード構造の改善

1. **明確なレイヤー分離**: プレゼンテーション層、ビジネスロジック層、データアクセス層の明確な分離
2. **依存性の明示化**: 暗黙の依存関係を明示的モジュール間インターフェースに置き換え
3. **共通インフラの統合**: ロギング、エラーハンドリング、設定管理の共通化

### 移行戦略

この統合は段階的に行われ、既存の機能を維持しながら、コードベースを徐々に改善していきます。詳細な実装計画は別途「サーバー統合提案書」と「API統合提案書」に記載されています。

## まとめ

Blender GraphQL MCPは、GraphQLの型安全性と一貫したインターフェースを活用し、Blenderの基本機能とアドオン機能をシームレスに統合するAPIを提供します。この設計により、AIが効率的かつ安全にBlenderを操作できるようになり、ユーザーは自然言語指示で複雑なモデリング作業を行えるようになります。さらに、計画されているサーバーおよびAPI統合により、コードベースの複雑さが減少し、メンテナンス性と拡張性が向上します。