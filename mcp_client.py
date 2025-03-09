#!/usr/bin/env python3
"""
MCP Client - Implementation of Model-Client Protocol with window screenshot support

This module provides a client implementation for the Model-Client Protocol (MCP)
to communicate with Language Learning Models, including window screenshot functionality.
"""

import json
import uuid
import asyncio
import websockets
import logging
from typing import Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPClient:
    """MCP protocol client implementation with window screenshot support"""
    
    def __init__(self, url="ws://localhost:8765"):
        """
        Initialize MCP client
        
        Args:
            url: WebSocket server URL
        """
        self.url = url
        self.session_id = str(uuid.uuid4())
        self.message_counter = 0
    
    def _generate_message_id(self):
        """Generate unique message ID"""
        self.message_counter += 1
        return f"{self.session_id}-{self.message_counter}"
    
    def create_request(self, content, message_type="text"):
        """
        Create MCP request message
        
        Args:
            content: Message content
            message_type: Message type, default is 'text'
            
        Returns:
            dict: Formatted MCP request
        """
        request = {
            "id": self._generate_message_id(),
            "type": message_type,
            "content": content
        }
        return request
    
    async def send_message(self, content, message_type="text"):
        """
        Send message to MCP server and wait for response
        
        Args:
            content: Message content
            message_type: Message type, default is 'text'
            
        Returns:
            dict: Server response
        """
        request = self.create_request(content, message_type)
        
        try:
            # Set a larger max_size for websocket messages (100MB)
            async with websockets.connect(self.url, max_size=100 * 1024 * 1024) as websocket:
                # Send request
                await websocket.send(json.dumps(request))
                logger.info(f"Sent: {request}")
                
                # Receive response
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # For window screenshot responses, log a placeholder instead of the full base64 data
                if response_data.get("type") == "window_screenshot_response" and "image_data" in response_data.get("content", {}):
                    log_data = response_data.copy()
                    log_data["content"]["image_data"] = "[BASE64_IMAGE_DATA]"
                    logger.info(f"Received: {log_data}")
                else:
                    logger.info(f"Received: {response_data}")
                
                return response_data
        except Exception as e:
            logger.error(f"Error during communication: {e}")
            return {"error": str(e)}
    
    async def get_window_list(self):
        """
        Get list of available windows
        
        Returns:
            dict: Window list response
        """
        return await self.send_message(
            content="{}",
            message_type="window_list_request"
        )
    
    async def get_window_screenshot(self, window_id):
        """
        Get screenshot of a specific window
        
        Args:
            window_id: ID of the window to capture
            
        Returns:
            dict: Window screenshot response
        """
        content = {
            "window_id": window_id
        }
        
        return await self.send_message(
            content=json.dumps(content),
            message_type="window_screenshot_request"
        )

async def main():
    """Main function - Demonstrates the use of MCP protocol client with window screenshot functionality"""
    client = MCPClient()
    
    # Get window list
    print("\n=== Getting Window List ===")
    window_list_response = await client.get_window_list()
    
    if window_list_response.get("type") == "window_list_response":
        windows = window_list_response.get("content", {}).get("windows", [])
        
        if windows:
            print(f"Found {len(windows)} windows:")
            for i, window in enumerate(windows, 1):
                print(f"{i}. {window['title']} ({window['process']})")
            
            # Get screenshot of first window
            if len(windows) > 0:
                print("\n=== Getting Window Screenshot ===")
                window_id = windows[0]['id']
                print(f"Capturing screenshot of: {windows[0]['title']}")
                
                screenshot_response = await client.get_window_screenshot(window_id)
                
                if screenshot_response.get("type") == "window_screenshot_response":
                    print("Screenshot captured successfully")
                    
                    # Save the screenshot
                    import base64
                    import time
                    
                    image_data = screenshot_response.get("content", {}).get("image_data")
                    if image_data:
                        filename = f"window_shot_{int(time.time())}.png"
                        with open(filename, "wb") as f:
                            f.write(base64.b64decode(image_data))
                        print(f"Screenshot saved to: {filename}")
                else:
                    print("Failed to capture screenshot")
                    print(json.dumps(screenshot_response, indent=2))
        else:
            print("No windows found")
    else:
        print("Failed to get window list")
        print(json.dumps(window_list_response, indent=2))
    
    # Send a simple Hello World message as well
    print("\n=== Sending Text Message ===")
    text_response = await client.send_message("Hello World! This is MCP with window screenshot support.")
    
    print("\n--- Text Response from Server ---")
    print(json.dumps(text_response, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main()) 