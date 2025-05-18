"""
API version management for the unified server.
Provides utilities for versioning APIs and handling backwards compatibility.
"""

import re
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Tuple, Set, Union

# Logger
logger = logging.getLogger("unified_server.api.version_manager")


class APIVersion:
    """
    Represents an API version using semantic versioning (major.minor.patch).
    """
    
    def __init__(self, version_str: str):
        """
        Initialize an API version from a version string.
        
        Args:
            version_str: Version string in the format "major.minor.patch"
        
        Raises:
            ValueError: If the version string is not in the correct format
        """
        pattern = r"^(\d+)\.(\d+)\.(\d+)$"
        match = re.match(pattern, version_str)
        
        if not match:
            raise ValueError(
                f"Invalid version string: {version_str}. Expected format: major.minor.patch"
            )
        
        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.patch = int(match.group(3))
        self._version_str = version_str
    
    def __str__(self) -> str:
        """Get version string."""
        return self._version_str
    
    def __repr__(self) -> str:
        """Get representation."""
        return f"APIVersion({self._version_str})"
    
    def __eq__(self, other: object) -> bool:
        """Check if versions are equal."""
        if not isinstance(other, APIVersion):
            return NotImplemented
        
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch
        )
    
    def __lt__(self, other: 'APIVersion') -> bool:
        """Check if this version is less than the other version."""
        if self.major != other.major:
            return self.major < other.major
        
        if self.minor != other.minor:
            return self.minor < other.minor
        
        return self.patch < other.patch
    
    def __le__(self, other: 'APIVersion') -> bool:
        """Check if this version is less than or equal to the other version."""
        return self < other or self == other
    
    def __gt__(self, other: 'APIVersion') -> bool:
        """Check if this version is greater than the other version."""
        return not (self <= other)
    
    def __ge__(self, other: 'APIVersion') -> bool:
        """Check if this version is greater than or equal to the other version."""
        return not (self < other)
    
    def is_compatible_with(self, other: 'APIVersion') -> bool:
        """
        Check if this version is compatible with the other version.
        Compatibility is defined as having the same major version.
        
        Args:
            other: The other API version to check compatibility with
            
        Returns:
            True if the versions are compatible, False otherwise
        """
        return self.major == other.major


class VersionedEndpoint:
    """
    Represents an API endpoint with version information.
    """
    
    def __init__(
        self,
        endpoint: str,
        min_version: APIVersion,
        max_version: Optional[APIVersion] = None,
        deprecated: bool = False,
        deprecated_message: Optional[str] = None,
        alternatives: Optional[List[str]] = None
    ):
        """
        Initialize a versioned endpoint.
        
        Args:
            endpoint: Endpoint path
            min_version: Minimum API version this endpoint is available in
            max_version: Maximum API version this endpoint is available in (None for no maximum)
            deprecated: Whether this endpoint is deprecated
            deprecated_message: Optional message for when a deprecated endpoint is used
            alternatives: Optional list of alternative endpoints to use instead
        """
        self.endpoint = endpoint
        self.min_version = min_version
        self.max_version = max_version
        self.deprecated = deprecated
        self.deprecated_message = deprecated_message
        self.alternatives = alternatives or []
    
    def is_available_in(self, version: APIVersion) -> bool:
        """
        Check if this endpoint is available in the given API version.
        
        Args:
            version: API version to check
            
        Returns:
            True if the endpoint is available, False otherwise
        """
        if version < self.min_version:
            return False
        
        if self.max_version and version > self.max_version:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the versioned endpoint to a dictionary.
        
        Returns:
            Dictionary representation of the endpoint
        """
        result = {
            "endpoint": self.endpoint,
            "min_version": str(self.min_version),
            "deprecated": self.deprecated
        }
        
        if self.max_version:
            result["max_version"] = str(self.max_version)
        
        if self.deprecated and self.deprecated_message:
            result["deprecated_message"] = self.deprecated_message
        
        if self.alternatives:
            result["alternatives"] = self.alternatives
        
        return result


class VersionManager:
    """
    Manages API versions and versioned endpoints.
    """
    
    # Singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'VersionManager':
        """Get the singleton instance of the version manager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the version manager."""
        # Current API version
        self.current_version = APIVersion("1.0.0")
        
        # Supported API versions (oldest to newest)
        self.supported_versions = [
            APIVersion("1.0.0")
        ]
        
        # Versioned endpoints {endpoint_path: VersionedEndpoint}
        self.endpoints: Dict[str, VersionedEndpoint] = {}
        
        # Endpoint aliases for backward compatibility
        self.endpoint_aliases: Dict[str, str] = {}
        
        # Schema version handlers
        self.schema_version_handlers: Dict[str, Dict[APIVersion, Callable]] = {
            "graphql": {},
            "rest": {}
        }
    
    def register_endpoint(
        self,
        endpoint: str,
        min_version: str,
        max_version: Optional[str] = None,
        deprecated: bool = False,
        deprecated_message: Optional[str] = None,
        alternatives: Optional[List[str]] = None
    ) -> VersionedEndpoint:
        """
        Register a versioned endpoint.
        
        Args:
            endpoint: Endpoint path
            min_version: Minimum API version this endpoint is available in
            max_version: Maximum API version this endpoint is available in (None for no maximum)
            deprecated: Whether this endpoint is deprecated
            deprecated_message: Optional message for when a deprecated endpoint is used
            alternatives: Optional list of alternative endpoints to use instead
            
        Returns:
            The registered versioned endpoint
        """
        min_ver = APIVersion(min_version)
        max_ver = APIVersion(max_version) if max_version else None
        
        versioned_endpoint = VersionedEndpoint(
            endpoint=endpoint,
            min_version=min_ver,
            max_version=max_ver,
            deprecated=deprecated,
            deprecated_message=deprecated_message,
            alternatives=alternatives
        )
        
        self.endpoints[endpoint] = versioned_endpoint
        return versioned_endpoint
    
    def register_endpoint_alias(self, alias: str, target: str) -> None:
        """
        Register an endpoint alias for backward compatibility.
        
        Args:
            alias: Alias endpoint path
            target: Target endpoint path
        """
        if target not in self.endpoints:
            logger.warning(f"Registering alias {alias} for non-existent endpoint {target}")
        
        self.endpoint_aliases[alias] = target
    
    def is_endpoint_available(self, endpoint: str, version: Union[APIVersion, str]) -> bool:
        """
        Check if an endpoint is available in the given API version.
        
        Args:
            endpoint: Endpoint path
            version: API version to check
            
        Returns:
            True if the endpoint is available, False otherwise
        """
        if isinstance(version, str):
            version = APIVersion(version)
        
        # Check if the endpoint exists
        if endpoint in self.endpoints:
            versioned_endpoint = self.endpoints[endpoint]
            return versioned_endpoint.is_available_in(version)
        
        # Check if there's an alias for the endpoint
        if endpoint in self.endpoint_aliases:
            target = self.endpoint_aliases[endpoint]
            return self.is_endpoint_available(target, version)
        
        return False
    
    def get_endpoint_info(
        self, 
        endpoint: str, 
        version: Union[APIVersion, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Get information about an endpoint in the given API version.
        
        Args:
            endpoint: Endpoint path
            version: API version to check
            
        Returns:
            Dictionary with endpoint information or None if the endpoint is not available
        """
        if isinstance(version, str):
            version = APIVersion(version)
        
        # Check if the endpoint exists
        if endpoint in self.endpoints:
            versioned_endpoint = self.endpoints[endpoint]
            
            if versioned_endpoint.is_available_in(version):
                result = versioned_endpoint.to_dict()
                
                # Add version specific information
                result["available_in_version"] = True
                
                if versioned_endpoint.deprecated:
                    result["deprecated"] = True
                    
                    if versioned_endpoint.deprecated_message:
                        result["deprecated_message"] = versioned_endpoint.deprecated_message
                    
                    if versioned_endpoint.alternatives:
                        result["alternatives"] = versioned_endpoint.alternatives
                
                return result
        
        # Check if there's an alias for the endpoint
        if endpoint in self.endpoint_aliases:
            target = self.endpoint_aliases[endpoint]
            info = self.get_endpoint_info(target, version)
            
            if info:
                info["is_alias"] = True
                info["alias_target"] = target
                return info
        
        return None
    
    def get_available_endpoints(self, version: Union[APIVersion, str]) -> List[Dict[str, Any]]:
        """
        Get all endpoints available in the given API version.
        
        Args:
            version: API version to check
            
        Returns:
            List of dictionaries with endpoint information
        """
        if isinstance(version, str):
            version = APIVersion(version)
        
        result = []
        
        # Add all available endpoints
        for endpoint_path, versioned_endpoint in self.endpoints.items():
            if versioned_endpoint.is_available_in(version):
                endpoint_info = versioned_endpoint.to_dict()
                endpoint_info["available_in_version"] = True
                result.append(endpoint_info)
        
        # Add all aliases pointing to available endpoints
        for alias, target in self.endpoint_aliases.items():
            if target in self.endpoints and self.endpoints[target].is_available_in(version):
                # Skip if the alias is already a known endpoint
                if alias in self.endpoints:
                    continue
                
                endpoint_info = self.endpoints[target].to_dict()
                endpoint_info["endpoint"] = alias
                endpoint_info["is_alias"] = True
                endpoint_info["alias_target"] = target
                endpoint_info["available_in_version"] = True
                result.append(endpoint_info)
        
        return result
    
    def register_schema_version_handler(
        self,
        api_type: str,
        version: str,
        handler: Callable
    ) -> None:
        """
        Register a schema version handler for a specific API type and version.
        
        Args:
            api_type: API type (e.g., "graphql", "rest")
            version: API version string
            handler: Handler function that returns the schema for the given version
        """
        if api_type not in self.schema_version_handlers:
            self.schema_version_handlers[api_type] = {}
        
        self.schema_version_handlers[api_type][APIVersion(version)] = handler
    
    def get_schema(self, api_type: str, version: Union[APIVersion, str]) -> Optional[Any]:
        """
        Get the schema for a specific API type and version.
        
        Args:
            api_type: API type (e.g., "graphql", "rest")
            version: API version
            
        Returns:
            Schema for the given API type and version, or None if not available
        """
        if isinstance(version, str):
            version = APIVersion(version)
        
        if api_type not in self.schema_version_handlers:
            return None
        
        # Find the highest version that is less than or equal to the requested version
        compatible_versions = [
            v for v in self.schema_version_handlers[api_type].keys()
            if v <= version and v.is_compatible_with(version)
        ]
        
        if not compatible_versions:
            return None
        
        highest_compatible_version = max(compatible_versions)
        handler = self.schema_version_handlers[api_type][highest_compatible_version]
        
        return handler()
    
    def get_api_version_info(self) -> Dict[str, Any]:
        """
        Get information about the API version.
        
        Returns:
            Dictionary with API version information
        """
        return {
            "current_version": str(self.current_version),
            "supported_versions": [str(v) for v in self.supported_versions],
            "deprecated_versions": [
                str(v) for v in self.supported_versions 
                if v < self.current_version and v.major == self.current_version.major
            ]
        }


# Decorator for versioned endpoints
def versioned_endpoint(
    min_version: str,
    max_version: Optional[str] = None,
    deprecated: bool = False,
    deprecated_message: Optional[str] = None,
    alternatives: Optional[List[str]] = None
):
    """
    Decorator to mark an endpoint handler with version information.
    
    Args:
        min_version: Minimum API version this endpoint is available in
        max_version: Maximum API version this endpoint is available in (None for no maximum)
        deprecated: Whether this endpoint is deprecated
        deprecated_message: Optional message for when a deprecated endpoint is used
        alternatives: Optional list of alternative endpoints to use instead
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        # Store version information in the function's metadata
        func._endpoint_version_info = {
            "min_version": min_version,
            "max_version": max_version,
            "deprecated": deprecated,
            "deprecated_message": deprecated_message,
            "alternatives": alternatives
        }
        
        # If the endpoint is deprecated, add a warning when it's called
        if deprecated:
            original_func = func
            
            async def wrapped_func(*args, **kwargs):
                warning_msg = deprecated_message or f"Endpoint {func.__name__} is deprecated"
                
                if alternatives:
                    alt_str = ", ".join(alternatives)
                    warning_msg += f". Use {alt_str} instead"
                
                logger.warning(warning_msg)
                return await original_func(*args, **kwargs)
            
            return wrapped_func
        
        return func
    
    return decorator


# Initialize the version manager
version_manager = VersionManager.get_instance()