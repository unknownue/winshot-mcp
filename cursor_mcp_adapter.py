#!/usr/bin/env python3
"""
Cursor MCP Adapter - Connects Cursor with MCP protocol including window screenshot support

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
from mcp_client import MCPClient

class CursorMCPAdapter:
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
            Dict: The model's response
        """
        # Prepare the message content
        content = {
            "prompt": prompt
        }
        
        # Add context if provided
        if context:
            content["context"] = context
        
        # Send the message and get response
        response = await self.client.send_message(
            content=json.dumps(content),
            message_type="cursor_prompt"
        )
        
        self.last_response = response
        return response
    
    async def get_completions(self, 
                             prompt: str, 
                             file_path: Optional[str] = None,
                             cursor_position: Optional[int] = None) -> List[str]:
        """
        Get code completions from the model
        
        Args:
            prompt: The code context
            file_path: Path to the file being edited
            cursor_position: Position of the cursor in the file
            
        Returns:
            List[str]: List of completion suggestions
        """
        context = {}
        if file_path:
            context["file_path"] = file_path
        if cursor_position is not None:
            context["cursor_position"] = cursor_position
        
        response = await self.send_to_model(prompt, context)
        
        # Extract completions from response
        try:
            if response.get("type") == "function_result":
                content = response.get("content", {})
                if isinstance(content, str):
                    content = json.loads(content)
                return content.get("completions", [])
            return []
        except Exception as e:
            print(f"Error extracting completions: {e}")
            return []
    
    async def get_explanation(self, code: str) -> str:
        """
        Get explanation for a piece of code
        
        Args:
            code: The code to explain
            
        Returns:
            str: Explanation of the code
        """
        context = {"request_type": "explanation"}
        response = await self.send_to_model(code, context)
        
        # Extract explanation from response
        try:
            if response.get("type") == "text":
                return response.get("content", "No explanation available")
            return "No explanation available"
        except Exception as e:
            print(f"Error extracting explanation: {e}")
            return "Error getting explanation"
    
    async def get_window_list(self) -> List[Dict[str, str]]:
        """
        Get a list of available windows from the MCP server
        
        Returns:
            List[Dict[str, str]]: List of window information dictionaries
        """
        # Send window list request
        response = await self.client.send_message(
            content="{}",
            message_type="window_list_request"
        )
        
        # Process response
        try:
            if response.get("type") == "window_list_response":
                content = response.get("content", {})
                if isinstance(content, str):
                    content = json.loads(content)
                return content.get("windows", [])
            return []
        except Exception as e:
            print(f"Error getting window list: {e}")
            return []
    
    async def get_window_screenshot(self, window_id: str) -> Tuple[Optional[bytes], str]:
        """
        Get a screenshot of a specific window
        
        Args:
            window_id: ID of the window to capture
            
        Returns:
            Tuple[Optional[bytes], str]: Screenshot image data (or None if failed) and status message
        """
        # Prepare request content
        content = {
            "window_id": window_id
        }
        
        # Send screenshot request
        response = await self.client.send_message(
            content=json.dumps(content),
            message_type="window_screenshot_request"
        )
        
        # Process response
        try:
            if response.get("type") == "window_screenshot_response":
                content = response.get("content", {})
                if isinstance(content, str):
                    content = json.loads(content)
                
                status = content.get("status")
                if status == "success":
                    # Now we expect path instead of base64 data
                    screenshot_path = content.get("screenshot_path", "")
                    if screenshot_path:
                        return None, f"success:{screenshot_path}"
                
                return None, f"Failed to get screenshot: {content.get('message', 'Unknown error')}"
            
            elif response.get("type") == "error":
                content = response.get("content", {})
                if isinstance(content, str):
                    content = json.loads(content)
                return None, f"Error: {content.get('message', 'Unknown error')}"
            
            return None, "Unknown response type"
        
        except Exception as e:
            print(f"Error processing screenshot response: {e}")
            return None, f"Error: {str(e)}"
    
    def save_screenshot(self, image_data: bytes, filename: str) -> Optional[str]:
        """
        Save screenshot data to a file
        
        Args:
            image_data: Raw image data (bytes)
            filename: Filename to save the screenshot to
            
        Returns:
            Optional[str]: Path to the saved file, or None if failed
        """
        try:
            # Save the raw image data to a file
            with open(filename, "wb") as f:
                f.write(image_data)
            return os.path.abspath(filename)
        except Exception as e:
            print(f"Error saving screenshot: {e}")
            return None
    
    async def capture_and_save_window(self, window_id: str, filename: Optional[str] = None) -> Tuple[Optional[str], str]:
        """
        Capture a window screenshot and save it to a file
        
        Args:
            window_id: ID of the window to capture
            filename: Filename to save the screenshot to (optional)
            
        Returns:
            Tuple[Optional[str], str]: Path to the saved file (or None if failed) and status message
        """
        # Generate a filename if not provided
        if filename is None:
            import time
            filename = f"window_shot_{int(time.time())}.png"
        
        # Get the screenshot
        _, status = await self.get_window_screenshot(window_id)
        
        # Check if the status contains a path
        if status.startswith("success:"):
            # Extract path from status
            screenshot_path = status.split(":", 1)[1]
            return screenshot_path, "success"
        
        return None, status

async def main():
    """Main function for testing the adapter"""
    adapter = CursorMCPAdapter()
    
    # Test window list functionality
    print("\n=== Getting Window List ===")
    windows = await adapter.get_window_list()
    
    if windows:
        print(f"Found {len(windows)} windows:")
        for i, window in enumerate(windows, 1):
            print(f"{i}. {window['title']} ({window['process']})")
        
        # Test window screenshot functionality with the first window
        if len(windows) > 0:
            print("\n=== Capturing Window Screenshot ===")
            window_id = windows[0]['id']
            print(f"Capturing screenshot of: {windows[0]['title']}")
            
            screenshot_path, status = await adapter.capture_and_save_window(window_id)
            
            if screenshot_path:
                print(f"Screenshot saved to: {screenshot_path}")
            else:
                print(f"Failed to capture screenshot: {status}")
    else:
        print("No windows found")

if __name__ == "__main__":
    asyncio.run(main()) 