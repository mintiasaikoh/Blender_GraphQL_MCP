"""
Unified server main entry point.
Provides a function to start the unified server and CLI entry point.
"""

import sys
import argparse
import logging
from typing import Dict, Any, Optional

# Import server components
from .core.server import UnifiedServer
from .core.config import ServerConfig
from .utils.logging import setup_logging


def start_server(config: Optional[Dict[str, Any]] = None) -> UnifiedServer:
    """
    Start the unified server with the given configuration.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Server instance
    """
    # Create server config from dict if provided
    server_config = ServerConfig(**(config or {}))
    
    # Create and initialize server
    server = UnifiedServer(server_config)
    if not server.initialize():
        sys.exit(1)
    
    # Start server
    if not server.start():
        sys.exit(1)
    
    return server


def main() -> None:
    """Main entry point for the unified server CLI."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Blender GraphQL MCP Unified Server")
    parser.add_argument("--host", default="localhost", help="Host to bind server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind server to")
    parser.add_argument("--log-level", default="info", help="Logging level")
    parser.add_argument("--enable-cors", action="store_true", help="Enable CORS")
    parser.add_argument("--enable-graphql", action="store_true", help="Enable GraphQL API")
    parser.add_argument("--enable-rest", action="store_true", help="Enable REST API")
    parser.add_argument("--enable-docs", action="store_true", help="Enable API documentation")
    parser.add_argument("--config-file", help="Path to configuration file")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    setup_logging(log_level=log_level)
    
    # Create configuration from arguments
    config = {
        "host": args.host,
        "port": args.port,
        "log_level": log_level,
        "enable_cors": args.enable_cors,
        "enable_graphql": args.enable_graphql,
        "enable_rest": args.enable_rest,
        "enable_docs": args.enable_docs
    }
    
    # Load config file if provided
    if args.config_file:
        # Import config loader based on file extension
        import json
        import yaml
        import os
        
        file_ext = os.path.splitext(args.config_file)[1].lower()
        
        try:
            with open(args.config_file, "r") as f:
                if file_ext == ".json":
                    file_config = json.load(f)
                elif file_ext in (".yaml", ".yml"):
                    file_config = yaml.safe_load(f)
                else:
                    print(f"Unsupported config file format: {file_ext}")
                    sys.exit(1)
                
                # Update config with file values
                config.update(file_config)
        except Exception as e:
            print(f"Error loading config file: {e}")
            sys.exit(1)
    
    # Start server
    server = start_server(config)
    
    try:
        # Keep the main thread alive
        print(f"Server running at http://{config['host']}:{config['port']}")
        print("Press Ctrl+C to stop the server")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping server...")
        server.stop()
        print("Server stopped")


if __name__ == "__main__":
    main()