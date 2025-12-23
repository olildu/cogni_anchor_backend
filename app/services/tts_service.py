"""
Text-to-Speech Service
Converts text to speech using pyttsx3 (offline) or OpenAI TTS API (online)
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
import pyttsx3

load_dotenv()

logger = logging.getLogger("TTS_Service")


class TTSService:
    """Text-to-Speech service with both offline and online options"""

    def __init__(self, use_online: bool = False):
        """
        Initialize TTS service

        Args:
            use_online: If True, use OpenAI TTS API. If False, use pyttsx3 (offline)
        """
        self.use_online = use_online

        if not use_online:
            # Initialize pyttsx3 for offline TTS
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 150)  # Speech speed
                self.engine.setProperty('volume', 1.0)  # Max volume
                logger.info("Initialized offline TTS (pyttsx3)")
            except Exception as e:
                logger.error(f"Failed to initialize pyttsx3: {e}")
                self.engine = None
        else:
            # For online TTS using OpenAI
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("Initialized online TTS (OpenAI)")
            else:
                logger.warning("OPENAI_API_KEY not found. Online TTS not available.")
                self.openai_client = None

    def speak_offline(self, text: str) -> bool:
        """
        Speak text using offline TTS (pyttsx3)

        Args:
            text: Text to speak

        Returns:
            True if successful, False otherwise
        """
        if not self.engine:
            logger.error("pyttsx3 engine not initialized")
            return False

        try:
            logger.info(f"Speaking (offline): {text[:50]}...")
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
            return False

    def generate_audio_file_offline(
        self,
        text: str,
        output_path: str = "output.mp3"
    ) -> Optional[str]:
        """
        Generate audio file from text using offline TTS (pyttsx3)

        Args:
            text: Text to convert to speech
            output_path: Path to save audio file

        Returns:
            Path to generated audio file or None if error
        """
        if not self.engine:
            logger.error("pyttsx3 engine not initialized")
            return None

        try:
            logger.info(f"Generating offline audio file for: {text[:50]}...")

            # Save to file using pyttsx3
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()

            logger.info(f"Offline audio file generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating offline audio file: {e}")
            return None

    def generate_audio_file(
        self,
        text: str,
        output_path: str = "output.mp3",
        voice: str = "alloy"
    ) -> Optional[str]:
        """
        Generate audio file from text using OpenAI TTS API

        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)

        Returns:
            Path to generated audio file or None if error
        """
        if not self.use_online or not self.openai_client:
            logger.error("Online TTS not available")
            return None

        try:
            logger.info(f"Generating audio file for: {text[:50]}...")

            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )

            # Save to file
            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Audio file generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating audio file: {e}")
            return None

    def text_to_speech(
        self,
        text: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert text to speech (chooses online or offline based on initialization)

        Args:
            text: Text to convert
            output_path: If provided, save to file (online mode only)

        Returns:
            Path to audio file if online mode, None if offline mode
        """
        if self.use_online and output_path:
            return self.generate_audio_file(text, output_path)
        else:
            self.speak_offline(text)
            return None


# Global TTS instance (offline by default)
tts_service = TTSService(use_online=False)


def speak(text: str) -> bool:
    """
    Quick helper function to speak text using offline TTS

    Args:
        text: Text to speak

    Returns:
        True if successful
    """
    return tts_service.speak_offline(text)


def generate_speech_file(
    text: str,
    output_path: str = "speech.mp3",
    voice: str = "alloy"
) -> Optional[str]:
    """
    Quick helper to generate speech file
    Automatically uses offline TTS if OpenAI API key not available

    Args:
        text: Text to convert
        output_path: Output file path
        voice: Voice to use (only for online mode)

    Returns:
        Path to generated file or None
    """
    # Check if OpenAI API key is available
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if OPENAI_API_KEY:
        # Try online TTS
        online_tts = TTSService(use_online=True)
        return online_tts.generate_audio_file(text, output_path, voice)
    else:
        # Use offline TTS
        logger.info("Using offline TTS for audio file generation")
        offline_tts = TTSService(use_online=False)
        # Change extension to .wav for offline TTS (pyttsx3 works better with wav)
        if output_path.endswith('.mp3'):
            output_path = output_path.replace('.mp3', '.wav')
        return offline_tts.generate_audio_file_offline(text, output_path)
