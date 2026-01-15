from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from app.core.database import Base

# --- USER MANAGEMENT ---

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    fcm_token = Column(String, nullable=True)
    
    name = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    date_of_birth = Column(DateTime(timezone=True), nullable=True)

class Pair(Base):
    __tablename__ = "pairs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_user_id = Column(String, ForeignKey("users.id"), unique=True)
    caretaker_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- FEATURES ---

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    pair_id = Column(String, index=True)
    title = Column(String)
    date = Column(String) 
    time = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EmergencyAlert(Base):
    __tablename__ = "emergency_alerts"

    id = Column(Integer, primary_key=True, index=True)
    pair_id = Column(String, index=True)
    alert_type = Column(String)
    reason = Column(String)
    status = Column(String, default="pending")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

# --- FACE RECOGNITION ---

class Person(Base):
    __tablename__ = "people"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pair_id = Column(String, index=True)
    name = Column(String)
    relationship = Column(String)
    occupation = Column(String)
    age = Column(Integer)
    notes = Column(Text)
    image_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(String, ForeignKey("people.id", ondelete="CASCADE"))
    embedding = Column(ARRAY(Float))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- LIVE FEATURES ---

class PatientStatus(Base):
    __tablename__ = "patient_status"

    id = Column(Integer, primary_key=True, index=True)
    patient_user_id = Column(String, ForeignKey("users.id"), unique=True)
    
    location_permission = Column(Boolean, default=False)
    mic_permission = Column(Boolean, default=False)
    location_toggle_on = Column(Boolean, default=False)
    mic_toggle_on = Column(Boolean, default=False)
    is_logged_in = Column(Boolean, default=False)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now())

class LiveLocation(Base):
    __tablename__ = "live_location"

    id = Column(Integer, primary_key=True, index=True)
    pair_id = Column(String, index=True)
    patient_user_id = Column(String, ForeignKey("users.id"), unique=True)
    latitude = Column(Float)
    longitude = Column(Float)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())