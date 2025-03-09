#!/usr/bin/env python3
"""
Cursor Adapter - Connects Cursor with MCP protocol including window screenshot support

This module provides an adapter to integrate the MCP protocol with Cursor,
allowing for communication between Cursor and language models using the MCP protocol,
with additional support for window screenshot functionality.
"""

import json
import asyncio
import sys
import os
import base64
import io
from typing import Dict, Any, Optional, List, Union, Tuple

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Import MCP client
from client.mcp_client import MCPClient

class CursorAdapter:
    """Adapter to connect Cursor with MCP protocol, including window screenshot support"""
    
    def __init__(self, mcp_server_url="ws://localhost:8765"):
        """
        Initialize the Cursor MCP adapter
        
        Args:
            mcp_server_url: URL of the MCP server
        """
        self.client = MCPClient(url=mcp_server_url)
        self.last_response = None
    
    async def send_to_model(self, 
                           prompt: str, 
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a prompt to the language model via MCP
        
        Args:
            prompt: The text prompt to send
            context: Optional context information
            
        Returns:
            Model response
        """
        if context is None:
            context = {}
            
        content = {
            "prompt": prompt,
            "context": context
        }
        
        # Connect to the server if not already connected
        if not self.client.connected:
            await self.client.connect()
            
        # Send the message
        response = await self.client.send_message("text", content)
        self.last_response = response
        return response
    
    async def get_completions(self, 
                             prompt: str, 
                             file_path: Optional[str] = None,
                             cursor_position: Optional[int] = None) -> List[str]:
        """
        Get completions from the language model
        
        Args:
            prompt: The prompt to send
            file_path: Optional file path for context
            cursor_position: Optional cursor position in the file
            
        Returns:
            List of completion strings
        """
        context = {}
        if file_path:
            context["file_path"] = file_path
        if cursor_position is not None:
            context["cursor_position"] = cursor_position
            
        response = await self.send_to_model(prompt, context)
        
        if "error" in response:
            return []
            
        content = response.get("content", {})
        completions = content.get("completions", [])
        
        if isinstance(completions, list):
            return completions
        return []
    
    async def get_explanation(self, code: str) -> str:
        """
        Get explanation for code from the language model
        
        Args:
            code: The code to explain
            
        Returns:
            Explanation string
        """
        prompt = f"Explain this code:\n\n{code}"
        response = await self.send_to_model(prompt)
        
        if "error" in response:
            return f"Error: {response.get('error')}"
            
        content = response.get("content", {})
        explanation = content.get("explanation", "")
        
        if not explanation:
            explanation = content.get("text", "No explanation available")
            
        return explanation
    
    async def get_window_list(self) -> List[Dict[str, str]]:
        """
        Get list of available windows
        
        Returns:
            List of window information dictionaries
        """
        # Connect to the server if not already connected
        if not self.client.connected:
            await self.client.connect()
            
        # Get window list
        windows = await self.client.get_window_list()
        return windows
    
    async def get_window_screenshot(self, window_id: str) -> Tuple[Optional[bytes], str]:
        """
        Get screenshot of a specific window
        
        Args:
            window_id: ID of the window to capture
            
        Returns:
            Tuple of (image_data, status_message)
        """
        # Connect to the server if not already connected
        if not self.client.connected:
            await self.client.connect()
            
        # Get window screenshot
        image_data, image_format = await self.client.get_window_screenshot(window_id)
        
        if not image_data:
            return None, "Failed to capture window screenshot"
            
        try:
            # Convert base64 string to bytes
            image_bytes = base64.b64decode(image_data)
            return image_bytes, "Screenshot captured successfully"
        except Exception as e:
            return None, f"Error processing screenshot: {str(e)}"
    
    def save_screenshot(self, image_data: bytes, filename: str) -> Optional[str]:
        """
        Save screenshot to file
        
        Args:
            image_data: Image data in bytes
            filename: Filename to save to
            
        Returns:
            Path to saved file or None if failed
        """
        if not image_data:
            return None
            
        try:
            # Save image data to file
            with open(filename, "wb") as f:
                f.write(image_data)
                
            # Get absolute path
            abs_path = os.path.abspath(filename)
            return abs_path
        except Exception as e:
            print(f"Error saving screenshot: {str(e)}")
            return None
    
    async def capture_and_save_window(self, window_id: str, filename: Optional[str] = None, save_locally: bool = True) -> Tuple[Optional[str], str]:
        """
        Capture window screenshot and save to file
        
        Args:
            window_id: ID of the window to capture
            filename: Optional filename to save to
            save_locally: Whether to save the screenshot locally (default: True)
            
        Returns:
            Tuple of (file_path, status_message)
        """
        # Generate filename if not provided
        if not filename:
            import time
            filename = f"window_shot_{int(time.time())}.png"
            
        # Get window screenshot
        image_data, status = await self.get_window_screenshot(window_id)
        
        if not image_data:
            return None, status
            
        # Save screenshot if requested
        if save_locally:
            file_path = self.save_screenshot(image_data, filename)
            
            if not file_path:
                return None, "Failed to save screenshot"
                
            return file_path, "Screenshot saved successfully"
        else:
            return None, "Screenshot captured but not saved locally"

async def main():
    """Test the Cursor adapter"""
    adapter = CursorAdapter()
    
    # Get window list
    windows = await adapter.get_window_list()
    
    if windows:
        print(f"Found {len(windows)} windows:")
        for i, window in enumerate(windows, 1):
            print(f"{i}. {window['title']} ({window['process']})")
            
        # Capture screenshot of first window
        if len(windows) > 0:
            window_id = windows[0]['id']
            print(f"\nCapturing screenshot of: {windows[0]['title']}")
            
            file_path, status = await adapter.capture_and_save_window(window_id)
            
            if file_path:
                print(f"Screenshot saved to: {file_path}")
            else:
                print(f"Failed to capture screenshot: {status}")
    else:
        print("No windows found")

if __name__ == "__main__":
    asyncio.run(main()) 