"""
MCP Server Manager
Utility module to start and manage the standard MCP server from within Blender
"""

import asyncio
import logging
import os
import threading
import time
from typing import Optional, Dict, Any

# Import the standard MCP server implementation
from .mcp_standard_server import MCPStandardServer, create_and_start_server

logger = logging.getLogger('blender_graphql_mcp.tools.mcp_server_manager')

class MCPServerManager:
    """
    Manager for the MCP server that allows easy starting/stopping
    and provides status information
    """
    
    _instance = None  # Singleton instance
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern"""
        if cls._instance is None:
            cls._instance = super(MCPServerManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the server manager"""
        if self._initialized:
            return
            
        self._initialized = True
        self.server = None
        self.server_task = None
        self.server_thread = None
        self.event_loop = None
        self.running = False
        self.port = 3000  # Default port
        self.host = 'localhost'  # Default host
    
    def start_server(self, port: int = 3000, host: str = 'localhost') -> bool:
        """
        Start the MCP server in a background thread
        
        Args:
            port: Port to run the server on
            host: Host to bind the server to
            
        Returns:
            bool: True if server started successfully, False otherwise
        """
        if self.running:
            logger.warning("Server is already running")
            return True
        
        self.port = port
        self.host = host
        
        # Start a new thread for the asyncio event loop
        self.server_thread = threading.Thread(
            target=self._run_server_in_thread,
            args=(host, port),
            daemon=True
        )
        self.server_thread.start()
        
        # Wait for server to start
        retry_count = 0
        while not self.running and retry_count < 10:
            time.sleep(0.5)
            retry_count += 1
        
        if self.running:
            logger.info(f"MCP server started on {host}:{port}")
            return True
        else:
            logger.error("Failed to start MCP server")
            return False
    
    def _run_server_in_thread(self, host: str, port: int):
        """
        Run the server in a background thread
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        try:
            # Create a new event loop for this thread
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
            
            # Start the server
            self.server_task = self.event_loop.create_task(self._start_server(host, port))
            
            # Run the event loop
            self.event_loop.run_forever()
        except Exception as e:
            logger.error(f"Error in server thread: {str(e)}")
            self.running = False
        finally:
            if self.event_loop:
                self.event_loop.close()
    
    async def _start_server(self, host: str, port: int):
        """
        Start the MCP server in the asyncio event loop
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        try:
            self.server = MCPStandardServer(host, port)
            await self.server.start()
            self.running = True
        except Exception as e:
            logger.error(f"Failed to start server: {str(e)}")
            self.running = False
            raise
    
    def stop_server(self) -> bool:
        """
        Stop the MCP server
        
        Returns:
            bool: True if server stopped successfully, False otherwise
        """
        if not self.running:
            logger.warning("Server is not running")
            return True
        
        try:
            # Stop the server by stopping the event loop
            if self.event_loop:
                self.event_loop.call_soon_threadsafe(self._stop_server_in_loop)
                
                # Wait for server to stop
                retry_count = 0
                while self.running and retry_count < 10:
                    time.sleep(0.5)
                    retry_count += 1
                
                if not self.running:
                    logger.info("MCP server stopped")
                    return True
                else:
                    logger.error("Failed to stop MCP server")
                    return False
        except Exception as e:
            logger.error(f"Error stopping server: {str(e)}")
            return False
    
    def _stop_server_in_loop(self):
        """Stop the server in the asyncio event loop"""
        async def _stop():
            try:
                if self.server:
                    await self.server.stop()
            finally:
                self.running = False
                self.event_loop.stop()
        
        asyncio.create_task(_stop())
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the MCP server
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            'running': self.running,
            'host': self.host,
            'port': self.port,
            'url': f"http://{self.host}:{self.port}" if self.running else None,
            'initialized': self.server.initialized if self.server else False
        }

# Get the singleton instance
def get_mcp_server_manager() -> MCPServerManager:
    """
    Get the MCP Server Manager singleton instance
    
    Returns:
        MCPServerManager: The server manager instance
    """
    return MCPServerManager()

# Utility functions for Blender operators

def start_mcp_server(port: int = 3000, host: str = 'localhost') -> bool:
    """
    Start the MCP server with the given parameters
    Convenience function for Blender operators
    
    Args:
        port: Port to run the server on
        host: Host to bind the server to
        
    Returns:
        bool: True if server started successfully, False otherwise
    """
    manager = get_mcp_server_manager()
    return manager.start_server(port, host)

def stop_mcp_server() -> bool:
    """
    Stop the MCP server
    Convenience function for Blender operators
    
    Returns:
        bool: True if server stopped successfully, False otherwise
    """
    manager = get_mcp_server_manager()
    return manager.stop_server()

def get_mcp_server_status() -> Dict[str, Any]:
    """
    Get the current MCP server status
    Convenience function for Blender operators
    
    Returns:
        Dict[str, Any]: Status information
    """
    manager = get_mcp_server_manager()
    return manager.get_status()