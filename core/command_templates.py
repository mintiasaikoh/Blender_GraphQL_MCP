"""
Command Templates
LLMの自然言語指示を正確なBlender操作に変換するためのテンプレート集
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger('blender_mcp.command_templates')

@dataclass
class CommandTemplate:
    """コマンドテンプレートの定義"""
    id: str
    name: str
    description: str
    keywords: List[str]
    parameters: Dict[str, Any]
    code_template: str
    pre_conditions: List[Callable] = field(default_factory=list)
    post_actions: List[Callable] = field(default_factory=list)
    
    def matches(self, text: str) -> float:
        """テキストとのマッチ度を計算"""
        text_lower = text.lower()
        keyword_matches = sum(1 for keyword in self.keywords if keyword in text_lower)
        return keyword_matches / len(self.keywords) if self.keywords else 0.0
    
    def generate_code(self, **kwargs) -> str:
        """パラメータを使用してコードを生成"""
        # デフォルトパラメータとマージ
        params = {**self.parameters, **kwargs}
        
        # テンプレートに値を挿入
        try:
            return self.code_template.format(**params)
        except KeyError as e:
            logger.error(f"Missing parameter for template {self.id}: {e}")
            raise

class CommandTemplateLibrary:
    """コマンドテンプレートのライブラリ"""
    
    def __init__(self):
        self.templates: Dict[str, CommandTemplate] = {}
        self._initialize_templates()
    
    def _initialize_templates(self):
        """基本的なテンプレートを初期化"""
        
        # プリミティブ作成テンプレート
        self.add_template(CommandTemplate(
            id="create_cube",
            name="立方体作成",
            description="立方体を作成します",
            keywords=['立方体', 'キューブ', 'cube', '箱', 'ボックス', 'box'],
            parameters={
                'location': '(0, 0, 0)',
                'size': '2',
                'name': '"Cube"'
            },
            code_template="""import bpy

# 立方体を作成
bpy.ops.mesh.primitive_cube_add(
    size={size},
    location={location}
)

# 名前を設定
obj = bpy.context.active_object
obj.name = {name}
"""
        ))
        
        self.add_template(CommandTemplate(
            id="create_sphere",
            name="球体作成",
            description="球体を作成します",
            keywords=['球', '球体', 'sphere', 'ボール', 'ball'],
            parameters={
                'location': '(0, 0, 0)',
                'radius': '1',
                'subdivisions': '2',
                'name': '"Sphere"'
            },
            code_template="""import bpy

# 球体を作成
bpy.ops.mesh.primitive_uv_sphere_add(
    radius={radius},
    location={location},
    subdivisions={subdivisions}
)

# 名前を設定
obj = bpy.context.active_object
obj.name = {name}
"""
        ))
        
        # 色/マテリアル設定テンプレート
        self.add_template(CommandTemplate(
            id="set_color",
            name="色設定",
            description="オブジェクトに色を設定します",
            keywords=['色', 'カラー', 'color', 'マテリアル', 'material'],
            parameters={
                'color': '(1.0, 0.0, 0.0, 1.0)',
                'material_name': '"Material"',
                'metallic': '0.0',
                'roughness': '0.5'
            },
            code_template="""import bpy

# アクティブオブジェクトを取得
obj = bpy.context.active_object
if not obj:
    raise Exception("No active object selected")

# マテリアルを作成または取得
mat_name = {material_name}
mat = bpy.data.materials.get(mat_name)
if not mat:
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True

# マテリアルをオブジェクトに適用
if obj.data.materials:
    obj.data.materials[0] = mat
else:
    obj.data.materials.append(mat)

# ノードを設定
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = {color}
    bsdf.inputs["Metallic"].default_value = {metallic}
    bsdf.inputs["Roughness"].default_value = {roughness}
"""
        ))
        
        # 移動/変形テンプレート
        self.add_template(CommandTemplate(
            id="move_object",
            name="オブジェクト移動",
            description="オブジェクトを移動します",
            keywords=['移動', 'move', '動かす', '位置', 'position'],
            parameters={
                'location': '(0, 0, 0)',
                'relative': 'False'
            },
            code_template="""import bpy

# アクティブオブジェクトを取得
obj = bpy.context.active_object
if not obj:
    raise Exception("No active object selected")

# 位置を設定
if {relative}:
    obj.location.x += {location}[0]
    obj.location.y += {location}[1]
    obj.location.z += {location}[2]
else:
    obj.location = {location}
"""
        ))
        
        self.add_template(CommandTemplate(
            id="scale_object",
            name="オブジェクトスケール",
            description="オブジェクトのサイズを変更します",
            keywords=['スケール', 'scale', 'サイズ', 'size', '大きさ', '拡大', '縮小'],
            parameters={
                'scale': '(1.0, 1.0, 1.0)',
                'uniform': 'True'
            },
            code_template="""import bpy

# アクティブオブジェクトを取得
obj = bpy.context.active_object
if not obj:
    raise Exception("No active object selected")

# スケールを設定
if {uniform}:
    scale_value = {scale}[0] if isinstance({scale}, tuple) else {scale}
    obj.scale = (scale_value, scale_value, scale_value)
else:
    obj.scale = {scale}
"""
        ))
        
        # 複合操作テンプレート
        self.add_template(CommandTemplate(
            id="create_colored_primitive",
            name="色付きプリミティブ作成",
            description="色付きのプリミティブを作成します",
            keywords=['作成', 'create', '色付き', 'colored'],
            parameters={
                'primitive_type': 'cube',
                'color': '(1.0, 0.0, 0.0, 1.0)',
                'location': '(0, 0, 0)',
                'size': '2',
                'name': '"ColoredObject"'
            },
            code_template="""import bpy

# プリミティブを作成
if '{primitive_type}' == 'cube':
    bpy.ops.mesh.primitive_cube_add(size={size}, location={location})
elif '{primitive_type}' == 'sphere':
    bpy.ops.mesh.primitive_uv_sphere_add(radius={size}/2, location={location})
elif '{primitive_type}' == 'cylinder':
    bpy.ops.mesh.primitive_cylinder_add(radius={size}/2, depth={size}, location={location})
else:
    bpy.ops.mesh.primitive_cube_add(size={size}, location={location})

# オブジェクトの名前を設定
obj = bpy.context.active_object
obj.name = {name}

# マテリアルを作成
mat = bpy.data.materials.new(name=f"{{name}}_Material")
mat.use_nodes = True

# 色を設定
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = {color}

# マテリアルを適用
obj.data.materials.append(mat)
"""
        ))
    
    def add_template(self, template: CommandTemplate):
        """テンプレートを追加"""
        self.templates[template.id] = template
    
    def find_best_match(self, text: str) -> Optional[CommandTemplate]:
        """最も適合するテンプレートを検索"""
        best_match = None
        best_score = 0.0
        
        for template in self.templates.values():
            score = template.matches(text)
            if score > best_score:
                best_score = score
                best_match = template
        
        return best_match if best_score > 0.3 else None
    
    def get_template(self, template_id: str) -> Optional[CommandTemplate]:
        """IDでテンプレートを取得"""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """利用可能なテンプレートのリストを返す"""
        return [
            {
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'keywords': template.keywords
            }
            for template in self.templates.values()
        ]

# グローバルインスタンス
_template_library = None

def get_template_library() -> CommandTemplateLibrary:
    """テンプレートライブラリのシングルトンインスタンスを取得"""
    global _template_library
    if _template_library is None:
        _template_library = CommandTemplateLibrary()
    return _template_library