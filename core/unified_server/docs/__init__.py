"""
Documentation package for the unified server.
Provides utilities for generating and serving API documentation.
"""

from .endpoint_registry import (
    EndpointRegistry, EndpointMetadata, EndpointDocumenter,
    endpoint_registry
)
from .schema_generator import (
    OpenAPIGenerator, GraphQLSchemaDocGenerator,
    generate_server_documentation
)

__all__ = [
    "EndpointRegistry", "EndpointMetadata", "EndpointDocumenter",
    "endpoint_registry", "OpenAPIGenerator", "GraphQLSchemaDocGenerator",
    "generate_server_documentation"
]