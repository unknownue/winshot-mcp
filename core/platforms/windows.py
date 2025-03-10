"""
Windows platform-specific window capture implementation.
"""

import os
import time
import logging
from typing import Optional, List, Dict

# Configure logging
logger = logging.getLogger("winshot")

try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL/Pillow is not installed. Image processing will fail.")


class WindowsWindowCapture:
    """Window capture implementation for Windows"""
    
    def __init__(self, max_image_dimension=1200, save_locally=False):
        """
        Initialize the Windows window capture utility
        
        Args:
            max_image_dimension: Maximum width or height of captured screenshots (in pixels)
            save_locally: Whether to save screenshots locally (default: False)
        """
        self.max_image_dimension = max_image_dimension
        self.save_locally = save_locally
    
    def get_window_list(self) -> List[Dict[str, str]]:
        """
        Get a list of all visible windows in Windows
        
        Returns:
            List[Dict[str, str]]: List of window information, each containing window ID, title, etc.
        """
        windows = []
        try:
            # Use pygetwindow library to get Windows window list
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
            
        return windows
        
    def capture_window(self, window_id: str) -> Optional[Image.Image]:
        """
        Capture a screenshot of the specified window on Windows
        
        Args:
            window_id: Window handle as string
            
        Returns:
            PIL.Image.Image: Window screenshot, or None if failed
        """
        if not HAS_PIL:
            logger.error("PIL/Pillow is not installed. Cannot capture screenshot.")
            return None
            
        try:
            # Use pygetwindow library to capture Windows window
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
                    self._save_screenshot(screenshot, filename)
                
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