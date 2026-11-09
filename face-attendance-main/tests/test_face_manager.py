"""
Tests for Face Manager module.
Property-based tests for face detection and processing.
"""

import io
import numpy as np
from PIL import Image, ImageDraw
import pytest
from hypothesis import given, strategies as st, assume
from src.face_manager import FaceManager, FaceDetector, BoundingBox


class TestFaceManager:
    """Test class for FaceManager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.face_manager = FaceManager()
        self.face_detector = FaceDetector()
    
    def create_test_image_with_face(self, width: int, height: int) -> bytes:
        """Create a test image with a simple face-like pattern."""
        # Create a simple image with a face-like pattern
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Draw a simple face-like pattern (circle for head, dots for eyes)
        center_x, center_y = width // 2, height // 2
        face_size = min(width, height) // 3
        
        # Head (circle)
        draw.ellipse([
            center_x - face_size, center_y - face_size,
            center_x + face_size, center_y + face_size
        ], fill='lightpink', outline='black')
        
        # Eyes (dots)
        eye_offset = face_size // 3
        draw.ellipse([
            center_x - eye_offset - 5, center_y - eye_offset - 5,
            center_x - eye_offset + 5, center_y - eye_offset + 5
        ], fill='black')
        draw.ellipse([
            center_x + eye_offset - 5, center_y - eye_offset - 5,
            center_x + eye_offset + 5, center_y - eye_offset + 5
        ], fill='black')
        
        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG')
        return buffer.getvalue()
    
    def create_simple_test_image(self, width: int, height: int) -> bytes:
        """Create a simple test image without face patterns."""
        image = Image.new('RGB', (width, height), color='blue')
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG')
        return buffer.getvalue()
    
    # Property 1: Face detection consistency
    @given(
        width=st.integers(min_value=200, max_value=800),
        height=st.integers(min_value=200, max_value=800)
    )
    def test_face_detection_consistency(self, width, height):
        """
        Feature: face-attendance-system, Property 1: Face detection consistency
        For any valid image, face detection should return consistent results.
        **Validates: Requirements 1.1**
        """
        # Create test image
        image_bytes = self.create_simple_test_image(width, height)
        
        # Process image
        image_array, faces = self.face_manager.process_image_bytes(image_bytes)
        
        # Verify image processing
        assert isinstance(image_array, np.ndarray)
        assert image_array.shape[:2] == (height, width)  # Height, Width for numpy arrays
        assert len(image_array.shape) == 3  # RGB channels
        
        # Verify faces list
        assert isinstance(faces, list)
        
        # If faces are detected, verify bounding box properties
        for face in faces:
            assert isinstance(face, BoundingBox)
            assert 0 <= face.x1 < face.x2 <= width
            assert 0 <= face.y1 < face.y2 <= height
            assert 0 <= face.confidence <= 1.0
    
    # Property 19: Face cropping consistency
    @given(
        width=st.integers(min_value=300, max_value=600),
        height=st.integers(min_value=300, max_value=600),
        padding=st.floats(min_value=0.1, max_value=0.5)
    )
    def test_face_cropping_consistency(self, width, height, padding):
        """
        Feature: face-attendance-system, Property 19: Face cropping consistency
        For any detected face, cropping should produce properly padded face images.
        **Validates: Requirements 6.1**
        """
        # Create test image
        image_bytes = self.create_simple_test_image(width, height)
        image_array, _ = self.face_manager.process_image_bytes(image_bytes)
        
        # Create a mock bounding box in the center of the image
        face_width = width // 4
        face_height = height // 4
        center_x, center_y = width // 2, height // 2
        
        bbox = BoundingBox(
            x1=center_x - face_width // 2,
            y1=center_y - face_height // 2,
            x2=center_x + face_width // 2,
            y2=center_y + face_height // 2,
            confidence=0.9
        )
        
        # Crop face
        cropped_face = self.face_manager.crop_face(image_array, bbox, padding)
        
        # Verify cropped face properties
        assert isinstance(cropped_face, np.ndarray)
        assert len(cropped_face.shape) == 3  # RGB channels
        assert cropped_face.shape[2] == 3  # RGB channels
        
        # Verify cropped dimensions are reasonable
        expected_width = face_width * (1 + 2 * padding)
        expected_height = face_height * (1 + 2 * padding)
        
        # Allow some tolerance for boundary constraints
        assert cropped_face.shape[1] <= expected_width + 10  # Width
        assert cropped_face.shape[0] <= expected_height + 10  # Height
        assert cropped_face.shape[1] > 0
        assert cropped_face.shape[0] > 0