import firebase_admin
from firebase_admin import credentials, messaging
import os

# ==========================================
# 1. SETUP: Put your device FCM Token here
# ==========================================
FCM_TOKEN = "dcdyFqE4RkGklaLfTBfn5C:APA91bG3V2fQu157Qluu6zHIIcDRd5j89l-8TqvRiCQmdVFMzoBTHcu1twCHqa1AA5kbu94NE4M71DWcl_w7-lSFCmVO9QZUB3EaTjXLX0kL13QKpdcrVno"

# ==========================================
# 2. CONFIGURATION
# ==========================================
SERVICE_ACCOUNT_KEY_PATH = "app/secrets/serviceAccountKey.json"

def initialize_firebase():
    if not firebase_admin._apps:
        try:
            if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
                print(f"❌ Error: Key not found at {SERVICE_ACCOUNT_KEY_PATH}")
                return False
            
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin Initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to init Firebase: {e}")
            return False
    return True

def send_immediate_notification():
    """
    Sends a direct 'Display Notification'.
    Android OS handles this automatically when app is backgrounded/killed.
    """
    print(f"🚀 Sending immediate notification to: {FCM_TOKEN[:20]}...")

    message = messaging.Message(
        # ✅ NOTIFICATION BLOCK: Handled by OS directly
        notification=messaging.Notification(
            title="Backend Test",
            body="This notification was triggered immediately by the server!"
        ),
        # ✅ ANDROID CONFIG: Force high priority and specific channel
        android=messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                channel_id='reminder_channel_v3', # Must match your Flutter channel ID
                priority='max',
                visibility='public',
                default_sound=True,
                default_vibrate_timings=True,
                click_action='FLUTTER_NOTIFICATION_CLICK'
            ),
        ),
        token=FCM_TOKEN,
    )

    try:
        response = messaging.send(message)
        print(f"✅ Message sent! ID: {response}")
        print("--> Check your device. If app is closed, you SHOULD see this immediately.")
    except Exception as e:
        print(f"❌ Error sending message: {e}")

if __name__ == "__main__":
    if initialize_firebase():
        send_immediate_notification()