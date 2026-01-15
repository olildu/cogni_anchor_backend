"""
LangGraph Agent API Endpoints
Intelligent chatbot with tool-calling capabilities
"""

import logging
import json
from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional
from app.services.chatbot.langgraph_agent import (
    run_agent,
    get_agent_history,
    add_to_agent_history
)
from app.services.infra.websocket_manager import agent_manager

logger = logging.getLogger("AgentAPI")
router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])


# === Pydantic Models ===

class AgentChatRequest(BaseModel):
    """Request model for agent chat"""
    patient_id: str
    pair_id: str
    message: str


class AgentChatResponse(BaseModel):
    """Response model for agent chat"""
    response: str
    patient_id: str
    pair_id: str


# === API Endpoints ===

@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    """
    Chat with the LangGraph agent via HTTP (Legacy/Fallback)
    """
    try:
        logger.info(f"Agent chat request from patient {request.patient_id}: {request.message}")

        history = get_agent_history(request.patient_id)

        response = await run_agent(
            patient_id=request.patient_id,
            pair_id=request.pair_id,
            message=request.message,
            conversation_history=history
        )

        add_to_agent_history(request.patient_id, "user", request.message)
        add_to_agent_history(request.patient_id, "assistant", response)

        return AgentChatResponse(
            response=response,
            patient_id=request.patient_id,
            pair_id=request.pair_id
        )

    except Exception as e:
        logger.error(f"Error in agent chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process agent chat: {str(e)}"
        )

@router.websocket("/ws/{patient_id}/{pair_id}")
async def ws_agent_chat(websocket: WebSocket, patient_id: str, pair_id: str):
    """
    Real-time WebSocket for Agent Chat
    URL: ws://<host>/api/v1/agent/ws/{patient_id}/{pair_id}
    """
    await agent_manager.connect(websocket, patient_id)
    try:
        while True:
            # 1. Receive Message
            data = await websocket.receive_text()
            
            # Parse JSON if possible, else treat as raw string
            user_message = ""
            try:
                payload = json.loads(data)
                user_message = payload.get("message", "")
            except:
                user_message = data

            if not user_message:
                continue

            # 2. Process with Agent
            history = get_agent_history(patient_id)
            
            # Update History (User)
            add_to_agent_history(patient_id, "user", user_message)

            # Run Agent
            response_text = await run_agent(
                patient_id=patient_id,
                pair_id=pair_id,
                message=user_message,
                conversation_history=history
            )

            # Update History (Assistant)
            add_to_agent_history(patient_id, "assistant", response_text)

            # 3. Send Response
            response_data = {
                "response": response_text,
                "patient_id": patient_id,
                "pair_id": pair_id
            }
            await agent_manager.send_personal_message(json.dumps(response_data), websocket)

    except WebSocketDisconnect:
        agent_manager.disconnect(websocket, patient_id)
    except Exception as e:
        logger.error(f"Agent WS Error: {e}")
        agent_manager.disconnect(websocket, patient_id)


@router.delete("/history/{patient_id}")
async def clear_agent_history(patient_id: str):
    """Clear conversation history for a patient"""
    try:
        from app.services.langgraph_agent import agent_conversations

        if patient_id in agent_conversations:
            agent_conversations[patient_id] = []
            logger.info(f"Cleared agent history for patient {patient_id}")

        return {
            "message": "Conversation history cleared",
            "patient_id": patient_id
        }

    except Exception as e:
        logger.error(f"Error clearing agent history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear history: {str(e)}"
        )


@router.get("/health")
async def agent_health_check():
    """Health check for agent service"""
    return {
        "status": "healthy",
        "service": "langgraph_agent",
        "features": [
            "reminder_management",
            "emergency_alerts",
            "emotional_support",
            "tool_calling",
            "websocket_chat"
        ],
        "tools": [
            "create_reminder",
            "list_reminders",
            "delete_reminder",
            "send_emergency_alert"
        ]
    }