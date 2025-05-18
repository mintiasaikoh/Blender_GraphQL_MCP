"""
MCP Server Operators
Blender operators for managing the MCP server from the UI
"""

import bpy
import logging
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty, BoolProperty

from tools.mcp_server_manager import start_mcp_server, stop_mcp_server, get_mcp_server_status

logger = logging.getLogger('blender_graphql_mcp.operators.mcp_server_operators')

class MCP_OT_StartServer(Operator):
    """Start the Model Context Protocol server"""
    bl_idname = "mcp.start_standard_server"
    bl_label = "Start MCP Server"
    bl_description = "Start the Model Context Protocol server for AI integration"
    bl_options = {'REGISTER', 'UNDO'}
    
    port: IntProperty(
        name="Port",
        description="Port to run the server on",
        default=3000,
        min=1024,
        max=65535
    )
    
    host: StringProperty(
        name="Host",
        description="Host to bind the server to",
        default="localhost"
    )
    
    def execute(self, context):
        try:
            # Store settings in scene properties
            if not hasattr(context.scene, "mcp_server_port"):
                context.scene.mcp_server_port = 3000
            if not hasattr(context.scene, "mcp_server_host"):
                context.scene.mcp_server_host = "localhost"
            if not hasattr(context.scene, "mcp_server_running"):
                context.scene.mcp_server_running = False
                
            # Update scene properties with current values
            context.scene.mcp_server_port = self.port
            context.scene.mcp_server_host = self.host
            
            # Start the server
            success = start_mcp_server(self.port, self.host)
            
            if success:
                # Update running state
                context.scene.mcp_server_running = True
                self.report({'INFO'}, f"MCP Server started on {self.host}:{self.port}")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to start MCP Server")
                return {'CANCELLED'}
        except Exception as e:
            logger.error(f"Error starting MCP server: {str(e)}")
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}

class MCP_OT_StopServer(Operator):
    """Stop the Model Context Protocol server"""
    bl_idname = "mcp.stop_standard_server"
    bl_label = "Stop MCP Server"
    bl_description = "Stop the Model Context Protocol server"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            # Stop the server
            success = stop_mcp_server()
            
            if success:
                # Update scene property
                if hasattr(context.scene, "mcp_server_running"):
                    context.scene.mcp_server_running = False
                
                self.report({'INFO'}, "MCP Server stopped")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to stop MCP Server")
                return {'CANCELLED'}
        except Exception as e:
            logger.error(f"Error stopping MCP server: {str(e)}")
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}

class MCP_OT_ServerStatus(Operator):
    """Show the status of the MCP server"""
    bl_idname = "mcp.server_status"
    bl_label = "MCP Server Status"
    bl_description = "Show the status of the Model Context Protocol server"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def execute(self, context):
        try:
            # Get server status
            status = get_mcp_server_status()
            
            # Show status in a popup
            message = (
                f"MCP Server Status:\n"
                f"Running: {'Yes' if status['running'] else 'No'}\n"
                f"URL: {status['url'] if status['running'] else 'N/A'}\n"
                f"Initialized: {'Yes' if status['initialized'] else 'No'}"
            )
            
            def draw(self, context):
                layout = self.layout
                for line in message.split("\n"):
                    layout.label(text=line)
            
            bpy.context.window_manager.popup_menu(draw, title="MCP Server Status", icon='INFO')
            
            return {'FINISHED'}
        except Exception as e:
            logger.error(f"Error getting MCP server status: {str(e)}")
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}

class MCP_OT_OpenDocs(Operator):
    """Open the MCP documentation in a web browser"""
    bl_idname = "mcp.open_docs"
    bl_label = "Open MCP Docs"
    bl_description = "Open the Model Context Protocol documentation in a web browser"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def execute(self, context):
        try:
            # Get server status to check if it's running
            status = get_mcp_server_status()
            
            if status['running']:
                # Open the MCP docs at the server URL
                url = f"{status['url']}/docs"
                bpy.ops.wm.url_open(url=url)
                self.report({'INFO'}, f"Opening MCP documentation at {url}")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "MCP Server is not running. Start the server first.")
                return {'CANCELLED'}
        except Exception as e:
            logger.error(f"Error opening MCP docs: {str(e)}")
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}

# Registration

def register():
    bpy.utils.register_class(MCP_OT_StartServer)
    bpy.utils.register_class(MCP_OT_StopServer)
    bpy.utils.register_class(MCP_OT_ServerStatus)
    bpy.utils.register_class(MCP_OT_OpenDocs)
    
    # Register properties on the Scene type
    bpy.types.Scene.mcp_server_port = bpy.props.IntProperty(
        name="MCP Server Port",
        description="Port for the MCP server",
        default=3000,
        min=1024,
        max=65535
    )
    
    bpy.types.Scene.mcp_server_host = bpy.props.StringProperty(
        name="MCP Server Host",
        description="Host for the MCP server",
        default="localhost"
    )
    
    bpy.types.Scene.mcp_server_running = bpy.props.BoolProperty(
        name="MCP Server Running",
        description="Whether the MCP server is currently running",
        default=False
    )

def unregister():
    bpy.utils.unregister_class(MCP_OT_StartServer)
    bpy.utils.unregister_class(MCP_OT_StopServer)
    bpy.utils.unregister_class(MCP_OT_ServerStatus)
    bpy.utils.unregister_class(MCP_OT_OpenDocs)
    
    # Remove properties
    del bpy.types.Scene.mcp_server_port
    del bpy.types.Scene.mcp_server_host
    del bpy.types.Scene.mcp_server_running