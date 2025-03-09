#!/usr/bin/env python3
"""
MCP Server - Server implementation for Model-Client Protocol with window screenshot support

This module provides a server that implements the Model-Client Protocol (MCP)
for communication with Language Learning Models using Server-Sent Events (SSE),
including window screenshot functionality.
"""

import argparse
import json
import base64
import logging
import sys
import os
import signal
from typing import Dict, Any
from core.winshot import WindowShot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("winshot-mcp-server")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run an MCP server with window screenshot support')
parser.add_argument('--port', type=int, default=8765, help='Port to run the server on')
args = parser.parse_args()

# Set environment variable for SSE port
port = args.port
os.environ["FASTMCP_PORT"] = str(port)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: MCP SDK not found. Please install it with 'pip install mcp'")
    print("For more information, visit: https://modelcontextprotocol.io/")
    exit(1)

# Initialize WindowShot
window_shot = WindowShot()

# Initialize FastMCP server
mcp = FastMCP(
    "Winshot MCP Server",
    initialization_delay=1.0
)

@mcp.tool()
def list_windows() -> Dict[str, Any]:
    """
    List all available windows.
    
    Returns:
        A dictionary containing a list of available windows
    """
    try:
        windows = window_shot.get_window_list()
        return {
            "windows": windows
        }
    except Exception as e:
        logger.error(f"Error listing windows: {str(e)}")
        return {
            "error": f"Failed to list windows: {str(e)}",
            "windows": []
        }

@mcp.tool()
def capture_window(app_name: str) -> Dict[str, Any]:
    """
    Capture screenshot of a specific application window.
    
    Args:
        app_name: Name of the application to capture
        
    Returns:
        A dictionary containing the captured image data and format
    """
    try:
        # Get list of windows
        windows = window_shot.get_window_list()
        
        # Find window by application name (case insensitive)
        window_id = None
        for window in windows:
            if window["process"].lower() == app_name.lower():
                window_id = window["id"]
                break
        
        # If no exact match, try partial match
        if window_id is None:
            for window in windows:
                if app_name.lower() in window["process"].lower():
                    window_id = window["id"]
                    break
        
        # If still no match, return error
        if window_id is None:
            logger.error(f"No window found for application: {app_name}")
            return {
                "error": f"No window found for application: {app_name}",
                "image_data": None,
                "format": None
            }
        
        logger.info(f"Found window ID {window_id} for application {app_name}")
        
        # Capture window screenshot
        image_data = window_shot.capture_window(window_id)
        
        # Convert image data to base64 if it's not already
        if not isinstance(image_data, str):
            # Check if it's a PIL Image object
            if hasattr(image_data, 'format') and hasattr(image_data, 'save'):
                # Use the get_screenshot_as_base64 method to convert PIL Image to base64
                image_data = window_shot.get_screenshot_as_base64(image_data)
            else:
                # If it's bytes or another format, encode it directly
                image_data = base64.b64encode(image_data).decode('utf-8')

        return {
            "image_data": image_data,
            "format": "png",
            "window_id": window_id
        }
    except Exception as e:
        logger.error(f"Error capturing window for application {app_name}: {str(e)}")
        return {
            "error": f"Failed to capture window for application {app_name}: {str(e)}",
            "image_data": None,
            "format": None
        }

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    """Handle termination signals for graceful shutdown."""
    logger.info("Received termination signal. Shutting down...")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

# Main function to run the server
def main():
    # Log server startup information
    logger.info(f"Starting Winshot MCP server on port {port}")
    logger.info(f"SSE endpoint: http://localhost:{port}/sse")
    logger.info("Press Ctrl+C to stop the server")

    try:
        # Run the server with SSE transport
        mcp.run(transport='sse')
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {str(e)}")
    finally:
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    main() 