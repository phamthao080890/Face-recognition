"""
Database connections and models for Face Attendance System
"""
import os
import time
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError
from bson import ObjectId
from dataclasses import dataclass, asdict

from .config import config

# Configure logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Exception for database connection errors"""
    pass


class DatabaseOperationError(Exception):
    """Exception for database operation errors"""
    pass


@dataclass
class ImageData:
    """Image data structure for user images"""
    image_id: str
    full_image: str  # base64, width=600px
    thumbnail: str   # base64, 150x150px
    face_vector_id: str  # Reference to Qdrant


@dataclass
class UserInfo:
    """User information data structure"""
    id: Optional[str]
    name: str
    email: str
    phone: Optional[str] = None
    department: Optional[str] = None
    images: List[ImageData] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


class MongoDBConnection:
    """MongoDB connection and operations manager with retry logic and error handling"""
    
    def __init__(self, connection_string: str = None, database_name: str = None, 
                 max_retries: int = None, retry_delay: float = None):
        """
        Initialize MongoDB connection with retry logic
        
        Args:
            connection_string: MongoDB connection string (defaults to config)
            database_name: Name of the database to use (defaults to config)
            max_retries: Maximum number of connection retries (defaults to config)
            retry_delay: Initial delay between retries (defaults to config)
        """
        # Use config defaults if not provided
        self.connection_string = connection_string or config.MONGODB_CONNECTION_STRING
        self.database_name = database_name or config.MONGODB_DATABASE
        self.max_retries = max_retries or config.DB_MAX_RETRIES
        self.retry_delay = retry_delay or config.DB_RETRY_DELAY
        
        self.client = None
        self.database = None
        self.users_collection = None
        
        # Establish connection with retry logic
        self._connect_with_retry()
    
    def _connect_with_retry(self):
        """Establish MongoDB connection with exponential backoff retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Attempting MongoDB connection (attempt {attempt + 1}/{self.max_retries + 1})")
                
                # Create client with timeout settings
                self.client = MongoClient(
                    self.connection_string,
                    serverSelectionTimeoutMS=5000,  # 5 second timeout
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000
                )
                
                # Test the connection
                self.client.admin.command('ping')
                
                # Set up database and collection references
                self.database: Database = self.client[self.database_name]
                self.users_collection: Collection = self.database.users
                
                # Create indexes for better performance
                self._create_indexes()
                
                logger.info("MongoDB connection established successfully")
                return
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.warning(f"MongoDB connection attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("All MongoDB connection attempts failed")
                    raise DatabaseConnectionError(f"Failed to connect to MongoDB after {self.max_retries + 1} attempts: {str(e)}")
            
            except Exception as e:
                logger.error(f"Unexpected error during MongoDB connection: {str(e)}")
                raise DatabaseConnectionError(f"Unexpected MongoDB connection error: {str(e)}")
    
    def _ensure_connection(self):
        """Ensure database connection is active, reconnect if necessary"""
        try:
            if self.client is None:
                logger.warning("MongoDB client is None, attempting to reconnect")
                self._connect_with_retry()
                return
            
            # Test the connection
            self.client.admin.command('ping')
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"MongoDB connection lost, attempting to reconnect: {str(e)}")
            try:
                self._connect_with_retry()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to MongoDB: {str(reconnect_error)}")
                raise DatabaseConnectionError(f"Database connection lost and reconnection failed: {str(reconnect_error)}")
        
        except Exception as e:
            logger.error(f"Unexpected error checking MongoDB connection: {str(e)}")
            raise DatabaseConnectionError(f"Database connection check failed: {str(e)}")
    
    def _create_indexes(self):
        """Create database indexes for better performance with error handling"""
        try:
            # Create unique index on email
            self.users_collection.create_index("email", unique=True)
            # Create index on name for faster searches
            self.users_collection.create_index("name")
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.warning(f"Failed to create database indexes: {str(e)}")
            # Don't raise exception for index creation failures
    
    def _execute_with_retry(self, operation_name: str, operation_func):
        """Execute database operation with retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                # Ensure connection is active
                self._ensure_connection()
                
                # Execute the operation
                result = operation_func()
                logger.debug(f"Database operation '{operation_name}' completed successfully")
                return result
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.warning(f"Database operation '{operation_name}' failed due to connection issue (attempt {attempt + 1}): {str(e)}")
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying operation '{operation_name}' in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"Database operation '{operation_name}' failed after {self.max_retries + 1} attempts")
                    raise DatabaseOperationError(f"Operation '{operation_name}' failed after multiple retries: {str(e)}")
            
            except PyMongoError as e:
                logger.error(f"Database operation '{operation_name}' failed with PyMongo error: {str(e)}")
                raise DatabaseOperationError(f"Database operation '{operation_name}' failed: {str(e)}")
            
            except Exception as e:
                logger.error(f"Database operation '{operation_name}' failed with unexpected error: {str(e)}")
                raise DatabaseOperationError(f"Unexpected error in operation '{operation_name}': {str(e)}")
    
    def create_user(self, user_info: UserInfo) -> str:
        """
        Create a new user in the database with retry logic
        
        Args:
            user_info: User information to store
            
        Returns:
            str: The created user's ID
            
        Raises:
            ValueError: If user data is invalid
            DatabaseOperationError: If database operation fails
        """
        def _create_operation():
            # Convert UserInfo to dict for MongoDB storage
            user_dict = asdict(user_info)
            user_dict.pop('id', None)  # Remove id field, MongoDB will generate _id
            
            # Convert ImageData objects to dicts
            user_dict['images'] = [asdict(img) for img in user_info.images]
            
            # Insert user into database
            result = self.users_collection.insert_one(user_dict)
            return str(result.inserted_id)
        
        return self._execute_with_retry("create_user", _create_operation)
    
    def get_user(self, user_id: str) -> Optional[UserInfo]:
        """
        Retrieve a user by ID with retry logic
        
        Args:
            user_id: The user's ID
            
        Returns:
            UserInfo or None if user not found
        """
        def _get_operation():
            user_doc = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if user_doc:
                return self._doc_to_user_info(user_doc)
            return None
        
        try:
            return self._execute_with_retry("get_user", _get_operation)
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[UserInfo]:
        """
        Retrieve a user by email with retry logic
        
        Args:
            email: The user's email
            
        Returns:
            UserInfo or None if user not found
        """
        def _get_operation():
            user_doc = self.users_collection.find_one({"email": email})
            if user_doc:
                return self._doc_to_user_info(user_doc)
            return None
        
        try:
            return self._execute_with_retry("get_user_by_email", _get_operation)
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {str(e)}")
            return None
    
    def get_all_users(self) -> List[UserInfo]:
        """
        Retrieve all users from the database with retry logic
        
        Returns:
            List of UserInfo objects
        """
        def _get_all_operation():
            users = []
            for user_doc in self.users_collection.find():
                users.append(self._doc_to_user_info(user_doc))
            return users
        
        try:
            return self._execute_with_retry("get_all_users", _get_all_operation)
        except Exception as e:
            logger.error(f"Failed to get all users: {str(e)}")
            return []
    
    def update_user(self, user_id: str, user_info: UserInfo) -> bool:
        """
        Update an existing user with retry logic
        
        Args:
            user_id: The user's ID
            user_info: Updated user information
            
        Returns:
            bool: True if update successful, False otherwise
        """
        def _update_operation():
            user_dict = asdict(user_info)
            user_dict.pop('id', None)  # Remove id field
            user_dict['updated_at'] = datetime.utcnow()
            
            # Convert ImageData objects to dicts
            user_dict['images'] = [asdict(img) for img in user_info.images]
            
            result = self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": user_dict}
            )
            return result.modified_count > 0
        
        try:
            return self._execute_with_retry("update_user", _update_operation)
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {str(e)}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user from the database with retry logic
        
        Args:
            user_id: The user's ID
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        def _delete_operation():
            result = self.users_collection.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        
        try:
            return self._execute_with_retry("delete_user", _delete_operation)
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {str(e)}")
            return False
    
    def _doc_to_user_info(self, user_doc: Dict[str, Any]) -> UserInfo:
        """
        Convert MongoDB document to UserInfo object
        
        Args:
            user_doc: MongoDB document
            
        Returns:
            UserInfo object
        """
        # Convert images from dicts to ImageData objects
        images = []
        for img_dict in user_doc.get('images', []):
            images.append(ImageData(**img_dict))
        
        return UserInfo(
            id=str(user_doc['_id']),
            name=user_doc['name'],
            email=user_doc['email'],
            phone=user_doc.get('phone'),
            department=user_doc.get('department'),
            images=images,
            created_at=user_doc.get('created_at'),
            updated_at=user_doc.get('updated_at')
        )
    
    def close(self):
        """Close the database connection"""
        if self.client:
            self.client.close()


import uuid
from typing import Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
import numpy as np


@dataclass
class FaceVector:
    """Face vector data structure for Qdrant storage"""
    id: str
    vector: List[float]  # 512 dimensions from FaceNet
    user_id: str
    image_id: str
    created_at: str


class QdrantConnection:
    """Qdrant vector database connection and operations manager with retry logic and error handling"""
    
    def __init__(self, host: str = None, port: int = None, collection_name: str = None,
                 max_retries: int = None, retry_delay: float = None):
        """
        Initialize Qdrant connection with retry logic
        
        Args:
            host: Qdrant server host (defaults to config)
            port: Qdrant server port (defaults to config)
            collection_name: Name of the collection to use (defaults to config)
            max_retries: Maximum number of connection retries (defaults to config)
            retry_delay: Initial delay between retries (defaults to config)
        """
        # Use config defaults if not provided
        self.host = host or config.QDRANT_HOST
        self.port = port or config.QDRANT_PORT
        self.collection_name = collection_name or config.QDRANT_COLLECTION_NAME
        self.max_retries = max_retries or config.DB_MAX_RETRIES
        self.retry_delay = retry_delay or config.DB_RETRY_DELAY
        
        self.client = None
        
        # Establish connection with retry logic
        self._connect_with_retry()
    
    def _connect_with_retry(self):
        """Establish Qdrant connection with exponential backoff retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Attempting Qdrant connection (attempt {attempt + 1}/{self.max_retries + 1})")
                
                # Create Qdrant client
                self.client = QdrantClient(host=self.host, port=self.port, timeout=5.0)
                
                # Test the connection by getting collections
                self.client.get_collections()
                
                # Create collection if it doesn't exist
                self._create_collection()
                
                logger.info("Qdrant connection established successfully")
                return
                
            except (ResponseHandlingException, UnexpectedResponse, ConnectionError) as e:
                logger.warning(f"Qdrant connection attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying Qdrant connection in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("All Qdrant connection attempts failed")
                    raise DatabaseConnectionError(f"Failed to connect to Qdrant after {self.max_retries + 1} attempts: {str(e)}")
            
            except Exception as e:
                logger.error(f"Unexpected error during Qdrant connection: {str(e)}")
                raise DatabaseConnectionError(f"Unexpected Qdrant connection error: {str(e)}")
    
    def _ensure_connection(self):
        """Ensure Qdrant connection is active, reconnect if necessary"""
        try:
            if self.client is None:
                logger.warning("Qdrant client is None, attempting to reconnect")
                self._connect_with_retry()
                return
            
            # Test the connection
            self.client.get_collections()
            
        except (ResponseHandlingException, UnexpectedResponse, ConnectionError) as e:
            logger.warning(f"Qdrant connection lost, attempting to reconnect: {str(e)}")
            try:
                self._connect_with_retry()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to Qdrant: {str(reconnect_error)}")
                raise DatabaseConnectionError(f"Qdrant connection lost and reconnection failed: {str(reconnect_error)}")
        
        except Exception as e:
            logger.error(f"Unexpected error checking Qdrant connection: {str(e)}")
            raise DatabaseConnectionError(f"Qdrant connection check failed: {str(e)}")
    
    def _execute_with_retry(self, operation_name: str, operation_func):
        """Execute Qdrant operation with retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                # Ensure connection is active
                self._ensure_connection()
                
                # Execute the operation
                result = operation_func()
                logger.debug(f"Qdrant operation '{operation_name}' completed successfully")
                return result
                
            except (ResponseHandlingException, UnexpectedResponse, ConnectionError) as e:
                logger.warning(f"Qdrant operation '{operation_name}' failed due to connection issue (attempt {attempt + 1}): {str(e)}")
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying Qdrant operation '{operation_name}' in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"Qdrant operation '{operation_name}' failed after {self.max_retries + 1} attempts")
                    raise DatabaseOperationError(f"Qdrant operation '{operation_name}' failed after multiple retries: {str(e)}")
            
            except Exception as e:
                logger.error(f"Qdrant operation '{operation_name}' failed with unexpected error: {str(e)}")
                raise DatabaseOperationError(f"Unexpected error in Qdrant operation '{operation_name}': {str(e)}")
    
    def _create_collection(self):
        """Create Qdrant collection with proper configuration and error handling"""
        def _create_operation():
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection with 512-dimensional vectors (FaceNet output)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=512,  # FaceNet produces 512-dimensional vectors
                        distance=Distance.COSINE  # Use cosine distance for face similarity
                    )
                )
                logger.info(f"Created Qdrant collection '{self.collection_name}'")
            else:
                logger.info(f"Qdrant collection '{self.collection_name}' already exists")
        
        try:
            self._execute_with_retry("create_collection", _create_operation)
        except Exception as e:
            logger.warning(f"Failed to create Qdrant collection: {str(e)}")
            # Don't raise exception for collection creation failures during initialization
    
    def store_face_vector(self, user_id: str, image_id: str, face_vector: np.ndarray) -> str:
        """
        Store a face vector in Qdrant with retry logic
        
        Args:
            user_id: ID of the user this face belongs to
            image_id: ID of the image this face was extracted from
            face_vector: 512-dimensional face vector from FaceNet
            
        Returns:
            str: The vector ID in Qdrant
            
        Raises:
            ValueError: If vector dimensions are incorrect
            DatabaseOperationError: If storage operation fails
        """
        # Validate face_vector input
        if face_vector is None:
            raise ValueError("Face vector cannot be None")
        
        if not hasattr(face_vector, 'shape'):
            raise ValueError(f"Face vector must be a numpy array, got {type(face_vector)}")
        
        if len(face_vector.shape) == 0:
            raise ValueError("Face vector cannot be a scalar")
        
        # Validate vector dimensions
        if face_vector.shape[0] != 512:
            raise ValueError(f"Face vector must be 512-dimensional, got {face_vector.shape[0]}")
        
        def _store_operation():
            # Generate unique ID for this vector
            vector_id = str(uuid.uuid4())
            
            # Create point with vector and metadata
            point = PointStruct(
                id=vector_id,
                vector=face_vector.tolist(),
                payload={
                    "user_id": user_id,
                    "image_id": image_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # Store in Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            return vector_id
        
        return self._execute_with_retry("store_face_vector", _store_operation)
    
    def search_similar_faces(self, query_vector: np.ndarray, limit: int = 10, score_threshold: float = 0.8) -> List[Tuple[str, float]]:
        """
        Search for similar face vectors with retry logic
        
        Args:
            query_vector: 512-dimensional query vector
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of tuples (user_id, similarity_score)
            
        Raises:
            ValueError: If vector dimensions are incorrect
            DatabaseOperationError: If search operation fails
        """
        # Validate vector dimensions
        if query_vector.shape[0] != 512:
            raise ValueError(f"Query vector must be 512-dimensional, got {query_vector.shape[0]}")
        
        def _search_operation():
            # Search for similar vectors
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector.tolist(),
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Extract user IDs and scores
            results = []
            for hit in search_result:
                user_id = hit.payload.get("user_id")
                score = hit.score
                if user_id and score >= score_threshold:
                    results.append((user_id, score))
            
            return results
        
        return self._execute_with_retry("search_similar_faces", _search_operation)
    
    def get_user_vectors(self, user_id: str) -> List[FaceVector]:
        """
        Get all face vectors for a specific user with retry logic
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of FaceVector objects
            
        Raises:
            DatabaseOperationError: If retrieval operation fails
        """
        def _get_vectors_operation():
            # Search for all vectors belonging to this user
            search_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=100  # Assuming max 100 vectors per user (20 images * 5 faces each)
            )
            
            vectors = []
            for point in search_result[0]:  # scroll returns (points, next_page_offset)
                vectors.append(FaceVector(
                    id=str(point.id),
                    vector=point.vector,
                    user_id=point.payload["user_id"],
                    image_id=point.payload["image_id"],
                    created_at=point.payload["created_at"]
                ))
            
            return vectors
        
        return self._execute_with_retry("get_user_vectors", _get_vectors_operation)
    
    def delete_user_vectors(self, user_id: str) -> bool:
        """
        Delete all face vectors for a specific user with retry logic
        
        Args:
            user_id: The user's ID
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        def _delete_operation():
            # Delete all vectors belonging to this user
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                )
            )
            return True
        
        try:
            return self._execute_with_retry("delete_user_vectors", _delete_operation)
        except Exception as e:
            logger.error(f"Failed to delete user vectors for user {user_id}: {str(e)}")
            return False
    
    def delete_vector(self, vector_id: str) -> bool:
        """
        Delete a specific face vector with retry logic
        
        Args:
            vector_id: The vector's ID
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        def _delete_operation():
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[vector_id]
            )
            return True
        
        try:
            return self._execute_with_retry("delete_vector", _delete_operation)
        except Exception as e:
            logger.error(f"Failed to delete vector {vector_id}: {str(e)}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection with retry logic
        
        Returns:
            Dictionary with collection information
        """
        def _get_info_operation():
            return self.client.get_collection(self.collection_name).dict()
        
        try:
            return self._execute_with_retry("get_collection_info", _get_info_operation)
        except Exception as e:
            logger.error(f"Failed to get collection info: {str(e)}")
            return {}
    
    def close(self):
        """Close the Qdrant connection"""
        # Qdrant client doesn't need explicit closing
        pass