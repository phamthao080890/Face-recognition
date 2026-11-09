"""
Image Processor module for face attendance system.
Handles image resizing, thumbnail generation, and base64 encoding/decoding.
"""

import base64
import io
from typing import Tuple
from PIL import Image
import numpy as np


class ImageProcessor:
    """Handles image processing operations for the face attendance system."""
    
    def resize_image(self, image_bytes: bytes, width: int) -> bytes:
        """
        Resize image to specified width while maintaining aspect ratio.
        
        Args:
            image_bytes: Input image as bytes
            width: Target width in pixels
            
        Returns:
            Resized image as bytes
        """
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Calculate new height maintaining aspect ratio
        aspect_ratio = image.height / image.width
        new_height = int(width * aspect_ratio)
        
        # Resize image
        resized_image = image.resize((width, new_height), Image.Resampling.LANCZOS)
        
        # Convert back to bytes
        output_buffer = io.BytesIO()
        resized_image.save(output_buffer, format=image.format or 'JPEG')
        return output_buffer.getvalue()
    
    def create_thumbnail(self, image_bytes: bytes, size: Tuple[int, int]) -> bytes:
        """
        Create thumbnail of specified size.
        
        Args:
            image_bytes: Input image as bytes
            size: Target size as (width, height) tuple
            
        Returns:
            Thumbnail image as bytes
        """
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Create thumbnail (maintains aspect ratio and fits within size)
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Create new image with exact size and paste thumbnail centered
        thumbnail = Image.new('RGB', size, (255, 255, 255))  # White background
        
        # Calculate position to center the thumbnail
        x = (size[0] - image.width) // 2
        y = (size[1] - image.height) // 2
        thumbnail.paste(image, (x, y))
        
        # Convert to bytes
        output_buffer = io.BytesIO()
        thumbnail.save(output_buffer, format='JPEG')
        return output_buffer.getvalue()
    
    def encode_base64(self, image_bytes: bytes) -> str:
        """
        Encode image bytes to base64 string.
        
        Args:
            image_bytes: Input image as bytes
            
        Returns:
            Base64 encoded string
        """
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def decode_base64(self, encoded_string: str) -> bytes:
        """
        Decode base64 string to image bytes.
        
        Args:
            encoded_string: Base64 encoded string
            
        Returns:
            Image as bytes
        """
        return base64.b64decode(encoded_string)