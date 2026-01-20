import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse 
from dotenv import load_dotenv

from app.api.v1.users import users_pairs
from app.api.v1.reminders import reminders
from app.api.v1.face_recognition import face_recognition
from app.api.v1.chatbot import patient_features, agent
from app.api.v1.audio import audio
from app.api.v1.location import location
from app import chatbot 
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

# Mount directories to serve files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/temp", StaticFiles(directory="temp"), name="temp") 

app.include_router(users_pairs.router)
app.include_router(reminders.router)
app.include_router(face_recognition.router)
app.include_router(patient_features.router)
app.include_router(agent.router)
app.include_router(chatbot.router) 
app.include_router(audio.router)
app.include_router(location.router)

@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.get("/privacy", response_class=HTMLResponse)
async def get_privacy_policy():
    privacy_path = os.path.join(os.getcwd(), "static", "privacy.html")
    if os.path.exists(privacy_path):
        with open(privacy_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse(content="Privacy Policy not found in static folder", status_code=404)

@app.get("/")
async def root():
    return {"message": "CogniAnchor API is running"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)