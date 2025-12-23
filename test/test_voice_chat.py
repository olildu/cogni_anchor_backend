"""
Complete Voice Chat Test Script
Records audio, sends to API, and shows the response
"""

import requests
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import time

def record_audio(duration=5, filename="test_audio.wav", sample_rate=16000):
    """Record audio from microphone"""
    print(f"\n🎤 Recording for {duration} seconds...")
    print("👉 Speak clearly into your microphone!")
    print("💡 Try saying: 'Hello, how are you today?'\n")

    # Countdown
    for i in range(3, 0, -1):
        print(f"   Starting in {i}...")
        time.sleep(1)

    print("   🔴 RECORDING NOW!\n")

    # Record audio
    audio_data = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype=np.int16
    )

    sd.wait()

    # Save to file
    wav.write(filename, sample_rate, audio_data)

    print(f"   ✅ Recording complete!\n")
    return filename

def test_voice_chat(audio_file, patient_id="test_patient"):
    """Send audio to voice chat endpoint and get response"""
    url = "http://localhost:8000/api/v1/chat/voice"

    print(f"📤 Sending audio to voice chat API...")
    print(f"   Patient ID: {patient_id}")
    print(f"   Audio file: {audio_file}\n")

    try:
        with open(audio_file, 'rb') as f:
            files = {'audio': f}
            data = {'patient_id': patient_id}

            response = requests.post(url, files=files, data=data, timeout=60)

        if response.status_code == 200:
            result = response.json()

            print("=" * 60)
            print("✅ SUCCESS! Voice chat response received:")
            print("=" * 60)
            print(f"\n📝 What you said (transcription):")
            print(f"   \"{result['transcription']}\"\n")
            print(f"🤖 Bot's response:")
            print(f"   \"{result['response']}\"\n")
            print(f"🔊 Audio response saved to:")
            print(f"   {result['audio_url']}\n")
            print(f"👤 Patient ID: {result['patient_id']}")
            print(f"🎵 Mode: {result['mode']}")
            print("=" * 60)

        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎙️  VOICE CHAT TEST TOOL")
    print("=" * 60)

    # Step 1: Record audio
    audio_file = record_audio(duration=5)

    # Step 2: Test voice chat
    test_voice_chat(audio_file, patient_id="alice")

    print("\n✨ Test complete!")
