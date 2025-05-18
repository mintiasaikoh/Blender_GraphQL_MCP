"""
Unified server package for Blender GraphQL MCP.
Provides a modular server architecture with support for multiple API types.
"""

__version__ = "1.0.0"

# Export core classes
from .core.server import UnifiedServer
from .core.config import ServerConfig

# Export API registry
from .api.base import APIRegistry, register_api

# Export utility functions
from .utils.logging import get_logger, setup_logging
from .utils.threading import execute_in_main_thread

# Export adapters
from .adapters.blender_adapter import blender_adapter, in_blender_thread
from .adapters.command_registry import (
    CommandRegistry, CommandError, register_command,
    CommandNotFoundError, CommandValidationError, CommandExecError
)