"""
Chatbot module for Cogni Anchor
Handles conversational AI using Gemini API
"""

import logging
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
import google.generativeai as genai
import os
import tempfile
from app.services.stt_service import transcribe_audio_bytes
from app.services.tts_service import generate_speech_file

# --- Logging Setup ---
logger = logging.getLogger("ChatbotAPI")

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    """Model for incoming chat requests"""
    patient_id: str
    message: str
    mode: str = "text"  # "text" or "audio"

class ChatResponse(BaseModel):
    """Model for chat API response"""
    response: str
    patient_id: str
    mode: str

class Message(BaseModel):
    """Model for conversation message"""
    role: str  # "user" or "assistant"
    content: str

# --- AI API Configuration ---
# Use Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    AI_MODEL = "gemini-2.5-flash"
    logger.info("Using Gemini API for chatbot")
else:
    AI_MODEL = None
    logger.warning("No Gemini API key found. Chatbot will not work.")

# --- In-Memory Conversation Storage (temporary) ---
# In production, you'd use a database
conversation_history: Dict[str, List[Dict[str, str]]] = {}

# --- Chatbot System Prompt ---
SYSTEM_PROMPT = """You are a compassionate AI companion for patients with cognitive challenges.

Your role:
- Speak with warmth, patience, and clarity
- Use simple, short sentences (maximum 2 sentences per response)
- Be empathetic and understanding
- Help with daily tasks and provide emotional support
- Never correct the patient harshly
- Validate their feelings

Guidelines:
- Keep responses brief and clear
- Use friendly, conversational tone
- Offer reassurance when needed
- Be patient and never show frustration

Remember: You are here to help and comfort the patient."""

# --- Core Chatbot Functions ---
def get_conversation_history(patient_id: str) -> List[Dict[str, str]]:
    """Retrieve conversation history for a patient"""
    if patient_id not in conversation_history:
        conversation_history[patient_id] = []
    return conversation_history[patient_id]

def add_to_history(patient_id: str, role: str, content: str):
    """Add a message to conversation history"""
    if patient_id not in conversation_history:
        conversation_history[patient_id] = []

    conversation_history[patient_id].append({
        "role": role,
        "content": content
    })

    # Keep only last 10 messages to avoid token limits
    if len(conversation_history[patient_id]) > 10:
        conversation_history[patient_id] = conversation_history[patient_id][-10:]

def generate_response(patient_id: str, user_message: str) -> str:
    """
    Generate a response using Grok API

    Args:
        patient_id: Unique identifier for the patient
        user_message: The user's input message

    Returns:
        str: The AI-generated response
    """
    try:
        # Get conversation history
        history = get_conversation_history(patient_id)

        # Add user message to history
        add_to_history(patient_id, "user", user_message)

        logger.info(f"Sending request to Gemini API for patient {patient_id}")

        # Initialize Gemini model
        model = genai.GenerativeModel(
            model_name=AI_MODEL,
            system_instruction=SYSTEM_PROMPT
        )

        # Build conversation history for Gemini
        chat_history = []
        for msg in history:
            if msg["role"] == "user":
                chat_history.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                chat_history.append({"role": "model", "parts": [msg["content"]]})

        # Start chat with history
        chat = model.start_chat(history=chat_history)

        # Send message and get response
        response = chat.send_message(
            user_message,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=500,
            )
        )

        assistant_response = response.text

        # Add assistant response to history
        add_to_history(patient_id, "assistant", assistant_response)

        logger.info(f"Successfully generated response for patient {patient_id}")
        return assistant_response

    except Exception as e:
        logger.error(f"Error generating response with Gemini API: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}"
        )

def clear_conversation(patient_id: str):
    """Clear conversation history for a patient"""
    if patient_id in conversation_history:
        conversation_history[patient_id] = []
        logger.info(f"Cleared conversation history for patient {patient_id}")

# --- FastAPI Router ---
router = APIRouter(prefix="/api/v1/chat", tags=["Chatbot"])

@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """
    Handle incoming chat messages from Flutter app

    Request body:
    {
        "patient_id": "123",
        "message": "Hello, how are you?",
        "mode": "text"
    }

    Response:
    {
        "response": "Hello! I'm doing well. How can I help you today?",
        "patient_id": "123",
        "mode": "text"
    }
    """
    logger.info(f"Received chat message from patient {request.patient_id}: {request.message}")

    try:
        # Generate response using Grok
        response = generate_response(request.patient_id, request.message)

        return ChatResponse(
            response=response,
            patient_id=request.patient_id,
            mode=request.mode
        )

    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process chat message"
        )

@router.get("/history/{patient_id}")
async def get_history(patient_id: str):
    """
    Retrieve conversation history for a patient

    Response:
    {
        "patient_id": "123",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
    }
    """
    history = get_conversation_history(patient_id)

    return {
        "patient_id": patient_id,
        "messages": history
    }

@router.delete("/history/{patient_id}")
async def delete_history(patient_id: str):
    """
    Clear conversation history for a patient

    Response:
    {
        "message": "Conversation history cleared",
        "patient_id": "123"
    }
    """
    clear_conversation(patient_id)

    return {
        "message": "Conversation history cleared",
        "patient_id": patient_id
    }

@router.post("/voice")
async def voice_chat(
    audio: UploadFile = File(...),
    patient_id: str = Form("default_patient")
):
    """
    Handle voice input - transcribe audio, get AI response, return text + audio

    Request:
    - patient_id: Patient identifier (form data)
    - audio: Audio file (WAV, MP3, etc.)

    Response:
    {
        "patient_id": "123",
        "transcription": "Hello, how are you?",
        "response": "I'm doing well! How can I help you?",
        "audio_url": "/static/response_123.mp3"
    }
    """
    try:
        logger.info(f"Received voice message from patient {patient_id}")

        # Read audio file
        audio_bytes = await audio.read()

        # Step 1: Transcribe audio to text (STT)
        logger.info("Transcribing audio...")
        transcription = await transcribe_audio_bytes(audio_bytes)

        if not transcription:
            raise HTTPException(
                status_code=400,
                detail="Failed to transcribe audio. Please try again."
            )

        logger.info(f"Transcribed: {transcription}")

        # Step 2: Generate AI response using Grok
        logger.info("Generating AI response...")
        response_text = generate_response(patient_id, transcription)

        # Step 3: Convert response to speech (TTS)
        logger.info("Generating speech audio...")

        # Create unique filename for audio response
        import uuid
        audio_filename = f"response_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = f"temp/{audio_filename}"

        # Ensure temp directory exists
        os.makedirs("temp", exist_ok=True)

        # Generate audio file
        generated_audio = generate_speech_file(
            text=response_text,
            output_path=audio_path,
            voice="nova"  # Warm, friendly voice
        )

        # Return both text and audio
        return {
            "patient_id": patient_id,
            "transcription": transcription,
            "response": response_text,
            "audio_url": f"/temp/{audio_filename}" if generated_audio else None,
            "mode": "audio"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process voice message: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify chatbot service is running

    Response:
    {
        "status": "healthy",
        "service": "chatbot"
    }
    """
    return {
        "status": "healthy",
        "service": "chatbot",
        "api": "grok",
        "features": ["text_chat", "voice_chat", "stt", "tts"]
    }
