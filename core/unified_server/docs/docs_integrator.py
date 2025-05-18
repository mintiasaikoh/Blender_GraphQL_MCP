"""
Documentation integrator for the unified server.

This module provides the integration between the documentation system and the unified server.
It initializes all documentation components and registers them with the server.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ..core.server import UnifiedServer
from ..utils.logging import get_logger
from ..api.version_manager import VersionManager
from .schema_generator import OpenAPIGenerator, GraphQLSchemaDocGenerator
from .endpoint_registry import EndpointRegistry
from .api_versioning import APICompatibilityChecker
from .html_generator import HTMLGenerator
from .static_handler import APIDocsHandler


class DocumentationIntegrator:
    """
    Integrates the documentation system with the unified server.
    """
    
    def __init__(self, server: UnifiedServer):
        """
        Initialize the documentation integrator.
        
        Args:
            server: The UnifiedServer instance
        """
        self.server = server
        self.logger = get_logger(__name__)
        self.version_manager = VersionManager.get_instance()
        self.endpoint_registry = EndpointRegistry.get_instance()
        
        # Set up docs directory
        self.docs_dir = os.path.join(
            self.server.config.data_dir, 
            "docs", 
            self.server.config.api_version
        )
        Path(self.docs_dir).mkdir(parents=True, exist_ok=True)
        
        # Documentation components
        self.openapi_generator = None
        self.graphql_schema_generator = None
        self.compatibility_checker = None
        self.html_generator = None
        self.docs_handler = None
        
    def initialize(self) -> bool:
        """
        Initialize all documentation components.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Initialize components
            self.openapi_generator = OpenAPIGenerator(self.server)
            
            # Initialize GraphQL schema generator if GraphQL API is available
            if "graphql" in self.server.apis:
                self.graphql_schema_generator = GraphQLSchemaDocGenerator(
                    self.server.apis["graphql"]
                )
            
            self.compatibility_checker = APICompatibilityChecker()
            self.html_generator = HTMLGenerator(self.server)
            
            # Generate documentation
            return self._generate_documentation()
        except Exception as e:
            self.logger.error(f"Error initializing documentation system: {e}", exc_info=True)
            return False
    
    def _generate_documentation(self) -> bool:
        """
        Generate all documentation.
        
        Returns:
            True if documentation generation was successful, False otherwise
        """
        try:
            # Generate OpenAPI schema
            openapi_schema = self.openapi_generator.generate_schema()
            openapi_path = os.path.join(self.docs_dir, "openapi.json")
            with open(openapi_path, "w") as f:
                import json
                json.dump(openapi_schema, f, indent=2)
            
            # Generate GraphQL schema documentation if available
            if self.graphql_schema_generator:
                graphql_schema_doc = self.graphql_schema_generator.generate_documentation()
                graphql_doc_path = os.path.join(self.docs_dir, "graphql_schema.md")
                with open(graphql_doc_path, "w") as f:
                    f.write(graphql_schema_doc)
            
            # Generate HTML documentation
            self.html_generator.generate_docs(self.docs_dir, openapi_schema)
            
            # Set up static file handler
            return self._setup_static_handler()
        except Exception as e:
            self.logger.error(f"Error generating documentation: {e}", exc_info=True)
            return False
    
    def _setup_static_handler(self) -> bool:
        """
        Set up the static file handler for serving documentation.
        
        Returns:
            True if setup was successful, False otherwise
        """
        try:
            # Create static file handler
            self.docs_handler = APIDocsHandler(self.server, self.docs_dir)
            
            # Mount static files
            docs_url = "/api-docs"
            self.server.app.mount(
                docs_url, 
                StaticFiles(directory=self.docs_dir, html=True), 
                name="api_docs"
            )
            
            # Create redirect from /docs to latest version
            @self.server.app.get("/docs/", include_in_schema=False)
            async def docs_redirect():
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=f"{docs_url}/index.html")
            
            self.logger.info(f"Documentation static files mounted at {docs_url}")
            self.logger.info(f"Documentation available at {self.server.config.host}:{self.server.config.port}{docs_url}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error setting up static file handler: {e}", exc_info=True)
            return False
    
    def register_endpoint(self, 
                          endpoint: str, 
                          method: str, 
                          description: str, 
                          version: str,
                          deprecated: bool = False,
                          tags: Optional[list] = None) -> None:
        """
        Register an API endpoint with the documentation system.
        
        Args:
            endpoint: The endpoint path
            method: The HTTP method
            description: Description of the endpoint
            version: API version that introduced this endpoint
            deprecated: Whether the endpoint is deprecated
            tags: List of tags for categorizing the endpoint
        """
        self.endpoint_registry.register_endpoint(
            endpoint=endpoint,
            method=method,
            description=description,
            version=version,
            deprecated=deprecated,
            tags=tags or []
        )