"""
Blender GraphQL MCP - 入力型定義
目的別に特化した入力型の定義
"""

import logging
from typing import Dict, Any, List, Optional

# GraphQL関連のインポート
from tools import (
    GraphQLInputObjectType,
    GraphQLInputField,
    GraphQLString,
    GraphQLFloat,
    GraphQLInt,
    GraphQLBoolean,
    GraphQLList,
    GraphQLNonNull,
    GraphQLEnumType
)

# スキーマレジストリのインポート
from tools.schema_registry import schema_registry

logger = logging.getLogger("blender_graphql_mcp.tools.schema_inputs")

# 座標入力型の定義
vector3_input = GraphQLInputObjectType(
    name="Vector3Input",
    fields={
        "x": GraphQLInputField(
            GraphQLFloat,
            description="X座標"
        ),
        "y": GraphQLInputField(
            GraphQLFloat,
            description="Y座標"
        ),
        "z": GraphQLInputField(
            GraphQLFloat,
            description="Z座標"
        )
    },
    description="3D座標入力"
)

# 色入力型の定義
color_input = GraphQLInputObjectType(
    name="ColorInput",
    fields={
        "r": GraphQLInputField(
            GraphQLFloat,
            description="赤成分 (0.0-1.0)"
        ),
        "g": GraphQLInputField(
            GraphQLFloat,
            description="緑成分 (0.0-1.0)"
        ),
        "b": GraphQLInputField(
            GraphQLFloat,
            description="青成分 (0.0-1.0)"
        ),
        "a": GraphQLInputField(
            GraphQLFloat,
            default_value=1.0,
            description="透明度 (0.0-1.0)"
        )
    },
    description="RGBA色情報入力"
)

# 寸法入力型の定義
dimensions_input = GraphQLInputObjectType(
    name="DimensionsInput",
    fields={
        "width": GraphQLInputField(
            GraphQLFloat,
            description="幅"
        ),
        "height": GraphQLInputField(
            GraphQLFloat,
            description="高さ"
        ),
        "depth": GraphQLInputField(
            GraphQLFloat,
            description="奥行き"
        )
    },
    description="3D寸法入力"
)

# 拡張3D座標入力（名前付き座標）の定義
named_vector3_input = GraphQLInputObjectType(
    name="NamedVector3Input",
    fields={
        "name": GraphQLInputField(
            GraphQLString,
            description="座標の名前"
        ),
        "position": GraphQLInputField(
            vector3_input,
            description="3D座標"
        )
    },
    description="名前付き3D座標入力"
)

# 変換パラメータ入力の定義
transform_params_input = GraphQLInputObjectType(
    name="TransformParamsInput",
    fields={
        "location": GraphQLInputField(
            vector3_input,
            description="位置"
        ),
        "rotation": GraphQLInputField(
            vector3_input,
            description="回転（度数法）"
        ),
        "scale": GraphQLInputField(
            vector3_input,
            description="スケール"
        ),
        "relative": GraphQLInputField(
            GraphQLBoolean,
            default_value=False,
            description="相対変換を適用するかどうか"
        )
    },
    description="オブジェクト変換パラメータ"
)

# ジオメトリパラメータ入力の定義
geometry_params_input = GraphQLInputObjectType(
    name="GeometryParamsInput",
    fields={
        "size": GraphQLInputField(
            GraphQLFloat,
            description="基本サイズ"
        ),
        "dimensions": GraphQLInputField(
            dimensions_input,
            description="寸法"
        ),
        "segments": GraphQLInputField(
            GraphQLInt,
            description="セグメント数"
        ),
        "vertices": GraphQLInputField(
            GraphQLList(vector3_input),
            description="頂点リスト"
        ),
        "radius": GraphQLInputField(
            GraphQLFloat,
            description="半径"
        ),
        "depth": GraphQLInputField(
            GraphQLFloat,
            description="深さ"
        )
    },
    description="ジオメトリ生成パラメータ"
)

# マテリアルパラメータ入力の定義
material_params_input = GraphQLInputObjectType(
    name="MaterialParamsInput",
    fields={
        "baseColor": GraphQLInputField(
            color_input,
            description="基本色"
        ),
        "metallic": GraphQLInputField(
            GraphQLFloat,
            description="金属度 (0.0-1.0)"
        ),
        "roughness": GraphQLInputField(
            GraphQLFloat,
            description="荒さ (0.0-1.0)"
        ),
        "specular": GraphQLInputField(
            GraphQLFloat,
            description="鏡面反射度 (0.0-1.0)"
        ),
        "alpha": GraphQLInputField(
            GraphQLFloat,
            description="透明度 (0.0-1.0)"
        ),
        "emissive": GraphQLInputField(
            GraphQLBoolean,
            description="発光するかどうか"
        ),
        "emissiveColor": GraphQLInputField(
            color_input,
            description="発光色"
        ),
        "emissiveStrength": GraphQLInputField(
            GraphQLFloat,
            description="発光強度"
        )
    },
    description="マテリアルパラメータ"
)

# レンダリングパラメータ入力の定義
render_params_input = GraphQLInputObjectType(
    name="RenderParamsInput",
    fields={
        "resolution": GraphQLInputField(
            GraphQLInputObjectType(
                name="ResolutionInput",
                fields={
                    "x": GraphQLInputField(
                        GraphQLInt,
                        description="横解像度（ピクセル）"
                    ),
                    "y": GraphQLInputField(
                        GraphQLInt,
                        description="縦解像度（ピクセル）"
                    )
                }
            ),
            description="レンダリング解像度"
        ),
        "samples": GraphQLInputField(
            GraphQLInt,
            description="サンプル数"
        ),
        "engine": GraphQLInputField(
            GraphQLString,
            description="レンダリングエンジン（CYCLES, EEVEE等）"
        ),
        "transparent": GraphQLInputField(
            GraphQLBoolean,
            description="透明な背景を使用するかどうか"
        ),
        "outputPath": GraphQLInputField(
            GraphQLString,
            description="出力ファイルパス"
        ),
        "viewportOnly": GraphQLInputField(
            GraphQLBoolean,
            default_value=False,
            description="ビューポートのみをキャプチャするかどうか"
        )
    },
    description="レンダリングパラメータ"
)

# カメラパラメータ入力の定義
camera_params_input = GraphQLInputObjectType(
    name="CameraParamsInput",
    fields={
        "location": GraphQLInputField(
            vector3_input,
            description="カメラ位置"
        ),
        "target": GraphQLInputField(
            vector3_input,
            description="カメラのターゲット位置"
        ),
        "focalLength": GraphQLInputField(
            GraphQLFloat,
            description="焦点距離（mm）"
        ),
        "type": GraphQLInputField(
            GraphQLString,
            description="カメラタイプ（PERSP, ORTHO等）"
        ),
        "orthoScale": GraphQLInputField(
            GraphQLFloat,
            description="正投影スケール"
        ),
        "clipStart": GraphQLInputField(
            GraphQLFloat,
            description="クリップ開始距離"
        ),
        "clipEnd": GraphQLInputField(
            GraphQLFloat,
            description="クリップ終了距離"
        ),
        "sensorWidth": GraphQLInputField(
            GraphQLFloat,
            description="センサー幅（mm）"
        )
    },
    description="カメラパラメータ"
)

# ライトパラメータ入力の定義
light_params_input = GraphQLInputObjectType(
    name="LightParamsInput",
    fields={
        "type": GraphQLInputField(
            GraphQLString,
            description="ライトタイプ（POINT, SUN, SPOT, AREA）"
        ),
        "location": GraphQLInputField(
            vector3_input,
            description="ライト位置"
        ),
        "rotation": GraphQLInputField(
            vector3_input,
            description="ライト方向（度数法）"
        ),
        "color": GraphQLInputField(
            color_input,
            description="ライト色"
        ),
        "energy": GraphQLInputField(
            GraphQLFloat,
            description="ライト強度"
        ),
        "radius": GraphQLInputField(
            GraphQLFloat,
            description="ライト半径"
        ),
        "spotSize": GraphQLInputField(
            GraphQLFloat,
            description="スポットライトサイズ（度数法）"
        ),
        "spotBlend": GraphQLInputField(
            GraphQLFloat,
            description="スポットライトのブレンド"
        ),
        "areaShape": GraphQLInputField(
            GraphQLString,
            description="エリアライトの形状（SQUARE, RECTANGLE, DISK, ELLIPSE）"
        )
    },
    description="ライトパラメータ"
)

# モディファイアパラメータ入力の定義
modifier_params_input = GraphQLInputObjectType(
    name="ModifierParamsInput",
    fields={
        "type": GraphQLInputField(
            GraphQLNonNull(GraphQLString),
            description="モディファイアタイプ"
        ),
        "name": GraphQLInputField(
            GraphQLString,
            description="モディファイア名（指定なしの場合は自動生成）"
        ),
        "levels": GraphQLInputField(
            GraphQLInt,
            description="レベル数（サブディビジョンなど）"
        ),
        "angle": GraphQLInputField(
            GraphQLFloat,
            description="角度（ベベル等）"
        ),
        "width": GraphQLInputField(
            GraphQLFloat,
            description="幅（ベベル等）"
        ),
        "distance": GraphQLInputField(
            GraphQLFloat,
            description="距離（ソリッド等）"
        ),
        "strength": GraphQLInputField(
            GraphQLFloat,
            description="強度（ディスプレイスメント等）"
        ),
        "object": GraphQLInputField(
            GraphQLString,
            description="参照オブジェクト名（ブーリアン等）"
        ),
        "operation": GraphQLInputField(
            GraphQLString,
            description="操作（ブーリアン等）"
        )
    },
    description="モディファイアパラメータ"
)

# 実行オプション入力の定義
execution_options_input = GraphQLInputObjectType(
    name="ExecutionOptionsInput",
    fields={
        "generatePreview": GraphQLInputField(
            GraphQLBoolean,
            default_value=True,
            description="プレビュー画像を生成するかどうか"
        ),
        "trackHistory": GraphQLInputField(
            GraphQLBoolean,
            default_value=True,
            description="操作履歴を記録するかどうか"
        ),
        "timeoutMs": GraphQLInputField(
            GraphQLInt,
            default_value=10000,
            description="タイムアウト時間（ミリ秒）"
        ),
        "returnContext": GraphQLInputField(
            GraphQLBoolean,
            default_value=True,
            description="実行後のコンテキストを返すかどうか"
        ),
        "executionMode": GraphQLInputField(
            GraphQLString,
            default_value="DEFAULT",
            description="実行モード（DEFAULT, SAFE, VERBOSE等）"
        )
    },
    description="実行オプションパラメータ"
)

def register_input_types():
    """入力型をスキーマレジストリに登録"""
    schema_registry.register_type("Vector3Input", vector3_input)
    schema_registry.register_type("ColorInput", color_input)
    schema_registry.register_type("DimensionsInput", dimensions_input)
    schema_registry.register_type("NamedVector3Input", named_vector3_input)
    schema_registry.register_type("TransformParamsInput", transform_params_input)
    schema_registry.register_type("GeometryParamsInput", geometry_params_input)
    schema_registry.register_type("MaterialParamsInput", material_params_input)
    schema_registry.register_type("RenderParamsInput", render_params_input)
    schema_registry.register_type("CameraParamsInput", camera_params_input)
    schema_registry.register_type("LightParamsInput", light_params_input)
    schema_registry.register_type("ModifierParamsInput", modifier_params_input)
    schema_registry.register_type("ExecutionOptionsInput", execution_options_input)
    schema_registry.register_component("schema_inputs")
    logger.info("入力型を登録しました")

# スキーマレジストリへの登録
register_input_types()