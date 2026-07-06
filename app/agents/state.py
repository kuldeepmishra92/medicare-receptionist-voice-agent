"""
Agent State — LangGraph Conversation State
"""
from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state across all agent nodes in the LangGraph workflow."""

    # ── Conversation ──────────────────────────────────────
    messages: Annotated[list, add_messages]
    intent: Optional[str]                   # book | cancel | reschedule | check_availability | inquiry

    # ── Patient Context ───────────────────────────────────
    patient_id: Optional[str]
    patient_name: Optional[str]
    patient_phone: Optional[str]
    patient_email: Optional[str]
    patient_found: Optional[bool]

    # ── Doctor Context ────────────────────────────────────
    doctor_id: Optional[str]
    doctor_name: Optional[str]
    specialization: Optional[str]
    symptoms: Optional[str]

    # ── Appointment Context ───────────────────────────────
    preferred_date: Optional[str]
    preferred_time: Optional[str]
    selected_slot: Optional[str]
    appointment_id: Optional[str]
    confirmed: Optional[bool]

    # ── Flow Control ──────────────────────────────────────
    next_step: Optional[str]
    error_message: Optional[str]
    is_complete: Optional[bool]
