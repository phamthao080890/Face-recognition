"""
Tests for Image Processor module.
Property-based tests for image processing operations.
"""

import io
import base64
from PIL import Image
import pytest
from hypothesis import given, strategies as st
from src.image_processor import ImageProcessor


class TestImageProcessor:
    """Test class for ImageProcessor functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.processor = ImageProcessor()
    
    def create_test_image(self, width: int, height: int, format: str = 'JPEG') -> bytes:
        """Create a test image with specified dimensions."""
        image = Image.new('RGB', (width, height), color='red')
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
    
    # Property 20: Image resizing consistency
    @given(
        original_width=st.integers(min_value=100, max_value=2000),
        original_height=st.integers(min_value=100, max_value=2000),
        target_width=st.integers(min_value=50, max_value=1000)
    )
    def test_image_resizing_consistency(self, original_width, original_height, target_width):
        """
        Feature: face-attendance-system, Property 20: Image resizing consistency
        For any image, resizing to specified width should maintain aspect ratio.
        **Validates: Requirements 6.2**
        """
        # Create test image
        image_bytes = self.create_test_image(original_width, original_height)
        
        # Resize image
        resized_bytes = self.processor.resize_image(image_bytes, target_width)
        
        # Verify resized image
        resized_image = Image.open(io.BytesIO(resized_bytes))
        
        # Check width is exactly target width
        assert resized_image.width == target_width
        
        # Check aspect ratio is maintained (within small tolerance for rounding)
        original_aspect_ratio = original_height / original_width
        resized_aspect_ratio = resized_image.height / resized_image.width
        assert abs(original_aspect_ratio - resized_aspect_ratio) < 0.02  # Increased tolerance for rounding
    
    # Property 21: Thumbnail generation consistency
    @given(
        original_width=st.integers(min_value=100, max_value=2000),
        original_height=st.integers(min_value=100, max_value=2000)
    )
    def test_thumbnail_generation_consistency(self, original_width, original_height):
        """
        Feature: face-attendance-system, Property 21: Thumbnail generation consistency
        For any image, thumbnail generation should produce exactly 150x150 pixel images.
        **Validates: Requirements 6.3**
        """
        # Create test image
        image_bytes = self.create_test_image(original_width, original_height)
        
        # Create thumbnail
        thumbnail_bytes = self.processor.create_thumbnail(image_bytes, (150, 150))
        
        # Verify thumbnail
        thumbnail_image = Image.open(io.BytesIO(thumbnail_bytes))
        
        # Check exact dimensions
        assert thumbnail_image.width == 150
        assert thumbnail_image.height == 150
    
    # Property 23: Base64 storage format
    @given(
        width=st.integers(min_value=50, max_value=500),
        height=st.integers(min_value=50, max_value=500)
    )
    def test_base64_storage_format(self, width, height):
        """
        Feature: face-attendance-system, Property 23: Base64 storage format
        For any image, base64 encoding then decoding should produce equivalent bytes.
        **Validates: Requirements 6.5**
        """
        # Create test image
        original_bytes = self.create_test_image(width, height)
        
        # Encode to base64
        encoded_string = self.processor.encode_base64(original_bytes)
        
        # Verify encoded string is valid base64
        assert isinstance(encoded_string, str)
        assert len(encoded_string) > 0
        
        # Decode back to bytes
        decoded_bytes = self.processor.decode_base64(encoded_string)
        
        # Verify round-trip consistency
        assert decoded_bytes == original_bytes
        
        # Verify decoded bytes can be opened as image
        decoded_image = Image.open(io.BytesIO(decoded_bytes))
        assert decoded_image.width == width
        assert decoded_image.height == height