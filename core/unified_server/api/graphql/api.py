"""
GraphQL API subsystem for UnifiedServer.
Provides GraphQL API functionality with schema and resolver integration.
"""

import os
import importlib
import json
from typing import Any, Dict, List, Optional, Tuple, Union, Set, Type

# Try to import GraphQL dependencies
try:
    from tools import (
        GraphQLSchema, GraphQLObjectType, GraphQLString, GraphQLInt, GraphQLFloat,
        GraphQLBoolean, GraphQLList, GraphQLNonNull, GraphQLArgument, GraphQLField,
        graphql_sync, parse, validate
    )
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False

# Import FastAPI types
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse

# Import base API class
from ..base import APISubsystem, register_api

# Import utilities
from ...utils.logging import get_logger


@register_api("graphql")
class GraphQLAPI(APISubsystem):
    """
    GraphQL API implementation for UnifiedServer.
    Provides a full GraphQL API with schema and resolver integration.
    """
    
    def __init__(self, server):
        """
        Initialize the GraphQL API subsystem.
        
        Args:
            server: The UnifiedServer instance
        """
        super().__init__(server)
        self.logger = get_logger("graphql_api")
        
        # GraphQL components
        self.schema = None
        self.resolvers = {}
        
        # Check GraphQL availability
        self.graphql_available = GRAPHQL_AVAILABLE
        if not self.graphql_available:
            self.logger.warning("GraphQL dependencies not available")
    
    def setup(self) -> None:
        """
        Set up the GraphQL API routes and schema.
        Loads the schema and resolvers from existing GraphQL modules.
        """
        if not self.check_dependencies():
            self.logger.error("GraphQL dependencies not available, cannot set up GraphQL API")
            return
        
        # Load schema
        if not self._load_schema():
            self.logger.error("Failed to load GraphQL schema, cannot set up GraphQL API")
            return
        
        # Set up endpoints
        self._setup_endpoints()
        
        self.logger.info("GraphQL API set up successfully")
    
    def cleanup(self) -> None:
        """Clean up resources when server is stopping."""
        self.logger.debug("Cleaning up GraphQL API")
        
        # Reset schema and resolvers
        self.schema = None
        self.resolvers = {}
    
    def check_dependencies(self) -> bool:
        """
        Check if required dependencies are available.
        
        Returns:
            True if all dependencies are available, False otherwise
        """
        return self.graphql_available
    
    def get_routes(self) -> List[Dict[str, Any]]:
        """
        Get information about available routes.
        
        Returns:
            List of route information dictionaries
        """
        routes = [
            {
                "path": "/graphql",
                "method": "POST",
                "description": "GraphQL endpoint for executing queries and mutations"
            },
            {
                "path": "/graphiql",
                "method": "GET",
                "description": "GraphiQL interface for exploring the GraphQL API"
            }
        ]
        
        return routes
    
    async def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query.
        
        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Query result as a dictionary
        """
        if not self.schema:
            return {"errors": [{"message": "GraphQL schema not loaded"}]}
        
        # Validate query
        try:
            document = parse(query)
            validation_errors = validate(self.schema, document)
            if validation_errors:
                return {"errors": [{"message": str(error)} for error in validation_errors]}
        except Exception as e:
            self.logger.error(f"Error validating GraphQL query: {e}")
            return {"errors": [{"message": f"Query validation error: {str(e)}"}]}
        
        # Execute query
        try:
            result = graphql_sync(
                schema=self.schema,
                source=query,
                variable_values=variables or {}
            )
            
            # Convert result to serializable dictionary
            return {
                "data": result.data,
                **({"errors": [{"message": str(error)} for error in result.errors]} if result.errors else {})
            }
        except Exception as e:
            self.logger.error(f"Error executing GraphQL query: {e}")
            return {"errors": [{"message": f"Query execution error: {str(e)}"}]}
    
    def _load_schema(self) -> bool:
        """
        Load GraphQL schema from existing schema modules in the project.
        Attempts to load schema from the standard location in the project.
        
        Returns:
            True if schema was loaded successfully, False otherwise
        """
        try:
            # Try to import schema from the main project
            schema_module = importlib.import_module("tools.definitions")
            if hasattr(schema_module, "schema"):
                self.schema = schema_module.schema
                self.logger.info("Loaded GraphQL schema from project's tools.definitions module")
                return True
        except ImportError:
            self.logger.warning("Failed to import schema from project's tools.definitions module")
        
        # If we couldn't load the schema from the main project, create a minimal schema
        try:
            # Create query type
            query_type = GraphQLObjectType(
                name="Query",
                fields={
                    "hello": GraphQLField(
                        GraphQLString,
                        resolve=lambda obj, info: "Hello, world!"
                    ),
                    "server_info": GraphQLField(
                        GraphQLObjectType(
                            name="ServerInfo",
                            fields={
                                "version": GraphQLField(GraphQLString),
                                "status": GraphQLField(GraphQLString)
                            }
                        ),
                        resolve=lambda obj, info: {
                            "version": self.server.config.api_version,
                            "status": "running"
                        }
                    )
                }
            )
            
            # Create mutation type
            mutation_type = GraphQLObjectType(
                name="Mutation",
                fields={
                    "echo": GraphQLField(
                        GraphQLString,
                        args={
                            "message": GraphQLArgument(GraphQLString)
                        },
                        resolve=lambda obj, info, message: f"Echo: {message}"
                    )
                }
            )
            
            # Create schema
            self.schema = GraphQLSchema(query=query_type, mutation=mutation_type)
            self.logger.info("Created minimal GraphQL schema")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create minimal GraphQL schema: {e}")
            return False
    
    def _load_resolvers(self) -> None:
        """
        Load GraphQL resolvers from existing resolver modules in the project.
        Attempts to discover and load resolvers from standard locations.
        """
        try:
            # Try to import resolvers from the main project
            resolvers_module = importlib.import_module("tools.handlers")
            self.logger.info("Loaded GraphQL resolvers from project's tools.handlers module")
        except ImportError:
            self.logger.warning("Failed to import resolvers from project's tools.handlers module")
    
    def _setup_endpoints(self) -> None:
        """Set up GraphQL endpoints for the FastAPI application."""
        # GraphQL endpoint
        @self.app.post("/graphql", response_class=JSONResponse)
        async def graphql_endpoint(request: Request):
            # Parse request
            try:
                data = await request.json()
                query = data.get("query")
                variables = data.get("variables")
                
                if not query:
                    return JSONResponse(
                        status_code=400,
                        content={"errors": [{"message": "No GraphQL query provided"}]}
                    )
                
                # Execute query
                result = await self.execute_query(query, variables)
                return JSONResponse(content=result)
            except Exception as e:
                self.logger.error(f"Error handling GraphQL request: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"errors": [{"message": f"Internal server error: {str(e)}"}]}
                )
        
        # GraphiQL interface
        @self.app.get("/graphiql", response_class=HTMLResponse)
        async def graphiql_interface():
            # Only serve GraphiQL if enabled in configuration
            if not self.config.enable_graphiql:
                raise HTTPException(
                    status_code=404,
                    detail="GraphiQL interface is disabled"
                )
            
            # Get GraphiQL HTML
            graphiql_html = self._get_graphiql_html()
            return HTMLResponse(content=graphiql_html)
    
    def _get_graphiql_html(self) -> str:
        """
        Get GraphiQL HTML for the GraphiQL interface.
        
        Returns:
            GraphiQL HTML
        """
        # Try to import graphiql module or generate simple HTML
        try:
            # Try to import graphiql from the main project
            graphiql_module = importlib.import_module("graphql.graphiql")
            if hasattr(graphiql_module, "get_graphiql_html"):
                return graphiql_module.get_graphiql_html()
        except ImportError:
            self.logger.debug("Failed to import graphiql.get_graphiql_html, using built-in GraphiQL HTML")
        
        # Use built-in GraphiQL HTML
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>GraphiQL - Blender GraphQL MCP</title>
            <link href="https://unpkg.com/graphiql/graphiql.min.css" rel="stylesheet" />
        </head>
        <body style="margin: 0; height: 100vh;">
            <div id="graphiql" style="height: 100vh;"></div>
            <script
                crossorigin
                src="https://unpkg.com/react/umd/react.production.min.js"
            ></script>
            <script
                crossorigin
                src="https://unpkg.com/react-dom/umd/react-dom.production.min.js"
            ></script>
            <script
                crossorigin
                src="https://unpkg.com/graphiql/graphiql.min.js"
            ></script>
            <script>
                const graphQLFetcher = graphQLParams =>
                    fetch('/graphql', {{
                        method: 'post',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(graphQLParams),
                    }})
                        .then(response => response.json())
                        .catch(() => response.text());
                ReactDOM.render(
                    React.createElement(GraphiQL, {{ fetcher: graphQLFetcher }}),
                    document.getElementById('graphiql'),
                );
            </script>
        </body>
        </html>
        """