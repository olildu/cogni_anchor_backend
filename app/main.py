import face_recognition
import numpy as np
import cv2
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ARRAY, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError

# --- 0. Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FacialRecogAPI")
 
# --- 1. Database Configuration ---
DATABASE_URL = "postgresql://ebinsanthosh:password@localhost:5432/facedb" 

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class KnownFace(Base):
    """SQLAlchemy model for storing known face data."""
    __tablename__ = "known_faces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    relationship = Column(String)
    occupation = Column(String) # NEW FIELD
    age = Column(String)        # NEW FIELD
    notes = Column(String)      # NEW FIELD
    face_encoding = Column(ARRAY(Float)) 

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to provide a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 2. Pydantic Models for Response ---
class RecognitionResult(BaseModel):
    """Model for the face recognition API response."""
    match_found: bool
    person_name: Optional[str] = None
    relationship: Optional[str] = None
    occupation: Optional[str] = None # NEW FIELD
    age: Optional[str] = None        # NEW FIELD
    notes: Optional[str] = None      # NEW FIELD
    similarity_score: Optional[float] = None

# --- 3. Core Face Recognition Utility ---
def get_face_encoding(image_bytes: bytes) -> Optional[np.ndarray]:
    """Detects a face in the image bytes and returns its 128-dim encoding."""
    
    img_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if image is None:
        logger.error("CV2 failed to decode image bytes.")
        return None

    if image.size == 0:
        logger.error("Decoded image is empty (zero size).")
        return None

    rgb_image = image[:, :, ::-1]
    rgb_image = np.ascontiguousarray(rgb_image) # Ensures memory contiguity for dlib

    try:
        face_locations = face_recognition.face_locations(rgb_image)
        
        if not face_locations:
            logger.info("No face locations detected in the image.")
            return None
        
        encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        return encodings[0] if encodings else None
        
    except Exception as e:
        logger.error(f"Error during dlib/face_recognition processing: {e}")
        return None


# --- 4. FastAPI Application and Endpoints ---
app = FastAPI()

@app.on_event("startup")
def startup_event():
    logger.info("Application startup initiated.")
    try:
        conn = engine.connect()
        conn.close()
        logger.info("SUCCESS: Database connection established successfully.")
    except OperationalError as e:
        logger.error(f"FATAL ERROR: Could not connect to the database. Error: {e}")
    
@app.post("/api/v1/faces/enroll")
async def enroll_person(
    name: str = Form(...),
    relationship: str = Form(...),
    occupation: str = Form('N/A'), # NEW FIELD
    age: str = Form('N/A'),        # NEW FIELD
    notes: str = Form(''),         # NEW FIELD
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    logger.info(f"Received enrollment request for: {name} ({relationship}).")
    try:
        image_bytes = await file.read()
        face_encoding_np = get_face_encoding(image_bytes)
    except Exception as e:
        logger.error(f"Error reading or processing image file during enrollment: {e}")
        raise HTTPException(status_code=500, detail="Failed to process image file.")

    if face_encoding_np is None:
        logger.warning(f"Enrollment failed for {name}: No usable face detected.")
        raise HTTPException(status_code=400, detail="No usable face detected in the image.")
    
    existing_face = db.query(KnownFace).filter(KnownFace.name == name).first()
    if existing_face:
        logger.warning(f"Enrollment failed for {name}: Name already exists in DB.")
        raise HTTPException(status_code=409, detail=f"Person '{name}' already exists in the database.")

    # Store the new fields
    new_face = KnownFace(
        name=name, 
        relationship=relationship, 
        occupation=occupation, # NEW
        age=age,               # NEW
        notes=notes,           # NEW
        face_encoding=face_encoding_np.tolist()
    )
    try:
        db.add(new_face)
        db.commit()
        db.refresh(new_face)
    except OperationalError as e:
        db.rollback()
        logger.error(f"Database write failed for {name}. Error: {e}")
        raise HTTPException(status_code=500, detail="Database error during enrollment.")

    logger.info(f"SUCCESS: Enrolled new person: {name} (ID: {new_face.id}).")
    return {"message": f"Successfully enrolled {name}", "person_id": new_face.id}


@app.post("/api/v1/faces/recognize", response_model=RecognitionResult)
async def recognize_face(
    file: UploadFile = File(...),
    tolerance: float = 0.6,
    db: Session = Depends(get_db)
):
    logger.info("Received recognition request.")
    try:
        image_bytes = await file.read()
        unknown_encoding_np = get_face_encoding(image_bytes)
    except Exception as e:
        logger.error(f"Error reading or processing image file during recognition: {e}")
        raise HTTPException(status_code=500, detail="Failed to process image file.")

    if unknown_encoding_np is None:
        logger.info("Recognition failed: No face detected in the unknown image.")
        return RecognitionResult(match_found=False)

    try:
        known_faces = db.query(KnownFace).all()
    except OperationalError as e:
        logger.error(f"Database read failed during recognition. Error: {e}")
        raise HTTPException(status_code=500, detail="Database error during recognition.")
    
    if not known_faces:
        logger.info("Recognition failed: Database is empty.")
        return RecognitionResult(match_found=False)

    known_encodings = [np.array(face.face_encoding) for face in known_faces]
    
    # Collect all data fields for response
    known_data = [
        {"name": face.name, "relationship": face.relationship, "occupation": face.occupation, "age": face.age, "notes": face.notes} 
        for face in known_faces
    ]

    distances = face_recognition.face_distance(known_encodings, unknown_encoding_np)
    min_distance_index = np.argmin(distances)
    best_match_distance = distances[min_distance_index]

    if best_match_distance < tolerance:
        match_data = known_data[min_distance_index]
        logger.info(f"SUCCESS: Recognized match: {match_data['name']} with similarity score {best_match_distance:.4f}.")
        return RecognitionResult(
            match_found=True,
            person_name=match_data['name'],
            relationship=match_data['relationship'],
            occupation=match_data['occupation'], # NEW
            age=match_data['age'],               # NEW
            notes=match_data['notes'],           # NEW
            similarity_score=best_match_distance
        )
    else:
        logger.info(f"NO MATCH: Closest distance was {best_match_distance:.4f}, exceeding tolerance {tolerance}.")
        return RecognitionResult(
            match_found=False, 
            similarity_score=best_match_distance
        )