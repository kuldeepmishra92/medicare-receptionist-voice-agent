"""
LangGraph Nodes — Individual Agent Node Functions
Executes nodes in the 12-step voice appointment scheduling flow.
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.agents.state import AgentState
from app.agents.tools import ALL_TOOLS

SYSTEM_PROMPT = """
You are an intelligent hospital voice receptionist responsible for managing doctor appointments through natural conversations.

Your goal is to help patients book, reschedule, and cancel appointments while ensuring there are no duplicate bookings, scheduling conflicts, or repeated questions.

RULES TO FOLLOW ALWAYS:
1. Be polite, professional, and empathetic.
2. Ask only ONE question at a time.
3. Keep responses SHORT, concise, and voice-friendly (1-3 sentences max).
4. NEVER ask for information already collected (patient name, doctor name, phone, preferred date/time) unless user changes it.
5. Suggest up to THREE available slots when offering times.
6. Always summarize and confirm details (Patient Name, Doctor Name, Specialization, Date, Time) before final booking.
"""

_llm = None
_llm_with_tools = None


def get_llm():
    """Get or create the Groq LLM instance (lazy init)."""
    global _llm, _llm_with_tools
    if _llm is None:
        from langchain_groq import ChatGroq
        from app.config import settings
        if not settings.GROQ_API_KEY:
            # Fallback mock LLM if key is not configured yet
            class MockLLM:
                def invoke(self, messages):
                    last_text = messages[-1].content if messages else ""
                    return AIMessage(content=f"Hello! I am your hospital voice assistant. You said: '{last_text}'. How can I help you book, reschedule, or cancel an appointment today?")

                def bind_tools(self, tools):
                    return self

            return MockLLM(), MockLLM()

        _llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=settings.GROQ_API_KEY,
            temperature=0.2,
        )
        _llm_with_tools = _llm.bind_tools(ALL_TOOLS)
    return _llm, _llm_with_tools
def safe_invoke_llm(messages):
    llm, llm_with_tools = get_llm()
    try:
        return llm_with_tools.invoke(messages)
    except Exception as e:
        from loguru import logger
        logger.warning(f"⚠️ Tool invocation fallback ({e}), attempting fallback model or standard response.")
        if "429" in str(e) or "rate_limit" in str(e).lower():
            try:
                from langchain_groq import ChatGroq
                from app.config import settings
                fallback = ChatGroq(model="llama-3.1-8b-instant", api_key=settings.GROQ_API_KEY, temperature=0.2).bind_tools(ALL_TOOLS)
                return fallback.invoke(messages)
            except Exception as fb_e:
                logger.error(f"Fallback model failed: {fb_e}")
        try:
            return llm.invoke(messages)
        except Exception:
            return AIMessage(content="Hello! I am your hospital voice assistant. How can I help you book, reschedule, or cancel your appointment today?")



# ── Node: Understand Intent ───────────────────────────────
def intent_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = safe_invoke_llm(messages)

    last_msg = state["messages"][-1].content.lower() if state["messages"] else ""
    if any(w in last_msg for w in ["book", "schedule", "appointment", "see a doctor"]):
        intent = "book"
        next_step = "identify"
    elif any(w in last_msg for w in ["cancel", "remove"]):
        intent = "cancel"
        next_step = "modify"
    elif any(w in last_msg for w in ["reschedule", "change time", "move"]):
        intent = "reschedule"
        next_step = "modify"
    elif any(w in last_msg for w in ["available", "free", "slots"]):
        intent = "check_availability"
        next_step = "availability"
    else:
        intent = "general"
        next_step = "identify"

    return {**state, "messages": [response], "intent": intent, "next_step": next_step}


# ── Node: Identify Patient ────────────────────────────────
def identify_patient_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = safe_invoke_llm(messages)
    return {**state, "messages": [response], "next_step": "doctor"}


# ── Node: Doctor Selection ────────────────────────────────
def doctor_selection_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = safe_invoke_llm(messages)
    return {**state, "messages": [response], "next_step": "availability"}


# ── Node: Check Availability ──────────────────────────────
def availability_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = safe_invoke_llm(messages)
    return {**state, "messages": [response], "next_step": "slots"}


# ── Node: Suggest Slots ───────────────────────────────────
def slot_suggestion_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = safe_invoke_llm(messages)
    return {**state, "messages": [response], "next_step": "validate"}


# ── Node: Validate Slot ───────────────────────────────────
def validation_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = safe_invoke_llm(messages)
    return {**state, "messages": [response], "next_step": "confirm"}


# ── Node: Confirm Appointment ─────────────────────────────
def confirmation_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = safe_invoke_llm(messages)
    return {**state, "messages": [response], "next_step": "book"}


# ── Node: Book Appointment ────────────────────────────────
def booking_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = safe_invoke_llm(messages)
    return {**state, "messages": [response], "is_complete": True, "next_step": "end"}


# ── Node: Send Notification ───────────────────────────────
def notification_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = safe_invoke_llm(messages)
    return {**state, "messages": [response], "is_complete": True, "next_step": None}


# ── Node: Handle Modifications ────────────────────────────
def modification_node(state: AgentState) -> AgentState:
    llm, llm_with_tools = get_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {**state, "messages": [response], "is_complete": True, "next_step": None}
