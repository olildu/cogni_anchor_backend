import logging
from typing import Optional
from app.services.audio.local_whisper_service import transcribe_audio_local, transcribe_audio_bytes_local

logger = logging.getLogger("STT_Service")

def transcribe_audio(
    audio_file_path: str,
    model: str = "base",
    response_format: str = "text"
) -> Optional[str]:
    try:
        logger.info(f"Using LOCAL Whisper to transcribe: {audio_file_path}")
        return transcribe_audio_local(audio_file_path, model_name=model)
    except Exception as e:
        logger.error(f"Error with local Whisper: {e}")
        return None


async def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str = "temp_audio.wav",
    model: str = "base"
) -> Optional[str]:
    try:
        return await transcribe_audio_bytes_local(
            audio_bytes=audio_bytes, 
            filename=filename, 
            model_name=model
        )
    except Exception as e:
        logger.error(f"Error transcribing audio bytes: {e}")
        return None