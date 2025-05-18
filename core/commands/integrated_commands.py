"""
Blender GraphQL MCP - 統合コマンド
基本機能とアドオン機能を統合的に提供するコマンド
"""

import bpy
import os
import json
from typing import Dict, List, Any, Optional, Union

from ..commands.base import register_command
from ...addons_bridge import SUPPORTED_ADDONS, AddonBridge

# -----------------------------
# 統合モデリングコマンド
# -----------------------------

@register_command("create_procedural_object", "プロシージャルオブジェクトを作成")
def create_procedural_object(object_type: str, name: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    プロシージャルオブジェクトを作成する統合コマンド
    標準機能とアドオン機能を連携させて実行
    
    Args:
        object_type: オブジェクトタイプ（例: 'LANDSCAPE', 'PROCEDURAL_SPHERE', 'COMPLEX_SHAPE'）
        name: オブジェクト名（省略時は自動生成）
        params: その他のパラメータ
        
    Returns:
        結果を含む辞書
    """
    if params is None:
        params = {}
        
    # 自動名前生成
    if name is None:
        name = f"{object_type.lower()}_{len(bpy.data.objects)}"
    
    # オブジェクトタイプに応じた処理
    if object_type == "LANDSCAPE":
        # 地形生成（Geometry Nodes利用）
        return _create_landscape(name, params)
    
    elif object_type == "PROCEDURAL_SPHERE":
        # プロシージャル球体（Geometry Nodes利用）
        return _create_procedural_sphere(name, params)
    
    elif object_type == "COMPLEX_SHAPE":
        # 複雑な形状（Geometry Nodes利用）
        return _create_complex_shape(name, params)
    
    elif object_type == "ANIMATED_OBJECT":
        # アニメーションオブジェクト（Animation Nodes利用）
        return _create_animated_object(name, params)
    
    else:
        # 標準的なBlenderオブジェクト作成
        return _create_standard_object(object_type, name, params)

def _create_landscape(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """地形を生成する内部関数"""
    try:
        # Geometry Nodesが利用可能か確認
        if not AddonBridge.is_addon_enabled("geometry_nodes"):
            # アドオンを自動的に有効化
            bpy.ops.preferences.addon_enable(module="geometry_nodes")
            if not AddonBridge.is_addon_enabled("geometry_nodes"):
                return {
                    "status": "error",
                    "message": "Geometry Nodesアドオンを有効化できませんでした",
                    "success": False
                }
        
        # パラメータ取得
        size = params.get("size", 10.0)
        resolution = params.get("resolution", 32)
        height = params.get("height", 2.0)
        noise_scale = params.get("noise_scale", 2.0)
        seed = params.get("seed", 0)
        
        # 基本グリッドを作成
        bpy.ops.mesh.primitive_grid_add(
            size=size, 
            x_subdivisions=resolution, 
            y_subdivisions=resolution
        )
        obj = bpy.context.active_object
        obj.name = name
        
        # Geometry Nodesを使用
        from .addon_feature_commands import create_geometry_node_group
        
        node_group_result = create_geometry_node_group(
            name=f"{name}_landscape", 
            object_name=name, 
            setup_type="PROCEDURAL_LANDSCAPE"
        )
        
        if node_group_result.get("status") != "success":
            return {
                "status": "partial",
                "message": "オブジェクトは作成されましたが、地形生成に失敗しました",
                "object_name": name,
                "error": node_group_result.get("message"),
                "success": True  # オブジェクト自体は作成
            }
        
        # モディファイア設定を調整
        modifier_name = node_group_result.get("modifier_name")
        if modifier_name and modifier_name in obj.modifiers:
            # 具体的なモディファイアのパラメータ調整は
            # Blenderバージョンやノードツリー構成に依存するため実装しない
            pass
        
        return {
            "status": "success",
            "message": f"地形 '{name}' を作成しました",
            "object_name": name,
            "object_type": "LANDSCAPE",
            "node_group_name": node_group_result.get("node_group_name"),
            "modifier_name": modifier_name,
            "success": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"地形の作成中にエラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False
        }

def _create_procedural_sphere(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """プロシージャル球体を生成する内部関数"""
    try:
        # Geometry Nodesが利用可能か確認
        if not AddonBridge.is_addon_enabled("geometry_nodes"):
            # アドオンを自動的に有効化
            bpy.ops.preferences.addon_enable(module="geometry_nodes")
            if not AddonBridge.is_addon_enabled("geometry_nodes"):
                return {
                    "status": "error",
                    "message": "Geometry Nodesアドオンを有効化できませんでした",
                    "success": False
                }
        
        # パラメータ取得
        radius = params.get("radius", 1.0)
        subdivision = params.get("subdivision", 3)
        distortion = params.get("distortion", 0.0)
        
        # 基本オブジェクト作成
        bpy.ops.mesh.primitive_ico_sphere_add(radius=radius, subdivisions=subdivision)
        obj = bpy.context.active_object
        obj.name = name
        
        # 変形が必要な場合
        if distortion > 0:
            # Geometry Nodesを使用
            from .addon_feature_commands import create_geometry_node_group
            
            node_group_result = create_geometry_node_group(
                name=f"{name}_distortion", 
                object_name=name, 
                setup_type="PROCEDURAL_SPHERE"
            )
            
            if node_group_result.get("status") != "success":
                return {
                    "status": "partial",
                    "message": "オブジェクトは作成されましたが、球体変形に失敗しました",
                    "object_name": name,
                    "error": node_group_result.get("message"),
                    "success": True  # オブジェクト自体は作成
                }
        
        return {
            "status": "success",
            "message": f"プロシージャル球体 '{name}' を作成しました",
            "object_name": name,
            "object_type": "PROCEDURAL_SPHERE",
            "success": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"プロシージャル球体の作成中にエラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False
        }

def _create_complex_shape(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """複雑な形状を生成する内部関数"""
    try:
        # Geometry Nodesを利用して複雑な形状を生成
        # 基本オブジェクトとして立方体を作成
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.active_object
        obj.name = name
        
        # Geometry Nodesを使用
        from .addon_feature_commands import create_geometry_node_group
        
        # 複雑な形状は任意のセットアップに置き換え可能
        node_group_result = create_geometry_node_group(
            name=f"{name}_complex", 
            object_name=name, 
            setup_type="PROCEDURAL_LANDSCAPE"  # 今回は例として地形生成を使用
        )
        
        if node_group_result.get("status") != "success":
            return {
                "status": "partial",
                "message": "オブジェクトは作成されましたが、形状生成に失敗しました",
                "object_name": name,
                "error": node_group_result.get("message"),
                "success": True  # オブジェクト自体は作成
            }
        
        # マテリアルを適用（Node Wranglerを利用）
        material_color = params.get("material_color", "#8B4513")
        metallic = params.get("metallic", 0.5)
        roughness = params.get("roughness", 0.7)
        
        from .addon_feature_commands import setup_pbr_material
        
        material_result = setup_pbr_material(
            material_name=f"{name}_material",
            base_color=material_color,
            metallic=metallic,
            roughness=roughness
        )
        
        if material_result.get("status") == "success":
            # マテリアルをオブジェクトに適用
            material = bpy.data.materials.get(f"{name}_material")
            if material and len(obj.data.materials) == 0:
                obj.data.materials.append(material)
        
        return {
            "status": "success",
            "message": f"複雑な形状 '{name}' を作成しました",
            "object_name": name,
            "object_type": "COMPLEX_SHAPE",
            "node_group_name": node_group_result.get("node_group_name"),
            "success": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"複雑な形状の作成中にエラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False
        }

def _create_animated_object(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """アニメーションオブジェクトを生成する内部関数"""
    try:
        # Animation Nodesが利用可能か確認
        if not AddonBridge.is_addon_enabled("animation_nodes"):
            # アドオンを自動的に有効化
            bpy.ops.preferences.addon_enable(module="animation_nodes")
            if not AddonBridge.is_addon_enabled("animation_nodes"):
                return {
                    "status": "error",
                    "message": "Animation Nodesアドオンを有効化できませんでした",
                    "success": False
                }
        
        # 基本オブジェクト作成
        object_type = params.get("base_object", "CUBE")
        if object_type == "CUBE":
            bpy.ops.mesh.primitive_cube_add()
        elif object_type == "SPHERE":
            bpy.ops.mesh.primitive_uv_sphere_add()
        elif object_type == "CYLINDER":
            bpy.ops.mesh.primitive_cylinder_add()
        else:
            bpy.ops.mesh.primitive_cube_add()
        
        obj = bpy.context.active_object
        obj.name = name
        
        # Animation Nodesを使用
        from .addon_feature_commands import create_animation_node_tree
        
        animation_type = params.get("animation_type", "OBJECT_WIGGLE")
        
        tree_result = create_animation_node_tree(
            name=f"{name}_animation",
            setup_type=animation_type,
            target_object=name
        )
        
        if tree_result.get("status") != "success":
            return {
                "status": "partial",
                "message": "オブジェクトは作成されましたが、アニメーション設定に失敗しました",
                "object_name": name,
                "error": tree_result.get("message"),
                "success": True  # オブジェクト自体は作成
            }
        
        return {
            "status": "success",
            "message": f"アニメーションオブジェクト '{name}' を作成しました",
            "object_name": name,
            "object_type": "ANIMATED_OBJECT",
            "tree_name": tree_result.get("tree_name"),
            "success": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"アニメーションオブジェクトの作成中にエラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False
        }

def _create_standard_object(object_type: str, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """標準的なBlenderオブジェクトを作成する内部関数"""
    try:
        # Blenderの標準オブジェクト作成
        if object_type == "CUBE":
            bpy.ops.mesh.primitive_cube_add()
        elif object_type == "SPHERE":
            bpy.ops.mesh.primitive_uv_sphere_add()
        elif object_type == "CYLINDER":
            bpy.ops.mesh.primitive_cylinder_add()
        elif object_type == "CONE":
            bpy.ops.mesh.primitive_cone_add()
        elif object_type == "TORUS":
            bpy.ops.mesh.primitive_torus_add()
        elif object_type == "GRID":
            bpy.ops.mesh.primitive_grid_add()
        elif object_type == "MONKEY":
            bpy.ops.mesh.primitive_monkey_add()
        else:
            return {
                "status": "error",
                "message": f"未知のオブジェクトタイプ: {object_type}",
                "success": False
            }
        
        # 作成されたオブジェクトの参照を取得
        obj = bpy.context.active_object
        obj.name = name
        
        # 位置、回転、スケールのパラメータを適用
        if "location" in params:
            loc = params["location"]
            if isinstance(loc, list) and len(loc) == 3:
                obj.location = loc
        
        if "rotation" in params:
            rot = params["rotation"]
            if isinstance(rot, list) and len(rot) == 3:
                obj.rotation_euler = [r * 3.14159 / 180.0 for r in rot]  # 度からラジアンに変換
        
        if "scale" in params:
            scale = params["scale"]
            if isinstance(scale, list) and len(scale) == 3:
                obj.scale = scale
            elif isinstance(scale, (int, float)):
                obj.scale = [scale, scale, scale]
        
        # マテリアルパラメータがあれば適用
        if "material_color" in params:
            # Node Wranglerが有効かチェック
            use_node_wrangler = AddonBridge.is_addon_enabled("node_wrangler")
            
            material_name = f"{name}_material"
            
            if use_node_wrangler:
                # Node Wranglerを使用して高度なマテリアルを設定
                from .addon_feature_commands import setup_pbr_material
                
                material_color = params.get("material_color")
                metallic = params.get("metallic", 0.0)
                roughness = params.get("roughness", 0.5)
                
                material_result = setup_pbr_material(
                    material_name=material_name,
                    base_color=material_color,
                    metallic=metallic,
                    roughness=roughness
                )
                
                if material_result.get("status") == "success":
                    # マテリアルをオブジェクトに適用
                    material = bpy.data.materials.get(material_name)
                    if material and len(obj.data.materials) == 0:
                        obj.data.materials.append(material)
            else:
                # 基本的なマテリアル作成
                if material_name not in bpy.data.materials:
                    material = bpy.data.materials.new(name=material_name)
                else:
                    material = bpy.data.materials[material_name]
                
                # ノード使用設定
                material.use_nodes = True
                
                # 色の設定
                material_color = params.get("material_color")
                if material_color.startswith('#') and len(material_color) == 7:
                    r = int(material_color[1:3], 16) / 255.0
                    g = int(material_color[3:5], 16) / 255.0
                    b = int(material_color[5:7], 16) / 255.0
                    
                    principled_bsdf = material.node_tree.nodes.get('Principled BSDF')
                    if principled_bsdf:
                        principled_bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
                
                # オブジェクトにマテリアルを適用
                if len(obj.data.materials) == 0:
                    obj.data.materials.append(material)
        
        return {
            "status": "success",
            "message": f"オブジェクト '{name}' ({object_type}) を作成しました",
            "object_name": name,
            "object_type": object_type,
            "success": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"オブジェクトの作成中にエラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False
        }

# -----------------------------
# 統合マテリアルコマンド
# -----------------------------

@register_command("create_material", "高度なマテリアルを作成")
def create_material(material_type: str, name: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    高度なマテリアルを作成する統合コマンド
    標準機能とNode Wranglerを連携させて実行
    
    Args:
        material_type: マテリアルタイプ（例: 'PBR', 'GLASS', 'METAL', 'WOOD'）
        name: マテリアル名（省略時は自動生成）
        params: その他のパラメータ
        
    Returns:
        結果を含む辞書
    """
    if params is None:
        params = {}
        
    # 自動名前生成
    if name is None:
        name = f"{material_type.lower()}_{len(bpy.data.materials)}"
    
    # 各マテリアルタイプに応じた処理
    if material_type == "PBR":
        # 標準PBRマテリアル
        base_color = params.get("base_color", "#FFFFFF")
        metallic = params.get("metallic", 0.0)
        roughness = params.get("roughness", 0.5)
        
        # Node Wranglerがあれば使用
        if AddonBridge.is_addon_enabled("node_wrangler"):
            from .addon_feature_commands import setup_pbr_material
            
            return setup_pbr_material(
                material_name=name,
                base_color=base_color,
                metallic=metallic,
                roughness=roughness
            )
        else:
            # 基本的なマテリアル作成
            try:
                # マテリアルの作成/取得
                if name in bpy.data.materials:
                    material = bpy.data.materials[name]
                else:
                    material = bpy.data.materials.new(name=name)
                
                # ノードの有効化
                material.use_nodes = True
                
                # 色の設定
                if base_color.startswith('#') and len(base_color) == 7:
                    r = int(base_color[1:3], 16) / 255.0
                    g = int(base_color[3:5], 16) / 255.0
                    b = int(base_color[5:7], 16) / 255.0
                    
                    principled_bsdf = material.node_tree.nodes.get('Principled BSDF')
                    if principled_bsdf:
                        principled_bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
                        principled_bsdf.inputs['Metallic'].default_value = metallic
                        principled_bsdf.inputs['Roughness'].default_value = roughness
                
                return {
                    "status": "success",
                    "message": f"マテリアル '{name}' を作成しました",
                    "material_name": name,
                    "material_type": "PBR",
                    "success": True
                }
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"マテリアルの作成中にエラーが発生しました: {str(e)}",
                    "error": str(e),
                    "success": False
                }
    
    elif material_type == "GLASS":
        # ガラスマテリアル
        try:
            # マテリアルの作成/取得
            if name in bpy.data.materials:
                material = bpy.data.materials[name]
            else:
                material = bpy.data.materials.new(name=name)
            
            # ノードの有効化
            material.use_nodes = True
            nodes = material.node_tree.nodes
            
            # 既存のノードをクリア
            nodes.clear()
            
            # 出力ノード追加
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            output_node.location = (300, 0)
            
            # ガラスBSDFノード追加
            glass_node = nodes.new(type='ShaderNodeBsdfGlass')
            glass_node.location = (0, 0)
            
            # パラメータ設定
            color = params.get("color", "#FFFFFF")
            if color.startswith('#') and len(color) == 7:
                r = int(color[1:3], 16) / 255.0
                g = int(color[3:5], 16) / 255.0
                b = int(color[5:7], 16) / 255.0
                glass_node.inputs['Color'].default_value = (r, g, b, 1.0)
            
            roughness = params.get("roughness", 0.0)
            glass_node.inputs['Roughness'].default_value = roughness
            
            ior = params.get("ior", 1.45)
            glass_node.inputs['IOR'].default_value = ior
            
            # ノードを接続
            material.node_tree.links.new(glass_node.outputs['BSDF'], output_node.inputs['Surface'])
            
            return {
                "status": "success",
                "message": f"ガラスマテリアル '{name}' を作成しました",
                "material_name": name,
                "material_type": "GLASS",
                "success": True
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"ガラスマテリアルの作成中にエラーが発生しました: {str(e)}",
                "error": str(e),
                "success": False
            }
    
    elif material_type == "METAL":
        # 金属マテリアル - Node Wranglerを使用
        try:
            # Node Wranglerが有効か確認
            if not AddonBridge.is_addon_enabled("node_wrangler"):
                # アドオンを自動的に有効化
                bpy.ops.preferences.addon_enable(module="node_wrangler")
                if not AddonBridge.is_addon_enabled("node_wrangler"):
                    return {
                        "status": "error",
                        "message": "Node Wranglerアドオンを有効化できませんでした",
                        "success": False
                    }
            
            # メタルタイプに応じてパラメータ調整
            metal_type = params.get("metal_type", "steel")
            
            if metal_type == "gold":
                base_color = params.get("base_color", "#FFD700")
                metallic = params.get("metallic", 1.0)
                roughness = params.get("roughness", 0.1)
            elif metal_type == "copper":
                base_color = params.get("base_color", "#B87333")
                metallic = params.get("metallic", 1.0)
                roughness = params.get("roughness", 0.2)
            elif metal_type == "silver":
                base_color = params.get("base_color", "#C0C0C0")
                metallic = params.get("metallic", 1.0)
                roughness = params.get("roughness", 0.1)
            else:  # steel
                base_color = params.get("base_color", "#808080")
                metallic = params.get("metallic", 1.0)
                roughness = params.get("roughness", 0.3)
            
            from .addon_feature_commands import setup_pbr_material
            
            return setup_pbr_material(
                material_name=name,
                base_color=base_color,
                metallic=metallic,
                roughness=roughness
            )
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"金属マテリアルの作成中にエラーが発生しました: {str(e)}",
                "error": str(e),
                "success": False
            }
    
    else:
        # その他の標準マテリアル
        try:
            # マテリアルの作成/取得
            if name in bpy.data.materials:
                material = bpy.data.materials[name]
            else:
                material = bpy.data.materials.new(name=name)
            
            # ノードの有効化
            material.use_nodes = True
            
            # 色の設定
            color = params.get("color", "#FFFFFF")
            if color.startswith('#') and len(color) == 7:
                r = int(color[1:3], 16) / 255.0
                g = int(color[3:5], 16) / 255.0
                b = int(color[5:7], 16) / 255.0
                
                principled_bsdf = material.node_tree.nodes.get('Principled BSDF')
                if principled_bsdf:
                    principled_bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
            
            return {
                "status": "success",
                "message": f"マテリアル '{name}' を作成しました",
                "material_name": name,
                "material_type": material_type,
                "success": True
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"マテリアルの作成中にエラーが発生しました: {str(e)}",
                "error": str(e),
                "success": False
            }