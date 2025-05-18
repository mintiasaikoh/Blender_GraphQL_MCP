"""
Unified server implementation for Blender GraphQL MCP.
Provides a modular server that supports both GraphQL and REST APIs.
"""

import os
import sys
import time
import threading
import importlib
from typing import Dict, List, Optional, Any, Type, Set, Tuple, Union
from pathlib import Path

# Core imports
from .config import ServerConfig

# Utils imports
from ..utils.logging import setup_logging, get_logger
from ..utils.threading import StoppableThread, execute_in_main_thread, start_main_thread_processing

# API imports
from ..api.base import APISubsystem, APIRegistry

# Optional docs imports
try:
    from ..docs.docs_integrator import DocumentationIntegrator
    DOCS_AVAILABLE = True
except ImportError:
    DOCS_AVAILABLE = False

# Try to import FastAPI
try:
    from fastapi import FastAPI, Request, Response, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, HTMLResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


class UnifiedServer:
    """
    Unified server implementation supporting both GraphQL and REST APIs.
    """
    
    _instance = None  # Singleton instance
    
    @classmethod
    def get_instance(cls) -> 'UnifiedServer':
        """Get singleton instance of the server."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self, config: Optional[ServerConfig] = None):
        """
        Initialize the server with optional configuration.
        
        Args:
            config: Server configuration. If None, uses default configuration.
        """
        # Check if we're in a valid Blender environment
        self._in_blender = self._check_blender_environment()
        
        # Set configuration
        self.config = config or ServerConfig()
        
        # Set up logging
        self.logger = setup_logging(
            log_level=self.config.log_level,
            log_format=self.config.log_format,
            log_dir=self.config.log_dir,
            log_file=self.config.log_file
        )
        
        # Initialize server components
        self.app = None  # FastAPI application
        self.server = None  # Uvicorn server
        self.server_thread = None  # Server thread
        self.is_running = False  # Server running flag
        self.stop_event = threading.Event()  # Stop event

        # API components
        self.apis: Dict[str, APISubsystem] = {}

        # Command registry
        self.command_registry = None

        # Documentation system
        self.docs_integrator = None
        self.docs_initialized = False

        # Log initialization
        self.logger.info(f"Initialized UnifiedServer with configuration: {self.config.to_dict()}")
    
    def initialize(self) -> bool:
        """
        Initialize the FastAPI application with enabled APIs.

        Returns:
            True if initialization was successful, False otherwise
        """
        # Check dependencies
        if not self._check_dependencies():
            self.logger.error("Failed to initialize server: Dependencies not available")
            return False

        # Create FastAPI app
        self.app = FastAPI(
            title=self.config.api_title,
            description=self.config.api_description,
            version=self.config.api_version,
            docs_url="/docs" if self.config.enable_docs else None
        )

        # Set up CORS if enabled
        if self.config.enable_cors:
            self._setup_cors()

        # Set up error handlers
        self._setup_error_handlers()

        # Set up base routes
        self._setup_base_routes()

        # Initialize and set up API subsystems
        if not self._setup_api_subsystems():
            self.logger.error("Failed to initialize server: API subsystem setup failed")
            return False

        # Initialize command registry if available
        if not self._setup_command_registry():
            self.logger.warning("Command registry initialization failed, some features may be limited")

        # Initialize documentation system if enabled
        if self.config.enable_docs:
            self._setup_documentation()

        self.logger.info("Server initialization complete")
        return True

    def _setup_documentation(self) -> bool:
        """
        Set up the documentation system.

        Returns:
            True if setup was successful, False otherwise
        """
        if not DOCS_AVAILABLE:
            self.logger.warning("Documentation system not available")
            return False

        try:
            # Initialize documentation integrator
            self.docs_integrator = DocumentationIntegrator(self)

            # Initialize documentation components
            success = self.docs_integrator.initialize()

            if success:
                self.docs_initialized = True
                self.logger.info("Documentation system initialized successfully")
            else:
                self.logger.warning("Documentation system initialization failed")

            return success
        except Exception as e:
            self.logger.error(f"Error setting up documentation system: {e}", exc_info=True)
            return False
    
    def start(self) -> bool:
        """
        Start the server in a separate thread.
        
        Returns:
            True if server started successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning("Server is already running")
            return True
        
        # Initialize if not already initialized
        if self.app is None and not self.initialize():
            return False
        
        # Find available port if auto_find_port is enabled
        port = self.config.port
        if self.config.auto_find_port:
            port = self._find_available_port(port)
            if port is None:
                self.logger.error("Failed to find available port")
                return False
        
        # Create server configuration
        server_config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=port,
            log_level="warning",  # Use our own logging
            loop="asyncio",
            workers=self.config.workers
        )
        
        # Create server
        self.server = uvicorn.Server(server_config)
        
        # Reset stop event
        self.stop_event.clear()
        
        # Start main thread processing if in Blender
        if self._in_blender:
            start_main_thread_processing()
            self.logger.info("Started Blender main thread processing")
        
        # Create and start server thread
        self.server_thread = ServerThread(self.server, self.stop_event)
        self.server_thread.start()
        
        # Set running flag
        self.is_running = True
        
        self.logger.info(f"Server started on {self.config.host}:{port}")
        return True
    
    def stop(self, timeout: float = 5.0) -> bool:
        """
        Stop the server gracefully.
        
        Args:
            timeout: Maximum time to wait for server to stop
        
        Returns:
            True if server stopped successfully, False otherwise
        """
        if not self.is_running:
            self.logger.warning("Server is not running")
            return True
        
        # Signal server to stop
        self.logger.info("Stopping server...")
        self.stop_event.set()
        
        # Wait for server thread to terminate
        if self.server_thread and self.server_thread.is_alive():
            self.logger.debug("Waiting for server thread to terminate...")
            self.server_thread.join(timeout)
            
            # If thread is still alive after timeout, it's stuck
            if self.server_thread.is_alive():
                self.logger.warning(f"Server thread did not terminate within {timeout} seconds")
                return False
        
        # Clean up API subsystems
        for api_name, api in self.apis.items():
            try:
                api.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up API subsystem {api_name}: {e}")
        
        # Reset state
        self.is_running = False
        self.server = None
        self.server_thread = None
        
        self.logger.info("Server stopped")
        return True
    
    def restart(self) -> bool:
        """
        Restart the server.
        
        Returns:
            True if server restarted successfully, False otherwise
        """
        self.logger.info("Restarting server...")
        
        # Stop server
        if not self.stop():
            self.logger.error("Failed to stop server for restart")
            return False
        
        # Small delay to ensure clean shutdown
        time.sleep(1)
        
        # Start server
        if not self.start():
            self.logger.error("Failed to start server after restart")
            return False
        
        self.logger.info("Server restarted successfully")
        return True
    
    def status(self) -> Dict[str, Any]:
        """
        Get server status information.
        
        Returns:
            Dictionary with server status information
        """
        status = {
            "running": self.is_running,
            "host": self.config.host,
            "port": self.config.port,
            "version": self.config.api_version,
            "uptime": None,  # Will be set if running
            "apis": list(self.apis.keys()),
            "blender_available": self._in_blender
        }
        
        # Add uptime if server is running
        if self.is_running and hasattr(self.server_thread, "start_time"):
            status["uptime"] = time.time() - self.server_thread.start_time
        
        return status
    
    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies are available.
        
        Returns:
            True if all required dependencies are available, False otherwise
        """
        # Check FastAPI availability
        if not FASTAPI_AVAILABLE:
            self.logger.error("FastAPI and/or Uvicorn not available. Please install them with 'pip install fastapi uvicorn'")
            return False
        
        return True
    
    def _check_blender_environment(self) -> bool:
        """
        Check if running inside Blender environment.
        
        Returns:
            True if running inside Blender, False otherwise
        """
        try:
            import bpy
            return True
        except ImportError:
            return False
    
    def _setup_cors(self) -> None:
        """Set up CORS middleware for the FastAPI application."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_methods=self.config.cors_methods,
            allow_headers=self.config.cors_headers,
            allow_credentials=True
        )
        self.logger.debug(f"CORS middleware set up with origins: {self.config.cors_origins}")
    
    def _setup_error_handlers(self) -> None:
        """Set up error handlers for the FastAPI application."""
        @self.app.exception_handler(Exception)
        async def generic_exception_handler(request: Request, exc: Exception):
            self.logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": str(exc), "type": type(exc).__name__}
            )
    
    def _setup_base_routes(self) -> None:
        """Set up base routes for the FastAPI application."""
        @self.app.get("/", response_class=JSONResponse)
        async def root():
            """Root endpoint returning basic information about the API."""
            return {
                "name": self.config.api_title,
                "version": self.config.api_version,
                "description": self.config.api_description,
                "docs_url": "/docs" if self.config.enable_docs else None,
                "status": "running"
            }
        
        @self.app.get("/status", response_class=JSONResponse)
        async def get_status():
            """Get detailed server status."""
            return self.status()
        
        @self.app.get("/health", response_class=JSONResponse)
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy"}
    
    def _setup_api_subsystems(self) -> bool:
        """
        Set up API subsystems based on configuration.
        
        Returns:
            True if setup was successful, False otherwise
        """
        # Get list of available APIs
        available_apis = APIRegistry.list_apis()
        self.logger.info(f"Available API subsystems: {available_apis}")
        
        # GraphQL API setup
        if self.config.enable_graphql and "graphql" in available_apis:
            graphql_api_class = APIRegistry.get("graphql")
            if graphql_api_class:
                try:
                    # Create and set up GraphQL API
                    graphql_api = graphql_api_class(self)
                    if graphql_api.check_dependencies():
                        graphql_api.setup()
                        self.apis["graphql"] = graphql_api
                        self.logger.info("GraphQL API subsystem set up successfully")
                    else:
                        self.logger.warning("GraphQL API dependencies not available, skipping setup")
                except Exception as e:
                    self.logger.error(f"Error setting up GraphQL API: {e}", exc_info=True)
            else:
                self.logger.warning("GraphQL API class not found")
        elif self.config.enable_graphql:
            self.logger.warning("GraphQL API enabled but not available")
        
        # REST API setup
        if self.config.enable_rest and "rest" in available_apis:
            rest_api_class = APIRegistry.get("rest")
            if rest_api_class:
                try:
                    # Create and set up REST API
                    rest_api = rest_api_class(self)
                    if rest_api.check_dependencies():
                        rest_api.setup()
                        self.apis["rest"] = rest_api
                        self.logger.info("REST API subsystem set up successfully")
                    else:
                        self.logger.warning("REST API dependencies not available, skipping setup")
                except Exception as e:
                    self.logger.error(f"Error setting up REST API: {e}", exc_info=True)
            else:
                self.logger.warning("REST API class not found")
        elif self.config.enable_rest:
            self.logger.warning("REST API enabled but not available")
        
        # Check if at least one API was set up
        if not self.apis:
            self.logger.error("No API subsystems were set up")
            return False
        
        return True
    
    def _setup_command_registry(self) -> bool:
        """
        Set up command registry for the server.
        
        Returns:
            True if setup was successful, False otherwise
        """
        try:
            # Dynamically import command registry
            from ..adapters.command_registry import CommandRegistry
            self.command_registry = CommandRegistry()
            self.logger.info("Command registry set up successfully")
            return True
        except ImportError:
            self.logger.warning("Command registry module not available")
            return False
        except Exception as e:
            self.logger.error(f"Error setting up command registry: {e}", exc_info=True)
            return False
    
    def _find_available_port(self, start_port: int) -> Optional[int]:
        """
        Find an available port starting from the given port.
        
        Args:
            start_port: Starting port number
            
        Returns:
            Available port number or None if no port is available
        """
        import socket
        
        port = start_port
        max_attempts = self.config.max_port_attempts
        attempts = 0
        
        while attempts < max_attempts:
            try:
                # Try to create a socket and bind to the port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((self.config.host, port))
                    return port
            except socket.error:
                # Port is in use, try next port
                self.logger.debug(f"Port {port} is in use, trying next port")
                port += self.config.port_increment
                attempts += 1
        
        # No port available
        self.logger.error(f"No available port found after {max_attempts} attempts")
        return None


class ServerThread(StoppableThread):
    """Thread for running the Uvicorn server."""
    
    def __init__(self, server, stop_event):
        """
        Initialize the server thread.
        
        Args:
            server: Uvicorn server instance
            stop_event: Threading event to signal when server should stop
        """
        super().__init__(name="ServerThread", daemon=True)
        self.server = server
        self.stop_event = stop_event
        self.start_time = None
    
    def run(self):
        """Run the server in a separate thread."""
        self.start_time = time.time()
        
        # Add signal handlers to the server's config to handle the stop event
        self.server.config.callback_notify = lambda: None
        
        # Check stop event in a separate thread
        def check_stop_event():
            while not self.stop_event.is_set():
                time.sleep(0.1)
            self.server.should_exit = True
        
        threading.Thread(target=check_stop_event, daemon=True).start()
        
        # Run the server
        self.server.run()


# Initialize register_api decorator
def register_api(name: str):
    """Import and re-export the register_api decorator."""
    from ..api.base import register_api as _register_api
    return _register_api(name)