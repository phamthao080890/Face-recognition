"""
Integration tests for Face Attendance System.
Tests complete face recognition workflow, API endpoints with real database connections,
and error scenarios and edge cases.

Requirements: All requirements integration
"""

import pytest
import os
import io
import time
import numpy as np
from PIL import Image
from typing import List, Dict, Any
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Import system components
from src.database import MongoDBConnection, QdrantConnection, UserInfo, ImageData
from src.face_manager import FaceManager, BoundingBox
from src.user_manager import UserManager, UserCreateData, UserUpdateData
from src.user_manager import ValidationError, DuplicateUserError, UserNotFoundError, ImageLimitExceededError, UnsupportedFormatError
from src.image_processor import ImageProcessor


class TestDatabaseIntegration:
    """Test database connections and operations with real database instances."""
    
    @pytest.fixture(scope="class")
    def mongodb_connection(self):
        """Create MongoDB connection for testing."""
        # Use test database to avoid conflicts
        connection = MongoDBConnection(
            connection_string="mongodb://admin:password123@localhost:27018",
            database_name="face_attendance_test"
        )
        yield connection
        
        # Cleanup: Drop test database
        try:
            connection.client.drop_database("face_attendance_test")
            connection.close()
        except Exception:
            pass
    
    @pytest.fixture(scope="class")
    def qdrant_connection(self):
        """Create Qdrant connection for testing."""
        connection = QdrantConnection(
            host="localhost",
            port=6333,
            collection_name="face_vectors_test"
        )
        yield connection
        
        # Cleanup: Delete test collection
        try:
            connection.client.delete_collection("face_vectors_test")
            connection.close()
        except Exception:
            pass
    
    def test_mongodb_connection_and_operations(self, mongodb_connection):
        """Test MongoDB connection establishment and basic operations."""
        # Test connection is established
        assert mongodb_connection.client is not None
        assert mongodb_connection.database is not None
        
        # Test ping
        result = mongodb_connection.client.admin.command('ping')
        assert result['ok'] == 1
        
        # Test collection access
        assert mongodb_connection.users_collection is not None
    
    def test_qdrant_connection_and_operations(self, qdrant_connection):
        """Test Qdrant connection establishment and basic operations."""
        # Test connection is established
        assert qdrant_connection.client is not None
        
        # Test collection info
        info = qdrant_connection.get_collection_info()
        assert isinstance(info, dict)
    
    def test_mongodb_user_crud_operations(self, mongodb_connection):
        """Test complete MongoDB CRUD operations for users."""
        # Create test user
        test_user = UserInfo(
            id=None,
            name="Integration Test User",
            email="integration@test.com",
            phone="123456789",
            department="Testing",
            images=[]
        )
        
        # Test create
        user_id = mongodb_connection.create_user(test_user)
        assert user_id is not None
        assert len(user_id) > 0
        
        # Test read
        retrieved_user = mongodb_connection.get_user(user_id)
        assert retrieved_user is not None
        assert retrieved_user.name == test_user.name
        assert retrieved_user.email == test_user.email
        
        # Test read by email
        user_by_email = mongodb_connection.get_user_by_email(test_user.email)
        assert user_by_email is not None
        assert user_by_email.id == user_id
        
        # Test update
        retrieved_user.name = "Updated Test User"
        update_success = mongodb_connection.update_user(user_id, retrieved_user)
        assert update_success is True
        
        # Verify update
        updated_user = mongodb_connection.get_user(user_id)
        assert updated_user.name == "Updated Test User"
        
        # Test get all users
        all_users = mongodb_connection.get_all_users()
        assert len(all_users) >= 1
        assert any(user.id == user_id for user in all_users)
        
        # Test delete
        delete_success = mongodb_connection.delete_user(user_id)
        assert delete_success is True
        
        # Verify deletion
        deleted_user = mongodb_connection.get_user(user_id)
        assert deleted_user is None
    
    def test_qdrant_vector_operations(self, qdrant_connection):
        """Test Qdrant vector storage and search operations."""
        # Create test vectors
        test_vector1 = np.random.rand(512).astype(np.float32)
        test_vector2 = np.random.rand(512).astype(np.float32)
        
        user_id = "test_user_123"
        image_id1 = "test_image_1"
        image_id2 = "test_image_2"
        
        # Test vector storage
        vector_id1 = qdrant_connection.store_face_vector(user_id, image_id1, test_vector1)
        vector_id2 = qdrant_connection.store_face_vector(user_id, image_id2, test_vector2)
        
        assert vector_id1 is not None
        assert vector_id2 is not None
        assert vector_id1 != vector_id2
        
        # Test vector search
        search_results = qdrant_connection.search_similar_faces(test_vector1, limit=5, score_threshold=0.5)
        assert len(search_results) >= 1
        
        # The exact same vector should have high similarity
        found_exact_match = False
        for result_user_id, score in search_results:
            if result_user_id == user_id and score > 0.99:  # Very high similarity for exact match
                found_exact_match = True
                break
        assert found_exact_match
        
        # Test get user vectors
        user_vectors = qdrant_connection.get_user_vectors(user_id)
        assert len(user_vectors) == 2
        assert all(vec.user_id == user_id for vec in user_vectors)
        
        # Test delete specific vector
        delete_success = qdrant_connection.delete_vector(vector_id1)
        assert delete_success is True
        
        # Test delete all user vectors
        delete_all_success = qdrant_connection.delete_user_vectors(user_id)
        assert delete_all_success is True
        
        # Verify deletion
        remaining_vectors = qdrant_connection.get_user_vectors(user_id)
        assert len(remaining_vectors) == 0


class TestFaceRecognitionWorkflow:
    """Test complete face recognition workflow integration."""
    
    @pytest.fixture
    def sample_face_image(self):
        """Create a sample face image for testing."""
        # Create a simple test image (RGB)
        image = Image.new('RGB', (300, 300), color='white')
        
        # Add some basic features to simulate a face-like pattern
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        
        # Draw a simple face-like pattern
        # Head outline
        draw.ellipse([50, 50, 250, 250], outline='black', width=3)
        # Eyes
        draw.ellipse([80, 100, 120, 140], fill='black')
        draw.ellipse([180, 100, 220, 140], fill='black')
        # Nose
        draw.line([150, 140, 150, 180], fill='black', width=2)
        # Mouth
        draw.arc([120, 180, 180, 220], 0, 180, fill='black', width=2)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG')
        return img_buffer.getvalue()
    
    @pytest.fixture
    def face_manager(self):
        """Create FaceManager instance for testing."""
        return FaceManager()
    
    @pytest.fixture
    def image_processor(self):
        """Create ImageProcessor instance for testing."""
        return ImageProcessor()
    
    def test_complete_face_processing_workflow(self, face_manager, sample_face_image):
        """Test complete face detection and encoding workflow."""
        # Test image processing from bytes
        image_array, detected_faces = face_manager.process_image_bytes(sample_face_image)
        
        # Verify image processing
        assert image_array is not None
        assert image_array.shape[2] == 3  # RGB channels
        assert isinstance(detected_faces, list)
        
        # Note: YOLOv8n might not detect faces in our simple test image,
        # but we can still test the workflow with mock detection
        if len(detected_faces) == 0:
            # Create a mock bounding box for testing
            mock_bbox = BoundingBox(50, 50, 250, 250, 0.9)
            detected_faces = [mock_bbox]
        
        # Test face cropping and encoding for each detected face
        for bbox in detected_faces:
            # Test face cropping
            cropped_face = face_manager.crop_face(image_array, bbox)
            assert cropped_face is not None
            assert len(cropped_face.shape) == 3  # Height, Width, Channels
            
            # Test face encoding
            face_vector = face_manager.encode_face(cropped_face)
            assert face_vector is not None
            assert face_vector.shape == (512,)  # FaceNet produces 512-dimensional vectors
            assert face_vector.dtype == np.float64 or face_vector.dtype == np.float32
    
    def test_face_similarity_calculation(self, face_manager, sample_face_image):
        """Test face similarity calculation and matching."""
        # Process image to get face vector
        image_array, detected_faces = face_manager.process_image_bytes(sample_face_image)
        
        if len(detected_faces) == 0:
            mock_bbox = BoundingBox(50, 50, 250, 250, 0.9)
            detected_faces = [mock_bbox]
        
        # Get face vectors
        face_vectors = []
        for bbox in detected_faces:
            cropped_face = face_manager.crop_face(image_array, bbox)
            face_vector = face_manager.encode_face(cropped_face)
            face_vectors.append(face_vector)
        
        if len(face_vectors) >= 1:
            vector1 = face_vectors[0]
            
            # Test similarity with itself (should be 1.0 or very close)
            self_similarity = face_manager.calculate_cosine_similarity(vector1, vector1)
            assert self_similarity >= 0.99  # Should be very close to 1.0
            
            # Test matching with itself
            is_match = face_manager.is_match(vector1, vector1, threshold=0.8)
            assert is_match is True
            
            # Test with random vector (should be low similarity)
            random_vector = np.random.rand(512).astype(np.float32)
            random_similarity = face_manager.calculate_cosine_similarity(vector1, random_vector)
            assert 0.0 <= random_similarity <= 1.0
            
            # Test search functionality
            stored_vectors = [("user1", vector1), ("user2", random_vector)]
            match_result = face_manager.search_similar_face(vector1, stored_vectors, threshold=0.8)
            assert match_result == "user1"  # Should match the identical vector
    
    def test_image_processing_workflow(self, image_processor, sample_face_image):
        """Test complete image processing workflow."""
        # Test image resizing
        resized_image = image_processor.resize_image(sample_face_image, 600)
        assert resized_image is not None
        assert len(resized_image) > 0
        
        # Verify resized image dimensions
        resized_pil = Image.open(io.BytesIO(resized_image))
        assert resized_pil.width == 600
        
        # Test thumbnail creation
        thumbnail = image_processor.create_thumbnail(sample_face_image, (150, 150))
        assert thumbnail is not None
        assert len(thumbnail) > 0
        
        # Verify thumbnail dimensions
        thumbnail_pil = Image.open(io.BytesIO(thumbnail))
        assert thumbnail_pil.size == (150, 150)
        
        # Test base64 encoding/decoding
        encoded = image_processor.encode_base64(sample_face_image)
        assert encoded is not None
        assert isinstance(encoded, str)
        assert len(encoded) > 0
        
        # Test decoding
        decoded = image_processor.decode_base64(encoded)
        assert decoded == sample_face_image


class TestUserManagerIntegration:
    """Test UserManager integration with all components."""
    
    @pytest.fixture(scope="class")
    def test_databases(self):
        """Set up test databases."""
        mongodb = MongoDBConnection(
            connection_string="mongodb://admin:password123@localhost:27018",
            database_name="face_attendance_integration_test"
        )
        qdrant = QdrantConnection(
            host="localhost",
            port=6333,
            collection_name="face_vectors_integration_test"
        )
        
        yield mongodb, qdrant
        
        # Cleanup
        try:
            mongodb.client.drop_database("face_attendance_integration_test")
            mongodb.close()
            qdrant.client.delete_collection("face_vectors_integration_test")
            qdrant.close()
        except Exception:
            pass
    
    @pytest.fixture
    def user_manager(self, test_databases):
        """Create UserManager with test databases."""
        mongodb, qdrant = test_databases
        return UserManager(
            mongodb_connection=mongodb,
            qdrant_connection=qdrant,
            face_manager=FaceManager(),
            image_processor=ImageProcessor()
        )
    
    @pytest.fixture
    def sample_images(self):
        """Create multiple sample images for testing."""
        images = []
        for i in range(3):
            # Create different colored images
            colors = ['red', 'green', 'blue']
            image = Image.new('RGB', (200, 200), color=colors[i])
            
            # Add some variation to make them different
            from PIL import ImageDraw
            draw = ImageDraw.Draw(image)
            draw.rectangle([50 + i*10, 50 + i*10, 150 + i*10, 150 + i*10], outline='black', width=2)
            
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='JPEG')
            images.append(img_buffer.getvalue())
        
        return images
    
    def test_complete_user_creation_workflow(self, user_manager, sample_images):
        """Test complete user creation with image processing and face vector storage."""
        # Create user data
        user_data = UserCreateData(
            name="Integration Test User",
            email="integration.test@example.com",
            phone="123-456-7890",
            department="Testing Department"
        )
        
        # Test user creation
        created_user = user_manager.create_user(user_data, sample_images)
        
        # Verify user creation
        assert created_user is not None
        assert created_user.id is not None
        assert created_user.name == user_data.name
        assert created_user.email == user_data.email.lower()
        assert len(created_user.images) == len(sample_images)
        
        # Verify images are processed correctly
        for image_data in created_user.images:
            assert image_data.image_id is not None
            assert image_data.full_image is not None  # base64 encoded
            assert image_data.thumbnail is not None  # base64 encoded
            
            # Verify base64 encoding is valid
            from base64 import b64decode
            try:
                decoded_full = b64decode(image_data.full_image)
                decoded_thumb = b64decode(image_data.thumbnail)
                assert len(decoded_full) > 0
                assert len(decoded_thumb) > 0
            except Exception as e:
                pytest.fail(f"Invalid base64 encoding: {e}")
        
        # Test user retrieval
        retrieved_user = user_manager.get_user(created_user.id)
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.name == created_user.name
        
        # Test user listing
        all_users = user_manager.get_all_users()
        assert len(all_users) >= 1
        assert any(user.id == created_user.id for user in all_users)
        
        # Cleanup
        user_manager.delete_user(created_user.id)
    
    def test_user_update_workflow(self, user_manager, sample_images):
        """Test user update while preserving face vectors."""
        # Create initial user
        user_data = UserCreateData(
            name="Update Test User",
            email="update.test@example.com"
        )
        created_user = user_manager.create_user(user_data, sample_images[:1])
        
        # Test update
        update_data = UserUpdateData(
            name="Updated Test User",
            phone="987-654-3210",
            department="Updated Department"
        )
        
        updated_user = user_manager.update_user(created_user.id, update_data)
        
        # Verify update
        assert updated_user.name == update_data.name
        assert updated_user.phone == update_data.phone
        assert updated_user.department == update_data.department
        assert updated_user.email == created_user.email  # Should remain unchanged
        assert len(updated_user.images) == len(created_user.images)  # Images preserved
        
        # Cleanup
        user_manager.delete_user(created_user.id)
    
    def test_image_limit_enforcement(self, user_manager, sample_images):
        """Test image limit enforcement (max 5 images per user)."""
        # Create user with maximum images
        user_data = UserCreateData(
            name="Limit Test User",
            email="limit.test@example.com"
        )
        
        # Create 5 images (at the limit)
        five_images = sample_images + sample_images[:2]  # 3 + 2 = 5
        created_user = user_manager.create_user(user_data, five_images)
        
        assert len(created_user.images) == 5
        
        # Try to add more images (should fail)
        with pytest.raises(ImageLimitExceededError):
            user_manager.add_user_images(created_user.id, sample_images[:1])
        
        # Verify image count validation
        assert not user_manager.validate_image_limit(created_user.id, 1)
        assert user_manager.validate_image_limit(created_user.id, 0)
        
        # Cleanup
        user_manager.delete_user(created_user.id)
    
    def test_complete_user_deletion(self, user_manager, sample_images):
        """Test complete user deletion from both MongoDB and Qdrant."""
        # Create user
        user_data = UserCreateData(
            name="Delete Test User",
            email="delete.test@example.com"
        )
        created_user = user_manager.create_user(user_data, sample_images[:1])
        user_id = created_user.id
        
        # Verify user exists in both databases
        retrieved_user = user_manager.get_user(user_id)
        assert retrieved_user is not None
        
        # Check if vectors exist in Qdrant (may be empty if no faces detected)
        vectors = user_manager.qdrant.get_user_vectors(user_id)
        # Note: vectors might be empty if face detection didn't work on test images
        
        # Delete user
        delete_success = user_manager.delete_user(user_id)
        assert delete_success is True
        
        # Verify deletion from MongoDB
        deleted_user = user_manager.get_user(user_id)
        assert deleted_user is None
        
        # Verify deletion from Qdrant
        remaining_vectors = user_manager.qdrant.get_user_vectors(user_id)
        assert len(remaining_vectors) == 0


class TestErrorHandlingAndEdgeCases:
    """Test error scenarios and edge cases."""
    
    @pytest.fixture
    def user_manager(self):
        """Create UserManager with test databases for error testing."""
        mongodb = MongoDBConnection(
            connection_string="mongodb://admin:password123@localhost:27018",
            database_name="face_attendance_error_test"
        )
        qdrant = QdrantConnection(
            host="localhost",
            port=6333,
            collection_name="face_vectors_error_test"
        )
        
        manager = UserManager(
            mongodb_connection=mongodb,
            qdrant_connection=qdrant,
            face_manager=FaceManager(),
            image_processor=ImageProcessor()
        )
        
        yield manager
        
        # Cleanup
        try:
            mongodb.client.drop_database("face_attendance_error_test")
            mongodb.close()
            qdrant.client.delete_collection("face_vectors_error_test")
            qdrant.close()
        except Exception:
            pass
    
    def test_invalid_user_data_validation(self, user_manager):
        """Test validation of invalid user data."""
        # Test empty name
        with pytest.raises(ValidationError) as exc_info:
            user_data = UserCreateData(name="", email="test@example.com")
            user_manager.create_user(user_data, [self._create_test_image()])
        assert "Name is required" in str(exc_info.value)
        
        # Test invalid email
        with pytest.raises(ValidationError) as exc_info:
            user_data = UserCreateData(name="Test User", email="invalid-email")
            user_manager.create_user(user_data, [self._create_test_image()])
        assert "Invalid email format" in str(exc_info.value)
        
        # Test name too short
        with pytest.raises(ValidationError) as exc_info:
            user_data = UserCreateData(name="A", email="test@example.com")
            user_manager.create_user(user_data, [self._create_test_image()])
        assert "at least 2 characters" in str(exc_info.value)
    
    def test_duplicate_user_handling(self, user_manager):
        """Test handling of duplicate user creation."""
        # Create first user
        user_data = UserCreateData(
            name="Duplicate Test",
            email="duplicate@example.com"
        )
        first_user = user_manager.create_user(user_data, [self._create_test_image()])
        
        # Try to create duplicate user with same email
        with pytest.raises(DuplicateUserError) as exc_info:
            duplicate_data = UserCreateData(
                name="Another User",
                email="duplicate@example.com"  # Same email
            )
            user_manager.create_user(duplicate_data, [self._create_test_image()])
        
        assert "already exists" in str(exc_info.value)
        
        # Cleanup
        user_manager.delete_user(first_user.id)
    
    def test_user_not_found_scenarios(self, user_manager):
        """Test scenarios where user is not found."""
        fake_user_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format
        
        # Test get non-existent user
        user = user_manager.get_user(fake_user_id)
        assert user is None
        
        # Test update non-existent user
        with pytest.raises(UserNotFoundError):
            update_data = UserUpdateData(name="Updated Name")
            user_manager.update_user(fake_user_id, update_data)
        
        # Test delete non-existent user
        with pytest.raises(UserNotFoundError):
            user_manager.delete_user(fake_user_id)
    
    def test_invalid_image_handling(self, user_manager):
        """Test handling of invalid images."""
        user_data = UserCreateData(
            name="Image Test User",
            email="imagetest@example.com"
        )
        
        # Test empty image
        with pytest.raises(ValidationError) as exc_info:
            user_manager.create_user(user_data, [b""])
        assert "empty" in str(exc_info.value)
        
        # Test invalid image data
        with pytest.raises((ValidationError, UnsupportedFormatError)) as exc_info:
            user_manager.create_user(user_data, [b"not an image"])
        assert ("corrupted" in str(exc_info.value) or 
                "not a valid image" in str(exc_info.value) or 
                "too small" in str(exc_info.value))
        
        # Test oversized image
        large_image_data = b"fake_image_data" * 1000000  # Simulate large file
        with pytest.raises(ValidationError) as exc_info:
            user_manager.create_user(user_data, [large_image_data])
        assert "exceeds maximum size" in str(exc_info.value)
    
    def test_database_connection_error_handling(self):
        """Test handling of database connection errors."""
        # Test MongoDB connection with invalid connection string
        with pytest.raises(Exception):  # Should raise DatabaseConnectionError
            MongoDBConnection(connection_string="mongodb://invalid:27018")
        
        # Test Qdrant connection with invalid host
        with pytest.raises(Exception):
            QdrantConnection(host="invalid_host", port=6333)
    
    def test_face_processing_edge_cases(self):
        """Test edge cases in face processing."""
        face_manager = FaceManager()
        
        # Test with image containing no faces
        no_face_image = self._create_solid_color_image()
        image_array, detected_faces = face_manager.process_image_bytes(no_face_image)
        
        assert image_array is not None
        assert isinstance(detected_faces, list)
        # Note: detected_faces might be empty, which is expected for images without faces
        
        # Test face encoding with invalid dimensions
        invalid_face = np.random.rand(50, 50, 3).astype(np.uint8)  # Too small
        try:
            # This might work or fail depending on FaceNet's preprocessing
            face_vector = face_manager.encode_face(invalid_face)
            assert face_vector.shape == (512,)  # Should still produce 512-dim vector
        except Exception:
            # It's acceptable if encoding fails for invalid input
            pass
    
    def test_system_statistics_and_monitoring(self, user_manager):
        """Test system statistics and monitoring capabilities."""
        # Test statistics with empty system
        stats = user_manager.get_user_statistics()
        assert isinstance(stats, dict)
        assert "total_users" in stats
        assert "total_images" in stats
        assert stats["total_users"] >= 0
        
        # Create some test users
        for i in range(3):
            user_data = UserCreateData(
                name=f"Stats Test User {i}",
                email=f"stats{i}@example.com"
            )
            user = user_manager.create_user(user_data, [self._create_test_image()])
        
        # Test statistics with users
        updated_stats = user_manager.get_user_statistics()
        assert updated_stats["total_users"] >= 3
        assert updated_stats["total_images"] >= 3
        assert "average_images_per_user" in updated_stats
        
        # Cleanup
        all_users = user_manager.get_all_users()
        for user in all_users:
            if "Stats Test User" in user.name:
                user_manager.delete_user(user.id)
    
    def _create_test_image(self) -> bytes:
        """Create a simple test image."""
        image = Image.new('RGB', (200, 200), color='white')
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG')
        return img_buffer.getvalue()
    
    def _create_solid_color_image(self) -> bytes:
        """Create a solid color image (no faces)."""
        image = Image.new('RGB', (100, 100), color='blue')
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG')
        return img_buffer.getvalue()


class TestSystemResilience:
    """Test system resilience under various conditions."""
    
    def test_concurrent_user_operations(self):
        """Test system behavior under concurrent operations."""
        # This would require threading/multiprocessing for true concurrency testing
        # For now, we'll test sequential operations that simulate concurrent scenarios
        
        mongodb = MongoDBConnection(
            connection_string="mongodb://admin:password123@localhost:27018",
            database_name="face_attendance_resilience_test"
        )
        qdrant = QdrantConnection(
            host="localhost",
            port=6333,
            collection_name="face_vectors_resilience_test"
        )
        
        user_manager = UserManager(
            mongodb_connection=mongodb,
            qdrant_connection=qdrant
        )
        
        try:
            # Create multiple users rapidly
            created_users = []
            for i in range(5):
                user_data = UserCreateData(
                    name=f"Concurrent User {i}",
                    email=f"concurrent{i}@example.com"
                )
                image = self._create_test_image()
                user = user_manager.create_user(user_data, [image])
                created_users.append(user)
            
            # Verify all users were created
            assert len(created_users) == 5
            
            # Test rapid retrieval
            for user in created_users:
                retrieved = user_manager.get_user(user.id)
                assert retrieved is not None
                assert retrieved.id == user.id
            
            # Test rapid updates
            for i, user in enumerate(created_users):
                update_data = UserUpdateData(name=f"Updated User {i}")
                updated = user_manager.update_user(user.id, update_data)
                assert updated.name == f"Updated User {i}"
            
            # Cleanup
            for user in created_users:
                user_manager.delete_user(user.id)
        
        finally:
            # Cleanup databases
            try:
                mongodb.client.drop_database("face_attendance_resilience_test")
                mongodb.close()
                qdrant.client.delete_collection("face_vectors_resilience_test")
                qdrant.close()
            except Exception:
                pass
    
    def test_large_dataset_handling(self):
        """Test system behavior with larger datasets."""
        mongodb = MongoDBConnection(
            connection_string="mongodb://admin:password123@localhost:27018",
            database_name="face_attendance_large_test"
        )
        qdrant = QdrantConnection(
            host="localhost",
            port=6333,
            collection_name="face_vectors_large_test"
        )
        
        user_manager = UserManager(
            mongodb_connection=mongodb,
            qdrant_connection=qdrant
        )
        
        try:
            # Create a moderate number of users (not too many for CI/testing)
            created_users = []
            for i in range(10):
                user_data = UserCreateData(
                    name=f"Large Test User {i:03d}",
                    email=f"large{i:03d}@example.com",
                    department=f"Department {i % 3}"
                )
                
                # Create 2-3 images per user
                images = [self._create_test_image() for _ in range(2 + (i % 2))]
                user = user_manager.create_user(user_data, images)
                created_users.append(user)
            
            # Test bulk retrieval
            all_users = user_manager.get_all_users()
            assert len(all_users) >= 10
            
            # Test statistics with larger dataset
            stats = user_manager.get_user_statistics()
            assert stats["total_users"] >= 10
            assert stats["total_images"] >= 20  # At least 2 images per user
            
            # Test search performance (basic timing)
            import time
            start_time = time.time()
            
            # Perform multiple retrievals
            for user in created_users[:5]:
                retrieved = user_manager.get_user(user.id)
                assert retrieved is not None
            
            end_time = time.time()
            retrieval_time = end_time - start_time
            
            # Should complete reasonably quickly (adjust threshold as needed)
            assert retrieval_time < 5.0  # 5 seconds for 5 retrievals
            
            # Cleanup
            for user in created_users:
                user_manager.delete_user(user.id)
        
        finally:
            # Cleanup databases
            try:
                mongodb.client.drop_database("face_attendance_large_test")
                mongodb.close()
                qdrant.client.delete_collection("face_vectors_large_test")
                qdrant.close()
            except Exception:
                pass
    
    def _create_test_image(self) -> bytes:
        """Create a test image with some variation."""
        import random
        
        # Create images with different colors and patterns
        colors = ['red', 'green', 'blue', 'yellow', 'purple', 'orange']
        color = random.choice(colors)
        
        image = Image.new('RGB', (150, 150), color=color)
        
        # Add some random pattern
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        for _ in range(5):
            x1, y1 = random.randint(0, 100), random.randint(0, 100)
            x2, y2 = x1 + random.randint(20, 50), y1 + random.randint(20, 50)
            draw.rectangle([x1, y1, x2, y2], outline='black', width=1)
        
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG')
        return img_buffer.getvalue()


# Test configuration and utilities
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment before running integration tests."""
    # Ensure test databases are clean
    print("\nSetting up integration test environment...")
    
    # Wait a moment for databases to be ready
    time.sleep(2)
    
    yield
    
    print("\nCleaning up integration test environment...")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])