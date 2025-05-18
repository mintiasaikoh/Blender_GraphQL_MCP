"""
GraphQL schema module for UnifiedServer.
Provides utilities for building and extending GraphQL schemas.
"""

from typing import Any, Dict, List, Optional, Set, Type, Union
import json
import inspect

# Try to import GraphQL dependencies
try:
    from tools import (
        GraphQLSchema, GraphQLObjectType, GraphQLString, GraphQLInt, GraphQLFloat,
        GraphQLBoolean, GraphQLList, GraphQLNonNull, GraphQLArgument, GraphQLField,
        GraphQLEnumType, GraphQLInputObjectType, GraphQLScalarType
    )
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False

    # Define dummy classes for type checking
    class GraphQLSchema:
        pass

    class GraphQLObjectType:
        pass

    class GraphQLField:
        pass

# Import utilities
from ...utils.logging import get_logger

# Get logger
logger = get_logger("graphql_schema")


# LLM Helper Functions

def _generate_function_info(function_name: str, schema_builder) -> Dict[str, Any]:
    """
    Generate detailed information about a specific GraphQL function for LLMs.

    Args:
        function_name: The name of the function
        schema_builder: The SchemaBuilder instance

    Returns:
        A dictionary with detailed information about the function
    """
    # Check if function exists in queries
    if function_name in schema_builder.query_fields:
        field = schema_builder.query_fields[function_name]
        operation_type = "query"
    # Check if function exists in mutations
    elif function_name in schema_builder.mutation_fields:
        field = schema_builder.mutation_fields[function_name]
        operation_type = "mutation"
    else:
        return {
            "error": f"Function '{function_name}' not found",
            "available_functions": {
                "queries": list(schema_builder.query_fields.keys()),
                "mutations": list(schema_builder.mutation_fields.keys())
            }
        }

    # Get function description
    description = field.description if hasattr(field, "description") else "No description"

    # Get function arguments
    arguments = {}
    if hasattr(field, "args") and field.args:
        for arg_name, arg in field.args.items():
            arg_type = _get_type_name(arg.type)
            arg_description = arg.description if hasattr(arg, "description") else "No description"
            arg_required = isinstance(arg.type, GraphQLNonNull) if GRAPHQL_AVAILABLE else False

            arguments[arg_name] = {
                "type": arg_type,
                "description": arg_description,
                "required": arg_required
            }

    # Get return type
    return_type = _get_type_name(field.type) if hasattr(field, "type") else "Unknown"

    # Generate example usage
    example = _generate_example_usage(function_name, operation_type, arguments, return_type)

    # Assemble function info
    function_info = {
        "name": function_name,
        "type": operation_type,
        "description": description,
        "arguments": arguments,
        "return_type": return_type,
        "example": example
    }

    return function_info


def _get_type_name(type_obj: Any) -> str:
    """
    Get the name of a GraphQL type.

    Args:
        type_obj: GraphQL type object

    Returns:
        String representation of the type
    """
    if not GRAPHQL_AVAILABLE:
        return "Unknown"

    if isinstance(type_obj, GraphQLNonNull):
        return f"{_get_type_name(type_obj.of_type)}!"
    elif isinstance(type_obj, GraphQLList):
        return f"[{_get_type_name(type_obj.of_type)}]"
    elif hasattr(type_obj, "name"):
        return type_obj.name
    else:
        return str(type_obj)


def _generate_example_usage(function_name: str, operation_type: str, arguments: Dict[str, Any], return_type: str) -> str:
    """
    Generate an example usage of a GraphQL function.

    Args:
        function_name: The name of the function
        operation_type: "query" or "mutation"
        arguments: Dictionary of function arguments
        return_type: Return type name

    Returns:
        Example usage string in GraphQL format
    """
    # Create argument string
    args_str = ""
    if arguments:
        args_list = []
        for arg_name, arg_info in arguments.items():
            if arg_info.get("type") == "String":
                args_list.append(f'{arg_name}: "example_{arg_name}"')
            elif arg_info.get("type") == "Int":
                args_list.append(f'{arg_name}: 42')
            elif arg_info.get("type") == "Float":
                args_list.append(f'{arg_name}: 3.14')
            elif arg_info.get("type") == "Boolean":
                args_list.append(f'{arg_name}: true')
            elif arg_info.get("type") == "Vector3Input":
                args_list.append(f'{arg_name}: {{x: 1, y: 2, z: 3}}')
            elif arg_info.get("type") in ["PrimitiveType", "ObjectType"]:
                args_list.append(f'{arg_name}: CUBE')
            else:
                args_list.append(f'{arg_name}: "..."')

        if args_list:
            args_str = f"({', '.join(args_list)})"

    # Create return fields based on return type
    return_fields = "  # Add fields to query here\n"
    if return_type in ["String", "Int", "Float", "Boolean"]:
        return_fields = ""
    elif return_type == "SceneInfo":
        return_fields = "  name\n  objects {\n    name\n    type\n  }\n  frame_current"
    elif return_type == "BlenderObject":
        return_fields = "  name\n  type\n  location {\n    x\n    y\n    z\n  }"
    elif return_type in ["CreateObjectResult", "OperationResult", "VrmOperationResult"]:
        return_fields = "  success\n  message\n  error"
        # Add object field if it's CreateObjectResult
        if return_type == "CreateObjectResult":
            return_fields += "\n  object {\n    name\n    type\n  }"
        # Add model field if it's VrmOperationResult
        elif return_type == "VrmOperationResult":
            return_fields += "\n  model {\n    name\n    version\n  }"

    # Assemble example
    example = f"{operation_type} {{\n  {function_name}{args_str} {{\n{return_fields}\n  }}\n}}"

    return example


def _generate_schema_doc(schema_builder) -> str:
    """
    Generate complete schema documentation in Markdown format for LLMs.

    Args:
        schema_builder: The SchemaBuilder instance

    Returns:
        Markdown string with complete schema documentation
    """
    if not GRAPHQL_AVAILABLE:
        return "GraphQL dependencies not available. Schema documentation cannot be generated."

    # Start with header
    doc = "# Blender GraphQL MCP Schema Documentation\n\n"
    doc += "This document describes the GraphQL schema for Blender GraphQL MCP.\n\n"

    # Add table of contents
    doc += "## Table of Contents\n\n"
    doc += "1. [Queries](#queries)\n"
    doc += "2. [Mutations](#mutations)\n"
    doc += "3. [Types](#types)\n\n"

    # Add queries section
    doc += "## Queries\n\n"
    for query_name, query in schema_builder.query_fields.items():
        # Skip LLM-specific queries in the main documentation
        if query_name.startswith("_llm"):
            continue

        doc += f"### {query_name}\n\n"
        doc += f"{query.description}\n\n"

        # Add arguments if any
        if hasattr(query, "args") and query.args:
            doc += "**Arguments:**\n\n"
            for arg_name, arg in query.args.items():
                arg_type = _get_type_name(arg.type)
                arg_required = "Required" if isinstance(arg.type, GraphQLNonNull) else "Optional"
                doc += f"- `{arg_name}` ({arg_type}, {arg_required}): {arg.description}\n"
            doc += "\n"

        # Add return type
        return_type = _get_type_name(query.type)
        doc += f"**Returns:** {return_type}\n\n"

        # Add example
        arguments = {}
        if hasattr(query, "args") and query.args:
            for arg_name, arg in query.args.items():
                arg_type = _get_type_name(arg.type)
                arg_description = arg.description if hasattr(arg, "description") else "No description"
                arg_required = isinstance(arg.type, GraphQLNonNull)

                arguments[arg_name] = {
                    "type": arg_type,
                    "description": arg_description,
                    "required": arg_required
                }

        example = _generate_example_usage(query_name, "query", arguments, return_type)
        doc += "**Example:**\n\n```graphql\n" + example + "\n```\n\n"

    # Add mutations section
    doc += "## Mutations\n\n"
    for mutation_name, mutation in schema_builder.mutation_fields.items():
        doc += f"### {mutation_name}\n\n"
        doc += f"{mutation.description}\n\n"

        # Add arguments if any
        if hasattr(mutation, "args") and mutation.args:
            doc += "**Arguments:**\n\n"
            for arg_name, arg in mutation.args.items():
                arg_type = _get_type_name(arg.type)
                arg_required = "Required" if isinstance(arg.type, GraphQLNonNull) else "Optional"
                doc += f"- `{arg_name}` ({arg_type}, {arg_required}): {arg.description}\n"
            doc += "\n"

        # Add return type
        return_type = _get_type_name(mutation.type)
        doc += f"**Returns:** {return_type}\n\n"

        # Add example
        arguments = {}
        if hasattr(mutation, "args") and mutation.args:
            for arg_name, arg in mutation.args.items():
                arg_type = _get_type_name(arg.type)
                arg_description = arg.description if hasattr(arg, "description") else "No description"
                arg_required = isinstance(arg.type, GraphQLNonNull)

                arguments[arg_name] = {
                    "type": arg_type,
                    "description": arg_description,
                    "required": arg_required
                }

        example = _generate_example_usage(mutation_name, "mutation", arguments, return_type)
        doc += "**Example:**\n\n```graphql\n" + example + "\n```\n\n"

    # Add types section
    doc += "## Types\n\n"
    for type_name, type_obj in schema_builder.object_types.items():
        doc += f"### {type_name}\n\n"
        doc += f"{type_obj.description}\n\n"

        # Add fields
        doc += "**Fields:**\n\n"
        for field_name, field in type_obj.fields.items():
            field_type = _get_type_name(field.type)
            doc += f"- `{field_name}` ({field_type}): {field.description}\n"
        doc += "\n"

    return doc


class SchemaBuilder:
    """
    Utility class for building GraphQL schemas.
    Provides methods for creating and extending GraphQL schemas.
    """
    
    def __init__(self):
        """Initialize the schema builder."""
        self.logger = logger
        
        # Check GraphQL availability
        if not GRAPHQL_AVAILABLE:
            self.logger.warning("GraphQL dependencies not available")
            return
        
        # Query fields
        self.query_fields: Dict[str, GraphQLField] = {}
        
        # Mutation fields
        self.mutation_fields: Dict[str, GraphQLField] = {}
        
        # Object types
        self.object_types: Dict[str, GraphQLObjectType] = {}
        
        # Schema
        self.schema: Optional[GraphQLSchema] = None
    
    def add_query_field(self, name: str, field: Any) -> None:
        """
        Add a field to the query type.
        
        Args:
            name: Field name
            field: GraphQLField instance
        """
        if not GRAPHQL_AVAILABLE:
            self.logger.warning("GraphQL dependencies not available, skipping add_query_field")
            return
        
        self.query_fields[name] = field
        self.logger.debug(f"Added query field: {name}")
    
    def add_mutation_field(self, name: str, field: Any) -> None:
        """
        Add a field to the mutation type.
        
        Args:
            name: Field name
            field: GraphQLField instance
        """
        if not GRAPHQL_AVAILABLE:
            self.logger.warning("GraphQL dependencies not available, skipping add_mutation_field")
            return
        
        self.mutation_fields[name] = field
        self.logger.debug(f"Added mutation field: {name}")
    
    def add_object_type(self, name: str, object_type: Any) -> None:
        """
        Add an object type to the schema.
        
        Args:
            name: Object type name
            object_type: GraphQLObjectType instance
        """
        if not GRAPHQL_AVAILABLE:
            self.logger.warning("GraphQL dependencies not available, skipping add_object_type")
            return
        
        self.object_types[name] = object_type
        self.logger.debug(f"Added object type: {name}")
    
    def create_object_type(
        self,
        name: str,
        fields: Dict[str, Any],
        description: Optional[str] = None
    ) -> Optional[Any]:
        """
        Create a GraphQL object type.
        
        Args:
            name: Object type name
            fields: Object type fields
            description: Optional object type description
            
        Returns:
            GraphQLObjectType instance or None if GraphQL is not available
        """
        if not GRAPHQL_AVAILABLE:
            self.logger.warning("GraphQL dependencies not available, skipping create_object_type")
            return None
        
        object_type = GraphQLObjectType(
            name=name,
            fields=fields,
            description=description
        )
        
        self.add_object_type(name, object_type)
        return object_type
    
    def create_field(
        self,
        type_: Any,
        description: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
        resolve: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Create a GraphQL field.
        
        Args:
            type_: Field type (GraphQLObjectType, GraphQLScalarType, etc.)
            description: Optional field description
            args: Optional field arguments
            resolve: Optional resolve function
            
        Returns:
            GraphQLField instance or None if GraphQL is not available
        """
        if not GRAPHQL_AVAILABLE:
            self.logger.warning("GraphQL dependencies not available, skipping create_field")
            return None
        
        return GraphQLField(
            type_=type_,
            args=args,
            resolve=resolve,
            description=description
        )
    
    def create_argument(
        self,
        type_: Any,
        default_value: Any = None,
        description: Optional[str] = None
    ) -> Optional[Any]:
        """
        Create a GraphQL argument.
        
        Args:
            type_: Argument type (GraphQLScalarType, etc.)
            default_value: Optional default value
            description: Optional argument description
            
        Returns:
            GraphQLArgument instance or None if GraphQL is not available
        """
        if not GRAPHQL_AVAILABLE:
            self.logger.warning("GraphQL dependencies not available, skipping create_argument")
            return None
        
        return GraphQLArgument(
            type_=type_,
            default_value=default_value,
            description=description
        )
    
    def build_schema(self) -> Optional[GraphQLSchema]:
        """
        Build the GraphQL schema.
        
        Returns:
            GraphQLSchema instance or None if GraphQL is not available
        """
        if not GRAPHQL_AVAILABLE:
            self.logger.warning("GraphQL dependencies not available, skipping build_schema")
            return None
        
        # Create query type
        query_type = GraphQLObjectType(
            name="Query",
            fields=self.query_fields
        )
        
        # Create mutation type if mutation fields exist
        mutation_type = None
        if self.mutation_fields:
            mutation_type = GraphQLObjectType(
                name="Mutation",
                fields=self.mutation_fields
            )
        
        # Create schema
        self.schema = GraphQLSchema(
            query=query_type,
            mutation=mutation_type
        )
        
        self.logger.info(f"Built GraphQL schema with {len(self.query_fields)} query fields, "
                        f"{len(self.mutation_fields)} mutation fields, and "
                        f"{len(self.object_types)} object types")
        
        return self.schema
    
    def get_schema(self) -> Optional[GraphQLSchema]:
        """
        Get the built schema or build it if not already built.
        
        Returns:
            GraphQLSchema instance or None if GraphQL is not available
        """
        if not GRAPHQL_AVAILABLE:
            self.logger.warning("GraphQL dependencies not available, skipping get_schema")
            return None
        
        if self.schema is None:
            return self.build_schema()
        
        return self.schema


# Create singleton schema builder
schema_builder = SchemaBuilder()

# Convenience functions for building GraphQL schemas
def add_query_field(name: str, field: Any) -> None:
    """Add a field to the query type."""
    schema_builder.add_query_field(name, field)

def add_mutation_field(name: str, field: Any) -> None:
    """Add a field to the mutation type."""
    schema_builder.add_mutation_field(name, field)

def add_object_type(name: str, object_type: Any) -> None:
    """Add an object type to the schema."""
    schema_builder.add_object_type(name, object_type)

def create_object_type(name: str, fields: Dict[str, Any], description: Optional[str] = None) -> Optional[Any]:
    """Create a GraphQL object type."""
    return schema_builder.create_object_type(name, fields, description)

def create_field(type_: Any, description: Optional[str] = None, args: Optional[Dict[str, Any]] = None, resolve: Optional[Any] = None) -> Optional[Any]:
    """Create a GraphQL field."""
    return schema_builder.create_field(type_, description, args, resolve)

def create_argument(type_: Any, default_value: Any = None, description: Optional[str] = None) -> Optional[Any]:
    """Create a GraphQL argument."""
    return schema_builder.create_argument(type_, default_value, description)

def build_schema() -> Optional[GraphQLSchema]:
    """Build the GraphQL schema."""
    # If GraphQL is not available, return None
    if not GRAPHQL_AVAILABLE:
        logger.warning("GraphQL dependencies not available, skipping build_schema")
        return None

    # Define base Blender types
    # Vector3 type for coordinates
    vector3_type = GraphQLObjectType(
        name='Vector3',
        fields={
            'x': GraphQLField(GraphQLFloat, description='X coordinate'),
            'y': GraphQLField(GraphQLFloat, description='Y coordinate'),
            'z': GraphQLField(GraphQLFloat, description='Z coordinate')
        },
        description='3D vector coordinates'
    )

    # Vector3 input type
    vector3_input_type = GraphQLInputObjectType(
        name='Vector3Input',
        fields={
            'x': GraphQLField(GraphQLFloat, description='X coordinate'),
            'y': GraphQLField(GraphQLFloat, description='Y coordinate'),
            'z': GraphQLField(GraphQLFloat, description='Z coordinate')
        },
        description='Input for 3D vector coordinates'
    )

    # Blender object type
    blender_object_type = GraphQLObjectType(
        name='BlenderObject',
        fields={
            'name': GraphQLField(GraphQLString, description='Object name'),
            'type': GraphQLField(GraphQLString, description='Object type (MESH, LIGHT, CAMERA, etc.)'),
            'location': GraphQLField(vector3_type, description='Object location'),
            'rotation': GraphQLField(vector3_type, description='Object rotation in Euler angles (degrees)'),
            'scale': GraphQLField(vector3_type, description='Object scale'),
            'visible': GraphQLField(GraphQLBoolean, description='Whether the object is visible')
        },
        description='A Blender object'
    )

    # Scene info type
    scene_info_type = GraphQLObjectType(
        name='SceneInfo',
        fields={
            'name': GraphQLField(GraphQLString, description='Scene name'),
            'objects': GraphQLField(
                GraphQLList(blender_object_type),
                description='Objects in the scene'
            ),
            'frame_current': GraphQLField(GraphQLInt, description='Current frame'),
            'frame_start': GraphQLField(GraphQLInt, description='Start frame'),
            'frame_end': GraphQLField(GraphQLInt, description='End frame'),
            'active_object': GraphQLField(GraphQLString, description='Currently active object name')
        },
        description='Information about the current Blender scene'
    )

    # Result types
    operation_result_type = GraphQLObjectType(
        name='OperationResult',
        fields={
            'success': GraphQLField(GraphQLBoolean, description='Whether the operation was successful'),
            'message': GraphQLField(GraphQLString, description='Result message or error description'),
            'error': GraphQLField(GraphQLString, description='Error message if operation failed')
        },
        description='Result of an operation'
    )

    # Object creation result
    create_object_result_type = GraphQLObjectType(
        name='CreateObjectResult',
        fields={
            'success': GraphQLField(GraphQLBoolean, description='Whether the operation was successful'),
            'message': GraphQLField(GraphQLString, description='Result message'),
            'object': GraphQLField(blender_object_type, description='Created object'),
            'error': GraphQLField(GraphQLString, description='Error message if operation failed')
        },
        description='Result of object creation operation'
    )

    # Object type enum
    object_type_enum = GraphQLEnumType(
        name='ObjectType',
        values={
            'MESH': GraphQLField(description='Mesh object'),
            'CURVE': GraphQLField(description='Curve object'),
            'SURFACE': GraphQLField(description='Surface object'),
            'META': GraphQLField(description='Meta object'),
            'FONT': GraphQLField(description='Font object'),
            'ARMATURE': GraphQLField(description='Armature object'),
            'LATTICE': GraphQLField(description='Lattice object'),
            'EMPTY': GraphQLField(description='Empty object'),
            'GPENCIL': GraphQLField(description='Grease Pencil object'),
            'CAMERA': GraphQLField(description='Camera object'),
            'LIGHT': GraphQLField(description='Light object'),
            'SPEAKER': GraphQLField(description='Speaker object'),
            'LIGHT_PROBE': GraphQLField(description='Light Probe object')
        },
        description='Types of Blender objects'
    )

    # Mesh type
    primitive_type_enum = GraphQLEnumType(
        name='PrimitiveType',
        values={
            'CUBE': GraphQLField(description='Cube'),
            'SPHERE': GraphQLField(description='UV Sphere'),
            'ICOSPHERE': GraphQLField(description='Icosphere'),
            'CYLINDER': GraphQLField(description='Cylinder'),
            'CONE': GraphQLField(description='Cone'),
            'TORUS': GraphQLField(description='Torus'),
            'MONKEY': GraphQLField(description='Monkey (Suzanne)'),
            'PLANE': GraphQLField(description='Plane')
        },
        description='Types of primitive mesh objects'
    )

    # VRM model type
    vrm_model_type = GraphQLObjectType(
        name='VrmModel',
        fields={
            'name': GraphQLField(GraphQLString, description='VRM model name'),
            'version': GraphQLField(GraphQLString, description='VRM version'),
            'author': GraphQLField(GraphQLString, description='VRM author'),
            'title': GraphQLField(GraphQLString, description='VRM title'),
            'object_name': GraphQLField(GraphQLString, description='Name of the root object in Blender')
        },
        description='A VRM model'
    )

    # VRM operation result
    vrm_operation_result_type = GraphQLObjectType(
        name='VrmOperationResult',
        fields={
            'success': GraphQLField(GraphQLBoolean, description='Whether the operation was successful'),
            'message': GraphQLField(GraphQLString, description='Result message'),
            'model': GraphQLField(vrm_model_type, description='VRM model'),
            'error': GraphQLField(GraphQLString, description='Error message if operation failed')
        },
        description='Result of a VRM operation'
    )

    # Add the types to the schema builder
    schema_builder.add_object_type('Vector3', vector3_type)
    schema_builder.add_object_type('Vector3Input', vector3_input_type)
    schema_builder.add_object_type('BlenderObject', blender_object_type)
    schema_builder.add_object_type('SceneInfo', scene_info_type)
    schema_builder.add_object_type('OperationResult', operation_result_type)
    schema_builder.add_object_type('CreateObjectResult', create_object_result_type)
    schema_builder.add_object_type('VrmModel', vrm_model_type)
    schema_builder.add_object_type('VrmOperationResult', vrm_operation_result_type)

    # Define basic query fields
    schema_builder.add_query_field(
        'hello',
        GraphQLField(
            GraphQLString,
            description='A simple greeting message',
            resolve=lambda obj, info: 'Hello from Blender GraphQL MCP!'
        )
    )

    schema_builder.add_query_field(
        'sceneInfo',
        GraphQLField(
            scene_info_type,
            description='Get information about the current scene',
            resolve=lambda obj, info: None  # Will be implemented in resolvers.py
        )
    )

    schema_builder.add_query_field(
        'object',
        GraphQLField(
            blender_object_type,
            description='Get information about a specific object',
            args={
                'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='Object name')
            },
            resolve=lambda obj, info, name: None  # Will be implemented in resolvers.py
        )
    )

    # Define basic mutation fields
    schema_builder.add_mutation_field(
        'createObject',
        GraphQLField(
            create_object_result_type,
            description='Create a new object',
            args={
                'type': GraphQLArgument(primitive_type_enum, description='Object primitive type'),
                'name': GraphQLArgument(GraphQLString, description='Object name (optional)'),
                'location': GraphQLArgument(vector3_input_type, description='Object location (optional)')
            },
            resolve=lambda obj, info, **kwargs: None  # Will be implemented in resolvers.py
        )
    )

    schema_builder.add_mutation_field(
        'transformObject',
        GraphQLField(
            operation_result_type,
            description='Transform an existing object',
            args={
                'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='Object name'),
                'location': GraphQLArgument(vector3_input_type, description='New location (optional)'),
                'rotation': GraphQLArgument(vector3_input_type, description='New rotation (optional)'),
                'scale': GraphQLArgument(vector3_input_type, description='New scale (optional)')
            },
            resolve=lambda obj, info, **kwargs: None  # Will be implemented in resolvers.py
        )
    )

    schema_builder.add_mutation_field(
        'deleteObject',
        GraphQLField(
            operation_result_type,
            description='Delete an object',
            args={
                'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='Object name')
            },
            resolve=lambda obj, info, name: None  # Will be implemented in resolvers.py
        )
    )

    # VRM-related mutations
    schema_builder.add_mutation_field(
        'createVrmModel',
        GraphQLField(
            vrm_operation_result_type,
            description='Create a new VRM model',
            args={
                'name': GraphQLArgument(GraphQLNonNull(GraphQLString), description='Model name'),
                'author': GraphQLArgument(GraphQLString, description='Author name (optional)'),
                'title': GraphQLArgument(GraphQLString, description='Model title (optional)')
            },
            resolve=lambda obj, info, **kwargs: None  # Will be implemented in resolvers.py
        )
    )

    # Add LLM-specific helper queries
    # These queries provide additional documentation and schema information
    # specifically designed for LLMs (Large Language Models)

    # _llmFunctionList - Get a list of all available GraphQL functions
    schema_builder.add_query_field(
        '_llmFunctionList',
        GraphQLField(
            GraphQLString,
            description='Get a list of all available GraphQL functions (for LLMs)',
            resolve=lambda obj, info: json.dumps({
                "queries": list(schema_builder.query_fields.keys()),
                "mutations": list(schema_builder.mutation_fields.keys()),
                "description": "This list contains all available GraphQL functions that can be used with this API",
                "usage": "Use _llmFunctionInfo(functionName: \"functionName\") to get detailed information about a specific function"
            }, indent=2)
        )
    )

    # _llmFunctionInfo - Get detailed information about a specific function
    schema_builder.add_query_field(
        '_llmFunctionInfo',
        GraphQLField(
            GraphQLString,
            description='Get detailed information about a specific GraphQL function (for LLMs)',
            args={
                'functionName': GraphQLArgument(GraphQLNonNull(GraphQLString), description='Function name')
            },
            resolve=lambda obj, info, functionName: json.dumps(_generate_function_info(functionName, schema_builder), indent=2)
        )
    )

    # _llmSchemaDoc - Get complete schema documentation in Markdown format
    schema_builder.add_query_field(
        '_llmSchemaDoc',
        GraphQLField(
            GraphQLString,
            description='Get complete schema documentation in Markdown format (for LLMs)',
            resolve=lambda obj, info: _generate_schema_doc(schema_builder)
        )
    )

    # Build the schema
    return schema_builder.build_schema()

def get_schema() -> Optional[GraphQLSchema]:
    """Get the built schema or build it if not already built."""
    return schema_builder.get_schema()