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
        self.websocket = None
        self.connected = False
        
    async def connect(self):
        """Connect to the MCP server"""
        try:
            self.websocket = await websockets.connect(self.url)
            self.connected = True
            logger.info(f"Connected to MCP server at {self.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {str(e)}")
            self.connected = False
            return False
            
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.websocket and self.connected:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from MCP server")
            
    async def send_message(self, message_type: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to the MCP server
        
        Args:
            message_type: Type of message to send
            content: Message content
            
        Returns:
            Server response
        """
        if not self.connected:
            await self.connect()
            
        if not self.connected:
            return {"error": "Not connected to MCP server"}
            
        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "type": message_type,
            "content": content
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            response = await self.websocket.recv()
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error sending message to MCP server: {str(e)}")
            return {"error": f"Failed to send message: {str(e)}"}
            
    async def get_window_list(self):
        """
        Get list of available windows
        
        Returns:
            List of windows
        """
        response = await self.send_message("window_list_request", {})
        if "error" in response:
            return []
        return response.get("content", {}).get("windows", [])
        
    async def get_window_screenshot(self, window_id: str):
        """
        Get screenshot of a specific window
        
        Args:
            window_id: ID of the window to capture
            
        Returns:
            Screenshot data and format
        """
        response = await self.send_message("window_screenshot_request", {"window_id": window_id})
        if "error" in response:
            return None, None
        content = response.get("content", {})
        return content.get("image_data"), content.get("format")

async def main():
    """Test the MCP client"""
    client = MCPClient()
    await client.connect()
    
    # Get window list
    window_list = await client.get_window_list()
    print(f"Found {len(window_list)} windows:")
    for i, window in enumerate(window_list, 1):
        print(f"{i}. {window['title']} ({window['process']})")
        
    # Disconnect
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 