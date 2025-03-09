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
import requests
from io import BytesIO
from typing import Dict, Any, Optional, Union, Tuple

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
        
    async def get_window_screenshot(self, window_id: str) -> Tuple[Optional[str], Optional[str], Optional[bytes]]:
        """
        Get screenshot of a specific window
        
        Args:
            window_id: ID of the window to capture
            
        Returns:
            Tuple containing:
            - URI to the screenshot (if available)
            - Format of the image (e.g., "png")
            - Downloaded image data (if uri is available)
        """
        response = await self.send_message("window_screenshot_request", {"window_id": window_id})
        if "error" in response:
            logger.error(f"Error getting screenshot: {response.get('error')}")
            return None, None, None
            
        content = response.get("content", {})
        uri = content.get("uri")
        image_format = content.get("format")
        
        # 如果有 URI，尝试下载图像
        image_data = None
        if uri:
            try:
                logger.info(f"Downloading screenshot from: {uri}")
                response = requests.get(uri, timeout=10)
                if response.status_code == 200:
                    image_data = response.content
                    logger.info(f"Successfully downloaded image: {len(image_data)} bytes")
                else:
                    logger.error(f"Failed to download image: HTTP {response.status_code}")
            except Exception as e:
                logger.error(f"Error downloading image: {str(e)}")
        
        return uri, image_format, image_data

    async def download_image_from_uri(self, uri: str) -> Optional[bytes]:
        """
        Download image from a URI
        
        Args:
            uri: URI to download from
            
        Returns:
            Image data as bytes, or None if download failed
        """
        try:
            response = requests.get(uri, timeout=10)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to download image: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            return None

async def main():
    """Test the MCP client"""
    client = MCPClient()
    await client.connect()
    
    # Get window list
    window_list = await client.get_window_list()
    print(f"Found {len(window_list)} windows:")
    for i, window in enumerate(window_list, 1):
        print(f"{i}. {window['title']} ({window['process']})")
    
    # 如果有窗口，尝试截图并下载第一个窗口
    if window_list:
        window_id = window_list[0]['id']
        print(f"\nCapturing screenshot of: {window_list[0]['title']}")
        uri, image_format, image_data = await client.get_window_screenshot(window_id)
        
        if uri:
            print(f"Screenshot URI: {uri}")
            print(f"Image format: {image_format}")
            
            if image_data:
                print(f"Downloaded image: {len(image_data)} bytes")
                
                # 可以保存到文件
                with open(f"test_screenshot.{image_format.lower()}", "wb") as f:
                    f.write(image_data)
                print("Saved image to test_screenshot.png")
        else:
            print("No screenshot URI received")
        
    # Disconnect
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 