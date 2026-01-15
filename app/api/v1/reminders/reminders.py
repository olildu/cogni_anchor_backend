import logging
from fastapi import APIRouter, HTTPException, status, Depends, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.database_models import (
    ReminderCreate,
    ReminderUpdate,
    ReminderInfo,
    ReminderListResponse,
    SuccessResponse
)
from app.core.database import get_db
from app.models.sql_models import Reminder
from app.services.infra.websocket_manager import reminder_manager

logger = logging.getLogger("RemindersAPI")
router = APIRouter(prefix="/api/v1/reminders", tags=["Reminders"])

# --- Helpers ---

def parse_reminder_datetime(date_str: str, time_str: str) -> datetime:
    try:
        datetime_str = f"{date_str} {time_str}"
        return datetime.strptime(datetime_str, "%d %b %Y %I:%M %p")
    except Exception as e:
        logger.error(f"Error parsing datetime: {e}")
        raise ValueError(f"Invalid date/time format: {e}")

def is_reminder_expired(date_str: str, time_str: str) -> bool:
    try:
        reminder_dt = parse_reminder_datetime(date_str, time_str)
        return reminder_dt < datetime.now()
    except:
        return False

# --- WebSockets ---

@router.websocket("/ws/{pair_id}")
async def ws_reminders(websocket: WebSocket, pair_id: str):
    """Real-time connection for reminder updates."""
    await reminder_manager.connect(websocket, pair_id)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        reminder_manager.disconnect(websocket, pair_id)
    except Exception as e:
        logger.error(f"Reminder WS Error: {e}")
        reminder_manager.disconnect(websocket, pair_id)


# --- HTTP Endpoints ---

@router.post("/", response_model=ReminderInfo, status_code=status.HTTP_201_CREATED)
async def create_reminder(reminder: ReminderCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Creating reminder for pair {reminder.pair_id}: {reminder.title}")

        try:
            parse_reminder_datetime(reminder.date, reminder.time)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        db_reminder = Reminder(
            pair_id=reminder.pair_id,
            title=reminder.title,
            date=reminder.date,
            time=reminder.time
        )
        
        db.add(db_reminder)
        db.commit()
        db.refresh(db_reminder)

        # Notify connected clients
        reminder_data = jsonable_encoder(ReminderInfo.from_orm(db_reminder))
        await reminder_manager.broadcast_json(
            {"type": "ADD", "data": reminder_data}, 
            reminder.pair_id
        )

        logger.info(f"Reminder created with ID: {db_reminder.id}")
        return db_reminder

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reminder: {str(e)}"
        )

@router.get("/{pair_id}", response_model=ReminderListResponse)
async def get_reminders(pair_id: str, include_expired: bool = False, db: Session = Depends(get_db)):
    try:
        logger.info(f"Fetching reminders for pair {pair_id}")

        query = db.query(Reminder).filter(Reminder.pair_id == pair_id)
        reminders_data = query.order_by(Reminder.id.desc()).all()

        reminders = [ReminderInfo.from_orm(r) for r in reminders_data]

        if not include_expired:
            reminders = [r for r in reminders if not is_reminder_expired(r.date, r.time)]

        logger.info(f"Found {len(reminders)} reminder(s)")

        return ReminderListResponse(
            reminders=reminders,
            count=len(reminders)
        )

    except Exception as e:
        logger.error(f"Error fetching reminders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch reminders: {str(e)}")

@router.get("/reminder/{reminder_id}", response_model=ReminderInfo)
async def get_reminder(reminder_id: int, db: Session = Depends(get_db)):
    try:
        reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            raise HTTPException(status_code=404, detail=f"Reminder {reminder_id} not found")
        return reminder
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch reminder: {str(e)}")

@router.put("/{reminder_id}", response_model=ReminderInfo)
async def update_reminder(reminder_id: int, reminder_update: ReminderUpdate, db: Session = Depends(get_db)):
    try:
        db_reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not db_reminder:
            raise HTTPException(status_code=404, detail=f"Reminder {reminder_id} not found")

        # Validate new date/time if provided
        date_to_check = reminder_update.date or db_reminder.date
        time_to_check = reminder_update.time or db_reminder.time

        if reminder_update.date or reminder_update.time:
            try:
                parse_reminder_datetime(date_to_check, time_to_check)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        if reminder_update.title is not None:
            db_reminder.title = reminder_update.title
        if reminder_update.date is not None:
            db_reminder.date = reminder_update.date
        if reminder_update.time is not None:
            db_reminder.time = reminder_update.time

        db.commit()
        db.refresh(db_reminder)
        
        # Real-time update
        await reminder_manager.broadcast_json(
            {"type": "UPDATE", "data": jsonable_encoder(ReminderInfo.from_orm(db_reminder))}, 
            db_reminder.pair_id
        )

        logger.info(f"Reminder {reminder_id} updated")
        return db_reminder

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update reminder: {str(e)}")

@router.delete("/{reminder_id}", response_model=SuccessResponse)
async def delete_reminder(reminder_id: int, db: Session = Depends(get_db)):
    try:
        db_reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not db_reminder:
            raise HTTPException(status_code=404, detail=f"Reminder {reminder_id} not found")

        pair_id = db_reminder.pair_id
        db.delete(db_reminder)
        db.commit()

        # Real-time delete
        await reminder_manager.broadcast_json(
            {"type": "DELETE", "id": reminder_id}, 
            pair_id
        )

        logger.info(f"Reminder {reminder_id} deleted")
        return SuccessResponse(message=f"Reminder {reminder_id} deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete reminder: {str(e)}")

@router.delete("/{pair_id}/expired", response_model=SuccessResponse)
async def delete_expired_reminders(pair_id: str, db: Session = Depends(get_db)):
    try:
        logger.info(f"Cleaning up expired reminders for {pair_id}")

        reminders = db.query(Reminder).filter(Reminder.pair_id == pair_id).all()
        
        expired_count = 0
        deleted_ids = []

        for reminder in reminders:
            if is_reminder_expired(reminder.date, reminder.time):
                deleted_ids.append(reminder.id)
                db.delete(reminder)
                expired_count += 1
        
        if expired_count > 0:
            db.commit()
            # Notify clients to remove these IDs
            for rid in deleted_ids:
                 await reminder_manager.broadcast_json(
                    {"type": "DELETE", "id": rid}, 
                    pair_id
                )

        if expired_count == 0:
            return SuccessResponse(message="No expired reminders found")

        logger.info(f"Deleted {expired_count} expired reminder(s)")
        return SuccessResponse(message=f"Deleted {expired_count} expired reminder(s)")

    except Exception as e:
        logger.error(f"Error deleting expired reminders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete expired reminders: {str(e)}")