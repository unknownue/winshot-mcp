# Winshot MCP

A Model-Client Protocol (MCP) window screenshot integration tool for Cursor, allowing Cursor's agent mode to capture and analyze application windows.

## Overview

This project implements the MCP protocol with window screenshot functionality, enabling Large Language Models (LLMs) to visually observe and interact with application UIs. By capturing screenshots of specific windows, LLMs can better understand the user's environment and provide more context-aware assistance.

## Features

- List all active windows on Windows, macOS, and Linux
- Capture screenshots of specific application windows
- Send window screenshots to LLMs via the MCP protocol
- Integrate with Cursor's agent mode

## Installation

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Platform-specific requirements:
   - Windows: `pip install pygetwindow`
   - Linux: `sudo apt-get install xdotool imagemagick`
   - macOS: Terminal/IDE needs screen recording permissions
     - The system will ask for permission on first run
     - You can also manually grant permission in System Settings > Privacy & Security > Screen Recording
     - If using an IDE (like VS Code), ensure the IDE has permission

3. Run the window screenshot demo:
   ```
   python winshot_demo.py
   ```

## Using with Cursor

To use window screenshot functionality in Cursor's agent mode:

1. Start the MCP server:
   ```
   python mcp_sse_server.py
   ```

2. In Cursor, you can use the following commands in agent mode:
   - `list_windows()` - List all available windows
   - `capture_window("Window Title")` - Capture a screenshot of a window with the given title
   - `capture_window(window_index)` - Capture a screenshot of a window by index

## Project Structure

- `winshot.py`: Core window screenshot functionality
- `mcp_sse_server.py`: MCP server with window screenshot support
- `mcp_client.py`: MCP client implementation
- `cursor_mcp_adapter.py`: Adapter connecting Cursor with MCP
- `cursor_winshot.py`: Cursor-specific window screenshot integration
- `winshot_demo.py`: Demo script showcasing window screenshot functionality

## Demo

Running `python winshot_demo.py` will start an interactive demo that:
1. Lists all available windows on your system
2. Allows you to select a window to screenshot
3. Initiates the screenshot process (**Note: Current version may require you to manually click on the window to be captured**)

The interactive prompts during the screenshot process are part of macOS security mechanisms, ensuring user control over screen capture. Screenshots are saved in the current directory with filenames starting with `window_shot_`.

## Troubleshooting Screenshot Issues

If you encounter issues with screenshots on macOS:

1. Confirm screen recording permission is granted to your terminal or IDE
2. **During the screenshot process, click on the window you want to capture when prompted**
3. Try different screenshot methods: the code automatically attempts three different methods
4. For windows that cannot be captured automatically, you may need to modify the screenshot parameters in `winshot.py`

### Known Limitations

- **User intervention required**: The current version on macOS may require manual window clicking to complete the screenshot. This is a result of system security limitations and is currently considered acceptable.
- Some windows may not be locatable by ID, in which case the foreground window will be captured.
- Some applications' windows may not be captured correctly, especially those using non-standard window management.

## Protocol Details

This implementation extends the MCP protocol by adding specific message types for window screenshots:

- `window_list_request`/`window_list_response`: Used to list available windows
- `window_screenshot_request`/`window_screenshot_response`: Used to capture screenshots 