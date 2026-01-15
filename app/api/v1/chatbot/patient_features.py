"""
Patient Status & Features API
Handles permissions, toggles, and live status updates
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.sql_models import PatientStatus
from app.models.database_models import PatientStatusUpdate, PatientStatusInfo

logger = logging.getLogger("PatientFeaturesAPI")
router = APIRouter(prefix="/api/v1/patient", tags=["Patient Status"])

@router.put("/status")
async def update_status(status_update: PatientStatusUpdate, user_id: str, db: Session = Depends(get_db)):
    """
    Update patient toggles (Location/Mic) and permissions.
    """
    try:
        # Check if status record exists
        status_record = db.query(PatientStatus).filter(PatientStatus.patient_user_id == user_id).first()
        
        if not status_record:
            # Create if doesn't exist
            status_record = PatientStatus(patient_user_id=user_id)
            db.add(status_record)
        
        # Update fields if provided
        if status_update.location_toggle_on is not None:
            status_record.location_toggle_on = status_update.location_toggle_on
        if status_update.mic_toggle_on is not None:
            status_record.mic_toggle_on = status_update.mic_toggle_on
        if status_update.location_permission is not None:
            status_record.location_permission = status_update.location_permission
        if status_update.mic_permission is not None:
            status_record.mic_permission = status_update.mic_permission
        if status_update.is_logged_in is not None:
            status_record.is_logged_in = status_update.is_logged_in
            
        db.commit()
        return {"message": "Status updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{user_id}", response_model=PatientStatusInfo)
async def get_status(user_id: str, db: Session = Depends(get_db)):
    """Get current patient status"""
    try:
        status_record = db.query(PatientStatus).filter(PatientStatus.patient_user_id == user_id).first()
        
        if not status_record:
            return PatientStatusInfo(
                patient_user_id=user_id, 
                location_permission=False,
                mic_permission=False,
                location_toggle_on=False, 
                mic_toggle_on=False,
                is_logged_in=False,
                last_active_at=None
            )
        
        return PatientStatusInfo(
            patient_user_id=str(status_record.patient_user_id),
            location_permission=status_record.location_permission,
            mic_permission=status_record.mic_permission,
            location_toggle_on=status_record.location_toggle_on,
            mic_toggle_on=status_record.mic_toggle_on,
            is_logged_in=status_record.is_logged_in,
            last_active_at=status_record.last_active_at
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))