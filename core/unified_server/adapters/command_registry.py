"""
Command registry for UnifiedServer.
Provides a centralized registry for commands with validation and execution.
"""

import inspect
import json
import threading
import traceback
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, Type, TypeVar

# Import utilities
from ..utils.logging import get_logger

# Import Blender adapter
from .blender_adapter import blender_adapter, in_blender_thread

# Type variable for function return type
T = TypeVar('T')

# Get logger
logger = get_logger("command_registry")


class CommandError(Exception):
    """Base class for command-related exceptions."""
    pass


class CommandNotFoundError(CommandError):
    """Exception raised when a command is not found in the registry."""
    pass


class CommandValidationError(CommandError):
    """Exception raised when command parameters fail validation."""
    pass


class CommandExecError(CommandError):
    """Exception raised when a command fails during execution."""
    pass


class CommandRegistry:
    """
    Registry for commands with validation and execution.
    Provides a centralized registry for all commands in the system.
    """
    
    def __init__(self):
        """Initialize the command registry."""
        self.logger = logger
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.registry_lock = threading.RLock()
        
        self.logger.info("Initialized CommandRegistry")
    
    def register_command(
        self,
        name: str,
        func: Callable,
        description: str = "",
        category: str = "general",
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        returns: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
        is_dangerous: bool = False,
        in_main_thread: bool = True
    ) -> None:
        """
        Register a command in the registry.
        
        Args:
            name: Command name
            func: Command function
            description: Command description
            category: Command category
            parameters: Command parameters schema
            returns: Command return value schema
            examples: Command usage examples
            is_dangerous: Whether the command is potentially dangerous
            in_main_thread: Whether to execute the command in Blender's main thread
        """
        with self.registry_lock:
            # Check if command already exists
            if name in self.commands:
                self.logger.warning(f"Command '{name}' already registered, overwriting")
            
            # Get function signature if parameters not provided
            if parameters is None:
                parameters = self._get_parameters_from_signature(func)
            
            # Create command entry
            command = {
                "name": name,
                "func": func,
                "description": description,
                "category": category,
                "parameters": parameters,
                "returns": returns or {"type": "dict", "description": "Command result"},
                "examples": examples or [],
                "is_dangerous": is_dangerous,
                "in_main_thread": in_main_thread
            }
            
            # Register command
            self.commands[name] = command
            self.logger.debug(f"Registered command: {name} ({description})")
    
    def unregister_command(self, name: str) -> bool:
        """
        Unregister a command from the registry.
        
        Args:
            name: Command name
            
        Returns:
            True if command was unregistered, False if not found
        """
        with self.registry_lock:
            if name in self.commands:
                del self.commands[name]
                self.logger.debug(f"Unregistered command: {name}")
                return True
            
            self.logger.warning(f"Command '{name}' not found in registry")
            return False
    
    def get_command(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a command from the registry.
        
        Args:
            name: Command name
            
        Returns:
            Command entry or None if not found
        """
        with self.registry_lock:
            return self.commands.get(name)
    
    def list_commands(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all commands in the registry.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            List of command entries
        """
        with self.registry_lock:
            if category:
                return [
                    {
                        "name": cmd["name"],
                        "description": cmd["description"],
                        "category": cmd["category"],
                        "parameters": cmd["parameters"],
                        "returns": cmd["returns"],
                        "examples": cmd["examples"],
                        "is_dangerous": cmd["is_dangerous"]
                    }
                    for cmd in self.commands.values()
                    if cmd["category"] == category
                ]
            
            return [
                {
                    "name": cmd["name"],
                    "description": cmd["description"],
                    "category": cmd["category"],
                    "parameters": cmd["parameters"],
                    "returns": cmd["returns"],
                    "examples": cmd["examples"],
                    "is_dangerous": cmd["is_dangerous"]
                }
                for cmd in self.commands.values()
            ]
    
    def list_categories(self) -> List[str]:
        """
        List all command categories.
        
        Returns:
            List of category names
        """
        with self.registry_lock:
            categories = set(cmd["category"] for cmd in self.commands.values())
            return sorted(list(categories))
    
    def validate_parameters(self, command_name: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate command parameters against command schema.
        
        Args:
            command_name: Command name
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        with self.registry_lock:
            # Get command
            command = self.get_command(command_name)
            if not command:
                return False, f"Command '{command_name}' not found"
            
            # Get parameter schema
            param_schema = command["parameters"]
            
            # Check for missing required parameters
            for param_name, param_info in param_schema.items():
                if param_info.get("required", True) and param_name not in params:
                    return False, f"Missing required parameter: {param_name}"
            
            # Check for unknown parameters
            for param_name in params:
                if param_name not in param_schema:
                    return False, f"Unknown parameter: {param_name}"
            
            # Validate parameter types
            for param_name, param_value in params.items():
                param_info = param_schema.get(param_name, {})
                param_type = param_info.get("type")
                
                if param_type == "str" and not isinstance(param_value, str):
                    return False, f"Parameter '{param_name}' must be a string"
                
                elif param_type == "int" and not isinstance(param_value, int):
                    # Try to convert to int if possible
                    try:
                        params[param_name] = int(param_value)
                    except (ValueError, TypeError):
                        return False, f"Parameter '{param_name}' must be an integer"
                
                elif param_type == "float" and not isinstance(param_value, (int, float)):
                    # Try to convert to float if possible
                    try:
                        params[param_name] = float(param_value)
                    except (ValueError, TypeError):
                        return False, f"Parameter '{param_name}' must be a number"
                
                elif param_type == "bool" and not isinstance(param_value, bool):
                    # Handle string representations of booleans
                    if isinstance(param_value, str):
                        if param_value.lower() in ("true", "yes", "1"):
                            params[param_name] = True
                        elif param_value.lower() in ("false", "no", "0"):
                            params[param_name] = False
                        else:
                            return False, f"Parameter '{param_name}' must be a boolean"
                    else:
                        return False, f"Parameter '{param_name}' must be a boolean"
                
                elif param_type == "list" and not isinstance(param_value, list):
                    # Try to parse JSON if it's a string
                    if isinstance(param_value, str):
                        try:
                            params[param_name] = json.loads(param_value)
                            if not isinstance(params[param_name], list):
                                return False, f"Parameter '{param_name}' must be a list"
                        except json.JSONDecodeError:
                            return False, f"Parameter '{param_name}' must be a valid JSON list"
                    else:
                        return False, f"Parameter '{param_name}' must be a list"
                
                elif param_type == "dict" and not isinstance(param_value, dict):
                    # Try to parse JSON if it's a string
                    if isinstance(param_value, str):
                        try:
                            params[param_name] = json.loads(param_value)
                            if not isinstance(params[param_name], dict):
                                return False, f"Parameter '{param_name}' must be a dictionary"
                        except json.JSONDecodeError:
                            return False, f"Parameter '{param_name}' must be a valid JSON object"
                    else:
                        return False, f"Parameter '{param_name}' must be a dictionary"
            
            return True, None
    
    def execute_command(self, command_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command with the given parameters.
        
        Args:
            command_name: Command name
            params: Command parameters
            
        Returns:
            Command result
            
        Raises:
            CommandNotFoundError: If command not found
            CommandValidationError: If parameters fail validation
            CommandExecError: If command execution fails
        """
        # Get command
        command = self.get_command(command_name)
        if not command:
            raise CommandNotFoundError(f"Command '{command_name}' not found")
        
        # Validate parameters
        is_valid, error_message = self.validate_parameters(command_name, params)
        if not is_valid:
            raise CommandValidationError(error_message)
        
        try:
            # Get command function
            func = command["func"]
            
            # Execute in main thread if required
            if command["in_main_thread"] and blender_adapter.blender_available:
                result = blender_adapter.execute_in_main_thread(func)(**params)
            else:
                result = func(**params)
            
            # Return result
            return result
        except Exception as e:
            # Build error details
            error_details = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "command": command_name,
                "params": params
            }
            
            # Log error
            self.logger.error(f"Error executing command '{command_name}': {e}", exc_info=True)
            
            # Raise command execution error
            raise CommandExecError(f"Error executing command '{command_name}': {e}", error_details)
    
    def execute_batch(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a batch of commands.
        
        Args:
            commands: List of command objects with 'command' and 'params' keys
            
        Returns:
            List of command results with success/error information
        """
        results = []
        
        for idx, cmd in enumerate(commands):
            command_name = cmd.get("command")
            params = cmd.get("params", {})
            
            if not command_name:
                results.append({
                    "success": False,
                    "error": "Missing command name",
                    "index": idx
                })
                continue
            
            try:
                # Execute command
                result = self.execute_command(command_name, params)
                
                # Add success result
                results.append({
                    "success": True,
                    "result": result,
                    "command": command_name,
                    "index": idx
                })
            except CommandError as e:
                # Add error result
                results.append({
                    "success": False,
                    "error": str(e),
                    "command": command_name,
                    "index": idx
                })
            except Exception as e:
                # Add unexpected error result
                results.append({
                    "success": False,
                    "error": f"Unexpected error: {str(e)}",
                    "command": command_name,
                    "index": idx
                })
        
        return results
    
    def _get_parameters_from_signature(self, func: Callable) -> Dict[str, Dict[str, Any]]:
        """
        Extract parameter information from function signature.
        
        Args:
            func: Function to extract parameters from
            
        Returns:
            Dictionary of parameter information
        """
        params = {}
        sig = inspect.signature(func)
        
        for name, param in sig.parameters.items():
            # Skip 'self' parameter
            if name == "self":
                continue
            
            # Get parameter type annotation
            param_type = "any"
            if param.annotation != inspect.Parameter.empty:
                if hasattr(param.annotation, "__name__"):
                    param_type = param.annotation.__name__.lower()
                elif hasattr(param.annotation, "__origin__"):
                    # Handle typing annotations like List[str]
                    origin = param.annotation.__origin__
                    if hasattr(origin, "__name__"):
                        param_type = origin.__name__.lower()
            
            # Get default value and determine if required
            has_default = param.default != inspect.Parameter.empty
            required = not has_default
            default = None if not has_default else param.default
            
            # Add parameter information
            params[name] = {
                "type": param_type,
                "required": required,
                "default": default,
                "description": ""  # No description available from signature
            }
        
        return params


# Decorator for registering commands
def register_command(
    name: str,
    description: str = "",
    category: str = "general",
    parameters: Optional[Dict[str, Dict[str, Any]]] = None,
    returns: Optional[Dict[str, Any]] = None,
    examples: Optional[List[Dict[str, Any]]] = None,
    is_dangerous: bool = False,
    in_main_thread: bool = True
):
    """
    Decorator for registering a function as a command.
    
    Args:
        name: Command name
        description: Command description
        category: Command category
        parameters: Command parameters schema (if None, extracted from function signature)
        returns: Command return value schema
        examples: Command usage examples
        is_dangerous: Whether the command is potentially dangerous
        in_main_thread: Whether to execute the command in Blender's main thread
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        # Import here to avoid circular imports
        from ..core.server import UnifiedServer
        
        # Get server instance
        server = UnifiedServer.get_instance()
        
        # Register command with server's command registry
        if server.command_registry:
            server.command_registry.register_command(
                name=name,
                func=func,
                description=description,
                category=category,
                parameters=parameters,
                returns=returns,
                examples=examples,
                is_dangerous=is_dangerous,
                in_main_thread=in_main_thread
            )
        else:
            logger.warning(f"Cannot register command '{name}': Command registry not available")
        
        return func
    
    return decorator