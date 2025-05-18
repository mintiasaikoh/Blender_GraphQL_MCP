"""
GraphiQL module for UnifiedServer.
Provides HTML for the GraphiQL interface with enhanced LLM-specific documentation.
"""

# Import for version information
import platform
import sys
import datetime

# GraphiQL template HTML
GRAPHIQL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>GraphiQL - Blender GraphQL MCP</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body {
            height: 100%;
            margin: 0;
            width: 100%;
            overflow: hidden;
        }
        
        #graphiql {
            height: 100vh;
        }
        
        /* Toolbar styling */
        .graphiql-container .toolbar {
            background: #f3f3f3;
            border-bottom: 1px solid #e1e1e1;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .graphiql-container .title {
            font-weight: bold;
            font-size: 16px;
            color: #333;
        }
        
        .graphiql-container .docExplorerShow {
            background: #f6f6f6;
            border: 1px solid #e1e1e1;
            border-radius: 3px;
            padding: 4px 8px;
            margin-left: 16px;
            cursor: pointer;
        }
    </style>
    
    <!-- Load React dependencies -->
    <script 
        crossorigin 
        src="https://unpkg.com/react@17/umd/react.production.min.js"
    ></script>
    <script 
        crossorigin 
        src="https://unpkg.com/react-dom@17/umd/react-dom.production.min.js"
    ></script>
    
    <!-- Load GraphiQL dependencies -->
    <link href="https://unpkg.com/graphiql@2.0.9/graphiql.min.css" rel="stylesheet" />
    <script
        crossorigin
        src="https://unpkg.com/graphiql@2.0.9/graphiql.min.js"
    ></script>
</head>
<body>
    <div id="graphiql">Loading GraphiQL...</div>
    <script>
        // Fetch schema and execute queries
        const fetcher = async (params) => {
            const response = await fetch('/graphql', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(params),
                credentials: 'same-origin',
            });
            
            // Handle both JSON and text responses
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            } else {
                return { 
                    errors: [{ message: await response.text() }] 
                };
            }
        };
        
        // Initialize GraphiQL
        ReactDOM.render(
            React.createElement(GraphiQL, {
                fetcher: fetcher,
                defaultVariableEditorOpen: true,
                defaultSecondaryEditorOpen: true,
                headerEditorEnabled: true,
                shouldPersistHeaders: true,
                docExplorerOpen: false,
            }),
            document.getElementById('graphiql')
        );
    </script>
</body>
</html>
"""

# Add LLM-specific documentation queries
LLM_DOCUMENTATION_QUERIES = """
# LLM-specific queries
# These queries provide additional documentation and schema information
# specifically designed for LLMs (Large Language Models)

# Get a list of all available GraphQL functions
query GetLLMFunctionList {
  _llmFunctionList
}

# Get detailed information about a specific function
query GetLLMFunctionInfo {
  _llmFunctionInfo(functionName: "createObject")
}

# Get complete schema documentation in Markdown format
query GetLLMSchemaDoc {
  _llmSchemaDoc
}

# Example: Create a simple cube
mutation CreateCubeExample {
  createObject(
    type: CUBE
    name: "MyCube"
    location: {x: 0, y: 0, z: 0}
  ) {
    success
    message
    object {
      name
      type
      location {
        x
        y
        z
      }
    }
  }
}

# Example: Get current scene information
query GetSceneInfoExample {
  sceneInfo {
    name
    objects {
      name
      type
      location {
        x
        y
        z
      }
    }
    frame_current
    active_object
  }
}
"""

def get_graphiql_html(path_prefix: str = '') -> str:
    """
    Get GraphiQL HTML template with LLM-specific enhancements.

    Args:
        path_prefix: Optional path prefix for GraphQL endpoint

    Returns:
        GraphiQL HTML
    """
    # Get system information for documentation
    system_info = {
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "graphql_endpoint": f"{path_prefix}/graphql" if path_prefix else "/graphql"
    }

    # Create custom HTML with LLM documentation
    html = GRAPHIQL_TEMPLATE

    # Add LLM documentation tab
    llm_doc_tab = f"""
    <script>
      // Add LLM documentation tabs after GraphiQL loads
      window.addEventListener('load', function() {{
        // Wait for GraphiQL to initialize
        setTimeout(function() {{
          // Add LLM example queries button to toolbar
          const toolbar = document.querySelector('.graphiql-container .toolbar');
          if (toolbar) {{
            const llmButton = document.createElement('button');
            llmButton.textContent = 'LLM Examples';
            llmButton.className = 'docExplorerShow';
            llmButton.onclick = function() {{
              // Set example queries in the editor
              const editor = document.querySelector('.graphiql-container .CodeMirror');
              if (editor && editor.CodeMirror) {{
                editor.CodeMirror.setValue(`{LLM_DOCUMENTATION_QUERIES}`);
              }}
            }};
            toolbar.appendChild(llmButton);
          }}

          // Add system info to footer
          const footer = document.createElement('div');
          footer.style.padding = '8px 16px';
          footer.style.fontSize = '12px';
          footer.style.borderTop = '1px solid #e1e1e1';
          footer.style.color = '#666';
          footer.innerHTML = `
            <div>Blender GraphQL MCP Server</div>
            <div>Platform: {system_info["platform"]}</div>
            <div>Python: {system_info["python_version"]}</div>
            <div>GraphQL Endpoint: {system_info["graphql_endpoint"]}</div>
            <div>Generated: {system_info["timestamp"]}</div>
          `;

          const container = document.querySelector('.graphiql-container');
          if (container) {{
            container.appendChild(footer);
          }}
        }}, 1000);
      }});
    </script>
    """

    # Insert the script before the closing body tag
    html = html.replace('</body>', f'{llm_doc_tab}</body>')

    # Update GraphQL endpoint in template if path prefix is provided
    if path_prefix:
        # Add trailing slash to path prefix if not present
        if not path_prefix.endswith('/'):
            path_prefix += '/'

        # Replace GraphQL endpoint in template
        graphql_endpoint = f"'{path_prefix}graphql'"
        html = html.replace("'/graphql'", graphql_endpoint)

    return html