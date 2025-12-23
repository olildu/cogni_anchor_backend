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
    date: str  # Format: dd MMM yyyy (e.g., "25 Dec 2024")
    time: str  # Format: hh:mm a (e.g., "02:30 PM")

class ReminderUpdate(BaseModel):
    """Model for updating a reminder"""
    title: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None

class ReminderInfo(BaseModel):
    """Reminder information"""
    id: int # Keep as int if reminders table uses SERIAL/BIGINT, change to str if using UUIDs
    pair_id: str
    title: str
    date: str
    time: str
    created_at: Optional[datetime] = None

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
    embedding: List[float]  # 192-dimensional face embedding vector

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
    id: str # ✅ CHANGED: from int to str (to support UUIDs)
    pair_id: str
    name: str
    relationship: str
    occupation: str
    age: Optional[int] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

class PersonWithEmbedding(PersonInfo):
    """Person information with face embedding"""
    embedding: List[float]

class FaceScanRequest(BaseModel):
    """Model for face scanning/matching request"""
    pair_id: str
    embedding: List[float]  # Face embedding to match

class FaceScanResponse(BaseModel):
    """Response model for face scanning"""
    matched: bool
    score: Optional[float] = None  # Cosine similarity score (0-1)
    person: Optional[PersonInfo] = None

class PeopleListResponse(BaseModel):
    """Response model for listing people"""
    people: List[PersonInfo]
    count: int

# ===== GENERIC RESPONSE MODELS =====

class SuccessResponse(BaseModel):
    """Generic success response"""
    ok: bool = True
    message: str

class ErrorResponse(BaseModel):
    """Generic error response"""
    ok: bool = False
    error: str
    detail: Optional[str] = None