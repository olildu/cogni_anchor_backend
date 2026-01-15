import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.sql_models import Reminder, Pair, User
from app.services.notification.firebase_service import send_multicast_notification
from app.services.infra.websocket_manager import reminder_manager

logger = logging.getLogger("Scheduler")

scheduler = AsyncIOScheduler()

async def check_reminders_job():
    """Runs every minute to check for due reminders."""
    db: Session = SessionLocal()
    try:
        now = datetime.now()
        # DB stores dates as strings, so we match that format
        current_date_str = now.strftime("%d %b %Y")
        current_time_str = now.strftime("%I:%M %p")

        due_reminders = db.query(Reminder).filter(
            Reminder.date == current_date_str,
            Reminder.time == current_time_str
        ).all()

        if not due_reminders:
            return

        logger.info(f"Found {len(due_reminders)} reminders due at {current_time_str}")

        for reminder in due_reminders:
            await _process_due_reminder(db, reminder)

    except Exception as e:
        logger.error(f"Scheduler Error: {e}")
    finally:
        db.close()

async def _process_due_reminder(db: Session, reminder: Reminder):
    try:
        pair = db.query(Pair).filter(Pair.id == reminder.pair_id).first()
        if not pair:
            return

        tokens = []

        # Collect FCM tokens for both patient and caretaker
        if pair.patient_user_id:
            patient = db.query(User).filter(User.id == pair.patient_user_id).first()
            if patient and patient.fcm_token:
                tokens.append(patient.fcm_token)

        if pair.caretaker_user_id:
            caretaker = db.query(User).filter(User.id == pair.caretaker_user_id).first()
            if caretaker and caretaker.fcm_token:
                tokens.append(caretaker.fcm_token)

        # Push notification
        if tokens:
            logger.info(f"Sending reminder '{reminder.title}' to {len(tokens)} device(s)")
            send_multicast_notification(
                tokens=tokens,
                title="Reminder",
                body=f"It's time for: {reminder.title}",
                data={
                    "type": "new_reminder", 
                    "title": reminder.title,
                    "date": reminder.date,
                    "time": reminder.time,
                    "id": str(reminder.id)
                }
            )

        # Notify frontend to remove the expired item from the list
        await reminder_manager.broadcast_json(
            {"type": "EXPIRED", "id": reminder.id},
            reminder.pair_id
        )

    except Exception as e:
        logger.error(f"Failed to process reminder {reminder.id}: {e}")

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(check_reminders_job, 'interval', seconds=60)
        scheduler.start()
        logger.info("Reminder Scheduler Started")

def shutdown_scheduler(): 
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Reminder Scheduler Stopped")