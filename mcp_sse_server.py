#!/usr/bin/env python3
"""
MCP SSE Server - Server implementation for Model-Client Protocol with window screenshot support

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
import time
import uuid
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from winshot import WindowShot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mcp_server.log')
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

# Initialize FastMCP server
mcp = FastMCP("Winshot MCP Server")

# Initialize WindowShot
window_shot = WindowShot()

# Track server start time for uptime calculation
START_TIME = time.time()

# Helper functions
def get_uptime() -> str:
    """Get the server uptime as a formatted string."""
    uptime_seconds = time.time() - START_TIME
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

@mcp.tool()
def get_server_status() -> Dict[str, Any]:
    """
    Get the current status of the MCP server.
    
    Returns information about the server's status, including uptime and connection count.
    """
    return {
        "status": "online",
        "uptime": get_uptime(),
        "message": "Server is running normally"
    }

@mcp.tool()
def echo_message(message: str) -> Dict[str, Any]:
    """
    Echo back a message sent by the client.
    
    Args:
        message: The message to echo back
        
    Returns:
        A dictionary containing the original message, echoed message, and timestamp
    """
    return {
        "original_message": message,
        "echoed_message": message,
        "timestamp": datetime.now().isoformat()
    }

@mcp.tool()
def get_current_time(format: str = "ISO") -> Dict[str, Any]:
    """
    Get the current server time.
    
    Args:
        format: The format to return the time in (default: ISO)
               Supported formats: ISO, RFC, HUMAN
               
    Returns:
        A dictionary containing the current time, format used, and timezone
    """
    now = datetime.now()
    
    if format.upper() == "ISO":
        time_str = now.isoformat()
    elif format.upper() == "RFC":
        time_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    elif format.upper() == "HUMAN":
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    else:
        time_str = now.isoformat()
    
    return {
        "current_time": time_str,
        "format": format,
        "timezone": "UTC"  # Simplified, in a real implementation you would use the actual timezone
    }

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
        logger.error(f"Error listing windows: {str(e)}\n{traceback.format_exc()}")
        return {
            "error": f"Failed to list windows: {str(e)}",
            "windows": []
        }

@mcp.tool()
def capture_window(window_id: str) -> Dict[str, Any]:
    """
    Capture screenshot of a specific window.
    
    Args:
        window_id: ID or title of the window to capture
        
    Returns:
        A dictionary containing the captured image data and format
    """
    try:
        # Capture window screenshot
        image_data = window_shot.capture_window(window_id)
        
        # Convert image data to base64 if it's not already
        if not isinstance(image_data, str):
            image_data = base64.b64encode(image_data).decode('utf-8')

        return {
            "image_data": image_data,
            "format": "png"
        }
    except Exception as e:
        logger.error(f"Error capturing window: {str(e)}\n{traceback.format_exc()}")
        return {
            "error": f"Failed to capture window: {str(e)}",
            "image_data": None,
            "format": None
        }

@mcp.prompt()
def test_tools() -> str:
    """
    A prompt to test the available tools.
    
    This prompt guides the user through testing the available tools in the MCP server.
    """
    return """
    Let's test the tools available in this Winshot MCP server:
    
    1. First, use the get_server_status tool to check if the server is running properly.
    2. Then, use the list_windows tool to see all available windows.
    3. Use the capture_window tool with a window_id from the list to capture a screenshot.
    4. You can also use the echo_message tool with a message of your choice.
    5. Finally, use the get_current_time tool to get the current server time.
    
    After testing these tools, please provide a summary of your findings.
    """

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    """Handle termination signals for graceful shutdown."""
    logger.info("Received termination signal. Shutting down...")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

# Log server startup information
logger.info(f"Starting Winshot MCP server with SSE transport on port {port}")
logger.info(f"SSE endpoint: http://localhost:{port}/sse")
logger.info("Press Ctrl+C to stop the server")

try:
    # Run the server with SSE transport
    mcp.run(transport='sse')
except KeyboardInterrupt:
    logger.info("Server stopped by user (Ctrl+C)")
except Exception as e:
    logger.error(f"Error running server: {str(e)}")
finally:
    logger.info("Server shutdown complete") 