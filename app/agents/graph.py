"""
LangGraph Workflow — Multi-Agent Appointment Scheduling Graph
"""
from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.nodes import (
    intent_node,
    identify_patient_node,
    doctor_selection_node,
    availability_node,
    slot_suggestion_node,
    validation_node,
    confirmation_node,
    booking_node,
    notification_node,
    modification_node,
)

# ── Route map: next_step value → node name ────────────────
ROUTE_MAP = {
    "identify":     "identify",
    "doctor":       "select_doctor",
    "availability": "check_avail",
    "slots":        "suggest_slots",
    "validate":     "validate_slot",
    "confirm":      "confirm_appt",
    "book":         "book_appt",
    "notify":       "send_notify",
    "modify":       "modify_appt",
}


def router(state: AgentState) -> str:
    """Decide which node to go to next based on state."""
    if state.get("is_complete"):
        return END
    nxt = state.get("next_step", "")
    return ROUTE_MAP.get(nxt, END)


def build_graph() -> StateGraph:
    """Build and compile the LangGraph appointment workflow."""
    builder = StateGraph(AgentState)

    # ── Register all nodes ────────────────────────────────
    builder.add_node("detect_intent",  intent_node)
    builder.add_node("identify",       identify_patient_node)
    builder.add_node("select_doctor",  doctor_selection_node)
    builder.add_node("check_avail",    availability_node)
    builder.add_node("suggest_slots",  slot_suggestion_node)
    builder.add_node("validate_slot",  validation_node)
    builder.add_node("confirm_appt",   confirmation_node)
    builder.add_node("book_appt",      booking_node)
    builder.add_node("send_notify",    notification_node)
    builder.add_node("modify_appt",    modification_node)

    # ── Entry point ───────────────────────────────────────
    builder.set_entry_point("detect_intent")

    # ── All possible destinations ─────────────────────────
    destinations = list(ROUTE_MAP.values()) + [END]

    # ── Conditional edges from each node ──────────────────
    builder.add_conditional_edges("detect_intent", router, destinations)
    builder.add_conditional_edges("identify",      router, destinations)
    builder.add_conditional_edges("select_doctor", router, destinations)
    builder.add_conditional_edges("check_avail",   router, destinations)
    builder.add_conditional_edges("suggest_slots", router, destinations)
    builder.add_conditional_edges("validate_slot", router, destinations)
    builder.add_conditional_edges("confirm_appt",  router, destinations)
    builder.add_conditional_edges("book_appt",     router, destinations)
    builder.add_edge("send_notify",  END)
    builder.add_edge("modify_appt",  END)

    return builder.compile()


# ── Compiled graph (lazy — only built once at import) ─────
appointment_graph = build_graph()
