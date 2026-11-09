"""
Face Manager module for face attendance system.
Handles face detection using YOLOv8n and face encoding using FaceNet.
"""

import io
import os
import numpy as np
from typing import List, Optional, Tuple
from PIL import Image
from ultralytics import YOLO
import torch
from facenet_pytorch import InceptionResnetV1
import torch.nn.functional as F

from .config import config


class BoundingBox:
    """Represents a face bounding box."""
    
    def __init__(self, x1: float, y1: float, x2: float, y2: float, confidence: float):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.confidence = confidence
    
    @property
    def width(self) -> float:
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        return self.y2 - self.y1


class FaceEncoder:
    """Face encoder using pre-trained FaceNet model."""
    
    def __init__(self):
        """Initialize the face encoder with pre-trained FaceNet model."""
        # Load pre-trained FaceNet model
        self.model = InceptionResnetV1(pretrained='vggface2').eval()
        self.device = torch.device('cpu')  # Use CPU as specified in requirements
        self.model.to(self.device)
        
        # Standard face size for FaceNet
        self.face_size = 160
    
    def normalize_face(self, face_image: np.ndarray) -> torch.Tensor:
        """
        Normalize face image for FaceNet processing.
        
        Args:
            face_image: Face image as numpy array (RGB format)
            
        Returns:
            Normalized face tensor ready for encoding
        """
        # Convert numpy array to PIL Image
        if isinstance(face_image, np.ndarray):
            pil_image = Image.fromarray(face_image.astype('uint8'))
        else:
            pil_image = face_image
        
        # Resize to standard FaceNet input size (160x160)
        pil_image = pil_image.resize((self.face_size, self.face_size), Image.Resampling.LANCZOS)
        
        # Convert to tensor and normalize
        face_tensor = torch.tensor(np.array(pil_image)).float()
        
        # Rearrange dimensions from HWC to CHW
        face_tensor = face_tensor.permute(2, 0, 1)
        
        # Normalize to [-1, 1] range (standard for FaceNet)
        face_tensor = (face_tensor - 127.5) / 128.0
        
        # Add batch dimension
        face_tensor = face_tensor.unsqueeze(0)
        
        return face_tensor.to(self.device)
    
    def encode_face(self, face_image: np.ndarray) -> np.ndarray:
        """
        Encode face image to 512-dimensional vector using FaceNet.
        
        Args:
            face_image: Face image as numpy array (RGB format)
            
        Returns:
            512-dimensional face encoding vector
        """
        # Normalize face image
        face_tensor = self.normalize_face(face_image)
        
        # Generate encoding
        with torch.no_grad():
            encoding = self.model(face_tensor)
            
            # Normalize the encoding vector (L2 normalization)
            encoding = F.normalize(encoding, p=2, dim=1)
        
        # Convert to numpy array and remove batch dimension
        encoding_vector = encoding.cpu().numpy().flatten()
        
        # Ensure exactly 512 dimensions
        assert len(encoding_vector) == 512, f"Expected 512 dimensions, got {len(encoding_vector)}"
        
        return encoding_vector


class FaceDetector:
    """Face detector using YOLOv8n model."""
    
    def __init__(self):
        """Initialize the face detector with YOLOv8n model."""
        # Set environment variable to allow loading YOLO models
        os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD'] = '1'
        
        # Load YOLOv8n model - will download if not present
        self.model = YOLO(config.YOLO_MODEL_PATH)  # Use config for model path
        self.confidence_threshold = config.YOLO_CONFIDENCE_THRESHOLD
    
    def detect_faces(self, image: np.ndarray) -> List[BoundingBox]:
        """
        Detect faces in an image using YOLOv8n.
        Note: Using person detection as a proxy for face detection in this implementation.
        
        Args:
            image: Input image as numpy array (RGB format)
            
        Returns:
            List of BoundingBox objects for detected faces/persons
        """
        # Run inference
        results = self.model(image, conf=self.confidence_threshold, verbose=False)
        
        faces = []
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    # Filter for person class (class 0 in COCO dataset)
                    if int(box.cls[0]) == 0:  # Person class
                        # Extract bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        
                        faces.append(BoundingBox(
                            x1=float(x1),
                            y1=float(y1), 
                            x2=float(x2),
                            y2=float(y2),
                            confidence=float(confidence)
                        ))
        
        return faces
    
    def crop_face(self, image: np.ndarray, bbox: BoundingBox, padding: float = 0.2) -> np.ndarray:
        """
        Crop face from image with appropriate padding.
        
        Args:
            image: Input image as numpy array
            bbox: Bounding box of the face
            padding: Padding factor (0.2 = 20% padding)
            
        Returns:
            Cropped face image as numpy array
        """
        height, width = image.shape[:2]
        
        # Calculate padding
        face_width = bbox.width
        face_height = bbox.height
        pad_x = face_width * padding
        pad_y = face_height * padding
        
        # Calculate crop coordinates with padding
        x1 = max(0, int(bbox.x1 - pad_x))
        y1 = max(0, int(bbox.y1 - pad_y))
        x2 = min(width, int(bbox.x2 + pad_x))
        y2 = min(height, int(bbox.y2 + pad_y))
        
        # Crop the face
        cropped_face = image[y1:y2, x1:x2]
        
        return cropped_face


class FaceManager:
    """Main face management class combining detection and encoding."""
    
    def __init__(self):
        """Initialize face manager with detector and encoder."""
        self.detector = FaceDetector()
        self.encoder = FaceEncoder()
    
    def detect_faces(self, image: np.ndarray) -> List[BoundingBox]:
        """
        Detect faces in an image.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of detected face bounding boxes
        """
        return self.detector.detect_faces(image)
    
    def encode_face(self, face_image: np.ndarray) -> np.ndarray:
        """
        Encode face image to 512-dimensional vector.
        
        Args:
            face_image: Face image as numpy array (RGB format)
            
        Returns:
            512-dimensional face encoding vector
        """
        return self.encoder.encode_face(face_image)
    
    def crop_face(self, image: np.ndarray, bbox: BoundingBox, padding: float = 0.2) -> np.ndarray:
        """
        Crop face from image with padding.
        
        Args:
            image: Input image as numpy array
            bbox: Face bounding box
            padding: Padding factor
            
        Returns:
            Cropped face image
        """
        return self.detector.crop_face(image, bbox, padding)
    
    def calculate_cosine_similarity(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two face vectors.
        
        Args:
            vector1: First face encoding vector
            vector2: Second face encoding vector
            
        Returns:
            Cosine similarity score (0-1, where 1 is identical)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(vector1)
        norm2 = np.linalg.norm(vector2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = np.dot(vector1, vector2) / (norm1 * norm2)
        
        # Ensure result is in [0, 1] range
        similarity = max(0.0, min(1.0, similarity))
        
        return float(similarity)
    
    def search_similar_face(self, face_vector: np.ndarray, stored_vectors: List[Tuple[str, np.ndarray]], 
                           threshold: float = None) -> Optional[str]:
        """
        Search for similar face in stored vectors using cosine distance.
        
        Args:
            face_vector: Face encoding vector to search for
            stored_vectors: List of (user_id, vector) tuples to search against
            threshold: Similarity threshold for matching (defaults to config)
            
        Returns:
            User ID of best match if above threshold, None otherwise
        """
        if threshold is None:
            threshold = config.FACE_SIMILARITY_THRESHOLD
        if not stored_vectors:
            return None
        
        best_match_id = None
        best_similarity = 0.0
        
        # Compare against all stored vectors
        for user_id, stored_vector in stored_vectors:
            similarity = self.calculate_cosine_similarity(face_vector, stored_vector)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = user_id
        
        # Return match only if above threshold
        if best_similarity >= threshold:
            return best_match_id
        
        return None
    
    def is_match(self, face_vector1: np.ndarray, face_vector2: np.ndarray, threshold: float = None) -> bool:
        """
        Check if two face vectors match based on threshold.
        
        Args:
            face_vector1: First face encoding vector
            face_vector2: Second face encoding vector
            threshold: Similarity threshold for matching (defaults to config)
            
        Returns:
            True if vectors match (similarity >= threshold), False otherwise
        """
        if threshold is None:
            threshold = config.FACE_SIMILARITY_THRESHOLD
        similarity = self.calculate_cosine_similarity(face_vector1, face_vector2)
        return similarity >= threshold
    
    def process_image_bytes(self, image_bytes: bytes) -> Tuple[np.ndarray, List[BoundingBox]]:
        """
        Process image bytes and detect faces.
        
        Args:
            image_bytes: Input image as bytes
            
        Returns:
            Tuple of (image_array, detected_faces)
        """
        # Convert bytes to PIL Image
        pil_image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(pil_image)
        
        # Detect faces
        faces = self.detect_faces(image_array)
        
        return image_array, faces