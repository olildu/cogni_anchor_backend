"""
Simple audio recorder for testing voice chat
Records audio from your microphone and saves it as a WAV file
"""

import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np

def record_audio(duration=5, filename="test_audio.wav", sample_rate=16000):
    """
    Record audio from microphone

    Args:
        duration: Recording duration in seconds (default: 5)
        filename: Output filename (default: test_audio.wav)
        sample_rate: Sample rate in Hz (default: 16000)
    """
    print(f"🎤 Recording for {duration} seconds...")
    print("Speak now!")

    # Record audio
    audio_data = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,  # Mono
        dtype=np.int16
    )

    # Wait for recording to complete
    sd.wait()

    # Save to file
    wav.write(filename, sample_rate, audio_data)

    print(f"✅ Recording saved to: {filename}")
    return filename

if __name__ == "__main__":
    import sys

    # Get duration from command line or use default (5 seconds)
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    print("=" * 50)
    print("🎙️  Voice Chat Audio Recorder")
    print("=" * 50)

    filename = record_audio(duration=duration)

    print("\n✨ You can now use this file to test the voice chat endpoint!")
    print(f"📁 File location: {filename}")
