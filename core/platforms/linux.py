"""
Linux platform-specific window capture implementation.
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


class LinuxWindowCapture:
    """Window capture implementation for Linux"""
    
    def __init__(self, max_image_dimension=1200, save_locally=False):
        """
        Initialize the Linux window capture utility
        
        Args:
            max_image_dimension: Maximum width or height of captured screenshots (in pixels)
            save_locally: Whether to save screenshots locally (default: False)
        """
        self.max_image_dimension = max_image_dimension
        self.save_locally = save_locally
    
    def get_window_list(self) -> List[Dict[str, str]]:
        """
        Get a list of all visible windows in Linux
        
        Returns:
            List[Dict[str, str]]: List of window information, each containing window ID, title, etc.
        """
        windows = []
        try:
            # Use xdotool to get Linux window list
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
        except Exception as e:
            logger.error(f"Error retrieving Linux window list: {e}")
            
        return windows
        
    def capture_window(self, window_id: str) -> Optional[Image.Image]:
        """
        Capture a screenshot of the specified window on Linux
        
        Args:
            window_id: Window ID (X11 window ID)
            
        Returns:
            PIL.Image.Image: Window screenshot, or None if failed
        """
        if not HAS_PIL:
            logger.error("PIL/Pillow is not installed. Cannot capture screenshot.")
            return None
            
        try:
            # Activate window
            subprocess.run(["xdotool", "windowactivate", window_id])
            time.sleep(0.5)  # Give window some time to activate
            
            # Capture window screenshot
            temp_file = f"/tmp/window_shot_{int(time.time())}.png"
            subprocess.run(["import", "-window", window_id, temp_file])
            
            # Read screenshot
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
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
                    self._save_screenshot(screenshot, filename)
                
                # Clean up temp file
                try:
                    os.remove(temp_file)
                except:
                    pass
                
                return screenshot
            else:
                logger.error(f"Screenshot file not created or empty: {temp_file}")
            
        except FileNotFoundError:
            logger.error("Required tools are not installed. Please install with: sudo apt-get install xdotool imagemagick")
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
        
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