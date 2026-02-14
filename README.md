<p align="center">
  <img src="https://raw.githubusercontent.com/olildu/cogni_anchor/main/assets/images/icons/icon.png" 
       alt="Cogni Anchor Logo" 
       width="180">
</p>

# 🧠 Cogni Anchor: AI-Powered Dementia Support (Backend)

The intelligent backbone of the Cogni Anchor ecosystem, providing an AI-driven safety net for dementia patients and real-time monitoring tools for caregivers. Built with **FastAPI**, **LangGraph**, and **PostgreSQL**.

<p align="center">
  <a href="https://x.com/olildu">
    <img src="https://img.shields.io/twitter/follow/olildu.svg?style=social&label=Follow" alt="Twitter">
  </a>
  &nbsp;&nbsp;
  <a href="https://www.linkedin.com/in/ebinsanthosh/">
    <img src="https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin&logoColor=white" alt="LinkedIn">
  </a>
</p>

## 🌟 Project Highlights & Technical Differentiators

This project was developed as a **Deloitte Capstone Project** and selected from **50+ teams** for its sophisticated use of AI agents and safety-critical engineering.

| Feature | Technical Implementation | Engineering Value Demonstrated |
| :--- | :--- | :--- |
| **AI Agent Orchestration** | **LangGraph** + **OpenAI/Anthropic** (`langgraph_agent.py`) | Stateful, multi-turn AI reasoning with specialized tools for cognitive aid |
| **Real-Time Safety** | **WebSockets** + **Geofencing** (`websocket_manager.py`) | Instant caretaker alerts based on patient location anomalies |
| **Voice Interaction** | **Whisper (STT)** + **TTS Services** (`stt_service.py`, `tts_service.py`) | Natural, hardware-abstracted voice interface for accessibility |
| **Identity Verification** | **Face Recognition API** (`face_recognition_service.py`) | Secure verification of family members to reduce patient anxiety |

## 🧱 Architecture Overview: AI & Infrastructure

Cogni Anchor uses a modular microservices-inspired architecture designed for high reliability and low-latency responses.

### **AI Core (`app/services/chatbot`)**
- **LangGraph Agent** — Implements a state-machine based chatbot that maintains patient context and uses tools to fetch reminders or patient info.
- **Agent Tools** — Custom Python functions allowing the AI to interact with the database and external APIs securely.

### **Audio & Vision Services (`app/services/audio`, `face_recognition`)**
- **STT/TTS Pipeline** — Combines OpenAI Whisper for high-accuracy Speech-to-Text and local/cloud TTS for rapid audio feedback.
- **Face Recognition** — Backend validation for family member identification, supporting the on-device MobileFaceNet model.

### **Safety Infrastructure (`app/services/infra`)**
- **WebSocket Manager** — Manages live connections for real-time location streaming and emergency notifications.
- **Automated Scheduler** — Uses **APScheduler** to trigger medication and appointment reminders via Firebase Cloud Messaging.

## ⚙️ Core API Modules

| Module | Purpose | Key Endpoints |
| :--- | :--- | :--- |
| **Chatbot API** | AI-driven patient assistance | `/api/v1/chatbot/agent` |
| **Location API** | Live tracking and geofencing | `/api/v1/location/` |
| **Reminders** | CRUD for medication/task schedules | `/api/v1/reminders/` |
| **User Pairing** | Secure patient-caretaker linking | `/api/v1/users/` |

## 🛠️ Development Setup

Requires **Python 3.11+** and **PostgreSQL**.

### **Installation**

1. **Clone the Repository:**
   ```bash
    git clone https://github.com/olildu/cogni_anchor_backend.git
    cd cogni_anchor_backend
   ```

2. **Environment Configuration:**
   ```bash
    DATABASE_URL=postgresql://user:password@localhost/cogni_anchor
    OPENAI_API_KEY=your_key
    FIREBASE_CREDENTIALS_PATH=path/to/firebase.json
   ```

3. **Environment Configuration:**
   ```bash
    pip install -r req.txt
    python -m app.main
   ```
   
   ## 📱 Ecosystem Logic

Cogni Anchor is designed for a **Caretaker–Patient** relationship.  
The backend infrastructure ensures a proactive safety net through the following core functionalities:

- **Caregiver Controls:**  
  Caretakers can remotely set precise geofences and schedules via the mobile application to monitor patient activity.

- **AI-Driven Assistance:**  
  The integrated AI agent proactively assists patients using natural voice commands, helping with daily tasks and cognitive recall.

- **Real-Time Alerts:**  
  If a patient exits a designated geofence, a high-priority WebSocket alert is pushed to the caretaker instantly to ensure rapid response and safety.

---

**MENTORED BY DELOITTE | Capstone Project 2026**
