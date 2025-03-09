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
from typing import Optional, List, Dict, Any, Union, Tuple

try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class WindowShot:
    """Window screenshot utility for capturing screenshots of specific application windows"""
    
    def __init__(self):
        """Initialize the window screenshot utility"""
        self.system = platform.system()  # Get operating system type
        
        # Check for required dependencies
        if not HAS_PIL:
            print("Warning: PIL/Pillow is not installed. Image processing will fail.")
    
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
                print("First approach failed, trying simpler window detection...")
                windows = self._get_macos_window_list_v2()
                
            # If still no windows, try the simplest approach
            if not windows:
                print("Second approach failed, trying basic app detection...")
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
                print("Error: pygetwindow library is not installed. Please install with: pip install pygetwindow")
        
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
                print("Error: xdotool is not installed. Please install with: sudo apt-get install xdotool")
        
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
            print(f"AppleScript result: {result.stdout}")
            print(f"AppleScript error (if any): {result.stderr}")
            
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
            print(f"Error in first macOS window detection approach: {e}")
        
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
            print(f"AppleScript (v2) result: {result.stdout}")
            print(f"AppleScript (v2) error (if any): {result.stderr}")
            
            if result.stdout:
                window_strings = result.stdout.strip().split(", ")
                for window_str in window_strings:
                    if ":" in window_str:
                        parts = window_str.split(":", 1)
                        proc = parts[0].strip()
                        win = parts[1].strip()
                        windows.append({"id": f"{proc}:{win}", "title": win, "process": proc})
        except Exception as e:
            print(f"Error in second macOS window detection approach: {e}")
        
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
            print(f"AppleScript (v3) result: {result.stdout}")
            
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
            print(f"Error in third macOS window detection approach: {e}")
        
        # If all else fails, add at least one entry for testing
        if not windows:
            print("All detection methods failed. Adding a fallback entry for testing.")
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
            print("Error: PIL/Pillow is not installed. Cannot capture screenshot.")
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
                    print("First capture approach failed, trying simpler capture...")
                    screenshot = self._capture_macos_window_v2(proc_name)
                
                if screenshot is None:
                    print("Second capture approach failed, trying full screen capture...")
                    screenshot = self._capture_macos_window_v3()
                
                return screenshot
            
            elif self.system == "Windows":
                # Use pygetwindow library to capture Windows window
                try:
                    import pygetwindow as gw
                    window = gw.getWindowsWithTitle(window_id)[0]
                    window.activate()
                    time.sleep(0.5)  # Give window some time to activate
                    screenshot = ImageGrab.grab(bbox=(window.left, window.top, 
                                                     window.left+window.width, 
                                                     window.top+window.height))
                    return screenshot
                except ImportError:
                    print("Error: pygetwindow library is not installed. Please install with: pip install pygetwindow")
            
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
                    os.remove(temp_file)  # Delete temporary file
                    
                    return screenshot
                except FileNotFoundError:
                    print("Error: Required tools are not installed. Please install with: sudo apt-get install xdotool imagemagick")
        
        except Exception as e:
            print(f"Screenshot capture failed: {e}")
        
        return None
    
    def _capture_macos_window_v1(self, proc_name: str, win_name: str) -> Optional[Image.Image]:
        """
        First approach to capture a macOS window using AppleScript and screencapture
        
        Args:
            proc_name: Process name
            win_name: Window name
            
        Returns:
            Optional[Image.Image]: Captured window or None if failed
        """
        try:
            # Create a temporary file to save the screenshot
            temp_file = f"/tmp/window_screenshot_{int(time.time())}.png"
            
            # Try to find the window using AppleScript
            script = f"""
            tell application "System Events"
                set frontmost of process "{proc_name}" to true
                delay 0.5
                set windowList to every window of process "{proc_name}"
                repeat with aWindow in windowList
                    if name of aWindow contains "{win_name}" then
                        set frontWindow to aWindow
                        return id of frontWindow
                    end if
                end repeat
                -- If no match found, try to get first window
                if (count of windowList) > 0 then
                    set frontWindow to item 1 of windowList
                    return id of frontWindow
                end if
                return ""
            end tell
            """
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            window_id = result.stdout.strip()
            
            if window_id:
                # Capture the specific window using the -l flag (window by ID)
                subprocess.run(["screencapture", "-l", window_id, temp_file], 
                             capture_output=True, text=True)
            else:
                # Fallback to window selection by application name
                activate_script = f"""
                tell application "{proc_name}"
                    activate
                    delay 0.5
                end tell
                """
                subprocess.run(["osascript", "-e", activate_script], capture_output=True, text=True)
                time.sleep(0.5)
                
                # Try to get the window id of frontmost window
                frontmost_script = f"""
                tell application "System Events"
                    set frontApp to first application process whose frontmost is true
                    if name of frontApp is "{proc_name}" then
                        set frontWindow to first window of frontApp
                        return id of frontWindow
                    end if
                    return ""
                end tell
                """
                result = subprocess.run(["osascript", "-e", frontmost_script], 
                                     capture_output=True, text=True)
                window_id = result.stdout.strip()
                
                if window_id:
                    # Use the window ID for capture
                    subprocess.run(["screencapture", "-l", window_id, temp_file], 
                                 capture_output=True, text=True)
                else:
                    # Last resort: use -w to capture the frontmost window (non-interactive)
                    subprocess.run(["screencapture", "-w", temp_file], 
                                 capture_output=True, text=True)
            
            # Load the captured image
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                screenshot = Image.open(temp_file)
                # Clean up the temporary file
                try:
                    os.remove(temp_file)
                except:
                    pass
                return screenshot
            else:
                print(f"Screenshot file not created or empty: {temp_file}")
        except Exception as e:
            print(f"Error in first macOS capture approach: {e}")
        
        return None
    
    def _capture_macos_window_v2(self, app_name: str) -> Optional[Image.Image]:
        """
        Second approach to capture a macOS window - activate the app and capture its window
        
        Args:
            app_name: Application name
            
        Returns:
            Optional[Image.Image]: Captured window or None if failed
        """
        try:
            # Create a temporary file to save the screenshot
            temp_file = f"/tmp/window_screenshot_{int(time.time())}.png"
            
            # Use AppleScript to activate the app and then screencapture to capture the window
            script = f"""
            tell application "{app_name}"
                activate
                delay 0.5
            end tell
            """
            # First activate the application
            subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            time.sleep(0.5)
            
            # Then use screencapture with -l flag to capture window by window id
            try:
                # Get the frontmost window ID
                frontmost_script = f"""
                tell application "System Events"
                    tell process "{app_name}"
                        set frontWindow to first window whose value of attribute "AXMain" is true
                        return id of frontWindow
                    end tell
                end tell
                """
                result = subprocess.run(["osascript", "-e", frontmost_script], 
                                      capture_output=True, text=True)
                window_id = result.stdout.strip()
                
                if window_id:
                    # Capture the specific window using the -l flag (window by ID)
                    subprocess.run(["screencapture", "-l", window_id, temp_file], 
                                 capture_output=True, text=True)
                else:
                    # Alternative approach - try to get the frontmost app's window
                    alt_script = f"""
                    tell application "System Events"
                        set frontApp to first application process whose frontmost is true
                        if frontApp exists then
                            set frontWindow to first window of frontApp
                            return id of frontWindow
                        end if
                        return ""
                    end tell
                    """
                    result = subprocess.run(["osascript", "-e", alt_script], 
                                         capture_output=True, text=True)
                    window_id = result.stdout.strip()
                    
                    if window_id:
                        # Use the window ID for capture
                        subprocess.run(["screencapture", "-l", window_id, temp_file], 
                                     capture_output=True, text=True)
                    else:
                        # Fallback to capturing the frontmost window (non-interactive)
                        subprocess.run(["screencapture", "-w", temp_file], 
                                     capture_output=True, text=True)
            except Exception as window_ex:
                print(f"Error getting window ID: {window_ex}")
                # Fallback to capturing the frontmost window (non-interactive)
                subprocess.run(["screencapture", "-w", temp_file], 
                             capture_output=True, text=True)
            
            # Load the captured image
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                screenshot = Image.open(temp_file)
                # Clean up the temporary file
                try:
                    os.remove(temp_file)
                except:
                    pass
                return screenshot
            else:
                print(f"Screenshot file not created or empty: {temp_file}")
                return None
                
        except Exception as e:
            print(f"Error in second macOS capture approach: {e}")
        
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
            
            # Attempt to capture the active window with -W flag
            # This is the most basic approach that should work in most cases
            subprocess.run(["screencapture", "-W", temp_file], 
                         capture_output=True, text=True)
            
            # If that fails, fallback to full screen capture
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                print("Active window capture failed, falling back to full screen capture...")
                subprocess.run(["screencapture", temp_file], 
                             capture_output=True, text=True)
            
            # Load the captured image
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                screenshot = Image.open(temp_file)
                # Clean up the temporary file
                try:
                    os.remove(temp_file)
                except:
                    pass
                return screenshot
            else:
                print(f"Screenshot file not created or empty: {temp_file}")
                # Last resort - use PIL's ImageGrab
                return ImageGrab.grab()
        except Exception as e:
            print(f"Error in third macOS capture approach: {e}")
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
            path: Save path
            
        Returns:
            str: Path to the saved file
        """
        if not HAS_PIL:
            print("Error: PIL/Pillow is not installed. Cannot save screenshot.")
            return None
            
        image.save(path)
        return path
    
    def capture_and_save(self, window_id: str, save_path: Optional[str] = None) -> Optional[str]:
        """
        Capture window screenshot and save to file
        
        Args:
            window_id: Window ID
            save_path: Save path, uses a temporary file if None
            
        Returns:
            str: Path to the saved file, or None if failed
        """
        screenshot = self.capture_window(window_id)
        if screenshot:
            if save_path is None:
                save_path = f"window_shot_{int(time.time())}.png"
            return self.save_screenshot(screenshot, save_path)
        return None
        
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
            print("Error: PIL/Pillow is not installed. Cannot process image.")
            return None
            
        try:
            buffer = io.BytesIO()
            image.save(buffer, format=format)
            image_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return image_data
        except Exception as e:
            print(f"Error converting image to base64: {e}")
            return None 