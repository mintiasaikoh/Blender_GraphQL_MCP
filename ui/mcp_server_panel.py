"""
MCP Server Panel
UI panel for the standard-compliant MCP server
"""

import bpy
from bpy.types import Panel

class VIEW3D_PT_mcp_standard_server(Panel):
    """Panel for the standard MCP server"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MCP'
    bl_label = "MCP Standard Server"
    bl_idname = "VIEW3D_PT_mcp_standard_server"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Server status and controls
        if getattr(scene, 'mcp_server_running', False):
            # Server is running - show status and stop button
            box = layout.box()
            row = box.row()
            row.label(text="Server Running", icon='CHECKMARK')
            
            row = box.row()
            row.label(text=f"Host: {scene.mcp_server_host}")
            
            row = box.row()
            row.label(text=f"Port: {scene.mcp_server_port}")
            
            row = box.row()
            row.operator("mcp.server_status", text="Check Status", icon='INFO')
            row.operator("mcp.open_docs", text="Open Docs", icon='URL')
            
            row = box.row()
            row.operator("mcp.stop_standard_server", text="Stop Server", icon='PAUSE')
            
        else:
            # Server is not running - show start controls
            box = layout.box()
            row = box.row()
            row.label(text="Server Not Running", icon='X')
            
            row = box.row()
            row.label(text="Server Configuration:")
            
            row = box.row()
            row.prop(scene, "mcp_server_host", text="Host")
            
            row = box.row()
            row.prop(scene, "mcp_server_port", text="Port")
            
            row = box.row()
            props = row.operator("mcp.start_standard_server", text="Start Server", icon='PLAY')
            props.host = scene.mcp_server_host
            props.port = scene.mcp_server_port

        # Information about the MCP standard
        box = layout.box()
        col = box.column()
        col.label(text="MCP Standard Information:")
        col.label(text="• JSON-RPC 2.0 protocol")
        col.label(text="• Tools API for LLM integration")
        col.label(text="• Resources for context sharing")
        col.label(text="• Prompt templates")

def register():
    bpy.utils.register_class(VIEW3D_PT_mcp_standard_server)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_mcp_standard_server)