"""
Face Recognition API Endpoints
Handles face detection, person enrollment, scanning, and matching
Consolidated to support both client-side and server-side embeddings.
"""

import logging
import os
import uuid
import json
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from typing import List, Optional

from app.models.database_models import (
    PersonInfo,
    FaceScanRequest,
    FaceScanResponse,
    PeopleListResponse,
    SuccessResponse
)
from app.services.supabase_client import get_supabase_client
from app.services.face_recognition_service import get_face_recognition_service

logger = logging.getLogger("FaceRecognitionAPI")
router = APIRouter(prefix="/api/v1/face", tags=["Face Recognition"])

# Temporary directory for image processing
TEMP_DIR = "temp/face_images"
os.makedirs(TEMP_DIR, exist_ok=True)

# ===== HELPER FUNCTIONS =====

async def save_uploaded_image(image: UploadFile) -> str:
    """Save uploaded image to temporary location"""
    try:
        # Generate unique filename
        ext = image.filename.split(".")[-1] if "." in image.filename else "jpg"
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(TEMP_DIR, filename)

        # Save image
        contents = await image.read()
        with open(filepath, "wb") as f:
            f.write(contents)

        logger.info(f"Saved uploaded image to {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Error saving uploaded image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save image: {str(e)}"
        )

async def upload_to_supabase_storage(filepath: str, pair_id: str, person_name: str) -> str:
    """Upload image to Supabase Storage"""
    try:
        # ✅ FIX: Use service key to bypass RLS policies for uploads
        supabase = get_supabase_client(use_service_key=True)

        # Generate storage path
        filename = os.path.basename(filepath)
        storage_path = f"{pair_id}/{person_name}_{filename}"

        # Read image file
        with open(filepath, "rb") as f:
            image_data = f.read()

        # Upload to Supabase Storage
        supabase.storage.from_("face-images").upload(
            path=storage_path,
            file=image_data,
            file_options={"content-type": "image/jpeg"}
        )

        # Get public URL
        public_url = supabase.storage.from_("face-images").get_public_url(storage_path)

        logger.info(f"Uploaded image to Supabase Storage: {storage_path}")
        return public_url

    except Exception as e:
        logger.error(f"Error uploading to Supabase Storage: {e}")
        # Return local path as fallback (or handle error appropriately)
        return filepath

# ===== API ENDPOINTS =====

@router.post("/addPerson", response_model=PersonInfo, status_code=status.HTTP_201_CREATED)
async def add_person(
    pair_id: str = Form(...),
    name: str = Form(...),
    relationship: str = Form(...),
    occupation: str = Form(...),
    age: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    embedding: Optional[str] = Form(None),  # JSON string from Flutter
    image: UploadFile = File(...)
):
    """
    Add a person to face recognition database.
    Accepts 'embedding' as a JSON string (Client-side generation) OR generates it Server-side.
    """
    temp_filepath = None
    try:
        logger.info(f"Adding person {name} for pair {pair_id}")

        # 1. Save uploaded image locally first
        temp_filepath = await save_uploaded_image(image)

        # 2. Handle Embedding Strategy
        final_embedding = None
        
        if embedding:
            # A: Client provided the embedding (Node.js style)
            try:
                final_embedding = json.loads(embedding)
                logger.info(f"Using client-provided embedding (dim: {len(final_embedding)})")
            except json.JSONDecodeError:
                logger.warning("Failed to parse client embedding JSON")

        if not final_embedding:
            # B: Fallback to Server-side generation (Python style)
            logger.info("Generating embedding server-side...")
            face_service = get_face_recognition_service()
            final_embedding = face_service.generate_embedding(temp_filepath)

        if not final_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No face detected in image and no valid embedding provided."
            )

        # 3. Upload image to Supabase Storage
        image_url = await upload_to_supabase_storage(temp_filepath, pair_id, name)

        supabase = get_supabase_client()

        # 4. Insert person into database
        person_result = supabase.table("people").insert({
            "pair_id": pair_id,
            "name": name,
            "relationship": relationship,
            "occupation": occupation,
            "age": age,
            "notes": notes,
            "image_url": image_url
        }).execute()

        if not person_result.data:
            raise HTTPException(status_code=500, detail="Failed to add person record")

        person_id = person_result.data[0]["id"]

        # 5. Insert face embedding
        supabase.table("face_embeddings").insert({
            "person_id": person_id,
            "embedding": final_embedding
        }).execute()

        logger.info(f"Person {name} added successfully with ID {person_id}")
        return PersonInfo(**person_result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding person: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add person: {str(e)}")
    finally:
        # Clean up temp file
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)

@router.get("/getPeople", response_model=PeopleListResponse)
async def get_people(pair_id: str):
    """Get all people for a pair"""
    try:
        logger.info(f"Fetching people for pair {pair_id}")
        supabase = get_supabase_client()

        result = supabase.table("people").select("*").eq("pair_id", pair_id).execute()
        people = [PersonInfo(**person) for person in result.data]

        return PeopleListResponse(people=people, count=len(people))
    except Exception as e:
        logger.error(f"Error fetching people: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch people: {str(e)}")

@router.post("/scan", response_model=FaceScanResponse)
async def scan_face(scan_request: FaceScanRequest):
    """
    Scan and match a face against database using embedding.
    Compatible with both 192-dim (Client) and 512-dim (Server) embeddings,
    as long as the database contains the same type.
    """
    try:
        logger.info(f"Scanning face for pair {scan_request.pair_id}")
        supabase = get_supabase_client()

        # 1. Get all people for this pair
        people_result = supabase.table("people").select("*").eq("pair_id", scan_request.pair_id).execute()
        if not people_result.data:
            return FaceScanResponse(matched=False)

        # 2. Get embeddings for these people
        database_embeddings = []
        for person in people_result.data:
            person_id = person["id"]
            # Fetch embedding
            emb_res = supabase.table("face_embeddings").select("embedding").eq("person_id", person_id).execute()
            if emb_res.data:
                # We assume 1 embedding per person for simplicity here
                db_emb = emb_res.data[0]["embedding"]
                database_embeddings.append((person_id, db_emb))

        if not database_embeddings:
            return FaceScanResponse(matched=False)

        # 3. Find best match
        face_service = get_face_recognition_service()
        match_result = face_service.find_best_match(
            query_embedding=scan_request.embedding,
            database_embeddings=database_embeddings,
            threshold=0.6
        )

        if not match_result:
            return FaceScanResponse(matched=False)

        person_id, score = match_result
        person = next((p for p in people_result.data if p["id"] == person_id), None)

        if not person:
            return FaceScanResponse(matched=False)

        return FaceScanResponse(matched=True, score=score, person=PersonInfo(**person))

    except Exception as e:
        logger.error(f"Error scanning face: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scan face: {str(e)}")

@router.post("/scanImage", response_model=FaceScanResponse)
async def scan_face_from_image(pair_id: str = Form(...), image: UploadFile = File(...)):
    """Server-side scanning endpoint (backup for client-side scanning)"""
    temp_filepath = None
    try:
        temp_filepath = await save_uploaded_image(image)
        face_service = get_face_recognition_service()
        embedding = face_service.generate_embedding(temp_filepath)

        if not embedding:
            return FaceScanResponse(matched=False)

        scan_req = FaceScanRequest(pair_id=pair_id, embedding=embedding)
        return await scan_face(scan_req)

    except Exception as e:
        logger.error(f"Error scanning from image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scan: {str(e)}")
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)

@router.put("/updatePerson", response_model=PersonInfo)
async def update_person(
    person_id: str = Form(...),  # ✅ CHANGED: int -> str (UUID)
    name: Optional[str] = Form(None),
    relationship: Optional[str] = Form(None),
    occupation: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    """Update person information"""
    temp_filepath = None
    try:
        supabase = get_supabase_client()
        update_data = {}
        if name: update_data["name"] = name
        if relationship: update_data["relationship"] = relationship
        if occupation: update_data["occupation"] = occupation
        if age: update_data["age"] = age
        if notes: update_data["notes"] = notes

        if image:
            person_res = supabase.table("people").select("pair_id, name").eq("id", person_id).single().execute()
            if person_res.data:
                # ✅ FIX: Use service key for image upload here too
                temp_filepath = await save_uploaded_image(image)
                
                # Upload with service key
                supabase_admin = get_supabase_client(use_service_key=True)
                filename = os.path.basename(temp_filepath)
                storage_path = f"{person_res.data['pair_id']}/{person_res.data['name']}_{filename}"
                
                with open(temp_filepath, "rb") as f:
                    supabase_admin.storage.from_("face-images").upload(
                        path=storage_path,
                        file=f.read(),
                        file_options={"content-type": "image/jpeg"}
                    )
                
                image_url = supabase_admin.storage.from_("face-images").get_public_url(storage_path)
                update_data["image_url"] = image_url

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = supabase.table("people").update(update_data).eq("id", person_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Person not found")

        return PersonInfo(**result.data[0])

    except Exception as e:
        logger.error(f"Error updating person: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update: {str(e)}")
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)

@router.delete("/deletePerson", response_model=SuccessResponse)
async def delete_person(person_id: str): # ✅ CHANGED: int -> str (UUID)
    """Delete a person"""
    try:
        supabase = get_supabase_client()
        # Delete embeddings first (FK constraint)
        supabase.table("face_embeddings").delete().eq("person_id", person_id).execute()
        # Delete person
        result = supabase.table("people").delete().eq("id", person_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Person not found")

        return SuccessResponse(message="Person deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting person: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")