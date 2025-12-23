"""
Face Recognition Service
Handles face detection, embedding generation, and matching using DeepFace
"""

import os
import logging
import numpy as np
from typing import Optional, List, Tuple
from deepface import DeepFace
import cv2
from PIL import Image
import io

logger = logging.getLogger("FaceRecognitionService")

class FaceRecognitionService:
    """Service for face detection and recognition operations"""

    def __init__(self, model_name: str = "Facenet512"):
        """
        Initialize face recognition service

        Args:
            model_name: DeepFace model to use (Facenet512, VGG-Face, ArcFace, etc.)
        """
        self.model_name = model_name
        self.detector_backend = "opencv"  # Fast and reliable
        logger.info(f"FaceRecognitionService initialized with model: {model_name}")

    def detect_faces(self, image_path: str) -> List[dict]:
        """
        Detect faces in an image

        Args:
            image_path: Path to image file

        Returns:
            List of detected face regions with bounding boxes
        """
        try:
            faces = DeepFace.extract_faces(
                img_path=image_path,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )
            logger.info(f"Detected {len(faces)} face(s) in image")
            return faces
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []

    def generate_embedding(self, image_path: str) -> Optional[List[float]]:
        """
        Generate face embedding from image

        Args:
            image_path: Path to image file

        Returns:
            Face embedding as list of floats, or None if failed
        """
        try:
            # Generate embedding using DeepFace
            embedding_objs = DeepFace.represent(
                img_path=image_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )

            if embedding_objs and len(embedding_objs) > 0:
                # Get first face embedding
                embedding = embedding_objs[0]["embedding"]
                logger.info(f"Generated embedding with dimension: {len(embedding)}")
                return embedding
            else:
                logger.warning("No face detected in image")
                return None

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def generate_embedding_from_bytes(self, image_bytes: bytes) -> Optional[List[float]]:
        """
        Generate face embedding from image bytes

        Args:
            image_bytes: Image data as bytes

        Returns:
            Face embedding as list of floats, or None if failed
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Generate embedding
            embedding_objs = DeepFace.represent(
                img_path=img,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )

            if embedding_objs and len(embedding_objs) > 0:
                embedding = embedding_objs[0]["embedding"]
                logger.info(f"Generated embedding from bytes with dimension: {len(embedding)}")
                return embedding
            else:
                logger.warning("No face detected in image bytes")
                return None

        except Exception as e:
            logger.error(f"Error generating embedding from bytes: {e}")
            return None

    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding

        Returns:
            Cosine similarity score (0-1, higher is more similar)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Convert from [-1, 1] to [0, 1] range
            similarity = (similarity + 1) / 2

            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def find_best_match(
        self,
        query_embedding: List[float],
        database_embeddings: List[Tuple[int, List[float]]],
        threshold: float = 0.6
    ) -> Optional[Tuple[int, float]]:
        """
        Find best matching face from database

        Args:
            query_embedding: Query face embedding
            database_embeddings: List of (person_id, embedding) tuples
            threshold: Minimum similarity threshold (0-1)

        Returns:
            Tuple of (person_id, similarity_score) if match found, else None
        """
        try:
            best_match_id = None
            best_score = 0.0

            for person_id, db_embedding in database_embeddings:
                similarity = self.cosine_similarity(query_embedding, db_embedding)

                if similarity > best_score and similarity >= threshold:
                    best_score = similarity
                    best_match_id = person_id

            if best_match_id is not None:
                logger.info(f"Found match: person_id={best_match_id}, score={best_score:.4f}")
                return (best_match_id, best_score)
            else:
                logger.info(f"No match found above threshold {threshold}")
                return None

        except Exception as e:
            logger.error(f"Error finding best match: {e}")
            return None

    def crop_face(self, image_path: str, output_path: str) -> bool:
        """
        Detect and crop face from image

        Args:
            image_path: Input image path
            output_path: Output cropped face path

        Returns:
            True if successful, False otherwise
        """
        try:
            faces = self.detect_faces(image_path)

            if not faces or len(faces) == 0:
                logger.warning("No face detected for cropping")
                return False

            # Get first face region
            face = faces[0]
            facial_area = face.get("facial_area", {})

            if not facial_area:
                logger.warning("No facial area found")
                return False

            # Read original image
            img = cv2.imread(image_path)

            # Crop face region
            x = facial_area.get("x", 0)
            y = facial_area.get("y", 0)
            w = facial_area.get("w", 0)
            h = facial_area.get("h", 0)

            cropped = img[y:y+h, x:x+w]

            # Save cropped face
            cv2.imwrite(output_path, cropped)
            logger.info(f"Face cropped and saved to {output_path}")

            return True

        except Exception as e:
            logger.error(f"Error cropping face: {e}")
            return False


# Global service instance
_face_recognition_service = None

def get_face_recognition_service() -> FaceRecognitionService:
    """Get or create global face recognition service instance"""
    global _face_recognition_service

    if _face_recognition_service is None:
        _face_recognition_service = FaceRecognitionService()

    return _face_recognition_service
