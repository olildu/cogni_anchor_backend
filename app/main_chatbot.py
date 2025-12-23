"""
CogniAnchor Complete API
Integrated backend with chatbot, face recognition, reminders, and user management
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CogniAnchorAPI")

# --- FastAPI Application ---
app = FastAPI(
    title="CogniAnchor Complete API",
    description="Backend API for cognitive health companion app - Full features",
    version="2.0.0"
)

# Add CORS middleware for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (adjust for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include all routers
from app.chatbot import router as chatbot_router
from app.routes.reminders import router as reminders_router
from app.routes.users_pairs import router as users_pairs_router
from app.routes.face_recognition import router as face_router

app.include_router(chatbot_router)
app.include_router(reminders_router)
app.include_router(users_pairs_router)
app.include_router(face_router)

@app.on_event("startup")
def startup_event():
    logger.info("CogniAnchor Complete API startup complete!")
    logger.info("API documentation available at: http://localhost:8000/docs")
    logger.info("Features: Chatbot, Face Recognition, Reminders, User Management")

@app.get("/")
def read_root():
    return {
        "message": "CogniAnchor Complete API",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "AI Chatbot (Gemini)",
            "Face Recognition (DeepFace)",
            "Reminder Management",
            "User & Pair Management",
            "Voice Chat (STT/TTS)"
        ],
        "endpoints": {
            "docs": "/docs",
            "chat": "/api/v1/chat/*",
            "reminders": "/api/v1/reminders/*",
            "users": "/api/v1/users/*",
            "pairs": "/api/v1/pairs/*",
            "face": "/api/v1/face/*"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
