"""
LangGraph Agent for CogniAnchor
Intelligent agent with tool-calling capabilities for dementia care
"""

import logging
import os
from datetime import datetime # Added datetime import
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.agent_tools import (
    create_reminder,
    list_reminders,
    delete_reminder,
    send_emergency_alert
)

logger = logging.getLogger("LangGraphAgent")

# === Agent State ===

class AgentState(TypedDict):
    """State for the agent graph"""
    messages: Annotated[Sequence[BaseMessage], "The conversation messages"]
    pair_id: str
    patient_id: str


# === System Prompt for Agent ===

AGENT_SYSTEM_PROMPT = """You are a compassionate AI companion for patients with cognitive challenges (dementia/Alzheimer's).

Your role:
- Provide warm, patient, and clear communication
- Help manage daily tasks through reminders
- Offer emotional support and reassurance
- Monitor for signs of distress or danger
- Use simple, short sentences (maximum 2 sentences per response)

Available Tools:
1. create_reminder: Set reminders. REQUIRED ARGUMENT: pair_id (I will provide this).
2. list_reminders: Show upcoming reminders. REQUIRED ARGUMENT: pair_id.
3. delete_reminder: Cancel reminders. REQUIRED ARGUMENT: pair_id.
4. send_emergency_alert: Alert caregiver. REQUIRED ARGUMENT: pair_id.

Guidelines:
- ALWAYS pass the provided 'Current Pair ID' to tools as the 'pair_id' argument. Never invent a pair_id.
- Be proactive: If patient mentions taking medicine, suggest creating a reminder.
- Validate their feelings and provide reassurance.
"""


# === Initialize LLM with Tools ===

def create_agent_llm():
    """Create LLM with tool binding"""
    try:
        gemini_api_key = os.getenv("GEMINI_API_KEY")

        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=gemini_api_key,
            temperature=0.7,
            max_output_tokens=500
        )

        tools = [create_reminder, list_reminders, delete_reminder, send_emergency_alert]
        llm_with_tools = llm.bind_tools(tools)

        return llm_with_tools, tools

    except Exception as e:
        logger.error(f"Failed to initialize agent LLM: {e}")
        raise


# === Agent Nodes ===

def call_agent(state: AgentState):
    """
    Agent node: Calls the LLM to decide next action
    """
    try:
        llm_with_tools, _ = create_agent_llm()

        # FIX: Explicitly inject IDs AND Current Date into the system prompt
        current_pair_id = state.get("pair_id", "UNKNOWN")
        current_patient_id = state.get("patient_id", "UNKNOWN")
        current_time = datetime.now().strftime("%d %b %Y %I:%M %p") # e.g. "07 Jan 2026 04:45 PM"
        
        dynamic_prompt = (
            f"{AGENT_SYSTEM_PROMPT}\n\n"
            f"CONTEXT DATA:\n"
            f"Current Date & Time: {current_time}\n"
            f"Current Patient ID: {current_patient_id}\n"
            f"Current Pair ID: {current_pair_id}\n"
            f"(Use '{current_pair_id}' for all tool calls requiring pair_id)"
        )

        # Build messages with dynamic system prompt
        messages = [
            SystemMessage(content=dynamic_prompt)
        ] + state["messages"]

        # Call LLM
        response = llm_with_tools.invoke(messages)

        logger.info(f"Agent response: {response.content if hasattr(response, 'content') else 'Tool call'}")

        return {"messages": [response]}

    except Exception as e:
        logger.error(f"Error in agent node: {e}")
        error_msg = AIMessage(content="I'm having trouble right now. Let me try to help you anyway.")
        return {"messages": [error_msg]}


def should_continue(state: AgentState):
    """
    Conditional edge: Determine if we should continue to tools or end
    """
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        logger.info(f"Agent calling {len(last_message.tool_calls)} tool(s)")
        return "tools"

    logger.info("Agent finished - no more tool calls")
    return END


# === Build Agent Graph ===

def create_agent_graph():
    """
    Create the LangGraph agent workflow
    """
    try:
        _, tools = create_agent_llm()
        workflow = StateGraph(AgentState)

        workflow.add_node("agent", call_agent)
        workflow.add_node("tools", ToolNode(tools))

        workflow.set_entry_point("agent")

        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END
            }
        )

        workflow.add_edge("tools", "agent")

        return workflow.compile()

    except Exception as e:
        logger.error(f"Failed to create agent graph: {e}")
        raise


# === Agent Execution ===

async def run_agent(patient_id: str, pair_id: str, message: str, conversation_history: list = None) -> str:
    """
    Run the agent with a user message
    """
    try:
        logger.info(f"Running agent for patient {patient_id}: {message}")

        agent = create_agent_graph()
        messages = []

        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=message))

        # Pass IDs into the state
        initial_state = {
            "messages": messages,
            "pair_id": pair_id,
            "patient_id": patient_id
        }

        final_state = await agent.ainvoke(initial_state)

        final_messages = final_state["messages"]

        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content:
                logger.info(f"Agent completed successfully")
                return msg.content

        return "I'm here to help. What would you like to know?"

    except Exception as e:
        logger.error(f"Error running agent: {e}")
        return "I'm having some trouble right now, but I'm here with you. How can I help?"


# === Conversation Memory ===
agent_conversations = {}

def get_agent_history(patient_id: str):
    if patient_id not in agent_conversations:
        agent_conversations[patient_id] = []
    return agent_conversations[patient_id]

def add_to_agent_history(patient_id: str, role: str, content: str):
    if patient_id not in agent_conversations:
        agent_conversations[patient_id] = []

    agent_conversations[patient_id].append({
        "role": role,
        "content": content
    })

    if len(agent_conversations[patient_id]) > 10:
        agent_conversations[patient_id] = agent_conversations[patient_id][-10:]