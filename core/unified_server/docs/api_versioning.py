"""
API versioning utilities for the unified server.
Provides tools for managing API versions and ensuring backward compatibility.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from pathlib import Path

# Import version manager
from ..api.version_manager import APIVersion, VersionManager

# Logger
logger = logging.getLogger("unified_server.docs.api_versioning")


class APIChangeTracker:
    """
    Tracks changes between API versions to help with backwards compatibility.
    """
    
    def __init__(self, version_manager: Optional[VersionManager] = None):
        """
        Initialize the API change tracker.
        
        Args:
            version_manager: The version manager instance
        """
        self.version_manager = version_manager or VersionManager.get_instance()
        
        # Breaking changes between API versions
        self.breaking_changes: Dict[str, List[Dict[str, Any]]] = {}
        
        # Deprecated endpoints and schemas
        self.deprecated_endpoints: Dict[str, Dict[str, Any]] = {}
        self.deprecated_schemas: Dict[str, Dict[str, Any]] = {}
        
        # Migration paths between versions
        self.migration_paths: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    
    def register_breaking_change(
        self,
        from_version: Union[str, APIVersion],
        to_version: Union[str, APIVersion],
        change_type: str,
        change_description: str,
        affected_endpoints: List[str],
        migration_guide: Optional[str] = None
    ) -> None:
        """
        Register a breaking change between API versions.
        
        Args:
            from_version: Source API version
            to_version: Target API version
            change_type: Type of breaking change (e.g., "removed", "renamed", "parameter_changed")
            change_description: Description of the breaking change
            affected_endpoints: List of affected endpoints
            migration_guide: Optional guide on how to migrate
        """
        if isinstance(from_version, str):
            from_version = APIVersion(from_version)
        
        if isinstance(to_version, str):
            to_version = APIVersion(to_version)
        
        # Create key for the breaking changes dictionary
        key = f"{from_version}->{to_version}"
        
        # Create change entry
        change = {
            "type": change_type,
            "description": change_description,
            "affected_endpoints": affected_endpoints,
            "migration_guide": migration_guide
        }
        
        # Add to breaking changes
        if key not in self.breaking_changes:
            self.breaking_changes[key] = []
        
        self.breaking_changes[key].append(change)
        
        # Log the breaking change
        logger.info(f"Registered breaking change from {from_version} to {to_version}: {change_description}")
    
    def deprecate_endpoint(
        self,
        endpoint: str,
        deprecated_in_version: Union[str, APIVersion],
        removed_in_version: Optional[Union[str, APIVersion]] = None,
        replacement_endpoint: Optional[str] = None,
        migration_guide: Optional[str] = None
    ) -> None:
        """
        Mark an endpoint as deprecated.
        
        Args:
            endpoint: Endpoint to deprecate
            deprecated_in_version: Version when the endpoint was deprecated
            removed_in_version: Optional version when the endpoint will be removed
            replacement_endpoint: Optional replacement endpoint
            migration_guide: Optional guide on how to migrate
        """
        if isinstance(deprecated_in_version, str):
            deprecated_in_version = APIVersion(deprecated_in_version)
        
        if removed_in_version and isinstance(removed_in_version, str):
            removed_in_version = APIVersion(removed_in_version)
        
        # Create deprecation entry
        deprecation = {
            "deprecated_in_version": str(deprecated_in_version),
            "removed_in_version": str(removed_in_version) if removed_in_version else None,
            "replacement_endpoint": replacement_endpoint,
            "migration_guide": migration_guide
        }
        
        # Add to deprecated endpoints
        self.deprecated_endpoints[endpoint] = deprecation
        
        # Register with version manager
        self.version_manager.register_endpoint(
            endpoint=endpoint,
            min_version="1.0.0",  # Assuming it was available since the beginning
            max_version=str(removed_in_version) if removed_in_version else None,
            deprecated=True,
            deprecated_message=f"Deprecated in {deprecated_in_version}, use {replacement_endpoint} instead",
            alternatives=[replacement_endpoint] if replacement_endpoint else []
        )
        
        # Log the deprecation
        logger.info(f"Marked endpoint {endpoint} as deprecated in version {deprecated_in_version}")
    
    def deprecate_schema(
        self,
        schema_name: str,
        deprecated_in_version: Union[str, APIVersion],
        removed_in_version: Optional[Union[str, APIVersion]] = None,
        replacement_schema: Optional[str] = None,
        migration_guide: Optional[str] = None
    ) -> None:
        """
        Mark a schema as deprecated.
        
        Args:
            schema_name: Schema to deprecate
            deprecated_in_version: Version when the schema was deprecated
            removed_in_version: Optional version when the schema will be removed
            replacement_schema: Optional replacement schema
            migration_guide: Optional guide on how to migrate
        """
        if isinstance(deprecated_in_version, str):
            deprecated_in_version = APIVersion(deprecated_in_version)
        
        if removed_in_version and isinstance(removed_in_version, str):
            removed_in_version = APIVersion(removed_in_version)
        
        # Create deprecation entry
        deprecation = {
            "deprecated_in_version": str(deprecated_in_version),
            "removed_in_version": str(removed_in_version) if removed_in_version else None,
            "replacement_schema": replacement_schema,
            "migration_guide": migration_guide
        }
        
        # Add to deprecated schemas
        self.deprecated_schemas[schema_name] = deprecation
        
        # Log the deprecation
        logger.info(f"Marked schema {schema_name} as deprecated in version {deprecated_in_version}")
    
    def add_migration_path(
        self,
        from_version: Union[str, APIVersion],
        to_version: Union[str, APIVersion],
        steps: List[Dict[str, Any]]
    ) -> None:
        """
        Add a migration path between API versions.
        
        Args:
            from_version: Source API version
            to_version: Target API version
            steps: List of migration steps
        """
        if isinstance(from_version, str):
            from_version = APIVersion(from_version)
        
        if isinstance(to_version, str):
            to_version = APIVersion(to_version)
        
        # Create key for the migration paths dictionary
        key = (str(from_version), str(to_version))
        
        # Add to migration paths
        self.migration_paths[key] = steps
        
        # Log the migration path
        logger.info(f"Added migration path from {from_version} to {to_version} with {len(steps)} steps")
    
    def get_breaking_changes(
        self,
        from_version: Union[str, APIVersion],
        to_version: Union[str, APIVersion]
    ) -> List[Dict[str, Any]]:
        """
        Get breaking changes between API versions.
        
        Args:
            from_version: Source API version
            to_version: Target API version
            
        Returns:
            List of breaking changes
        """
        if isinstance(from_version, str):
            from_version = APIVersion(from_version)
        
        if isinstance(to_version, str):
            to_version = APIVersion(to_version)
        
        # Create key for the breaking changes dictionary
        key = f"{from_version}->{to_version}"
        
        # Return breaking changes if available
        return self.breaking_changes.get(key, [])
    
    def is_endpoint_deprecated(
        self,
        endpoint: str,
        version: Union[str, APIVersion]
    ) -> bool:
        """
        Check if an endpoint is deprecated in the given version.
        
        Args:
            endpoint: Endpoint to check
            version: API version to check
            
        Returns:
            True if the endpoint is deprecated, False otherwise
        """
        if isinstance(version, str):
            version = APIVersion(version)
        
        # Check if endpoint is deprecated
        if endpoint in self.deprecated_endpoints:
            deprecated_in_version = APIVersion(self.deprecated_endpoints[endpoint]["deprecated_in_version"])
            removed_in_version = None
            
            if self.deprecated_endpoints[endpoint]["removed_in_version"]:
                removed_in_version = APIVersion(self.deprecated_endpoints[endpoint]["removed_in_version"])
            
            # Check if the endpoint is deprecated in the given version
            if version >= deprecated_in_version:
                # Check if the endpoint is removed in the given version
                if removed_in_version and version >= removed_in_version:
                    return False  # Endpoint is removed, not deprecated
                
                return True  # Endpoint is deprecated
        
        return False  # Endpoint is not deprecated
    
    def get_migration_path(
        self,
        from_version: Union[str, APIVersion],
        to_version: Union[str, APIVersion]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get migration path between API versions.
        
        Args:
            from_version: Source API version
            to_version: Target API version
            
        Returns:
            Migration path if available, None otherwise
        """
        if isinstance(from_version, str):
            from_version = APIVersion(from_version)
        
        if isinstance(to_version, str):
            to_version = APIVersion(to_version)
        
        # Create key for the migration paths dictionary
        key = (str(from_version), str(to_version))
        
        # Return migration path if available
        return self.migration_paths.get(key)
    
    def get_upgrade_path(
        self,
        from_version: Union[str, APIVersion],
        to_version: Union[str, APIVersion]
    ) -> Optional[List[APIVersion]]:
        """
        Get upgrade path between API versions.
        This returns a list of intermediate versions that should be used to upgrade.
        
        Args:
            from_version: Source API version
            to_version: Target API version
            
        Returns:
            List of intermediate versions if available, None otherwise
        """
        if isinstance(from_version, str):
            from_version = APIVersion(from_version)
        
        if isinstance(to_version, str):
            to_version = APIVersion(to_version)
        
        # Get supported versions in order
        versions = sorted(self.version_manager.supported_versions)
        
        # Find indices of from_version and to_version
        from_index = -1
        to_index = -1
        
        for i, version in enumerate(versions):
            if version == from_version:
                from_index = i
            
            if version == to_version:
                to_index = i
        
        # Check if versions are found
        if from_index == -1 or to_index == -1:
            return None
        
        # Check if from_version is newer than to_version
        if from_index > to_index:
            return None
        
        # Return intermediate versions (including from_version and to_version)
        return versions[from_index:to_index + 1]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert API change tracker to a dictionary.
        
        Returns:
            Dictionary representation of the API change tracker
        """
        return {
            "breaking_changes": self.breaking_changes,
            "deprecated_endpoints": self.deprecated_endpoints,
            "deprecated_schemas": self.deprecated_schemas,
            "migration_paths": {
                f"{from_version}->{to_version}": steps
                for (from_version, to_version), steps in self.migration_paths.items()
            }
        }
    
    def save(self, file_path: str) -> None:
        """
        Save API change tracker to a file.
        
        Args:
            file_path: Path to save the API change tracker
        """
        # Create directory if it doesn't exist
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        
        logger.info(f"Saved API change tracker to {file_path}")
    
    @classmethod
    def load(cls, file_path: str) -> 'APIChangeTracker':
        """
        Load API change tracker from a file.
        
        Args:
            file_path: Path to load the API change tracker from
            
        Returns:
            Loaded API change tracker
        """
        # Create instance
        change_tracker = cls()
        
        # Load from file
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Load breaking changes
        for key, changes in data.get("breaking_changes", {}).items():
            from_version, to_version = key.split("->")
            change_tracker.breaking_changes[key] = changes
        
        # Load deprecated endpoints
        change_tracker.deprecated_endpoints = data.get("deprecated_endpoints", {})
        
        # Load deprecated schemas
        change_tracker.deprecated_schemas = data.get("deprecated_schemas", {})
        
        # Load migration paths
        for key, steps in data.get("migration_paths", {}).items():
            from_version, to_version = key.split("->")
            change_tracker.migration_paths[(from_version, to_version)] = steps
        
        logger.info(f"Loaded API change tracker from {file_path}")
        
        return change_tracker


class APIVersionConstraint:
    """
    Represents a version constraint for API compatibility.
    """
    
    def __init__(self, constraint_str: str):
        """
        Initialize an API version constraint from a constraint string.
        The constraint string can be:
        - ">=1.0.0": Greater than or equal to version 1.0.0
        - "<=2.0.0": Less than or equal to version 2.0.0
        - ">1.0.0": Greater than version 1.0.0
        - "<2.0.0": Less than version 2.0.0
        - "=1.0.0": Equal to version 1.0.0
        - "1.0.0": Equal to version 1.0.0
        - ">=1.0.0,<2.0.0": Greater than or equal to version 1.0.0 and less than version 2.0.0
        
        Args:
            constraint_str: Version constraint string
        
        Raises:
            ValueError: If the constraint string is not in the correct format
        """
        self.constraint_str = constraint_str
        self.constraints = []
        
        # Split by comma
        parts = constraint_str.split(",")
        
        for part in parts:
            # Parse constraint
            part = part.strip()
            
            # Check if it's a version constraint
            if re.match(r"^[<>=]+\d+\.\d+\.\d+$", part):
                # Extract operator and version
                operator = re.match(r"^([<>=]+)", part).group(1)
                version_str = part[len(operator):]
                
                self.constraints.append((operator, APIVersion(version_str)))
            else:
                # Check if it's just a version
                if re.match(r"^\d+\.\d+\.\d+$", part):
                    self.constraints.append(("=", APIVersion(part)))
                else:
                    raise ValueError(f"Invalid version constraint: {part}")
    
    def __str__(self) -> str:
        """Get constraint string."""
        return self.constraint_str
    
    def __repr__(self) -> str:
        """Get representation."""
        return f"APIVersionConstraint({self.constraint_str})"
    
    def is_satisfied_by(self, version: Union[str, APIVersion]) -> bool:
        """
        Check if the given version satisfies the constraint.
        
        Args:
            version: API version to check
            
        Returns:
            True if the version satisfies the constraint, False otherwise
        """
        if isinstance(version, str):
            version = APIVersion(version)
        
        # Check each constraint
        for operator, constraint_version in self.constraints:
            if operator == ">=":
                if not version >= constraint_version:
                    return False
            elif operator == "<=":
                if not version <= constraint_version:
                    return False
            elif operator == ">":
                if not version > constraint_version:
                    return False
            elif operator == "<":
                if not version < constraint_version:
                    return False
            elif operator == "=":
                if not version == constraint_version:
                    return False
        
        return True


class APICompatibilityChecker:
    """
    Checks API compatibility between different versions.
    """
    
    def __init__(
        self,
        version_manager: Optional[VersionManager] = None,
        change_tracker: Optional[APIChangeTracker] = None
    ):
        """
        Initialize the API compatibility checker.
        
        Args:
            version_manager: The version manager instance
            change_tracker: The API change tracker instance
        """
        self.version_manager = version_manager or VersionManager.get_instance()
        self.change_tracker = change_tracker or APIChangeTracker()
    
    def check_endpoint_compatibility(
        self,
        endpoint: str,
        from_version: Union[str, APIVersion],
        to_version: Union[str, APIVersion]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if an endpoint is compatible between API versions.
        
        Args:
            endpoint: Endpoint to check
            from_version: Source API version
            to_version: Target API version
            
        Returns:
            Tuple of (compatible, reason)
        """
        if isinstance(from_version, str):
            from_version = APIVersion(from_version)
        
        if isinstance(to_version, str):
            to_version = APIVersion(to_version)
        
        # Check if the endpoint is available in the source version
        if not self.version_manager.is_endpoint_available(endpoint, from_version):
            return False, f"Endpoint {endpoint} is not available in version {from_version}"
        
        # Check if the endpoint is available in the target version
        if not self.version_manager.is_endpoint_available(endpoint, to_version):
            return False, f"Endpoint {endpoint} is not available in version {to_version}"
        
        # Check if the endpoint has breaking changes
        breaking_changes = self.change_tracker.get_breaking_changes(from_version, to_version)
        
        for change in breaking_changes:
            if endpoint in change["affected_endpoints"]:
                return False, f"Endpoint {endpoint} has breaking changes: {change['description']}"
        
        return True, None
    
    def check_client_compatibility(
        self,
        client_version: Union[str, APIVersion],
        server_version: Union[str, APIVersion],
        used_endpoints: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Check if a client is compatible with a server.
        
        Args:
            client_version: Client API version
            server_version: Server API version
            used_endpoints: Optional list of endpoints used by the client
            
        Returns:
            Tuple of (compatible, incompatible_endpoints)
        """
        if isinstance(client_version, str):
            client_version = APIVersion(client_version)
        
        if isinstance(server_version, str):
            server_version = APIVersion(server_version)
        
        # Check if the server version is compatible with the client version
        if client_version.major != server_version.major:
            return False, ["Major version mismatch"]
        
        # If client is newer than server, then it might use endpoints not available in the server
        if client_version > server_version:
            return False, ["Client version is newer than server version"]
        
        # Check if the client uses endpoints that have breaking changes
        incompatible_endpoints = []
        
        if used_endpoints:
            for endpoint in used_endpoints:
                compatible, reason = self.check_endpoint_compatibility(endpoint, client_version, server_version)
                
                if not compatible:
                    incompatible_endpoints.append(f"{endpoint}: {reason}")
        
        return len(incompatible_endpoints) == 0, incompatible_endpoints
    
    def get_required_server_version(
        self,
        client_version: Union[str, APIVersion],
        used_endpoints: Optional[List[str]] = None
    ) -> APIVersion:
        """
        Get the minimum server version required for a client.
        
        Args:
            client_version: Client API version
            used_endpoints: Optional list of endpoints used by the client
            
        Returns:
            Minimum required server version
        """
        if isinstance(client_version, str):
            client_version = APIVersion(client_version)
        
        # Get all supported versions
        versions = sorted(self.version_manager.supported_versions)
        
        # Filter versions with the same major version as the client
        versions = [v for v in versions if v.major == client_version.major]
        
        # Find the first version that is compatible with the client
        for version in versions:
            if version >= client_version:
                compatible, _ = self.check_client_compatibility(client_version, version, used_endpoints)
                
                if compatible:
                    return version
        
        # If no compatible version is found, return the client version
        return client_version
    
    def get_compatibility_report(
        self,
        client_version: Union[str, APIVersion],
        server_version: Union[str, APIVersion],
        used_endpoints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get a compatibility report between a client and a server.
        
        Args:
            client_version: Client API version
            server_version: Server API version
            used_endpoints: Optional list of endpoints used by the client
            
        Returns:
            Compatibility report
        """
        if isinstance(client_version, str):
            client_version = APIVersion(client_version)
        
        if isinstance(server_version, str):
            server_version = APIVersion(server_version)
        
        # Check compatibility
        compatible, incompatible_endpoints = self.check_client_compatibility(
            client_version, server_version, used_endpoints
        )
        
        # Get required server version
        required_server_version = self.get_required_server_version(client_version, used_endpoints)
        
        # Get upgrade path
        upgrade_path = self.change_tracker.get_upgrade_path(client_version, server_version)
        
        # Create report
        report = {
            "client_version": str(client_version),
            "server_version": str(server_version),
            "compatible": compatible,
            "incompatible_endpoints": incompatible_endpoints,
            "required_server_version": str(required_server_version),
            "upgrade_path": [str(v) for v in upgrade_path] if upgrade_path else None,
            "migration_recommendations": []
        }
        
        # Add migration recommendations
        if not compatible and upgrade_path and len(upgrade_path) > 2:
            # There are intermediate versions
            for i in range(len(upgrade_path) - 1):
                from_version = upgrade_path[i]
                to_version = upgrade_path[i + 1]
                
                migration_path = self.change_tracker.get_migration_path(from_version, to_version)
                
                if migration_path:
                    report["migration_recommendations"].append({
                        "from_version": str(from_version),
                        "to_version": str(to_version),
                        "migration_path": migration_path
                    })
        
        return report