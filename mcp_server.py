"""
MCP Server
LLMとBlenderをつなぐMCPサーバーの実装
"""

import asyncio
import json
import logging
from typing import Dict, Any
from mcp.server import Server, Tool
from mcp.types import Resource, Prompt

logger = logging.getLogger(__name__)

class BlenderMCPServer(Server):
    """
    MCPサーバー実装
    LLMからのリクエストを受けてBlenderに転送
    """
    
    def __init__(self):
        super().__init__("blender-mcp")
        self.blender_url = "http://localhost:8000/graphql"
        
    async def list_tools(self) -> list[Tool]:
        """利用可能なツールのリスト"""
        return [
            Tool(
                name="execute",
                description="Blenderで自然言語コマンドを実行",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "実行する自然言語コマンド"
                        }
                    },
                    "required": ["command"]
                }
            ),
            Tool(
                name="get_state",
                description="Blenderの現在の状態を取得",
                parameters={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: dict) -> Dict[str, Any]:
        """ツールの実行"""
        if name == "execute":
            return await self.execute_command(arguments["command"])
        elif name == "get_state":
            return await self.get_blender_state()
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """Blenderでコマンドを実行"""
        # GraphQLクエリを構築
        query = """
        mutation($cmd: String!) {
            executeNaturalCommand(command: $cmd) {
                success
                result
                preview
                error
                context {
                    selectedObjects {
                        name
                        type
                    }
                }
            }
        }
        """
        
        # Blenderに送信
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.blender_url,
                json={
                    "query": query,
                    "variables": {"cmd": command}
                }
            ) as response:
                result = await response.json()
                
        # 結果を返す
        execution_result = result.get("data", {}).get("executeNaturalCommand", {})
        
        return {
            "success": execution_result.get("success", False),
            "result": execution_result.get("result"),
            "preview": execution_result.get("preview"),
            "error": execution_result.get("error"),
            "objects": execution_result.get("context", {}).get("selectedObjects", [])
        }
    
    async def get_blender_state(self) -> Dict[str, Any]:
        """Blenderの状態を取得"""
        query = """
        query {
            sceneContext {
                name
                framesCurrent
                selectedObjects {
                    id
                    name
                    type
                    location { x y z }
                }
                mode
            }
        }
        """
        
        # Blenderに送信
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.blender_url,
                json={"query": query}
            ) as response:
                result = await response.json()
        
        return result.get("data", {}).get("sceneContext", {})
    
    async def list_resources(self) -> list[Resource]:
        """利用可能なリソース"""
        return [
            Resource(
                uri="blender://scene",
                name="Current Scene",
                description="現在のBlenderシーン情報",
                mime_type="application/json"
            )
        ]
    
    async def read_resource(self, uri: str) -> str:
        """リソースの読み取り"""
        if uri == "blender://scene":
            state = await self.get_blender_state()
            return json.dumps(state, indent=2)
        else:
            raise ValueError(f"Unknown resource: {uri}")
    
    async def list_prompts(self) -> list[Prompt]:
        """利用可能なプロンプトテンプレート"""
        return [
            Prompt(
                name="create_object",
                description="オブジェクト作成のテンプレート",
                prompt="Create a {color} {object_type} at position {x}, {y}, {z}"
            ),
            Prompt(
                name="modify_object", 
                description="オブジェクト変更のテンプレート",
                prompt="Change the {property} of {object_name} to {value}"
            )
        ]

# サーバー起動
async def main():
    server = BlenderMCPServer()
    
    # MCPプロトコルで通信開始
    async with asyncio.create_server(
        lambda: server.handle_connection(),
        'localhost',
        3000
    ) as server_instance:
        logger.info("MCP Server running on localhost:3000")
        await server_instance.serve_forever()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())