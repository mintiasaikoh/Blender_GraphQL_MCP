"""
Blender GraphQL Schema
GraphQLのスキーマ定義を提供するモジュール
"""

import logging
import traceback
from typing import Dict, Any, List, Optional, Union

# ロガー初期化
logger = logging.getLogger("blender_graphql_mcp.graphql.schema")

# スキーマビルド済みフラグ
_schema_built = False
schema = None
GRAPHQL_AVAILABLE = False

# 例外処理でimportを行う
try:
    import graphql
    from graphql import (
        GraphQLSchema,
        GraphQLObjectType,
        GraphQLString,
        GraphQLInt,
        GraphQLFloat,
        GraphQLBoolean,
        GraphQLList,
        GraphQLNonNull,
        GraphQLField,
        GraphQLArgument,
        GraphQLEnumType,
        GraphQLEnumValue,
        GraphQLInputObjectType,
        GraphQLInputField
    )
    GRAPHQL_AVAILABLE = True
    logger.info("graphql-coreライブラリが正常にロードされました")
except ImportError as e:
    logger.error(f"graphql-coreライブラリのインポートエラー: {e}")
    GRAPHQL_AVAILABLE = False

# リゾルバのインポート - 互換レイヤーを優先使用
RESOLVERS_AVAILABLE = False
RESOLVER_MODULE = None

# 結果をログに記録するヘルパー関数
def log_resolver_import_result(success, module_name, error=None):
    if success:
        logger.info(f"{module_name}を正常にインポートしました")
    else:
        if error:
            logger.error(f"{module_name}のインポートに失敗しました: {error}")
        else:
            logger.error(f"{module_name}のインポートに失敗しました")

# インポートの試行順序:
# 1. リゾルバ互換レイヤー
# 2. 複数形リゾルバモジュール (resolvers.py)
# 3. 単数形リゾルバモジュール (resolver.py)

# 1. まずリゾルバ互換レイヤーを試す
try:
    from . import resolver_compatibility
    RESOLVERS_AVAILABLE = True
    RESOLVER_MODULE = resolver_compatibility
    log_resolver_import_result(True, "GraphQLリゾルバ互換レイヤー")
except ImportError as e:
    log_resolver_import_result(False, "GraphQLリゾルバ互換レイヤー", e)
    
    # 2. 次に複数形リゾルバモジュールを試す
    try:
        from . import resolvers
        RESOLVERS_AVAILABLE = True
        RESOLVER_MODULE = resolvers
        log_resolver_import_result(True, "複数形リゾルバモジュール (resolvers.py)")
    except ImportError as e:
        log_resolver_import_result(False, "複数形リゾルバモジュール (resolvers.py)", e)
        
        # 3. 最後に単数形リゾルバモジュールを試す
        try:
            from . import resolver
            RESOLVERS_AVAILABLE = True
            RESOLVER_MODULE = resolver
            log_resolver_import_result(True, "単数形リゾルバモジュール (resolver.py)")
        except ImportError as e:
            log_resolver_import_result(False, "単数形リゾルバモジュール (resolver.py)", e)
            logger.error("すべてのリゾルバモジュールのインポートに失敗しました。GraphQL機能は利用できません。")

# 基本型定義
def build_schema():
    """リゾルバモジュールを使用してGraphQLスキーマを構築して返す"""
    global _schema_built, schema
    
    if _schema_built and schema is not None:
        logger.info("既存のスキーマを再利用します")
        return schema

    if not GRAPHQL_AVAILABLE:
        logger.error("graphql-coreライブラリがインストールされていません。スキーマを構築できません。")
        return None
        
    # リゾルバモジュールが正しく読み込まれたかチェック
    if not RESOLVERS_AVAILABLE:
        logger.error("リゾルバモジュールが利用できません")
        return None
        
    # 主要なリゾルバ関数が存在するか確認
    required_resolvers = [
        'resolve_hello', 'resolve_scene_info', 'resolve_object',
        'resolve_create_object', 'resolve_transform_object', 'resolve_delete_object'
    ]
    
    missing_resolvers = []
    for resolver_name in required_resolvers:
        if not hasattr(RESOLVER_MODULE, resolver_name):
            missing_resolvers.append(resolver_name)
    
    if missing_resolvers:
        logger.error(f"必要なリゾルバ関数が見つかりません: {', '.join(missing_resolvers)}")
        return None
    
    try:
        logger.info("GraphQLスキーマを構築しています...")
        
        # 3D座標型を定義（位置、回転、スケール用）
        vector3_type = GraphQLObjectType(
            name='Vector3',
            fields={
                'x': GraphQLField(GraphQLFloat, description='X座標'),
                'y': GraphQLField(GraphQLFloat, description='Y座標'),
                'z': GraphQLField(GraphQLFloat, description='Z座標')
            }
        )
        
        # Vector3入力型
        vector3_input_type = GraphQLInputObjectType(
            name='Vector3Input',
            fields={
                'x': GraphQLInputField(GraphQLFloat, description='X座標'),
                'y': GraphQLInputField(GraphQLFloat, description='Y座標'),
                'z': GraphQLInputField(GraphQLFloat, description='Z座標')
            }
        )
        
        # オブジェクト型の定義
        object_type = GraphQLObjectType(
            name='BlenderObject',
            fields={
                'name': GraphQLField(GraphQLString, description='オブジェクト名'),
                'type': GraphQLField(GraphQLString, description='オブジェクトタイプ'),
                'location': GraphQLField(vector3_type, description='位置情報'),
                'rotation': GraphQLField(vector3_type, description='回転情報（度数法）'),
                'scale': GraphQLField(vector3_type, description='スケール情報')
            }
        )
        
        # シーン情報型の定義
        scene_info_type = GraphQLObjectType(
            name='SceneInfo',
            fields={
                'name': GraphQLField(GraphQLString, description='シーン名'),
                'objects': GraphQLField(
                    GraphQLList(object_type),
                    description='シーン内のオブジェクトリスト'
                )
            }
        )
        
        # オブジェクト作成結果型
        create_object_result_type = GraphQLObjectType(
            name='CreateObjectResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='作成成功フラグ'),
                'object': GraphQLField(object_type, description='作成されたオブジェクト')
            }
        )
        
        # オブジェクト変換結果型
        transform_object_result_type = GraphQLObjectType(
            name='TransformObjectResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='変換成功フラグ'),
                'object': GraphQLField(object_type, description='変換されたオブジェクト')
            }
        )
        
        # オブジェクト削除結果型
        delete_object_result_type = GraphQLObjectType(
            name='DeleteObjectResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='削除成功フラグ'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ')
            }
        )
        
        # オブジェクトタイプ列挙型
        object_type_enum = GraphQLEnumType(
            name='ObjectType',
            values={
                'CUBE': GraphQLEnumValue(description='立方体'),
                'SPHERE': GraphQLEnumValue(description='球体'),
                'CYLINDER': GraphQLEnumValue(description='円柱'),
                'CONE': GraphQLEnumValue(description='円錫'),
                'PLANE': GraphQLEnumValue(description='平面'),
                'EMPTY': GraphQLEnumValue(description='空'),
                'TORUS': GraphQLEnumValue(description='トーラス'),
                'SUZANNE': GraphQLEnumValue(description='サザンヌ'),
                'MESH': GraphQLEnumValue(description='カスタムメッシュ'),
            }
        )
        
        # ブーリアン操作タイプ列挙型
        boolean_operation_enum = GraphQLEnumType(
            name='BooleanOperationType',
            values={
                'UNION': GraphQLEnumValue(description='組み合わせ・結合'),
                'DIFFERENCE': GraphQLEnumValue(description='差集合・減算'),
                'INTERSECT': GraphQLEnumValue(description='共通部分・交差'),
            }
        )
        
        # マテリアルタイプ型
        material_type = GraphQLObjectType(
            name='Material',
            fields={
                'name': GraphQLField(GraphQLString, description='マテリアル名'),
                'baseColor': GraphQLField(vector3_type, description='ベースカラー'),
                'metallic': GraphQLField(GraphQLFloat, description='金属度'),
                'roughness': GraphQLField(GraphQLFloat, description='粗さ'),
                'useNodes': GraphQLField(GraphQLBoolean, description='ノード使用フラグ'),
            }
        )
        
        # テクスチャ型
        texture_type = GraphQLObjectType(
            name='Texture',
            fields={
                'name': GraphQLField(GraphQLString, description='テクスチャ名'),
                'type': GraphQLField(GraphQLString, description='テクスチャタイプ'),
                'filepath': GraphQLField(GraphQLString, description='ファイルパス'),
            }
        )
        
        # Polyhavenアセット型
        polyhaven_asset_type = GraphQLObjectType(
            name='PolyhavenAsset',
            fields={
                'id': GraphQLField(GraphQLString, description='アセットID'),
                'title': GraphQLField(GraphQLString, description='アセットタイトル'),
                'category': GraphQLField(GraphQLString, description='カテゴリ'),
                'downloadUrl': GraphQLField(GraphQLString, description='ダウンロードURL'),
                'thumbnailUrl': GraphQLField(GraphQLString, description='サムネイルURL'),
            }
        )
        
        # メッシュデータ型
        vertex_type = GraphQLObjectType(
            name='Vertex',
            fields={
                'index': GraphQLField(GraphQLInt, description='頂点インデックス'),
                'position': GraphQLField(vector3_type, description='位置'),
                'normal': GraphQLField(vector3_type, description='法線'),
            }
        )
        
        edge_type = GraphQLObjectType(
            name='Edge',
            fields={
                'index': GraphQLField(GraphQLInt, description='エッジインデックス'),
                'vertices': GraphQLField(
                    GraphQLList(GraphQLInt),
                    description='エッジを構成する頂点インデックス配列'
                ),
            }
        )
        
        face_type = GraphQLObjectType(
            name='Face',
            fields={
                'index': GraphQLField(GraphQLInt, description='フェイスインデックス'),
                'vertices': GraphQLField(
                    GraphQLList(GraphQLInt),
                    description='フェイスを構成する頂点インデックス配列'
                ),
                'material_index': GraphQLField(GraphQLInt, description='マテリアルインデックス'),
            }
        )
        
        mesh_data_type = GraphQLObjectType(
            name='MeshData',
            fields={
                'name': GraphQLField(GraphQLString, description='メッシュ名'),
                'vertices': GraphQLField(
                    GraphQLList(vertex_type),
                    description='頂点リスト'
                ),
                'edges': GraphQLField(
                    GraphQLList(edge_type),
                    description='エッジリスト'
                ),
                'faces': GraphQLField(
                    GraphQLList(face_type),
                    description='フェイスリスト'
                ),
                'materials': GraphQLField(
                    GraphQLList(material_type),
                    description='適用されたマテリアル'
                ),
            }
        )

        # 入力型も定義
        vertex_input_type = GraphQLInputObjectType(
            name='VertexInput',
            fields={
                'position': GraphQLInputField(vector3_input_type, description='頂点位置'),
            }
        )
        
        face_input_type = GraphQLInputObjectType(
            name='FaceInput',
            fields={
                'vertices': GraphQLInputField(
                    GraphQLList(GraphQLInt),
                    description='フェイスを構成する頂点インデックス配列'
                ),
                'material_index': GraphQLInputField(GraphQLInt, description='マテリアルインデックス', default_value=0),
            }
        )
        
        # 操作結果型
        mesh_operation_result_type = GraphQLObjectType(
            name='MeshOperationResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='操作成功フラグ'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                'mesh': GraphQLField(mesh_data_type, description='操作後のメッシュデータ'),
            }
        )
        
        boolean_operation_result_type = GraphQLObjectType(
            name='BooleanOperationResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='操作成功フラグ'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                'object': GraphQLField(object_type, description='操作結果オブジェクト'),
            }
        )
        
        material_operation_result_type = GraphQLObjectType(
            name='MaterialOperationResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='操作成功フラグ'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                'material': GraphQLField(material_type, description='操作結果マテリアル'),
            }
        )
        
        # レンダリング設定型
        render_settings_type = GraphQLObjectType(
            name='RenderSettings',
            fields={
                'engine': GraphQLField(GraphQLString, description='レンダーエンジン'),
                'resolution_x': GraphQLField(GraphQLInt, description='X解像度'),
                'resolution_y': GraphQLField(GraphQLInt, description='Y解像度'),
                'resolution_percentage': GraphQLField(GraphQLInt, description='解像度パーセンテージ'),
                'file_format': GraphQLField(GraphQLString, description='ファイルフォーマット'),
                'filepath': GraphQLField(GraphQLString, description='出力ファイルパス'),
                'use_motion_blur': GraphQLField(GraphQLBoolean, description='モーションブラー'),
                'samples': GraphQLField(GraphQLInt, description='サンプル数'),
            }
        )
        
        # カメラ型
        camera_type = GraphQLObjectType(
            name='Camera',
            fields={
                'name': GraphQLField(GraphQLString, description='カメラ名'),
                'location': GraphQLField(vector3_type, description='位置'),
                'rotation': GraphQLField(vector3_type, description='回転（度数法）'),
                'type': GraphQLField(GraphQLString, description='カメラタイプ'),
                'lens': GraphQLField(GraphQLFloat, description='焦点距離'),
                'sensor_width': GraphQLField(GraphQLFloat, description='センサー幅'),
                'sensor_height': GraphQLField(GraphQLFloat, description='センサー高'),
                'clip_start': GraphQLField(GraphQLFloat, description='クリップ開始'),
                'clip_end': GraphQLField(GraphQLFloat, description='クリップ終了'),
                'perspective_type': GraphQLField(GraphQLString, description='パースペクティブタイプ'),
                'fov': GraphQLField(GraphQLFloat, description='視野角（度数法）'),
            }
        )
        
        # ライト型
        light_type = GraphQLObjectType(
            name='Light',
            fields={
                'name': GraphQLField(GraphQLString, description='ライト名'),
                'location': GraphQLField(vector3_type, description='位置'),
                'rotation': GraphQLField(vector3_type, description='回転（度数法）'),
                'type': GraphQLField(GraphQLString, description='ライトタイプ'),
                'color': GraphQLField(vector3_type, description='色'),
                'energy': GraphQLField(GraphQLFloat, description='強度'),
                'shadow': GraphQLField(GraphQLBoolean, description='シャドウ'),
                'size': GraphQLField(GraphQLFloat, description='サイズ'),
            }
        )
        
        # モディファイア型
        modifier_type = GraphQLObjectType(
            name='Modifier',
            fields={
                'name': GraphQLField(GraphQLString, description='モディファイア名'),
                'type': GraphQLField(GraphQLString, description='モディファイアタイプ'),
                'show_viewport': GraphQLField(GraphQLBoolean, description='ビューポートに表示'),
                'show_render': GraphQLField(GraphQLBoolean, description='レンダリングに表示'),
            }
        )
        
        # 操作結果型
        generic_operation_result_type = GraphQLObjectType(
            name='GenericOperationResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='操作成功フラグ'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                'data': GraphQLField(GraphQLString, description='操作結果データ（JSON形式）'),
            }
        )
        
        # レンダリング操作結果型
        render_operation_result_type = GraphQLObjectType(
            name='RenderOperationResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='操作成功フラグ'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                'filepath': GraphQLField(GraphQLString, description='出力ファイルパス'),
                'settings': GraphQLField(render_settings_type, description='レンダリング設定'),
            }
        )
        
        # カメラ操作結果型
        camera_operation_result_type = GraphQLObjectType(
            name='CameraOperationResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='操作成功フラグ'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                'camera': GraphQLField(camera_type, description='操作結果カメラ'),
            }
        )
        
        # ライト操作結果型
        light_operation_result_type = GraphQLObjectType(
            name='LightOperationResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='操作成功フラグ'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                'light': GraphQLField(light_type, description='操作結果ライト'),
            }
        )
        
        # モディファイア操作結果型
        modifier_operation_result_type = GraphQLObjectType(
            name='ModifierOperationResult',
            fields={
                'success': GraphQLField(GraphQLBoolean, description='操作成功フラグ'),
                'message': GraphQLField(GraphQLString, description='結果メッセージ'),
                'modifier': GraphQLField(modifier_type, description='操作結果モディファイア'),
                'object': GraphQLField(object_type, description='関連オブジェクト'),
            }
        )
        
        polyhaven_search_result_type = GraphQLObjectType(
            name='PolyhavenSearchResult',
            fields={
                'totalCount': GraphQLField(GraphQLInt, description='総件数'),
                'assets': GraphQLField(
                    GraphQLList(polyhaven_asset_type),
                    description='Polyhavenアセット一覧'
                ),
            }
        )
        
        # リゾルバ関数を参照
        # 各リゾルバ関数が存在するか確認
        for resolver_name in [
            'resolve_hello', 'resolve_scene_info', 'resolve_object',
            'resolve_create_object', 'resolve_transform_object', 'resolve_delete_object'
        ]:
            if not hasattr(resolvers, resolver_name):
                logger.error(f"リゾルバ関数 {resolver_name} が見つかりません")
                return None
            
        logger.info("スキーマの型定義が完了しました。クエリ・ミューテーションの定義を行います。")
        
        # ----------------------
        # クエリタイプの定義
        # ----------------------
        
        # リゾルバモジュールからリゾルバ関数を使用
        logger.info("リゾルバモジュールからリゾルバ関数を参照します")
        
        # ---------------------
        # スキーマ定義
        # ---------------------
        
        # クエリタイプの定義（読み取り操作）
        query_type = GraphQLObjectType(
            name='Query',
            fields={
                'hello': GraphQLField(
                    GraphQLString,
                    description='テスト用挙拶メッセージ',
                    resolve=RESOLVER_MODULE.hello
                ),
                'sceneInfo': GraphQLField(
                    scene_info_type,
                    description='現在のシーン情報',
                    resolve=RESOLVER_MODULE.scene_info
                ),
                'object': GraphQLField(
                    object_type,
                    description='指定された名前のオブジェクト情報',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名')
                    },
                    resolve=RESOLVER_MODULE.object
                ),
                # メッシュデータ取得
                'meshData': GraphQLField(
                    mesh_data_type,
                    description='メッシュデータ取得',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名')
                    },
                    resolve=RESOLVER_MODULE.resolve_mesh_data
                ),
                # マテリアル一覧取得
                'materials': GraphQLField(
                    GraphQLList(material_type),
                    description='全マテリアル一覧',
                    resolve=RESOLVER_MODULE.materials
                ),
                # 特定マテリアル情報取得
                'material': GraphQLField(
                    material_type,
                    description='特定マテリアルの情報',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='マテリアル名')
                    },
                    resolve=RESOLVER_MODULE.resolve_material
                ),
                # Polyhaven素材検索
                'searchPolyhaven': GraphQLField(
                    polyhaven_search_result_type,
                    description='Polyhavenアセット検索',
                    args={
                        'query': GraphQLArgument(GraphQLString, description='検索クエリ'),
                        'category': GraphQLArgument(GraphQLString, description='カテゴリフィルタ'),
                        'limit': GraphQLArgument(GraphQLInt, description='取得件数制限', default_value=10)
                    },
                    resolve=RESOLVER_MODULE.search_polyhaven
                ),
                # テクスチャ一覧取得
                'textures': GraphQLField(
                    GraphQLList(texture_type),
                    description='全テクスチャ一覧',
                    resolve=RESOLVER_MODULE.textures
                ),
                # カメラ一覧取得
                'cameras': GraphQLField(
                    GraphQLList(camera_type),
                    description='全カメラ一覧',
                    resolve=RESOLVER_MODULE.cameras
                ),
                # 特定カメラ情報取得
                'camera': GraphQLField(
                    camera_type,
                    description='特定カメラの情報',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='カメラ名')
                    },
                    resolve=RESOLVER_MODULE.resolve_camera
                ),
                # ライト一覧取得
                'lights': GraphQLField(
                    GraphQLList(light_type),
                    description='全ライト一覧',
                    resolve=RESOLVER_MODULE.lights
                ),
                # 特定ライト情報取得
                'light': GraphQLField(
                    light_type,
                    description='特定ライトの情報',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ライト名')
                    },
                    resolve=RESOLVER_MODULE.resolve_light
                ),
                # レンダリング設定取得
                'renderSettings': GraphQLField(
                    render_settings_type,
                    description='現在のレンダリング設定',
                    resolve=RESOLVER_MODULE.render_settings
                ),
                # モディファイア一覧取得
                'modifiers': GraphQLField(
                    GraphQLList(modifier_type),
                    description='指定されたオブジェクトのモディファイア一覧',
                    args={
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名')
                    },
                    resolve=RESOLVER_MODULE.modifiers
                )
            }
        )
        
        # ミューテーションタイプの定義（書き込み操作）
        mutation_type = GraphQLObjectType(
            name='Mutation',
            fields={
                'createObject': GraphQLField(
                    create_object_result_type,
                    description='新規オブジェクトを作成',
                    args={
                        'type': GraphQLArgument(object_type_enum, description='オブジェクトタイプ'),
                        'name': GraphQLArgument(GraphQLString, description='オブジェクト名（指定しない場合は自動生成）'),
                        'location': GraphQLArgument(vector3_input_type, description='作成位置')
                    },
                    resolve=RESOLVER_MODULE.create_object
                ),
                'transformObject': GraphQLField(
                    transform_object_result_type,
                    description='オブジェクトを変換（移動・回転・スケール）',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'location': GraphQLArgument(vector3_input_type, description='新しい位置'),
                        'rotation': GraphQLArgument(vector3_input_type, description='新しい回転（度数法）'),
                        'scale': GraphQLArgument(vector3_input_type, description='新しいスケール')
                    },
                    resolve=RESOLVER_MODULE.transform_object
                ),
                'deleteObject': GraphQLField(
                    delete_object_result_type,
                    description='オブジェクトを削除',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名')
                    },
                    resolve=RESOLVER_MODULE.delete_object
                ),
                # カメラ関連のミューテーション
                'createCamera': GraphQLField(
                    camera_operation_result_type,
                    description='新規カメラを作成',
                    args={
                        'name': GraphQLArgument(GraphQLString, description='カメラ名（省略時は自動生成）'),
                        'location': GraphQLArgument(vector3_input_type, description='位置'),
                        'rotation': GraphQLArgument(vector3_input_type, description='回転（度数法）'),
                        'type': GraphQLArgument(GraphQLString, description='カメラタイプ', default_value='PERSP'),
                        'lens': GraphQLArgument(GraphQLFloat, description='焦点距離', default_value=50.0),
                        'clip_start': GraphQLArgument(GraphQLFloat, description='クリップ開始', default_value=0.1),
                        'clip_end': GraphQLArgument(GraphQLFloat, description='クリップ終了', default_value=1000.0),
                        'fov': GraphQLArgument(GraphQLFloat, description='視野角（度数法）', default_value=None)
                    },
                    resolve=RESOLVER_MODULE.resolve_create_camera
                ),
                'updateCamera': GraphQLField(
                    camera_operation_result_type,
                    description='カメラ設定を更新',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='カメラ名'),
                        'location': GraphQLArgument(vector3_input_type, description='新しい位置'),
                        'rotation': GraphQLArgument(vector3_input_type, description='新しい回転（度数法）'),
                        'lens': GraphQLArgument(GraphQLFloat, description='新しい焦点距離'),
                        'clip_start': GraphQLArgument(GraphQLFloat, description='新しいクリップ開始'),
                        'clip_end': GraphQLArgument(GraphQLFloat, description='新しいクリップ終了'),
                        'fov': GraphQLArgument(GraphQLFloat, description='新しい視野角（度数法）')
                    },
                    resolve=RESOLVER_MODULE.resolve_update_camera
                ),
                'deleteCamera': GraphQLField(
                    camera_operation_result_type,
                    description='カメラを削除',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='カメラ名')
                    },
                    resolve=RESOLVER_MODULE.resolve_delete_camera
                ),
                # ライト関連のミューテーション
                'createLight': GraphQLField(
                    light_operation_result_type,
                    description='新規ライトを作成',
                    args={
                        'name': GraphQLArgument(GraphQLString, description='ライト名（省略時は自動生成）'),
                        'type': GraphQLArgument(GraphQLString, description='ライトタイプ', default_value='POINT'),
                        'location': GraphQLArgument(vector3_input_type, description='位置'),
                        'rotation': GraphQLArgument(vector3_input_type, description='回転（度数法）'),
                        'color': GraphQLArgument(vector3_input_type, description='色'),
                        'energy': GraphQLArgument(GraphQLFloat, description='強度', default_value=10.0),
                        'shadow': GraphQLArgument(GraphQLBoolean, description='シャドウフラグ', default_value=True)
                    },
                    resolve=RESOLVER_MODULE.resolve_create_light
                ),
                'updateLight': GraphQLField(
                    light_operation_result_type,
                    description='ライト設定を更新',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ライト名'),
                        'location': GraphQLArgument(vector3_input_type, description='新しい位置'),
                        'rotation': GraphQLArgument(vector3_input_type, description='新しい回転（度数法）'),
                        'color': GraphQLArgument(vector3_input_type, description='新しい色'),
                        'energy': GraphQLArgument(GraphQLFloat, description='新しい強度'),
                        'shadow': GraphQLArgument(GraphQLBoolean, description='新しいシャドウフラグ')
                    },
                    resolve=RESOLVER_MODULE.resolve_update_light
                ),
                'deleteLight': GraphQLField(
                    light_operation_result_type,
                    description='ライトを削除',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ライト名')
                    },
                    resolve=RESOLVER_MODULE.resolve_delete_light
                ),
                # レンダリング関連のミューテーション
                'updateRenderSettings': GraphQLField(
                    render_operation_result_type,
                    description='レンダリング設定を更新',
                    args={
                        'engine': GraphQLArgument(GraphQLString, description='レンダーエンジン'),
                        'resolution_x': GraphQLArgument(GraphQLInt, description='X解像度'),
                        'resolution_y': GraphQLArgument(GraphQLInt, description='Y解像度'),
                        'resolution_percentage': GraphQLArgument(GraphQLInt, description='解像度パーセンテージ'),
                        'file_format': GraphQLArgument(GraphQLString, description='ファイルフォーマット'),
                        'filepath': GraphQLArgument(GraphQLString, description='出力ファイルパス'),
                        'samples': GraphQLArgument(GraphQLInt, description='サンプル数')
                    },
                    resolve=RESOLVER_MODULE.resolve_update_render_settings
                ),
                'renderFrame': GraphQLField(
                    render_operation_result_type,
                    description='レンダリングを実行',
                    args={
                        'filepath': GraphQLArgument(GraphQLString, description='出力ファイルパス（省略時は現在の設定を使用）'),
                        'frame': GraphQLArgument(GraphQLInt, description='レンダリングするフレーム番号（省略時は現在のフレーム）')
                    },
                    resolve=RESOLVER_MODULE.resolve_render_frame
                ),
                # モディファイアー関連のミューテーション
                'addModifier': GraphQLField(
                    modifier_operation_result_type,
                    description='オブジェクトにモディファイアーを追加',
                    args={
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'modType': GraphQLArgument(GraphQLNonNull(GraphQLString), description='モディファイアータイプ'),
                        'modName': GraphQLArgument(GraphQLString, description='モディファイアー名（省略時は自動生成）')
                    },
                    resolve=RESOLVER_MODULE.resolve_add_modifier
                ),
                'updateModifier': GraphQLField(
                    modifier_operation_result_type,
                    description='モディファイアー設定を更新',
                    args={
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'modName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='モディファイアー名'),
                        'params': GraphQLArgument(GraphQLNonNull(GraphQLString), description='パラメータ辞書（JSON文字列）')
                    },
                    resolve=RESOLVER_MODULE.resolve_update_modifier
                ),
                'applyModifier': GraphQLField(
                    modifier_operation_result_type,
                    description='モディファイアーを適用',
                    args={
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'modName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='モディファイアー名')
                    },
                    resolve=RESOLVER_MODULE.resolve_apply_modifier
                ),
                'deleteModifier': GraphQLField(
                    modifier_operation_result_type,
                    description='モディファイアーを削除',
                    args={
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'modName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='モディファイアー名')
                    },
                    resolve=RESOLVER_MODULE.resolve_delete_modifier
                ),
                # メッシュ作成
                'createMesh': GraphQLField(
                    mesh_operation_result_type,
                    description='カスタムメッシュを作成',
                    args={
                        'name': GraphQLArgument(GraphQLString, description='メッシュ名'),
                        'vertices': GraphQLArgument(GraphQLList(vertex_input_type), description='頂点リスト'),
                        'faces': GraphQLArgument(GraphQLList(face_input_type), description='フェイスリスト')
                    },
                    resolve=RESOLVER_MODULE.resolve_create_mesh
                ),
                # 頂点編集
                'editMeshVertices': GraphQLField(
                    mesh_operation_result_type,
                    description='メッシュの頂点を編集',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'vertexIndices': GraphQLArgument(GraphQLList(GraphQLInt), description='編集する頂点のインデックスリスト'),
                        'newPositions': GraphQLArgument(GraphQLList(vector3_input_type), description='新しい位置情報リスト')
                    },
                    resolve=RESOLVER_MODULE.resolve_edit_mesh_vertices
                ),
                # ブーリアン操作
                'booleanOperation': GraphQLField(
                    boolean_operation_result_type,
                    description='ブーリアン操作を実行',
                    args={
                        'operation': GraphQLArgument(boolean_operation_enum, description='ブーリアン操作タイプ'),
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='対象オブジェクト名'),
                        'targetName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='操作相手オブジェクト名'),
                        'resultName': GraphQLArgument(GraphQLString, description='結果オブジェクト名（省略時は自動生成）')
                    },
                    resolve=RESOLVER_MODULE.resolve_boolean_operation
                ),
                # マテリアル作成
                'createMaterial': GraphQLField(
                    material_operation_result_type,
                    description='新規マテリアル作成',
                    args={
                        'name': GraphQLArgument(GraphQLString, description='マテリアル名'),
                        'baseColor': GraphQLArgument(vector3_input_type, description='ベースカラー'),
                        'metallic': GraphQLArgument(GraphQLFloat, description='金属度'),
                        'roughness': GraphQLArgument(GraphQLFloat, description='粗さ'),
                        'useNodes': GraphQLArgument(GraphQLBoolean, description='ノード使用フラグ')
                    },
                    resolve=RESOLVER_MODULE.resolve_create_material
                ),
                # マテリアル割り当て
                'assignMaterial': GraphQLField(
                    material_operation_result_type,
                    description='オブジェクトにマテリアルを割り当て',
                    args={
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'materialName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='マテリアル名')
                    },
                    resolve=RESOLVER_MODULE.resolve_assign_material
                ),
                # テクスチャ追加
                'addTexture': GraphQLField(
                    material_operation_result_type,
                    description='マテリアルにテクスチャを追加',
                    args={
                        'materialName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='マテリアル名'),
                        'texturePath': GraphQLArgument(GraphQLNonNull(GraphQLString), description='テクスチャファイルパス'),
                        'textureType': GraphQLArgument(GraphQLString, description='テクスチャタイプ（color, normal, roughnessなど）')
                    },
                    resolve=RESOLVER_MODULE.resolve_add_texture
                ),
                # Polyhavenアセットダウンロード
                'importPolyhavenAsset': GraphQLField(
                    material_operation_result_type,
                    description='Polyhavenアセットをダウンロードしマテリアル作成',
                    args={
                        'assetId': GraphQLArgument(GraphQLNonNull(GraphQLString), description='アセットID'),
                        'resolution': GraphQLArgument(GraphQLString, description='解像度（「2k」「4k」など）', default_value='2k'),
                        'materialName': GraphQLArgument(GraphQLString, description='作成するマテリアル名（省略時はアセットIDが使用される）')
                    },
                    resolve=RESOLVER_MODULE.resolve_import_polyhaven_asset
                ),
                # カメラ作成
                'createCamera': GraphQLField(
                    camera_operation_result_type,
                    description='新規カメラを作成',
                    args={
                        'name': GraphQLArgument(GraphQLString, description='カメラ名（省略時は自動生成）'),
                        'location': GraphQLArgument(vector3_input_type, description='位置'),
                        'rotation': GraphQLArgument(vector3_input_type, description='回転（度数法）'),
                        'type': GraphQLArgument(GraphQLString, description='カメラタイプ（PERSP/ORTHO）', default_value='PERSP'),
                        'lens': GraphQLArgument(GraphQLFloat, description='焦点距離', default_value=50.0),
                        'clip_start': GraphQLArgument(GraphQLFloat, description='クリップ開始', default_value=0.1),
                        'clip_end': GraphQLArgument(GraphQLFloat, description='クリップ終了', default_value=100.0)
                    },
                    resolve=RESOLVER_MODULE.resolve_create_camera
                ),
                # カメラ編集
                'updateCamera': GraphQLField(
                    camera_operation_result_type,
                    description='既存カメラを編集',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='カメラ名'),
                        'location': GraphQLArgument(vector3_input_type, description='新しい位置'),
                        'rotation': GraphQLArgument(vector3_input_type, description='新しい回転（度数法）'),
                        'lens': GraphQLArgument(GraphQLFloat, description='新しい焦点距離'),
                        'clip_start': GraphQLArgument(GraphQLFloat, description='新しいクリップ開始'),
                        'clip_end': GraphQLArgument(GraphQLFloat, description='新しいクリップ終了')
                    },
                    resolve=RESOLVER_MODULE.resolve_update_camera
                ),
                # カメラ削除
                'deleteCamera': GraphQLField(
                    camera_operation_result_type,
                    description='カメラを削除',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='カメラ名')
                    },
                    resolve=RESOLVER_MODULE.resolve_delete_camera
                ),
                # ライト作成
                'createLight': GraphQLField(
                    light_operation_result_type,
                    description='新規ライトを作成',
                    args={
                        'name': GraphQLArgument(GraphQLString, description='ライト名（省略時は自動生成）'),
                        'type': GraphQLArgument(GraphQLString, description='ライトタイプ（POINT/SUN/SPOT/AREA）', default_value='POINT'),
                        'location': GraphQLArgument(vector3_input_type, description='位置'),
                        'rotation': GraphQLArgument(vector3_input_type, description='回転（度数法）'),
                        'color': GraphQLArgument(vector3_input_type, description='色'),
                        'energy': GraphQLArgument(GraphQLFloat, description='強度', default_value=10.0),
                        'shadow': GraphQLArgument(GraphQLBoolean, description='シャドウ使用フラグ', default_value=True)
                    },
                    resolve=RESOLVER_MODULE.resolve_create_light
                ),
                # ライト編集
                'updateLight': GraphQLField(
                    light_operation_result_type,
                    description='既存ライトを編集',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ライト名'),
                        'location': GraphQLArgument(vector3_input_type, description='新しい位置'),
                        'rotation': GraphQLArgument(vector3_input_type, description='新しい回転（度数法）'),
                        'color': GraphQLArgument(vector3_input_type, description='新しい色'),
                        'energy': GraphQLArgument(GraphQLFloat, description='新しい強度'),
                        'shadow': GraphQLArgument(GraphQLBoolean, description='シャドウ使用フラグ')
                    },
                    resolve=RESOLVER_MODULE.resolve_update_light
                ),
                # ライト削除
                'deleteLight': GraphQLField(
                    light_operation_result_type,
                    description='ライトを削除',
                    args={
                        'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='ライト名')
                    },
                    resolve=RESOLVER_MODULE.resolve_delete_light
                ),
                # レンダリング設定更新
                'updateRenderSettings': GraphQLField(
                    render_operation_result_type,
                    description='レンダリング設定を更新',
                    args={
                        'engine': GraphQLArgument(GraphQLString, description='レンダーエンジン（CYCLES/EEVEE/WORKBENCH）'),
                        'resolution_x': GraphQLArgument(GraphQLInt, description='X解像度'),
                        'resolution_y': GraphQLArgument(GraphQLInt, description='Y解像度'),
                        'resolution_percentage': GraphQLArgument(GraphQLInt, description='解像度パーセンテージ'),
                        'file_format': GraphQLArgument(GraphQLString, description='ファイルフォーマット（PNG/JPEG/OPEN_EXRなど）'),
                        'filepath': GraphQLArgument(GraphQLString, description='出力ファイルパス'),
                        'samples': GraphQLArgument(GraphQLInt, description='サンプル数')
                    },
                    resolve=RESOLVER_MODULE.resolve_update_render_settings
                ),
                # レンダリング実行
                'renderFrame': GraphQLField(
                    render_operation_result_type,
                    description='レンダリングを実行',
                    args={
                        'filepath': GraphQLArgument(GraphQLString, description='出力ファイルパス（省略時は現在の設定を使用）'),
                        'frame': GraphQLArgument(GraphQLInt, description='レンダリングするフレーム番号')
                    },
                    resolve=RESOLVER_MODULE.resolve_render_frame
                ),
                # モディファイア追加
                'addModifier': GraphQLField(
                    modifier_operation_result_type,
                    description='オブジェクトにモディファイアを追加',
                    args={
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'modifierType': GraphQLArgument(GraphQLNonNull(GraphQLString), description='モディファイアタイプ（SUBDIVISION/BEVEL/MIRRORなど）'),
                        'modifierName': GraphQLArgument(GraphQLString, description='モディファイア名（省略時はタイプから自動生成）'),
                        'parameters': GraphQLArgument(GraphQLString, description='モディファイアのパラメータ（JSON形式）')
                    },
                    resolve=RESOLVER_MODULE.resolve_add_modifier
                ),
                # モディファイア編集
                'updateModifier': GraphQLField(
                    modifier_operation_result_type,
                    description='モディファイアのパラメータを編集',
                    args={
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'modifierName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='モディファイア名'),
                        'parameters': GraphQLArgument(GraphQLNonNull(GraphQLString), description='新しいパラメータ（JSON形式）'),
                        'show_viewport': GraphQLArgument(GraphQLBoolean, description='ビューポートに表示'),
                        'show_render': GraphQLArgument(GraphQLBoolean, description='レンダリングに表示')
                    },
                    resolve=RESOLVER_MODULE.resolve_update_modifier
                ),
                # モディファイア適用
                'applyModifier': GraphQLField(
                    modifier_operation_result_type,
                    description='モディファイアを適用（固定化）',
                    args={
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'modifierName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='モディファイア名')
                    },
                    resolve=RESOLVER_MODULE.resolve_apply_modifier
                ),
                # モディファイア削除
                'deleteModifier': GraphQLField(
                    modifier_operation_result_type,
                    description='モディファイアを削除',
                    args={
                        'objectName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='オブジェクト名'),
                        'modifierName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='モディファイア名')
                    },
                    resolve=RESOLVER_MODULE.resolve_delete_modifier
                )
            }
        )
        
        # スキーマを作成
        schema = GraphQLSchema(query=query_type, mutation=mutation_type)
        
        _schema_built = True
        logger.info("GraphQLスキーマを正常に構築しました")
        return schema
        
    except Exception as e:
        logger.error(f"GraphQLスキーマ構築エラー: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        _schema_built = False
        schema = None
        return None