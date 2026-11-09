"""
Configuration module for Face Attendance System.
Loads configuration from environment variables with defaults.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for Face Attendance System."""
    
    # MongoDB Configuration
    MONGODB_HOST: str = os.getenv('MONGODB_HOST', 'localhost')
    MONGODB_PORT: int = int(os.getenv('MONGODB_PORT', '27018'))
    MONGODB_USERNAME: str = os.getenv('MONGODB_USERNAME', 'admin')
    MONGODB_PASSWORD: str = os.getenv('MONGODB_PASSWORD', 'password123')
    MONGODB_DATABASE: str = os.getenv('MONGODB_DATABASE', 'face_attendance')
    
    @property
    def MONGODB_CONNECTION_STRING(self) -> str:
        """Generate MongoDB connection string from components."""
        if self.MONGODB_USERNAME and self.MONGODB_PASSWORD:
            return f"mongodb://{self.MONGODB_USERNAME}:{self.MONGODB_PASSWORD}@{self.MONGODB_HOST}:{self.MONGODB_PORT}"
        else:
            return f"mongodb://{self.MONGODB_HOST}:{self.MONGODB_PORT}"
    
    # Qdrant Configuration
    QDRANT_HOST: str = os.getenv('QDRANT_HOST', 'localhost')
    QDRANT_PORT: int = int(os.getenv('QDRANT_PORT', '6333'))
    QDRANT_COLLECTION_NAME: str = os.getenv('QDRANT_COLLECTION_NAME', 'face_vectors')
    
    @property
    def QDRANT_URL(self) -> str:
        """Generate Qdrant URL from components."""
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"
    
    # Face Recognition Configuration
    FACE_SIMILARITY_THRESHOLD: float = float(os.getenv('FACE_SIMILARITY_THRESHOLD', '0.8'))
    MAX_IMAGES_PER_USER: int = int(os.getenv('MAX_IMAGES_PER_USER', '5'))
    
    # Image Processing Configuration
    IMAGE_RESIZE_WIDTH: int = int(os.getenv('IMAGE_RESIZE_WIDTH', '600'))
    THUMBNAIL_SIZE: int = int(os.getenv('THUMBNAIL_SIZE', '150'))
    MAX_IMAGE_SIZE_MB: int = int(os.getenv('MAX_IMAGE_SIZE_MB', '10'))
    MIN_IMAGE_SIZE_KB: int = int(os.getenv('MIN_IMAGE_SIZE_KB', '1'))
    
    @property
    def MAX_IMAGE_SIZE_BYTES(self) -> int:
        """Convert max image size from MB to bytes."""
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024
    
    @property
    def MIN_IMAGE_SIZE_BYTES(self) -> int:
        """Convert min image size from KB to bytes."""
        return self.MIN_IMAGE_SIZE_KB * 1024
    
    # API Configuration
    API_HOST: str = os.getenv('API_HOST', '0.0.0.0')
    API_PORT: int = int(os.getenv('API_PORT', '8000'))
    API_CORS_ORIGINS: str = os.getenv('API_CORS_ORIGINS', '*')
    
    # Model Configuration
    YOLO_MODEL_PATH: str = os.getenv('YOLO_MODEL_PATH', 'yolov8n.pt')
    YOLO_CONFIDENCE_THRESHOLD: float = float(os.getenv('YOLO_CONFIDENCE_THRESHOLD', '0.5'))
    FACENET_MODEL: str = os.getenv('FACENET_MODEL', 'vggface2')
    
    # Database Connection Settings
    DB_MAX_RETRIES: int = int(os.getenv('DB_MAX_RETRIES', '3'))
    DB_RETRY_DELAY: int = int(os.getenv('DB_RETRY_DELAY', '2'))
    DB_CONNECTION_TIMEOUT: int = int(os.getenv('DB_CONNECTION_TIMEOUT', '5000'))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def get_test_mongodb_connection_string(cls, database_name: str) -> str:
        """Generate test MongoDB connection string with custom database name."""
        if cls.MONGODB_USERNAME and cls.MONGODB_PASSWORD:
            return f"mongodb://{cls.MONGODB_USERNAME}:{cls.MONGODB_PASSWORD}@{cls.MONGODB_HOST}:{cls.MONGODB_PORT}/{database_name}"
        else:
            return f"mongodb://{cls.MONGODB_HOST}:{cls.MONGODB_PORT}/{database_name}"


# Global configuration instance
config = Config()