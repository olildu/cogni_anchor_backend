"""
Simple test script for the chatbot API
Run this after starting the server to test the chatbot
"""

import requests
import json

BASE_URL = "http://localhost:8000"
PATIENT_ID = "test_patient_123"

def test_health():
    """Test if chatbot service is running"""
    print("\n--- Testing Health Check ---")
    response = requests.get(f"{BASE_URL}/api/v1/chat/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_chat(message):
    """Send a chat message"""
    print(f"\n--- Sending Message: '{message}' ---")
    response = requests.post(
        f"{BASE_URL}/api/v1/chat/message",
        json={
            "patient_id": PATIENT_ID,
            "message": message,
            "mode": "text"
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data['response']}")
    else:
        print(f"Error: {response.text}")
    return response

def test_history():
    """Get conversation history"""
    print(f"\n--- Getting Conversation History ---")
    response = requests.get(f"{BASE_URL}/api/v1/chat/history/{PATIENT_ID}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response

def test_clear_history():
    """Clear conversation history"""
    print(f"\n--- Clearing Conversation History ---")
    response = requests.delete(f"{BASE_URL}/api/v1/chat/history/{PATIENT_ID}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response

def main():
    """Run all tests"""
    print("="*60)
    print("Cogni Anchor Chatbot API Test")
    print("="*60)

    try:
        # Test health check
        if not test_health():
            print("\n❌ Health check failed! Is the server running?")
            return

        print("\n✅ Health check passed!")

        # Test chat messages
        test_chat("Hello!")
        test_chat("What time is it?")
        test_chat("I feel confused")

        # Test conversation history
        test_history()

        # Clear history
        test_clear_history()

        # Verify history is cleared
        test_history()

        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server!")
        print("Make sure the server is running:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
