"""
Blender GraphQL MCP - アドオン機能コマンド
各アドオンの具体的な機能を実行するためのコマンドを提供
"""

import bpy
import os
import json
from typing import Dict, List, Any, Optional, Union

from ..commands.base import register_command
from ...addons_bridge import SUPPORTED_ADDONS, AddonBridge

# -----------------------------
# ジオメトリノード機能コマンド
# -----------------------------

@register_command("create_geometry_node_group", "ジオメトリノードグループを作成")
def create_geometry_node_group(name: str, object_name: str, setup_type: str = "BASIC") -> Dict[str, Any]:
    """
    ジオメトリノードグループを作成し、オブジェクトに適用する
    
    Args:
        name: 作成するノードグループ名
        object_name: 対象オブジェクト名
        setup_type: セットアップタイプ（BASIC, PROCEDURAL_SPHERE, PROCEDURAL_LANDSCAPE など）
        
    Returns:
        結果を含む辞書
    """
    if "geometry_nodes" not in SUPPORTED_ADDONS:
        return {
            "status": "error",
            "message": "Geometry Nodesアドオンはサポートされていません"
        }
    
    # アドオンが有効か確認
    if not AddonBridge.is_addon_enabled("geometry_nodes"):
        return {
            "status": "error",
            "message": "Geometry Nodesアドオンが有効ではありません。有効化してから再試行してください。",
            "addon_name": "geometry_nodes",
            "is_enabled": False
        }
    
    try:
        # オブジェクトが存在するか確認
        if object_name not in bpy.data.objects:
            return {
                "status": "error",
                "message": f"オブジェクト '{object_name}' が見つかりません",
                "object_name": object_name
            }
            
        obj = bpy.data.objects[object_name]
        
        # ノードグループの作成
        if name in bpy.data.node_groups:
            # 同名のノードグループが既に存在する場合
            node_group = bpy.data.node_groups[name]
            if node_group.type != 'GeometryNodeTree':
                return {
                    "status": "error",
                    "message": f"名前 '{name}' は既に別のタイプのノードグループで使用されています",
                    "name": name,
                    "existing_type": node_group.type
                }
        else:
            # 新規ノードグループ作成
            node_group = bpy.data.node_groups.new(name=name, type='GeometryNodeTree')
        
        # 入出力ノードの設定
        if len(node_group.nodes) == 0:
            # 入力ノード
            input_node = node_group.nodes.new('NodeGroupInput')
            input_node.location = (-200, 0)
            
            # 出力ノード
            output_node = node_group.nodes.new('NodeGroupOutput')
            output_node.location = (200, 0)
            
            # ソケット設定
            node_group.inputs.clear()
            node_group.outputs.clear()
            
            geometry_in = node_group.inputs.new('NodeSocketGeometry', 'Geometry')
            geometry_out = node_group.outputs.new('NodeSocketGeometry', 'Geometry')
            
            # リンク
            node_group.links.new(input_node.outputs['Geometry'], output_node.inputs['Geometry'])
        
        # セットアップタイプに応じた処理
        if setup_type == "PROCEDURAL_SPHERE":
            # 球体生成ノードの設定
            if 'GeometryNodeMeshIcoSphere' in dir(bpy.types):
                sphere_node = node_group.nodes.new('GeometryNodeMeshIcoSphere')
                sphere_node.location = (0, 0)
                sphere_node.inputs['Radius'].default_value = 1.0
                sphere_node.inputs['Subdivisions'].default_value = 3
                
                # 入出力ノードとの接続
                input_node = next((n for n in node_group.nodes if n.type == 'GROUP_INPUT'), None)
                output_node = next((n for n in node_group.nodes if n.type == 'GROUP_OUTPUT'), None)
                
                if input_node and output_node:
                    # 既存のリンクを削除
                    for link in node_group.links:
                        if link.to_node == output_node and link.to_socket.name == 'Geometry':
                            node_group.links.remove(link)
                    
                    # 新しいリンクを作成
                    node_group.links.new(sphere_node.outputs['Mesh'], output_node.inputs['Geometry'])
        
        elif setup_type == "PROCEDURAL_LANDSCAPE":
            # 地形生成ノードの設定
            grid_node = node_group.nodes.new('GeometryNodeMeshGrid')
            grid_node.location = (-100, 100)
            grid_node.inputs['Size X'].default_value = 10.0
            grid_node.inputs['Size Y'].default_value = 10.0
            grid_node.inputs['Vertices X'].default_value = 32
            grid_node.inputs['Vertices Y'].default_value = 32
            
            # ノイズテクスチャノード
            noise_node = node_group.nodes.new('ShaderNodeTexNoise')
            noise_node.location = (-100, -100)
            noise_node.inputs['Scale'].default_value = 2.0
            noise_node.inputs['Detail'].default_value = 10.0
            
            # セットポジションノード
            set_position_node = node_group.nodes.new('GeometryNodeSetPosition')
            set_position_node.location = (100, 0)
            
            # マルチプライノード
            multiply_node = node_group.nodes.new('ShaderNodeMath')
            multiply_node.location = (0, -50)
            multiply_node.operation = 'MULTIPLY'
            multiply_node.inputs[1].default_value = 2.0  # 高さ倍率
            
            # 入出力ノードとの接続
            input_node = next((n for n in node_group.nodes if n.type == 'GROUP_INPUT'), None)
            output_node = next((n for n in node_group.nodes if n.type == 'GROUP_OUTPUT'), None)
            
            if input_node and output_node:
                # 既存のリンクを削除
                for link in node_group.links:
                    if link.to_node == output_node and link.to_socket.name == 'Geometry':
                        node_group.links.remove(link)
                
                # ノードの接続
                node_group.links.new(grid_node.outputs['Mesh'], set_position_node.inputs['Geometry'])
                node_group.links.new(noise_node.outputs['Fac'], multiply_node.inputs[0])
                
                # 頂点位置設定（Blenderバージョンによって異なる可能性あり）
                if hasattr(set_position_node.inputs, 'Offset'):
                    # 新しいBlenderバージョン
                    sep_xyz_node = node_group.nodes.new('ShaderNodeSeparateXYZ')
                    sep_xyz_node.location = (0, -150)
                    com_xyz_node = node_group.nodes.new('ShaderNodeCombineXYZ')
                    com_xyz_node.location = (100, -150)
                    
                    node_group.links.new(set_position_node.outputs['Geometry'], output_node.inputs['Geometry'])
                    node_group.links.new(multiply_node.outputs[0], com_xyz_node.inputs['Z'])
                    node_group.links.new(com_xyz_node.outputs['Vector'], set_position_node.inputs['Offset'])
                else:
                    # 古いバージョン
                    node_group.links.new(set_position_node.outputs['Geometry'], output_node.inputs['Geometry'])
                    node_group.links.new(multiply_node.outputs[0], set_position_node.inputs['Z'])
                
                # テクスチャ座標の接続
                if hasattr(set_position_node.inputs, 'Position'):
                    position_node = node_group.nodes.new('GeometryNodeInputPosition')
                    position_node.location = (-200, -100)
                    node_group.links.new(position_node.outputs['Position'], noise_node.inputs['Vector'])
        
        # モディファイアの適用
        # 既存のモディファイアをチェック
        existing_modifier = None
        for mod in obj.modifiers:
            if mod.type == 'NODES' and hasattr(mod, 'node_group') and mod.node_group == node_group:
                existing_modifier = mod
                break
        
        if not existing_modifier:
            # 新規モディファイア作成
            modifier = obj.modifiers.new(name=f"GeometryNodes_{name}", type='NODES')
            modifier.node_group = node_group
        else:
            # 既存モディファイアを更新
            modifier = existing_modifier
            
        return {
            "status": "success",
            "message": f"ジオメトリノードグループ '{name}' を作成し、オブジェクト '{object_name}' に適用しました",
            "node_group_name": name,
            "object_name": object_name,
            "setup_type": setup_type,
            "modifier_name": modifier.name,
            "success": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"ジオメトリノードグループの作成中にエラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False
        }

# -----------------------------
# アニメーションノード機能コマンド
# -----------------------------

@register_command("create_animation_node_tree", "アニメーションノードツリーを作成")
def create_animation_node_tree(name: str, setup_type: str = "BASIC", target_object: Optional[str] = None) -> Dict[str, Any]:
    """
    アニメーションノードツリーを作成する
    
    Args:
        name: 作成するノードツリー名
        setup_type: セットアップタイプ（BASIC, OBJECT_WIGGLE など）
        target_object: ターゲットオブジェクト名（必要な場合）
        
    Returns:
        結果を含む辞書
    """
    if "animation_nodes" not in SUPPORTED_ADDONS:
        return {
            "status": "error",
            "message": "Animation Nodesアドオンはサポートされていません"
        }
    
    # アドオンが有効か確認
    if not AddonBridge.is_addon_enabled("animation_nodes"):
        return {
            "status": "error",
            "message": "Animation Nodesアドオンが有効ではありません。有効化してから再試行してください。",
            "addon_name": "animation_nodes",
            "is_enabled": False
        }
    
    try:
        # アドオンブリッジを使用して関数呼び出し
        result = AddonBridge.call_addon_function("animation_nodes", "create_node_tree", name)
        
        if result is None:
            return {
                "status": "error",
                "message": "Animation Nodesの関数呼び出しに失敗しました",
                "success": False
            }
        
        # セットアップタイプに応じた処理
        tree = result
        
        if setup_type == "OBJECT_WIGGLE" and target_object:
            # オブジェクトが存在するか確認
            if target_object not in bpy.data.objects:
                return {
                    "status": "error",
                    "message": f"オブジェクト '{target_object}' が見つかりません",
                    "object_name": target_object,
                    "success": False
                }
            
            # Animation Nodesのモジュールにアクセス（アドオンブリッジ経由）
            an = __import__('animation_nodes')
            if an is None:
                return {
                    "status": "error",
                    "message": "Animation Nodesモジュールにアクセスできません",
                    "success": False
                }
            
            # ウィグルアニメーション用のノードを追加
            try:
                # 時間情報ノード
                time_info_node = tree.nodes.new("an_TimeInfoNode")
                time_info_node.location = (-400, 0)
                
                # 時間からサイン波を生成
                combine_float_node = tree.nodes.new("an_CombineVectorNode")
                combine_float_node.location = (-200, 0)
                
                # サイン波ノード1（X軸）
                sin_node1 = tree.nodes.new("an_FloatMathNode")
                sin_node1.location = (-300, 100)
                sin_node1.operation = "SINE"
                
                # サイン波ノード2（Y軸）
                sin_node2 = tree.nodes.new("an_FloatMathNode")
                sin_node2.location = (-300, 0)
                sin_node2.operation = "SINE"
                sin_node2.inputs[1].value = 0.5  # 位相差
                
                # サイン波ノード3（Z軸）
                sin_node3 = tree.nodes.new("an_FloatMathNode")
                sin_node3.location = (-300, -100)
                sin_node3.operation = "SINE"
                sin_node3.inputs[1].value = 1.0  # 位相差
                
                # スケールノード
                scale_node = tree.nodes.new("an_VectorMathNode")
                scale_node.location = (-100, 0)
                scale_node.operation = "SCALE"
                scale_node.inputs[1].value = 0.2  # スケール値
                
                # オブジェクトトランスフォーム出力ノード
                transform_output_node = tree.nodes.new("an_ObjectTransformsOutputNode")
                transform_output_node.location = (100, 0)
                transform_output_node.inputLocationIsAvailable = True
                transform_output_node.inputRotationIsAvailable = False
                transform_output_node.inputScaleIsAvailable = False
                
                # オブジェクト入力ノード
                object_input_node = tree.nodes.new("an_ObjectInstanceInput")
                object_input_node.location = (0, 100)
                object_input_node.setProperty("Object", bpy.data.objects[target_object])
                
                # リンク設定
                tree.links.new(time_info_node.outputs[0], sin_node1.inputs[0])
                tree.links.new(time_info_node.outputs[0], sin_node2.inputs[0])
                tree.links.new(time_info_node.outputs[0], sin_node3.inputs[0])
                
                tree.links.new(sin_node1.outputs[0], combine_float_node.inputs[0])
                tree.links.new(sin_node2.outputs[0], combine_float_node.inputs[1])
                tree.links.new(sin_node3.outputs[0], combine_float_node.inputs[2])
                
                tree.links.new(combine_float_node.outputs[0], scale_node.inputs[0])
                tree.links.new(scale_node.outputs[0], transform_output_node.inputs["Location"])
                tree.links.new(object_input_node.outputs[0], transform_output_node.inputs["Object"])
                
                return {
                    "status": "success",
                    "message": f"オブジェクト '{target_object}' にウィグルアニメーションを設定しました",
                    "tree_name": name,
                    "object_name": target_object,
                    "setup_type": setup_type,
                    "success": True
                }
                
            except Exception as node_error:
                return {
                    "status": "partial",
                    "message": f"ノードツリーは作成されましたが、ウィグルアニメーション設定に失敗しました: {str(node_error)}",
                    "tree_name": name,
                    "error": str(node_error),
                    "success": True  # ツリー自体は作成できた
                }
        
        # 基本設定の場合やその他のケース
        return {
            "status": "success",
            "message": f"アニメーションノードツリー '{name}' を作成しました",
            "tree_name": name,
            "setup_type": setup_type,
            "success": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"アニメーションノードツリーの作成中にエラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False
        }

# -----------------------------
# ノードラングラー機能コマンド
# -----------------------------

@register_command("setup_pbr_material", "PBRマテリアルをセットアップ")
def setup_pbr_material(material_name: str, base_color: str = "#FFFFFF", metallic: float = 0.0, roughness: float = 0.5) -> Dict[str, Any]:
    """
    Node Wranglerを使用してPBRマテリアルをセットアップする
    
    Args:
        material_name: マテリアル名
        base_color: 基本色（16進数カラーコード）
        metallic: 金属度 (0.0-1.0)
        roughness: 粗さ (0.0-1.0)
        
    Returns:
        結果を含む辞書
    """
    if "node_wrangler" not in SUPPORTED_ADDONS:
        return {
            "status": "error",
            "message": "Node Wranglerアドオンはサポートされていません"
        }
    
    # アドオンが有効か確認
    if not AddonBridge.is_addon_enabled("node_wrangler"):
        return {
            "status": "error",
            "message": "Node Wranglerアドオンが有効ではありません。有効化してから再試行してください。",
            "addon_name": "node_wrangler",
            "is_enabled": False
        }
    
    try:
        # 16進数カラーから RGB に変換
        if base_color.startswith('#') and len(base_color) == 7:
            r = int(base_color[1:3], 16) / 255.0
            g = int(base_color[3:5], 16) / 255.0
            b = int(base_color[5:7], 16) / 255.0
            color = (r, g, b, 1.0)
        else:
            return {
                "status": "error",
                "message": "無効なカラーフォーマットです。#RRGGBB形式で指定してください。",
                "success": False
            }
        
        # 数値の範囲確認
        metallic = max(0.0, min(1.0, metallic))
        roughness = max(0.0, min(1.0, roughness))
        
        # マテリアルの作成/取得
        if material_name in bpy.data.materials:
            material = bpy.data.materials[material_name]
        else:
            material = bpy.data.materials.new(name=material_name)
        
        # ノードの有効化
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        # 既存のノードをクリア
        nodes.clear()
        
        # 出力ノード追加
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (300, 0)
        
        # PrincipledBSDFノード追加
        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf_node.location = (0, 0)
        bsdf_node.inputs['Base Color'].default_value = color
        bsdf_node.inputs['Metallic'].default_value = metallic
        bsdf_node.inputs['Roughness'].default_value = roughness
        
        # ノードを接続
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])
        
        # Node Wranglerの自動テクスチャマッピング機能は直接呼び出せないため、
        # 代わりに基本的なノードセットアップを行う
        
        # 追加のPBRセットアップのためのノードを作成
        # テクスチャ座標ノード
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord')
        tex_coord_node.location = (-600, 0)
        
        # マッピングノード
        mapping_node = nodes.new(type='ShaderNodeMapping')
        mapping_node.location = (-400, 0)
        
        # ノードを接続
        links.new(tex_coord_node.outputs['UV'], mapping_node.inputs['Vector'])
        
        # このマテリアルを使用しているオブジェクトに適用
        objects_using_material = []
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material == material:
                        objects_using_material.append(obj.name)
                        break
        
        return {
            "status": "success",
            "message": f"PBRマテリアル '{material_name}' をセットアップしました",
            "material_name": material_name,
            "base_color": base_color,
            "metallic": metallic,
            "roughness": roughness,
            "nodes_created": ["PrincipledBSDF", "MaterialOutput", "TexCoord", "Mapping"],
            "objects_using_material": objects_using_material,
            "success": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"PBRマテリアルのセットアップ中にエラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False
        }