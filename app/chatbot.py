"""
Chatbot module for Cogni Anchor
Handles conversational AI using Gemini API + Local STT/TTS
"""

import logging
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
import google.generativeai as genai
import os
import uuid
from app.services.stt_service import transcribe_audio_bytes
from app.services.tts_service import generate_speech_file

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

# --- AI API Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    AI_MODEL = "gemini-2.5-flash"
else:
    AI_MODEL = None
    logger.warning("No Gemini API key found. Chatbot will not work.")

conversation_history: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = """You are a compassionate AI companion for patients with cognitive challenges.
Keep responses brief, warm, and clear."""

# --- Core Chatbot Functions ---
def get_conversation_history(patient_id: str) -> List[Dict[str, str]]:
    if patient_id not in conversation_history:
        conversation_history[patient_id] = []
    return conversation_history[patient_id]

def add_to_history(patient_id: str, role: str, content: str):
    if patient_id not in conversation_history:
        conversation_history[patient_id] = []
    conversation_history[patient_id].append({"role": role, "content": content})
    if len(conversation_history[patient_id]) > 10:
        conversation_history[patient_id] = conversation_history[patient_id][-10:]

def generate_response(patient_id: str, user_message: str) -> str:
    try:
        history = get_conversation_history(patient_id)
        add_to_history(patient_id, "user", user_message)

        model = genai.GenerativeModel(model_name=AI_MODEL, system_instruction=SYSTEM_PROMPT)
        
        chat_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            chat_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=chat_history)
        response = chat.send_message(user_message)
        assistant_response = response.text

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
        logger.info(f"File name: {audio.filename}, Content-Type: {audio.content_type}")

        audio_bytes = await audio.read()
        file_size = len(audio_bytes)
        logger.info(f"Read {file_size} bytes from uploaded file.")

        if file_size == 0:
            logger.error("Audio file is empty!")
            raise HTTPException(status_code=400, detail="Audio file is empty")

        # 1. Transcribe (Local Whisper)
        # Pass filename so we can detect .aac and convert it
        transcription = await transcribe_audio_bytes(audio_bytes, filename=audio.filename)
        
        if not transcription:
            logger.error("Transcription returned None/Empty")
            raise HTTPException(status_code=400, detail="Could not understand audio. Please speak clearly.")

        logger.info(f"Transcribed: {transcription}")

        # 2. AI Response
        response_text = generate_response(patient_id, transcription)

        # 3. Text to Speech (Local pyttsx3)
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
    return {"status": "healthy", "service": "chatbot", "mode": "local_hybrid"}