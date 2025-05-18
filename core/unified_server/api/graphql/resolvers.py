"""
GraphQL resolvers module for UnifiedServer.
Provides utility classes and functions for implementing GraphQL resolvers.
"""

import inspect
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, Type

# Import utilities
from ...utils.logging import get_logger

# Import Blender adapter
from ...adapters.blender_adapter import blender_adapter

# Import command registry adapter
from ...adapters.command_registry import command_registry

# Get logger
logger = get_logger("graphql_resolvers")


# Define standard Blender-related resolvers
# These functions will be attached to the resolver system defined below
def resolve_scene_info(parent, info, context):
    """
    Resolver for the sceneInfo query
    Gets information about the current Blender scene

    Returns:
        Dict: Scene information
    """
    try:
        # Get scene info from Blender adapter
        result = context.blender.execute_in_main_thread(lambda: context.blender.get_scene_info())
        return result
    except Exception as e:
        logger.error(f"Error resolving scene info: {e}", exc_info=True)
        return None


def resolve_object(parent, info, context, name):
    """
    Resolver for the object query
    Gets information about a specific Blender object

    Args:
        name: Object name

    Returns:
        Dict: Object information
    """
    try:
        # Get object info from Blender adapter
        result = context.blender.execute_in_main_thread(lambda: context.blender.get_object(name))
        return result
    except Exception as e:
        logger.error(f"Error resolving object {name}: {e}", exc_info=True)
        return None


def resolve_create_object(parent, info, context, **kwargs):
    """
    Resolver for the createObject mutation
    Creates a new Blender object

    Args:
        type: Primitive type (CUBE, SPHERE, etc.)
        name: Optional object name
        location: Optional location

    Returns:
        Dict: Creation result
    """
    try:
        # Create command parameters
        params = {k: v for k, v in kwargs.items() if v is not None}

        # Execute create_object command
        result = context.execute_command('create_object', params)
        return result
    except Exception as e:
        logger.error(f"Error creating object: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create object: {str(e)}"
        }


def resolve_transform_object(parent, info, context, **kwargs):
    """
    Resolver for the transformObject mutation
    Transforms an existing Blender object

    Args:
        name: Object name
        location: Optional new location
        rotation: Optional new rotation
        scale: Optional new scale

    Returns:
        Dict: Transformation result
    """
    try:
        # Create command parameters
        params = {k: v for k, v in kwargs.items() if v is not None}

        # Execute transform_object command
        result = context.execute_command('transform_object', params)
        return result
    except Exception as e:
        logger.error(f"Error transforming object: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to transform object: {str(e)}"
        }


def resolve_delete_object(parent, info, context, name):
    """
    Resolver for the deleteObject mutation
    Deletes a Blender object

    Args:
        name: Object name

    Returns:
        Dict: Deletion result
    """
    try:
        # Execute delete_object command
        result = context.execute_command('delete_object', {"name": name})
        return result
    except Exception as e:
        logger.error(f"Error deleting object: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete object: {str(e)}"
        }


def resolve_create_vrm_model(parent, info, context, **kwargs):
    """
    Resolver for the createVrmModel mutation
    Creates a new VRM model

    Args:
        name: Model name
        author: Optional author name
        title: Optional model title

    Returns:
        Dict: Creation result
    """
    try:
        # Create command parameters
        params = {k: v for k, v in kwargs.items() if v is not None}

        # Execute create_vrm_model command
        result = context.execute_command('create_vrm_model', params)
        return result
    except Exception as e:
        logger.error(f"Error creating VRM model: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create VRM model: {str(e)}"
        }


class ResolverContext:
    """
    Context object passed to GraphQL resolvers.
    Provides access to server, Blender adapter, and other useful utilities.
    """

    def __init__(self, server):
        """
        Initialize the resolver context.

        Args:
            server: UnifiedServer instance
        """
        self.server = server
        self.blender = blender_adapter
        self.command_registry = server.command_registry if hasattr(server, 'command_registry') else command_registry
        self.logger = logger

        # Register standard resolver functions
        self.register_standard_resolvers()

    def execute_command(self, command_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command from the server's command registry.

        Args:
            command_name: Command name
            params: Command parameters

        Returns:
            Command result

        Raises:
            Exception: If command execution fails
        """
        if not self.command_registry:
            raise Exception("Command registry not available")

        return self.command_registry.execute_command(command_name, params)

    def register_standard_resolvers(self):
        """
        Register standard resolver functions with GraphQL schema.
        This method is called during initialization to attach resolver functions
        to the GraphQL schema fields.
        """
        try:
            # Import schema to register resolvers
            from .schema import schema_builder

            # Register query resolvers
            schema_builder.query_fields['sceneInfo'] = schema_builder.create_field(
                type_=schema_builder.object_types.get('SceneInfo'),
                description='Get information about the current scene',
                resolve=lambda obj, info: resolve_scene_info(obj, info, self)
            )

            schema_builder.query_fields['object'] = schema_builder.create_field(
                type_=schema_builder.object_types.get('BlenderObject'),
                description='Get information about a specific object',
                args={
                    'name': schema_builder.create_argument(
                        type_=schema_builder.query_fields['object'].args['name'].type,
                        description='Object name'
                    )
                },
                resolve=lambda obj, info, name: resolve_object(obj, info, self, name)
            )

            # Register mutation resolvers
            schema_builder.mutation_fields['createObject'] = schema_builder.create_field(
                type_=schema_builder.object_types.get('CreateObjectResult'),
                description='Create a new object',
                args=schema_builder.mutation_fields['createObject'].args,
                resolve=lambda obj, info, **kwargs: resolve_create_object(obj, info, self, **kwargs)
            )

            schema_builder.mutation_fields['transformObject'] = schema_builder.create_field(
                type_=schema_builder.object_types.get('OperationResult'),
                description='Transform an existing object',
                args=schema_builder.mutation_fields['transformObject'].args,
                resolve=lambda obj, info, **kwargs: resolve_transform_object(obj, info, self, **kwargs)
            )

            schema_builder.mutation_fields['deleteObject'] = schema_builder.create_field(
                type_=schema_builder.object_types.get('OperationResult'),
                description='Delete an object',
                args=schema_builder.mutation_fields['deleteObject'].args,
                resolve=lambda obj, info, name: resolve_delete_object(obj, info, self, name)
            )

            # Register VRM-related resolvers
            if 'createVrmModel' in schema_builder.mutation_fields:
                schema_builder.mutation_fields['createVrmModel'] = schema_builder.create_field(
                    type_=schema_builder.object_types.get('VrmOperationResult'),
                    description='Create a new VRM model',
                    args=schema_builder.mutation_fields['createVrmModel'].args,
                    resolve=lambda obj, info, **kwargs: resolve_create_vrm_model(obj, info, self, **kwargs)
                )

            self.logger.info("Standard resolver functions registered successfully")

        except ImportError as e:
            self.logger.warning(f"Failed to import schema for registering resolvers: {e}")
        except Exception as e:
            self.logger.error(f"Error registering standard resolvers: {e}", exc_info=True)


def resolver(
    command_name: Optional[str] = None,
    params_mapping: Optional[Dict[str, str]] = None,
    result_mapping: Optional[Dict[str, str]] = None
):
    """
    Decorator for creating GraphQL resolvers that execute commands.
    
    Args:
        command_name: Name of the command to execute. If None, the resolver function name is used.
        params_mapping: Mapping from GraphQL parameter names to command parameter names.
        result_mapping: Mapping from command result keys to GraphQL result keys.
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(parent, info, **kwargs):
            # Get server from info context
            if not hasattr(info, "context") or not hasattr(info.context, "get"):
                logger.error("GraphQL resolver called without proper context")
                return None
            
            # Get server from context
            server = info.context.get("server")
            if not server:
                logger.error("GraphQL resolver called without server context")
                return None
            
            # Get command registry
            command_registry = server.command_registry
            if not command_registry:
                logger.error("Command registry not available")
                return None
            
            try:
                # Call original resolver if not using command integration
                if command_name is None and params_mapping is None and result_mapping is None:
                    # Create resolver context
                    context = ResolverContext(server)
                    return func(parent, info, context, **kwargs)
                
                # Determine command name
                cmd_name = command_name or func.__name__
                
                # Map parameters
                if params_mapping:
                    mapped_params = {}
                    for graphql_param, command_param in params_mapping.items():
                        if graphql_param in kwargs:
                            mapped_params[command_param] = kwargs[graphql_param]
                    params = mapped_params
                else:
                    params = kwargs
                
                # Execute command
                result = command_registry.execute_command(cmd_name, params)
                
                # Map result
                if result_mapping:
                    mapped_result = {}
                    for command_key, graphql_key in result_mapping.items():
                        if command_key in result:
                            mapped_result[graphql_key] = result[command_key]
                    return mapped_result
                
                return result
            except Exception as e:
                logger.error(f"Error in GraphQL resolver: {e}", exc_info=True)
                
                # Provide error information in the result
                return {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "params": kwargs
                }
        
        return wrapper
    
    return decorator


def command_resolver(command_name: str):
    """
    Shorthand decorator for creating a resolver that directly executes a command.
    
    Args:
        command_name: Name of the command to execute
        
    Returns:
        Decorator function
    """
    return resolver(command_name=command_name)


def blender_resolver(in_main_thread: bool = True):
    """
    Decorator for creating resolvers that interact with Blender.
    Ensures that Blender operations are executed in the main thread.
    
    Args:
        in_main_thread: Whether to execute the resolver in Blender's main thread
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(parent, info, **kwargs):
            # Execute in main thread if needed
            if in_main_thread and blender_adapter.blender_available:
                main_thread_func = blender_adapter.execute_in_main_thread(func)
                try:
                    return main_thread_func(parent, info, **kwargs)
                except Exception as e:
                    logger.error(f"Error in Blender resolver: {e}", exc_info=True)
                    return None
            else:
                try:
                    return func(parent, info, **kwargs)
                except Exception as e:
                    logger.error(f"Error in resolver: {e}", exc_info=True)
                    return None
        
        return wrapper
    
    return decorator