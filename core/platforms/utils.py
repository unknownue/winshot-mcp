"""
Shared utility functions for platform-specific window capture implementation.
"""

import os
import base64
import io
import logging
from typing import Optional

# Configure logging
logger = logging.getLogger("winshot")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL/Pillow is not installed. Image processing will fail.")


def save_screenshot(image: Image.Image, path: str) -> str:
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

def safe_resize_image(image: Image.Image, max_size: int) -> Image.Image:
    """
    Safely resize an image to a maximum dimension while maintaining aspect ratio.
    Handles edge cases and errors that might occur during normal resize operations.
    
    Args:
        image: PIL Image object to resize
        max_size: Maximum width or height (in pixels)
        
    Returns:
        Resized PIL Image object
    """
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

def get_screenshot_as_base64(image: Image.Image, format: str = "PNG", max_file_size_bytes: int = 5242880) -> Optional[str]:
    """
    Convert screenshot to base64-encoded string
    
    Args:
        image: PIL Image object
        format: Image format (PNG, JPEG, etc.)
        max_file_size_bytes: Maximum file size in bytes (default: 5MB)
        
    Returns:
        str: Base64-encoded image data, or None if failed
    """
    if not HAS_PIL:
        logger.error("PIL/Pillow is not installed. Cannot process image.")
        return None
        
    try:
        # Check image size and resize if too large
        original_width, original_height = image.size
        
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
        if buffer_size > max_file_size_bytes:
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