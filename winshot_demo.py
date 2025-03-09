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
from cursor_mcp_adapter import CursorMCPAdapter


async def run_window_list_demo():
    """Demonstrate window list functionality"""
    print("\n=== Window List Demo ===")
    
    adapter = CursorMCPAdapter()
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
        window_id: Specific window ID to capture, if None will use the first available window
        windows: List of available windows (to avoid fetching the list again)
    """
    print("\n=== Window Screenshot Demo ===")
    
    adapter = CursorMCPAdapter()
    
    # If no windows provided, get the list
    if windows is None or len(windows) == 0:
        windows = await adapter.get_window_list()
    
    if not windows:
        print("No windows available for screenshot")
        return
    
    # If no specific window_id was provided, use the first window
    if window_id is None:
        selected_window = windows[0]
        window_id = selected_window['id']
    else:
        # Find the window with the provided ID
        selected_window = next((w for w in windows if w['id'] == window_id), None)
        if not selected_window:
            print(f"Window with ID '{window_id}' not found")
            return
    
    print(f"Capturing screenshot of: {selected_window['title']} ({selected_window['process']})")
    
    # Capture the screenshot
    screenshot_path, status = await adapter.capture_and_save_window(window_id)
    
    if screenshot_path:
        print(f"Screenshot saved to: {screenshot_path}")
        print(f"Absolute path: {os.path.abspath(screenshot_path)}")
        
        # Try to display the screenshot in a basic way if available
        try:
            # Check if we're in an environment that can display images
            import platform
            system = platform.system()
            
            if system == "Darwin":  # macOS
                print("Attempting to open screenshot with default viewer...")
                subprocess.run(["open", screenshot_path])
            elif system == "Windows":
                print("Attempting to open screenshot with default viewer...")
                os.startfile(screenshot_path)
            elif system == "Linux":
                print("Attempting to open screenshot with default viewer...")
                subprocess.run(["xdg-open", screenshot_path])
            
        except Exception as e:
            print(f"Could not display screenshot: {e}")
    else:
        print(f"Failed to capture screenshot: {status}")


async def interactive_demo():
    """Run an interactive demo with window selection"""
    print("\n=== Interactive Window Screenshot Demo ===")
    
    adapter = CursorMCPAdapter()
    windows = await adapter.get_window_list()
    
    if not windows:
        print("No windows found")
        return
    
    # Display the list of windows
    print("\nAvailable windows:")
    for i, window in enumerate(windows, 1):
        print(f"{i}. {window['title']} ({window['process']})")
    
    # Get user selection
    try:
        selection = int(input("\nEnter the number of the window to capture (or 0 to exit): "))
        if selection == 0:
            print("Exiting demo")
            return
        
        if 1 <= selection <= len(windows):
            selected_window = windows[selection-1]
            window_id = selected_window['id']
            
            print(f"\nYou selected: {selected_window['title']} ({selected_window['process']})")
            await run_window_screenshot_demo(window_id, windows)
        else:
            print(f"Invalid selection. Please enter a number between 1 and {len(windows)}")
    except ValueError:
        print("Invalid input. Please enter a number")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run window screenshot demo")
    parser.add_argument("--list", action="store_true", help="List available windows")
    parser.add_argument("--interactive", action="store_true", help="Run interactive demo")
    parser.add_argument("--capture-all", action="store_true", help="Capture all available windows")
    parser.add_argument("--window-index", type=int, help="Capture the window at the specified index (1-based)")
    args = parser.parse_args()
    
    # Print welcome message
    print("=" * 60)
    print("Window Screenshot Demo")
    print("=" * 60)
    
    try:
        if args.interactive:
            await interactive_demo()
        elif args.list:
            await run_window_list_demo()
        elif args.capture_all:
            windows = await run_window_list_demo()
            for window in windows:
                await run_window_screenshot_demo(window['id'], windows)
                time.sleep(1)  # Short delay between captures
        elif args.window_index is not None:
            windows = await run_window_list_demo()
            if 1 <= args.window_index <= len(windows):
                await run_window_screenshot_demo(windows[args.window_index-1]['id'], windows)
            else:
                print(f"Invalid window index. Please specify a value between 1 and {len(windows)}")
        else:
            # Default behavior: run both demos
            windows = await run_window_list_demo()
            if windows:
                await run_window_screenshot_demo(None, windows)
    
    except Exception as e:
        print(f"Error during demo: {e}")
    
    print("\n" + "=" * 60)
    print("Demo completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 