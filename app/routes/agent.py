"""
LangGraph Agent API Endpoints
Intelligent chatbot with tool-calling capabilities
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.services.langgraph_agent import (
    run_agent,
    get_agent_history,
    add_to_agent_history
)

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
    Chat with the LangGraph agent

    The agent can:
    - Create reminders from natural language
    - List upcoming reminders
    - Delete reminders
    - Send emergency alerts to caregivers
    - Provide emotional support

    Request body:
    {
        "patient_id": "demo_patient_001",
        "pair_id": "demo_pair_001",
        "message": "Remind me to take my medicine at 8pm"
    }

    Response:
    {
        "response": "Reminder created successfully! I'll remind you about 'Take medicine' on 25 Dec 2024 at 08:00 PM.",
        "patient_id": "demo_patient_001",
        "pair_id": "demo_pair_001"
    }
    """
    try:
        logger.info(f"Agent chat request from patient {request.patient_id}: {request.message}")

        # Get conversation history
        history = get_agent_history(request.patient_id)

        # Run the agent
        response = await run_agent(
            patient_id=request.patient_id,
            pair_id=request.pair_id,
            message=request.message,
            conversation_history=history
        )

        # Update conversation history
        add_to_agent_history(request.patient_id, "user", request.message)
        add_to_agent_history(request.patient_id, "assistant", response)

        logger.info(f"Agent response generated successfully for patient {request.patient_id}")

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


@router.delete("/history/{patient_id}")
async def clear_agent_history(patient_id: str):
    """
    Clear conversation history for a patient

    This resets the agent's memory of past conversations.

    Response:
    {
        "message": "Conversation history cleared",
        "patient_id": "demo_patient_001"
    }
    """
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
    """
    Health check for agent service

    Response:
    {
        "status": "healthy",
        "service": "langgraph_agent",
        "features": ["reminder_management", "emergency_alerts", "emotional_support"]
    }
    """
    return {
        "status": "healthy",
        "service": "langgraph_agent",
        "features": [
            "reminder_management",
            "emergency_alerts",
            "emotional_support",
            "tool_calling"
        ],
        "tools": [
            "create_reminder",
            "list_reminders",
            "delete_reminder",
            "send_emergency_alert"
        ]
    }