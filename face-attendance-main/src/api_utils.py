"""
Utility functions for the Face Attendance System API.
Contains validation, sanitization, and error handling utilities.
"""

import io
import base64
import logging
from typing import Dict, Any, Optional
from PIL import Image
from fastapi import HTTPException, UploadFile, status
from .user_manager import (
    ValidationError, 
    DuplicateUserError, 
    UserNotFoundError, 
    ImageLimitExceededError, 
    UnsupportedFormatError
)
from .database import DatabaseConnectionError, DatabaseOperationError
from .config import config

logger = logging.getLogger(__name__)


def sanitize_string_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent injection attacks.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Raises:
        HTTPException: If input is invalid
    """
    if not value:
        return value
    
    # Remove null bytes and control characters
    sanitized = ''.join(char for char in value if ord(char) >= 32 or char in ['\n', '\r', '\t'])
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Check length
    if len(sanitized) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "input_too_long",
                "message": f"Input exceeds maximum length of {max_length} characters"
            }
        )
    
    return sanitized


def validate_user_id(user_id: str) -> str:
    """
    Validate user ID format.
    
    Args:
        user_id: User ID to validate
        
    Returns:
        Validated user ID
        
    Raises:
        HTTPException: If user ID is invalid
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "missing_user_id",
                "message": "User ID is required"
            }
        )
    
    # Basic MongoDB ObjectId validation (24 hex characters)
    if len(user_id) != 24 or not all(c in '0123456789abcdefABCDEF' for c in user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_user_id",
                "message": "User ID must be a valid 24-character hexadecimal string"
            }
        )
    
    return user_id.lower()


def validate_email_format(email: str) -> str:
    """
    Additional email validation beyond Pydantic.
    
    Args:
        email: Email to validate
        
    Returns:
        Validated email
        
    Raises:
        HTTPException: If email is invalid
    """
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "missing_email",
                "message": "Email is required"
            }
        )
    
    # Basic length check
    if len(email) > 254:  # RFC 5321 limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "email_too_long",
                "message": "Email address is too long (maximum 254 characters)"
            }
        )
    
    # Check for dangerous characters
    dangerous_chars = ['<', '>', '"', '\'', '&', '\n', '\r', '\t']
    if any(char in email for char in dangerous_chars):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_email_characters",
                "message": "Email contains invalid characters"
            }
        )
    
    return email.lower().strip()


def handle_user_manager_error(e: Exception) -> HTTPException:
    """
    Convert user manager exceptions to appropriate HTTP exceptions.
    
    Args:
        e: Exception from user manager
        
    Returns:
        HTTPException with appropriate status code and message
    """
    if isinstance(e, ValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": e.message,
                "field": getattr(e, 'field', None)
            }
        )
    elif isinstance(e, DuplicateUserError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate_user",
                "message": str(e)
            }
        )
    elif isinstance(e, UserNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "user_not_found",
                "message": str(e)
            }
        )
    elif isinstance(e, ImageLimitExceededError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "image_limit_exceeded",
                "message": str(e)
            }
        )
    elif isinstance(e, UnsupportedFormatError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "unsupported_format",
                "message": str(e)
            }
        )
    elif isinstance(e, DatabaseConnectionError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "database_unavailable",
                "message": "Database service is temporarily unavailable"
            }
        )
    elif isinstance(e, DatabaseOperationError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_operation_failed",
                "message": "Database operation failed"
            }
        )
    else:
        # Log unexpected errors for debugging
        logger.error(f"Unexpected user manager error: {str(e)}", exc_info=True)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An internal error occurred"
            }
        )


def validate_base64_image(base64_string: str) -> bytes:
    """
    Validate and decode base64 encoded image with comprehensive security checks.
    
    Args:
        base64_string: Base64 encoded image string (with or without data URL prefix)
        
    Returns:
        Image bytes
        
    Raises:
        HTTPException: If image is invalid
    """
    if not base64_string:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "no_image_data",
                "message": "No image data provided"
            }
        )
    
    # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
    if base64_string.startswith('data:'):
        try:
            # Extract the base64 part after the comma
            base64_data = base64_string.split(',', 1)[1]
        except IndexError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_data_url",
                    "message": "Invalid data URL format"
                }
            )
    else:
        base64_data = base64_string
    
    # Decode base64 string
    try:
        image_bytes = base64.b64decode(base64_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_base64",
                "message": f"Invalid base64 encoding: {str(e)}"
            }
        )
    
    # Check if decoded data is empty
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "empty_image",
                "message": "Decoded image data is empty"
            }
        )
    
    # Check file size limits
    if len(image_bytes) > config.MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "image_too_large",
                "message": f"Image size exceeds {config.MAX_IMAGE_SIZE_MB}MB limit",
                "details": {"max_size_mb": config.MAX_IMAGE_SIZE_MB}
            }
        )
    
    if len(image_bytes) < config.MIN_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "image_too_small",
                "message": f"Image size is too small (minimum {config.MIN_IMAGE_SIZE_KB}KB)",
                "details": {"min_size_kb": config.MIN_IMAGE_SIZE_KB}
            }
        )
    
    # Validate it's actually a valid image by attempting to open it
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Check image format
            img_format = img.format.lower() if img.format else ''
            allowed_formats = ["jpeg", "jpg", "png", "bmp", "tiff", "tif", "webp"]
            
            if img_format not in allowed_formats:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "unsupported_format",
                        "message": f"Image format '{img_format}' not supported. Allowed: {', '.join(allowed_formats)}"
                    }
                )
            
            # Check image dimensions (reasonable limits)
            width, height = img.size
            max_dimension = 4096  # 4K max
            min_dimension = 32    # Minimum 32px
            
            if width > max_dimension or height > max_dimension:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "image_dimensions_too_large",
                        "message": f"Image dimensions too large: {width}x{height}. Maximum: {max_dimension}x{max_dimension}",
                        "details": {"max_dimension": max_dimension}
                    }
                )
            
            if width < min_dimension or height < min_dimension:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "image_dimensions_too_small",
                        "message": f"Image dimensions too small: {width}x{height}. Minimum: {min_dimension}x{min_dimension}",
                        "details": {"min_dimension": min_dimension}
                    }
                )
            
            # Verify image is not corrupted by loading pixel data
            img.verify()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_image",
                "message": f"Invalid image data or corrupted image: {str(e)}"
            }
        )
    
    return image_bytes


def validate_image_file(file: UploadFile) -> bytes:
    """
    Validate and read uploaded image file with comprehensive security checks.
    
    Args:
        file: Uploaded file
        
    Returns:
        Image bytes
        
    Raises:
        HTTPException: If file is invalid
    """
    # Check if file is provided
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "no_file",
                "message": "No file provided"
            }
        )
    
    # Check filename for security (basic sanitization)
    if any(char in file.filename for char in ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_filename",
                "message": "Filename contains invalid characters"
            }
        )
    
    # Check file extension
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    if f'.{file_extension}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_extension",
                "message": f"File extension '.{file_extension}' not supported. Allowed: {', '.join(allowed_extensions)}"
            }
        )
    
    # Check file size (max configured limit)
    if file.size and file.size > config.MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "file_too_large",
                "message": f"File size exceeds {config.MAX_IMAGE_SIZE_MB}MB limit",
                "details": {"max_size_mb": config.MAX_IMAGE_SIZE_MB}
            }
        )
    
    # Check minimum file size
    if file.size and file.size < config.MIN_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "file_too_small",
                "message": f"File size is too small (minimum {config.MIN_IMAGE_SIZE_KB}KB)",
                "details": {"min_size_kb": config.MIN_IMAGE_SIZE_KB}
            }
        )
    
    # Check content type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/bmp", "image/tiff", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_content_type",
                "message": f"Content type {file.content_type} not supported",
                "details": {"allowed_types": allowed_types}
            }
        )
    
    # Read file content with error handling
    try:
        content = file.file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "empty_file",
                    "message": "Uploaded file is empty"
                }
            )
        
        # Validate actual file size matches header
        if file.size and len(content) != file.size:
            logger.warning(f"File size mismatch: header={file.size}, actual={len(content)}")
        
        # Validate it's actually a valid image by attempting to open it
        try:
            with Image.open(io.BytesIO(content)) as img:
                # Verify image format matches content type
                img_format = img.format.lower() if img.format else ''
                expected_formats = {
                    "image/jpeg": ["jpeg", "jpg"],
                    "image/jpg": ["jpeg", "jpg"],
                    "image/png": ["png"],
                    "image/bmp": ["bmp"],
                    "image/tiff": ["tiff", "tif"],
                    "image/webp": ["webp"]
                }
                
                if file.content_type in expected_formats:
                    if img_format not in expected_formats[file.content_type]:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={
                                "error": "format_mismatch",
                                "message": f"Image format {img_format} doesn't match content type {file.content_type}"
                            }
                        )
                
                # Check image dimensions (reasonable limits)
                width, height = img.size
                max_dimension = 4096  # 4K max
                min_dimension = 32    # Minimum 32px
                
                if width > max_dimension or height > max_dimension:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error": "image_too_large",
                            "message": f"Image dimensions too large: {width}x{height}. Maximum: {max_dimension}x{max_dimension}",
                            "details": {"max_dimension": max_dimension}
                        }
                    )
                
                if width < min_dimension or height < min_dimension:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error": "image_too_small",
                            "message": f"Image dimensions too small: {width}x{height}. Minimum: {min_dimension}x{min_dimension}",
                            "details": {"min_dimension": min_dimension}
                        }
                    )
                
                # Verify image is not corrupted by loading pixel data
                img.verify()
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_image",
                    "message": f"File is not a valid image or is corrupted: {str(e)}"
                }
            )
        
        return content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading uploaded file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "file_read_error",
                "message": "Failed to read uploaded file"
            }
        )


def user_info_to_response(user_info):
    """
    Convert UserInfo object to API response format.
    
    Args:
        user_info: UserInfo object from database
        
    Returns:
        UserInfoResponse object
    """
    # Import here to avoid circular imports
    from pydantic import BaseModel
    from typing import List, Dict, Any
    
    class UserInfoResponse(BaseModel):
        """Response model for user information"""
        id: str
        name: str
        email: str
        phone: Optional[str] = None
        department: Optional[str] = None
        images: List[Dict[str, str]]  # List of image data with thumbnails
        created_at: str
        updated_at: str
    
    images_data = []
    for img in user_info.images:
        images_data.append({
            "image_id": img.image_id,
            "thumbnail": img.thumbnail,
            # Don't include full_image in API responses to reduce payload size
        })
    
    return UserInfoResponse(
        id=user_info.id,
        name=user_info.name,
        email=user_info.email,
        phone=user_info.phone,
        department=user_info.department,
        images=images_data,
        created_at=user_info.created_at.isoformat() if user_info.created_at else "",
        updated_at=user_info.updated_at.isoformat() if user_info.updated_at else ""
    )