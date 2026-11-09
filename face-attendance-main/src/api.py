"""
FastAPI server for Face Attendance System.
Provides REST API endpoints for face recognition and user management.
"""

import io
import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, EmailStr, Field, ValidationError as PydanticValidationError
import numpy as np
from PIL import Image

from .database import MongoDBConnection, QdrantConnection, DatabaseConnectionError, DatabaseOperationError
from .face_manager import FaceManager
from .user_manager import UserManager, UserCreateData, UserUpdateData, ValidationError, DuplicateUserError, UserNotFoundError, ImageLimitExceededError, UnsupportedFormatError
from .image_processor import ImageProcessor
from .config import config
from .api_utils import (
    sanitize_string_input,
    validate_user_id,
    validate_email_format,
    handle_user_manager_error,
    validate_image_file,
    validate_base64_image,
    user_info_to_response
)

# Configure logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)


# Pydantic models for request/response
class UserSearchResult(BaseModel):
    """Response model for face search results"""
    match_found: bool
    user_info: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    message: str


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


class UserCreateRequest(BaseModel):
    """Request model for user creation"""
    name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    phone: Optional[str] = Field(None, max_length=20, description="User's phone number")
    department: Optional[str] = Field(None, max_length=100, description="User's department")
    images: List[str] = Field(..., min_items=1, max_items=5, description="Base64 encoded images (1-5 images required)")


class UserImageAddRequest(BaseModel):
    """Request model for adding images to existing user"""
    images: List[str] = Field(..., min_items=1, description="Base64 encoded images to add")


class FaceSearchRequest(BaseModel):
    """Request model for face search"""
    image: str = Field(..., description="Base64 encoded image containing face to search for")


class UserUpdateRequest(BaseModel):
    """Request model for user updates"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="User's full name")
    email: Optional[EmailStr] = Field(None, description="User's email address")
    phone: Optional[str] = Field(None, max_length=20, description="User's phone number")
    department: Optional[str] = Field(None, max_length=100, description="User's department")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    version: str = "1.0.0"
    services: Dict[str, str]


# Initialize FastAPI app
app = FastAPI(
    title="Face Attendance System API",
    description="REST API for face recognition and user management in attendance system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    
    # Extract field-specific errors
    error_details = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": error_details
        }
    )


@app.exception_handler(DatabaseConnectionError)
async def database_connection_exception_handler(request: Request, exc: DatabaseConnectionError):
    """Handle database connection errors"""
    logger.error(f"Database connection error on {request.url}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "database_unavailable",
            "message": "Database service is temporarily unavailable. Please try again later.",
            "details": {"retry_after": "30 seconds"}
        }
    )


@app.exception_handler(DatabaseOperationError)
async def database_operation_exception_handler(request: Request, exc: DatabaseOperationError):
    """Handle database operation errors"""
    logger.error(f"Database operation error on {request.url}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "database_operation_failed",
            "message": "Database operation failed. Please try again.",
            "details": {"operation": "database_query"}
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error on {request.url}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "details": {"request_id": str(uuid.uuid4())}
        }
    )


# Request size middleware
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    """Middleware to limit request body size"""
    # Check content length header
    content_length = request.headers.get("content-length")
    if content_length:
        content_length = int(content_length)
        # Allow for base64 encoded images (roughly 33% larger than binary) + JSON overhead
        max_size = config.MAX_IMAGE_SIZE_BYTES * 5 * 2  # 5 images * 2x for base64 overhead
        
        if content_length > max_size:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "request_too_large",
                    "message": f"Request body too large. Maximum size: {max_size // (1024*1024)}MB",
                    "details": {"max_size_mb": max_size // (1024*1024)}
                }
            )
    
    response = await call_next(request)
    return response


# Global instances (will be initialized on startup)
mongodb_connection: Optional[MongoDBConnection] = None
qdrant_connection: Optional[QdrantConnection] = None
face_manager: Optional[FaceManager] = None
user_manager: Optional[UserManager] = None
image_processor: Optional[ImageProcessor] = None


@app.on_event("startup")
async def startup_event():
    """Initialize database connections and services on startup with comprehensive error handling"""
    global mongodb_connection, qdrant_connection, face_manager, user_manager, image_processor
    
    try:
        logger.info("Starting Face Attendance System API...")
        
        # Initialize database connections with error handling
        try:
            logger.info("Initializing MongoDB connection...")
            mongodb_connection = MongoDBConnection()
            logger.info("MongoDB connection established successfully")
        except DatabaseConnectionError as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {str(e)}")
            raise DatabaseConnectionError(f"MongoDB initialization failed: {str(e)}")
        
        try:
            logger.info("Initializing Qdrant connection...")
            qdrant_connection = QdrantConnection()
            logger.info("Qdrant connection established successfully")
        except DatabaseConnectionError as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to Qdrant: {str(e)}")
            raise DatabaseConnectionError(f"Qdrant initialization failed: {str(e)}")
        
        # Initialize processors with error handling
        try:
            logger.info("Initializing face processing components...")
            face_manager = FaceManager()
            image_processor = ImageProcessor()
            logger.info("Face processing components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize face processing components: {str(e)}")
            raise
        
        # Initialize user manager with error handling
        try:
            logger.info("Initializing user management service...")
            user_manager = UserManager(
                mongodb_connection=mongodb_connection,
                qdrant_connection=qdrant_connection,
                face_manager=face_manager,
                image_processor=image_processor
            )
            logger.info("User management service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize user management service: {str(e)}")
            raise
        
        logger.info("Face Attendance System API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Face Attendance System API: {str(e)}")
        # Clean up any partially initialized connections
        if mongodb_connection:
            try:
                mongodb_connection.close()
            except Exception:
                pass
        if qdrant_connection:
            try:
                qdrant_connection.close()
            except Exception:
                pass
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown with error handling"""
    global mongodb_connection, qdrant_connection
    
    try:
        logger.info("Shutting down Face Attendance System API...")
        
        if mongodb_connection:
            try:
                mongodb_connection.close()
                logger.info("MongoDB connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {str(e)}")
        
        if qdrant_connection:
            try:
                qdrant_connection.close()
                logger.info("Qdrant connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing Qdrant connection: {str(e)}")
        
        logger.info("Face Attendance System API shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify system status.
    
    Returns:
        HealthResponse: System health information
    """
    try:
        # Check database connections
        mongodb_status = "connected" if mongodb_connection else "disconnected"
        qdrant_status = "connected" if qdrant_connection else "disconnected"
        
        # Test database connectivity
        if mongodb_connection:
            try:
                # Simple ping to test MongoDB connection
                mongodb_connection.client.admin.command('ping')
                mongodb_status = "healthy"
            except Exception:
                mongodb_status = "unhealthy"
        
        if qdrant_connection:
            try:
                # Test Qdrant connection
                qdrant_connection.get_collection_info()
                qdrant_status = "healthy"
            except Exception:
                qdrant_status = "unhealthy"
        
        overall_status = "healthy" if mongodb_status == "healthy" and qdrant_status == "healthy" else "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            services={
                "mongodb": mongodb_status,
                "qdrant": qdrant_status,
                "face_detection": "available" if face_manager else "unavailable",
                "image_processing": "available" if image_processor else "unavailable"
            }
        )
        
    except Exception as e:
        return HealthResponse(
            status="error",
            timestamp=datetime.utcnow().isoformat(),
            services={
                "error": str(e)
            }
        )


@app.get("/users", response_model=List[UserInfoResponse])
async def get_users():
    """
    Retrieve all users with their thumbnail images.
    
    Returns:
        List[UserInfoResponse]: List of all users with their information and thumbnails
        
    Raises:
        HTTPException: If retrieval fails
    """
    if not user_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "service_unavailable",
                "message": "User management service is not available"
            }
        )
    
    try:
        users = user_manager.get_all_users()
        return [user_info_to_response(user) for user in users]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "retrieval_failed",
                "message": "Failed to retrieve users"
            }
        )


@app.post("/users", response_model=UserInfoResponse, status_code=status.HTTP_201_CREATED)
async def create_user(request: UserCreateRequest):
    """
    Create a new user with base64 encoded images.
    
    Args:
        request: User creation request with base64 encoded images
        
    Returns:
        UserInfoResponse: Created user information
        
    Raises:
        HTTPException: If creation fails or validation errors occur
    """
    if not user_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "service_unavailable",
                "message": "User management service is not available"
            }
        )
    
    try:
        # Sanitize and validate input data
        sanitized_name = request.name
        sanitized_email = validate_email_format(request.email)
        sanitized_phone = sanitize_string_input(request.phone, 20) if request.phone else None
        sanitized_department = sanitize_string_input(request.department, 100) if request.department else None
        
        # Validate and decode base64 images
        image_bytes_list = []
        for i, base64_image in enumerate(request.images):
            try:
                image_bytes = validate_base64_image(base64_image)
                image_bytes_list.append(image_bytes)
            except HTTPException as e:
                # Add image index to error message
                error_detail = e.detail
                if isinstance(error_detail, dict):
                    error_detail["message"] = f"Image {i+1}: {error_detail.get('message', 'Invalid image')}"
                raise HTTPException(status_code=e.status_code, detail=error_detail)
        
        # Create user data object with sanitized inputs
        user_data = UserCreateData(
            name=sanitized_name,
            email=sanitized_email,
            phone=sanitized_phone,
            department=sanitized_department
        )
        
        # Create user
        created_user = user_manager.create_user(user_data, image_bytes_list)
        return user_info_to_response(created_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_user_manager_error(e)


@app.put("/users/{user_id}", response_model=UserInfoResponse)
async def update_user(user_id: str, request: UserUpdateRequest):
    """
    Update an existing user's information.
    
    Args:
        user_id: The user's ID
        request: User update request with optional fields
        
    Returns:
        UserInfoResponse: Updated user information
        
    Raises:
        HTTPException: If update fails or user not found
    """
    if not user_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "service_unavailable",
                "message": "User management service is not available"
            }
        )
    
    # Check if at least one field is provided for update
    if all(field is None for field in [request.name, request.email, request.phone, request.department]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "no_update_data",
                "message": "At least one field must be provided for update"
            }
        )
    
    try:
        # Validate user ID format
        validated_user_id = validate_user_id(user_id)
        
        # Sanitize and validate input data
        sanitized_name = sanitize_string_input(request.name, 100) if request.name else None
        sanitized_email = validate_email_format(request.email) if request.email else None
        sanitized_phone = sanitize_string_input(request.phone, 20) if request.phone else None
        sanitized_department = sanitize_string_input(request.department, 100) if request.department else None
        
        # Create update data object with sanitized inputs
        update_data = UserUpdateData(
            name=sanitized_name,
            email=sanitized_email,
            phone=sanitized_phone,
            department=sanitized_department
        )
        
        # Update user
        updated_user = user_manager.update_user(validated_user_id, update_data)
        return user_info_to_response(updated_user)
        
    except Exception as e:
        raise handle_user_manager_error(e)


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    """
    Delete a user from the system.
    
    Args:
        user_id: The user's ID
        
    Returns:
        No content (204 status code)
        
    Raises:
        HTTPException: If deletion fails or user not found
    """
    if not user_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "service_unavailable",
                "message": "User management service is not available"
            }
        )
    
    try:
        # Validate user ID format
        validated_user_id = validate_user_id(user_id)
        
        success = user_manager.delete_user(validated_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "deletion_failed",
                    "message": "Failed to delete user"
                }
            )
        
        # Return 204 No Content for successful deletion
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_user_manager_error(e)


@app.post("/users/{user_id}/images", response_model=UserInfoResponse)
async def add_user_images(user_id: str, request: UserImageAddRequest):
    """
    Add additional base64 encoded images to an existing user.
    
    Args:
        user_id: The user's ID
        request: Request containing base64 encoded images
        
    Returns:
        UserInfoResponse: Updated user information
        
    Raises:
        HTTPException: If operation fails or limits exceeded
    """
    if not user_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "service_unavailable",
                "message": "User management service is not available"
            }
        )
    
    try:
        # Validate user ID format
        validated_user_id = validate_user_id(user_id)
        
        # Validate and decode base64 images
        image_bytes_list = []
        for i, base64_image in enumerate(request.images):
            try:
                image_bytes = validate_base64_image(base64_image)
                image_bytes_list.append(image_bytes)
            except HTTPException as e:
                # Add image index to error message
                error_detail = e.detail
                if isinstance(error_detail, dict):
                    error_detail["message"] = f"Image {i+1}: {error_detail.get('message', 'Invalid image')}"
                raise HTTPException(status_code=e.status_code, detail=error_detail)
        
        # Add images to user
        updated_user = user_manager.add_user_images(validated_user_id, image_bytes_list)
        return user_info_to_response(updated_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_user_manager_error(e)


@app.post("/search", response_model=UserSearchResult)
async def search_face(request: FaceSearchRequest):
    """
    Search for a matching user by face recognition using base64 encoded image.
    
    Args:
        request: Request containing base64 encoded image with face to search for
        
    Returns:
        UserSearchResult: Search results with user information if match found
        
    Raises:
        HTTPException: If image processing fails or other errors occur
    """
    if not user_manager or not face_manager or not qdrant_connection:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "service_unavailable",
                "message": "Face recognition services are not available"
            }
        )
    
    try:
        # Validate and decode base64 image
        image_bytes = validate_base64_image(request.image)
        
        # Process image and detect faces
        try:
            image_array, detected_faces = face_manager.process_image_bytes(image_bytes)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "image_processing_failed",
                    "message": f"Failed to process image: {str(e)}"
                }
            )
        
        # Check if any faces were detected
        if not detected_faces:
            return UserSearchResult(
                match_found=False,
                user_info=None,
                confidence=None,
                message="No face detected in the provided image"
            )
        
        # Process the first detected face (could be extended to handle multiple faces)
        best_match_user_id = None
        best_confidence = 0.0
        
        for face_bbox in detected_faces:
            try:
                # Crop and encode the face
                cropped_face = face_manager.crop_face(image_array, face_bbox)
                face_vector = face_manager.encode_face(cropped_face)
                
                # Search for similar faces in Qdrant
                similar_faces = qdrant_connection.search_similar_faces(
                    query_vector=face_vector,
                    limit=10,
                    score_threshold=0.8
                )
                
                # Find the best match
                for user_id, confidence in similar_faces:
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match_user_id = user_id
                        
            except Exception as e:
                # Log face processing error but continue with other faces
                continue
        
        # If we found a match above threshold
        if best_match_user_id and best_confidence >= 0.8:
            try:
                # Get user information
                user_info = user_manager.get_user(best_match_user_id)
                if user_info:
                    user_response = user_info_to_response(user_info)
                    return UserSearchResult(
                        match_found=True,
                        user_info=user_response.dict(),
                        confidence=round(best_confidence, 3),
                        message=f"Match found with {round(best_confidence * 100, 1)}% confidence"
                    )
                else:
                    # User was deleted but vectors still exist
                    return UserSearchResult(
                        match_found=False,
                        user_info=None,
                        confidence=None,
                        message="Face matched but user information not found"
                    )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "user_retrieval_failed",
                        "message": "Failed to retrieve user information"
                    }
                )
        else:
            return UserSearchResult(
                match_found=False,
                user_info=None,
                confidence=round(best_confidence, 3) if best_confidence > 0 else None,
                message=f"No matching user found (best confidence: {round(best_confidence * 100, 1)}%)" if best_confidence > 0 else "No matching user found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "search_failed",
                "message": "Face search operation failed"
            }
        )


if __name__ == "__main__":
    import argparse
    import uvicorn
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Face Attendance System API Server")
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0", 
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to bind the server to (default: 8000)"
    )
    # Parse arguments
    args = parser.parse_args()
    
    # Run the server with parsed arguments
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
    )