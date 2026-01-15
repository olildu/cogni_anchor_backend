"""
Agent Tools for LangGraph Agent
Provides tools for reminder management and emergency alerts (PostgreSQL Version)
"""

import logging
import re
from datetime import datetime
from langchain_core.tools import tool

from app.core.database import SessionLocal
from app.models.sql_models import Reminder, EmergencyAlert

logger = logging.getLogger("AgentTools")

def parse_flexible_datetime(date_str: str, time_str: str) -> str:
    """
    Helper to parse natural language dates (e.g. '11th January') into required DB format.
    Returns: Tuple (formatted_date, formatted_time) or raises ValueError
    """
    # 1. Remove ordinal suffixes (st, nd, rd, th) from the date string
    # Matches numbers followed by suffixes (e.g., 11th -> 11)
    clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    
    dt_str = f"{clean_date} {time_str}"
    
    # 2. List of supported formats
    formats = [
        "%d %b %Y %I:%M %p", # 11 Jan 2026 05:00 PM (Ideal)
        "%d %B %Y %I:%M %p", # 11 January 2026 05:00 PM
        "%d %b %Y %H:%M",    # 11 Jan 2026 17:00
        "%d %B %Y %H:%M",    # 11 January 2026 17:00
    ]
    
    # 3. Try parsing with current year if year is missing
    current_year = datetime.now().year
    formats_without_year = [
        "%d %b %I:%M %p",    # 11 Jan 05:00 PM
        "%d %B %I:%M %p",    # 11 January 05:00 PM
    ]

    parsed_dt = None

    # Try full formats
    for fmt in formats:
        try:
            parsed_dt = datetime.strptime(dt_str, fmt)
            break
        except ValueError:
            continue
            
    # Try formats without year
    if not parsed_dt:
        for fmt in formats_without_year:
            try:
                temp_dt = datetime.strptime(dt_str, fmt)
                parsed_dt = temp_dt.replace(year=current_year)
                break
            except ValueError:
                continue

    if not parsed_dt:
        raise ValueError(f"Could not parse date/time: {date_str} {time_str}")

    # 4. Convert back to the strictly required format for the DB/App
    return parsed_dt.strftime("%d %b %Y"), parsed_dt.strftime("%I:%M %p")

@tool
def create_reminder(pair_id: str, title: str, date: str, time: str) -> str:
    """
    Create a new reminder. 
    Args:
        pair_id: The pair ID provided in context.
        title: Title of the reminder.
        date: Date string (e.g. '11 Jan 2026' or '11th January').
        time: Time string (e.g. '5:00 PM').
    """
    db = SessionLocal()
    try:
        logger.info(f"Creating reminder request: {title} on {date} at {time}")

        # Use flexible parser
        try:
            fmt_date, fmt_time = parse_flexible_datetime(date, time)
        except ValueError as e:
            return f"Error: Invalid date format. Please use format like '25 Jan 2026' and '5:00 PM'."

        # Create SQL record
        db_reminder = Reminder(
            pair_id=pair_id,
            title=title,
            date=fmt_date,
            time=fmt_time
        )
        db.add(db_reminder)
        db.commit()
        db.refresh(db_reminder)

        logger.info(f"Reminder created: {title} ({fmt_date} {fmt_time})")
        return f"Reminder created successfully! I'll remind you about '{title}' on {fmt_date} at {fmt_time}."

    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        return f"Error: Failed to create reminder - {str(e)}"
    finally:
        db.close()

@tool
def list_reminders(pair_id: str) -> str:
    """
    List all upcoming (non-expired) reminders for the patient.
    """
    db = SessionLocal()
    try:
        reminders = db.query(Reminder).filter(Reminder.pair_id == pair_id).all()

        if not reminders:
            return "You don't have any reminders set right now."

        now = datetime.now()
        upcoming_reminders = []

        for r in reminders:
            try:
                # Flexible parsing for reading from DB (just in case)
                # But standard DB format is "%d %b %Y %I:%M %p"
                dt_str = f"{r.date} {r.time}"
                reminder_dt = datetime.strptime(dt_str, "%d %b %Y %I:%M %p")
                
                if reminder_dt >= now:
                    upcoming_reminders.append(r)
            except:
                continue

        if not upcoming_reminders:
            return "All your reminders have passed. You don't have any upcoming reminders."

        reminder_list = []
        for idx, r in enumerate(upcoming_reminders, 1):
            reminder_list.append(f"{idx}. {r.title} - {r.date} at {r.time}")

        return f"You have {len(upcoming_reminders)} upcoming reminder(s):\n" + "\n".join(reminder_list)

    except Exception as e:
        logger.error(f"Error fetching reminders: {e}")
        return "Error fetching reminders."
    finally:
        db.close()

@tool
def delete_reminder(pair_id: str, reminder_title: str) -> str:
    """Delete a reminder by searching for its title."""
    db = SessionLocal()
    try:
        reminders = db.query(Reminder).filter(Reminder.pair_id == pair_id).all()
        
        matching = [r for r in reminders if reminder_title.lower() in r.title.lower()]

        if not matching:
            return f"I couldn't find a reminder matching '{reminder_title}'."

        to_delete = matching[0]
        db.delete(to_delete)
        db.commit()
        return f"I've deleted the reminder '{to_delete.title}'."
    except Exception as e:
        return f"Error deleting reminder: {str(e)}"
    finally:
        db.close()

@tool
def send_emergency_alert(pair_id: str, reason: str) -> str:
    """Send an emergency alert to the patient's caregiver."""
    db = SessionLocal()
    try:
        new_alert = EmergencyAlert(pair_id=pair_id, alert_type="emergency", reason=reason, status="pending")
        db.add(new_alert)
        db.commit()
        return "I've notified your caregiver. Help is on the way."
    except Exception as e:
        return "I'm here with you. Let me help you feel safe."
    finally:
        db.close()