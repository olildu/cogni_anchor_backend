"""
Audio Streaming WebSocket Endpoint
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.infra.websocket_manager import audio_manager
import logging

router = APIRouter(tags=["Audio Streaming"])
logger = logging.getLogger("AudioSocket")

@router.websocket("/ws/audio/{pair_id}/{role}")
async def audio_websocket(websocket: WebSocket, pair_id: str, role: str):
    """
    Real-time Audio Streaming.
    - Caretaker sends "START" -> Patient starts Mic
    - Patient sends Bytes -> Caretaker plays Audio
    """
    await audio_manager.connect(websocket, pair_id)
    
    try:
        while True:
            # We must handle both text (commands) and bytes (audio)
            # receive() returns a dict with 'type', 'text', or 'bytes' 
            message = await websocket.receive()
            
            if "text" in message:
                command = message["text"]
                # Relay commands (e.g., "START_MIC") to the other party
                await audio_manager.broadcast_text(command, pair_id, websocket)
                
            elif "bytes" in message:
                # Relay audio data
                data = message["bytes"]
                await audio_manager.broadcast_bytes(data, pair_id, websocket)

    except WebSocketDisconnect:
        audio_manager.disconnect(websocket, pair_id)
    except Exception as e:
        logger.error(f"Audio socket error: {e}")
        audio_manager.disconnect(websocket, pair_id)