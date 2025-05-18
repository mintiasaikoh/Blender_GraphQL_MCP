"""
Blender adapter for UnifiedServer.
Provides utilities for interacting with Blender from the server.
"""

import sys
import time
import threading
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, Tuple

# Import utilities
from ..utils.logging import get_logger
from ..utils.threading import execute_in_main_thread

# Type variable for function return type
T = TypeVar('T')

# Get logger
logger = get_logger("blender_adapter")

# Check if we're running in Blender environment
try:
    import bpy
    IS_BLENDER_AVAILABLE = True
except ImportError:
    IS_BLENDER_AVAILABLE = False
    logger.warning("Blender environment not available")


class BlenderAdapter:
    """
    Adapter for interacting with Blender from the server.
    Provides utilities for executing commands in Blender's main thread
    and accessing Blender data safely.
    """
    
    _instance = None  # Singleton instance
    
    @classmethod
    def get_instance(cls) -> 'BlenderAdapter':
        """Get singleton instance of the adapter."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the Blender adapter."""
        self.logger = logger
        
        # Verify Blender environment
        self.blender_available = IS_BLENDER_AVAILABLE
        if not self.blender_available:
            self.logger.warning("Initialized BlenderAdapter without Blender environment")
            return
        
        # Get Blender version info
        self.version_info = self._get_version_info()
        self.logger.info(f"Initialized BlenderAdapter for Blender {self.version_info['version_string']}")
    
    def execute_in_main_thread(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to ensure a function is executed in the main Blender thread.
        
        Args:
            func: Function to execute in main thread
        
        Returns:
            Wrapped function that executes in main thread
        """
        if not self.blender_available:
            # If Blender is not available, just return the function as-is
            return func
        
        # Use the threading utility's execute_in_main_thread
        return execute_in_main_thread(func)
    
    def safe_execute(self, func: Callable[..., T], *args, **kwargs) -> Tuple[bool, Union[T, Exception]]:
        """
        Safely execute a function in Blender context with exception handling.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        
        Returns:
            Tuple of (success, result or exception)
        """
        if not self.blender_available:
            return False, RuntimeError("Blender environment not available")
        
        # Convert function to main thread execution if needed
        main_thread_func = self.execute_in_main_thread(func)
        
        try:
            # Execute function and return result
            result = main_thread_func(*args, **kwargs)
            return True, result
        except Exception as e:
            # Log the exception
            self.logger.error(f"Error executing {func.__name__}: {e}", exc_info=True)
            return False, e
    
    def get_object(self, name: str) -> Optional[Any]:
        """
        Get a Blender object by name.
        
        Args:
            name: Object name
        
        Returns:
            Blender object or None if not found
        """
        if not self.blender_available:
            return None
        
        @self.execute_in_main_thread
        def _get_object():
            return bpy.data.objects.get(name)
        
        return _get_object()
    
    def get_scene(self, name: Optional[str] = None) -> Optional[Any]:
        """
        Get a Blender scene by name or the active scene if name is None.
        
        Args:
            name: Scene name or None for active scene
        
        Returns:
            Blender scene or None if not found
        """
        if not self.blender_available:
            return None
        
        @self.execute_in_main_thread
        def _get_scene():
            if name is None:
                return bpy.context.scene
            return bpy.data.scenes.get(name)
        
        return _get_scene()
    
    def get_material(self, name: str) -> Optional[Any]:
        """
        Get a Blender material by name.
        
        Args:
            name: Material name
        
        Returns:
            Blender material or None if not found
        """
        if not self.blender_available:
            return None
        
        @self.execute_in_main_thread
        def _get_material():
            return bpy.data.materials.get(name)
        
        return _get_material()
    
    def get_addon_prefs(self, addon_name: str) -> Optional[Any]:
        """
        Get addon preferences for a specific addon.
        
        Args:
            addon_name: Addon name
        
        Returns:
            Addon preferences or None if addon not found
        """
        if not self.blender_available:
            return None
        
        @self.execute_in_main_thread
        def _get_addon_prefs():
            if not hasattr(bpy.context, 'preferences'):
                return None
            
            if not hasattr(bpy.context.preferences, 'addons'):
                return None
            
            if addon_name not in bpy.context.preferences.addons:
                return None
            
            return bpy.context.preferences.addons[addon_name].preferences
        
        return _get_addon_prefs()
    
    def is_addon_enabled(self, addon_name: str) -> bool:
        """
        Check if an addon is enabled.
        
        Args:
            addon_name: Addon name
        
        Returns:
            True if addon is enabled, False otherwise
        """
        if not self.blender_available:
            return False
        
        @self.execute_in_main_thread
        def _is_addon_enabled():
            if not hasattr(bpy.context, 'preferences'):
                return False
            
            if not hasattr(bpy.context.preferences, 'addons'):
                return False
            
            return addon_name in bpy.context.preferences.addons
        
        return _is_addon_enabled()
    
    def enable_addon(self, addon_name: str) -> bool:
        """
        Enable an addon.
        
        Args:
            addon_name: Addon name
        
        Returns:
            True if addon was enabled successfully, False otherwise
        """
        if not self.blender_available:
            return False
        
        @self.execute_in_main_thread
        def _enable_addon():
            try:
                bpy.ops.preferences.addon_enable(module=addon_name)
                return addon_name in bpy.context.preferences.addons
            except Exception as e:
                self.logger.error(f"Error enabling addon {addon_name}: {e}", exc_info=True)
                return False
        
        return _enable_addon()
    
    def get_all_addons(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all addons.
        
        Returns:
            Dictionary mapping addon names to addon information
        """
        if not self.blender_available:
            return {}
        
        @self.execute_in_main_thread
        def _get_all_addons():
            addons = {}
            
            # Check if we can access preferences
            if not hasattr(bpy.context, 'preferences') or not hasattr(bpy.context.preferences, 'addons'):
                return addons
            
            try:
                # Iterate over all addon modules
                for addon_name in bpy.context.preferences.addons.keys():
                    try:
                        # Get addon module information
                        mod = sys.modules.get(addon_name)
                        info = {}
                        
                        if mod and hasattr(mod, 'bl_info'):
                            # Extract bl_info
                            for key, value in mod.bl_info.items():
                                info[key] = value
                        
                        # Add addon to result
                        addons[addon_name] = {
                            'name': addon_name,
                            'is_enabled': True,
                            'info': info
                        }
                    except Exception as e:
                        self.logger.warning(f"Error getting info for addon {addon_name}: {e}")
            except Exception as e:
                self.logger.error(f"Error getting all addons: {e}", exc_info=True)
            
            return addons
        
        return _get_all_addons()
    
    def _get_version_info(self) -> Dict[str, Any]:
        """
        Get Blender version information.
        
        Returns:
            Dictionary with version information
        """
        if not self.blender_available:
            return {
                'version': (0, 0, 0),
                'version_string': 'Unknown',
                'build_date': 'Unknown',
                'platform': sys.platform
            }
        
        @self.execute_in_main_thread
        def _get_info():
            info = {
                'version': bpy.app.version,
                'version_string': '.'.join(map(str, bpy.app.version)),
                'build_date': getattr(bpy.app, 'build_date', 'Unknown'),
                'platform': sys.platform
            }
            
            # Additional Blender information if available
            if hasattr(bpy.app, 'version_cycle'):
                info['version_cycle'] = bpy.app.version_cycle
            
            if hasattr(bpy.app, 'build_branch'):
                info['build_branch'] = bpy.app.build_branch
            
            if hasattr(bpy.app, 'build_commit_date'):
                info['build_commit_date'] = bpy.app.build_commit_date
            
            if hasattr(bpy.app, 'build_commit_time'):
                info['build_commit_time'] = bpy.app.build_commit_time
            
            if hasattr(bpy.app, 'build_cflags'):
                info['build_cflags'] = bpy.app.build_cflags
            
            if hasattr(bpy.app, 'build_system'):
                info['build_system'] = bpy.app.build_system
            
            return info
        
        return _get_info()


# Create singleton instance
blender_adapter = BlenderAdapter.get_instance()

# Decorator for executing functions in Blender main thread
def in_blender_thread(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to ensure a function is executed in the main Blender thread.
    
    Args:
        func: Function to execute in main thread
        
    Returns:
        Wrapped function that executes in main thread
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return blender_adapter.execute_in_main_thread(func)(*args, **kwargs)
    
    return wrapper