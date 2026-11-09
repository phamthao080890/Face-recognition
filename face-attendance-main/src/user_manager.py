"""
User Manager module for face attendance system.
Handles user creation, retrieval, updates, and deletion with image limit validation.
"""

import uuid
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import numpy as np

from .database import MongoDBConnection, QdrantConnection, UserInfo, ImageData
from .face_manager import FaceManager
from .image_processor import ImageProcessor
from .config import config


class UserCreateData:
    """Data structure for user creation requests"""
    
    def __init__(self, name: str, email: str, phone: str = None, department: str = None):
        self.name = name
        self.email = email
        self.phone = phone
        self.department = department


class UserUpdateData:
    """Data structure for user update requests"""
    
    def __init__(self, name: str = None, email: str = None, phone: str = None, department: str = None):
        self.name = name
        self.email = email
        self.phone = phone
        self.department = department


class ValidationError(Exception):
    """Custom exception for validation errors"""
    
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


class DuplicateUserError(Exception):
    """Exception for duplicate user errors"""
    pass


class UserNotFoundError(Exception):
    """Exception for user not found errors"""
    pass


class ImageLimitExceededError(Exception):
    """Exception for image limit exceeded errors"""
    pass


class UnsupportedFormatError(Exception):
    """Exception for unsupported image format errors"""
    pass


class UserManager:
    """Manages user operations including creation, retrieval, updates, and deletion."""
    
    def __init__(self, mongodb_connection: MongoDBConnection = None, 
                 qdrant_connection: QdrantConnection = None,
                 face_manager: FaceManager = None,
                 image_processor: ImageProcessor = None):
        """
        Initialize UserManager with database connections and processors.
        
        Args:
            mongodb_connection: MongoDB connection instance
            qdrant_connection: Qdrant connection instance
            face_manager: Face manager instance
            image_processor: Image processor instance
        """
        self.mongodb = mongodb_connection or MongoDBConnection()
        self.qdrant = qdrant_connection or QdrantConnection()
        self.face_manager = face_manager or FaceManager()
        self.image_processor = image_processor or ImageProcessor()
        
        # Maximum images per user from config
        self.max_images_per_user = config.MAX_IMAGES_PER_USER
    
    def create_user(self, user_data: UserCreateData, images: List[bytes]) -> UserInfo:
        """
        Create a new user with image limit validation (max 5).
        
        Args:
            user_data: User creation data
            images: List of image bytes (max 5)
            
        Returns:
            Created UserInfo object
            
        Raises:
            ValidationError: If validation fails
            DuplicateUserError: If user already exists
            UnsupportedFormatError: If image format is unsupported
            Exception: If creation fails
        """
        # Validate input data
        self._validate_user_data(user_data)
        self._validate_images(images)
        
        # Check if user already exists
        existing_user = self.mongodb.get_user_by_email(user_data.email)
        if existing_user:
            raise DuplicateUserError(f"User with email {user_data.email} already exists")
        
        # Process images and generate face vectors
        processed_images = []
        all_face_vectors = []  # List of (image_data, vectors) tuples
        
        for i, image_bytes in enumerate(images):
            try:
                # Process the image
                image_data, vectors = self._process_user_image(image_bytes)
                processed_images.append(image_data)
                all_face_vectors.append((image_data, vectors))
                
            except UnsupportedFormatError as e:
                raise UnsupportedFormatError(f"Image {i+1}: {str(e)}")
            except Exception as e:
                raise ValidationError(f"Failed to process image {i+1}: {str(e)}")
        
        # Create user info object
        user_info = UserInfo(
            id=None,  # Will be set by MongoDB
            name=user_data.name.strip(),
            email=user_data.email.strip().lower(),
            phone=user_data.phone.strip() if user_data.phone else None,
            department=user_data.department.strip() if user_data.department else None,
            images=processed_images,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            # Store user in MongoDB
            user_id = self.mongodb.create_user(user_info)
            user_info.id = user_id
            
            # Store face vectors in Qdrant
            for image_data, vectors in all_face_vectors:
                for vector in vectors:
                    vector_id = self.qdrant.store_face_vector(user_id, image_data.image_id, vector)
                    # Update the face_vector_id in image_data
                    if not hasattr(image_data, 'face_vector_ids'):
                        image_data.face_vector_ids = []
                    image_data.face_vector_ids.append(vector_id)
            
            # Update user with vector IDs
            self.mongodb.update_user(user_id, user_info)
            
            return user_info
            
        except Exception as e:
            # Cleanup on failure
            if user_info.id:
                try:
                    self.mongodb.delete_user(user_info.id)
                    self.qdrant.delete_user_vectors(user_info.id)
                except Exception:
                    pass  # Ignore cleanup errors
            raise Exception(f"Failed to create user: {str(e)}")
    
    def get_user(self, user_id: str) -> Optional[UserInfo]:
        """
        Retrieve a user by ID with all thumbnails.
        
        Args:
            user_id: The user's ID
            
        Returns:
            UserInfo object or None if not found
            
        Raises:
            ValidationError: If user_id is invalid
        """
        if not user_id or not user_id.strip():
            raise ValidationError("User ID is required and cannot be empty")
        
        try:
            return self.mongodb.get_user(user_id.strip())
        except Exception as e:
            # Log error but don't expose internal details
            return None
    
    def get_all_users(self) -> List[UserInfo]:
        """
        Retrieve all users with all thumbnails.
        
        Returns:
            List of UserInfo objects
        """
        return self.mongodb.get_all_users()
    
    def update_user(self, user_id: str, user_data: UserUpdateData) -> UserInfo:
        """
        Update user information while preserving face vectors.
        
        Args:
            user_id: The user's ID
            user_data: Updated user data
            
        Returns:
            Updated UserInfo object
            
        Raises:
            ValidationError: If validation fails
            UserNotFoundError: If user not found
            DuplicateUserError: If email conflicts with existing user
            Exception: If update fails
        """
        if not user_id or not user_id.strip():
            raise ValidationError("User ID is required and cannot be empty")
        
        # Get existing user
        existing_user = self.mongodb.get_user(user_id.strip())
        if not existing_user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        
        # Validate update data
        self._validate_user_update_data(user_data)
        
        # Check for email conflicts if email is being updated
        if user_data.email and user_data.email.strip().lower() != existing_user.email.lower():
            email_conflict = self.mongodb.get_user_by_email(user_data.email.strip().lower())
            if email_conflict and email_conflict.id != user_id:
                raise DuplicateUserError(f"Email {user_data.email} is already in use")
        
        # Update user information (preserve images and face vectors)
        updated_user = UserInfo(
            id=existing_user.id,
            name=user_data.name.strip() if user_data.name is not None else existing_user.name,
            email=user_data.email.strip().lower() if user_data.email is not None else existing_user.email,
            phone=user_data.phone.strip() if user_data.phone is not None else existing_user.phone,
            department=user_data.department.strip() if user_data.department is not None else existing_user.department,
            images=existing_user.images,  # Preserve existing images
            created_at=existing_user.created_at,
            updated_at=datetime.utcnow()
        )
        
        # Update in database
        try:
            success = self.mongodb.update_user(user_id, updated_user)
            if not success:
                raise Exception("Failed to update user in database")
            
            return updated_user
        except Exception as e:
            raise Exception(f"Failed to update user: {str(e)}")
    
    def delete_user(self, user_id: str) -> bool:
        """
        Complete user deletion (MongoDB + Qdrant).
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if deletion successful, False otherwise
            
        Raises:
            ValidationError: If user_id is invalid
            UserNotFoundError: If user not found
        """
        if not user_id or not user_id.strip():
            raise ValidationError("User ID is required and cannot be empty")
        
        # Check if user exists
        existing_user = self.mongodb.get_user(user_id.strip())
        if not existing_user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        
        try:
            # Delete from both databases
            mongodb_success = self.mongodb.delete_user(user_id)
            qdrant_success = self.qdrant.delete_user_vectors(user_id)
            
            # Return True only if both deletions succeeded
            return mongodb_success and qdrant_success
            
        except Exception:
            return False
    
    def validate_image_limit(self, user_id: str, new_images_count: int) -> bool:
        """
        Validate image limit for a user.
        
        Args:
            user_id: The user's ID
            new_images_count: Number of new images to add
            
        Returns:
            True if within limit, False otherwise
        """
        user = self.mongodb.get_user(user_id)
        if not user:
            return False
        
        current_count = len(user.images)
        total_count = current_count + new_images_count
        
        return total_count <= self.max_images_per_user
    
    def add_user_images(self, user_id: str, images: List[bytes]) -> UserInfo:
        """
        Add new images to an existing user (respecting the 5-image limit).
        
        Args:
            user_id: The user's ID
            images: List of new image bytes
            
        Returns:
            Updated UserInfo object
            
        Raises:
            ValidationError: If validation fails
            UserNotFoundError: If user not found
            ImageLimitExceededError: If image limit exceeded
            UnsupportedFormatError: If image format is unsupported
            Exception: If operation fails
        """
        if not user_id or not user_id.strip():
            raise ValidationError("User ID is required and cannot be empty")
        
        # Get existing user
        existing_user = self.mongodb.get_user(user_id.strip())
        if not existing_user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        
        # Validate image limit
        if not self.validate_image_limit(user_id, len(images)):
            current_count = len(existing_user.images)
            max_new = self.max_images_per_user - current_count
            raise ImageLimitExceededError(
                f"Cannot add {len(images)} images. User has {current_count} images, "
                f"maximum is {self.max_images_per_user}. Can add at most {max_new} more images."
            )
        
        # Validate images
        self._validate_images(images)
        
        # Process new images
        new_processed_images = []
        new_face_vectors = []
        
        for i, image_bytes in enumerate(images):
            try:
                image_data, vectors = self._process_user_image(image_bytes)
                new_processed_images.append(image_data)
                new_face_vectors.extend(vectors)
                
            except UnsupportedFormatError as e:
                raise UnsupportedFormatError(f"Image {i+1}: {str(e)}")
            except Exception as e:
                raise ValidationError(f"Failed to process image {i+1}: {str(e)}")
        
        try:
            # Store new face vectors in Qdrant
            for image_data, vectors in zip(new_processed_images, new_face_vectors):
                for vector in vectors:
                    vector_id = self.qdrant.store_face_vector(user_id, image_data.image_id, vector)
                    if not hasattr(image_data, 'face_vector_ids'):
                        image_data.face_vector_ids = []
                    image_data.face_vector_ids.append(vector_id)
            
            # Update user with new images
            updated_user = UserInfo(
                id=existing_user.id,
                name=existing_user.name,
                email=existing_user.email,
                phone=existing_user.phone,
                department=existing_user.department,
                images=existing_user.images + new_processed_images,
                created_at=existing_user.created_at,
                updated_at=datetime.utcnow()
            )
            
            # Update in MongoDB
            success = self.mongodb.update_user(user_id, updated_user)
            if not success:
                raise Exception("Failed to update user in database")
            
            return updated_user
            
        except Exception as e:
            # Cleanup on failure - remove any vectors that were stored
            for image_data in new_processed_images:
                if hasattr(image_data, 'face_vector_ids'):
                    for vector_id in image_data.face_vector_ids:
                        try:
                            self.qdrant.delete_vector(vector_id)
                        except Exception:
                            pass  # Ignore cleanup errors
            raise Exception(f"Failed to add images: {str(e)}")
    
    def _process_user_image(self, image_bytes: bytes) -> tuple[ImageData, List[np.ndarray]]:
        """
        Process a user image: resize, create thumbnail, detect faces, and encode.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Tuple of (ImageData, List of face vectors)
            
        Raises:
            UnsupportedFormatError: If image format is unsupported
            ValidationError: If image processing fails
        """
        try:
            # Generate unique image ID
            image_id = str(uuid.uuid4())
            
            # Validate image can be opened
            from PIL import Image
            import io
            
            try:
                with Image.open(io.BytesIO(image_bytes)) as img:
                    # Ensure image is in RGB mode
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGB')
                    
                    # Save as JPEG for consistency
                    output_buffer = io.BytesIO()
                    img.save(output_buffer, format='JPEG', quality=95)
                    processed_bytes = output_buffer.getvalue()
                    
            except Exception as e:
                raise UnsupportedFormatError(f"Cannot process image: {str(e)}")
            
            # Resize image to 600px width
            try:
                resized_image = self.image_processor.resize_image(processed_bytes, 600)
            except Exception as e:
                raise ValidationError(f"Failed to resize image: {str(e)}")
            
            # Create thumbnail (150x150)
            try:
                thumbnail = self.image_processor.create_thumbnail(processed_bytes, (150, 150))
            except Exception as e:
                raise ValidationError(f"Failed to create thumbnail: {str(e)}")
            
            # Encode to base64
            try:
                full_image_b64 = self.image_processor.encode_base64(resized_image)
                thumbnail_b64 = self.image_processor.encode_base64(thumbnail)
            except Exception as e:
                raise ValidationError(f"Failed to encode image: {str(e)}")
            
            # Detect and encode faces
            face_vectors = []
            try:
                image_array, detected_faces = self.face_manager.process_image_bytes(resized_image)
                
                if detected_faces:
                    for face_bbox in detected_faces:
                        try:
                            # Crop face
                            cropped_face = self.face_manager.crop_face(image_array, face_bbox)
                            
                            # Encode face
                            face_vector = self.face_manager.encode_face(cropped_face)
                            face_vectors.append(face_vector)
                        except Exception as e:
                            # Log face processing error but continue with other faces
                            continue
                else:
                    # No faces detected - this might be acceptable depending on requirements
                    # For now, we'll allow images without detected faces
                    pass
                    
            except Exception as e:
                # Face detection/encoding failed - still allow the image to be stored
                # but without face vectors
                pass
            
            # Create ImageData object
            image_data = ImageData(
                image_id=image_id,
                full_image=full_image_b64,
                thumbnail=thumbnail_b64,
                face_vector_id=""  # Will be updated after storing in Qdrant
            )
            
            return image_data, face_vectors
            
        except (UnsupportedFormatError, ValidationError):
            raise  # Re-raise known errors
        except Exception as e:
            raise ValidationError(f"Unexpected error processing image: {str(e)}")
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about users in the system.
        
        Returns:
            Dictionary with user statistics
        """
        try:
            all_users = self.get_all_users()
            
            total_users = len(all_users)
            total_images = sum(len(user.images) for user in all_users)
            
            # Calculate average images per user
            avg_images = total_images / total_users if total_users > 0 else 0
            
            # Find users with max images
            users_at_limit = sum(1 for user in all_users if len(user.images) >= self.max_images_per_user)
            
            return {
                "total_users": total_users,
                "total_images": total_images,
                "average_images_per_user": round(avg_images, 2),
                "users_at_image_limit": users_at_limit,
                "max_images_per_user": self.max_images_per_user
            }
        except Exception:
            return {
                "total_users": 0,
                "total_images": 0,
                "average_images_per_user": 0,
                "users_at_image_limit": 0,
                "max_images_per_user": self.max_images_per_user
            }
    
    def _validate_user_data(self, user_data: UserCreateData):
        """
        Validate user creation data.
        
        Args:
            user_data: User data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        import re
        errors = []
        
        # Name validation
        if not user_data.name or not user_data.name.strip():
            errors.append("Name is required and cannot be empty")
        elif len(user_data.name.strip()) < 2:
            errors.append("Name must be at least 2 characters long")
        elif len(user_data.name.strip()) > 100:
            errors.append("Name cannot exceed 100 characters")
        
        # Email validation
        if not user_data.email or not user_data.email.strip():
            errors.append("Email is required and cannot be empty")
        else:
            email = user_data.email.strip()
            if len(email) > 255:
                errors.append("Email cannot exceed 255 characters")
            elif "@" not in email or "." not in email:
                errors.append("Invalid email format")
            else:
                # More comprehensive email validation
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, email):
                    errors.append("Invalid email format")
        
        # Phone validation (optional)
        if user_data.phone is not None and user_data.phone.strip():
            phone = user_data.phone.strip()
            if len(phone) > 20:
                errors.append("Phone number cannot exceed 20 characters")
            # Basic phone validation - allow digits, spaces, hyphens, parentheses, plus
            import re
            phone_pattern = r'^[\d\s\-\(\)\+]+$'
            if not re.match(phone_pattern, phone):
                errors.append("Phone number contains invalid characters")
        
        # Department validation (optional)
        if user_data.department is not None and user_data.department.strip():
            if len(user_data.department.strip()) > 100:
                errors.append("Department cannot exceed 100 characters")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    def _validate_user_update_data(self, user_data: UserUpdateData):
        """
        Validate user update data.
        
        Args:
            user_data: User update data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        import re
        errors = []
        
        # Name validation (if provided)
        if user_data.name is not None:
            if not user_data.name.strip():
                errors.append("Name cannot be empty")
            elif len(user_data.name.strip()) < 2:
                errors.append("Name must be at least 2 characters long")
            elif len(user_data.name.strip()) > 100:
                errors.append("Name cannot exceed 100 characters")
        
        # Email validation (if provided)
        if user_data.email is not None:
            if not user_data.email.strip():
                errors.append("Email cannot be empty")
            else:
                email = user_data.email.strip()
                if len(email) > 255:
                    errors.append("Email cannot exceed 255 characters")
                elif "@" not in email or "." not in email:
                    errors.append("Invalid email format")
                else:
                    import re
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not re.match(email_pattern, email):
                        errors.append("Invalid email format")
        
        # Phone validation (if provided)
        if user_data.phone is not None and user_data.phone.strip():
            phone = user_data.phone.strip()
            if len(phone) > 20:
                errors.append("Phone number cannot exceed 20 characters")
            import re
            phone_pattern = r'^[\d\s\-\(\)\+]+$'
            if not re.match(phone_pattern, phone):
                errors.append("Phone number contains invalid characters")
        
        # Department validation (if provided)
        if user_data.department is not None and user_data.department.strip():
            if len(user_data.department.strip()) > 100:
                errors.append("Department cannot exceed 100 characters")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    def _validate_images(self, images: List[bytes]):
        """
        Validate image data.
        
        Args:
            images: List of image bytes to validate
            
        Raises:
            ValidationError: If validation fails
            UnsupportedFormatError: If image format is unsupported
        """
        if not images:
            raise ValidationError("At least one image is required")
        
        if len(images) > self.max_images_per_user:
            raise ValidationError(f"Cannot add more than {self.max_images_per_user} images per user")
        
        supported_formats = {'JPEG', 'JPG', 'PNG', 'BMP', 'TIFF', 'WEBP'}
        
        for i, image_bytes in enumerate(images):
            if not image_bytes:
                raise ValidationError(f"Image {i+1} is empty")
            
            # Check image size (max 10MB per image)
            if len(image_bytes) > 10 * 1024 * 1024:
                raise ValidationError(f"Image {i+1} exceeds maximum size of 10MB")
            
            # Check minimum size (at least 1KB)
            if len(image_bytes) < 1024:
                raise ValidationError(f"Image {i+1} is too small (minimum 1KB)")
            
            # Validate image format and basic properties
            try:
                from PIL import Image
                import io
                
                with Image.open(io.BytesIO(image_bytes)) as img:
                    # Check format
                    if img.format not in supported_formats:
                        raise UnsupportedFormatError(
                            f"Image {i+1} format '{img.format}' is not supported. "
                            f"Supported formats: {', '.join(supported_formats)}"
                        )
                    
                    # Check dimensions
                    width, height = img.size
                    if width < 100 or height < 100:
                        raise ValidationError(f"Image {i+1} is too small (minimum 100x100 pixels)")
                    
                    if width > 5000 or height > 5000:
                        raise ValidationError(f"Image {i+1} is too large (maximum 5000x5000 pixels)")
                    
                    # Verify image can be processed
                    img.verify()
                    
            except UnsupportedFormatError:
                raise  # Re-raise format errors
            except Exception as e:
                raise UnsupportedFormatError(f"Image {i+1} is corrupted or not a valid image: {str(e)}")