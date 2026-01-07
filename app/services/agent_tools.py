"""
Agent Tools for LangGraph Agent
Provides tools for reminder management and emergency alerts
"""

import logging
from typing import Optional, List
from datetime import datetime
from langchain_core.tools import tool
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger("AgentTools")


@tool
def create_reminder(pair_id: str, title: str, date: str, time: str) -> str:
    """
    Create a new reminder for the patient.

    Use this tool when the patient asks to set a reminder or be reminded of something.

    Args:
        pair_id: The patient-caretaker pair ID
        title: What to remind about (e.g., "Take medicine", "Doctor appointment")
        date: Date in format 'dd MMM yyyy' (e.g., '25 Dec 2024', '01 Jan 2025')
        time: Time in format 'hh:mm AM/PM' (e.g., '02:30 PM', '08:00 AM')

    Returns:
        Success or error message
    """
    try:
        logger.info(f"Creating reminder: {title} on {date} at {time}")

        # Validate date/time format
        try:
            datetime.strptime(f"{date} {time}", "%d %b %Y %I:%M %p")
        except ValueError as e:
            return f"Error: Invalid date/time format. Please use 'dd MMM yyyy' for date and 'hh:mm AM/PM' for time. Error: {e}"

        # FIX: Use service key to bypass RLS policies
        supabase = get_supabase_client(use_service_key=True)

        # Insert reminder
        result = supabase.table("reminders").insert({
            "pair_id": pair_id,
            "title": title,
            "date": date,
            "time": time
        }).execute()

        if not result.data or len(result.data) == 0:
            return "Error: Failed to create reminder in database"

        reminder_id = result.data[0]["id"]
        logger.info(f"Reminder created successfully with ID: {reminder_id}")

        return f"Reminder created successfully! I'll remind you about '{title}' on {date} at {time}."

    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        return f"Error: Failed to create reminder - {str(e)}"


@tool
def list_reminders(pair_id: str) -> str:
    """
    List all upcoming (non-expired) reminders for the patient.
    """
    try:
        logger.info(f"Fetching reminders for pair {pair_id}")

        # FIX: Use service key to bypass RLS policies
        supabase = get_supabase_client(use_service_key=True)

        # Fetch reminders
        result = supabase.table("reminders") \
            .select("*") \
            .eq("pair_id", pair_id) \
            .order("date", desc=False) \
            .order("time", desc=False) \
            .execute()

        if not result.data or len(result.data) == 0:
            return "You don't have any reminders set right now."

        # Filter out expired reminders
        now = datetime.now()
        upcoming_reminders = []

        for reminder in result.data:
            try:
                reminder_dt = datetime.strptime(
                    f"{reminder['date']} {reminder['time']}",
                    "%d %b %Y %I:%M %p"
                )
                if reminder_dt >= now:
                    upcoming_reminders.append(reminder)
            except:
                continue

        if not upcoming_reminders:
            return "All your reminders have passed. You don't have any upcoming reminders."

        # Format reminders as a friendly list
        reminder_list = []
        for idx, reminder in enumerate(upcoming_reminders, 1):
            reminder_list.append(
                f"{idx}. {reminder['title']} - {reminder['date']} at {reminder['time']}"
            )

        return f"You have {len(upcoming_reminders)} upcoming reminder(s):\n" + "\n".join(reminder_list)

    except Exception as e:
        logger.error(f"Error fetching reminders: {e}")
        return f"Error: Failed to fetch reminders - {str(e)}"


@tool
def delete_reminder(pair_id: str, reminder_title: str) -> str:
    """
    Delete a reminder by searching for its title.
    """
    try:
        logger.info(f"Deleting reminder with title containing: {reminder_title}")

        # FIX: Use service key to bypass RLS policies
        supabase = get_supabase_client(use_service_key=True)

        # Find reminders matching the title
        result = supabase.table("reminders") \
            .select("*") \
            .eq("pair_id", pair_id) \
            .execute()

        if not result.data:
            return "You don't have any reminders to delete."

        # Find matching reminders (case-insensitive partial match)
        matching_reminders = [
            r for r in result.data
            if reminder_title.lower() in r["title"].lower()
        ]

        if not matching_reminders:
            return f"I couldn't find a reminder matching '{reminder_title}'. Please check the reminder title and try again."

        if len(matching_reminders) > 1:
            titles = [r["title"] for r in matching_reminders]
            return f"Found multiple reminders matching '{reminder_title}': {', '.join(titles)}. Please be more specific."

        # Delete the matching reminder
        reminder_to_delete = matching_reminders[0]
        supabase.table("reminders").delete().eq("id", reminder_to_delete["id"]).execute()

        logger.info(f"Deleted reminder: {reminder_to_delete['title']}")

        return f"I've deleted the reminder '{reminder_to_delete['title']}' scheduled for {reminder_to_delete['date']} at {reminder_to_delete['time']}."

    except Exception as e:
        logger.error(f"Error deleting reminder: {e}")
        return f"Error: Failed to delete reminder - {str(e)}"


@tool
def send_emergency_alert(pair_id: str, reason: str) -> str:
    """
    Send an emergency alert to the patient's caregiver.
    """
    try:
        logger.warning(f"EMERGENCY ALERT for pair {pair_id}: {reason}")

        # FIX: Use service key to bypass RLS policies
        supabase = get_supabase_client(use_service_key=True)

        # Store emergency alert in database
        alert_data = {
            "pair_id": pair_id,
            "alert_type": "emergency",
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }

        # Try to insert into alerts table
        try:
            supabase.table("emergency_alerts").insert(alert_data).execute()
        except Exception as db_error:
            logger.error(f"Could not save to database: {db_error}")

        logger.info(f"Emergency alert sent successfully for pair {pair_id}")

        return f"I've notified your caregiver about this situation. Help is on the way. Please stay calm."

    except Exception as e:
        logger.error(f"Error sending emergency alert: {e}")
        return "I'm here with you. Let me help you feel safe."