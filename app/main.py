import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.api.v1.users import users_pairs
from app.api.v1.reminders import reminders
from app.api.v1.face_recognition import face_recognition
from app.api.v1.chatbot import patient_features, agent
from app.api.v1.audio import audio
from app.api.v1.location import location
from app.services.infra.scheduler import start_scheduler

load_dotenv()

app = FastAPI(title="CogniAnchor Complete API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/uploads", exist_ok=True)
os.makedirs("temp", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# FIX: Removed redundant 'prefix' arguments. 
# Relies on prefixes defined inside the router files.
app.include_router(users_pairs.router)
app.include_router(reminders.router)
app.include_router(face_recognition.router)
app.include_router(patient_features.router)
app.include_router(agent.router)
app.include_router(audio.router)
app.include_router(location.router)

@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.get("/")
async def root():
    return {"message": "CogniAnchor API is running"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)