"""
Reminder Management API Endpoints
Handles CRUD operations for reminders
"""

import logging
from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime

from app.models.database_models import (
    ReminderCreate,
    ReminderUpdate,
    ReminderInfo,
    ReminderListResponse,
    SuccessResponse
)
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger("RemindersAPI")
router = APIRouter(prefix="/api/v1/reminders", tags=["Reminders"])

# === Helper Functions ===

def parse_reminder_datetime(date_str: str, time_str: str) -> datetime:
    """
    Parse reminder date and time strings to datetime object

    Args:
        date_str: Date in format 'dd MMM yyyy' (e.g., '25 Dec 2024')
        time_str: Time in format 'hh:mm a' (e.g., '02:30 PM')

    Returns:
        datetime object
    """
    try:
        datetime_str = f"{date_str} {time_str}"
        return datetime.strptime(datetime_str, "%d %b %Y %I:%M %p")
    except Exception as e:
        logger.error(f"Error parsing datetime: {e}")
        raise ValueError(f"Invalid date/time format: {e}")

def is_reminder_expired(date_str: str, time_str: str) -> bool:
    """Check if reminder is expired"""
    try:
        reminder_dt = parse_reminder_datetime(date_str, time_str)
        return reminder_dt < datetime.now()
    except:
        return False

# === API Endpoints ===

@router.post("/", response_model=ReminderInfo, status_code=status.HTTP_201_CREATED)
async def create_reminder(reminder: ReminderCreate):
    """
    Create a new reminder

    - **pair_id**: Patient-caretaker pair ID
    - **title**: Reminder title/description
    - **date**: Date in format 'dd MMM yyyy'
    - **time**: Time in format 'hh:mm a'
    """
    try:
        logger.info(f"Creating reminder for pair {reminder.pair_id}: {reminder.title}")

        # Validate date/time format
        try:
            parse_reminder_datetime(reminder.date, reminder.time)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        supabase = get_supabase_client()

        # Insert reminder into database
        result = supabase.table("reminders").insert({
            "pair_id": reminder.pair_id,
            "title": reminder.title,
            "date": reminder.date,
            "time": reminder.time
        }).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create reminder"
            )

        created_reminder = result.data[0]
        logger.info(f"Reminder created successfully with ID: {created_reminder['id']}")

        return ReminderInfo(**created_reminder)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reminder: {str(e)}"
        )

@router.get("/{pair_id}", response_model=ReminderListResponse)
async def get_reminders(pair_id: str, include_expired: bool = False):
    """
    Get all reminders for a pair

    - **pair_id**: Patient-caretaker pair ID
    - **include_expired**: Include expired reminders (default: False)
    """
    try:
        logger.info(f"Fetching reminders for pair {pair_id}")

        supabase = get_supabase_client()

        # Fetch reminders from database
        result = supabase.table("reminders") \
            .select("*") \
            .eq("pair_id", pair_id) \
            .order("date", desc=False) \
            .order("time", desc=False) \
            .execute()

        reminders = [ReminderInfo(**reminder) for reminder in result.data]

        # Filter out expired reminders if requested
        if not include_expired:
            reminders = [
                r for r in reminders
                if not is_reminder_expired(r.date, r.time)
            ]

        logger.info(f"Found {len(reminders)} reminder(s) for pair {pair_id}")

        return ReminderListResponse(
            reminders=reminders,
            count=len(reminders)
        )

    except Exception as e:
        logger.error(f"Error fetching reminders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch reminders: {str(e)}"
        )

@router.get("/reminder/{reminder_id}", response_model=ReminderInfo)
async def get_reminder(reminder_id: int):
    """
    Get a specific reminder by ID

    - **reminder_id**: Reminder ID
    """
    try:
        logger.info(f"Fetching reminder {reminder_id}")

        supabase = get_supabase_client()

        result = supabase.table("reminders") \
            .select("*") \
            .eq("id", reminder_id) \
            .execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reminder {reminder_id} not found"
            )

        return ReminderInfo(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch reminder: {str(e)}"
        )

@router.put("/{reminder_id}", response_model=ReminderInfo)
async def update_reminder(reminder_id: int, reminder: ReminderUpdate):
    """
    Update a reminder

    - **reminder_id**: Reminder ID
    - **title**: New title (optional)
    - **date**: New date (optional)
    - **time**: New time (optional)
    """
    try:
        logger.info(f"Updating reminder {reminder_id}")

        # Build update data
        update_data = {}
        if reminder.title is not None:
            update_data["title"] = reminder.title
        if reminder.date is not None:
            update_data["date"] = reminder.date
        if reminder.time is not None:
            update_data["time"] = reminder.time

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        # Validate date/time if provided
        if "date" in update_data or "time" in update_data:
            # Get current reminder to check existing values
            supabase = get_supabase_client()
            current = supabase.table("reminders").select("*").eq("id", reminder_id).execute()

            if not current.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Reminder {reminder_id} not found"
                )

            date_to_check = update_data.get("date", current.data[0]["date"])
            time_to_check = update_data.get("time", current.data[0]["time"])

            try:
                parse_reminder_datetime(date_to_check, time_to_check)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )

        supabase = get_supabase_client()

        # Update reminder
        result = supabase.table("reminders") \
            .update(update_data) \
            .eq("id", reminder_id) \
            .execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reminder {reminder_id} not found"
            )

        logger.info(f"Reminder {reminder_id} updated successfully")

        return ReminderInfo(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update reminder: {str(e)}"
        )

@router.delete("/{reminder_id}", response_model=SuccessResponse)
async def delete_reminder(reminder_id: int):
    """
    Delete a reminder

    - **reminder_id**: Reminder ID
    """
    try:
        logger.info(f"Deleting reminder {reminder_id}")

        supabase = get_supabase_client()

        # Delete reminder
        result = supabase.table("reminders") \
            .delete() \
            .eq("id", reminder_id) \
            .execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reminder {reminder_id} not found"
            )

        logger.info(f"Reminder {reminder_id} deleted successfully")

        return SuccessResponse(message=f"Reminder {reminder_id} deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete reminder: {str(e)}"
        )

@router.delete("/{pair_id}/expired", response_model=SuccessResponse)
async def delete_expired_reminders(pair_id: str):
    """
    Delete all expired reminders for a pair

    - **pair_id**: Patient-caretaker pair ID
    """
    try:
        logger.info(f"Deleting expired reminders for pair {pair_id}")

        supabase = get_supabase_client()

        # Fetch all reminders for the pair
        result = supabase.table("reminders") \
            .select("*") \
            .eq("pair_id", pair_id) \
            .execute()

        # Find expired reminders
        expired_ids = [
            r["id"] for r in result.data
            if is_reminder_expired(r["date"], r["time"])
        ]

        if not expired_ids:
            return SuccessResponse(message="No expired reminders found")

        # Delete expired reminders
        for reminder_id in expired_ids:
            supabase.table("reminders").delete().eq("id", reminder_id).execute()

        logger.info(f"Deleted {len(expired_ids)} expired reminder(s)")

        return SuccessResponse(
            message=f"Deleted {len(expired_ids)} expired reminder(s)"
        )

    except Exception as e:
        logger.error(f"Error deleting expired reminders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete expired reminders: {str(e)}"
        )
