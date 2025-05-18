"""
REST API subsystem for UnifiedServer.
Provides REST API functionality with command registry integration.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union, Type

# Import FastAPI types
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import base API class
from ..base import APISubsystem, register_api

# Import utilities
from ...utils.logging import get_logger

# Try to import Pydantic v2 compatibility
try:
    from pydantic import create_model
    PYDANTIC_V2 = True
except ImportError:
    # Fallback for Pydantic v1
    from pydantic import create_model as _create_model
    PYDANTIC_V2 = False
    
    def create_model(*args, **kwargs):
        """Wrapper for Pydantic v1 create_model."""
        return _create_model(*args, **kwargs)


@register_api("rest")
class RestAPI(APISubsystem):
    """
    REST API implementation for UnifiedServer.
    Provides REST API routes for commands and Blender operations.
    """
    
    def __init__(self, server):
        """
        Initialize the REST API subsystem.
        
        Args:
            server: The UnifiedServer instance
        """
        super().__init__(server)
        self.logger = get_logger("rest_api")
        
        # API router
        self.router = None
        
        # Command registry
        self.command_registry = server.command_registry
        
        # Model cache
        self.model_cache = {}
    
    def setup(self) -> None:
        """
        Set up the REST API routes.
        Creates routes for commands and Blender operations.
        """
        # Create API router
        self.router = APIRouter(
            prefix=self.config.api_prefix or "/api/v1",
            tags=["api"]
        )
        
        # Set up routes
        self._setup_info_routes()
        self._setup_command_routes()
        self._setup_object_routes()
        self._setup_scene_routes()
        self._setup_addon_routes()
        
        # Include router in FastAPI app
        self.app.include_router(self.router)
        
        self.logger.info(f"REST API set up with prefix: {self.config.api_prefix or '/api/v1'}")
    
    def cleanup(self) -> None:
        """Clean up resources when server is stopping."""
        self.logger.debug("Cleaning up REST API")
        
        # Reset resources
        self.router = None
        self.model_cache = {}
    
    def check_dependencies(self) -> bool:
        """
        Check if required dependencies are available.
        
        Returns:
            True if all dependencies are available, False otherwise
        """
        return True  # FastAPI is already checked by the server
    
    def get_routes(self) -> List[Dict[str, Any]]:
        """
        Get information about available routes.
        
        Returns:
            List of route information dictionaries
        """
        if not self.router:
            return []
        
        routes = []
        for route in self.router.routes:
            route_info = {
                "path": route.path,
                "methods": route.methods,
                "name": route.name,
                "endpoint": route.endpoint.__name__ if hasattr(route.endpoint, "__name__") else str(route.endpoint)
            }
            routes.append(route_info)
        
        return routes
    
    def _setup_info_routes(self) -> None:
        """Set up informational routes."""
        @self.router.get("/info")
        async def get_info():
            """Get API information."""
            return {
                "name": self.config.api_title,
                "version": self.config.api_version,
                "description": self.config.api_description,
                "server_status": "running"
            }
        
        @self.router.get("/status")
        async def get_status():
            """Get server status."""
            return self.server.status()
    
    def _setup_command_routes(self) -> None:
        """Set up command-related routes."""
        if not self.command_registry:
            self.logger.warning("Command registry not available, skipping command routes")
            return
        
        # Define Pydantic models for requests and responses
        class CommandRequest(BaseModel):
            params: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")
        
        class CommandResponse(BaseModel):
            success: bool = Field(..., description="Command success status")
            result: Optional[Dict[str, Any]] = Field(None, description="Command result")
            error: Optional[str] = Field(None, description="Error message if command failed")
        
        class BatchRequest(BaseModel):
            commands: List[Dict[str, Any]] = Field(..., description="List of commands to execute")
        
        class BatchResponse(BaseModel):
            success: bool = Field(..., description="Batch success status")
            results: List[Dict[str, Any]] = Field(..., description="Results for each command")
            successful_commands: int = Field(..., description="Number of successful commands")
            total_commands: int = Field(..., description="Total number of commands")
        
        # List available commands
        @self.router.get("/commands")
        async def list_commands(category: Optional[str] = None):
            """
            List available commands.
            
            Args:
                category: Optional category to filter by
                
            Returns:
                List of command information
            """
            try:
                commands = self.command_registry.list_commands(category)
                return {"commands": commands}
            except Exception as e:
                self.logger.error(f"Error listing commands: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        # Get command information
        @self.router.get("/commands/{command_name}")
        async def get_command_info(command_name: str):
            """
            Get information about a specific command.
            
            Args:
                command_name: Command name
                
            Returns:
                Command information
            """
            command = self.command_registry.get_command(command_name)
            if not command:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Command '{command_name}' not found"
                )
            
            # Return command information without the function
            return {
                "name": command["name"],
                "description": command["description"],
                "category": command["category"],
                "parameters": command["parameters"],
                "returns": command["returns"],
                "examples": command["examples"],
                "is_dangerous": command["is_dangerous"]
            }
        
        # Execute command
        @self.router.post("/commands/{command_name}")
        async def execute_command(command_name: str, request: CommandRequest):
            """
            Execute a command with the given parameters.
            
            Args:
                command_name: Command name
                request: Command request with parameters
                
            Returns:
                Command result
            """
            try:
                result = self.command_registry.execute_command(command_name, request.params)
                return {"success": True, "result": result}
            except Exception as e:
                self.logger.error(f"Error executing command '{command_name}': {e}")
                return {"success": False, "error": str(e)}
        
        # Execute batch of commands
        @self.router.post("/batch")
        async def execute_batch(request: BatchRequest):
            """
            Execute a batch of commands.
            
            Args:
                request: Batch request with commands
                
            Returns:
                Batch result
            """
            try:
                # Format commands for batch execution
                commands = [
                    {
                        "command": cmd.get("command"),
                        "params": cmd.get("params", {})
                    }
                    for cmd in request.commands
                ]
                
                # Execute batch
                results = self.command_registry.execute_batch(commands)
                
                # Count successful commands
                successful_commands = sum(1 for result in results if result.get("success", False))
                
                return {
                    "success": True,
                    "results": results,
                    "successful_commands": successful_commands,
                    "total_commands": len(commands)
                }
            except Exception as e:
                self.logger.error(f"Error executing batch: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "results": [],
                    "successful_commands": 0,
                    "total_commands": len(request.commands)
                }
    
    def _setup_object_routes(self) -> None:
        """Set up object-related routes."""
        # Define Pydantic models
        class ObjectInfo(BaseModel):
            name: str = Field(..., description="Object name")
            type: str = Field(..., description="Object type")
            location: Optional[Dict[str, float]] = Field(None, description="Object location")
            rotation: Optional[Dict[str, float]] = Field(None, description="Object rotation")
            scale: Optional[Dict[str, float]] = Field(None, description="Object scale")
            visible: Optional[bool] = Field(None, description="Object visibility")
        
        class CreateObjectRequest(BaseModel):
            type: str = Field(..., description="Object type (e.g., 'MESH', 'CURVE', 'EMPTY')")
            name: Optional[str] = Field(None, description="Object name")
            primitive: Optional[str] = Field(None, description="Primitive type for mesh objects (e.g., 'CUBE', 'SPHERE')")
            location: Optional[Dict[str, float]] = Field(None, description="Object location")
            rotation: Optional[Dict[str, float]] = Field(None, description="Object rotation")
            scale: Optional[Dict[str, float]] = Field(None, description="Object scale")
        
        # Get all objects
        @self.router.get("/objects")
        async def get_objects():
            """
            Get all objects in the scene.
            
            Returns:
                List of objects
            """
            if not self.command_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Command registry not available"
                )
            
            try:
                result = self.command_registry.execute_command("get_all_objects", {})
                return result
            except Exception as e:
                self.logger.error(f"Error getting objects: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        # Get object by name
        @self.router.get("/objects/{object_name}")
        async def get_object(object_name: str):
            """
            Get object by name.
            
            Args:
                object_name: Object name
                
            Returns:
                Object information
            """
            if not self.command_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Command registry not available"
                )
            
            try:
                result = self.command_registry.execute_command("get_object", {"name": object_name})
                if not result.get("success", False):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Object '{object_name}' not found"
                    )
                
                return result.get("object", {})
            except Exception as e:
                self.logger.error(f"Error getting object '{object_name}': {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        # Create object
        @self.router.post("/objects")
        async def create_object(request: CreateObjectRequest):
            """
            Create a new object.
            
            Args:
                request: Object creation request
                
            Returns:
                Created object information
            """
            if not self.command_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Command registry not available"
                )
            
            try:
                params = request.dict(exclude_none=True)
                result = self.command_registry.execute_command("create_object", params)
                return result
            except Exception as e:
                self.logger.error(f"Error creating object: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        # Delete object
        @self.router.delete("/objects/{object_name}")
        async def delete_object(object_name: str):
            """
            Delete an object.
            
            Args:
                object_name: Object name
                
            Returns:
                Deletion result
            """
            if not self.command_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Command registry not available"
                )
            
            try:
                result = self.command_registry.execute_command("delete_object", {"name": object_name})
                return result
            except Exception as e:
                self.logger.error(f"Error deleting object '{object_name}': {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
    
    def _setup_scene_routes(self) -> None:
        """Set up scene-related routes."""
        # Get scene info
        @self.router.get("/scene")
        async def get_scene_info():
            """
            Get information about the current scene.
            
            Returns:
                Scene information
            """
            if not self.command_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Command registry not available"
                )
            
            try:
                result = self.command_registry.execute_command("get_scene_info", {})
                return result
            except Exception as e:
                self.logger.error(f"Error getting scene info: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
    
    def _setup_addon_routes(self) -> None:
        """Set up addon-related routes."""
        # Define Pydantic models
        class AddonInfo(BaseModel):
            name: str = Field(..., description="Addon name")
            is_enabled: bool = Field(..., description="Whether the addon is enabled")
            description: Optional[str] = Field(None, description="Addon description")
            version: Optional[str] = Field(None, description="Addon version")
            author: Optional[str] = Field(None, description="Addon author")
        
        class InstallAddonRequest(BaseModel):
            file_path: Optional[str] = Field(None, description="Path to addon zip file")
            url: Optional[str] = Field(None, description="URL to addon zip file")
        
        # Get all addons
        @self.router.get("/addons")
        async def get_all_addons():
            """
            Get all addons.
            
            Returns:
                List of addons
            """
            if not self.command_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Command registry not available"
                )
            
            try:
                result = self.command_registry.execute_command("get_all_addons", {})
                return result
            except Exception as e:
                self.logger.error(f"Error getting addons: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        # Get addon info
        @self.router.get("/addons/{addon_name}")
        async def get_addon_info(addon_name: str):
            """
            Get addon information.
            
            Args:
                addon_name: Addon name
                
            Returns:
                Addon information
            """
            if not self.command_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Command registry not available"
                )
            
            try:
                result = self.command_registry.execute_command("get_addon_info", {"addon_name": addon_name})
                return result
            except Exception as e:
                self.logger.error(f"Error getting addon info for '{addon_name}': {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        # Enable addon
        @self.router.post("/addons/{addon_name}/enable")
        async def enable_addon(addon_name: str):
            """
            Enable an addon.
            
            Args:
                addon_name: Addon name
                
            Returns:
                Addon enable result
            """
            if not self.command_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Command registry not available"
                )
            
            try:
                result = self.command_registry.execute_command("enable_addon", {"addon_name": addon_name})
                return result
            except Exception as e:
                self.logger.error(f"Error enabling addon '{addon_name}': {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        # Disable addon
        @self.router.post("/addons/{addon_name}/disable")
        async def disable_addon(addon_name: str):
            """
            Disable an addon.
            
            Args:
                addon_name: Addon name
                
            Returns:
                Addon disable result
            """
            if not self.command_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Command registry not available"
                )
            
            try:
                result = self.command_registry.execute_command("disable_addon", {"addon_name": addon_name})
                return result
            except Exception as e:
                self.logger.error(f"Error disabling addon '{addon_name}': {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        # Install addon
        @self.router.post("/addons/install")
        async def install_addon(request: InstallAddonRequest):
            """
            Install an addon.
            
            Args:
                request: Addon installation request
                
            Returns:
                Addon installation result
            """
            if not self.command_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Command registry not available"
                )
            
            try:
                params = request.dict(exclude_none=True)
                
                if "file_path" in params:
                    result = self.command_registry.execute_command("install_addon", {"file_path": params["file_path"]})
                elif "url" in params:
                    result = self.command_registry.execute_command("install_addon_from_url", {"url": params["url"]})
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Either file_path or url must be provided"
                    )
                
                return result
            except Exception as e:
                self.logger.error(f"Error installing addon: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )