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
        self.model_name = model_name
        self.detector_backend = "opencv"  
        logger.info(f"FaceRecognitionService initialized with model: {model_name}")

    def detect_faces(self, image_path: str) -> List[dict]:
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
        try:
            embedding_objs = DeepFace.represent(
                img_path=image_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )

            if embedding_objs and len(embedding_objs) > 0:
                embedding = embedding_objs[0]["embedding"]
                logger.info(f"Generated embedding with dimension: {len(embedding)}")
                return embedding
            else:
                logger.warning("No face detected in image")
                return None

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def find_best_match(
        self,
        query_embedding: List[float],
        database_embeddings: List[Tuple[str, List[float]]],
        threshold: float = 0.4
    ) -> Optional[Tuple[str, float]]: 
        """Find best matching face from database"""
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

# Global service instance
_face_recognition_service = None

def get_face_recognition_service() -> FaceRecognitionService:
    global _face_recognition_service
    if _face_recognition_service is None:
        _face_recognition_service = FaceRecognitionService()
    return _face_recognition_service