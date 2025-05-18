"""
MCP Standard Integration
Integrates the Standard MCP server with the Blender GraphQL MCP addon
"""

import logging
import os
import sys
from typing import Dict, Any, List, Optional

# Import the required modules
from .mcp_server_manager import get_mcp_server_manager

logger = logging.getLogger('blender_graphql_mcp.tools.mcp_standard_integration')

def register_mcp_operators():
    """Register MCP server operators"""
    try:
        from Blender_GraphQL_MCP.operators.mcp_server_operators import register as register_operators
        register_operators()
        logger.info("MCP server operators registered")
    except ImportError as e:
        logger.error(f"Error registering MCP server operators: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error registering MCP server operators: {str(e)}")
        return False
    
    return True

def register_mcp_ui():
    """Register MCP server UI components"""
    try:
        from Blender_GraphQL_MCP.ui.mcp_server_panel import register as register_ui
        register_ui()
        logger.info("MCP server UI registered")
    except ImportError as e:
        logger.error(f"Error registering MCP server UI: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error registering MCP server UI: {str(e)}")
        return False
    
    return True

def start_mcp_server_if_needed(auto_start: bool = False, port: int = 3000):
    """
    Start the MCP server if auto-start is enabled
    
    Args:
        auto_start: Whether to automatically start the server
        port: Port to start the server on
    
    Returns:
        bool: True if server started successfully or was already running, False otherwise
    """
    if not auto_start:
        logger.info("Auto-start disabled, not starting MCP server")
        return True
    
    try:
        manager = get_mcp_server_manager()
        
        # Check if server is already running
        status = manager.get_status()
        if status.get('running', False):
            logger.info(f"MCP server already running on port {status.get('port', 'unknown')}")
            return True
        
        # Start the server
        success = manager.start_server(port=port)
        if success:
            logger.info(f"MCP server started on port {port}")
            return True
        else:
            logger.error("Failed to start MCP server")
            return False
    
    except Exception as e:
        logger.error(f"Error starting MCP server: {str(e)}")
        return False

def stop_mcp_server_if_running():
    """
    Stop the MCP server if it's running
    
    Returns:
        bool: True if server stopped successfully or wasn't running, False otherwise
    """
    try:
        manager = get_mcp_server_manager()
        
        # Check if server is running
        status = manager.get_status()
        if not status.get('running', False):
            logger.info("MCP server not running, nothing to stop")
            return True
        
        # Stop the server
        success = manager.stop_server()
        if success:
            logger.info("MCP server stopped")
            return True
        else:
            logger.error("Failed to stop MCP server")
            return False
    
    except Exception as e:
        logger.error(f"Error stopping MCP server: {str(e)}")
        return False

def register_mcp_standard():
    """
    Register the MCP standard integration components
    
    Returns:
        bool: True if registration was successful, False otherwise
    """
    success = True
    
    # Register operators
    if not register_mcp_operators():
        success = False
    
    # Register UI
    if not register_mcp_ui():
        success = False
    
    return success

def unregister_mcp_standard():
    """
    Unregister the MCP standard integration components
    
    Returns:
        bool: True if unregistration was successful, False otherwise
    """
    success = True
    
    # First stop the server if running
    if not stop_mcp_server_if_running():
        success = False
    
    # Unregister UI
    try:
        from Blender_GraphQL_MCP.ui.mcp_server_panel import unregister as unregister_ui
        unregister_ui()
        logger.info("MCP server UI unregistered")
    except ImportError as e:
        logger.error(f"Error unregistering MCP server UI: {str(e)}")
        success = False
    except Exception as e:
        logger.error(f"Unexpected error unregistering MCP server UI: {str(e)}")
        success = False
    
    # Unregister operators
    try:
        from Blender_GraphQL_MCP.operators.mcp_server_operators import unregister as unregister_operators
        unregister_operators()
        logger.info("MCP server operators unregistered")
    except ImportError as e:
        logger.error(f"Error unregistering MCP server operators: {str(e)}")
        success = False
    except Exception as e:
        logger.error(f"Unexpected error unregistering MCP server operators: {str(e)}")
        success = False
    
    return success

# Main registration function to be called from the addon's register function
def register():
    """
    Register the MCP standard integration
    
    Returns:
        bool: True if registration was successful, False otherwise
    """
    logger.info("Registering MCP standard integration")
    return register_mcp_standard()

# Main unregistration function to be called from the addon's unregister function
def unregister():
    """
    Unregister the MCP standard integration
    
    Returns:
        bool: True if unregistration was successful, False otherwise
    """
    logger.info("Unregistering MCP standard integration")
    return unregister_mcp_standard()