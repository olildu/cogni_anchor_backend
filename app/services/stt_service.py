"""
Speech-to-Text Service
Supports both OpenAI Whisper API (online) and Local Whisper (offline)
Automatically falls back to local Whisper if OpenAI key is not available
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger("STT_Service")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_LOCAL_WHISPER = not OPENAI_API_KEY  # Auto-switch to local if no API key

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("Using OpenAI Whisper API for STT")
else:
    client = None
    logger.info("OpenAI API key not found. Using LOCAL Whisper for STT (offline)")


def transcribe_audio(
    audio_file_path: str,
    model: str = "whisper-1",
    response_format: str = "text"
) -> Optional[str]:
    """
    Transcribe audio file to text
    Uses OpenAI Whisper API if available, otherwise uses local Whisper

    Args:
        audio_file_path: Path to the audio file
        model: Whisper model to use (default: whisper-1 for OpenAI, base for local)
        response_format: Response format (text, json, verbose_json)

    Returns:
        Transcribed text or None if error
    """
    # Use local Whisper if OpenAI client not available
    if USE_LOCAL_WHISPER:
        try:
            from app.services.local_whisper_service import transcribe_audio_local
            logger.info(f"Using LOCAL Whisper to transcribe: {audio_file_path}")
            return transcribe_audio_local(audio_file_path, model_name="base")
        except Exception as e:
            logger.error(f"Error with local Whisper: {e}")
            return None

    # Use OpenAI Whisper API
    try:
        with open(audio_file_path, "rb") as audio_file:
            logger.info(f"Transcribing audio file with OpenAI: {audio_file_path}")

            transcription = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                response_format=response_format
            )

            # Extract text from response
            if hasattr(transcription, 'text'):
                text = transcription.text
            else:
                text = str(transcription)

            logger.info(f"Transcription successful: {text[:50]}...")
            return text

    except FileNotFoundError:
        logger.error(f"Audio file not found: {audio_file_path}")
        return None
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        return None


async def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str = "temp_audio.wav",
    model: str = "whisper-1"
) -> Optional[str]:
    """
    Transcribe audio from bytes (useful for uploaded files)
    Automatically uses local Whisper if OpenAI API key not available

    Args:
        audio_bytes: Audio file bytes
        filename: Temporary filename to use
        model: Whisper model to use (whisper-1 for OpenAI, base for local)

    Returns:
        Transcribed text or None if error
    """
    import tempfile
    import os

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        # Transcribe (will auto-use local Whisper if no OpenAI key)
        text = transcribe_audio(temp_path, model=model)

        # Clean up
        os.unlink(temp_path)

        return text

    except Exception as e:
        logger.error(f"Error transcribing audio bytes: {e}")
        return None
