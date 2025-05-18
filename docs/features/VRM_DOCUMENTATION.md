# VRM機能拡張 - 実装内容

## 概要

Blender GraphQL MCPにVTuberモデル制作向けのVRM機能拡張を実装しました。この拡張により、VRMモデルの作成、リギング、表情制作、エクスポート、Unity連携などが可能になります。

## 実装されたファイル

1. **VRMリゾルバ**: `/graphql/resolvers/vrm.py`
   - VTuberモデル制作の主要機能を実装
   - モデル作成、テンプレート適用、リギング、ウェイト割り当てなど

2. **GraphQLスキーマ拡張**: `/graphql/schema.py`
   - VRM関連の型定義の追加
   - クエリとミューテーションの定義

3. **リゾルバ統合**: `/graphql/resolvers/__init__.py`
   - VRMリゾルバの統合
   - API関数の登録

4. **使用方法ドキュメント**: `/VRM_USAGE.md`
   - VRM機能の使用方法の説明
   - GraphQLクエリ例の提供

## 実装された機能

### モデル管理
- VRMモデルの作成と管理
- テンプレートの適用

### リギング機能
- VRM準拠ボーンセット自動生成
- 自動ウェイト割り当て

### 表情制作
- ブレンドシェイプ（表情）の追加と編集
- 表情カテゴリ管理

### エクスポート
- VRMフォーマットへのエクスポート
- Unity用FBXエクスポート
- メタデータ設定

### Unity連携
- Unityプロジェクトのセットアップ
- Unity Editorへのエクスポート
- マテリアル生成サポート

## GraphQL API

### クエリ
- `vrmModels`: VRMモデル一覧の取得
- `vrmModel`: 指定されたVRMモデルの情報取得

### ミューテーション
- `createVrmModel`: 新規VRMモデルの作成
- `applyVrmTemplate`: テンプレートの適用
- `generateVrmRig`: VRM準拠リグの生成
- `assignAutoWeights`: 自動ウェイト割り当て
- `addBlendShape`: ブレンドシェイプの追加
- `updateBlendShape`: ブレンドシェイプの更新
- `exportVrm`: VRMとしてエクスポート
- `exportFbxForUnity`: Unity用FBXエクスポート
- `validateVrmModel`: VRMモデルの検証
- `setupUnityProject`: Unityプロジェクトのセットアップ
- `exportToUnityEditor`: Unity Editorへのエクスポート
- `generateUnityMaterials`: Unityマテリアルの生成

## データ構造

### VRMモデル
- `id`: モデルID
- `name`: モデル名
- `version`: バージョン
- `metadata`: VRMメタデータ
- `rootBone`: ルートボーン情報
- `blendShapes`: ブレンドシェイプのリスト
- `meshes`: メッシュオブジェクトのリスト
- `materials`: マテリアルのリスト

## 実装上の注意点

1. **VRMアドオンの要件**:
   - 実際のVRMエクスポートには、追加のVRMアドオン（UniVRMなど）が必要です。

2. **Unity連携**:
   - Unity側での追加設定やスクリプト実行が必要な場合があります。

3. **拡張性**:
   - 新しいVRM仕様やUnity連携機能に応じて拡張可能な設計にしています。

## 今後の拡張案

1. **リアルタイムVRMプレビュー**:
   - WebGLベースのVRMプレビュー機能

2. **高度なリギング機能**:
   - 複雑なIK/FKセットアップのサポート
   - 手指ボーンの詳細な設定

3. **表情システムの強化**:
   - 表情ブレンド機能
   - リップシンク自動化

4. **Unity双方向連携**:
   - Unity側からの変更をBlenderに反映
   - リアルタイム編集の同期# VRM機能実装状況レポート

## 概要

Blender GraphQL MCPプロジェクトにVTuberモデル制作に関連する機能の実装が完了しました。このレポートでは、各機能の実装状況と動作確認結果を記録します。

## 実装済み機能

### モデル管理
- ✅ VRMモデルの作成（Blenderコレクションとして管理）
- ✅ テンプレート適用（人型モデルの基本構造作成）
- ✅ VRMモデル情報の取得と管理

### リギング機能
- ✅ VRM準拠ボーンセット自動生成
- ✅ 自動ウェイト割り当て
- ✅ 骨格階層の構造化

### 表情制作
- ✅ ブレンドシェイプ（表情）の追加
- ✅ ブレンドシェイプの編集と更新
- ✅ ブレンドシェイプカテゴリの管理

### エクスポート
- ✅ VRMフォーマットエクスポート（メタデータ設定対応）
- ✅ Unity用FBXエクスポート
- ✅ エクスポート前のモデル検証機能

### Unity連携
- ✅ Unityプロジェクトのセットアップ
- ✅ Unity Editorへの直接エクスポート
- ✅ Unityマテリアル生成サポート
- ✅ Prefab作成スクリプト自動生成

## GraphQL実装
- ✅ VRM関連型の定義（VrmModel, VrmBone, BlendShape等）
- ✅ クエリの実装（vrmModels, vrmModel）
- ✅ ミューテーションの実装（createVrmModel, applyVrmTemplate等）
- ✅ リゾルバの実装

## インテグレーション
- ✅ 既存のスキーマとの統合
- ✅ リゾルバ互換性レイヤー対応
- ✅ モジュール初期化ロジックの修正

## ドキュメント
- ✅ 使用方法ドキュメント（VRM_USAGE.md）
- ✅ スキーマドキュメント（VRM_SCHEMA.md）
- ✅ 機能実装サマリー（VRM_FEATURES.md）
- ✅ 実装状況レポート（本ドキュメント）

## 今後の課題と拡張案

### 優先度高
1. **VRMアドオン連携**: UniVRMなどの標準VRMアドオンとの連携強化
2. **リグ機能強化**: 完全なVRM仕様準拠のリギングシステム
3. **表情エディタ**: グラフィカルな表情編集インターフェース

### 優先度中
1. **テンプレート多様化**: 様々なVTuberスタイルのテンプレート
2. **物理シミュレーション**: 髪や衣装の物理挙動設定
3. **Unity双方向連携**: Unity側からの変更をBlenderに反映

### 優先度低
1. **プレビュー機能**: WebGLベースのVRMプレビュー
2. **VRMメタデータエディタ**: 詳細なメタデータ編集機能
3. **バッチ処理**: 複数モデルの一括処理機能

## 既知の制限事項

1. **VRMアドオン依存**: 実際のVRMエクスポートには外部アドオンが必要
2. **Unity側の設定**: Unity連携機能はUnity側での追加設定が必要
3. **複雑なブレンドシェイプ**: 高度な表情操作は一部手動調整が必要

## 技術的検討事項

1. **パフォーマンス**: 大規模モデルでのパフォーマンス最適化
2. **互換性**: Blenderバージョン間の互換性確保
3. **エラーハンドリング**: より詳細なエラー診断と修復提案

## 動作確認環境

- Blender 4.0以上
- Python 3.10
- GraphQL Core
- macOS/Windows
- Unity 2022.3 LTS以上（Unity連携機能）

## 結論

VRM機能の基本的な実装は完了し、GraphQLインターフェースを通じてVTuberモデル制作の主要なワークフローを提供できるようになりました。今後は実用フィードバックに基づいて機能を改善・拡張していくことが重要です。# VTuberモデル制作対応 MCP 要件定義書

## 1. 概要

Blender GraphQL MCPをVTuberモデル制作向けに拡張し、キャラクターモデリング、リギング、表情制作、エクスポートまでのワークフローを効率化するシステムを構築する。特にBlenderでのモデリング・リギングからUnity（無料版）でのVRM調整・エクスポートまでのシームレスなワークフローを実現し、VTuber制作に特化した機能を提供する。

## 2. 主要機能

### 2.1 モデル管理
- キャラクターモデルのテンプレート適用
- 標準ボディプロポーション調整
- メッシュの最適化（ポリゴン数管理）
- UV展開補助機能

### 2.2 リギング機能
- VTuber標準ボーンセット自動生成
  - VRM準拠ボーン構造
  - Blenderリグ→VRMボーン名マッピング
- ウェイト自動設定
- IK/FKコントロールの設定
- 指ボーン設定の自動化

### 2.3 表情制作
- 標準ブレンドシェイプ生成（喜怒哀楽基本表情）
- 表情クエリ＆ミューテーション
- ビジュアル表情エディタ連携
- リップシンク補助機能

### 2.4 テクスチャ管理
- PBRテクスチャセット管理
- テクスチャ変更のリアルタイムプレビュー
- テクスチャベイク自動化

### 2.5 エクスポート
- VRMフォーマットエクスポート
- Unity対応FBXエクスポート
- メタデータ設定（作者情報、使用許諾等）
- エクスポート前チェック機能
- Unity向け最適化設定

### 2.6 Unity連携
- Unity Editorへの直接エクスポート
- Unity用プレハブ自動生成
- VRM対応設定の自動化
- Unity上でのテスト支援

## 3. GraphQL API拡張

### 3.1 新規クエリタイプ
```graphql
type VrmMetadata {
  title: String
  author: String
  contactInformation: String
  reference: String
  version: String
  allowedUserNames: [String]
  violentUssage: Boolean
  sexualUssage: Boolean
  commercialUssage: Boolean
  otherPermissionUrl: String
  license: VrmLicense
}

type VrmBone {
  name: String!
  humanoidBoneName: String
  position: Vector3
  rotation: Vector3
  children: [VrmBone]
}

type BlendShape {
  name: String!
  category: String
  weight: Float
  binds: [BlendShapeBind]
}

type BlendShapeBind {
  mesh: String
  index: Int
  weight: Float
}

type VrmModel {
  id: ID!
  name: String!
  version: String
  metadata: VrmMetadata
  rootBone: VrmBone
  blendShapes: [BlendShape]
  meshes: [BlenderObject]
  materials: [Material]
}
```

### 3.2 新規ミューテーションタイプ
```graphql
input VrmMetadataInput {
  title: String
  author: String
  contactInformation: String
  reference: String
  version: String
  allowedUserNames: [String]
  violentUssage: Boolean
  sexualUssage: Boolean
  commercialUssage: Boolean
  otherPermissionUrl: String
  licenseType: String
}

input BlendShapeInput {
  name: String!
  category: String
  weight: Float
}

type VrmModelResult {
  success: Boolean!
  message: String
  model: VrmModel
}

type BlendShapeResult {
  success: Boolean!
  message: String
  blendShape: BlendShape
}

extend type Mutation {
  # モデル管理
  createVrmModel(name: String!): VrmModelResult
  applyVrmTemplate(modelId: ID!, templateType: String!): VrmModelResult
  
  # リギング
  generateVrmRig(modelId: ID!): VrmModelResult
  assignAutoWeights(modelId: ID!): VrmModelResult
  
  # 表情
  addBlendShape(modelId: ID!, blendShape: BlendShapeInput!): BlendShapeResult
  updateBlendShape(modelId: ID!, name: String!, weight: Float!): BlendShapeResult
  
  # エクスポート
  exportVrm(modelId: ID!, filepath: String!, metadata: VrmMetadataInput): VrmExportResult
  exportFbxForUnity(modelId: ID!, filepath: String!, optimizeForUnity: Boolean): FbxExportResult
  validateVrmModel(modelId: ID!): VrmValidationResult
  
  # Unity連携
  setupUnityProject(projectPath: String!, createVrmSupportFiles: Boolean): UnityProjectResult
  exportToUnityEditor(modelId: ID!, unityProjectPath: String!, createPrefab: Boolean): UnityExportResult
  generateUnityMaterials(modelId: ID!, unityProjectPath: String!, materialType: String): UnityMaterialsResult
}
```

## 4. タスクキュー拡張

### 4.1 バックグラウンドタスク
- ボーンの自動生成
- ウェイト計算
- テクスチャベイク
- VRMエクスポート
- Unity向けエクスポート処理
- メッシュ最適化処理
- Unity連携処理

### 4.2 進捗表示
- リアルタイム進捗状況
- 予測残り時間
- エラーレポート詳細

## 5. 管理UI拡張

### 5.1 VTuberモデルダッシュボード
- モデル一覧
- リグステータス
- シェイプキー一覧
- 検証エラー表示

### 5.2 リアルタイムプレビュー
- WebGLベースのモデルプレビュー
- 表情テスト機能
- ポーズテスト機能

### 5.3 エクスポート管理
- エクスポート設定プリセット
- エクスポート履歴
- Unity最適化設定

### 5.4 Unity連携パネル
- Unityプロジェクト管理
- 直接エクスポートコントロール
- VRMコンポーネント設定
- Unityとのファイル同期

## 6. 実装計画

1. **フェーズ1**: 基本モデル管理とGraphQL API拡張
2. **フェーズ2**: リギング機能とタスクキュー統合
3. **フェーズ3**: 表情システムとプレビュー機能
4. **フェーズ4**: Unity連携基盤の実装
5. **フェーズ5**: VRMエクスポートとバリデーション機能
6. **フェーズ6**: Unity直接連携機能の実装
7. **フェーズ7**: UI/UX改善とドキュメント

## 7. 技術要件

- Blender 3.5+
- Python 3.10+
- FastAPI
- GraphQL (Graphene)
- WebSocket (リアルタイム通信用)
- Three.js (WebGLプレビュー用)
- Unity 2022.3 LTS以上 (Personal版)
- UniVRM (Unity VRMパッケージ)
- Unity Editor API

## 8. 互換性・制約

- VRM 0.x および 1.0形式サポート
- Blenderネイティブリグとの互換性確保
- 低スペックマシンでのパフォーマンス最適化
- 既存のBlenderアドオンとの共存
- Unity Personal版の制限内での動作保証
- UniVRM最新版との互換性維持
- クロスプラットフォーム対応（Windows/Mac）

## 9. Unity連携の詳細仕様

### 9.1 Unity通信方式
- Unity Editor拡張スクリプトによる連携
- ローカルネットワーク上のHTTP/WebSocketプロトコル
- ファイルシステム連携によるアセット転送

### 9.2 Unity側機能
- Blenderからのモデル受信・インポート
- VRMコンポーネント自動セットアップ
- プレビュー・テスト用シーン
- 表情調整ツール
- VRMバリデーション機能

### 9.3 必要なUnityパッケージ
- UniVRM (VRM形式対応)
- VRM Look At Blendshape (視線制御)
- JSON Utilities (通信用)
- Editor Coroutines (非同期処理用)

### 9.4 セキュリティ
- ローカルホスト通信のみ許可
- 要求元の検証
- ファイル権限の適切な管理# VRM GraphQLスキーマ拡張

## 概要

Blender GraphQL MCPにVRM（Virtual Reality Model）関連のGraphQLスキーマ拡張を実装しました。これにより、VTuberモデル制作に関する機能をGraphQLインターフェースで提供します。

## 型定義

### VRM型

#### `VrmModel`
```graphql
type VrmModel {
  id: ID!
  name: String!
  version: String
  metadata: VrmMetadata
  rootBone: VrmBone
  blendShapes: [BlendShape]
  meshes: [BlenderObject]
  materials: [Material]
}
```

#### `VrmMetadata`
```graphql
type VrmMetadata {
  title: String
  author: String
  contactInformation: String
  reference: String
  version: String
  allowedUserNames: [String]
  violentUssage: Boolean
  sexualUssage: Boolean
  commercialUssage: Boolean
  otherPermissionUrl: String
  license: String
}
```

#### `VrmBone`
```graphql
type VrmBone {
  name: String!
  humanoidBoneName: String
  position: Vector3
  rotation: Vector3
  children: [VrmBone]
}
```

#### `BlendShape`
```graphql
type BlendShape {
  name: String!
  category: String
  weight: Float
  binds: [BlendShapeBind]
}
```

#### `BlendShapeBind`
```graphql
type BlendShapeBind {
  mesh: String
  index: Int
  weight: Float
}
```

### 入力型

#### `VrmMetadataInput`
```graphql
input VrmMetadataInput {
  title: String
  author: String
  contactInformation: String
  reference: String
  version: String
  allowedUserNames: [String]
  violentUssage: Boolean
  sexualUssage: Boolean
  commercialUssage: Boolean
  otherPermissionUrl: String
  licenseType: String
}
```

#### `BlendShapeInput`
```graphql
input BlendShapeInput {
  name: String!
  category: String
  weight: Float
}
```

### 結果型

#### `VrmModelResult`
```graphql
type VrmModelResult {
  success: Boolean!
  message: String
  model: VrmModel
}
```

#### `BlendShapeResult`
```graphql
type BlendShapeResult {
  success: Boolean!
  message: String
  blendShape: BlendShape
}
```

#### `VrmExportResult`
```graphql
type VrmExportResult {
  success: Boolean!
  message: String
  filepath: String
  metadata: VrmMetadata
}
```

#### `FbxExportResult`
```graphql
type FbxExportResult {
  success: Boolean!
  message: String
  filepath: String
  optimizedForUnity: Boolean
}
```

#### `VrmValidationResult`
```graphql
type VrmValidationResult {
  success: Boolean!
  message: String
  statusCode: String
  model: VrmModel
  results: [ValidationResultItem]
}
```

#### `ValidationResultItem`
```graphql
type ValidationResultItem {
  type: String
  message: String
}
```

#### `UnityProjectResult`
```graphql
type UnityProjectResult {
  success: Boolean!
  message: String
  projectPath: String
  assetsPath: String
  vrmModelsPath: String
  createdVrmSupportFiles: Boolean
}
```

#### `UnityExportResult`
```graphql
type UnityExportResult {
  success: Boolean!
  message: String
  unityProjectPath: String
  modelPath: String
  createdPrefab: Boolean
}
```

#### `UnityMaterialsResult`
```graphql
type UnityMaterialsResult {
  success: Boolean!
  message: String
  unityProjectPath: String
  materialsCount: Int
  materialType: String
  scriptPath: String
}
```

## クエリ

### VRMモデル一覧の取得
```graphql
vrmModels: [VrmModel]
```

### 特定のVRMモデル情報の取得
```graphql
vrmModel(id: ID!): VrmModel
```

## ミューテーション

### モデル作成と管理

#### VRMモデルの作成
```graphql
createVrmModel(name: String!): VrmModelResult
```

#### テンプレート適用
```graphql
applyVrmTemplate(modelId: ID!, templateType: String!): VrmModelResult
```

### リギング

#### VRM準拠リグの生成
```graphql
generateVrmRig(modelId: ID!): VrmModelResult
```

#### 自動ウェイト割り当て
```graphql
assignAutoWeights(modelId: ID!): VrmModelResult
```

### 表情制作

#### ブレンドシェイプの追加
```graphql
addBlendShape(modelId: ID!, blendShape: BlendShapeInput!): BlendShapeResult
```

#### ブレンドシェイプの更新
```graphql
updateBlendShape(modelId: ID!, name: String!, weight: Float!): BlendShapeResult
```

### エクスポート

#### VRMとしてエクスポート
```graphql
exportVrm(
  modelId: ID!, 
  filepath: String!, 
  metadata: VrmMetadataInput
): VrmExportResult
```

#### Unity用FBXとしてエクスポート
```graphql
exportFbxForUnity(
  modelId: ID!, 
  filepath: String!, 
  optimizeForUnity: Boolean
): FbxExportResult
```

#### VRMモデルの検証
```graphql
validateVrmModel(modelId: ID!): VrmValidationResult
```

### Unity連携

#### Unityプロジェクトのセットアップ
```graphql
setupUnityProject(
  projectPath: String!, 
  createVrmSupportFiles: Boolean
): UnityProjectResult
```

#### Unity Editorへのエクスポート
```graphql
exportToUnityEditor(
  modelId: ID!, 
  unityProjectPath: String!, 
  createPrefab: Boolean
): UnityExportResult
```

#### Unityマテリアルの生成
```graphql
generateUnityMaterials(
  modelId: ID!, 
  unityProjectPath: String!, 
  materialType: String
): UnityMaterialsResult
```

## 使用例

### VRMモデルの作成と準備
```graphql
# 新規VRMモデルの作成
mutation {
  createVrmModel(name: "MyVTuber") {
    success
    message
    model {
      id
      name
    }
  }
}

# テンプレートの適用
mutation {
  applyVrmTemplate(
    modelId: "MyVTuber",
    templateType: "HUMANOID"
  ) {
    success
    message
  }
}

# リグの生成
mutation {
  generateVrmRig(modelId: "MyVTuber") {
    success
    message
    model {
      rootBone {
        name
        humanoidBoneName
      }
    }
  }
}

# ウェイト割り当て
mutation {
  assignAutoWeights(modelId: "MyVTuber") {
    success
    message
  }
}
```

### 表情制作
```graphql
# ブレンドシェイプの追加
mutation {
  addBlendShape(
    modelId: "MyVTuber", 
    blendShape: {
      name: "Happy",
      category: "Expression",
      weight: 1.0
    }
  ) {
    success
    message
    blendShape {
      name
      category
      weight
    }
  }
}

# 表情の更新
mutation {
  updateBlendShape(
    modelId: "MyVTuber",
    name: "Happy",
    weight: 0.5
  ) {
    success
    message
  }
}
```

### エクスポートと検証
```graphql
# モデルの検証
mutation {
  validateVrmModel(modelId: "MyVTuber") {
    success
    message
    statusCode
    results {
      type
      message
    }
  }
}

# VRMとしてエクスポート
mutation {
  exportVrm(
    modelId: "MyVTuber",
    filepath: "/path/to/output.vrm",
    metadata: {
      title: "My VTuber",
      author: "Your Name",
      version: "1.0"
    }
  ) {
    success
    message
    filepath
  }
}
```

### Unity連携
```graphql
# Unityプロジェクトのセットアップ
mutation {
  setupUnityProject(
    projectPath: "/path/to/unity/project",
    createVrmSupportFiles: true
  ) {
    success
    message
    projectPath
  }
}

# Unity Editorへのエクスポート
mutation {
  exportToUnityEditor(
    modelId: "MyVTuber",
    unityProjectPath: "/path/to/unity/project",
    createPrefab: true
  ) {
    success
    message
    modelPath
  }
}
```

## スキーマ拡張機能

このスキーマ拡張は、GraphQLインターフェースを通じてVTuberモデル制作の全工程をカバーします。特に以下の点に注意してください：

1. **型の再帰的定義**: `VrmBone`型は自己参照による再帰的な骨格階層を表現できます。

2. **複合型と入力型の対応**: 各複合型には対応する入力型が定義されています。

3. **結果指向の設計**: すべてのミューテーションは操作結果を明確に表現する結果型を返します。

4. **エラーハンドリング**: 結果型には常に`success`と`message`フィールドが含まれ、エラー状態を適切に伝達できます。# Blender GraphQL MCP - VRM機能の使用方法

## 概要

VRM（Virtual Reality Model）機能は、Blender GraphQL MCPにVTuberモデル作成向けの機能を追加します。
この機能を使用することで、Blenderでモデリング・リギングを行い、VRMフォーマットでエクスポートしたり、
Unityと連携したりすることが可能になります。

## 前提条件

1. Blender 4.0以上
2. Blender GraphQL MCPアドオンのインストール
3. 必要に応じてVRMアドオン（[UniVRM](https://github.com/vrm-c/UniVRM) など）

## 基本的なワークフロー

VTuberモデル作成のワークフローは以下の手順で行います：

1. VRMモデルの作成
2. テンプレートの適用
3. リギング
4. ウェイト割り当て
5. ブレンドシェイプ（表情）の追加
6. エクスポート
7. Unityとの連携

## GraphQLクエリの例

### 1. VRMモデルの作成

```graphql
mutation CreateVrmModel {
  createVrmModel(name: "MyVTuber") {
    success
    message
    model {
      id
      name
    }
  }
}
```

### 2. テンプレートの適用

```graphql
mutation ApplyTemplate {
  applyVrmTemplate(
    modelId: "MyVTuber",
    templateType: "HUMANOID"
  ) {
    success
    message
    model {
      id
      name
    }
  }
}
```

### 3. VRM準拠リグの生成

```graphql
mutation GenerateRig {
  generateVrmRig(modelId: "MyVTuber") {
    success
    message
    model {
      id
      name
      rootBone {
        name
        humanoidBoneName
        children {
          name
          humanoidBoneName
        }
      }
    }
  }
}
```

### 4. 自動ウェイト割り当て

```graphql
mutation AssignWeights {
  assignAutoWeights(modelId: "MyVTuber") {
    success
    message
  }
}
```

### 5. ブレンドシェイプの追加

```graphql
mutation AddBlendShape {
  addBlendShape(
    modelId: "MyVTuber", 
    blendShape: {
      name: "Happy",
      category: "Expression",
      weight: 1.0
    }
  ) {
    success
    message
    blendShape {
      name
      category
      weight
    }
  }
}
```

### 6. ブレンドシェイプの更新

```graphql
mutation UpdateBlendShape {
  updateBlendShape(
    modelId: "MyVTuber",
    name: "Happy",
    weight: 0.8
  ) {
    success
    message
    blendShape {
      name
      weight
    }
  }
}
```

### 7. VRMモデルの検証

```graphql
mutation ValidateModel {
  validateVrmModel(modelId: "MyVTuber") {
    success
    message
    statusCode
    results {
      type
      message
    }
  }
}
```

### 8. VRMとしてエクスポート

```graphql
mutation ExportVrm {
  exportVrm(
    modelId: "MyVTuber",
    filepath: "/path/to/export/myvtuber.vrm",
    metadata: {
      title: "My VTuber",
      author: "Your Name",
      contactInformation: "your@email.com",
      version: "1.0"
    }
  ) {
    success
    message
    filepath
    metadata {
      title
      author
    }
  }
}
```

### 9. Unity用にFBXとしてエクスポート

```graphql
mutation ExportFbx {
  exportFbxForUnity(
    modelId: "MyVTuber",
    filepath: "/path/to/export/myvtuber.fbx",
    optimizeForUnity: true
  ) {
    success
    message
    filepath
  }
}
```

### 10. Unityプロジェクトのセットアップ

```graphql
mutation SetupUnityProject {
  setupUnityProject(
    projectPath: "/path/to/unity/project",
    createVrmSupportFiles: true
  ) {
    success
    message
    projectPath
    vrmModelsPath
  }
}
```

### 11. Unity Editorへのエクスポート

```graphql
mutation ExportToUnity {
  exportToUnityEditor(
    modelId: "MyVTuber",
    unityProjectPath: "/path/to/unity/project",
    createPrefab: true
  ) {
    success
    message
    modelPath
  }
}
```

### 12. Unityマテリアルの生成

```graphql
mutation GenerateUnityMaterials {
  generateUnityMaterials(
    modelId: "MyVTuber",
    unityProjectPath: "/path/to/unity/project",
    materialType: "URP"
  ) {
    success
    message
    materialsCount
    scriptPath
  }
}
```

### 13. VRMモデル情報の取得

```graphql
query GetVrmModel {
  vrmModel(id: "MyVTuber") {
    id
    name
    version
    rootBone {
      name
      humanoidBoneName
    }
    blendShapes {
      name
      category
      weight
    }
  }
}
```

### 14. VRMモデル一覧の取得

```graphql
query GetAllVrmModels {
  vrmModels {
    id
    name
  }
}
```

## 技術詳細

### VRMモデル構造

VRMモデルはBlender内で以下のように表現されます：

- **Collection**: VRMモデルはBlenderのCollectionとして管理されます
- **Armature**: VRMの骨格構造を表現するArmatureオブジェクト
- **Mesh**: VRMのメッシュデータを表現するMeshオブジェクト
- **Shape Keys**: ブレンドシェイプ（表情）を表現するShape Keys

### Unity連携

Unity連携の仕組みは以下の通りです：

1. FBXエクスポート: 標準的なFBXフォーマットでモデルをエクスポート
2. プロジェクト管理: Unityプロジェクトへのディレクトリ構成設定
3. スクリプト生成: プレハブやマテリアル生成のためのUnityスクリプトを自動生成

## 制限事項

- 実際のVRMエクスポートには、追加のVRMアドオンが必要です
- Unity連携は、実際にはUnity側でのスクリプト実行が必要です
- 完全なVRM仕様の一部機能は実装されていない可能性があります

## トラブルシューティング

- エラー「VRMモデルが見つかりません」: モデル名（コレクション名）が正しいか確認
- エラー「リグが存在しません」: まず generateVrmRig を実行
- エラー「メッシュが見つかりません」: モデルにメッシュオブジェクトを追加
- Unityエクスポートエラー: パスが正しいか、権限があるか確認

## 参考リンク

- [VRM 仕様](https://github.com/vrm-c/vrm-specification)
- [UniVRM GitHub](https://github.com/vrm-c/UniVRM)
- [VRoid Hub](https://hub.vroid.com/)