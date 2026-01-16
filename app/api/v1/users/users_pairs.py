"""
User and Pair Management API Endpoints
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends, Body
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.sql_models import User, Pair
from app.models.database_models import (
    UserCreate,
    UserProfile,
    UserProfileUpdate,
    PairInfo,
    PairConnection
)
from app.core.security import get_password_hash, verify_password

logger = logging.getLogger("UsersPairsAPI")
router = APIRouter(prefix="/api/v1", tags=["Users & Pairs"])

# --- Models for this router ---
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class FCMTokenRequest(BaseModel):
    fcm_token: str

# ===== USER ENDPOINTS =====

@router.post("/users/signup", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def signup_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Creating new user: {user.email}")
        existing = db.query(User).filter(User.email == user.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        db_user = User(
            email=user.email,
            hashed_password=get_password_hash(user.password),
            role=user.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        pair_id = None
        if user.role == "patient":
            db_pair = Pair(patient_user_id=db_user.id)
            db.add(db_pair)
            db.commit()
            db.refresh(db_pair)
            pair_id = str(db_pair.id)

        return UserProfile(
            id=str(db_user.id),
            email=db_user.email,
            role=db_user.role,
            pair_id=pair_id,
            created_at=db_user.created_at
        )
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/login", response_model=UserProfile)
async def login_user(email: str = Body(...), password: str = Body(...), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        pair_id = None
        if user.role == "patient":
            pair = db.query(Pair).filter(Pair.patient_user_id == user.id).first()
            if pair: pair_id = str(pair.id)
        else:
            pair = db.query(Pair).filter(Pair.caretaker_user_id == user.id).first()
            if pair: pair_id = str(pair.id)

        return UserProfile(
            id=str(user.id),
            email=user.email,
            role=user.role,
            pair_id=pair_id,
            created_at=user.created_at,
            name=user.name,
            contact=user.contact,
            gender=user.gender,
            date_of_birth=user.date_of_birth
        )
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/fcm-token")
async def update_fcm_token(user_id: str, request: FCMTokenRequest, db: Session = Depends(get_db)):
    """Update user FCM token for notifications"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.fcm_token = request.fcm_token
        db.commit()
        return {"message": "FCM token updated successfully"}
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Error updating FCM token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    """Get full user profile including profile fields"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        pair_id = None
        if user.role == "patient":
            pair = db.query(Pair).filter(Pair.patient_user_id == user.id).first()
            if pair: pair_id = str(pair.id)
        else:
            pair = db.query(Pair).filter(Pair.caretaker_user_id == user.id).first()
            if pair: pair_id = str(pair.id)

        return UserProfile(
            id=str(user.id),
            email=user.email,
            role=user.role,
            pair_id=pair_id,
            created_at=user.created_at,
            name=user.name,
            contact=user.contact,
            gender=user.gender,
            date_of_birth=user.date_of_birth
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}")
async def update_user_profile(user_id: str, update: UserProfileUpdate, db: Session = Depends(get_db)):
    """Update user profile fields"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if update.name is not None: user.name = update.name
        if update.contact is not None: user.contact = update.contact
        if update.gender is not None: user.gender = update.gender
        if update.date_of_birth is not None: user.date_of_birth = update.date_of_birth

        db.commit()
        return {"message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}/password")
async def change_password(user_id: str, req: PasswordChangeRequest, db: Session = Depends(get_db)):
    """Change user password"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(req.current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        user.hashed_password = get_password_hash(req.new_password)
        db.commit()
        return {"message": "Password changed successfully"}
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== PAIR ENDPOINTS =====

@router.get("/pairs/{pair_id}", response_model=PairInfo)
async def get_pair_info(pair_id: str, db: Session = Depends(get_db)):
    try:
        pair = db.query(Pair).filter(Pair.id == pair_id).first()
        if not pair:
            raise HTTPException(status_code=404, detail="Pair not found")
        
        # FIX: Explicitly cast UUIDs to strings to satisfy Pydantic strict typing
        return PairInfo(
            id=str(pair.id),
            patient_user_id=str(pair.patient_user_id),
            caretaker_user_id=str(pair.caretaker_user_id) if pair.caretaker_user_id else None,
            created_at=pair.created_at
        )
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pairs/connect", response_model=PairInfo)
async def connect_pair(connection: PairConnection, db: Session = Depends(get_db)):
    try:
        pair_id = connection.pair_code
        pair = db.query(Pair).filter(Pair.id == pair_id).first()
        
        if not pair:
            raise HTTPException(status_code=404, detail="Invalid Pair Code")
        
        if pair.caretaker_user_id:
             raise HTTPException(status_code=400, detail="This patient is already connected to a caretaker")

        pair.caretaker_user_id = connection.caretaker_user_id
        db.commit()
        db.refresh(pair)

        # FIX: Explicitly cast UUIDs to strings
        return PairInfo(
            id=str(pair.id),
            patient_user_id=str(pair.patient_user_id),
            caretaker_user_id=str(pair.caretaker_user_id) if pair.caretaker_user_id else None,
            created_at=pair.created_at
        )
    except HTTPException: raise
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))