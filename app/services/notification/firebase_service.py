import firebase_admin
from firebase_admin import credentials, messaging
import logging
import os

logger = logging.getLogger("FirebaseService")

# Initialize only once to prevent errors during reloads
if not firebase_admin._apps:
    try:
        # Dynamic path loading to handle different execution contexts
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to 'app', then into 'secrets'
        key_path = os.path.join(current_dir, "..", "secrets", "serviceAccountKey.json")
        
        # Fallback if running from root
        if not os.path.exists(key_path):
            if os.path.exists("app/secrets/serviceAccountKey.json"):
                key_path = "app/secrets/serviceAccountKey.json"
            elif os.path.exists("serviceAccountKey.json"):
                key_path = "serviceAccountKey.json"

        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin Initialized")
        else:
            logger.error(f"❌ Service account key not found at: {key_path}")

    except Exception as e:
        logger.error(f"Failed to init Firebase: {e}")

def send_reminder_push(token: str, title: str, date: str, time: str, reminder_id: str):
    """Sends a data-only message to trigger background processing (Legacy/Single User)"""
    try:
        message = messaging.Message(
            data={
                "type": "new_reminder",
                "title": title,
                "date": date,
                "time": time,
                "id": str(reminder_id)
            },
            token=token,
        )
        response = messaging.send(message)
        logger.info(f"Successfully sent FCM message: {response}")
        return True
    except Exception as e:
        logger.error(f"Error sending FCM message: {e}")
        return False

def send_multicast_notification(tokens: list[str], title: str, body: str, data: dict = None):
    """
    Sends a standard Notification + Data to multiple devices.
    Standard notifications are handled by the OS automatically when app is backgrounded.
    """
    if not tokens:
        return

    try:
        # We send both 'notification' (for OS display) and 'data' (for app logic)
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id='reminder_channel_v4', # Must match frontend
                    priority='max',
                    visibility='public',
                    default_sound=True,
                    default_vibrate_timings=True,
                    click_action='FLUTTER_NOTIFICATION_CLICK',
                ),
            ),
            data=data or {},
            tokens=tokens,
        )
        
        response = messaging.send_each_for_multicast(message)
        logger.info(f"Sent multicast. Success: {response.success_count}, Failure: {response.failure_count}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending multicast message: {e}")
        return False 