#!/usr/bin/env python3
"""
Window Screenshot Demo - Demonstrates the window screenshot functionality

This script demonstrates the window screenshot functionality by capturing
screenshots of application windows and saving them to files.
"""

import os
import sys
import time
import asyncio
import argparse
from typing import Optional, List, Dict
import subprocess

# Import the window screenshot client
from client.cursor_adapter import CursorAdapter


async def run_window_list_demo():
    """Demonstrate window list functionality"""
    print("\n=== Window List Demo ===")
    
    adapter = CursorAdapter()
    windows = await adapter.get_window_list()
    
    if windows:
        print(f"Found {len(windows)} windows:")
        for i, window in enumerate(windows, 1):
            print(f"{i}. {window['title']} ({window['process']})")
        return windows
    else:
        print("No windows found")
        return []


async def run_window_screenshot_demo(window_id: Optional[str] = None, windows: Optional[List[Dict]] = None):
    """
    Demonstrate window screenshot functionality
    
    Args:
        window_id: Optional window ID to capture
        windows: Optional list of windows
    """
    print("\n=== Window Screenshot Demo ===")
    
    adapter = CursorAdapter()
    
    # If no window ID provided, let user select from list
    if not window_id:
        if not windows:
            windows = await adapter.get_window_list()
            
        if not windows:
            print("No windows available to capture")
            return
            
        print("Select a window to capture:")
        for i, window in enumerate(windows, 1):
            print(f"{i}. {window['title']} ({window['process']})")
            
        try:
            selection = int(input("\nEnter window number: "))
            if 1 <= selection <= len(windows):
                window_id = windows[selection-1]["id"]
                print(f"Selected: {windows[selection-1]['title']}")
            else:
                print("Invalid selection")
                return
        except ValueError:
            print("Invalid input")
            return
    
    # Generate filename
    timestamp = int(time.time())
    filename = f"window_shot_{timestamp}.png"
    
    print(f"Capturing window screenshot to {filename}...")
    print("Note: You may need to click on the window to be captured when prompted")
    
    # Capture window
    file_path, status = await adapter.capture_and_save_window(window_id, filename)
    
    if file_path:
        print(f"Screenshot saved to: {file_path}")
        
        # Try to open the image
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", file_path])
            elif sys.platform == "win32":  # Windows
                os.startfile(file_path)
            elif sys.platform == "linux":  # Linux
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            print(f"Could not open image: {e}")
    else:
        print(f"Failed to capture screenshot: {status}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Window Screenshot Demo")
    parser.add_argument("--list-only", action="store_true", help="Only list windows, don't capture")
    parser.add_argument("--window-id", help="Capture specific window ID")
    
    args = parser.parse_args()
    
    if args.list_only:
        await run_window_list_demo()
    elif args.window_id:
        await run_window_screenshot_demo(window_id=args.window_id)
    else:
        windows = await run_window_list_demo()
        if windows:
            await run_window_screenshot_demo(windows=windows)


if __name__ == "__main__":
    asyncio.run(main()) 