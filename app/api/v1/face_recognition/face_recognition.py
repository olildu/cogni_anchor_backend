"""
Face Recognition API Endpoints (PostgreSQL Version)
Handles face detection, person enrollment, scanning, and matching
"""

import logging
import os
import uuid
import json
import shutil
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sql_models import Person, FaceEmbedding
from app.models.database_models import (
    PersonInfo,
    FaceScanRequest,
    FaceScanResponse,
    PeopleListResponse,
    SuccessResponse
)

from app.services.face_recognition.face_recognition_service import get_face_recognition_service

logger = logging.getLogger("FaceRecognitionAPI")
router = APIRouter(prefix="/api/v1/face", tags=["Face Recognition"])

# Directories
UPLOAD_DIR = "static/uploads"
TEMP_DIR = "temp"

# ===== HELPER FUNCTIONS =====

def save_image_locally(upload_file: UploadFile) -> str:
    """Save uploaded image to permanent local storage"""
    try:
        # Generate unique filename
        ext = upload_file.filename.split(".")[-1] if "." in upload_file.filename else "jpg"
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        # Save file
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        # Return URL path accessible via FastAPI static mount
        return f"/static/uploads/{filename}"
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        raise HTTPException(status_code=500, detail="Failed to save image locally")

async def save_temp_image(upload_file: UploadFile) -> str:
    """Save uploaded image to temp directory for processing"""
    try:
        ext = upload_file.filename.split(".")[-1] if "." in upload_file.filename else "jpg"
        filename = f"temp_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(TEMP_DIR, filename)
        
        contents = await upload_file.read()
        with open(filepath, "wb") as f:
            f.write(contents)
            
        return filepath
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save temp image")

# ===== API ENDPOINTS =====

@router.post("/addPerson", response_model=PersonInfo, status_code=status.HTTP_201_CREATED)
async def add_person(
    pair_id: str = Form(...),
    name: str = Form(...),
    relationship: str = Form(...),
    occupation: str = Form(...),
    age: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    embedding: Optional[str] = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Add a person to face recognition database (PostgreSQL)"""
    temp_path = None
    try:
        logger.info(f"Adding person {name} for pair {pair_id}")

        # 1. Process Image & Embedding
        # Save locally for serving
        image_url = save_image_locally(image)
        
        await image.seek(0)        
        temp_path = await save_temp_image(image)

        final_embedding = None
        if embedding:
            try:
                final_embedding = json.loads(embedding)
            except: pass
        
        if not final_embedding:
            face_service = get_face_recognition_service()
            final_embedding = face_service.generate_embedding(temp_path)

        if not final_embedding:
            raise HTTPException(status_code=400, detail="No face detected.")

        # 2. Save to PostgreSQL
        new_person = Person(
            pair_id=pair_id,
            name=name,
            relationship=relationship,
            occupation=occupation,
            age=age,
            notes=notes,
            image_url=image_url
        )
        db.add(new_person)
        db.commit()
        db.refresh(new_person)

        # 3. Save Embedding
        new_embedding = FaceEmbedding(
            person_id=new_person.id,
            embedding=final_embedding
        )
        db.add(new_embedding)
        db.commit()

        logger.info(f"Person added: {new_person.id}")
        return new_person

    except Exception as e:
        logger.error(f"Add person error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@router.get("/getPeople", response_model=PeopleListResponse)
async def get_people(pair_id: str, db: Session = Depends(get_db)):
    """Get all people for a pair"""
    try:
        people = db.query(Person).filter(Person.pair_id == pair_id).all()
        people_list = [PersonInfo.from_orm(p) for p in people]
        return PeopleListResponse(people=people_list, count=len(people_list))
    except Exception as e:
        logger.error(f"Error getting people: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan", response_model=FaceScanResponse)
async def scan_face(scan_request: FaceScanRequest, db: Session = Depends(get_db)):
    """Match face against database"""
    try:
        # 1. Get all people for this pair
        people = db.query(Person).filter(Person.pair_id == scan_request.pair_id).all()
        if not people:
            return FaceScanResponse(matched=False)
        
        person_ids = [p.id for p in people]

        # 2. Get embeddings
        embeddings = db.query(FaceEmbedding).filter(FaceEmbedding.person_id.in_(person_ids)).all()
        
        if not embeddings:
            return FaceScanResponse(matched=False)

        # Prepare for service [(id, vector), ...]
        db_embeddings = [(e.person_id, e.embedding) for e in embeddings]

        # 3. Match
        face_service = get_face_recognition_service()
        match = face_service.find_best_match(scan_request.embedding, db_embeddings)

        if match:
            person_id, score = match
            person = next((p for p in people if p.id == person_id), None)
            if person:
                return FaceScanResponse(matched=True, score=score, person=PersonInfo.from_orm(person))

        return FaceScanResponse(matched=False)

    except Exception as e:
        logger.error(f"Scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/updatePerson", response_model=PersonInfo)
async def update_person(
    person_id: str = Form(...),
    name: Optional[str] = Form(None),
    relationship: Optional[str] = Form(None),
    occupation: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    try:
        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        if name: person.name = name
        if relationship: person.relationship = relationship
        if occupation: person.occupation = occupation
        if age: person.age = age
        if notes: person.notes = notes

        if image:
            # Save new image locally
            image_url = save_image_locally(image)
            person.image_url = image_url
            
            # Update embedding
            await image.seek(0)
            temp_path = await save_temp_image(image)
            face_service = get_face_recognition_service()
            new_emb = face_service.generate_embedding(temp_path)
            
            if new_emb:
                # Update existing embedding record
                db_emb = db.query(FaceEmbedding).filter(FaceEmbedding.person_id == person_id).first()
                if db_emb:
                    db_emb.embedding = new_emb
                else:
                    db.add(FaceEmbedding(person_id=person_id, embedding=new_emb))
            
            if os.path.exists(temp_path): os.remove(temp_path)

        db.commit()
        db.refresh(person)
        return person

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/deletePerson", response_model=SuccessResponse)
async def delete_person(person_id: str, db: Session = Depends(get_db)):
    try:
        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        # Delete image file if exists
        if person.image_url and person.image_url.startswith("/static/uploads/"):
            file_name = person.image_url.replace("/static/uploads/", "")
            local_path = os.path.join(UPLOAD_DIR, file_name)
            if os.path.exists(local_path):
                os.remove(local_path)

        db.delete(person) # Cascade deletes embedding
        db.commit()
        return SuccessResponse(message="Person deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))