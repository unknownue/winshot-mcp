#!/usr/bin/env python3
"""
Window Screenshot Module - Core functionality for capturing window screenshots

This module provides functionality to capture screenshots of specific application windows
across different operating systems (Windows, macOS, Linux).
"""

import os
import time
import platform
import subprocess
import base64
import io
import logging
from typing import Optional, List, Dict, Any, Union, Tuple

# Configure logging
logger = logging.getLogger("winshot")

try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class WindowShot:
    """Window screenshot utility for capturing screenshots of specific application windows"""
    
    def __init__(self, max_image_dimension=1200, max_file_size_mb=5, save_locally=False):
        """
        Initialize the window screenshot utility
        
        Args:
            max_image_dimension: Maximum width or height of captured screenshots (in pixels)
            max_file_size_mb: Maximum file size of captured screenshots (in MB)
            save_locally: Whether to save screenshots locally (default: False)
        """
        self.system = platform.system()  # Get operating system type
        self.max_image_dimension = max_image_dimension
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.save_locally = save_locally
        
        # Check for required dependencies
        if not HAS_PIL:
            logger.warning("PIL/Pillow is not installed. Image processing will fail.")
    
    def get_window_list(self) -> List[Dict[str, str]]:
        """
        Get a list of all visible windows in the current system
        
        Returns:
            List[Dict[str, str]]: List of window information, each containing window ID, title, etc.
        """
        windows = []
        
        if self.system == "Darwin":  # macOS
            # For macOS, we'll use different approaches and try them in sequence
            windows = self._get_macos_window_list_v1()
            
            # If first approach failed, try simpler approach
            if not windows:
                logger.debug("First approach failed, trying simpler window detection...")
                windows = self._get_macos_window_list_v2()
                
            # If still no windows, try the simplest approach
            if not windows:
                logger.debug("Second approach failed, trying basic app detection...")
                windows = self._get_macos_window_list_v3()
        
        elif self.system == "Windows":
            # Use pygetwindow library to get Windows window list
            try:
                import pygetwindow as gw
                all_windows = gw.getAllWindows()
                for window in all_windows:
                    if window.title:  # Only add windows with titles
                        windows.append({
                            "id": str(window._hWnd),
                            "title": window.title,
                            "process": "Unknown"  # Need additional processing to get process name
                        })
            except ImportError:
                logger.error("pygetwindow library is not installed. Please install with: pip install pygetwindow")
        
        elif self.system == "Linux":
            # Use xdotool to get Linux window list
            try:
                result = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", ".*"], 
                                       capture_output=True, text=True)
                window_ids = result.stdout.strip().split("\n")
                for win_id in window_ids:
                    if win_id:
                        # Get window title
                        title_result = subprocess.run(["xdotool", "getwindowname", win_id], 
                                                    capture_output=True, text=True)
                        title = title_result.stdout.strip()
                        if title:
                            windows.append({
                                "id": win_id,
                                "title": title,
                                "process": "Unknown"  # Need additional processing to get process name
                            })
            except FileNotFoundError:
                logger.error("xdotool is not installed. Please install with: sudo apt-get install xdotool")
        
        return windows
        
    def _get_macos_window_list_v1(self) -> List[Dict[str, str]]:
        """
        First approach to get macOS window list using detailed AppleScript
        
        Returns:
            List[Dict[str, str]]: List of window information
        """
        windows = []
        try:
            # Use AppleScript to get window list
            script = """
            tell application "System Events"
                set windowList to {}
                set allProcesses to processes whose visible is true
                repeat with proc in allProcesses
                    set procName to name of proc
                    set procWindows to windows of proc
                    repeat with win in procWindows
                        set winName to name of win
                        set end of windowList to {process:procName, window:winName}
                    end repeat
                end repeat
                return windowList
            end tell
            """
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            
            # Parse AppleScript output
            if result.stdout:
                # Process output format, convert to window list
                lines = result.stdout.strip().split(", ")
                for i in range(0, len(lines), 2):
                    if i+1 < len(lines):
                        proc = lines[i].replace("process:", "").strip()
                        win = lines[i+1].replace("window:", "").strip()
                        windows.append({"id": f"{proc}:{win}", "title": win, "process": proc})
        except Exception as e:
            logger.error(f"Error in first macOS window detection approach: {e}")
        
        return windows
    
    def _get_macos_window_list_v2(self) -> List[Dict[str, str]]:
        """
        Second approach to get macOS window list using simpler AppleScript
        
        Returns:
            List[Dict[str, str]]: List of window information
        """
        windows = []
        try:
            script = """
            tell application "System Events"
                set windowList to {}
                set appList to application processes whose visible is true
                repeat with appProcess in appList
                    set appName to name of appProcess
                    try
                        set windowNames to name of every window of appProcess
                        repeat with winName in windowNames
                            set end of windowList to appName & ":" & winName
                        end repeat
                    end try
                end repeat
                return windowList
            end tell
            """
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            
            if result.stdout:
                window_strings = result.stdout.strip().split(", ")
                for window_str in window_strings:
                    if ":" in window_str:
                        parts = window_str.split(":", 1)
                        proc = parts[0].strip()
                        win = parts[1].strip()
                        windows.append({"id": f"{proc}:{win}", "title": win, "process": proc})
        except Exception as e:
            logger.error(f"Error in second macOS window detection approach: {e}")
        
        return windows
    
    def _get_macos_window_list_v3(self) -> List[Dict[str, str]]:
        """
        Third simplest approach - just get running applications
        
        Returns:
            List[Dict[str, str]]: List of application information as windows
        """
        windows = []
        try:
            script = """
            tell application "System Events"
                set appList to name of every process whose visible is true
                return appList
            end tell
            """
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            
            if result.stdout:
                apps = result.stdout.strip().split(", ")
                for app in apps:
                    app = app.strip()
                    if app:
                        windows.append({
                            "id": f"{app}:MainWindow",
                            "title": f"{app}",
                            "process": app
                        })
        except Exception as e:
            logger.error(f"Error in third macOS window detection approach: {e}")
        
        # If all else fails, add at least one entry for testing
        if not windows:
            logger.warning("All detection methods failed. Adding a fallback entry for testing.")
            windows.append({
                "id": "Finder:MainWindow",
                "title": "Finder",
                "process": "Finder"
            })
        
        return windows
    
    def capture_window(self, window_id: str) -> Optional[Image.Image]:
        """
        Capture a screenshot of the specified window
        
        Args:
            window_id: Window ID, format depends on the operating system
            
        Returns:
            PIL.Image.Image: Window screenshot, or None if failed
        """
        if not HAS_PIL:
            logger.error("PIL/Pillow is not installed. Cannot capture screenshot.")
            return None
            
        try:
            if self.system == "Darwin":  # macOS
                # Parse window_id
                try:
                    proc_name, win_name = window_id.split(":", 1)
                except ValueError:
                    # Fallback if window_id doesn't contain a colon
                    proc_name = window_id
                    win_name = "MainWindow"
                
                # For macOS, we'll try different capture approaches
                screenshot = self._capture_macos_window_v1(proc_name, win_name)
                
                if screenshot is None:
                    logger.debug("First capture approach failed, trying simpler capture...")
                    screenshot = self._capture_macos_window_v2(proc_name)
                
                if screenshot is None:
                    logger.debug("Second capture approach failed, trying full screen capture...")
                    screenshot = self._capture_macos_window_v3()
                
                # Resize image if needed
                if screenshot:
                    width, height = screenshot.size
                    logger.info(f"Original screenshot size: {width}x{height} pixels")
                    if width > self.max_image_dimension or height > self.max_image_dimension:
                        screenshot = self._safe_resize_image(screenshot)
                        width, height = screenshot.size
                        logger.info(f"Resized screenshot to: {width}x{height} pixels")
                
                # Save locally if requested
                if screenshot and self.save_locally:
                    timestamp = int(time.time())
                    filename = f"window_shot_{timestamp}.png"
                    width, height = screenshot.size
                    logger.info(f"Saving local screenshot ({width}x{height} pixels) to {filename}")
                    self.save_screenshot(screenshot, filename)
                
                return screenshot
            
            elif self.system == "Windows":
                # Use pygetwindow library to capture Windows window
                try:
                    import pygetwindow as gw
                    import win32gui
                    import win32con
                    
                    try:
                        # Convert window_id to integer (it's the window handle)
                        hwnd = int(window_id)
                        
                        # Verify the window exists and get its title
                        window_title = win32gui.GetWindowText(hwnd)
                        if not window_title:
                            logger.error(f"No window found with handle: {hwnd}")
                            return None
                        
                        # Bring window to front
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # Restore if minimized
                        win32gui.SetForegroundWindow(hwnd)  # Bring to front
                        time.sleep(0.5)  # Give window some time to activate
                        
                        # Get the window rect
                        rect = win32gui.GetWindowRect(hwnd)
                        x, y, x2, y2 = rect
                        
                        # Add a small delay to ensure window is fully visible
                        time.sleep(0.2)
                        
                        # Capture the specific window area
                        screenshot = ImageGrab.grab(bbox=(x, y, x2, y2))
                        
                        # Resize image if needed
                        if screenshot:
                            width, height = screenshot.size
                            logger.info(f"Original screenshot size: {width}x{height} pixels")
                            if width > self.max_image_dimension or height > self.max_image_dimension:
                                screenshot = self._safe_resize_image(screenshot)
                                width, height = screenshot.size
                                logger.info(f"Resized screenshot to: {width}x{height} pixels")
                        
                        # Save locally if requested
                        if screenshot and self.save_locally:
                            timestamp = int(time.time())
                            filename = f"window_shot_{timestamp}.png"
                            width, height = screenshot.size
                            logger.info(f"Saving local screenshot ({width}x{height} pixels) to {filename}")
                            self.save_screenshot(screenshot, filename)
                        
                        return screenshot
                        
                    except ValueError as ve:
                        logger.error(f"Invalid window handle: {window_id}")
                        return None
                    except Exception as grab_error:
                        logger.warning(f"Failed to grab specific window: {grab_error}")
                        logger.info("Falling back to full screen capture...")
                        screenshot = ImageGrab.grab()
                        return screenshot
                        
                except ImportError as import_error:
                    logger.error(f"Required library not installed: {import_error}")
                    logger.error("Please install required libraries with: pip install pygetwindow pywin32")
                except Exception as e:
                    logger.warning(f"Failed to capture specific window: {e}")
                    logger.info("Falling back to full screen capture...")
                    try:
                        screenshot = ImageGrab.grab()
                        return screenshot
                    except Exception as grab_error:
                        logger.error(f"Full screen capture also failed: {grab_error}")
            
            elif self.system == "Linux":
                # Use xdotool and import to capture Linux window
                try:
                    # Activate window
                    subprocess.run(["xdotool", "windowactivate", window_id])
                    time.sleep(0.5)  # Give window some time to activate
                    
                    # Capture window screenshot
                    temp_file = f"/tmp/window_shot_{int(time.time())}.png"
                    subprocess.run(["import", "-window", window_id, temp_file])
                    
                    # Read screenshot
                    screenshot = Image.open(temp_file)
                    
                    # Resize image if needed
                    if screenshot:
                        width, height = screenshot.size
                        logger.info(f"Original screenshot size: {width}x{height} pixels")
                        if width > self.max_image_dimension or height > self.max_image_dimension:
                            screenshot = self._safe_resize_image(screenshot)
                            width, height = screenshot.size
                            logger.info(f"Resized screenshot to: {width}x{height} pixels")
                    
                    # Save locally if requested
                    if screenshot and self.save_locally:
                        timestamp = int(time.time())
                        filename = f"window_shot_{timestamp}.png"
                        width, height = screenshot.size
                        logger.info(f"Saving local screenshot ({width}x{height} pixels) to {filename}")
                        self.save_screenshot(screenshot, filename)
                    
                    os.remove(temp_file)  # Delete temporary file
                    
                    return screenshot
                except FileNotFoundError:
                    logger.error("Required tools are not installed. Please install with: sudo apt-get install xdotool imagemagick")
        
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
        
        return None
    
    def _capture_macos_window_v1(self, proc_name: str, win_name: str) -> Optional[Image.Image]:
        """
        First approach to capture a macOS window using AppleScript and screencapture
        
        Args:
            proc_name: Process name
            win_name: Window name
            
        Returns:
            Optional[Image.Image]: Window screenshot or None if failed
        """
        try:
            # Create a temporary file to save the screenshot
            temp_file = f"/tmp/window_screenshot_{int(time.time())}.png"
            
            # Activate the application and move to front
            script = f"""
            tell application "{proc_name}"
                activate
                delay 0.5
            end tell
            tell application "System Events"
                set frontmost of process "{proc_name}" to true
            end tell
            """
            subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            
            # Wait for app to activate
            time.sleep(0.5)
            
            # Try to capture the window using screencapture with -l flag (window by ID/name)
            # First, find the window ID
            window_id_script = f"""
            tell application "System Events"
                tell process "{proc_name}"
                    set winID to id of window 1
                    return winID
                end tell
            end tell
            """
            
            # Get window ID
            try:
                window_id_result = subprocess.run(["osascript", "-e", window_id_script], 
                                            capture_output=True, text=True)
                window_id = window_id_result.stdout.strip()
                
                # Capture window by ID if we got one
                if window_id:
                    subprocess.run(["screencapture", "-l", window_id, temp_file], 
                                 capture_output=True, text=True)
            except Exception as window_ex:
                # If can't get window ID, try by window title
                logger.debug(f"Error getting window ID: {window_ex}")
                # Try a more generic approach with standard screencapture
                subprocess.run(["screencapture", "-w", temp_file], 
                             capture_output=True, text=True)
            
            # Check if screenshot was successfully saved
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                # Load the screenshot
                screenshot = Image.open(temp_file)
                
                # Clean up the temporary file
                os.remove(temp_file)
                
                return screenshot
            else:
                logger.debug(f"Screenshot file not created or empty: {temp_file}")
                return None
                
        except Exception as e:
            logger.error(f"Error in first macOS capture approach: {e}")
            return None
    
    def _capture_macos_window_v2(self, app_name: str) -> Optional[Image.Image]:
        """
        Second approach to capture a macOS window using screencapture utility
        
        Args:
            app_name: Application name
            
        Returns:
            Optional[Image.Image]: Window screenshot or None if failed
        """
        try:
            # Create a temporary file to save the screenshot
            temp_file = f"/tmp/window_screenshot_{int(time.time())}.png"
            
            # Activate the application
            script = f"""
            tell application "{app_name}"
                activate
                delay 0.5
            end tell
            """
            subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            
            # Wait for app to activate
            time.sleep(0.5)
            
            # Capture the frontmost window
            subprocess.run(["screencapture", "-w", temp_file], 
                         capture_output=True, text=True)
            
            # Check if screenshot was successfully saved
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                # Load the screenshot
                screenshot = Image.open(temp_file)
                
                # Clean up the temporary file
                os.remove(temp_file)
                
                return screenshot
            else:
                logger.debug(f"Screenshot file not created or empty: {temp_file}")
                return None
                
        except Exception as e:
            logger.error(f"Error in second macOS capture approach: {e}")
            return None
    
    def _capture_macos_window_v3(self) -> Optional[Image.Image]:
        """
        Third approach - simple backup using screencapture to capture the active window
        
        Returns:
            Optional[Image.Image]: Active window screenshot or None if failed
        """
        try:
            # Create a temporary file to save the screenshot
            temp_file = f"/tmp/window_screenshot_{int(time.time())}.png"
            
            # Attempt to capture the active window with -W flag using timeout
            # First check if the temp directory exists
            temp_dir = os.path.dirname(temp_file)
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            # Run command with timeout
            process = subprocess.Popen(["screencapture", "-W", temp_file], 
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
            
            # Wait for command to finish, with timeout
            timeout = 15  # 15 seconds timeout
            
            try:
                process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Kill the process
                process.kill()
                process.communicate()  # Clean up
                # Try a full-screen capture as fallback
                try:
                    subprocess.run(["screencapture", temp_file], 
                                  capture_output=True, 
                                  timeout=10)  # 10 second timeout for full screen
                except subprocess.TimeoutExpired:
                    # Just continue and check if file exists
                    pass
            
            # If active window capture fails, fallback to full screen capture
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                subprocess.run(["screencapture", temp_file], 
                              capture_output=True, text=True, timeout=10)
            
            # Load the captured image
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                try:
                    screenshot = Image.open(temp_file)
                    
                    # Clean up the temporary file
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                    return screenshot
                except Exception:
                    pass
            
            # Last resort - use PIL's ImageGrab
            try:
                return ImageGrab.grab()
            except:
                pass
        except:
            # Last resort - use PIL's ImageGrab
            try:
                return ImageGrab.grab()
            except:
                pass
        
        return None
    
    def save_screenshot(self, image: Image.Image, path: str) -> str:
        """
        Save screenshot to file
        
        Args:
            image: PIL Image object
            path: Path to save the screenshot to
            
        Returns:
            str: Path to the saved screenshot
        """
        if not HAS_PIL:
            logger.error("PIL/Pillow is not installed. Cannot save screenshot.")
            return ""
            
        # Save the image
        image.save(path)
        return os.path.abspath(path)
    
    def capture_and_save(self, window_id: str, save_path: Optional[str] = None) -> Optional[str]:
        """
        Capture a window screenshot and save it to a file
        
        Args:
            window_id: Window ID to capture
            save_path: Path to save the screenshot to (default: generates a filename)
            
        Returns:
            Optional[str]: Path to the saved screenshot, or None if failed
        """
        if save_path is None:
            save_path = f"window_shot_{int(time.time())}.png"
            
        screenshot = self.capture_window(window_id)
        if screenshot:
            return self.save_screenshot(screenshot, save_path)
        return None
    
    def _safe_resize_image(self, image: Image.Image, max_size: Optional[int] = None) -> Image.Image:
        """
        Safely resize an image to a maximum dimension while maintaining aspect ratio.
        Handles edge cases and errors that might occur during normal resize operations.
        
        Args:
            image: PIL Image object to resize
            max_size: Maximum width or height (in pixels), uses self.max_image_dimension if None
            
        Returns:
            Resized PIL Image object
        """
        # Use class config if no specific size provided
        if max_size is None:
            max_size = self.max_image_dimension
            
        try:
            width, height = image.size
            
            # If image is already smaller than max_size, return as is
            if width <= max_size and height <= max_size:
                return image
                
            # Calculate new dimensions
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
                
            # Try standard resizing first
            try:
                return image.resize((new_width, new_height), Image.LANCZOS)
            except:
                # Try with thumbnail method, which is more robust
                img_copy = image.copy()
                img_copy.thumbnail((new_width, new_height), Image.LANCZOS)
                return img_copy
                
        except:
            # Create a new blank image with target size
            try:
                mode = image.mode if image.mode in ('RGB', 'RGBA') else 'RGB'
                new_img = Image.new(mode, (min(width, max_size), min(height, max_size)), (255, 255, 255))
                
                # Attempt to paste the original image, scaled down
                if width > max_size or height > max_size:
                    # Calculate scaling factor to fit within max_size
                    scale = min(max_size / width, max_size / height)
                    scaled_width = int(width * scale)
                    scaled_height = int(height * scale)
                    
                    # Create a scaled version using a very basic method
                    try:
                        # Try a basic averaging resize method
                        scaled_img = image.resize((scaled_width, scaled_height), Image.NEAREST)
                        new_img.paste(scaled_img, (0, 0))
                    except:
                        # Just return the blank canvas if all else fails
                        pass
                        
                return new_img
            except:
                # If all else fails, return a small blank image
                return Image.new('RGB', (800, 600), (255, 255, 255))

    def get_screenshot_as_base64(self, image: Image.Image, format: str = "PNG") -> Optional[str]:
        """
        Convert screenshot to base64-encoded string
        
        Args:
            image: PIL Image object
            format: Image format (PNG, JPEG, etc.)
            
        Returns:
            str: Base64-encoded image data, or None if failed
        """
        if not HAS_PIL:
            logger.error("PIL/Pillow is not installed. Cannot process image.")
            return None
            
        try:
            # Check image size and resize if too large
            original_width, original_height = image.size
            
            # Calculate if resizing is needed
            if original_width > self.max_image_dimension or original_height > self.max_image_dimension:
                # Use safe resize method
                image = self._safe_resize_image(image)
            
            # Use optimized compression parameters based on format
            buffer = io.BytesIO()
            if format.upper() == "JPEG":
                image.save(buffer, format="JPEG", quality=85, optimize=True)
            elif format.upper() == "PNG":
                # Convert to RGB if image has alpha channel (makes PNG smaller)
                if image.mode == 'RGBA':
                    # Create white background
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    # Paste image with alpha channel on white background
                    background.paste(image, mask=image.split()[3])
                    image = background
                
                image.save(buffer, format="PNG", optimize=True, compress_level=9)
            else:
                image.save(buffer, format=format)
                
            buffer_size = len(buffer.getvalue())
            
            # Check if image is still too large
            if buffer_size > self.max_file_size_bytes:
                buffer = io.BytesIO()
                
                # Convert to RGB if needed
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                    
                image.save(buffer, format="JPEG", quality=75, optimize=True)
            
            image_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return image_data
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            
            # Try with a more aggressive image reduction as a last resort
            try:
                # Create a tiny thumbnail as last resort
                thumb = image.copy()
                thumb.thumbnail((800, 800), Image.LANCZOS)
                
                buffer = io.BytesIO()
                thumb.save(buffer, format="JPEG", quality=70)
                image_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                return image_data
            except:
                return None 