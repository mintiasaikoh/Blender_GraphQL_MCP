"""
Standard Model Context Protocol (MCP) Server Implementation
JSON-RPC 2.0 compliant MCP server that connects Blender to Language Models
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Union, Callable
import traceback
import aiohttp
from aiohttp import web

# Blender-specific imports
from Blender_GraphQL_MCP.tools.handlers.improved_mcp import get_improved_mcp_resolvers
from Blender_GraphQL_MCP.core.blender_mcp import get_blender_mcp
from Blender_GraphQL_MCP.core.blender_context import get_context_manager

logger = logging.getLogger('blender_graphql_mcp.tools.mcp_standard_server')

# Standard JSON-RPC 2.0 error codes
class ErrorCodes:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific error codes
    TOOL_NOT_FOUND = -32000
    TOOL_EXECUTION_ERROR = -32001
    RESOURCE_NOT_FOUND = -32010
    RESOURCE_READ_ERROR = -32011
    AUTHENTICATION_ERROR = -32020
    AUTHORIZATION_ERROR = -32021
    RATE_LIMIT_EXCEEDED = -32030

class MCPStandardServer:
    """
    Standard-compliant MCP Server implementing the Model Context Protocol
    based on JSON-RPC 2.0
    """
    
    def __init__(self, host: str = 'localhost', port: int = 3000):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.resolvers = get_improved_mcp_resolvers()
        self.mcp = get_blender_mcp()
        self.context_manager = get_context_manager()
        
        # Setup routes
        self.app.router.add_post('/', self.handle_jsonrpc)
        self.app.router.add_get('/status', self.handle_status)
        
        # Initialize methods registry
        self.methods = {
            # Standard MCP endpoints
            'initialize': self.initialize,
            'tools/list': self.list_tools,
            'tools/call': self.call_tool,
            'resources/list': self.list_resources,
            'resources/templates/list': self.list_resource_templates,
            'resources/read': self.read_resource,
            'prompts/list': self.list_prompts,
            'prompts/get': self.get_prompt,
            'shutdown': self.shutdown,
            'complete': self.complete,
            
            # Additional utility methods
            'context/get': self.get_context,
        }
        
        # Server state
        self.running = False
        self.initialized = False
        self.client_capabilities = {}
        self.runner = None
        self.site = None
    
    async def start(self):
        """Start the MCP server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        self.running = True
        logger.info(f"MCP Standard Server running on http://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the MCP server"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        self.running = False
        logger.info("MCP Standard Server stopped")
    
    async def handle_status(self, request):
        """Simple status endpoint for health checks"""
        return web.json_response({
            "status": "ok",
            "server": "Blender GraphQL MCP",
            "initialized": self.initialized
        })
    
    async def handle_jsonrpc(self, request):
        """Handle JSON-RPC 2.0 requests"""
        try:
            # Parse request
            body = await request.json()
            
            # Check if it's a batch request
            if isinstance(body, list):
                responses = [await self.process_single_request(req) for req in body]
                return web.json_response(responses)
            else:
                response = await self.process_single_request(body)
                return web.json_response(response)
                
        except json.JSONDecodeError:
            # Handle JSON parse error
            return web.json_response(self.make_error_response(
                None, ErrorCodes.PARSE_ERROR, "Invalid JSON"
            ))
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
            return web.json_response(self.make_error_response(
                None, ErrorCodes.INTERNAL_ERROR, f"Internal error: {str(e)}"
            ))
    
    async def process_single_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single JSON-RPC request"""
        # Check if it's a valid JSON-RPC 2.0 request
        if not isinstance(request, dict) or request.get('jsonrpc') != '2.0':
            return self.make_error_response(
                request.get('id'), ErrorCodes.INVALID_REQUEST,
                "Invalid JSON-RPC 2.0 request"
            )
        
        # Get request components
        request_id = request.get('id')
        method = request.get('method')
        params = request.get('params', {})
        
        # Check if it's a notification (no id)
        is_notification = 'id' not in request
        
        # Validate method
        if not method or not isinstance(method, str):
            return self.make_error_response(
                request_id, ErrorCodes.INVALID_REQUEST,
                "Method must be a non-empty string"
            )
        
        # Find and execute the method
        method_func = self.methods.get(method)
        if not method_func:
            return self.make_error_response(
                request_id, ErrorCodes.METHOD_NOT_FOUND,
                f"Method '{method}' not found"
            )
        
        try:
            result = await method_func(params)
            
            # Don't return a response for notifications
            if is_notification:
                return None
                
            # Return the result
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': result
            }
        except Exception as e:
            logger.error(f"Error executing method '{method}': {str(e)}")
            logger.error(traceback.format_exc())
            
            # Don't return errors for notifications
            if is_notification:
                return None
                
            # Return the error
            return self.make_error_response(
                request_id, ErrorCodes.INTERNAL_ERROR,
                f"Error executing method '{method}': {str(e)}"
            )
    
    def make_error_response(self, request_id: Optional[Union[str, int]], 
                          code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create a JSON-RPC 2.0 error response"""
        error = {
            'code': code,
            'message': message
        }
        
        if data is not None:
            error['data'] = data
            
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': error
        }
    
    # Standard MCP Endpoint Implementations
    
    async def initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the server with client capabilities
        This is the first method called by clients to establish capabilities
        """
        client_name = params.get('clientName', 'Unknown Client')
        client_version = params.get('clientVersion', 'Unknown Version')
        capabilities = params.get('capabilities', {})
        
        logger.info(f"Client connected: {client_name} {client_version}")
        
        # Store client capabilities for later use
        self.client_capabilities = capabilities
        self.initialized = True
        
        # Return server capabilities
        return {
            'serverName': 'Blender GraphQL MCP',
            'serverVersion': '1.0.0',
            'capabilities': {
                'tools': True,
                'resources': True,
                'prompts': True,
                'complete': True,
                'streaming': False,  # Could be implemented in the future
                'security': {
                    'authentication': False,  # No authentication required for local use
                }
            }
        }
    
    async def list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools that can be called by the client"""
        return {
            'tools': [
                {
                    'name': 'command.executeNatural',
                    'description': 'Execute a natural language command in Blender',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'command': {
                                'type': 'string',
                                'description': 'The natural language command to execute'
                            },
                            'options': {
                                'type': 'object',
                                'description': 'Optional execution parameters',
                                'properties': {
                                    'capturePreview': {
                                        'type': 'boolean',
                                        'description': 'Whether to capture and return a preview image'
                                    },
                                    'captureContext': {
                                        'type': 'boolean',
                                        'description': 'Whether to capture and return the scene context'
                                    }
                                }
                            }
                        },
                        'required': ['command']
                    }
                },
                {
                    'name': 'command.executeRaw',
                    'description': 'Execute raw Python code in Blender (use with caution)',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'pythonCode': {
                                'type': 'string',
                                'description': 'The Python code to execute'
                            },
                            'metadata': {
                                'type': 'object',
                                'description': 'Optional metadata about the execution'
                            }
                        },
                        'required': ['pythonCode']
                    }
                },
                {
                    'name': 'scene.capturePreview',
                    'description': 'Capture a preview image of the current viewport',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'width': {
                                'type': 'integer',
                                'description': 'Width of the preview image',
                                'default': 512
                            },
                            'height': {
                                'type': 'integer',
                                'description': 'Height of the preview image',
                                'default': 512
                            },
                            'view': {
                                'type': 'string',
                                'description': 'Viewport to capture',
                                'default': 'current'
                            }
                        }
                    }
                },
                {
                    'name': 'model.iterate',
                    'description': 'Iterate on a 3D model based on feedback',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'modelId': {
                                'type': 'string',
                                'description': 'ID of the model to iterate on'
                            },
                            'feedback': {
                                'type': 'string',
                                'description': 'Feedback to apply to the model'
                            },
                            'renderOptions': {
                                'type': 'object',
                                'description': 'Rendering options',
                                'properties': {
                                    'width': {
                                        'type': 'integer',
                                        'default': 512
                                    },
                                    'height': {
                                        'type': 'integer',
                                        'default': 512
                                    },
                                    'format': {
                                        'type': 'string',
                                        'default': 'PNG'
                                    }
                                }
                            }
                        },
                        'required': ['modelId', 'feedback']
                    }
                }
            ]
        }
    
    async def call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool with the specified parameters"""
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        if not tool_name:
            raise ValueError("Tool name is required")
        
        # Map tool names to resolver methods
        tool_map = {
            'command.executeNatural': self._execute_natural_command,
            'command.executeRaw': self._execute_raw_command,
            'scene.capturePreview': self._capture_preview,
            'model.iterate': self._iterate_on_model
        }
        
        tool_function = tool_map.get(tool_name)
        if not tool_function:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Execute the tool
        result = await tool_function(arguments)
        return result
    
    async def list_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available resources"""
        return {
            'resources': [
                {
                    'uri': 'blender://scene/context',
                    'name': 'Current Scene Context',
                    'description': 'Information about the current Blender scene',
                    'mimeType': 'application/json'
                },
                {
                    'uri': 'blender://scene/selected',
                    'name': 'Selected Objects',
                    'description': 'Currently selected objects in the scene',
                    'mimeType': 'application/json'
                },
                {
                    'uri': 'blender://scene/preview',
                    'name': 'Scene Preview',
                    'description': 'Current viewport preview image',
                    'mimeType': 'image/png'
                }
            ]
        }
    
    async def list_resource_templates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available resource templates"""
        return {
            'templates': [
                {
                    'uriTemplate': 'blender://object/{objectName}',
                    'name': 'Object Data',
                    'description': 'Detailed information about a specific object',
                    'mimeType': 'application/json',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'objectName': {
                                'type': 'string',
                                'description': 'Name of the object to retrieve'
                            }
                        },
                        'required': ['objectName']
                    }
                }
            ]
        }
    
    async def read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a resource by URI"""
        uri = params.get('uri')
        if not uri:
            raise ValueError("Resource URI is required")
        
        # Handle different resource types
        if uri == 'blender://scene/context':
            context_result = self.resolvers.resolve_scene_context(None, None)
            return {'content': json.dumps(context_result, indent=2)}
            
        elif uri == 'blender://scene/selected':
            selected_result = self.resolvers.resolve_selected_objects(None, None)
            return {'content': json.dumps(selected_result, indent=2)}
            
        elif uri == 'blender://scene/preview':
            preview_result = self.resolvers.resolve_capture_preview(None, None)
            if preview_result.get('success'):
                preview_url = preview_result.get('additional_data', {}).get('preview', {}).get('imageUrl')
                return {
                    'content': preview_url,
                    'isReference': True
                }
            else:
                raise ValueError("Failed to capture preview")
                
        elif uri.startswith('blender://object/'):
            object_name = uri.split('/')[-1]
            # Get object information
            context = self.context_manager.get_complete_context()
            for obj in context.get('all_objects', []):
                if obj.get('name') == object_name:
                    return {'content': json.dumps(obj, indent=2)}
            
            raise ValueError(f"Object not found: {object_name}")
            
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
    
    async def list_prompts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available prompt templates"""
        return {
            'prompts': [
                {
                    'name': 'createObject',
                    'description': 'Create a new object in the scene',
                    'promptTemplate': 'Create a {objectType} at position {x}, {y}, {z} with {properties}.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'objectType': {
                                'type': 'string',
                                'description': 'Type of object to create (cube, sphere, etc.)'
                            },
                            'x': {
                                'type': 'number',
                                'description': 'X coordinate'
                            },
                            'y': {
                                'type': 'number',
                                'description': 'Y coordinate'
                            },
                            'z': {
                                'type': 'number',
                                'description': 'Z coordinate'
                            },
                            'properties': {
                                'type': 'string',
                                'description': 'Additional properties to apply'
                            }
                        },
                        'required': ['objectType']
                    }
                },
                {
                    'name': 'modifyObject',
                    'description': 'Modify an existing object',
                    'promptTemplate': 'Modify the {objectName} by changing its {property} to {value}.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'objectName': {
                                'type': 'string',
                                'description': 'Name of the object to modify'
                            },
                            'property': {
                                'type': 'string',
                                'description': 'Property to modify'
                            },
                            'value': {
                                'type': 'string',
                                'description': 'New value for the property'
                            }
                        },
                        'required': ['objectName', 'property', 'value']
                    }
                }
            ]
        }
    
    async def get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific prompt template"""
        prompt_name = params.get('name')
        
        if not prompt_name:
            raise ValueError("Prompt name is required")
            
        # Map of available prompts
        prompts = {
            'createObject': {
                'name': 'createObject',
                'description': 'Create a new object in the scene',
                'promptTemplate': 'Create a {objectType} at position {x}, {y}, {z} with {properties}.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'objectType': {
                            'type': 'string',
                            'description': 'Type of object to create (cube, sphere, etc.)'
                        },
                        'x': {
                            'type': 'number',
                            'description': 'X coordinate'
                        },
                        'y': {
                            'type': 'number',
                            'description': 'Y coordinate'
                        },
                        'z': {
                            'type': 'number',
                            'description': 'Z coordinate'
                        },
                        'properties': {
                            'type': 'string',
                            'description': 'Additional properties to apply'
                        }
                    },
                    'required': ['objectType']
                }
            },
            'modifyObject': {
                'name': 'modifyObject',
                'description': 'Modify an existing object',
                'promptTemplate': 'Modify the {objectName} by changing its {property} to {value}.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'objectName': {
                            'type': 'string',
                            'description': 'Name of the object to modify'
                        },
                        'property': {
                            'type': 'string',
                            'description': 'Property to modify'
                        },
                        'value': {
                            'type': 'string',
                            'description': 'New value for the property'
                        }
                    },
                    'required': ['objectName', 'property', 'value']
                }
            }
        }
        
        if prompt_name not in prompts:
            raise ValueError(f"Unknown prompt: {prompt_name}")
            
        return prompts[prompt_name]
    
    async def complete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Autocomplete functionality for command assistance
        Not fully implemented in this version
        """
        prefix = params.get('prefix', '')
        context = params.get('context', {})
        
        # Simple example completion implementation
        # In a real implementation, this would use more sophisticated logic
        completions = []
        
        # Simple completions based on common Blender operations
        common_operations = [
            "create a cube",
            "create a sphere",
            "create a cylinder",
            "select all objects",
            "delete selected objects",
            "move object to",
            "rotate object",
            "scale object",
            "add material",
            "render scene",
            "set camera view"
        ]
        
        # Filter completions based on prefix
        for operation in common_operations:
            if operation.startswith(prefix.lower()):
                completions.append({
                    'text': operation,
                    'description': f"Command to {operation}"
                })
        
        return {
            'completions': completions[:5]  # Return top 5 matches
        }
    
    async def shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Shutdown the server"""
        # Schedule server shutdown
        asyncio.create_task(self.stop())
        
        return {
            'success': True,
            'message': 'Server shutdown initiated'
        }
    
    async def get_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get the current Blender context"""
        # This is a convenience method that wraps the standard context query
        result = self.resolvers.resolve_scene_context(None, None)
        return result
    
    # Tool implementation methods
    
    async def _execute_natural_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a natural language command"""
        command = params.get('command')
        options = params.get('options', {})
        
        if not command:
            raise ValueError("Command is required")
            
        result = self.resolvers.resolve_execute_natural_command(None, None, command, options)
        return result
    
    async def _execute_raw_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute raw Python code"""
        python_code = params.get('pythonCode')
        metadata = params.get('metadata')
        
        if not python_code:
            raise ValueError("Python code is required")
            
        # Convert metadata to string if it's an object
        if isinstance(metadata, dict):
            metadata = json.dumps(metadata)
            
        result = self.resolvers.resolve_execute_raw_command(None, None, python_code, metadata)
        return result
    
    async def _capture_preview(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Capture a preview image"""
        width = params.get('width', 512)
        height = params.get('height', 512)
        view = params.get('view', 'current')
        
        result = self.resolvers.resolve_capture_preview(None, None, width, height, view)
        return result
    
    async def _iterate_on_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Iterate on a model with feedback"""
        model_id = params.get('modelId')
        feedback = params.get('feedback')
        render_options = params.get('renderOptions', {})
        
        if not model_id:
            raise ValueError("Model ID is required")
        if not feedback:
            raise ValueError("Feedback is required")
            
        result = self.resolvers.resolve_iterate_on_model(
            None, None, model_id, feedback, render_options
        )
        return result

# Helper function to create and start the server
async def create_and_start_server(host='localhost', port=3000):
    """Create and start an MCP server instance"""
    server = MCPStandardServer(host, port)
    await server.start()
    return server

# Main entry point for running the server directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        server = await create_and_start_server()
        try:
            # Keep the server running until interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        finally:
            await server.stop()
    
    asyncio.run(main())