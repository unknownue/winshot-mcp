# Winshot MCP

A Model-Client Protocol (MCP) window screenshot integration tool for Cursor, allowing Cursor's agent mode to capture and analyze application windows.

## Overview

This project implements the MCP protocol with window screenshot functionality, enabling Large Language Models (LLMs) to visually observe and interact with application UIs. By capturing screenshots of specific windows, LLMs can better understand the user's environment and provide more context-aware assistance.

## Features

- List all active windows on Windows, macOS, and Linux
- Capture screenshots of specific application windows
- Send window screenshots to LLMs via the MCP protocol
- Integrate with Cursor's agent mode
- Serve screenshots via HTTP for more efficient data transfer

## Project Structure

The project is organized into three main components:

- **Core**: Core window screenshot functionality
  - `core/winshot.py`: Core window screenshot implementation

- **Server**: MCP server implementation
  - `server/mcp_server.py`: MCP server with window screenshot support
  - `server/__main__.py`: Entry point for running the server

- **Client**: Client implementations and utilities
  - `client/mcp_client.py`: MCP client implementation
  - `client/cursor_adapter.py`: Adapter connecting Cursor with MCP
  - `client/cursor_winshot.py`: Cursor-specific window screenshot integration
  - `client/demo.py`: Demo script showcasing window screenshot functionality
  - `client/__main__.py`: Entry point for running the client demo

- **Main Entry Point**: 
  - `__main__.py`: Unified entry point for both server and client components

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

## Usage

### Image Size Configuration

The server supports configuring the maximum image dimensions and file size to optimize performance and memory usage:

- `--max-image-dimension <pixels>` - Maximum width or height of captured screenshots (default: 1200 pixels)
- `--max-file-size-mb <size>` - Maximum file size for screenshot data (default: 5 MB)

Reducing these values can improve performance and decrease memory usage, especially when working with large screens or high-resolution displays.

### Screenshot File Server

Instead of encoding screenshots as base64 (which increases data size by ~30%), the server now uses a file server approach:

- Screenshots are saved to a dedicated temporary directory
- Each screenshot is assigned a unique hash identifier
- A lightweight HTTP file server serves the images via `/img/{hash}` paths
- LLMs receive URIs with hash references instead of direct file paths
- Files are automatically cleaned up after a configurable expiry time

This approach offers several advantages:
- Significantly reduces data transfer size compared to base64 encoding
- Provides secure access without exposing the actual file system structure
- Each image has a unique identifier independent of its filename
- Links remain stable even if file locations change

Configuration options:
- `--fileserver-port <port>` - Port for the screenshot file server (default: 8766)
- `--tmp-dir <path>` - Custom temporary directory for screenshots (default: `./tmp` directory in project root)
- `--file-expiry-minutes <minutes>` - Time after which temporary files are deleted (default: 60 minutes)

> 🔹 **Important for Cursor Users**: Use the `--tmp-dir` parameter to specify a location accessible to Cursor. 
> The server will provide both the HTTP URI and the local file path in its response, allowing Cursor 
> to view screenshots using the `@file` syntax. **Setting a proper `--tmp-dir` is critical** for enabling 
> Cursor's LLM to analyze images.
>
> Example: `python . server --tmp-dir /Users/username/cursor-accessible-folder`

This approach significantly reduces data transfer size and memory usage, especially for large screenshots.

> ⚠️ **Important Cursor Limitation**: Currently Cursor's agent mode cannot directly process images via URIs/links. Cursor only supports viewing images when referenced with the `@file` syntax (e.g., `@/path/to/image.png`). This means that while our server provides optimized HTTP URIs, Cursor's LLM cannot directly "see" these images. You may need to manually download images or develop additional integrations to convert URIs to local file references for Cursor to process them properly.

### Using the Unified Entry Point

Run the server:
```
python . server
```

Run the server with custom image size settings:
```
python . server --max-image-dimension 800 --max-file-size-mb 2
```

Run the server with custom file server settings:
```
python . server --fileserver-port 8080 --tmp-dir ./screenshots --file-expiry-minutes 120
```

Run the client:
```
python . client
```

Specify a custom port for the server:
```
python . server --port 8766
```

### Running the Server Directly

Start the MCP server:
```
python -m server
```

Start the server with custom image size settings:
```
python -m server --max-image-dimension 800 --max-file-size-mb 2
```

Or:
```
python server/mcp_server.py
```

### Running the Demo Client Directly

Run the demo client:
```
python -m client
```

Or:
```
python client/demo.py
```

### Using with Cursor

In Cursor's agent mode, you can use the following commands:
- `list_windows()` - List all available windows
- `capture_window("Window Title")` - Capture a screenshot of a window with the given title
- `capture_window(window_index)` - Capture a screenshot of a window by index

#### Viewing Screenshots in Cursor

Since Cursor only supports viewing images through the `@file` syntax, the server is designed to help with this limitation:

1. **Start the server with an accessible directory**:
   ```
   python . server --tmp-dir /path/accessible/to/cursor
   ```

2. **Capture a window**:
   ```python
   result = capture_window("Chrome")
   ```

3. **Use the provided Cursor syntax to view the image**:
   ```python
   # The result contains a cursor_syntax field ready to use
   print(f"Screenshot: {result['cursor_syntax']}")
   
   # Example output:
   # Screenshot: @/path/accessible/to/cursor/window_shot_Chrome_1234567890_abcdef12.png
   ```

4. **Full response example**:
   ```json
   {
     "uri": "http://localhost:8766/img/a1b2c3d4e5f67890",
     "format": "png",
     "window_id": "Chrome:MainWindow",
     "window_title": "Chrome",
     "hash": "a1b2c3d4e5f67890",
     "local_file_path": "/path/accessible/to/cursor/window_shot_Chrome_1234567890_abcdef12.png",
     "cursor_syntax": "@/path/accessible/to/cursor/window_shot_Chrome_1234567890_abcdef12.png"
   }
   ```

This approach ensures that both the HTTP URI (for general use) and local file path (for Cursor use) are available.

#### Example Cursor Workflow

Here's a complete example of how you might interact with screenshots in Cursor:

```
# 1. First, list all available windows
windows = list_windows()
print("Available windows:", [w["title"] for w in windows["windows"]])

# 2. Capture a specific window
result = capture_window("Firefox")

# 3. Check if capture was successful
if "error" in result:
    print(f"Error: {result['error']}")
else:
    # 4. View the screenshot in Cursor
    print(f"Screenshot captured successfully!")
    print(f"Viewing screenshot: {result['cursor_syntax']}")
    
    # 5. Ask LLM to analyze the screenshot
    print("What can you see in this screenshot?")
    
    # LLM will be able to view and analyze the image using the @file reference
```

When you run the above code in Cursor:
1. The server captures the Firefox window screenshot
2. The screenshot is saved to your specified `--tmp-dir`
3. Cursor displays the image when it encounters the `result['cursor_syntax']` value
4. The LLM can analyze and comment on what it sees in the screenshot

This seamless integration makes it easy to use screenshots in your conversations with Cursor's LLM.

## Demo

Running the client demo will:
1. List all available windows on your system
2. Allow you to select a window to screenshot
3. Initiate the screenshot process (**Note: Current version may require you to manually click on the window to be captured**)

The interactive prompts during the screenshot process are part of macOS security mechanisms, ensuring user control over screen capture. Screenshots are saved in the current directory with filenames starting with `window_shot_`.

## Troubleshooting Screenshot Issues

If you encounter issues with screenshots on macOS:

1. Confirm screen recording permission is granted to your terminal or IDE
2. **During the screenshot process, click on the window you want to capture when prompted**
3. Try different screenshot methods: the code automatically attempts three different methods
4. For windows that cannot be captured automatically, you may need to modify the screenshot parameters in `core/winshot.py`
5. **Memory or performance issues**: Try reducing the image size with `--max-image-dimension` and `--max-file-size-mb` options

### Known Limitations

- **User intervention required**: The current version on macOS may require manual window clicking to complete the screenshot. This is a result of system security limitations and is currently considered acceptable.
- Some windows may not be locatable by ID, in which case the foreground window will be captured.
- Some applications' windows may not be captured correctly, especially those using non-standard window management.
- **Large screens/high-resolution displays**: May require adjusting the maximum image dimensions and file size to prevent memory issues.

## Protocol Details

This implementation extends the MCP protocol by adding specific message types for window screenshots:

- `window_list_request`/`window_list_response`: Used to list available windows
- `window_screenshot_request`/`window_screenshot_response`: Used to capture screenshots and receive URIs to the images 