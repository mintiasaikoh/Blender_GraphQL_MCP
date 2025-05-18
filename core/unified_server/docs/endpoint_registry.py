"""
Endpoint registry for unified server.
Provides a central registry for all API endpoints with documentation and metadata.
"""

import logging
from typing import Dict, List, Any, Optional, Callable, Tuple, Set, Union

# Import version manager
from ..api.version_manager import APIVersion, VersionManager, VersionedEndpoint

# Logger
logger = logging.getLogger("unified_server.docs.endpoint_registry")


class EndpointMetadata:
    """
    Metadata for an API endpoint.
    """
    
    def __init__(
        self,
        path: str,
        methods: List[str],
        description: str,
        tags: List[str] = None,
        deprecated: bool = False,
        deprecated_message: Optional[str] = None,
        authentication_required: bool = False,
        permissions_required: List[str] = None,
        rate_limit: Optional[int] = None,
        examples: List[Dict[str, Any]] = None,
        response_schemas: Dict[str, Any] = None
    ):
        """
        Initialize endpoint metadata.
        
        Args:
            path: Endpoint path
            methods: HTTP methods supported by the endpoint
            description: Endpoint description
            tags: Tags for categorizing the endpoint
            deprecated: Whether the endpoint is deprecated
            deprecated_message: Optional message for when a deprecated endpoint is used
            authentication_required: Whether authentication is required
            permissions_required: List of permissions required to access the endpoint
            rate_limit: Optional rate limit for the endpoint (requests per minute)
            examples: Example requests and responses
            response_schemas: Response schemas for different status codes
        """
        self.path = path
        self.methods = methods
        self.description = description
        self.tags = tags or []
        self.deprecated = deprecated
        self.deprecated_message = deprecated_message
        self.authentication_required = authentication_required
        self.permissions_required = permissions_required or []
        self.rate_limit = rate_limit
        self.examples = examples or []
        self.response_schemas = response_schemas or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the endpoint metadata to a dictionary.
        
        Returns:
            Dictionary representation of the metadata
        """
        result = {
            "path": self.path,
            "methods": self.methods,
            "description": self.description,
            "tags": self.tags,
            "deprecated": self.deprecated,
            "authentication_required": self.authentication_required,
            "permissions_required": self.permissions_required
        }
        
        if self.deprecated and self.deprecated_message:
            result["deprecated_message"] = self.deprecated_message
        
        if self.rate_limit:
            result["rate_limit"] = self.rate_limit
        
        if self.examples:
            result["examples"] = self.examples
        
        if self.response_schemas:
            result["response_schemas"] = self.response_schemas
        
        return result


class EndpointRegistry:
    """
    Registry for API endpoints.
    """
    
    # Singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'EndpointRegistry':
        """Get the singleton instance of the endpoint registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the endpoint registry."""
        # Version manager
        self.version_manager = VersionManager.get_instance()
        
        # REST endpoints {path: {method: metadata}}
        self.rest_endpoints: Dict[str, Dict[str, EndpointMetadata]] = {}
        
        # GraphQL operations {operation_name: metadata}
        self.graphql_operations: Dict[str, EndpointMetadata] = {}
    
    def register_rest_endpoint(
        self,
        path: str,
        method: str,
        description: str,
        min_version: str,
        max_version: Optional[str] = None,
        tags: List[str] = None,
        deprecated: bool = False,
        deprecated_message: Optional[str] = None,
        authentication_required: bool = False,
        permissions_required: List[str] = None,
        rate_limit: Optional[int] = None,
        examples: List[Dict[str, Any]] = None,
        response_schemas: Dict[str, Any] = None
    ) -> None:
        """
        Register a REST API endpoint.
        
        Args:
            path: Endpoint path
            method: HTTP method
            description: Endpoint description
            min_version: Minimum API version this endpoint is available in
            max_version: Maximum API version this endpoint is available in
            tags: Tags for categorizing the endpoint
            deprecated: Whether the endpoint is deprecated
            deprecated_message: Optional message for when a deprecated endpoint is used
            authentication_required: Whether authentication is required
            permissions_required: List of permissions required to access the endpoint
            rate_limit: Optional rate limit for the endpoint (requests per minute)
            examples: Example requests and responses
            response_schemas: Response schemas for different status codes
        """
        method = method.upper()
        
        # Create metadata
        metadata = EndpointMetadata(
            path=path,
            methods=[method],
            description=description,
            tags=tags,
            deprecated=deprecated,
            deprecated_message=deprecated_message,
            authentication_required=authentication_required,
            permissions_required=permissions_required,
            rate_limit=rate_limit,
            examples=examples,
            response_schemas=response_schemas
        )
        
        # Register endpoint in version manager
        self.version_manager.register_endpoint(
            endpoint=f"{method}:{path}",
            min_version=min_version,
            max_version=max_version,
            deprecated=deprecated,
            deprecated_message=deprecated_message
        )
        
        # Register endpoint in registry
        if path not in self.rest_endpoints:
            self.rest_endpoints[path] = {}
        
        self.rest_endpoints[path][method] = metadata
        
        logger.debug(f"Registered REST endpoint: {method} {path}")
    
    def register_graphql_operation(
        self,
        operation_name: str,
        operation_type: str,
        description: str,
        min_version: str,
        max_version: Optional[str] = None,
        tags: List[str] = None,
        deprecated: bool = False,
        deprecated_message: Optional[str] = None,
        authentication_required: bool = False,
        permissions_required: List[str] = None,
        rate_limit: Optional[int] = None,
        examples: List[Dict[str, Any]] = None
    ) -> None:
        """
        Register a GraphQL operation.
        
        Args:
            operation_name: Operation name
            operation_type: Operation type (query, mutation, subscription)
            description: Operation description
            min_version: Minimum API version this operation is available in
            max_version: Maximum API version this operation is available in
            tags: Tags for categorizing the operation
            deprecated: Whether the operation is deprecated
            deprecated_message: Optional message for when a deprecated operation is used
            authentication_required: Whether authentication is required
            permissions_required: List of permissions required to access the operation
            rate_limit: Optional rate limit for the operation (requests per minute)
            examples: Example requests and responses
        """
        operation_type = operation_type.lower()
        
        # Create metadata
        metadata = EndpointMetadata(
            path=f"/graphql:{operation_type}:{operation_name}",
            methods=["POST"],
            description=description,
            tags=tags,
            deprecated=deprecated,
            deprecated_message=deprecated_message,
            authentication_required=authentication_required,
            permissions_required=permissions_required,
            rate_limit=rate_limit,
            examples=examples
        )
        
        # Register operation in version manager
        self.version_manager.register_endpoint(
            endpoint=f"graphql:{operation_type}:{operation_name}",
            min_version=min_version,
            max_version=max_version,
            deprecated=deprecated,
            deprecated_message=deprecated_message
        )
        
        # Register operation in registry
        self.graphql_operations[f"{operation_type}:{operation_name}"] = metadata
        
        logger.debug(f"Registered GraphQL operation: {operation_type} {operation_name}")
    
    def get_rest_endpoint(
        self,
        path: str,
        method: str,
        api_version: Union[str, APIVersion] = None
    ) -> Optional[EndpointMetadata]:
        """
        Get metadata for a REST API endpoint.
        
        Args:
            path: Endpoint path
            method: HTTP method
            api_version: Optional API version
            
        Returns:
            Endpoint metadata or None if not found or not available in the requested version
        """
        method = method.upper()
        
        # Check if endpoint exists
        if path not in self.rest_endpoints or method not in self.rest_endpoints[path]:
            return None
        
        # Check if endpoint is available in the requested version
        if api_version:
            endpoint_id = f"{method}:{path}"
            if not self.version_manager.is_endpoint_available(endpoint_id, api_version):
                return None
        
        return self.rest_endpoints[path][method]
    
    def get_graphql_operation(
        self,
        operation_name: str,
        operation_type: str,
        api_version: Union[str, APIVersion] = None
    ) -> Optional[EndpointMetadata]:
        """
        Get metadata for a GraphQL operation.
        
        Args:
            operation_name: Operation name
            operation_type: Operation type (query, mutation, subscription)
            api_version: Optional API version
            
        Returns:
            Operation metadata or None if not found or not available in the requested version
        """
        operation_type = operation_type.lower()
        operation_id = f"{operation_type}:{operation_name}"
        
        # Check if operation exists
        if operation_id not in self.graphql_operations:
            return None
        
        # Check if operation is available in the requested version
        if api_version:
            endpoint_id = f"graphql:{operation_id}"
            if not self.version_manager.is_endpoint_available(endpoint_id, api_version):
                return None
        
        return self.graphql_operations[operation_id]
    
    def get_all_rest_endpoints(
        self,
        api_version: Union[str, APIVersion] = None,
        tags: List[str] = None
    ) -> Dict[str, Dict[str, EndpointMetadata]]:
        """
        Get all REST API endpoints available in the given API version.
        
        Args:
            api_version: Optional API version
            tags: Optional list of tags to filter by
            
        Returns:
            Dictionary with paths as keys and dictionaries of methods and metadata as values
        """
        result = {}
        
        for path, methods in self.rest_endpoints.items():
            result_methods = {}
            
            for method, metadata in methods.items():
                # Check if endpoint is available in the requested version
                if api_version:
                    endpoint_id = f"{method}:{path}"
                    if not self.version_manager.is_endpoint_available(endpoint_id, api_version):
                        continue
                
                # Check if endpoint has the requested tags
                if tags and not any(tag in metadata.tags for tag in tags):
                    continue
                
                result_methods[method] = metadata
            
            if result_methods:
                result[path] = result_methods
        
        return result
    
    def get_all_graphql_operations(
        self,
        api_version: Union[str, APIVersion] = None,
        operation_type: str = None,
        tags: List[str] = None
    ) -> Dict[str, EndpointMetadata]:
        """
        Get all GraphQL operations available in the given API version.
        
        Args:
            api_version: Optional API version
            operation_type: Optional operation type to filter by (query, mutation, subscription)
            tags: Optional list of tags to filter by
            
        Returns:
            Dictionary with operation IDs as keys and metadata as values
        """
        result = {}
        
        for operation_id, metadata in self.graphql_operations.items():
            # Check if operation is of the requested type
            if operation_type:
                if not operation_id.startswith(operation_type.lower() + ":"):
                    continue
            
            # Check if operation is available in the requested version
            if api_version:
                endpoint_id = f"graphql:{operation_id}"
                if not self.version_manager.is_endpoint_available(endpoint_id, api_version):
                    continue
            
            # Check if operation has the requested tags
            if tags and not any(tag in metadata.tags for tag in tags):
                continue
            
            result[operation_id] = metadata
        
        return result
    
    def to_dict(self, api_version: Union[str, APIVersion] = None) -> Dict[str, Any]:
        """
        Convert the registry to a dictionary.
        
        Args:
            api_version: Optional API version to filter by
            
        Returns:
            Dictionary representation of the registry
        """
        result = {
            "rest_endpoints": {},
            "graphql_operations": {}
        }
        
        # REST endpoints
        rest_endpoints = self.get_all_rest_endpoints(api_version)
        for path, methods in rest_endpoints.items():
            result["rest_endpoints"][path] = {}
            for method, metadata in methods.items():
                result["rest_endpoints"][path][method] = metadata.to_dict()
        
        # GraphQL operations
        graphql_operations = self.get_all_graphql_operations(api_version)
        for operation_id, metadata in graphql_operations.items():
            result["graphql_operations"][operation_id] = metadata.to_dict()
        
        return result


# Initialize the endpoint registry
endpoint_registry = EndpointRegistry.get_instance()


class EndpointDocumenter:
    """
    Utility for documenting API endpoints.
    """
    
    @staticmethod
    def document_rest_endpoint(
        path: str,
        method: str,
        description: str,
        min_version: str,
        max_version: Optional[str] = None,
        tags: List[str] = None,
        deprecated: bool = False,
        deprecated_message: Optional[str] = None,
        authentication_required: bool = False,
        permissions_required: List[str] = None,
        rate_limit: Optional[int] = None,
        examples: List[Dict[str, Any]] = None,
        response_schemas: Dict[str, Any] = None
    ) -> None:
        """
        Document a REST API endpoint.
        
        Args:
            path: Endpoint path
            method: HTTP method
            description: Endpoint description
            min_version: Minimum API version this endpoint is available in
            max_version: Maximum API version this endpoint is available in
            tags: Tags for categorizing the endpoint
            deprecated: Whether the endpoint is deprecated
            deprecated_message: Optional message for when a deprecated endpoint is used
            authentication_required: Whether authentication is required
            permissions_required: List of permissions required to access the endpoint
            rate_limit: Optional rate limit for the endpoint (requests per minute)
            examples: Example requests and responses
            response_schemas: Response schemas for different status codes
        """
        # Register endpoint
        endpoint_registry.register_rest_endpoint(
            path=path,
            method=method,
            description=description,
            min_version=min_version,
            max_version=max_version,
            tags=tags,
            deprecated=deprecated,
            deprecated_message=deprecated_message,
            authentication_required=authentication_required,
            permissions_required=permissions_required,
            rate_limit=rate_limit,
            examples=examples,
            response_schemas=response_schemas
        )
    
    @staticmethod
    def document_graphql_operation(
        operation_name: str,
        operation_type: str,
        description: str,
        min_version: str,
        max_version: Optional[str] = None,
        tags: List[str] = None,
        deprecated: bool = False,
        deprecated_message: Optional[str] = None,
        authentication_required: bool = False,
        permissions_required: List[str] = None,
        rate_limit: Optional[int] = None,
        examples: List[Dict[str, Any]] = None
    ) -> None:
        """
        Document a GraphQL operation.
        
        Args:
            operation_name: Operation name
            operation_type: Operation type (query, mutation, subscription)
            description: Operation description
            min_version: Minimum API version this operation is available in
            max_version: Maximum API version this operation is available in
            tags: Tags for categorizing the operation
            deprecated: Whether the operation is deprecated
            deprecated_message: Optional message for when a deprecated operation is used
            authentication_required: Whether authentication is required
            permissions_required: List of permissions required to access the operation
            rate_limit: Optional rate limit for the operation (requests per minute)
            examples: Example requests and responses
        """
        # Register operation
        endpoint_registry.register_graphql_operation(
            operation_name=operation_name,
            operation_type=operation_type,
            description=description,
            min_version=min_version,
            max_version=max_version,
            tags=tags,
            deprecated=deprecated,
            deprecated_message=deprecated_message,
            authentication_required=authentication_required,
            permissions_required=permissions_required,
            rate_limit=rate_limit,
            examples=examples
        )