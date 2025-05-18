"""
Static file handler for API documentation.
Provides a FastAPI route for serving static documentation files.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from pathlib import Path

# Import FastAPI components
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Import version manager
from ..api.version_manager import VersionManager

# Logger
logger = logging.getLogger("unified_server.docs.static_handler")


class APIDocsHandler:
    """
    Handler for API documentation static files.
    """
    
    def __init__(self, server, docs_dir: str):
        """
        Initialize the API docs handler.
        
        Args:
            server: The UnifiedServer instance
            docs_dir: Directory containing API documentation files
        """
        self.server = server
        self.app = server.app
        self.docs_dir = docs_dir
        self.version_manager = VersionManager.get_instance()
        
        # Create docs directory if it doesn't exist
        Path(docs_dir).mkdir(parents=True, exist_ok=True)
        
        # Create router for documentation
        self.router = APIRouter(prefix="/docs/api")
        
        # Set up routes
        self._setup_routes()
        
        # Set up static files
        self._setup_static_files()
    
    def _setup_routes(self) -> None:
        """Set up routes for documentation."""
        # API versions information
        @self.router.get("/versions", response_class=JSONResponse)
        async def get_api_versions():
            """
            Get information about all API versions.
            
            Returns:
                JSON response with API versions information
            """
            return {
                "current_version": str(self.version_manager.current_version),
                "supported_versions": [str(v) for v in self.version_manager.supported_versions]
            }
        
        # Get documentation for a specific API version
        @self.router.get("/v/{version}", response_class=HTMLResponse)
        async def get_api_docs(version: str, request: Request):
            """
            Get API documentation for a specific version.
            
            Args:
                version: API version
                request: Request object
                
            Returns:
                HTML response with API documentation
            """
            try:
                # Check if the version exists
                file_path = os.path.join(self.docs_dir, f"api_docs_{version}.html")
                
                if not os.path.exists(file_path):
                    # Check if we have the current version
                    current_version = str(self.version_manager.current_version)
                    current_file_path = os.path.join(self.docs_dir, f"api_docs_{current_version}.html")
                    
                    if not os.path.exists(current_file_path):
                        # Generate documentation for the current version
                        from .html_generator import HTMLGenerator
                        generator = HTMLGenerator(self.server)
                        generator.save_html_doc(self.docs_dir, current_version)
                    
                    if version != current_version:
                        # Redirect to the current version
                        return HTMLResponse(f"""
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <meta http-equiv="refresh" content="0;url=/docs/api/v/{current_version}">
                            <title>Redirecting to current version</title>
                        </head>
                        <body>
                            <p>Version {version} is not available. Redirecting to the current version {current_version}...</p>
                            <p><a href="/docs/api/v/{current_version}">Click here if you are not redirected automatically</a></p>
                        </body>
                        </html>
                        """)
                
                # Return the API documentation
                return FileResponse(file_path)
            except Exception as e:
                logger.error(f"Error getting API docs for version {version}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error getting API docs for version {version}: {str(e)}"
                )
        
        # Include the router in the app
        self.app.include_router(self.router)
    
    def _setup_static_files(self) -> None:
        """Set up static files for documentation."""
        # Set up static files
        try:
            # Mount static files directory
            self.app.mount(
                "/docs/static",
                StaticFiles(directory=os.path.join(self.docs_dir, "static")),
                name="api_docs_static"
            )
            
            # Create static files directory if it doesn't exist
            static_dir = os.path.join(self.docs_dir, "static")
            Path(static_dir).mkdir(parents=True, exist_ok=True)
            
            # Create CSS file
            css_dir = os.path.join(static_dir, "css")
            Path(css_dir).mkdir(parents=True, exist_ok=True)
            
            with open(os.path.join(css_dir, "styles.css"), "w") as f:
                f.write("""
                /* Base styles */
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }
                
                /* Header styles */
                header {
                    background-color: #343a40;
                    color: white;
                    padding: 1rem;
                    margin-bottom: 2rem;
                    border-radius: 5px;
                }
                
                header h1 {
                    margin: 0;
                    font-size: 1.8rem;
                }
                
                /* Rest of CSS styles... */
                """)
            
            # Create JavaScript file
            js_dir = os.path.join(static_dir, "js")
            Path(js_dir).mkdir(parents=True, exist_ok=True)
            
            with open(os.path.join(js_dir, "script.js"), "w") as f:
                f.write("""
                // Toggle navigation on mobile
                function toggleNav() {
                    const nav = document.querySelector('nav ul');
                    nav.classList.toggle('active');
                }
                
                // Add copy buttons to code blocks
                document.addEventListener('DOMContentLoaded', function() {
                    const codeBlocks = document.querySelectorAll('pre');
                    
                    codeBlocks.forEach(function(codeBlock) {
                        const copyButton = document.createElement('button');
                        copyButton.className = 'copy-button';
                        copyButton.textContent = 'Copy';
                        
                        copyButton.addEventListener('click', function() {
                            const code = codeBlock.querySelector('code').textContent;
                            navigator.clipboard.writeText(code).then(function() {
                                copyButton.textContent = 'Copied!';
                                setTimeout(function() {
                                    copyButton.textContent = 'Copy';
                                }, 2000);
                            });
                        });
                        
                        codeBlock.prepend(copyButton);
                    });
                });
                """)
            
            # Create images directory
            img_dir = os.path.join(static_dir, "img")
            Path(img_dir).mkdir(parents=True, exist_ok=True)
            
            logger.info("Set up static files for API documentation")
        except Exception as e:
            logger.error(f"Error setting up static files for API documentation: {e}")
    
    def generate_docs(self) -> Dict[str, str]:
        """
        Generate API documentation.
        
        Returns:
            Dictionary with paths to generated documentation files
        """
        try:
            # Import HTML generator
            from .html_generator import generate_documentation
            
            # Generate documentation
            result = generate_documentation(self.server, self.docs_dir)
            
            logger.info(f"Generated API documentation: {result}")
            
            return result
        except Exception as e:
            logger.error(f"Error generating API documentation: {e}")
            return {}


def setup_api_docs(server, docs_dir: str) -> APIDocsHandler:
    """
    Set up API documentation.
    
    Args:
        server: The UnifiedServer instance
        docs_dir: Directory to store API documentation
        
    Returns:
        APIDocsHandler instance
    """
    # Create API docs handler
    handler = APIDocsHandler(server, docs_dir)
    
    # Generate documentation
    handler.generate_docs()
    
    return handler