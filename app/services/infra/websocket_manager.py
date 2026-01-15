"""
WebSocket Manager
Handles real-time connections for live location, audio, agent chat, and reminders.
"""

from typing import Dict, List
from fastapi import WebSocket
import logging

logger = logging.getLogger("WebSocketManager")

class ConnectionManager:
    def __init__(self):
        # Maps key (pair_id or patient_id) -> List of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, key: str):
        await websocket.accept()
        if key not in self.active_connections:
            self.active_connections[key] = []
        self.active_connections[key].append(websocket)
        logger.info(f"New connection for {key}. Total: {len(self.active_connections[key])}")

    def disconnect(self, websocket: WebSocket, key: str):
        if key in self.active_connections:
            if websocket in self.active_connections[key]:
                self.active_connections[key].remove(websocket)
            if not self.active_connections[key]:
                del self.active_connections[key]
        logger.info(f"Connection removed for {key}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def broadcast_json(self, data: dict, pair_id: str, sender_socket: WebSocket = None):
        """Broadcast JSON data (Location, Reminders, etc.)"""
        if pair_id not in self.active_connections: return
        
        for connection in self.active_connections[pair_id]:
            if connection != sender_socket:
                try:
                    await connection.send_json(data)
                except Exception:
                    self.disconnect(connection, pair_id)

    async def broadcast_bytes(self, data: bytes, pair_id: str, sender_socket: WebSocket = None):
        """Broadcast Binary (Audio data)"""
        if pair_id not in self.active_connections: return

        for connection in self.active_connections[pair_id]:
            if connection != sender_socket:
                try:
                    await connection.send_bytes(data)
                except Exception:
                    self.disconnect(connection, pair_id)
    
    async def broadcast_text(self, message: str, pair_id: str, sender_socket: WebSocket = None):
        """Broadcast control messages (START/STOP)"""
        if pair_id not in self.active_connections: return

        for connection in self.active_connections[pair_id]:
            if connection != sender_socket:
                try:
                    await connection.send_text(message)
                except Exception:
                    self.disconnect(connection, pair_id)

# Separate managers for different features
location_manager = ConnectionManager()
audio_manager = ConnectionManager()
agent_manager = ConnectionManager()
reminder_manager = ConnectionManager() # ✅ Added for Reminders