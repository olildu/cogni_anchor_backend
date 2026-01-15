"""
Text-to-Speech Service
Converts text to speech using pyttsx3 (offline).
Removes dependency on OpenAI API.
"""

import os
import logging
from typing import Optional
import pyttsx3

logger = logging.getLogger("TTS_Service")


class TTSService:
    """Text-to-Speech service using offline pyttsx3"""

    def __init__(self):
        """
        Initialize TTS service (Offline only)
        """
        try:
            self.engine = pyttsx3.init()
            # Configure voice properties
            self.engine.setProperty('rate', 150)  # Speed of speech
            self.engine.setProperty('volume', 1.0)  # Volume (0.0 to 1.0)
            logger.info("Initialized offline TTS (pyttsx3)")
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
            self.engine = None

    def speak_offline(self, text: str) -> bool:
        """
        Speak text immediately using offline TTS.
        """
        if not self.engine:
            logger.error("pyttsx3 engine not initialized")
            return False

        try:
            logger.info(f"Speaking: {text[:50]}...")
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
            return False

    def generate_audio_file(
        self,
        text: str,
        output_path: str = "output.wav"
    ) -> Optional[str]:
        """
        Generate audio file from text using offline TTS.
        """
        if not self.engine:
            logger.error("pyttsx3 engine not initialized")
            return None

        if output_path.endswith(".mp3"):
             output_path = output_path.replace(".mp3", ".wav")

        try:
            logger.info(f"Generating offline audio file: {output_path}")
            
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()

            if os.path.exists(output_path):
                logger.info(f"Audio file generated successfully: {output_path}")
                return output_path
            else:
                logger.error("File was not created by pyttsx3")
                return None

        except Exception as e:
            logger.error(f"Error generating audio file: {e}")
            return None

    def text_to_speech(
        self,
        text: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert text to speech interface.
        """
        if output_path:
            return self.generate_audio_file(text, output_path)
        else:
            self.speak_offline(text)
            return None


# Global TTS instance
tts_service = TTSService()


def speak(text: str) -> bool:
    """Quick helper function to speak text"""
    return tts_service.speak_offline(text)


def generate_speech_file(
    text: str,
    output_path: str = "speech.wav",
    voice: str = "alloy" # Parameter ignored in offline mode
) -> Optional[str]:
    """Quick helper to generate speech file using offline TTS"""
    return tts_service.generate_audio_file(text, output_path)