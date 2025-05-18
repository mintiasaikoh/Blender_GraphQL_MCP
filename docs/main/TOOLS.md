# Blender MCP Tools - LLM用ツール一覧

## 概要

このドキュメントでは、LLM（大規模言語モデル）がBlenderを操作するために使用できるツールを説明します。

## 基本ツール

### create_object
3Dオブジェクトを作成します。

```json
{
  "tool": "create_object",
  "parameters": {
    "type": "CUBE",  // CUBE, SPHERE, CYLINDER, PLANE など
    "name": "MyCube",
    "location": {"x": 0, "y": 0, "z": 0}
  }
}
```

### transform_object
オブジェクトの位置、回転、スケールを変更します。

```json
{
  "tool": "transform_object",
  "parameters": {
    "object_name": "MyCube",
    "location": {"x": 1, "y": 2, "z": 3},
    "rotation": {"x": 45, "y": 0, "z": 0},
    "scale": {"x": 2, "y": 2, "z": 2}
  }
}
```

### apply_material
オブジェクトにマテリアル（質感）を適用します。

```json
{
  "tool": "apply_material",
  "parameters": {
    "object_name": "MyCube",
    "material_name": "RedMaterial",
    "base_color": {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0},
    "metallic": 0.0,
    "roughness": 0.5
  }
}
```

### delete_object
オブジェクトを削除します。

```json
{
  "tool": "delete_object",
  "parameters": {
    "object_name": "MyCube"
  }
}
```

## カメラ・ライトツール

### create_camera
新しいカメラを作成します。

```json
{
  "tool": "create_camera",
  "parameters": {
    "name": "MainCamera",
    "location": {"x": 7, "y": -7, "z": 5},
    "look_at": {"x": 0, "y": 0, "z": 0}
  }
}
```

### create_light
新しいライトを作成します。

```json
{
  "tool": "create_light",
  "parameters": {
    "name": "MainLight",
    "type": "POINT",  // POINT, SUN, SPOT, AREA
    "location": {"x": 5, "y": 5, "z": 5},
    "color": {"r": 1.0, "g": 0.9, "b": 0.8},
    "energy": 100
  }
}
```

## レンダリングツール

### render_scene
現在のシーンをレンダリングします。

```json
{
  "tool": "render_scene",
  "parameters": {
    "resolution": {"x": 1920, "y": 1080},
    "samples": 128,
    "output_path": "/tmp/render.png"
  }
}
```

### capture_viewport
3Dビューポートのスクリーンショットを取得します。

```json
{
  "tool": "capture_viewport",
  "parameters": {
    "include_overlays": false
  }
}
```

## シーン情報取得ツール

### get_scene_info
現在のシーンの情報を取得します。

```json
{
  "tool": "get_scene_info",
  "parameters": {}
}
```

### get_object_info
特定のオブジェクトの詳細情報を取得します。

```json
{
  "tool": "get_object_info",
  "parameters": {
    "object_name": "MyCube"
  }
}
```

### list_objects
シーン内のすべてのオブジェクトをリストします。

```json
{
  "tool": "list_objects",
  "parameters": {
    "type_filter": "MESH"  // オプション：MESH, CAMERA, LIGHT など
  }
}
```

## 高度なツール

### boolean_operation
ブーリアン演算（結合、差分、交差）を実行します。

```json
{
  "tool": "boolean_operation",
  "parameters": {
    "operation": "DIFFERENCE",  // UNION, DIFFERENCE, INTERSECT
    "object_a": "Cube",
    "object_b": "Sphere"
  }
}
```

### create_material_node
ノードベースのマテリアルを作成します。

```json
{
  "tool": "create_material_node",
  "parameters": {
    "name": "ComplexMaterial",
    "nodes": [
      {
        "type": "BSDF_PRINCIPLED",
        "params": {
          "base_color": {"r": 0.5, "g": 0.5, "b": 1.0},
          "metallic": 0.8
        }
      }
    ]
  }
}
```

### apply_modifier
モディファイアを適用します。

```json
{
  "tool": "apply_modifier",
  "parameters": {
    "object_name": "MyCube",
    "modifier_type": "SUBDIVISION",
    "params": {
      "levels": 2,
      "render_levels": 3
    }
  }
}
```

## 使用例

### 赤い立方体を作成

```json
[
  {
    "tool": "create_object",
    "parameters": {
      "type": "CUBE",
      "name": "RedCube",
      "location": {"x": 0, "y": 0, "z": 0}
    }
  },
  {
    "tool": "apply_material",
    "parameters": {
      "object_name": "RedCube",
      "material_name": "RedMaterial",
      "base_color": {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}
    }
  }
]
```

### シーンをセットアップしてレンダリング

```json
[
  {
    "tool": "create_camera",
    "parameters": {
      "name": "MainCamera",
      "location": {"x": 5, "y": -5, "z": 3},
      "look_at": {"x": 0, "y": 0, "z": 0}
    }
  },
  {
    "tool": "create_light",
    "parameters": {
      "name": "KeyLight",
      "type": "SUN",
      "rotation": {"x": 45, "y": 45, "z": 0},
      "energy": 2
    }
  },
  {
    "tool": "render_scene",
    "parameters": {
      "resolution": {"x": 1920, "y": 1080},
      "samples": 128
    }
  }
]
```

## エラーハンドリング

各ツールは以下の形式でエラーを返すことがあります：

```json
{
  "success": false,
  "error": {
    "code": "OBJECT_NOT_FOUND",
    "message": "Object 'NonExistentCube' not found",
    "details": {
      "available_objects": ["Cube", "Sphere", "Camera"]
    }
  }
}
```

## ベストプラクティス

1. **オブジェクト名の確認**: 操作前に`list_objects`でオブジェクトの存在を確認
2. **段階的な操作**: 複雑な操作は小さなステップに分解
3. **エラーチェック**: 各操作後にエラーをチェック
4. **プレビュー**: `capture_viewport`で結果を確認

## 今後追加予定のツール

- アニメーション操作ツール
- テクスチャ管理ツール
- 物理シミュレーションツール
- ジオメトリノードツール