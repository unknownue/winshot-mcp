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
import time
import threading
import uuid
import tempfile
import hashlib
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
from typing import Dict, Any, Optional
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
parser.add_argument('--fileserver-port', type=int, default=8766, help='Port to run the file server on')
parser.add_argument('--max-image-dimension', type=int, default=1920, 
                   help='Maximum dimension (width or height) for screenshots in pixels')
parser.add_argument('--max-file-size-mb', type=int, default=5, 
                   help='Maximum file size for screenshots in MB')
parser.add_argument('--save-locally', action='store_true', default=False,
                   help='Whether to save screenshots locally on the server')
parser.add_argument('--tmp-dir', type=str, default=None,
                   help='Custom temporary directory for screenshots (defaults to system temp dir)')
parser.add_argument('--file-expiry-minutes', type=int, default=60,
                   help='Time in minutes after which temporary screenshot files will be deleted')
args = parser.parse_args()

# Set environment variable for SSE port
port = args.port
fileserver_port = args.fileserver_port
os.environ["FASTMCP_PORT"] = str(port)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    logger.error("MCP SDK not found. Please install it with 'pip install mcp'")
    logger.error("For more information, visit: https://modelcontextprotocol.io/")
    exit(1)

# Screenshot Manager Class
class ScreenshotManager:
    def __init__(self, base_dir=None, expiry_minutes=60):
        """
        Initialize the screenshot manager.
        
        Args:
            base_dir: Base directory for screenshots, if None uses project's tmp dir
            expiry_minutes: Time in minutes after which files should be deleted
        """
        # Create temporary directory, if not specified use the tmp directory in the project root
        if base_dir:
            self.tmp_dir = Path(base_dir)
        else:
            # Get project root directory
            project_root = Path(__file__).resolve().parent.parent
            self.tmp_dir = project_root / "tmp"
        
        os.makedirs(self.tmp_dir, exist_ok=True)
        logger.info(f"Screenshots temporary directory: {self.tmp_dir}")
        
        # Set file expiration time
        self.expiry_minutes = expiry_minutes
        
        # Create hash to file path mapping
        self.hash_to_path = {}
        
        # Start periodic cleanup
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start a background thread to periodically clean up old files."""
        def cleanup_task():
            while True:
                try:
                    self.cleanup_old_files()
                except Exception as e:
                    logger.error(f"Error in cleanup task: {str(e)}")
                # Check every 1/10 of the expiration time
                time.sleep(self.expiry_minutes * 60 / 10)
        
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
        
    def save_screenshot(self, image_data, window_title=None) -> tuple:
        """
        Save a screenshot to the temporary directory and generate a hash for it.
        
        Args:
            image_data: The image data (PIL Image or bytes)
            window_title: Optional window title for the filename
            
        Returns:
            Tuple of (file path, file hash)
        """
        # Generate unique filename
        safe_title = "unknown"
        if window_title:
            # Create safe filename
            safe_title = "".join(c if c.isalnum() else "_" for c in window_title)
            safe_title = safe_title[:50]  # Limit length
            
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex[:8]
        filename = f"window_shot_{safe_title}_{timestamp}_{unique_id}.png"
        filepath = self.tmp_dir / filename
        
        # Save image
        if hasattr(image_data, 'save'):  # PIL Image
            image_data.save(filepath)
        else:  # Byte data
            with open(filepath, 'wb') as f:
                f.write(image_data)
        
        # Generate file hash
        file_hash = self._generate_file_hash(filepath, safe_title, timestamp)
        
        # Store hash to file path mapping
        self.hash_to_path[file_hash] = filepath
                
        logger.info(f"Screenshot saved to {filepath} with hash {file_hash}")
        return filepath, file_hash

    def _generate_file_hash(self, filepath, title, timestamp):
        """
        Generate a unique hash for a file.
        
        Args:
            filepath: Path to the file
            title: Window title
            timestamp: Timestamp when file was created
            
        Returns:
            Unique hash string
        """
        # Combine filename and timestamp to generate hash
        hash_input = f"{filepath}_{title}_{timestamp}_{uuid.uuid4().hex}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
        
    def get_file_by_hash(self, file_hash) -> Optional[Path]:
        """
        Get file path by its hash.
        
        Args:
            file_hash: Hash of the file
            
        Returns:
            Path to the file or None if not found
        """
        return self.hash_to_path.get(file_hash)
        
    def cleanup_old_files(self):
        """Delete files that are older than the expiry time."""
        now = time.time()
        expiry_seconds = self.expiry_minutes * 60
        count = 0
        
        # Create list of hashes to remove
        hashes_to_remove = []
        
        # Check each file
        for file_path in self.tmp_dir.glob("window_shot_*.png"):
            if os.path.isfile(file_path):
                file_age = now - os.stat(file_path).st_mtime
                if file_age > expiry_seconds:
                    try:
                        os.remove(file_path)
                        count += 1
                        
                        # Find and mark corresponding hash
                        for h, p in self.hash_to_path.items():
                            if p == file_path:
                                hashes_to_remove.append(h)
                                break
                    except Exception as e:
                        logger.error(f"Error deleting old file {file_path}: {str(e)}")
        
        # Remove expired hashes from mapping
        for h in hashes_to_remove:
            if h in self.hash_to_path:
                del self.hash_to_path[h]
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired screenshot files")

# File Server Class
class ScreenshotFileServer:
    def __init__(self, directory, screenshot_manager, port=8766, host='localhost'):
        """
        Initialize the screenshot file server.
        
        Args:
            directory: Directory to serve files from
            screenshot_manager: Screenshot manager instance for hash lookups
            port: Port to run the server on
            host: Host to bind the server to
        """
        self.directory = directory
        self.port = port
        self.host = host
        self.httpd = None
        self.server_thread = None
        self.screenshot_manager = screenshot_manager
        
    def start(self):
        """Start the file server in a background thread."""
        # Create handler and set file directory
        screenshot_manager = self.screenshot_manager  # Closure reference
        
        class HashBasedHandler(SimpleHTTPRequestHandler):
            # Save directory as class variable so all instances can access it
            directory = str(self.directory)
            
            def __init__(self, *args, **kwargs):
                # Use class variable directly as directory instead of getting from server
                super().__init__(*args, directory=self.directory, **kwargs)
                
            def log_message(self, format, *args):
                # Redirect logs to our logging system
                logger.debug(f"FileServer: {format % args}")
                
            def do_GET(self):
                """Handle GET requests, supporting file access via hash"""
                # Get request path
                path = self.path.strip('/')
                
                # Check if it's a hash access path
                if path.startswith('img/'):
                    # Extract hash from path
                    file_hash = path[4:]  # Remove 'img/' prefix
                    
                    # Check if hash is valid
                    if not all(c in '0123456789abcdef' for c in file_hash.lower()):
                        self.send_error(400, "Invalid hash format")
                        return
                    
                    # Get file path by hash
                    file_path = screenshot_manager.get_file_by_hash(file_hash)
                    
                    if not file_path or not os.path.isfile(file_path):
                        self.send_error(404, "File not found")
                        return
                    
                    # Serve file
                    self.send_response(200)
                    self.send_header('Content-type', 'image/png')
                    self.send_header('Cache-Control', 'max-age=600')  # 10 minutes cache
                    self.end_headers()
                    
                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    # For other paths, use default handler
                    super().do_GET()
        
        # Create reusable address server
        class ReusableTCPServer(socketserver.TCPServer):
            allow_reuse_address = True
        
        # Create and configure server
        server = ReusableTCPServer((self.host, self.port), HashBasedHandler)
        self.httpd = server
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True  # Set as daemon thread, terminates when main program exits
        self.server_thread.start()
        
        logger.info(f"Screenshot file server started at http://{self.host}:{self.port}")
        
    def stop(self):
        """Stop the file server."""
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            logger.info("Screenshot file server stopped")
    
    def get_uri_for_hash(self, file_hash):
        """
        Get the URI for a file hash.
        
        Args:
            file_hash: Hash of the file
            
        Returns:
            URI for accessing the file via hash
        """
        return f"http://{self.host}:{self.port}/img/{file_hash}"

# Initialize WindowShot with configuration
window_shot = WindowShot(
    max_image_dimension=args.max_image_dimension,
    max_file_size_mb=args.max_file_size_mb,
    save_locally=args.save_locally
)

# Initialize screenshot manager and file server
screenshot_manager = ScreenshotManager(args.tmp_dir, args.file_expiry_minutes)
file_server = ScreenshotFileServer(screenshot_manager.tmp_dir, screenshot_manager, args.fileserver_port)
file_server.start()

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
    Capture screenshot of a specific application window using fuzzy matching.
    Will use the first matching window if multiple matches are found.
    
    Args:
        app_name: Name or partial name of the application to capture
        
    Returns:
        A dictionary containing the URI to the screenshot and format
    """
    try:
        # Get list of windows
        windows = window_shot.get_window_list()
        
        # Find first matching window (case insensitive)
        matching_window = None
        for window in windows:
            # Check both process name and window title for matches
            if (app_name.lower() in window["process"].lower() or 
                app_name.lower() in window["title"].lower()):
                matching_window = window
                break
        
        # If no match found, return error
        if matching_window is None:
            logger.error(f"No windows found matching: {app_name}")
            return {
                "error": f"No windows found matching: {app_name}",
                "uri": None,
                "format": None
            }
        
        window_id = matching_window["id"]
        window_title = matching_window["title"]
        
        logger.info(f"Found window ID {window_id} for query '{app_name}' (process: {matching_window['process']}, title: {window_title})")
        
        # Capture window screenshot
        image_data = window_shot.capture_window(window_id)
        
        # Check if capture was successful
        if image_data is None:
            logger.error("Screenshot capture failed")
            return {
                "error": "Failed to capture screenshot",
                "uri": None,
                "format": None
            }
        
        # Save screenshot to temporary directory and get hash
        screenshot_file, file_hash = screenshot_manager.save_screenshot(image_data, window_title)
        
        # Get hash-based URI
        screenshot_uri = file_server.get_uri_for_hash(file_hash)
        
        # Get absolute file path (for Cursor @file syntax)
        absolute_file_path = str(screenshot_file.absolute())
        
        logger.info(f"Screenshot available at: {screenshot_uri}")
        logger.info(f"Local file path: {absolute_file_path}")
        
        # Return URI and local file path
        return {
            "uri": screenshot_uri,
            "format": "png",
            "window_id": window_id,
            "window_title": window_title,
            "process": matching_window["process"],
            "hash": file_hash,
            "local_file_path": absolute_file_path,
            "cursor_syntax": f"@{absolute_file_path}"
        }
    except Exception as e:
        logger.error(f"Error capturing window for query '{app_name}': {str(e)}")
        return {
            "error": f"Failed to capture window for query '{app_name}': {str(e)}",
            "uri": None,
            "format": None
        }

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    """Handle termination signals for graceful shutdown."""
    logger.info("Received termination signal. Shutting down...")
    file_server.stop()
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

# Main function to run the server
def main():
    # Log server startup information
    logger.info(f"Starting Winshot MCP server on port {port}")
    logger.info(f"File server running on port {fileserver_port}")
    logger.info(f"Maximum image dimension: {args.max_image_dimension}px")
    logger.info(f"Maximum file size: {args.max_file_size_mb}MB")
    logger.info(f"Save screenshots locally: {args.save_locally}")
    logger.info(f"Screenshot file expiry: {args.file_expiry_minutes} minutes")
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
        file_server.stop()
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    main() 