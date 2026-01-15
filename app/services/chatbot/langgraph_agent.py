import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.chatbot.agent_tools import (
    create_reminder,
    list_reminders,
    delete_reminder,
    send_emergency_alert
)

logger = logging.getLogger("SimpleAgent")

TOOL_MAP = {
    "create_reminder": create_reminder,
    "list_reminders": list_reminders,
    "delete_reminder": delete_reminder,
    "send_emergency_alert": send_emergency_alert
}

SYSTEM_PROMPT = """You are a helpful assistant for a patient with dementia.
Your goal is to manage their reminders and alerts.

AVAILABLE TOOLS:
1. create_reminder(pair_id, title, date, time): Use for "remind me", "set alarm".
   - date format: 'dd MMM yyyy' (e.g., 25 Dec 2024).
   - time format: 'hh:mm AM/PM' (e.g., 05:00 PM).
2. list_reminders(pair_id): Use for "what are my reminders?".
3. delete_reminder(pair_id, reminder_title): Use for "delete reminder".
4. send_emergency_alert(pair_id, reason): Use for "help", "emergency".

CURRENT CONTEXT:
- Date: {current_date}
- Time: {current_time}
- Pair ID: {pair_id}

RULES:
- If the user asks to do something, CALL THE TOOL.
- Do not ask for confirmation, just do it.
- If the date is missing, assume TODAY ({current_date}).
"""

def get_llm():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")
    
    # Low temp for deterministic tool usage
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=api_key,
        temperature=0.1
    )
    
    tools = [create_reminder, list_reminders, delete_reminder, send_emergency_alert]
    return llm.bind_tools(tools)

async def run_agent(patient_id: str, pair_id: str, message: str, conversation_history: list = None) -> str:
    """
    Standard agent flow: User Input -> LLM -> Tool? -> Result
    """
    try:
        llm = get_llm()
        
        now = datetime.now()
        formatted_prompt = SYSTEM_PROMPT.format(
            current_date=now.strftime("%d %b %Y"),
            current_time=now.strftime("%I:%M %p"),
            pair_id=pair_id
        )

        messages = [SystemMessage(content=formatted_prompt)]
        
        # Inject limited history to maintain context without overloading
        if conversation_history:
            for msg in conversation_history[-4:]: 
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))

        messages.append(HumanMessage(content=message))

        logger.info(f"Invoking Agent for: {message}")
        
        # 1. Get LLM decision
        response = await llm.ainvoke(messages)

        # 2. Handle tool calls if present
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            logger.info(f"Agent selected tool: {tool_name} with args: {tool_args}")
            
            if tool_name in TOOL_MAP:
                tool_func = TOOL_MAP[tool_name]
                
                # Fix pair_id injection if the LLM hallucinated or missed it
                if "pair_id" not in tool_args or tool_args["pair_id"] != pair_id:
                    tool_args["pair_id"] = pair_id

                try:
                    result = tool_func.invoke(tool_args)
                    logger.info(f"Tool Result: {result}")
                    return result
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    return f"I tried to do that, but something went wrong: {str(e)}"
            else:
                return "I tried to use a tool I don't have."
        
        # 3. Fallback to simple text response
        return response.content or "I heard you, but I'm not sure what to do."

    except Exception as e:
        logger.error(f"Agent Critical Error: {e}")
        return "I'm having trouble connecting right now. Please try again."

# --- History Management ---
agent_conversations = {}

def get_agent_history(patient_id: str):
    if patient_id not in agent_conversations: agent_conversations[patient_id] = []
    return agent_conversations[patient_id]

def add_to_agent_history(patient_id: str, role: str, content: str):
    if patient_id not in agent_conversations: agent_conversations[patient_id] = []
    agent_conversations[patient_id].append({"role": role, "content": content})
    
    # Cap history size
    if len(agent_conversations[patient_id]) > 10:
        agent_conversations[patient_id] = agent_conversations[patient_id][-10:]