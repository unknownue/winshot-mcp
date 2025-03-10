#!/usr/bin/env python3
"""
Window Screenshot Module - Core functionality for capturing window screenshots

This module provides functionality to capture screenshots of specific application windows
across different operating systems (Windows, macOS, Linux).
"""

import os
import time
import platform
import logging
import base64
import io
from typing import Optional, List, Dict, Any, Union, Tuple

# Configure logging
logger = logging.getLogger("winshot")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Import platform-specific implementation
from .platforms import PlatformWindowCapture
from .platforms.utils import save_screenshot, safe_resize_image, get_screenshot_as_base64


class WindowShot:
    """Window screenshot utility for capturing screenshots of specific application windows"""
    
    def __init__(self, max_image_dimension=1200, max_file_size_mb=5):
        """
        Initialize the window screenshot utility
        
        Args:
            max_image_dimension: Maximum width or height of captured screenshots (in pixels)
            max_file_size_mb: Maximum file size of captured screenshots (in MB)
        """
        self.system = platform.system()  # Get operating system type
        self.max_image_dimension = max_image_dimension
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
        # Check for required dependencies
        if not HAS_PIL:
            logger.warning("PIL/Pillow is not installed. Image processing will fail.")
            
        # Initialize platform-specific implementation
        self.platform_impl = PlatformWindowCapture(max_image_dimension)
    
    def get_window_list(self) -> List[Dict[str, str]]:
        """
        Get a list of all visible windows in the current system
        
        Returns:
            List[Dict[str, str]]: List of window information, each containing window ID, title, etc.
        """
        # Use platform-specific implementation
        return self.platform_impl.get_window_list()
    
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
        
        # Use platform-specific implementation to capture the window
        screenshot = self.platform_impl.capture_window(window_id)
        
        return screenshot
    
    def save_screenshot(self, image: Image.Image, path: str) -> str:
        """
        Save screenshot to file
        
        Args:
            image: PIL Image object
            path: Path to save the screenshot to
            
        Returns:
            str: Path to the saved screenshot
        """
        return save_screenshot(image, path)
    
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
        if max_size is None:
            max_size = self.max_image_dimension
        return safe_resize_image(image, max_size)

    def get_screenshot_as_base64(self, image: Image.Image, format: str = "PNG") -> Optional[str]:
        """
        Convert screenshot to base64-encoded string
        
        Args:
            image: PIL Image object
            format: Image format (PNG, JPEG, etc.)
            
        Returns:
            str: Base64-encoded image data, or None if failed
        """
        return get_screenshot_as_base64(image, format, self.max_file_size_bytes) 