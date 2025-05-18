"""
Blender Unified MCP Addons Bridge
他のBlenderアドオンとの連携を提供するモジュール
"""

import bpy
import importlib
from typing import Dict, List, Any, Optional, Union, Callable

# 連携可能なアドオンリスト
SUPPORTED_ADDONS = [
    # Blender標準/組み込みアドオン（追加インストール不要）
    "geometry_nodes",  # Blender 2.92以降標準搭載
    "mesh_tools",      # メッシュ編集ツール
    "node_wrangler",   # ノードエディタ機能拡張

    # Blender Extensions Marketplace (https://extensions.blender.org/)から入手可能なアドオン
    "simple_deform_helper", # 変形補助ツール
    "orient_and_origin",    # 選択基準の方向と原点設定
    "mmd_tools",            # MMDモデル操作ツール
    "molecular_nodes",      # 分子構造生成
    "place_helper",         # オブジェクト配置ヘルパー
    "quick_groups",         # インスタンスグループ作成

    # 将来の連携可能性（Blender Extensions Marketplace対応予定）
    "one_click_damage",     # オブジェクト損傷効果
    "retopoflow",           # リトポロジーツール
    "auto_rig_pro",         # 自動リギングシステム

    # その他の互換アドオン
    "animation_nodes"
]

# アドオン機能マッピング
addon_functions = {}

class AddonBridge:
    """他のアドオンとの連携を管理するブリッジクラス"""
    
    @staticmethod
    def register_addon_function(addon_name: str, function_name: str, function: Callable) -> bool:
        """
        他のアドオンの関数を登録
        
        Args:
            addon_name: アドオン名
            function_name: 関数名
            function: 関数オブジェクト
            
        Returns:
            登録成功かどうか
        """
        key = f"{addon_name}.{function_name}"
        addon_functions[key] = function
        print(f"Unified MCP: アドオン関数を登録しました: {key}")
        return True
    
    @staticmethod
    def call_addon_function(addon_name: str, function_name: str, *args, **kwargs) -> Any:
        """
        登録された他のアドオンの関数を呼び出し
        
        Args:
            addon_name: アドオン名
            function_name: 関数名
            *args, **kwargs: 関数に渡す引数
            
        Returns:
            関数の戻り値
        """
        key = f"{addon_name}.{function_name}"
        if key in addon_functions:
            try:
                return addon_functions[key](*args, **kwargs)
            except Exception as e:
                print(f"Unified MCP: アドオン関数呼び出しエラー: {key} - {str(e)}")
                import traceback
                traceback.print_exc()
                return None
        else:
            print(f"Unified MCP: 未登録のアドオン関数: {key}")
            return None
    
    @staticmethod
    def get_addon_module(addon_name: str) -> Optional[Any]:
        """
        アドオンのモジュールを取得
        
        Args:
            addon_name: アドオン名
            
        Returns:
            アドオンモジュールまたはNone
        """
        if addon_name in SUPPORTED_ADDONS:
            try:
                return importlib.import_module(addon_name)
            except ImportError:
                print(f"Unified MCP: アドオン '{addon_name}' をインポートできません")
                return None
        else:
            print(f"Unified MCP: 未サポートのアドオン: {addon_name}")
            return None
    
    @staticmethod
    def is_addon_enabled(addon_name: str) -> bool:
        """
        アドオンが有効かどうかを確認
        
        Args:
            addon_name: アドオン名
            
        Returns:
            アドオンが有効かどうか
        """
        return addon_name in bpy.context.preferences.addons

    @staticmethod
    def get_enabled_addons() -> List[str]:
        """
        有効なサポート対象アドオンのリストを取得
        
        Returns:
            有効なアドオンのリスト
        """
        return [addon for addon in SUPPORTED_ADDONS if addon in bpy.context.preferences.addons]
    
    @staticmethod
    def get_addon_functions(addon_name: str) -> List[str]:
        """
        登録されたアドオン関数のリストを取得
        
        Args:
            addon_name: アドオン名
            
        Returns:
            関数名のリスト
        """
        prefix = f"{addon_name}."
        return [key.replace(prefix, "") for key in addon_functions if key.startswith(prefix)]

# -----------------------------
# アニメーションノード連携
# -----------------------------

def setup_animation_nodes_bridge():
    """Animation Nodesアドオンとの連携をセットアップ"""
    if not AddonBridge.is_addon_enabled("animation_nodes"):
        print("Unified MCP: Animation Nodesアドオンが有効ではありません")
        return False
    
    try:
        import animation_nodes as an
        
        # 関数の登録例
        def create_animation_node_tree(name: str) -> Any:
            """アニメーションノードツリーを作成"""
            try:
                tree = an.tree_info.create_node_tree(name)
                return tree
            except Exception as e:
                print(f"Unified MCP: アニメーションノードツリー作成エラー: {str(e)}")
                return None
        
        AddonBridge.register_addon_function("animation_nodes", "create_node_tree", create_animation_node_tree)
        
        # 他の関数も必要に応じて登録
        
        print("Unified MCP: Animation Nodesブリッジを設定しました")
        return True
    except ImportError:
        print("Unified MCP: Animation Nodesモジュールをインポートできません")
        return False

# -----------------------------
# ジオメトリーノード連携
# -----------------------------

def setup_geometry_nodes_bridge():
    """Geometry Nodesとの連携をセットアップ"""
    # Geometry Nodesは標準機能なので、特別なインポートは不要
    
    try:
        # 関数の登録例
        def create_geometry_node_group(name: str) -> Any:
            """ジオメトリノードグループを作成"""
            try:
                node_group = bpy.data.node_groups.new(name=name, type='GeometryNodeTree')
                return node_group
            except Exception as e:
                print(f"Unified MCP: ジオメトリノードグループ作成エラー: {str(e)}")
                return None
        
        AddonBridge.register_addon_function("geometry_nodes", "create_node_group", create_geometry_node_group)
        
        # オブジェクトにジオメトリノード修飾子を追加する関数
        def add_geometry_nodes_modifier(obj_name: str, node_group_name: str = None) -> Any:
            """オブジェクトにジオメトリノード修飾子を追加"""
            try:
                obj = bpy.data.objects.get(obj_name)
                if not obj:
                    print(f"Unified MCP: オブジェクト '{obj_name}' が見つかりません")
                    return None
                
                # 修飾子を追加
                modifier = obj.modifiers.new(name="GeometryNodes", type='NODES')
                
                # ノードグループを設定（指定されている場合）
                if node_group_name and node_group_name in bpy.data.node_groups:
                    modifier.node_group = bpy.data.node_groups.get(node_group_name)
                
                return modifier
            except Exception as e:
                print(f"Unified MCP: ジオメトリノード修飾子追加エラー: {str(e)}")
                return None
        
        AddonBridge.register_addon_function("geometry_nodes", "add_modifier", add_geometry_nodes_modifier)
        
        print("Unified MCP: Geometry Nodesブリッジを設定しました")
        return True
    except Exception as e:
        print(f"Unified MCP: Geometry Nodesブリッジ設定エラー: {str(e)}")
        return False

# -----------------------------
# レガシーアドオン互換性
# -----------------------------

def setup_legacy_mcp_bridge():
    """旧MCPアドオンとの互換性ブリッジをセットアップ"""
    if not AddonBridge.is_addon_enabled("blender_mcp"):
        print("Unified MCP: 旧MCPアドオンが有効ではありません")
        return False
    
    try:
        # 旧MCPのモジュールをインポート
        import blender_mcp
        
        # 互換性関数の登録
        # 例: execute_command関数のラッパー
        def legacy_execute_command(command: str, *args, **kwargs) -> Any:
            """旧MCPのexecute_command関数を呼び出す"""
            try:
                if hasattr(blender_mcp, 'execute_command'):
                    return blender_mcp.execute_command(command, *args, **kwargs)
                else:
                    print("Unified MCP: 旧MCPのexecute_command関数が見つかりません")
                    return None
            except Exception as e:
                print(f"Unified MCP: 旧MCP互換性関数呼び出しエラー: {str(e)}")
                return None
        
        AddonBridge.register_addon_function("blender_mcp", "execute_command", legacy_execute_command)
        
        print("Unified MCP: 旧MCPブリッジを設定しました")
        return True
    except ImportError:
        print("Unified MCP: 旧MCPモジュールをインポートできません")
        return False

def setup_legacy_llm_bridge():
    """旧LLM Bridgeアドオンとの互換性ブリッジをセットアップ"""
    if not AddonBridge.is_addon_enabled("blender_llm_bridge"):
        print("Unified MCP: 旧LLM Bridgeアドオンが有効ではありません")
        return False
    
    try:
        # 旧LLM Bridgeのモジュールをインポート
        import blender_llm_bridge
        
        # 互換性関数の登録
        # 例: send_to_llm関数のラッパー
        def legacy_send_to_llm(message: str, *args, **kwargs) -> Any:
            """旧LLM Bridgeのsend_to_llm関数を呼び出す"""
            try:
                if hasattr(blender_llm_bridge, 'send_to_llm'):
                    return blender_llm_bridge.send_to_llm(message, *args, **kwargs)
                else:
                    print("Unified MCP: 旧LLM Bridgeのsend_to_llm関数が見つかりません")
                    return None
            except Exception as e:
                print(f"Unified MCP: 旧LLM Bridge互換性関数呼び出しエラー: {str(e)}")
                return None
        
        AddonBridge.register_addon_function("blender_llm_bridge", "send_to_llm", legacy_send_to_llm)
        
        print("Unified MCP: 旧LLM Bridgeブリッジを設定しました")
        return True
    except ImportError:
        print("Unified MCP: 旧LLM Bridgeモジュールをインポートできません")
        return False

# -----------------------------
# モジュール登録関数
# -----------------------------

def register():
    """アドオンブリッジモジュールを登録"""
    print("Unified MCP: アドオンブリッジモジュールを登録しています...")
    
    # 各アドオンとの連携をセットアップ
    setup_geometry_nodes_bridge()
    setup_animation_nodes_bridge()
    
    # レガシーアドオンとの互換性を設定
    setup_legacy_mcp_bridge()
    setup_legacy_llm_bridge()
    
    print("Unified MCP: アドオンブリッジモジュールを登録しました")

def unregister():
    """アドオンブリッジモジュールの登録解除"""
    # 特別なクリーンアップは不要
    # 登録された関数はアドオンが登録解除される際に自動的にクリアされる
    print("Unified MCP: アドオンブリッジモジュールを登録解除しました")
