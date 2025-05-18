"""
HTML documentation generator for the unified server.
Provides utilities for generating HTML documentation for the API.
"""

import os
import json
import logging
import datetime
import re
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from pathlib import Path

# Import version manager
from ..api.version_manager import APIVersion, VersionManager

# Logger
logger = logging.getLogger("unified_server.docs.html_generator")


# HTML templates
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        /* Base styles */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        
        /* Header styles */
        header {{
            background-color: #343a40;
            color: white;
            padding: 1rem;
            margin-bottom: 2rem;
            border-radius: 5px;
        }}
        
        header h1 {{
            margin: 0;
            font-size: 1.8rem;
        }}
        
        /* Section styles */
        section {{
            background-color: white;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        h2 {{
            margin-top: 0;
            color: #0066cc;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.5rem;
            font-size: 1.5rem;
        }}
        
        h3 {{
            color: #0066cc;
            font-size: 1.3rem;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }}
        
        h4 {{
            font-size: 1.1rem;
            margin-top: 1.2rem;
            margin-bottom: 0.5rem;
        }}
        
        /* Table styles */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1.5rem;
        }}
        
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border: 1px solid #dee2e6;
        }}
        
        th {{
            background-color: #f2f2f2;
            font-weight: 600;
        }}
        
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        /* Code styles */
        pre, code {{
            font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
            background-color: #f6f8fa;
            border-radius: 3px;
            padding: 0.2em 0.4em;
            font-size: 0.9em;
        }}
        
        pre {{
            padding: 1rem;
            overflow-x: auto;
            border: 1px solid #e1e4e8;
        }}
        
        pre code {{
            padding: 0;
            background-color: transparent;
        }}
        
        /* Utility classes */
        .deprecated {{
            background-color: #fff3cd;
            padding: 0.5rem;
            border-radius: 3px;
            border-left: 3px solid #ffc107;
            margin-bottom: 1rem;
        }}
        
        .experimental {{
            background-color: #d1ecf1;
            padding: 0.5rem;
            border-radius: 3px;
            border-left: 3px solid #17a2b8;
            margin-bottom: 1rem;
        }}
        
        .required {{
            color: #e63946;
            font-weight: bold;
        }}
        
        .tag {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            font-size: 0.8rem;
            font-weight: 600;
            border-radius: 3px;
            margin-right: 0.3rem;
        }}
        
        .tag-get {{
            background-color: #61affe;
            color: white;
        }}
        
        .tag-post {{
            background-color: #49cc90;
            color: white;
        }}
        
        .tag-put {{
            background-color: #fca130;
            color: white;
        }}
        
        .tag-delete {{
            background-color: #f93e3e;
            color: white;
        }}
        
        .tag-patch {{
            background-color: #50e3c2;
            color: white;
        }}
        
        .tag-query {{
            background-color: #61affe;
            color: white;
        }}
        
        .tag-mutation {{
            background-color: #49cc90;
            color: white;
        }}
        
        .tag-subscription {{
            background-color: #fca130;
            color: white;
        }}
        
        .version {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            font-size: 0.8rem;
            border-radius: 3px;
            background-color: #e9ecef;
            color: #495057;
            margin-left: 0.5rem;
        }}
        
        /* Navigation styles */
        nav {{
            margin-bottom: 2rem;
        }}
        
        nav ul {{
            list-style-type: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-wrap: wrap;
            background-color: #f8f9fa;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }}
        
        nav ul li {{
            margin: 0;
        }}
        
        nav ul li a {{
            display: block;
            padding: 0.8rem 1rem;
            color: #0066cc;
            text-decoration: none;
            transition: background-color 0.2s ease;
            border-right: 1px solid #dee2e6;
        }}
        
        nav ul li:last-child a {{
            border-right: none;
        }}
        
        nav ul li a:hover, nav ul li a.active {{
            background-color: #e9ecef;
        }}
        
        /* Footer styles */
        footer {{
            text-align: center;
            margin-top: 2rem;
            padding: 1rem;
            color: #6c757d;
            font-size: 0.9rem;
            border-top: 1px solid #dee2e6;
        }}
        
        /* Responsive layouts */
        @media (max-width: 768px) {{
            nav ul {{
                flex-direction: column;
            }}
            
            nav ul li a {{
                border-right: none;
                border-bottom: 1px solid #dee2e6;
            }}
            
            nav ul li:last-child a {{
                border-bottom: none;
            }}
        }}
        
        /* Dark mode */
        @media (prefers-color-scheme: dark) {{
            body {{
                background-color: #222;
                color: #eee;
            }}
            
            section, nav ul {{
                background-color: #333;
                border-color: #444;
            }}
            
            h2 {{
                border-bottom-color: #444;
                color: #61dafb;
            }}
            
            h3, h4 {{
                color: #61dafb;
            }}
            
            th, td {{
                border-color: #444;
            }}
            
            th {{
                background-color: #3a3a3a;
            }}
            
            tr:nth-child(even) {{
                background-color: #2a2a2a;
            }}
            
            pre, code {{
                background-color: #2a2a2a;
            }}
            
            pre {{
                border-color: #444;
            }}
            
            nav ul li a {{
                color: #61dafb;
                border-color: #444;
            }}
            
            nav ul li a:hover, nav ul li a.active {{
                background-color: #3a3a3a;
            }}
            
            footer {{
                color: #aaa;
                border-top-color: #444;
            }}
            
            .version {{
                background-color: #444;
                color: #eee;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>{header}</h1>
        <p>{description}</p>
        <p>Version: {version}</p>
    </header>
    
    <nav>
        <ul>
            <li><a href="#overview">Overview</a></li>
            <li><a href="#versions">Versions</a></li>
            <li><a href="#rest-endpoints">REST Endpoints</a></li>
            <li><a href="#graphql-operations">GraphQL Operations</a></li>
            <li><a href="#models">Models</a></li>
            <li><a href="#authentication">Authentication</a></li>
            <li><a href="#examples">Examples</a></li>
        </ul>
    </nav>
    
    <main>
        {content}
    </main>
    
    <footer>
        <p>Generated on {generated_date} by Blender GraphQL MCP Documentation Generator</p>
    </footer>
</body>
</html>
"""


OVERVIEW_TEMPLATE = """
<section id="overview">
    <h2>Overview</h2>
    <p>{overview}</p>
    
    <h3>Base URLs</h3>
    <ul>
        <li><strong>REST API:</strong> <code>{rest_base_url}</code></li>
        <li><strong>GraphQL API:</strong> <code>{graphql_base_url}</code></li>
        <li><strong>GraphiQL Interface:</strong> <code>{graphiql_url}</code></li>
    </ul>
    
    <h3>Features</h3>
    <ul>
        {features}
    </ul>
</section>
"""


VERSIONS_TEMPLATE = """
<section id="versions">
    <h2>API Versions</h2>
    <p>{versions_description}</p>
    
    <h3>Supported Versions</h3>
    <table>
        <thead>
            <tr>
                <th>Version</th>
                <th>Status</th>
                <th>Release Date</th>
                <th>End of Support</th>
                <th>Notes</th>
            </tr>
        </thead>
        <tbody>
            {supported_versions}
        </tbody>
    </table>
    
    <h3>Version Compatibility</h3>
    <p>{compatibility_description}</p>
    
    <h4>Breaking Changes</h4>
    <ul>
        {breaking_changes}
    </ul>
</section>
"""


REST_ENDPOINTS_TEMPLATE = """
<section id="rest-endpoints">
    <h2>REST Endpoints</h2>
    <p>{rest_description}</p>
    
    <h3>Endpoints by Category</h3>
    {rest_endpoints_by_category}
</section>
"""


GRAPHQL_OPERATIONS_TEMPLATE = """
<section id="graphql-operations">
    <h2>GraphQL Operations</h2>
    <p>{graphql_description}</p>
    
    <h3>GraphQL Schema</h3>
    <p>{schema_description}</p>
    
    <h4>Queries</h4>
    {graphql_queries}
    
    <h4>Mutations</h4>
    {graphql_mutations}
    
    <h4>Types</h4>
    {graphql_types}
</section>
"""


MODELS_TEMPLATE = """
<section id="models">
    <h2>Models</h2>
    <p>{models_description}</p>
    
    {models}
</section>
"""


AUTHENTICATION_TEMPLATE = """
<section id="authentication">
    <h2>Authentication</h2>
    <p>{authentication_description}</p>
    
    <h3>Authentication Methods</h3>
    {authentication_methods}
</section>
"""


EXAMPLES_TEMPLATE = """
<section id="examples">
    <h2>Examples</h2>
    <p>{examples_description}</p>
    
    <h3>REST API Examples</h3>
    {rest_examples}
    
    <h3>GraphQL API Examples</h3>
    {graphql_examples}
</section>
"""


class HTMLGenerator:
    """
    Generator for HTML API documentation.
    """
    
    def __init__(self, server):
        """
        Initialize the HTML generator.
        
        Args:
            server: The UnifiedServer instance
        """
        self.server = server
        self.version_manager = VersionManager.get_instance()
        
        # Get current version
        self.current_version = self.version_manager.current_version
    
    def _generate_overview_section(self, api_version: APIVersion) -> str:
        """
        Generate the overview section of the documentation.
        
        Args:
            api_version: The API version to generate documentation for
            
        Returns:
            HTML content for the overview section
        """
        # API overview
        overview = f"""
        The Blender GraphQL MCP API provides a unified interface for interacting with Blender.
        It supports both REST and GraphQL APIs, allowing you to use the best interface for your needs.
        This documentation covers version {api_version}.
        """
        
        # Base URLs
        host = self.server.config.host
        port = self.server.config.port
        rest_base_url = f"http://{host}:{port}/api/v{api_version.major}"
        graphql_base_url = f"http://{host}:{port}/graphql"
        graphiql_url = f"http://{host}:{port}/graphiql"
        
        # Features
        features_list = [
            "Blender object manipulation",
            "Scene management",
            "Material creation and editing",
            "Addon management",
            "Batch operations",
            "Asynchronous tasks",
            "GraphQL introspection"
        ]
        
        features = "\n".join([f"<li>{feature}</li>" for feature in features_list])
        
        # Render template
        return OVERVIEW_TEMPLATE.format(
            overview=overview,
            rest_base_url=rest_base_url,
            graphql_base_url=graphql_base_url,
            graphiql_url=graphiql_url,
            features=features
        )
    
    def _generate_versions_section(self, api_version: APIVersion) -> str:
        """
        Generate the versions section of the documentation.
        
        Args:
            api_version: The API version to generate documentation for
            
        Returns:
            HTML content for the versions section
        """
        # Versions description
        versions_description = """
        The API uses semantic versioning (MAJOR.MINOR.PATCH). 
        Breaking changes are introduced in major versions, 
        new features in minor versions, and bug fixes in patch versions.
        """
        
        # Supported versions
        supported_versions_list = []
        current_date = datetime.datetime.now()
        
        for version in sorted(self.version_manager.supported_versions):
            version_str = str(version)
            status = "Current" if version == self.current_version else "Active"
            
            if version < self.current_version:
                # Calculate end of support date (1 year after next major release)
                end_of_support = current_date.replace(year=current_date.year + 1)
                end_of_support_str = end_of_support.strftime("%Y-%m-%d")
                notes = "Legacy support"
            else:
                end_of_support_str = "TBD"
                notes = ""
            
            # Fake release date for demonstration
            release_date = current_date.replace(year=current_date.year - 1)
            release_date_str = release_date.strftime("%Y-%m-%d")
            
            supported_versions_list.append(f"""
            <tr>
                <td>{version_str}</td>
                <td>{status}</td>
                <td>{release_date_str}</td>
                <td>{end_of_support_str}</td>
                <td>{notes}</td>
            </tr>
            """)
        
        supported_versions = "\n".join(supported_versions_list)
        
        # Compatibility description
        compatibility_description = """
        Clients using the same major version as the server should be compatible.
        Minor version differences may result in missing features but should not break existing functionality.
        """
        
        # Breaking changes
        breaking_changes_list = [
            "Version 2.0.0: Changed auth token handling",
            "Version 2.0.0: Removed deprecated endpoints",
            "Version 2.0.0: Restructured error responses",
            "Version 3.0.0: Changed parameter format for batch operations"
        ]
        
        breaking_changes = "\n".join([f"<li>{change}</li>" for change in breaking_changes_list])
        
        # Render template
        return VERSIONS_TEMPLATE.format(
            versions_description=versions_description,
            supported_versions=supported_versions,
            compatibility_description=compatibility_description,
            breaking_changes=breaking_changes
        )
    
    def _generate_rest_endpoints_section(self, api_version: APIVersion) -> str:
        """
        Generate the REST endpoints section of the documentation.
        
        Args:
            api_version: The API version to generate documentation for
            
        Returns:
            HTML content for the REST endpoints section
        """
        # REST description
        rest_description = """
        The REST API provides a traditional HTTP interface for interacting with Blender.
        It follows REST principles and uses standard HTTP methods and status codes.
        """
        
        # Categories
        categories = {
            "objects": "Endpoints for manipulating Blender objects",
            "scenes": "Endpoints for managing scenes",
            "materials": "Endpoints for working with materials",
            "addons": "Endpoints for managing Blender addons",
            "commands": "Endpoints for executing commands",
            "batch": "Endpoints for batch operations",
            "async": "Endpoints for asynchronous tasks"
        }
        
        # Mock endpoints for demonstration
        endpoints = {
            "objects": [
                {
                    "path": "/api/v1/objects",
                    "method": "GET",
                    "description": "List all objects in the scene",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/objects/{object_name}",
                    "method": "GET",
                    "description": "Get details of a specific object",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/objects",
                    "method": "POST",
                    "description": "Create a new object",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/objects/{object_name}",
                    "method": "PUT",
                    "description": "Update an object",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/objects/{object_name}",
                    "method": "DELETE",
                    "description": "Delete an object",
                    "deprecated": False
                }
            ],
            "scenes": [
                {
                    "path": "/api/v1/scenes",
                    "method": "GET",
                    "description": "List all scenes",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/scenes/{scene_name}",
                    "method": "GET",
                    "description": "Get details of a specific scene",
                    "deprecated": False
                }
            ],
            "materials": [
                {
                    "path": "/api/v1/materials",
                    "method": "GET",
                    "description": "List all materials",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/materials/{material_name}",
                    "method": "GET",
                    "description": "Get details of a specific material",
                    "deprecated": False
                }
            ],
            "addons": [
                {
                    "path": "/api/v1/addons",
                    "method": "GET",
                    "description": "List all addons",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/addons/{addon_name}",
                    "method": "GET",
                    "description": "Get details of a specific addon",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/addons/{addon_name}/enable",
                    "method": "POST",
                    "description": "Enable an addon",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/addons/{addon_name}/disable",
                    "method": "POST",
                    "description": "Disable an addon",
                    "deprecated": False
                }
            ],
            "commands": [
                {
                    "path": "/api/v1/commands",
                    "method": "GET",
                    "description": "List all available commands",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/commands/{command_name}",
                    "method": "GET",
                    "description": "Get details of a specific command",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/command",
                    "method": "POST",
                    "description": "Execute a command",
                    "deprecated": False
                }
            ],
            "batch": [
                {
                    "path": "/api/v1/batch",
                    "method": "POST",
                    "description": "Execute multiple commands in a batch",
                    "deprecated": False
                }
            ],
            "async": [
                {
                    "path": "/api/v1/async/command",
                    "method": "POST",
                    "description": "Execute a command asynchronously",
                    "deprecated": False
                },
                {
                    "path": "/api/v1/task/{task_id}",
                    "method": "GET",
                    "description": "Get status of an asynchronous task",
                    "deprecated": False
                }
            ]
        }
        
        # Generate HTML for each category
        categories_html = []
        
        for category, description in categories.items():
            category_endpoints = endpoints.get(category, [])
            
            if not category_endpoints:
                continue
            
            endpoints_html = []
            
            for endpoint in category_endpoints:
                method_class = f"tag-{endpoint['method'].lower()}"
                
                deprecated_html = """
                <div class="deprecated">
                    <strong>Deprecated:</strong> This endpoint is deprecated and will be removed in a future version.
                </div>
                """ if endpoint.get("deprecated", False) else ""
                
                endpoints_html.append(f"""
                <tr>
                    <td><span class="tag {method_class}">{endpoint['method']}</span></td>
                    <td><code>{endpoint['path']}</code></td>
                    <td>{endpoint['description']}</td>
                </tr>
                {deprecated_html}
                """)
            
            categories_html.append(f"""
            <h4>{category.capitalize()}</h4>
            <p>{description}</p>
            <table>
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Path</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(endpoints_html)}
                </tbody>
            </table>
            """)
        
        rest_endpoints_by_category = "\n".join(categories_html)
        
        # Render template
        return REST_ENDPOINTS_TEMPLATE.format(
            rest_description=rest_description,
            rest_endpoints_by_category=rest_endpoints_by_category
        )
    
    def _generate_graphql_operations_section(self, api_version: APIVersion) -> str:
        """
        Generate the GraphQL operations section of the documentation.
        
        Args:
            api_version: The API version to generate documentation for
            
        Returns:
            HTML content for the GraphQL operations section
        """
        # GraphQL description
        graphql_description = """
        The GraphQL API provides a flexible and type-safe interface for interacting with Blender.
        It allows you to request exactly the data you need in a single request.
        """
        
        # Schema description
        schema_description = """
        The GraphQL schema defines the available types, queries, mutations, and subscriptions.
        You can explore the schema interactively using the GraphiQL interface.
        """
        
        # Mock queries for demonstration
        queries = [
            {
                "name": "getObject",
                "description": "Get a Blender object by name",
                "arguments": [
                    {
                        "name": "name",
                        "type": "String!",
                        "description": "The name of the object to get"
                    }
                ],
                "return_type": "Object",
                "deprecated": False
            },
            {
                "name": "getAllObjects",
                "description": "Get all objects in the scene",
                "arguments": [
                    {
                        "name": "filter",
                        "type": "ObjectFilter",
                        "description": "Filter criteria for objects"
                    }
                ],
                "return_type": "[Object]",
                "deprecated": False
            },
            {
                "name": "getScene",
                "description": "Get scene information",
                "arguments": [
                    {
                        "name": "name",
                        "type": "String",
                        "description": "The name of the scene to get (defaults to current scene)"
                    }
                ],
                "return_type": "Scene",
                "deprecated": False
            }
        ]
        
        # Generate HTML for queries
        queries_html = []
        
        for query in queries:
            arguments_html = []
            
            for arg in query["arguments"]:
                arguments_html.append(f"""
                <tr>
                    <td><code>{arg['name']}</code></td>
                    <td><code>{arg['type']}</code></td>
                    <td>{arg['description']}</td>
                </tr>
                """)
            
            deprecated_html = """
            <div class="deprecated">
                <strong>Deprecated:</strong> This query is deprecated and will be removed in a future version.
            </div>
            """ if query.get("deprecated", False) else ""
            
            queries_html.append(f"""
            <h5>{query['name']}</h5>
            <p>{query['description']}</p>
            {deprecated_html}
            <p><strong>Return type:</strong> <code>{query['return_type']}</code></p>
            <h6>Arguments</h6>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(arguments_html)}
                </tbody>
            </table>
            <pre><code>query {{
  {query['name']}(
    {', '.join([f'{arg["name"]}: {arg["type"]}' for arg in query["arguments"]])}
  ) {{
    # fields
  }}
}}</code></pre>
            """)
        
        graphql_queries = "\n".join(queries_html) if queries_html else "<p>No queries available.</p>"
        
        # Mock mutations for demonstration
        mutations = [
            {
                "name": "createObject",
                "description": "Create a new Blender object",
                "arguments": [
                    {
                        "name": "type",
                        "type": "String!",
                        "description": "The type of object to create"
                    },
                    {
                        "name": "name",
                        "type": "String!",
                        "description": "The name of the object"
                    },
                    {
                        "name": "location",
                        "type": "Vector3Input",
                        "description": "The location of the object"
                    }
                ],
                "return_type": "CreateObjectResult",
                "deprecated": False
            },
            {
                "name": "updateObject",
                "description": "Update a Blender object",
                "arguments": [
                    {
                        "name": "name",
                        "type": "String!",
                        "description": "The name of the object to update"
                    },
                    {
                        "name": "location",
                        "type": "Vector3Input",
                        "description": "The new location of the object"
                    },
                    {
                        "name": "rotation",
                        "type": "Vector3Input",
                        "description": "The new rotation of the object"
                    }
                ],
                "return_type": "UpdateObjectResult",
                "deprecated": False
            },
            {
                "name": "deleteObject",
                "description": "Delete a Blender object",
                "arguments": [
                    {
                        "name": "name",
                        "type": "String!",
                        "description": "The name of the object to delete"
                    }
                ],
                "return_type": "DeleteObjectResult",
                "deprecated": False
            }
        ]
        
        # Generate HTML for mutations
        mutations_html = []
        
        for mutation in mutations:
            arguments_html = []
            
            for arg in mutation["arguments"]:
                arguments_html.append(f"""
                <tr>
                    <td><code>{arg['name']}</code></td>
                    <td><code>{arg['type']}</code></td>
                    <td>{arg['description']}</td>
                </tr>
                """)
            
            deprecated_html = """
            <div class="deprecated">
                <strong>Deprecated:</strong> This mutation is deprecated and will be removed in a future version.
            </div>
            """ if mutation.get("deprecated", False) else ""
            
            mutations_html.append(f"""
            <h5>{mutation['name']}</h5>
            <p>{mutation['description']}</p>
            {deprecated_html}
            <p><strong>Return type:</strong> <code>{mutation['return_type']}</code></p>
            <h6>Arguments</h6>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(arguments_html)}
                </tbody>
            </table>
            <pre><code>mutation {{
  {mutation['name']}(
    {', '.join([f'{arg["name"]}: {arg["type"]}' for arg in mutation["arguments"]])}
  ) {{
    # fields
  }}
}}</code></pre>
            """)
        
        graphql_mutations = "\n".join(mutations_html) if mutations_html else "<p>No mutations available.</p>"
        
        # Mock types for demonstration
        types = [
            {
                "name": "Object",
                "description": "A Blender object",
                "fields": [
                    {
                        "name": "name",
                        "type": "String!",
                        "description": "The name of the object"
                    },
                    {
                        "name": "type",
                        "type": "String!",
                        "description": "The type of the object"
                    },
                    {
                        "name": "location",
                        "type": "Vector3!",
                        "description": "The location of the object"
                    },
                    {
                        "name": "rotation",
                        "type": "Vector3!",
                        "description": "The rotation of the object"
                    },
                    {
                        "name": "scale",
                        "type": "Vector3!",
                        "description": "The scale of the object"
                    }
                ]
            },
            {
                "name": "Vector3",
                "description": "A 3D vector",
                "fields": [
                    {
                        "name": "x",
                        "type": "Float!",
                        "description": "The X component of the vector"
                    },
                    {
                        "name": "y",
                        "type": "Float!",
                        "description": "The Y component of the vector"
                    },
                    {
                        "name": "z",
                        "type": "Float!",
                        "description": "The Z component of the vector"
                    }
                ]
            },
            {
                "name": "Scene",
                "description": "A Blender scene",
                "fields": [
                    {
                        "name": "name",
                        "type": "String!",
                        "description": "The name of the scene"
                    },
                    {
                        "name": "objects",
                        "type": "[Object!]!",
                        "description": "The objects in the scene"
                    },
                    {
                        "name": "active_object",
                        "type": "Object",
                        "description": "The active object in the scene"
                    }
                ]
            }
        ]
        
        # Generate HTML for types
        types_html = []
        
        for type_info in types:
            fields_html = []
            
            for field in type_info["fields"]:
                fields_html.append(f"""
                <tr>
                    <td><code>{field['name']}</code></td>
                    <td><code>{field['type']}</code></td>
                    <td>{field['description']}</td>
                </tr>
                """)
            
            types_html.append(f"""
            <h5>{type_info['name']}</h5>
            <p>{type_info['description']}</p>
            <table>
                <thead>
                    <tr>
                        <th>Field</th>
                        <th>Type</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(fields_html)}
                </tbody>
            </table>
            """)
        
        graphql_types = "\n".join(types_html) if types_html else "<p>No types available.</p>"
        
        # Render template
        return GRAPHQL_OPERATIONS_TEMPLATE.format(
            graphql_description=graphql_description,
            schema_description=schema_description,
            graphql_queries=graphql_queries,
            graphql_mutations=graphql_mutations,
            graphql_types=graphql_types
        )
    
    def _generate_models_section(self, api_version: APIVersion) -> str:
        """
        Generate the models section of the documentation.
        
        Args:
            api_version: The API version to generate documentation for
            
        Returns:
            HTML content for the models section
        """
        # Models description
        models_description = """
        These models represent the data structures used in the API.
        They are used in request and response bodies.
        """
        
        # Mock models for demonstration
        models_data = [
            {
                "name": "ObjectCreationRequest",
                "description": "Request body for creating a new object",
                "properties": [
                    {
                        "name": "type",
                        "type": "string",
                        "description": "The type of object to create",
                        "required": True
                    },
                    {
                        "name": "name",
                        "type": "string",
                        "description": "The name of the object",
                        "required": True
                    },
                    {
                        "name": "location",
                        "type": "Vector3",
                        "description": "The location of the object",
                        "required": False
                    },
                    {
                        "name": "rotation",
                        "type": "Vector3",
                        "description": "The rotation of the object",
                        "required": False
                    },
                    {
                        "name": "scale",
                        "type": "Vector3",
                        "description": "The scale of the object",
                        "required": False
                    }
                ]
            },
            {
                "name": "Vector3",
                "description": "A 3D vector",
                "properties": [
                    {
                        "name": "x",
                        "type": "number",
                        "description": "The X component of the vector",
                        "required": True
                    },
                    {
                        "name": "y",
                        "type": "number",
                        "description": "The Y component of the vector",
                        "required": True
                    },
                    {
                        "name": "z",
                        "type": "number",
                        "description": "The Z component of the vector",
                        "required": True
                    }
                ]
            },
            {
                "name": "CommandRequest",
                "description": "Request body for executing a command",
                "properties": [
                    {
                        "name": "command",
                        "type": "string",
                        "description": "The name of the command to execute",
                        "required": True
                    },
                    {
                        "name": "params",
                        "type": "object",
                        "description": "The parameters for the command",
                        "required": False
                    }
                ]
            },
            {
                "name": "BatchRequest",
                "description": "Request body for executing multiple commands in a batch",
                "properties": [
                    {
                        "name": "commands",
                        "type": "array of CommandRequest",
                        "description": "The commands to execute",
                        "required": True
                    },
                    {
                        "name": "stop_on_error",
                        "type": "boolean",
                        "description": "Whether to stop execution if a command fails",
                        "required": False
                    }
                ]
            }
        ]
        
        # Generate HTML for models
        models_html = []
        
        for model in models_data:
            properties_html = []
            
            for prop in model["properties"]:
                required_class = "required" if prop.get("required", False) else ""
                required_text = "<span class='required'>*</span>" if prop.get("required", False) else ""
                
                properties_html.append(f"""
                <tr>
                    <td><code>{prop['name']}</code> {required_text}</td>
                    <td><code>{prop['type']}</code></td>
                    <td>{prop['description']}</td>
                </tr>
                """)
            
            models_html.append(f"""
            <h3>{model['name']}</h3>
            <p>{model['description']}</p>
            <table>
                <thead>
                    <tr>
                        <th>Property</th>
                        <th>Type</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(properties_html)}
                </tbody>
            </table>
            <p><small>* Required property</small></p>
            """)
        
        models = "\n".join(models_html)
        
        # Render template
        return MODELS_TEMPLATE.format(
            models_description=models_description,
            models=models
        )
    
    def _generate_authentication_section(self, api_version: APIVersion) -> str:
        """
        Generate the authentication section of the documentation.
        
        Args:
            api_version: The API version to generate documentation for
            
        Returns:
            HTML content for the authentication section
        """
        # Authentication description
        authentication_description = """
        Authentication is required for some endpoints.
        The API supports multiple authentication methods.
        """
        
        # Mock authentication methods for demonstration
        auth_methods = [
            {
                "name": "Bearer Token",
                "description": "Send a Bearer token in the Authorization header",
                "example": "Authorization: Bearer <token>"
            },
            {
                "name": "API Key",
                "description": "Send an API key in the X-API-Key header",
                "example": "X-API-Key: <api_key>"
            }
        ]
        
        # Generate HTML for authentication methods
        auth_methods_html = []
        
        for method in auth_methods:
            auth_methods_html.append(f"""
            <h4>{method['name']}</h4>
            <p>{method['description']}</p>
            <pre><code>{method['example']}</code></pre>
            """)
        
        authentication_methods = "\n".join(auth_methods_html)
        
        # Render template
        return AUTHENTICATION_TEMPLATE.format(
            authentication_description=authentication_description,
            authentication_methods=authentication_methods
        )
    
    def _generate_examples_section(self, api_version: APIVersion) -> str:
        """
        Generate the examples section of the documentation.
        
        Args:
            api_version: The API version to generate documentation for
            
        Returns:
            HTML content for the examples section
        """
        # Examples description
        examples_description = """
        These examples demonstrate how to use the API in different programming languages.
        """
        
        # Mock REST examples for demonstration
        rest_examples_data = [
            {
                "title": "Get all objects (curl)",
                "language": "bash",
                "code": """curl -X GET "http://localhost:8000/api/v1/objects" \\
     -H "Accept: application/json" \\
     -H "X-API-Key: your_api_key_here\""""
            },
            {
                "title": "Create an object (curl)",
                "language": "bash",
                "code": """curl -X POST "http://localhost:8000/api/v1/objects" \\
     -H "Content-Type: application/json" \\
     -H "X-API-Key: your_api_key_here" \\
     -d '{
       "type": "MESH",
       "name": "Cube",
       "location": {
         "x": 0,
         "y": 0,
         "z": 0
       }
     }'"""
            },
            {
                "title": "Execute a command (Python)",
                "language": "python",
                "code": """import requests

url = "http://localhost:8000/api/v1/command"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "your_api_key_here"
}
payload = {
    "command": "create_object",
    "params": {
        "type": "MESH",
        "name": "Cube",
        "location": {
            "x": 0,
            "y": 0,
            "z": 0
        }
    }
}

response = requests.post(url, headers=headers, json=payload)
print(response.json())"""
            }
        ]
        
        # Generate HTML for REST examples
        rest_examples_html = []
        
        for example in rest_examples_data:
            rest_examples_html.append(f"""
            <h4>{example['title']}</h4>
            <pre><code class="language-{example['language']}">{example['code']}</code></pre>
            """)
        
        rest_examples = "\n".join(rest_examples_html)
        
        # Mock GraphQL examples for demonstration
        graphql_examples_data = [
            {
                "title": "Get all objects (curl)",
                "language": "bash",
                "code": """curl -X POST "http://localhost:8000/graphql" \\
     -H "Content-Type: application/json" \\
     -H "X-API-Key: your_api_key_here" \\
     -d '{
       "query": "{ getAllObjects { name type location { x y z } } }"
     }'"""
            },
            {
                "title": "Create an object (curl)",
                "language": "bash",
                "code": """curl -X POST "http://localhost:8000/graphql" \\
     -H "Content-Type: application/json" \\
     -H "X-API-Key: your_api_key_here" \\
     -d '{
       "query": "mutation { createObject(type: \\"MESH\\", name: \\"Cube\\", location: { x: 0, y: 0, z: 0 }) { success message object_name } }"
     }'"""
            },
            {
                "title": "Get and update an object (Python)",
                "language": "python",
                "code": """import requests

url = "http://localhost:8000/graphql"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "your_api_key_here"
}

# Get object
query = """
{
  getObject(name: "Cube") {
    name
    type
    location {
      x
      y
      z
    }
  }
}
"""

response = requests.post(url, headers=headers, json={"query": query})
print(response.json())

# Update object
mutation = """
mutation {
  updateObject(
    name: "Cube",
    location: { x: 1, y: 2, z: 3 }
  ) {
    success
    message
    object_name
  }
}
"""

response = requests.post(url, headers=headers, json={"query": mutation})
print(response.json())"""
            }
        ]
        
        # Generate HTML for GraphQL examples
        graphql_examples_html = []
        
        for example in graphql_examples_data:
            graphql_examples_html.append(f"""
            <h4>{example['title']}</h4>
            <pre><code class="language-{example['language']}">{example['code']}</code></pre>
            """)
        
        graphql_examples = "\n".join(graphql_examples_html)
        
        # Render template
        return EXAMPLES_TEMPLATE.format(
            examples_description=examples_description,
            rest_examples=rest_examples,
            graphql_examples=graphql_examples
        )
    
    def generate_html_doc(self, api_version: Union[str, APIVersion] = None) -> str:
        """
        Generate HTML documentation for the API.
        
        Args:
            api_version: The API version to generate documentation for
            
        Returns:
            HTML documentation
        """
        if api_version is None:
            api_version = self.current_version
        elif isinstance(api_version, str):
            api_version = APIVersion(api_version)
        
        # Title and header
        title = f"Blender GraphQL MCP API Documentation v{api_version}"
        header = f"Blender GraphQL MCP API v{api_version}"
        description = "Unified API for interacting with Blender through GraphQL and REST"
        
        # Generate content sections
        overview_section = self._generate_overview_section(api_version)
        versions_section = self._generate_versions_section(api_version)
        rest_endpoints_section = self._generate_rest_endpoints_section(api_version)
        graphql_operations_section = self._generate_graphql_operations_section(api_version)
        models_section = self._generate_models_section(api_version)
        authentication_section = self._generate_authentication_section(api_version)
        examples_section = self._generate_examples_section(api_version)
        
        # Combine content sections
        content = (
            overview_section +
            versions_section +
            rest_endpoints_section +
            graphql_operations_section +
            models_section +
            authentication_section +
            examples_section
        )
        
        # Generate HTML
        html = HTML_TEMPLATE.format(
            title=title,
            header=header,
            description=description,
            version=str(api_version),
            content=content,
            generated_date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return html
    
    def save_html_doc(self, output_dir: str, api_version: Union[str, APIVersion] = None) -> str:
        """
        Generate HTML documentation for the API and save it to a file.
        
        Args:
            output_dir: Directory to save the documentation
            api_version: The API version to generate documentation for
            
        Returns:
            Path to the saved documentation file
        """
        if api_version is None:
            api_version = self.current_version
        elif isinstance(api_version, str):
            api_version = APIVersion(api_version)
        
        # Generate HTML
        html = self.generate_html_doc(api_version)
        
        # Create directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        file_path = output_path / f"api_docs_{api_version}.html"
        with open(file_path, "w") as f:
            f.write(html)
        
        logger.info(f"Saved HTML documentation to {file_path}")
        
        return str(file_path)
    
    def generate_versioned_docs(self, output_dir: str) -> Dict[str, str]:
        """
        Generate HTML documentation for all supported API versions.
        
        Args:
            output_dir: Directory to save the documentation
            
        Returns:
            Dictionary mapping version strings to file paths
        """
        # Create directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate documentation for each version
        result = {}
        
        for version in self.version_manager.supported_versions:
            version_str = str(version)
            file_path = self.save_html_doc(output_dir, version)
            result[version_str] = file_path
        
        # Also create a redirect to the current version
        redirect_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="refresh" content="0;url=api_docs_{self.current_version}.html">
            <title>Redirecting to current version</title>
        </head>
        <body>
            <p>Redirecting to the current version...</p>
            <p><a href="api_docs_{self.current_version}.html">Click here if you are not redirected automatically</a></p>
        </body>
        </html>
        """
        
        redirect_path = output_path / "index.html"
        with open(redirect_path, "w") as f:
            f.write(redirect_html)
        
        logger.info(f"Created redirect to current version at {redirect_path}")
        
        return result


def generate_documentation(server, output_dir: str) -> Dict[str, str]:
    """
    Generate documentation for the API.
    
    Args:
        server: The UnifiedServer instance
        output_dir: Directory to save the documentation
        
    Returns:
        Dictionary with paths to generated documentation files
    """
    # Create HTML generator
    html_generator = HTMLGenerator(server)
    
    # Generate versioned documentation
    result = html_generator.generate_versioned_docs(output_dir)
    
    return result