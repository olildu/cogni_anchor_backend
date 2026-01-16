from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.infra.websocket_manager import location_manager as manager
from app.models.sql_models import LiveLocation
import logging
import json

# FIX: Added prefix to match the app's WebSocket URL expectation
router = APIRouter(prefix="/api/v1/location", tags=["Live Location"])
logger = logging.getLogger("LocationSocket")

@router.websocket("/ws/location/{pair_id}/{role}")
async def location_websocket(websocket: WebSocket, pair_id: str, role: str, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for realtime tracking.
    - Patient connects and SENDS location data.
    - Caretaker connects and RECEIVES location data.
    """
    await manager.connect(websocket, pair_id)
    
    try:
        # If Caretaker connects, send the LAST KNOWN LOCATION immediately
        if role != "patient":
            last_location = db.query(LiveLocation).filter(LiveLocation.pair_id == pair_id).first()
            if last_location:
                logger.info(f"Sending last known location to caretaker: {last_location.latitude}, {last_location.longitude}")
                await websocket.send_json({
                    "latitude": last_location.latitude,
                    "longitude": last_location.longitude,
                    "status": "history"
                })

        while True:
            # Wait for data from the client
            data = await websocket.receive_text()
            location_data = json.loads(data)
            
            # If sender is patient, broadcast to caretaker AND save to DB
            if role == "patient":
                # 1. Broadcast immediately (Realtime)
                await manager.broadcast_json(location_data, pair_id, websocket)
                
                # 2. Persist last known location to DB
                try:
                    existing = db.query(LiveLocation).filter(LiveLocation.pair_id == pair_id).first()
                    if existing:
                        existing.latitude = location_data['latitude']
                        existing.longitude = location_data['longitude']
                        existing.patient_user_id = location_data.get('user_id')
                    else:
                        new_loc = LiveLocation(
                            pair_id=pair_id,
                            patient_user_id=location_data.get('user_id'),
                            latitude=location_data['latitude'],
                            longitude=location_data['longitude']
                        )
                        db.add(new_loc)
                    db.commit()
                except Exception as db_e:
                    logger.error(f"Failed to persist location: {db_e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, pair_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, pair_id)