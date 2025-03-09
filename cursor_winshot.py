#!/usr/bin/env python3
"""
Cursor Window Screenshot Integration - Integrates window screenshot functionality with Cursor

This module provides functions to capture window screenshots and provide them to Cursor's
agent mode, allowing the LLM to see and analyze the UI of specific applications.
"""

import os
import sys
import time
import json
import asyncio
import base64
from typing import Optional, Dict, Any, List, Tuple, Union

# Import MCP adapter
from cursor_mcp_adapter import CursorMCPAdapter

# Global adapter instance
_adapter = None

def get_adapter() -> CursorMCPAdapter:
    """
    Get or create the MCP adapter instance
    
    Returns:
        CursorMCPAdapter: The MCP adapter instance
    """
    global _adapter
    if _adapter is None:
        _adapter = CursorMCPAdapter()
    return _adapter

async def get_windows() -> List[Dict[str, str]]:
    """
    Get list of available windows
    
    Returns:
        List[Dict[str, str]]: List of window information dictionaries
    """
    adapter = get_adapter()
    return await adapter.get_window_list()

async def capture_window(window_id: str, save_path: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    Capture a screenshot of the specified window
    
    Args:
        window_id: ID of the window to capture
        save_path: Path to save the screenshot to (optional)
        
    Returns:
        Tuple[Optional[str], str]: Path to saved screenshot (or None if failed) and status message
    """
    adapter = get_adapter()
    return await adapter.capture_and_save_window(window_id, save_path)

async def find_window_by_title(title_fragment: str) -> Optional[Dict[str, str]]:
    """
    Find a window by a fragment of its title
    
    Args:
        title_fragment: Fragment of the window title to search for
        
    Returns:
        Optional[Dict[str, str]]: Window information dictionary, or None if not found
    """
    adapter = get_adapter()
    windows = await adapter.get_window_list()
    
    # Case-insensitive search
    title_fragment = title_fragment.lower()
    
    # Find the first window that contains the title fragment
    for window in windows:
        if title_fragment in window['title'].lower():
            return window
    
    return None

async def capture_window_by_title(title_fragment: str, save_path: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    Capture a screenshot of a window identified by a fragment of its title
    
    Args:
        title_fragment: Fragment of the window title to search for
        save_path: Path to save the screenshot to (optional)
        
    Returns:
        Tuple[Optional[str], str]: Path to saved screenshot (or None if failed) and status message
    """
    window = await find_window_by_title(title_fragment)
    
    if window:
        adapter = get_adapter()
        return await adapter.capture_and_save_window(window['id'], save_path)
    else:
        return None, f"No window found with title containing '{title_fragment}'"

# Functions for Cursor integration

async def list_windows_for_cursor() -> str:
    """
    Get a formatted list of windows for Cursor
    
    Returns:
        str: JSON-formatted list of windows
    """
    windows = await get_windows()
    
    if not windows:
        return json.dumps({"status": "error", "message": "No windows found"})
    
    # Format the window list for Cursor
    window_list = []
    for i, window in enumerate(windows, 1):
        window_list.append({
            "index": i,
            "id": window['id'],
            "title": window['title'],
            "process": window['process']
        })
    
    return json.dumps({
        "status": "success",
        "windows": window_list
    })

async def capture_for_cursor(window_identifier: Union[str, int]) -> str:
    """
    Capture a window screenshot for Cursor
    
    Args:
        window_identifier: Window ID, title fragment, or index (1-based)
        
    Returns:
        str: JSON-formatted result with screenshot path
    """
    # Determine what type of identifier was provided
    if isinstance(window_identifier, int) or (isinstance(window_identifier, str) and window_identifier.isdigit()):
        # It's an index
        index = int(window_identifier)
        windows = await get_windows()
        
        if not windows:
            return json.dumps({"status": "error", "message": "No windows found"})
        
        if 1 <= index <= len(windows):
            window_id = windows[index-1]['id']
            window_title = windows[index-1]['title']
        else:
            return json.dumps({
                "status": "error", 
                "message": f"Invalid window index: {index}. Valid range is 1-{len(windows)}"
            })
    
    elif ":" in window_identifier:
        # It looks like a window ID
        window_id = window_identifier
        window = None
        
        # Try to get the window title
        windows = await get_windows()
        for w in windows:
            if w['id'] == window_id:
                window = w
                break
        
        window_title = window['title'] if window else "Unknown window"
    
    else:
        # It's probably a title fragment
        window = await find_window_by_title(window_identifier)
        
        if not window:
            return json.dumps({
                "status": "error", 
                "message": f"No window found with title containing '{window_identifier}'"
            })
        
        window_id = window['id']
        window_title = window['title']
    
    # Capture the screenshot
    timestamp = int(time.time())
    filename = f"window_shot_{timestamp}.png"
    
    path, status = await capture_window(window_id, filename)
    
    if path:
        return json.dumps({
            "status": "success",
            "window_title": window_title,
            "screenshot_path": path,
            "absolute_path": os.path.abspath(path),
            "timestamp": timestamp
        })
    else:
        return json.dumps({
            "status": "error",
            "message": f"Failed to capture screenshot: {status}"
        })

# Command-line interface for Cursor integration

async def main():
    """Main function - CLI for Cursor integration"""
    if len(sys.argv) < 2:
        print("Usage: python cursor_winshot.py <command> [args...]")
        print("Commands:")
        print("  list - List available windows")
        print("  capture <window_id|title_fragment|index> - Capture a window screenshot")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        result = await list_windows_for_cursor()
        print(result)
    
    elif command == "capture" and len(sys.argv) >= 3:
        window_identifier = sys.argv[2]
        result = await capture_for_cursor(window_identifier)
        print(result)
    
    else:
        print("Unknown command or missing arguments")

if __name__ == "__main__":
    asyncio.run(main()) 