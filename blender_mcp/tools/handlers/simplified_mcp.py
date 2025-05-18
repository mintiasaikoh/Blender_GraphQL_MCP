"""
Simplified MCP Resolvers
LLMが使いやすいシンプルなリゾルバー実装
"""

import logging
from typing import Dict, Any, List, Optional
import bpy

from core.mcp_command_processor import get_mcp_processor
from core.blender_context import get_context_manager
from core.preview_generator import get_preview_generator

logger = logging.getLogger('blender_mcp.simplified_resolvers')

class SimplifiedMCPResolvers:
    """LLM向けの簡潔なリゾルバー"""
    
    def __init__(self):
        self.processor = get_mcp_processor()
        self.context = get_context_manager()
        self.preview = get_preview_generator()
    
    def execute(self, command: str) -> Dict[str, Any]:
        """
        最もシンプルな実行インターフェース
        LLMは単にテキストコマンドを送るだけ
        
        Args:
            command: 自然言語コマンドまたはPythonコード
            
        Returns:
            {
                "success": bool,
                "result": str,
                "preview": str (base64 image),
                "objects": [{"name": str, "type": str, "location": [x,y,z]}],
                "error": str (if failed)
            }
        """
        try:
            # Pythonコードかどうかを判定
            is_python = command.strip().startswith('import ') or 'bpy.' in command
            
            if is_python:
                # Pythonコードとして実行
                result = self.processor.process_raw_command(command)
            else:
                # 自然言語として処理
                from core.blender_mcp import get_blender_mcp
                mcp = get_blender_mcp()
                result = mcp.process_natural_command(command)
            
            # 簡潔な形式に変換
            return self._simplify_result(result)
            
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None,
                "preview": None,
                "objects": []
            }
    
    def get_state(self) -> Dict[str, Any]:
        """
        現在の状態を取得
        
        Returns:
            {
                "objects": [{"name": str, "type": str, "location": [x,y,z]}],
                "selected": [str],  # 選択中のオブジェクト名
                "mode": str,  # 現在のモード
                "preview": str  # base64画像
            }
        """
        try:
            context = self.context.get_scene_context()
            
            # オブジェクト情報を簡潔に
            objects = []
            for obj in bpy.data.objects:
                objects.append({
                    "name": obj.name,
                    "type": obj.type,
                    "location": list(obj.location)
                })
            
            # 選択中のオブジェクト
            selected = [obj.name for obj in bpy.context.selected_objects]
            
            # プレビュー生成
            preview_result = self.preview.capture_viewport()
            preview_image = preview_result.get("preview") if preview_result["success"] else None
            
            return {
                "objects": objects,
                "selected": selected,
                "mode": bpy.context.mode,
                "preview": preview_image
            }
            
        except Exception as e:
            logger.error(f"State retrieval error: {e}")
            return {
                "objects": [],
                "selected": [],
                "mode": "UNKNOWN",
                "preview": None,
                "error": str(e)
            }
    
    def batch_execute(self, commands: List[str]) -> List[Dict[str, Any]]:
        """
        複数のコマンドを順次実行
        
        Args:
            commands: コマンドのリスト
            
        Returns:
            各コマンドの実行結果のリスト
        """
        results = []
        
        for i, command in enumerate(commands):
            logger.info(f"Executing command {i+1}/{len(commands)}: {command[:50]}...")
            result = self.execute(command)
            results.append(result)
            
            # エラーが発生した場合は中断
            if not result["success"]:
                logger.warning(f"Command {i+1} failed, stopping batch execution")
                break
        
        return results
    
    def create_object(self, object_type: str, **kwargs) -> Dict[str, Any]:
        """
        オブジェクトを作成する簡易メソッド
        
        Args:
            object_type: "cube", "sphere", "cylinder" など
            **kwargs: color=(r,g,b), location=(x,y,z), size=float, name=str
            
        Returns:
            実行結果
        """
        # 自然言語コマンドを構築
        command_parts = [f"{object_type}を作成"]
        
        if "color" in kwargs:
            color = kwargs["color"]
            color_names = {
                (1, 0, 0): "赤い",
                (0, 1, 0): "緑の",
                (0, 0, 1): "青い",
                (1, 1, 0): "黄色い",
                (1, 0, 1): "紫の",
                (0, 1, 1): "水色の",
                (1, 1, 1): "白い",
                (0, 0, 0): "黒い"
            }
            color_name = color_names.get(color, "")
            if color_name:
                command_parts.insert(0, color_name)
        
        if "location" in kwargs:
            loc = kwargs["location"]
            command_parts.append(f"位置({loc[0]}, {loc[1]}, {loc[2]})")
        
        if "size" in kwargs:
            size = kwargs["size"]
            if size < 1:
                command_parts.insert(1, "小さい")
            elif size > 2:
                command_parts.insert(1, "大きい")
        
        if "name" in kwargs:
            command_parts.append(f'名前「{kwargs["name"]}」')
        
        command = " ".join(command_parts)
        return self.execute(command)
    
    def _simplify_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """結果を簡潔な形式に変換"""
        simplified = {
            "success": result.get("success", False),
            "result": None,
            "preview": None,
            "objects": [],
            "error": None
        }
        
        # エラー情報
        if not simplified["success"]:
            simplified["error"] = result.get("error", "Unknown error")
            
        # 実行結果
        if result.get("execution_result"):
            exec_result = result["execution_result"]
            simplified["result"] = exec_result.get("output", "")
        elif result.get("result"):
            simplified["result"] = str(result["result"])
        
        # プレビュー
        if result.get("preview"):
            simplified["preview"] = result["preview"]
        
        # オブジェクト情報
        if result.get("context_after"):
            context = result["context_after"]
            for obj_data in context.get("selected_objects", []):
                simplified["objects"].append({
                    "name": obj_data.get("id", ""),
                    "type": obj_data.get("type", ""),
                    "location": obj_data.get("location", [0, 0, 0])
                })
        
        return simplified

# グローバルインスタンス
_simplified_resolvers = None

def get_simplified_resolvers() -> SimplifiedMCPResolvers:
    """SimplifiedMCPResolversのシングルトンインスタンスを取得"""
    global _simplified_resolvers
    if _simplified_resolvers is None:
        _simplified_resolvers = SimplifiedMCPResolvers()
    return _simplified_resolvers

# シンプルなリゾルバー関数
def resolve_execute(root, info, command: str):
    """最もシンプルな実行関数"""
    return get_simplified_resolvers().execute(command)

def resolve_get_state(root, info):
    """状態取得"""
    return get_simplified_resolvers().get_state()

def resolve_batch_execute(root, info, commands: List[str]):
    """バッチ実行"""
    return get_simplified_resolvers().batch_execute(commands)

def resolve_create_object(root, info, object_type: str, **kwargs):
    """オブジェクト作成"""
    return get_simplified_resolvers().create_object(object_type, **kwargs)