"""
Server configuration module for Blender GraphQL MCP unified server.
Provides a flexible configuration system for server settings.
"""

import os
import logging
from typing import List, Optional, Dict, Any, Union


class ServerConfig:
    """
    Configuration options for UnifiedServer.
    Provides settings for host, port, logging, API features, and more.
    """
    
    def __init__(self, **kwargs):
        # Server settings
        self.host: str = kwargs.get('host', 'localhost')
        self.port: int = kwargs.get('port', 8000)
        self.workers: int = kwargs.get('workers', 1)
        self.timeout: int = kwargs.get('timeout', 60)
        
        # Logging settings
        self.log_dir: str = kwargs.get('log_dir', os.path.expanduser("~/blender_graphql_mcp_logs"))
        self.log_file: Optional[str] = kwargs.get('log_file', None)
        self.log_level: Union[str, int] = kwargs.get('log_level', logging.INFO)
        self.log_format: str = kwargs.get('log_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # API settings
        self.api_title: str = kwargs.get('api_title', 'Blender GraphQL MCP API')
        self.api_description: str = kwargs.get('api_description', 'GraphQL and REST API for Blender')
        self.api_version: str = kwargs.get('api_version', '1.0.0')
        self.api_prefix: str = kwargs.get('api_prefix', '/api/v1')
        
        # Feature flags
        self.enable_graphql: bool = kwargs.get('enable_graphql', True)
        self.enable_rest: bool = kwargs.get('enable_rest', True)
        self.enable_admin: bool = kwargs.get('enable_admin', False)
        self.enable_docs: bool = kwargs.get('enable_docs', True)
        self.enable_graphiql: bool = kwargs.get('enable_graphiql', True)
        
        # Security settings
        self.enable_cors: bool = kwargs.get('enable_cors', True)
        self.cors_origins: List[str] = kwargs.get('cors_origins', ["*"])
        self.cors_methods: List[str] = kwargs.get('cors_methods', ["*"])
        self.cors_headers: List[str] = kwargs.get('cors_headers', ["*"])
        
        # Advanced settings
        self.auto_find_port: bool = kwargs.get('auto_find_port', True)
        self.max_port_attempts: int = kwargs.get('max_port_attempts', 10)
        self.port_increment: int = kwargs.get('port_increment', 1)
        self.shutdown_timeout: int = kwargs.get('shutdown_timeout', 5)

        # Documentation settings
        self.docs_url: str = kwargs.get('docs_url', '/api-docs')
        self.docs_versions: List[str] = kwargs.get('docs_versions', ['1.0.0'])
        self.data_dir: str = kwargs.get('data_dir', os.path.expanduser("~/blender_graphql_mcp_data"))

        # Custom settings
        self.custom: Dict[str, Any] = kwargs.get('custom', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ServerConfig':
        """Create a ServerConfig instance from a dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def from_file(cls, file_path: str) -> 'ServerConfig':
        """
        Load configuration from a file.
        Supports JSON, YAML, or TOML format based on file extension.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        extension = os.path.splitext(file_path)[1].lower()
        
        if extension == '.json':
            import json
            with open(file_path, 'r') as f:
                config_dict = json.load(f)
        elif extension in ('.yaml', '.yml'):
            try:
                import yaml
                with open(file_path, 'r') as f:
                    config_dict = yaml.safe_load(f)
            except ImportError:
                raise ImportError("YAML support requires pyyaml. Install with 'pip install pyyaml'")
        elif extension == '.toml':
            try:
                import toml
                with open(file_path, 'r') as f:
                    config_dict = toml.load(f)
            except ImportError:
                raise ImportError("TOML support requires toml. Install with 'pip install toml'")
        else:
            raise ValueError(f"Unsupported configuration file format: {extension}")
        
        return cls.from_dict(config_dict)