"""
Local Whisper STT Service (Offline)
Uses OpenAI's Whisper model running locally for speech-to-text
"""

import os
import logging
import tempfile
import subprocess
from typing import Optional

logger = logging.getLogger("LocalWhisperService")

# Global Whisper model instance (lazy loaded)
_whisper_model = None
_model_loaded = False


def load_whisper_model(model_name: str = "base"):
    """
    Load Whisper model (lazy loading)
    """
    global _whisper_model, _model_loaded

    if _model_loaded and _whisper_model is not None:
        return _whisper_model

    try:
        import whisper
        logger.info(f"Loading Whisper model: {model_name}")
        # Download and load the model (happens only once)
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
    """
    model = load_whisper_model(model_name)

    if model is None:
        logger.error("Whisper model not available")
        return None

    try:
        logger.info(f"Transcribing audio file: {audio_file_path}")

        # Transcribe with Whisper
        # fp16=False is safer for CPU usage to avoid warnings
        result = model.transcribe(
            audio_file_path,
            language=language,
            fp16=False 
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
    Transcribe audio from bytes using local Whisper.
    Converts input audio to safe WAV format before processing.
    """
    input_path = None
    output_path = None
    
    try:
        # 1. Determine extension
        _, ext = os.path.splitext(filename)
        if not ext:
            ext = ".aac" # Default for Flutter sound

        # 2. Save raw bytes to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(audio_bytes)
            input_path = temp_file.name

        logger.info(f"Saved temp audio: {input_path} ({len(audio_bytes)} bytes)")

        # 3. Convert to 16kHz Mono WAV (Standard for Whisper)
        # This fixes issues with AAC/M4A/MP3 containers
        output_path = input_path + "_converted.wav"
        
        try:
            subprocess.run([
                "ffmpeg", "-y",           # Overwrite if exists
                "-i", input_path,         # Input file
                "-ar", "16000",           # 16k Sample rate
                "-ac", "1",               # Mono channel
                "-c:a", "pcm_s16le",      # WAV codec
                output_path               # Output file
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info("Audio converted to 16kHz WAV successfully")
            file_to_transcribe = output_path
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"FFmpeg conversion failed (using original): {e}")
            file_to_transcribe = input_path

        # 4. Transcribe the clean file
        text = transcribe_audio_local(file_to_transcribe, model_name=model_name)
        return text

    except Exception as e:
        logger.error(f"Error transcribing audio bytes: {e}")
        return None
        
    finally:
        # 5. Cleanup temp files
        if input_path and os.path.exists(input_path):
            os.unlink(input_path)
        if output_path and os.path.exists(output_path):
            os.unlink(output_path)