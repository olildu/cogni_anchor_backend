"""
Chatbot module for Cogni Anchor
Handles conversational AI using LangChain (Gemini) + Local STT/TTS
"""

import logging
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
import os
import uuid
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.services.audio.stt_service import transcribe_audio_bytes
from app.services.audio.tts_service import generate_speech_file

# --- Logging Setup ---
logger = logging.getLogger("ChatbotAPI")

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    patient_id: str
    message: str
    mode: str = "text"

class ChatResponse(BaseModel):
    response: str
    patient_id: str
    mode: str

# --- AI Configuration ---
conversation_history: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = """You are a compassionate AI companion for patients with cognitive challenges.
Keep responses brief, warm, and clear. Do not offer medical advice.
Always be patient and reassuring."""

def get_chat_model():
    """Initialize LangChain Chat Model"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("No Gemini API key found.")
        return None
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=api_key,
        temperature=0.7
    )

# --- Core Functions ---

def get_conversation_history(patient_id: str) -> List[Dict[str, str]]:
    if patient_id not in conversation_history:
        conversation_history[patient_id] = []
    return conversation_history[patient_id]

def add_to_history(patient_id: str, role: str, content: str):
    if patient_id not in conversation_history:
        conversation_history[patient_id] = []
    conversation_history[patient_id].append({"role": role, "content": content})
    # Keep last 10 messages
    if len(conversation_history[patient_id]) > 10:
        conversation_history[patient_id] = conversation_history[patient_id][-10:]

def generate_response(patient_id: str, user_message: str) -> str:
    try:
        model = get_chat_model()
        if not model:
            return "I'm currently offline (API Key missing)."

        # Build LangChain message history
        history = get_conversation_history(patient_id)
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        messages.append(HumanMessage(content=user_message))

        response = model.invoke(messages)
        assistant_response = response.content

        # Update History
        add_to_history(patient_id, "user", user_message)
        add_to_history(patient_id, "assistant", assistant_response)

        return assistant_response

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return "I'm having a little trouble connecting right now, but I'm here."

def clear_conversation(patient_id: str):
    conversation_history[patient_id] = []

# --- FastAPI Router ---
router = APIRouter(prefix="/api/v1/chat", tags=["Chatbot"])

@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    response = generate_response(request.patient_id, request.message)
    return ChatResponse(response=response, patient_id=request.patient_id, mode=request.mode)

@router.get("/history/{patient_id}")
async def get_history(patient_id: str):
    return {"patient_id": patient_id, "messages": get_conversation_history(patient_id)}

@router.delete("/history/{patient_id}")
async def delete_history(patient_id: str):
    clear_conversation(patient_id)
    return {"message": "Conversation history cleared", "patient_id": patient_id}

@router.post("/voice")
async def voice_chat(
    audio: UploadFile = File(...),
    patient_id: str = Form("default_patient")
):
    try:
        logger.info(f"Received voice message from patient {patient_id}")
        audio_bytes = await audio.read()

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Audio file is empty")

        # 1. Transcribe (Local Whisper)
        transcription = await transcribe_audio_bytes(audio_bytes, filename=audio.filename)
        
        if not transcription:
            raise HTTPException(status_code=400, detail="Could not understand audio.")

        # 2. AI Response
        response_text = generate_response(patient_id, transcription)

        # 3. Text to Speech
        initial_filename = f"response_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = f"temp/{initial_filename}"
        os.makedirs("temp", exist_ok=True)

        generated_audio_path = generate_speech_file(
            text=response_text,
            output_path=audio_path
        )

        final_filename = os.path.basename(generated_audio_path) if generated_audio_path else None

        return {
            "patient_id": patient_id,
            "transcription": transcription,
            "response": response_text,
            "audio_url": f"/temp/{final_filename}" if final_filename else None,
            "mode": "audio"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chatbot (LangChain)"}