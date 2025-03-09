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
from client.cursor_adapter import CursorAdapter

# Global adapter instance
_adapter = None

def get_adapter() -> CursorAdapter:
    """Get or create the global adapter instance"""
    global _adapter
    if _adapter is None:
        _adapter = CursorAdapter()
    return _adapter

async def list_windows() -> List[Dict[str, str]]:
    """
    List all available windows
    
    Returns:
        List of window information dictionaries
    """
    adapter = get_adapter()
    return await adapter.get_window_list()

async def capture_window(window_id: str, save_path: Optional[str] = None, save_locally: bool = True) -> Tuple[Optional[str], str]:
    """
    Capture screenshot of a specific window
    
    Args:
        window_id: ID of the window to capture
        save_path: Optional path to save the screenshot
        save_locally: Whether to save the screenshot locally (default: True)
        
    Returns:
        Tuple of (file_path, status_message)
    """
    adapter = get_adapter()
    return await adapter.capture_and_save_window(window_id, save_path, save_locally)

async def capture_window_by_title(title_fragment: str, save_path: Optional[str] = None, save_locally: bool = True) -> Tuple[Optional[str], str]:
    """
    Capture screenshot of a window by title fragment
    
    Args:
        title_fragment: Fragment of the window title to match
        save_path: Optional path to save the screenshot
        save_locally: Whether to save the screenshot locally (default: True)
        
    Returns:
        Tuple of (file_path, status_message)
    """
    adapter = get_adapter()
    
    # Get window list
    windows = await adapter.get_window_list()
    
    # Find window by title fragment
    window_id = None
    window_title = None
    
    for window in windows:
        if title_fragment.lower() in window["title"].lower():
            window_id = window["id"]
            window_title = window["title"]
            break
    
    # If no match, try process name
    if window_id is None:
        for window in windows:
            if title_fragment.lower() in window["process"].lower():
                window_id = window["id"]
                window_title = window["title"]
                break
    
    # If still no match, return error
    if window_id is None:
        return None, f"No window found matching '{title_fragment}'"
    
    # Capture window
    file_path, status = await adapter.capture_and_save_window(window_id, save_path, save_locally)
    
    if file_path:
        return file_path, f"Captured window: {window_title}"
    
    return None, status

def list_windows_sync() -> List[Dict[str, str]]:
    """
    Synchronous version of list_windows
    
    Returns:
        List of window information dictionaries
    """
    return asyncio.run(list_windows())

def capture_window_sync(window_id: str, save_path: Optional[str] = None, save_locally: bool = True) -> Tuple[Optional[str], str]:
    """
    Synchronous version of capture_window
    
    Args:
        window_id: ID of the window to capture
        save_path: Optional path to save the screenshot
        save_locally: Whether to save the screenshot locally (default: True)
        
    Returns:
        Tuple of (file_path, status_message)
    """
    return asyncio.run(capture_window(window_id, save_path, save_locally))

def capture_window_by_title_sync(title_fragment: str, save_path: Optional[str] = None, save_locally: bool = True) -> Tuple[Optional[str], str]:
    """
    Synchronous version of capture_window_by_title
    
    Args:
        title_fragment: Fragment of the window title to match
        save_path: Optional path to save the screenshot
        save_locally: Whether to save the screenshot locally (default: True)
        
    Returns:
        Tuple of (file_path, status_message)
    """
    return asyncio.run(capture_window_by_title(title_fragment, save_path, save_locally))

# Command-line interface
async def main():
    """Command-line interface for window screenshot functionality"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Capture window screenshots")
    parser.add_argument("--list", action="store_true", help="List available windows")
    parser.add_argument("--capture", help="Capture window by ID")
    parser.add_argument("--title", help="Capture window by title fragment")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    if args.list:
        windows = await list_windows()
        print(f"Found {len(windows)} windows:")
        for i, window in enumerate(windows, 1):
            print(f"{i}. {window['title']} ({window['process']})")
    
    elif args.capture:
        window_id = args.capture
        filename = args.output
        path, status = await capture_window(window_id, filename)
        
        if path:
            print(f"Screenshot saved to: {path}")
        else:
            print(f"Failed to capture screenshot: {status}")
    
    elif args.title:
        title_fragment = args.title
        filename = args.output
        path, status = await capture_window_by_title(title_fragment, filename)
        
        if path:
            print(f"Screenshot saved to: {path}")
        else:
            print(f"Failed to capture screenshot: {status}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main()) 