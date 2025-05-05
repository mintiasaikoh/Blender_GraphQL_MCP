"""
Unified MCP サンプルプラグイン
プラグインシステムの使用例を示すサンプル実装
"""

import bpy
import logging
from typing import Dict, List, Any, Optional

# ロギング設定
logger = logging.getLogger('unified_mcp.plugins.sample')

# プラグイン情報
PLUGIN_INFO = {
    'name': 'サンプルプラグイン',
    'version': '1.0.0',
    'description': 'プラグインシステムのデモンストレーション',
    'author': 'Unified MCP Team',
    'docs_url': 'https://example.com/sample_plugin_docs'
}

# コマンド定義
SAMPLE_COMMANDS = [
    {
        'name': 'sample_create_cube',
        'description': 'サンプルキューブを作成',
        'callback': lambda params: create_sample_cube(params),
        'schema': {
            'type': 'object',
            'properties': {
                'size': {'type': 'number', 'description': 'キューブのサイズ'},
                'location': {
                    'type': 'array', 
                    'items': {'type': 'number'},
                    'description': '位置座標 [x, y, z]'
                }
            }
        }
    },
    {
        'name': 'sample_get_stats',
        'description': 'サンプル統計情報を取得',
        'callback': lambda params: get_sample_stats(),
        'schema': {
            'type': 'object',
            'properties': {}
        }
    }
]

# GraphQLスキーマ拡張
SAMPLE_SCHEMA_EXTENSIONS = [
    {
        'name': 'SampleExtension',
        'type_defs': '''
            extend type Query {
                sampleInfo: SampleInfo
            }
            
            type SampleInfo {
                pluginName: String!
                version: String!
                cubeCount: Int!
            }
        ''',
        'resolvers': {
            'Query': {
                'sampleInfo': lambda parent, info: {
                    'pluginName': PLUGIN_INFO['name'],
                    'version': PLUGIN_INFO['version'],
                    'cubeCount': count_cubes()
                }
            }
        }
    }
]

# UIコンポーネント
SAMPLE_UI_COMPONENTS = [
    {
        'type': 'panel',
        'space_type': 'VIEW_3D',
        'region_type': 'UI',
        'category': 'MCP',
        'label': 'サンプルプラグイン',
        'items': [
            {
                'type': 'operator',
                'operator': 'unified_mcp.execute_plugin_command',
                'text': 'サンプルキューブ作成',
                'properties': {
                    'command_name': 'sample_create_cube',
                    'command_params': '{"size": 2.0, "location": [0, 0, 0]}'
                }
            },
            {
                'type': 'operator',
                'operator': 'unified_mcp.execute_plugin_command',
                'text': '統計情報取得',
                'properties': {
                    'command_name': 'sample_get_stats',
                    'command_params': '{}'
                }
            }
        ]
    }
]

# プラグイン内部の関数実装
def create_sample_cube(params: Dict[str, Any]) -> Dict[str, Any]:
    """サンプルキューブを作成"""
    size = params.get('size', 1.0)
    location = params.get('location', [0, 0, 0])
    
    # メインスレッドでの実行を確保
    def execute():
        bpy.ops.mesh.primitive_cube_add(size=size, location=location)
        obj = bpy.context.active_object
        obj.name = f"SampleCube_{size}"
        return obj.name
    
    # Blenderのタイマーを使用してメインスレッドで実行
    cube_name = None
    
    def timer_callback():
        nonlocal cube_name
        cube_name = execute()
        return None  # タイマーを停止
    
    bpy.app.timers.register(timer_callback)
    
    # 少し待機してキューブ名を取得
    import time
    max_wait = 1.0
    start_time = time.time()
    while cube_name is None and time.time() - start_time < max_wait:
        time.sleep(0.05)
    
    return {
        'success': cube_name is not None,
        'cube_name': cube_name,
        'params': {
            'size': size,
            'location': location
        }
    }

def get_sample_stats() -> Dict[str, Any]:
    """サンプル統計情報を取得"""
    return {
        'plugin_info': PLUGIN_INFO,
        'cube_count': count_cubes(),
        'timestamp': bpy.context.scene.frame_current
    }

def count_cubes() -> int:
    """シーン内のサンプルキューブ数をカウント"""
    count = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name.startswith("SampleCube_"):
            count += 1
    return count

# プラグイン登録関数（必須）
def register_plugin():
    """プラグインを登録"""
    logger.info(f"サンプルプラグイン v{PLUGIN_INFO['version']} を登録しています...")
    
    # プラグイン情報を返す（必須）
    return {
        'name': PLUGIN_INFO['name'],
        'version': PLUGIN_INFO['version'],
        'description': PLUGIN_INFO['description'],
        'author': PLUGIN_INFO['author'],
        'commands': SAMPLE_COMMANDS,
        'schema_extensions': SAMPLE_SCHEMA_EXTENSIONS,
        'ui_components': SAMPLE_UI_COMPONENTS
    }

# プラグイン登録解除関数（任意）
def unregister_plugin():
    """プラグインを登録解除"""
    logger.info("サンプルプラグインを登録解除しています...")
    # クリーンアップが必要な場合はここに記述