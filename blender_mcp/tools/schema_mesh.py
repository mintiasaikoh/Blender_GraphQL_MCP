"""
Blender GraphQL MCP - メッシュスキーマ拡張
メッシュ操作のGraphQLスキーマ定義
"""

import logging
from tools import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLString,
    GraphQLInt,
    GraphQLFloat,
    GraphQLBoolean,
    GraphQLList,
    GraphQLNonNull,
    GraphQLField,
    GraphQLArgument
)

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_mesh")

# レジストリのインポート
from .schema_registry import schema_registry
# リゾルバモジュールのインポート
import tools.resolver as RESOLVER_MODULE

def register_mesh_schema():
    """メッシュ操作のスキーマを登録"""
    
    # -----------------------------
    # メッシュデータ型
    # -----------------------------
    
    # 頂点型
    schema_registry.register_type('Vertex', GraphQLObjectType(
        name='Vertex',
        fields={
            'index': GraphQLField(GraphQLInt, description='頂点インデックス'),
            'x': GraphQLField(GraphQLFloat, description='X座標'),
            'y': GraphQLField(GraphQLFloat, description='Y座標'),
            'z': GraphQLField(GraphQLFloat, description='Z座標')
        }
    ))
    
    # エッジ型
    schema_registry.register_type('Edge', GraphQLObjectType(
        name='Edge',
        fields={
            'index': GraphQLField(GraphQLInt, description='エッジインデックス'),
            'vertex1': GraphQLField(GraphQLInt, description='頂点1のインデックス'),
            'vertex2': GraphQLField(GraphQLInt, description='頂点2のインデックス')
        }
    ))
    
    # 面型
    schema_registry.register_type('Face', GraphQLObjectType(
        name='Face',
        fields={
            'index': GraphQLField(GraphQLInt, description='面インデックス'),
            'vertices': GraphQLField(GraphQLList(GraphQLInt), description='面を構成する頂点のインデックスリスト')
        }
    ))
    
    # メッシュデータ型
    schema_registry.register_type('MeshData', GraphQLObjectType(
        name='MeshData',
        fields={
            'name': GraphQLField(GraphQLString, description='メッシュ名'),
            'vertices_count': GraphQLField(GraphQLInt, description='頂点数'),
            'edges_count': GraphQLField(GraphQLInt, description='エッジ数'),
            'faces_count': GraphQLField(GraphQLInt, description='面数'),
            'vertices': GraphQLField(GraphQLList(schema_registry.get_type('Vertex')), description='頂点リスト'),
            'edges': GraphQLField(GraphQLList(schema_registry.get_type('Edge')), description='エッジリスト'),
            'faces': GraphQLField(GraphQLList(schema_registry.get_type('Face')), description='面リスト')
        }
    ))
    
    # メッシュ操作結果型
    schema_registry.register_type('MeshOperationResult', GraphQLObjectType(
        name='MeshOperationResult',
        fields={
            'success': GraphQLField(GraphQLBoolean, description='成功フラグ'),
            'status': GraphQLField(GraphQLString, description='ステータス'),
            'message': GraphQLField(GraphQLString, description='メッセージ'),
            'object_name': GraphQLField(GraphQLString, description='オブジェクト名'),
            'mesh': GraphQLField(schema_registry.get_type('MeshData'), description='操作後のメッシュデータ')
        }
    ))
    
    # -----------------------------
    # メッシュクエリ
    # -----------------------------
    
    # メッシュデータクエリ
    schema_registry.register_query('meshData', GraphQLField(
        schema_registry.get_type('MeshData'),
        args={
            'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='メッシュ名')
        },
        description='指定したメッシュの詳細データを取得',
        resolve=lambda obj, info, name: RESOLVER_MODULE.resolve_mesh_data(obj, info, name)
    ))
    
    # -----------------------------
    # メッシュミューテーション
    # -----------------------------
    
    # メッシュ作成
    schema_registry.register_mutation('mesh.create', GraphQLField(
        schema_registry.get_type('MeshOperationResult'),
        args={
            'name': GraphQLArgument(GraphQLString, description='メッシュ名（省略時は自動生成）'),
            'primitive_type': GraphQLArgument(GraphQLString, description='プリミティブタイプ（cube, sphere, plane等）'),
            'params': GraphQLArgument(schema_registry.get_type('ParametersInput'), description='パラメータ')
        },
        description='新しいメッシュを作成',
        resolve=lambda obj, info, **kwargs: RESOLVER_MODULE.resolve_create_mesh(obj, info, **kwargs)
    ))
    
    # 頂点編集
    schema_registry.register_mutation('mesh.editVertices', GraphQLField(
        schema_registry.get_type('MeshOperationResult'),
        args={
            'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='メッシュ名'),
            'vertices': GraphQLArgument(GraphQLNonNull(GraphQLList(schema_registry.get_type('VectorInput'))), 
                                       description='新しい頂点座標リスト')
        },
        description='メッシュの頂点を編集',
        resolve=lambda obj, info, **kwargs: RESOLVER_MODULE.resolve_edit_mesh_vertices(obj, info, **kwargs)
    ))
    
    logger.info("メッシュスキーマを登録しました")
