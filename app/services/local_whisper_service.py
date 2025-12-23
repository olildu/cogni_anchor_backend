"""
Local Whisper STT Service (Offline)
Uses OpenAI's Whisper model running locally for speech-to-text
"""

import os
import logging
import tempfile
from typing import Optional

logger = logging.getLogger("LocalWhisperService")

# Global Whisper model instance (lazy loaded)
_whisper_model = None
_model_loaded = False


def load_whisper_model(model_name: str = "base"):
    """
    Load Whisper model (lazy loading)

    Available models (by size and accuracy):
    - tiny: Fastest, least accurate (~1GB RAM)
    - base: Fast, good for most cases (~1GB RAM) - DEFAULT
    - small: More accurate (~2GB RAM)
    - medium: High accuracy (~5GB RAM)
    - large: Best accuracy (~10GB RAM)

    Args:
        model_name: Name of the Whisper model to load

    Returns:
        Loaded Whisper model
    """
    global _whisper_model, _model_loaded

    if _model_loaded and _whisper_model is not None:
        return _whisper_model

    try:
        import whisper
        logger.info(f"Loading Whisper model: {model_name}")
        _whisper_model = whisper.load_model(model_name)
        _model_loaded = True
        logger.info(f"Whisper model '{model_name}' loaded successfully!")
        return _whisper_model
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        logger.error("Make sure you installed whisper: pip install openai-whisper")
        _model_loaded = False
        return None


def transcribe_audio_local(
    audio_file_path: str,
    model_name: str = "base",
    language: str = "en"
) -> Optional[str]:
    """
    Transcribe audio file using local Whisper model

    Args:
        audio_file_path: Path to audio file (mp3, wav, m4a, etc.)
        model_name: Whisper model to use (tiny/base/small/medium/large)
        language: Language code (en, es, fr, etc.) - None for auto-detect

    Returns:
        Transcribed text or None if error
    """
    model = load_whisper_model(model_name)

    if model is None:
        logger.error("Whisper model not available")
        return None

    try:
        logger.info(f"Transcribing audio file: {audio_file_path}")

        # Transcribe with Whisper
        result = model.transcribe(
            audio_file_path,
            language=language,
            fp16=False  # Use FP32 for CPU (FP16 for GPU)
        )

        text = result["text"].strip()
        logger.info(f"Transcription successful: {text[:50]}...")
        return text

    except FileNotFoundError:
        logger.error(f"Audio file not found: {audio_file_path}")
        return None
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        return None


async def transcribe_audio_bytes_local(
    audio_bytes: bytes,
    filename: str = "temp_audio.wav",
    model_name: str = "base"
) -> Optional[str]:
    """
    Transcribe audio from bytes using local Whisper

    Args:
        audio_bytes: Audio file bytes
        filename: Temporary filename extension
        model_name: Whisper model to use

    Returns:
        Transcribed text or None if error
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        # Transcribe using local Whisper
        text = transcribe_audio_local(temp_path, model_name=model_name)

        # Clean up temp file
        os.unlink(temp_path)

        return text

    except Exception as e:
        logger.error(f"Error transcribing audio bytes: {e}")
        return None


# Preload model on module import (optional - comment out to lazy load)
# load_whisper_model("base")
