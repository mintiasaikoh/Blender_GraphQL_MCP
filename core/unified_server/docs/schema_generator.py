"""
Schema generator for unified server documentation.
Provides utilities for generating OpenAPI/Swagger schemas and GraphQL schema documentation.
"""

import json
import logging
import inspect
from typing import Dict, List, Any, Optional, Callable, Tuple, Set, Union, Type
from pathlib import Path

# Import version manager
from ..api.version_manager import APIVersion, VersionManager

# Logger
logger = logging.getLogger("unified_server.docs.schema_generator")


class OpenAPIGenerator:
    """
    Generator for OpenAPI/Swagger schemas.
    """
    
    def __init__(self, server):
        """
        Initialize the OpenAPI generator.
        
        Args:
            server: The UnifiedServer instance
        """
        self.server = server
        self.version_manager = VersionManager.get_instance()
        self.base_info = {
            "openapi": "3.0.0",
            "info": {
                "title": server.config.api_title,
                "description": server.config.api_description,
                "version": server.config.api_version,
                "contact": {
                    "name": "Blender GraphQL MCP Team",
                    "url": "https://github.com/yourusername/blender-graphql-mcp"
                },
                "license": {
                    "name": "GPL-3.0",
                    "url": "https://www.gnu.org/licenses/gpl-3.0.html"
                }
            },
            "servers": [
                {
                    "url": f"http://{server.config.host}:{server.config.port}",
                    "description": "Development server"
                }
            ]
        }
    
    def generate_openapi_schema(self, api_version: Union[str, APIVersion] = None) -> Dict[str, Any]:
        """
        Generate OpenAPI schema for the REST API.
        
        Args:
            api_version: Optional API version to generate schema for
            
        Returns:
            OpenAPI schema as a dictionary
        """
        if api_version is None:
            api_version = self.version_manager.current_version
        elif isinstance(api_version, str):
            api_version = APIVersion(api_version)
        
        # Start with base info
        schema = self.base_info.copy()
        
        # Update version in schema
        schema["info"]["version"] = str(api_version)
        
        # Paths and components
        schema["paths"] = {}
        schema["components"] = {
            "schemas": {},
            "securitySchemes": {}
        }
        
        # Add security schemes if authentication is enabled
        if self.server.config.enable_auth:
            schema["components"]["securitySchemes"] = {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
            schema["security"] = [{"bearerAuth": []}]
        
        # Check if we have a REST API
        if "rest" not in self.server.apis:
            return schema
        
        rest_api = self.server.apis["rest"]
        
        # Extract routes from FastAPI app
        if hasattr(rest_api, "router") and rest_api.router:
            for route in rest_api.router.routes:
                # Skip routes that are not available in the requested version
                if hasattr(route.endpoint, "_endpoint_version_info"):
                    version_info = route.endpoint._endpoint_version_info
                    min_version = APIVersion(version_info["min_version"])
                    
                    if min_version > api_version:
                        continue
                    
                    if version_info["max_version"]:
                        max_version = APIVersion(version_info["max_version"])
                        if api_version > max_version:
                            continue
                
                # Get route path
                path = route.path
                if not path.startswith("/"):
                    path = f"/{path}"
                
                # Initialize path info if not exists
                if path not in schema["paths"]:
                    schema["paths"][path] = {}
                
                # Get HTTP methods
                for method in route.methods:
                    method = method.lower()
                    
                    # Skip HEAD and OPTIONS
                    if method in ["head", "options"]:
                        continue
                    
                    # Get operation info
                    operation = {}
                    operation["tags"] = getattr(route, "tags", ["default"])
                    operation["summary"] = route.name or route.endpoint.__name__
                    
                    # Get docstring for description
                    if route.endpoint.__doc__:
                        operation["description"] = inspect.cleandoc(route.endpoint.__doc__)
                    
                    # Deprecated flag
                    if hasattr(route.endpoint, "_endpoint_version_info"):
                        operation["deprecated"] = route.endpoint._endpoint_version_info["deprecated"]
                    
                    # Parameters
                    operation["parameters"] = []
                    
                    # Request body
                    if method in ["post", "put", "patch"]:
                        if hasattr(route, "body_field"):
                            operation["requestBody"] = {
                                "content": {
                                    "application/json": {
                                        "schema": self._get_model_schema(route.body_field.type_)
                                    }
                                },
                                "required": route.body_field.required
                            }
                    
                    # Responses
                    operation["responses"] = {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {
                                                "type": "boolean",
                                                "description": "Whether the request was successful"
                                            },
                                            "data": {
                                                "type": "object",
                                                "description": "Response data"
                                            },
                                            "metadata": {
                                                "type": "object",
                                                "description": "Metadata about the response"
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Bad request",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {
                                                "type": "boolean",
                                                "description": "Always false for errors"
                                            },
                                            "errors": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "code": {
                                                            "type": "string",
                                                            "description": "Error code"
                                                        },
                                                        "message": {
                                                            "type": "string",
                                                            "description": "Error message"
                                                        },
                                                        "context": {
                                                            "type": "object",
                                                            "description": "Error context"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "500": {
                            "description": "Internal server error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {
                                                "type": "boolean",
                                                "description": "Always false for errors"
                                            },
                                            "errors": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "code": {
                                                            "type": "string",
                                                            "description": "Error code"
                                                        },
                                                        "message": {
                                                            "type": "string",
                                                            "description": "Error message"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    schema["paths"][path][method] = operation
        
        # Add model schemas from REST API models
        if hasattr(rest_api, "model_cache"):
            for model_name, model in rest_api.model_cache.items():
                schema["components"]["schemas"][model_name] = self._get_model_schema(model)
        
        return schema
    
    def save_openapi_schema(self, output_dir: str, api_version: Union[str, APIVersion] = None) -> str:
        """
        Generate OpenAPI schema and save it to a file.
        
        Args:
            output_dir: Directory to save the schema to
            api_version: Optional API version to generate schema for
            
        Returns:
            Path to the saved schema file
        """
        if api_version is None:
            api_version = self.version_manager.current_version
        elif isinstance(api_version, str):
            api_version = APIVersion(api_version)
        
        # Generate schema
        schema = self.generate_openapi_schema(api_version)
        
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save schema to file
        file_path = output_path / f"openapi_{api_version}.json"
        with open(file_path, "w") as f:
            json.dump(schema, f, indent=2)
        
        return str(file_path)
    
    def _get_model_schema(self, model: Type) -> Dict[str, Any]:
        """
        Get OpenAPI schema for a Pydantic model.
        
        Args:
            model: Pydantic model class
            
        Returns:
            OpenAPI schema as a dictionary
        """
        if hasattr(model, "schema") and callable(model.schema):
            return model.schema()
        
        # Fallback for non-Pydantic models
        return {
            "type": "object",
            "properties": {}
        }


class GraphQLSchemaDocGenerator:
    """
    Generator for GraphQL schema documentation.
    """
    
    def __init__(self, server):
        """
        Initialize the GraphQL schema documentation generator.
        
        Args:
            server: The UnifiedServer instance
        """
        self.server = server
        self.version_manager = VersionManager.get_instance()
    
    def generate_schema_doc(self, api_version: Union[str, APIVersion] = None) -> Dict[str, Any]:
        """
        Generate GraphQL schema documentation.
        
        Args:
            api_version: Optional API version to generate schema for
            
        Returns:
            GraphQL schema documentation as a dictionary
        """
        if api_version is None:
            api_version = self.version_manager.current_version
        elif isinstance(api_version, str):
            api_version = APIVersion(api_version)
        
        # Check if we have a GraphQL API
        if "graphql" not in self.server.apis:
            return {}
        
        graphql_api = self.server.apis["graphql"]
        
        # Check if we have a schema
        if not hasattr(graphql_api, "schema") or graphql_api.schema is None:
            return {}
        
        # Get schema
        schema = graphql_api.schema
        
        # Get schema types
        doc = {}
        doc["info"] = {
            "title": self.server.config.api_title,
            "description": self.server.config.api_description,
            "version": str(api_version)
        }
        
        # Query type
        if schema.query_type:
            doc["query"] = self._get_type_doc(schema.query_type)
        
        # Mutation type
        if schema.mutation_type:
            doc["mutation"] = self._get_type_doc(schema.mutation_type)
        
        # Subscription type
        if schema.subscription_type:
            doc["subscription"] = self._get_type_doc(schema.subscription_type)
        
        # Types
        doc["types"] = {}
        for type_name, type_obj in schema.type_map.items():
            # Skip built-in types
            if type_name.startswith("__"):
                continue
            
            # Skip query, mutation, and subscription types
            if (schema.query_type and type_name == schema.query_type.name) or \
               (schema.mutation_type and type_name == schema.mutation_type.name) or \
               (schema.subscription_type and type_name == schema.subscription_type.name):
                continue
            
            doc["types"][type_name] = self._get_type_doc(type_obj)
        
        return doc
    
    def save_schema_doc(self, output_dir: str, api_version: Union[str, APIVersion] = None) -> str:
        """
        Generate GraphQL schema documentation and save it to a file.
        
        Args:
            output_dir: Directory to save the documentation to
            api_version: Optional API version to generate documentation for
            
        Returns:
            Path to the saved documentation file
        """
        if api_version is None:
            api_version = self.version_manager.current_version
        elif isinstance(api_version, str):
            api_version = APIVersion(api_version)
        
        # Generate documentation
        doc = self.generate_schema_doc(api_version)
        
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save documentation to file
        file_path = output_path / f"graphql_schema_{api_version}.json"
        with open(file_path, "w") as f:
            json.dump(doc, f, indent=2)
        
        return str(file_path)
    
    def _get_type_doc(self, type_obj) -> Dict[str, Any]:
        """
        Get documentation for a GraphQL type.
        
        Args:
            type_obj: GraphQL type object
            
        Returns:
            Type documentation as a dictionary
        """
        doc = {
            "name": type_obj.name,
            "description": type_obj.description or ""
        }
        
        # Object type
        if hasattr(type_obj, "fields"):
            doc["fields"] = {}
            for field_name, field_obj in type_obj.fields.items():
                doc["fields"][field_name] = {
                    "type": self._get_field_type_str(field_obj.type),
                    "description": field_obj.description or ""
                }
                
                # Arguments
                if hasattr(field_obj, "args") and field_obj.args:
                    doc["fields"][field_name]["args"] = {}
                    for arg_name, arg_obj in field_obj.args.items():
                        doc["fields"][field_name]["args"][arg_name] = {
                            "type": self._get_field_type_str(arg_obj.type),
                            "description": arg_obj.description or ""
                        }
                        
                        # Default value
                        if hasattr(arg_obj, "default_value") and arg_obj.default_value is not None:
                            doc["fields"][field_name]["args"][arg_name]["defaultValue"] = arg_obj.default_value
        
        # Interface type
        if hasattr(type_obj, "interfaces") and type_obj.interfaces:
            doc["interfaces"] = [interface.name for interface in type_obj.interfaces]
        
        # Enum type
        if hasattr(type_obj, "values") and type_obj.values:
            doc["enumValues"] = {}
            for value_name, value_obj in type_obj.values.items():
                doc["enumValues"][value_name] = {
                    "description": value_obj.description or ""
                }
                
                # Deprecated
                if hasattr(value_obj, "deprecation_reason") and value_obj.deprecation_reason:
                    doc["enumValues"][value_name]["isDeprecated"] = True
                    doc["enumValues"][value_name]["deprecationReason"] = value_obj.deprecation_reason
                else:
                    doc["enumValues"][value_name]["isDeprecated"] = False
        
        # Union type
        if hasattr(type_obj, "types") and type_obj.types:
            doc["possibleTypes"] = [type_.name for type_ in type_obj.types]
        
        # Input object type
        if hasattr(type_obj, "input_fields") and type_obj.input_fields:
            doc["inputFields"] = {}
            for field_name, field_obj in type_obj.input_fields.items():
                doc["inputFields"][field_name] = {
                    "type": self._get_field_type_str(field_obj.type),
                    "description": field_obj.description or ""
                }
                
                # Default value
                if hasattr(field_obj, "default_value") and field_obj.default_value is not None:
                    doc["inputFields"][field_name]["defaultValue"] = field_obj.default_value
        
        return doc
    
    def _get_field_type_str(self, type_obj) -> str:
        """
        Get string representation of a GraphQL field type.
        
        Args:
            type_obj: GraphQL type object
            
        Returns:
            String representation of the type
        """
        # Non-null type
        if hasattr(type_obj, "of_type") and getattr(type_obj, "name") is None:
            if hasattr(type_obj, "of_type") and hasattr(type_obj.of_type, "of_type") and getattr(type_obj.of_type, "name") is None:
                # List of non-null types
                if hasattr(type_obj.of_type.of_type, "of_type"):
                    return f"[{self._get_field_type_str(type_obj.of_type.of_type.of_type)}!]!"
                else:
                    return f"[{type_obj.of_type.of_type.name}!]!"
            elif hasattr(type_obj, "of_type") and hasattr(type_obj.of_type, "of_type"):
                # List of nullable types
                if hasattr(type_obj.of_type, "of_type"):
                    return f"[{self._get_field_type_str(type_obj.of_type.of_type)}]!"
                else:
                    return f"[{type_obj.of_type.name}]!"
            else:
                # Non-null scalar or object type
                return f"{type_obj.of_type.name}!"
        
        # List type
        elif hasattr(type_obj, "of_type") and hasattr(type_obj.of_type, "name"):
            return f"[{type_obj.of_type.name}]"
        
        # List of non-null types
        elif hasattr(type_obj, "of_type") and hasattr(type_obj.of_type, "of_type"):
            return f"[{self._get_field_type_str(type_obj.of_type.of_type)}]"
        
        # Scalar or object type
        else:
            return type_obj.name


def generate_server_documentation(server, output_dir: str) -> Dict[str, str]:
    """
    Generate documentation for the server.
    
    Args:
        server: The UnifiedServer instance
        output_dir: Directory to save documentation to
        
    Returns:
        Dictionary with paths to generated documentation files
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get version manager
    version_manager = VersionManager.get_instance()
    
    # Generators
    openapi_generator = OpenAPIGenerator(server)
    graphql_generator = GraphQLSchemaDocGenerator(server)
    
    # Result paths
    result = {}
    
    # Generate documentation for each supported version
    for version in version_manager.supported_versions:
        version_str = str(version)
        version_dir = output_path / version_str
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # OpenAPI schema
        try:
            openapi_path = openapi_generator.save_openapi_schema(str(version_dir), version)
            result[f"openapi_{version_str}"] = openapi_path
            logger.info(f"Generated OpenAPI schema for version {version_str}: {openapi_path}")
        except Exception as e:
            logger.error(f"Failed to generate OpenAPI schema for version {version_str}: {e}")
        
        # GraphQL schema documentation
        try:
            graphql_path = graphql_generator.save_schema_doc(str(version_dir), version)
            result[f"graphql_{version_str}"] = graphql_path
            logger.info(f"Generated GraphQL schema documentation for version {version_str}: {graphql_path}")
        except Exception as e:
            logger.error(f"Failed to generate GraphQL schema documentation for version {version_str}: {e}")
    
    # Generate documentation index
    index = {
        "server_info": {
            "title": server.config.api_title,
            "description": server.config.api_description,
            "version": server.config.api_version
        },
        "versions": version_manager.get_api_version_info(),
        "documentation": result
    }
    
    # Save index
    index_path = output_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
    
    result["index"] = str(index_path)
    
    return result