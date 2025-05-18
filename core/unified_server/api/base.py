"""
Base API subsystem for Blender GraphQL MCP unified server.
Provides the base class for API implementations.
"""

from typing import Any, Dict, List, Optional, Type
from fastapi import FastAPI


class APISubsystem:
    """
    Base class for API subsystems.
    Provides a common interface for all API implementations.
    """
    
    def __init__(self, server):
        """
        Initialize the API subsystem.
        
        Args:
            server: The UnifiedServer instance
        """
        self.server = server
        self.app = server.app
        self.config = server.config
        self.logger = server.logger
    
    def setup(self) -> None:
        """
        Set up the API routes and handlers.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("API subsystems must implement setup()")
    
    def cleanup(self) -> None:
        """
        Clean up resources when server is stopping.
        Subclasses should override as needed.
        """
        pass
    
    def check_dependencies(self) -> bool:
        """
        Check if required dependencies are available.
        Subclasses should override as needed.
        
        Returns:
            True if all dependencies are available, False otherwise
        """
        return True
    
    def get_routes(self) -> List[Dict[str, Any]]:
        """
        Get information about available routes.
        Useful for API documentation and introspection.
        
        Returns:
            List of route information dictionaries
        """
        return []


class APIRegistry:
    """
    Registry of available API subsystems.
    """
    _registry: Dict[str, Type[APISubsystem]] = {}
    
    @classmethod
    def register(cls, name: str, api_class: Type[APISubsystem]) -> None:
        """
        Register an API subsystem class.
        
        Args:
            name: Name for the API subsystem
            api_class: APISubsystem subclass
        """
        cls._registry[name] = api_class
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[APISubsystem]]:
        """
        Get an API subsystem class by name.
        
        Args:
            name: Name of the API subsystem
            
        Returns:
            APISubsystem subclass or None if not found
        """
        return cls._registry.get(name)
    
    @classmethod
    def list_apis(cls) -> List[str]:
        """
        List all registered API subsystems.
        
        Returns:
            List of API subsystem names
        """
        return list(cls._registry.keys())


# Decorator for registering API subsystems
def register_api(name: str):
    """
    Decorator to register an API subsystem class.
    
    Args:
        name: Name for the API subsystem
        
    Returns:
        Decorator function
    """
    def decorator(api_class: Type[APISubsystem]) -> Type[APISubsystem]:
        APIRegistry.register(name, api_class)
        return api_class
    
    return decorator