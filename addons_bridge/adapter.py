"""
Blender GraphQL MCP - アドオン抽象化アダプター
各アドオンへの統一アクセスインターフェースを提供
"""

import logging
from typing import Dict, List, Any, Optional, Union, Callable

logger = logging.getLogger("blender_graphql_mcp.addons_bridge.adapter")

class AddonAdapter:
    """アドオン機能のアダプターベースクラス"""
    
    def __init__(self, addon_id: str):
        """初期化
        
        Args:
            addon_id: アドオンID
        """
        self.addon_id = addon_id
        self.is_available = self._check_availability()
        
    def _check_availability(self) -> bool:
        """アドオンの利用可能性を確認
        
        Returns:
            利用可能な場合はTrue
        """
        import bpy
        return self.addon_id in bpy.context.preferences.addons
        
    def get_capabilities(self) -> List[str]:
        """このアドオンが提供する機能リスト
        
        Returns:
            機能名のリスト
        """
        return []
        
    def execute(self, function_name: str, **params) -> Dict[str, Any]:
        """アドオン機能を実行
        
        Args:
            function_name: 実行する機能名
            **params: パラメータ
            
        Returns:
            実行結果を含む辞書
        """
        raise NotImplementedError("Subclasses must implement this")


class GeometryNodesAdapter(AddonAdapter):
    """Geometry Nodesアドオン用アダプター"""
    
    def __init__(self):
        """初期化"""
        super().__init__("geometry_nodes")
        
    def get_capabilities(self) -> List[str]:
        """提供する機能リスト"""
        return [
            "procedural_sphere",
            "procedural_landscape",
            "geometry_modifier"
        ]
        
    def execute(self, function_name: str, **params) -> Dict[str, Any]:
        """アドオン機能を実行"""
        if not self.is_available:
            return {
                "success": False,
                "status": "error",
                "message": "Geometry Nodes addon is not available"
            }
            
        if function_name == "procedural_sphere":
            return self._create_procedural_sphere(**params)
        elif function_name == "procedural_landscape":
            return self._create_procedural_landscape(**params)
        elif function_name == "geometry_modifier":
            return self._apply_geometry_modifier(**params)
            
        return {
            "success": False,
            "status": "error",
            "message": f"Unknown function: {function_name}"
        }
        
    def _create_procedural_sphere(self, name: Optional[str] = None, **params) -> Dict[str, Any]:
        """ジオメトリノードを使った球体作成
        
        Args:
            name: オブジェクト名（省略時は自動生成）
            **params: その他のパラメータ
            
        Returns:
            実行結果
        """
        from ..core.commands.addon_feature_commands import create_geometry_node_group
        
        # パラメータの準備
        if name is None:
            name = f"ProcSphere_{len(['obj' for obj in bpy.data.objects if 'ProcSphere_' in obj.name])}"
        
        size = params.get("size", 1.0)
        
        # 一時的な球体を作成
        import bpy
        bpy.ops.mesh.primitive_uv_sphere_add(radius=size)
        obj = bpy.context.active_object
        obj.name = name
        
        # ジオメトリノードグループを適用
        node_group_name = f"{name}_nodes"
        result = create_geometry_node_group(node_group_name, name, "PROCEDURAL_SPHERE")
        
        # 結果を返却
        return {
            "success": result.get("success", False),
            "status": result.get("status", "unknown"),
            "message": result.get("message", ""),
            "object_name": name,
            "node_group_name": node_group_name
        }
        
    def _create_procedural_landscape(self, name: Optional[str] = None, **params) -> Dict[str, Any]:
        """ジオメトリノードを使った地形作成
        
        Args:
            name: オブジェクト名（省略時は自動生成）
            **params: その他のパラメータ
            
        Returns:
            実行結果
        """
        from ..core.commands.addon_feature_commands import create_geometry_node_group
        
        # パラメータの準備
        if name is None:
            name = f"Landscape_{len(['obj' for obj in bpy.data.objects if 'Landscape_' in obj.name])}"
        
        # 一時的な平面を作成
        import bpy
        bpy.ops.mesh.primitive_plane_add(size=10.0)
        obj = bpy.context.active_object
        obj.name = name
        
        # ジオメトリノードグループを適用
        node_group_name = f"{name}_nodes"
        result = create_geometry_node_group(node_group_name, name, "PROCEDURAL_LANDSCAPE")
        
        # 結果を返却
        return {
            "success": result.get("success", False),
            "status": result.get("status", "unknown"),
            "message": result.get("message", ""),
            "object_name": name,
            "node_group_name": node_group_name
        }
        
    def _apply_geometry_modifier(self, object_name: str, **params) -> Dict[str, Any]:
        """指定オブジェクトにジオメトリモディファイアを適用
        
        Args:
            object_name: 対象オブジェクト名
            **params: その他のパラメータ
            
        Returns:
            実行結果
        """
        from ..core.commands.addon_feature_commands import create_geometry_node_group
        
        # ジオメトリノードグループを適用
        setup_type = params.get("setup_type", "BASIC")
        node_group_name = params.get("node_group_name", f"{object_name}_geo_nodes")
        
        result = create_geometry_node_group(node_group_name, object_name, setup_type)
        
        # 結果を返却
        return result


# アダプターマップ - 知っているアドオンに対応するアダプター
ADAPTER_MAP = {
    "geometry_nodes": GeometryNodesAdapter
}

def get_adapter(addon_id: str) -> Optional[AddonAdapter]:
    """指定IDのアドオンアダプターを取得
    
    Args:
        addon_id: アドオンID
        
    Returns:
        アダプターインスタンス（未対応の場合はNone）
    """
    if addon_id not in ADAPTER_MAP:
        return None
        
    adapter_class = ADAPTER_MAP[addon_id]
    return adapter_class()

def get_all_adapters() -> Dict[str, AddonAdapter]:
    """すべてのアダプターのマップを取得
    
    Returns:
        アドオンID:アダプターインスタンスのマップ
    """
    adapters = {}
    
    for addon_id, adapter_class in ADAPTER_MAP.items():
        adapters[addon_id] = adapter_class()
        
    return adapters

def get_available_capabilities() -> Dict[str, List[str]]:
    """利用可能なすべての機能のマップを取得
    
    Returns:
        アドオンID:機能リストのマップ
    """
    capabilities = {}
    
    for addon_id, adapter_class in ADAPTER_MAP.items():
        adapter = adapter_class()
        if adapter.is_available:
            capabilities[addon_id] = adapter.get_capabilities()
            
    return capabilities
