"""
macOS platform-specific window capture implementation.
"""

import os
import time
import subprocess
import logging
from typing import Optional, List, Dict

# Configure logging
logger = logging.getLogger("winshot")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL/Pillow is not installed. Image processing will fail.")


class MacOSWindowCapture:
    """Window capture implementation for macOS"""
    
    def __init__(self, max_image_dimension=1200):
        """
        Initialize the macOS window capture utility
        
        Args:
            max_image_dimension: Maximum width or height of captured screenshots (in pixels)
        """
        self.max_image_dimension = max_image_dimension
    
    def get_window_list(self) -> List[Dict[str, str]]:
        """
        Get a list of all visible windows in macOS
        
        Returns:
            List[Dict[str, str]]: List of window information, each containing window ID, title, etc.
        """
        windows = self._get_window_list_v1()
        
        # If first approach failed, try simpler approach
        if not windows:
            logger.debug("First approach failed, trying simpler window detection...")
            windows = self._get_window_list_v2()
            
        # If still no windows, try the simplest approach
        if not windows:
            logger.debug("Second approach failed, trying basic app detection...")
            windows = self._get_window_list_v3()
        
        return windows
        
    def _get_window_list_v1(self) -> List[Dict[str, str]]:
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
    
    def _get_window_list_v2(self) -> List[Dict[str, str]]:
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
    
    def _get_window_list_v3(self) -> List[Dict[str, str]]:
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
        Capture a screenshot of the specified window on macOS
        
        Args:
            window_id: Window ID in the format "process:window"
            
        Returns:
            PIL.Image.Image: Window screenshot, or None if failed
        """
        if not HAS_PIL:
            logger.error("PIL/Pillow is not installed. Cannot capture screenshot.")
            return None
            
        try:
            # Parse window_id
            try:
                proc_name, win_name = window_id.split(":", 1)
            except ValueError:
                # Fallback if window_id doesn't contain a colon
                proc_name = window_id
                win_name = "MainWindow"
            
            # Try different capture approaches
            screenshot = self._capture_window_v1(proc_name, win_name)
            
            if screenshot is None:
                logger.debug("First capture approach failed, trying simpler capture...")
                screenshot = self._capture_window_v2(proc_name)
            
            if screenshot is None:
                logger.debug("Second capture approach failed, trying full screen capture...")
                screenshot = self._capture_window_v3()
            
            # Resize image if needed
            if screenshot:
                width, height = screenshot.size
                logger.info(f"Original screenshot size: {width}x{height} pixels")
                if width > self.max_image_dimension or height > self.max_image_dimension:
                    screenshot = self._safe_resize_image(screenshot)
                    width, height = screenshot.size
                    logger.info(f"Resized screenshot to: {width}x{height} pixels")
            
            return screenshot
            
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
        
        return None
    
    def _capture_window_v1(self, proc_name: str, win_name: str) -> Optional[Image.Image]:
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
    
    def _capture_window_v2(self, app_name: str) -> Optional[Image.Image]:
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
    
    def _capture_window_v3(self) -> Optional[Image.Image]:
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
                from PIL import ImageGrab
                return ImageGrab.grab()
            except:
                pass
        except:
            # Last resort - use PIL's ImageGrab
            try:
                from PIL import ImageGrab
                return ImageGrab.grab()
            except:
                pass
        
        return None
    
    def _save_screenshot(self, image: Image.Image, path: str) -> str:
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