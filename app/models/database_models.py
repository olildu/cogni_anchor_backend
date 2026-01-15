"""
Database Models for CogniAnchor Application
Pydantic models for data validation and API contracts
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ===== USER MODELS =====

class UserRole(str, Enum):
    """User roles in the system"""
    PATIENT = "patient"
    CARETAKER = "caretaker"

class UserCreate(BaseModel):
    """Model for creating a new user"""
    email: str
    password: str
    role: UserRole

class UserProfile(BaseModel):
    """User profile information"""
    id: str
    email: str
    role: UserRole
    pair_id: Optional[str] = None
    created_at: Optional[datetime] = None
    name: Optional[str] = None
    contact: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime] = None

class UserProfileUpdate(BaseModel):
    """Model for updating user profile details"""
    name: Optional[str] = None
    contact: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime] = None

# ===== PAIR MODELS =====

class PairCreate(BaseModel):
    """Model for creating a patient-caretaker pair"""
    patient_user_id: str
    caretaker_user_id: Optional[str] = None

class PairInfo(BaseModel):
    """Pair information"""
    id: str
    patient_user_id: str
    caretaker_user_id: Optional[str] = None
    created_at: Optional[datetime] = None

class PairConnection(BaseModel):
    """Model for connecting caretaker to patient via pair code"""
    pair_code: str
    caretaker_user_id: str

# ===== REMINDER MODELS =====

class ReminderCreate(BaseModel):
    """Model for creating a reminder"""
    pair_id: str
    title: str
    date: str  
    time: str  

class ReminderUpdate(BaseModel):
    """Model for updating a reminder"""
    title: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None

class ReminderInfo(BaseModel):
    """Reminder information"""
    id: int
    pair_id: str
    title: str
    date: str
    time: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ReminderListResponse(BaseModel):
    """Response model for listing reminders"""
    reminders: List[ReminderInfo]
    count: int

# ===== FACE RECOGNITION MODELS =====

class PersonCreate(BaseModel):
    """Model for adding a person to face recognition database"""
    pair_id: str
    name: str
    relationship: str
    occupation: str
    age: Optional[int] = None
    notes: Optional[str] = None
    embedding: List[float]

class PersonUpdate(BaseModel):
    """Model for updating person information"""
    name: Optional[str] = None
    relationship: Optional[str] = None
    occupation: Optional[str] = None
    age: Optional[int] = None
    notes: Optional[str] = None
    embedding: Optional[List[float]] = None

class PersonInfo(BaseModel):
    """Person information"""
    id: str 
    pair_id: str
    name: str
    relationship: str
    occupation: str
    age: Optional[int] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PersonWithEmbedding(PersonInfo):
    """Person information with face embedding"""
    embedding: List[float]

class FaceScanRequest(BaseModel):
    """Model for face scanning/matching request"""
    pair_id: str
    embedding: List[float]

class FaceScanResponse(BaseModel):
    """Response model for face scanning"""
    matched: bool
    score: Optional[float] = None
    person: Optional[PersonInfo] = None

class PeopleListResponse(BaseModel):
    """Response model for listing people"""
    people: List[PersonInfo]
    count: int

# ===== PATIENT STATUS & LOCATION MODELS =====

class PatientStatusUpdate(BaseModel):
    location_permission: Optional[bool] = None
    mic_permission: Optional[bool] = None
    location_toggle_on: Optional[bool] = None
    mic_toggle_on: Optional[bool] = None
    is_logged_in: Optional[bool] = None
    last_active_at: Optional[datetime] = None

class PatientStatusInfo(BaseModel):
    patient_user_id: str
    location_permission: bool
    mic_permission: bool
    location_toggle_on: bool
    mic_toggle_on: bool
    is_logged_in: bool
    last_active_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LocationUpdate(BaseModel):
    pair_id: str
    latitude: float
    longitude: float

class LocationInfo(BaseModel):
    patient_user_id: str
    latitude: float
    longitude: float
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ===== GENERIC RESPONSE MODELS =====

class SuccessResponse(BaseModel):
    ok: bool = True
    message: str

class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    detail: Optional[str] = None