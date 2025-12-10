import face_recognition
import numpy as np
import cv2
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ARRAY, Float, DateTime
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
from sqlalchemy import func # Import func for datetime operations

# --- 0. Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CogniAnchorAPI")
 
# --- 1. Database Configuration ---
DATABASE_URL = "postgresql://ebinsanthosh:password@localhost:5432/facedb" 

engine = create_engine(DATABASE_URL)
Base = declarative_base()

# --- 1.1. Face Recognition Model (Existing) ---
class KnownFace(Base):
    """SQLAlchemy model for storing known face data."""
    __tablename__ = "known_faces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    relationship = Column(String)
    occupation = Column(String)
    age = Column(String)
    notes = Column(String)
    face_encoding = Column(ARRAY(Float)) 

# --- 1.2. Reminder System Model (NEW) ---
class Reminder(Base):
    """SQLAlchemy model for storing reminder data."""
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    # Stores combined date and time for easy sorting
    scheduled_datetime = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to provide a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 2. Pydantic Models for Request/Response ---

# Model for Recognition Result (Existing)
class RecognitionResult(BaseModel):
    """Model for the face recognition API response."""
    match_found: bool
    person_name: Optional[str] = None
    relationship: Optional[str] = None
    occupation: Optional[str] = None
    age: Optional[str] = None
    notes: Optional[str] = None
    similarity_score: Optional[float] = None

# Models for Reminder System (NEW)
class ReminderCreate(BaseModel):
    """Request model for creating a new reminder."""
    title: str
    date: str # Expects format like '17 Nov 2025'
    time: str # Expects format like '06:30 AM'

class ReminderResponse(BaseModel):
    """Response model for a reminder."""
    id: int
    title: str
    # Return date and time as separate formatted strings for the Flutter UI
    date: str
    time: str
    
    class Config:
        orm_mode = True

# --- 3. Core Face Recognition Utility (Existing) ---
def get_face_encoding(image_bytes: bytes) -> Optional[np.ndarray]:
    """Detects a face in the image bytes and returns its 128-dim encoding."""
    
    img_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if image is None or image.size == 0:
        logger.error("CV2 failed to decode image bytes or image is empty.")
        return None

    rgb_image = image[:, :, ::-1]
    rgb_image = np.ascontiguousarray(rgb_image)

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
        # Create all tables if they don't exist
        Base.metadata.create_all(bind=engine)
        logger.info("SUCCESS: Database connection established and tables ensured.")
    except OperationalError as e:
        logger.error(f"FATAL ERROR: Could not connect to the database or create tables. Error: {e}")

# --- 4.1. Reminder Endpoints (NEW) ---

@app.post("/api/v1/reminders/create")
async def create_reminder(
    reminder_data: ReminderCreate, 
    db: Session = Depends(get_db)
):
    """Creates a new reminder in the database."""
    logger.info(f"Received request to create reminder: {reminder_data.title}")
    
    try:
        # Combine date and time strings into a parsable format, then into a datetime object
        datetime_str = f"{reminder_data.date} {reminder_data.time}"
        # Example format: '17 Nov 2025 06:30 AM' -> '%d %b %Y %I:%M %p'
        scheduled_dt = datetime.strptime(datetime_str, '%d %b %Y %I:%M %p')
    except ValueError as e:
        logger.error(f"Failed to parse datetime: {e}. Input: {datetime_str}")
        raise HTTPException(status_code=400, detail="Invalid date or time format. Expected 'dd MMM yyyy' and 'HH:MM AM/PM'.")

    new_reminder = Reminder(
        title=reminder_data.title, 
        scheduled_datetime=scheduled_dt
    )
    
    try:
        db.add(new_reminder)
        db.commit()
        db.refresh(new_reminder)
    except OperationalError as e:
        db.rollback()
        logger.error(f"Database write failed for reminder {reminder_data.title}. Error: {e}")
        raise HTTPException(status_code=500, detail="Database error during reminder creation.")
        
    logger.info(f"SUCCESS: Created new reminder: {new_reminder.title}")
    return {"message": "Reminder created successfully", "reminder_id": new_reminder.id}

@app.get("/api/v1/reminders/get", response_model=List[ReminderResponse])
async def get_reminders(
    db: Session = Depends(get_db)
):
    """Fetches all future reminders, sorted by scheduled time."""
    logger.info("Received request to get all future reminders.")
    
    try:
        # Query for all reminders scheduled from now onwards, ordered ascendingly
        reminders_db = db.query(Reminder) \
            .filter(Reminder.scheduled_datetime >= datetime.now()) \
            .order_by(Reminder.scheduled_datetime) \
            .all()
    except OperationalError as e:
        logger.error(f"Database read failed during reminder retrieval. Error: {e}")
        raise HTTPException(status_code=500, detail="Database error during reminder retrieval.")

    # Convert database objects to the desired response format
    reminders_response = []
    for r in reminders_db:
        reminders_response.append(ReminderResponse(
            id=r.id,
            title=r.title,
            # Format scheduled_datetime back into separate date and time strings
            date=r.scheduled_datetime.strftime('%d %b %Y'), 
            time=r.scheduled_datetime.strftime('%I:%M %p'),
        ))
        
    logger.info(f"SUCCESS: Retrieved {len(reminders_response)} future reminders.")
    return reminders_response

# --- 4.2. Face Recognition Endpoints (Existing) ---

@app.post("/api/v1/faces/enroll")
async def enroll_person(
    name: str = Form(...),
    relationship: str = Form(...),
    occupation: str = Form('N/A'),
    age: str = Form('N/A'),
    notes: str = Form(''),
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    logger.info(f"Received enrollment request for: {name} ({relationship}).")
    # ... [Existing face recognition logic for enrollment] ...
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
        occupation=occupation,
        age=age,
        notes=notes,
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
    # ... [Existing face recognition logic for recognition] ...
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
            occupation=match_data['occupation'],
            age=match_data['age'],
            notes=match_data['notes'],
            similarity_score=best_match_distance
        )
    else:
        logger.info(f"NO MATCH: Closest distance was {best_match_distance:.4f}, exceeding tolerance {tolerance}.")
        return RecognitionResult(
            match_found=False, 
            similarity_score=best_match_distance
        )