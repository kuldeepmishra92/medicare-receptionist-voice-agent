"""
API Route — Voice (Vapi AI + ElevenLabs STT & TTS Handlers)
Handles Speech-to-Text and Text-to-Speech via ElevenLabs.
"""
from fastapi import APIRouter, Request, HTTPException, File, UploadFile, Response
from pydantic import BaseModel
from typing import Optional
from langchain_core.messages import HumanMessage
from loguru import logger

from app.agents.graph import appointment_graph
from app.agents.state import AgentState
from app.services.elevenlabs_service import elevenlabs_service
from app.database import AsyncSessionLocal
from app.schemas.patient import PatientCreate, PatientUpdate
from app.schemas.appointment import AppointmentCreate
from app.services import patient_service, doctor_service, appointment_service
from app.services.notification_service import notification_service
from datetime import datetime, timedelta
import re

router = APIRouter()

VOICE_SESSIONS: dict[str, dict] = {}

SYMPTOM_SPECIALIZATION = {
    "chest": "Cardiologist",
    "heart": "Cardiologist",
    "skin": "Dermatologist",
    "rash": "Dermatologist",
    "eye": "Ophthalmologist",
    "vision": "Ophthalmologist",
    "ear": "ENT Specialist",
    "hearing": "ENT Specialist",
    "body pain": "General Physician",
    "body": "General Physician",
    "pain": "General Physician",
    "fever": "General Physician",
    "cold": "General Physician",
}


def _detect_specialization(text: str) -> Optional[str]:
    lowered = text.lower()
    for keyword, specialization in SYMPTOM_SPECIALIZATION.items():
        if keyword in lowered:
            return specialization
    return None


def _is_yes(text: str) -> bool:
    lowered = text.lower().strip()
    return lowered in {"yes", "yes yes", "yeah", "yep", "ok", "okay", "sure", "please", "book it"}

def _has_any_word(text: str, words: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def _is_general_inquiry(text: str) -> bool:
    inquiry_words = ["service", "services", "provide", "facility", "facilities", "hospital", "available"]
    return _has_any_word(text, inquiry_words) and not _has_any_word(text, ["appointment", "book", "schedule"])

def _general_inquiry_reply(text: str) -> Optional[str]:
    lowered = text.lower()
    if any(phrase in lowered for phrase in [
        "how do you answer", "how do you ans", "how do you work", "what can you do",
        "who are you", "are you ai", "are you listening", "help me",
    ]):
        return (
            "I am the hospital voice receptionist. I can answer basic hospital questions and help book, "
            "reschedule, or cancel doctor appointments. For booking, I will ask the reason, doctor type, "
            "patient name, phone number, email, date, and time."
        )
    if any(phrase in lowered for phrase in [
        "doctor type", "doctor types", "types of doctor", "types of doctors",
        "specialties", "specializations", "speciality", "what doctors", "doctore type", "doctore types"
    ]) or ("doctor" in lowered and "type" in lowered) or ("doctore" in lowered and "type" in lowered) or _is_general_inquiry(lowered):
        return (
            "Our hospital has specialists across multiple disciplines: General Physician, "
            "Cardiologist (heart), Dermatologist (skin), Ophthalmologist (eyes), ENT Specialist (ear, nose, throat), "
            "Pediatrician (child care), Orthopedist (bones/joints), and Psychiatrist (mental health). "
            "Which doctor type would you like to consult or book an appointment with?"
        )
    return None


def _parse_requested_datetime(text: str) -> Optional[datetime]:
    lowered = text.lower().strip()
    base = datetime.now().replace(second=0, microsecond=0)

    if "tomorrow" in lowered:
        day = base.date() + timedelta(days=1)
    elif "today" in lowered:
        day = base.date()
    else:
        for fmt in ("%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(text.strip(), fmt)
            except ValueError:
                pass
        return None

    hour = 10
    minute = 0
    import re
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", lowered)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        suffix = match.group(3)
        if suffix == "pm" and hour < 12:
            hour += 12
        if suffix == "am" and hour == 12:
            hour = 0
    return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)


def _looks_like_email(text: str) -> bool:
    return "@" in text and "." in text.split("@")[-1]


def _looks_like_phone(text: str) -> bool:
    digits = "".join(ch for ch in text if ch.isdigit())
    return len(digits) >= 10

def _normalize_spoken_email(text: str) -> str:
    email = text.lower().strip()
    prefixes = [
        "i given", "i gave", "my email is", "email is", "mail is",
        "my mail is", "new email is", "new mail is", "it is", "this is",
    ]
    for prefix in prefixes:
        if email.startswith(prefix):
            email = email[len(prefix):].strip()
            break
    replacements = {
        " at the rate ": "@",
        " at ": "@",
        " dot ": ".",
        " point ": ".",
        " underscore ": "_",
        " dash ": "-",
        " hyphen ": "-",
    }
    email = f" {email} "
    for old, new in replacements.items():
        email = email.replace(old, new)
    return "".join(email.strip().split())


def _normalize_phone(text: str) -> str:
    digits = "".join(ch for ch in text if ch.isdigit())
    if text.strip().startswith("+"):
        return "+" + digits
    return digits


def _correction_target(text: str) -> Optional[str]:
    lowered = text.lower()
    correction_words = ["update", "change", "correct", "wrong", "mistake", "missing", "edit", "replace"]
    if not any(word in lowered for word in correction_words):
        return None
    if any(word in lowered for word in ["mail", "email", "gmail"]):
        return "patient_email"
    if any(word in lowered for word in ["phone", "mobile", "number"]):
        return "patient_phone"
    if "name" in lowered:
        return "patient_name"
    if any(word in lowered for word in ["time", "date", "schedule"]):
        return "preferred_time"
    if any(word in lowered for word in ["reason", "symptom", "doctor type", "doctor"]):
        return "symptom"
    return None


def _clear_after_edit(state: dict, field: str) -> None:
    reset_map = {
        "symptom": ["symptom", "specialization", "patient_name", "patient_phone", "patient_email", "preferred_time", "confirmed", "appointment_id"],
        "patient_name": ["patient_name", "patient_phone", "patient_email", "preferred_time", "confirmed", "appointment_id"],
        "patient_phone": ["patient_phone", "patient_email", "preferred_time", "confirmed", "appointment_id"],
        "patient_email": ["patient_email", "preferred_time", "confirmed", "appointment_id"],
        "preferred_time": ["preferred_time", "confirmed", "appointment_id"],
    }
    for key in reset_map.get(field, [field]):
        state.pop(key, None)


async def _send_professional_confirmation_email(patient, doctor, appointment) -> None:
    if not patient.email:
        return

    date_str = appointment.appointment_date.strftime("%d %B %Y")
    time_str = appointment.appointment_date.strftime("%I:%M %p")
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 680px; margin: 0 auto; color: #111;">
        <h2 style="margin-bottom: 8px;">Appointment Confirmation</h2>
        <p>Dear <strong>{patient.full_name}</strong>,</p>
        <p>Your appointment has been scheduled successfully. Please find the details below.</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #ddd;">
            <tr><th style="text-align:left; padding: 10px; border: 1px solid #ddd; background:#f5f5f5;">Appointment ID</th><td style="padding: 10px; border: 1px solid #ddd;">{appointment.appointment_id}</td></tr>
            <tr><th style="text-align:left; padding: 10px; border: 1px solid #ddd; background:#f5f5f5;">Patient Name</th><td style="padding: 10px; border: 1px solid #ddd;">{patient.full_name}</td></tr>
            <tr><th style="text-align:left; padding: 10px; border: 1px solid #ddd; background:#f5f5f5;">Phone Number</th><td style="padding: 10px; border: 1px solid #ddd;">{patient.phone_number}</td></tr>
            <tr><th style="text-align:left; padding: 10px; border: 1px solid #ddd; background:#f5f5f5;">Doctor</th><td style="padding: 10px; border: 1px solid #ddd;">{doctor.full_name}</td></tr>
            <tr><th style="text-align:left; padding: 10px; border: 1px solid #ddd; background:#f5f5f5;">Doctor Type</th><td style="padding: 10px; border: 1px solid #ddd;">{doctor.specialization}</td></tr>
            <tr><th style="text-align:left; padding: 10px; border: 1px solid #ddd; background:#f5f5f5;">Date</th><td style="padding: 10px; border: 1px solid #ddd;">{date_str}</td></tr>
            <tr><th style="text-align:left; padding: 10px; border: 1px solid #ddd; background:#f5f5f5;">Time</th><td style="padding: 10px; border: 1px solid #ddd;">{time_str}</td></tr>
            <tr><th style="text-align:left; padding: 10px; border: 1px solid #ddd; background:#f5f5f5;">Status</th><td style="padding: 10px; border: 1px solid #ddd;">Confirmed</td></tr>
        </table>
        <p>Please arrive 10 minutes before your scheduled time.</p>
        <p style="margin-top: 24px;">Regards,<br><strong>Hospital Appointment Desk</strong></p>
    </div>
    """
    await notification_service.send_email(
        to=patient.email,
        subject=f"Appointment Confirmed - {appointment.appointment_id}",
        html_body=html_body,
    )


async def _create_real_appointment_from_state(state: dict):
    requested_dt = _parse_requested_datetime(state.get("preferred_time", ""))
    if not requested_dt:
        raise ValueError("Please provide date and time like 'tomorrow 10 AM' or '2026-07-10 10:00'.")

    async with AsyncSessionLocal() as db:
        patient = await patient_service.get_patient_by_phone(db, state["patient_phone"])
        if patient:
            patient = await patient_service.update_patient(
                db,
                patient.id,
                PatientUpdate(full_name=state["patient_name"], email=state["patient_email"]),
            )
        else:
            patient = await patient_service.create_patient(
                db,
                PatientCreate(
                    full_name=state["patient_name"],
                    phone_number=state["patient_phone"],
                    email=state["patient_email"],
                ),
            )

        doctors = await doctor_service.list_doctors(db, specialization=state["specialization"])
        if not doctors:
            raise ValueError(f"No active doctor found for {state['specialization']}.")
        doctor = doctors[0]

        appointment = await appointment_service.create_appointment(
            db,
            AppointmentCreate(
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_date=requested_dt,
                notes=f"Booked by voice simulator. Reason: {state.get('symptom', 'Not provided')}",
            ),
        )
        await db.commit()
        return patient, doctor, appointment


async def _fast_simulator_reply(user_speech: str, phone_number: Optional[str], session_id: str) -> Optional[str]:
    """Fast deterministic appointment flow for the dashboard voice simulator."""
    text = user_speech.strip()
    lowered = text.lower()
    state = VOICE_SESSIONS.setdefault(session_id, {})

    edit_field = state.pop("editing_field", None)
    if edit_field:
        if edit_field == "patient_email":
            normalized_email = _normalize_spoken_email(text)
            if not _looks_like_email(normalized_email):
                state["editing_field"] = "patient_email"
                return "That still does not look like a valid email. Please say or type it like name@example.com."
            state["patient_email"] = normalized_email
            return f"Email updated to {normalized_email}. What date and time would you prefer?"
        if edit_field == "patient_phone":
            normalized_phone = _normalize_phone(text)
            if not _looks_like_phone(normalized_phone):
                state["editing_field"] = "patient_phone"
                return "That phone number still looks incomplete. Please provide at least 10 digits."
            state["patient_phone"] = normalized_phone
            return "Phone number updated. Please share the patient email address for the appointment confirmation."
        if edit_field == "patient_name":
            state["patient_name"] = text
            return "Name updated. Please share the patient phone number."
        if edit_field == "preferred_time":
            requested_dt = _parse_requested_datetime(text)
            if not requested_dt:
                state["editing_field"] = "preferred_time"
                return "Please provide date and time like tomorrow 10 AM or 2026-07-10 10:00."
            state["preferred_time"] = text
            date_str = requested_dt.strftime("%d %B %Y")
            time_str = requested_dt.strftime("%I:%M %p")
            return f"Appointment time updated to {date_str} at {time_str}. Should I book it?"

    correction = _correction_target(text)
    if correction:
        _clear_after_edit(state, correction)
        state["editing_field"] = correction
        if correction == "patient_email":
            return "No problem. Please provide the correct email address."
        if correction == "patient_phone":
            return "No problem. Please provide the correct phone number."
        if correction == "patient_name":
            return "No problem. Please provide the correct patient name."
        if correction == "preferred_time":
            return "No problem. Please provide the correct date and time."
        if correction == "symptom":
            return "No problem. Please tell me the correct reason for the visit."

    if _is_general_inquiry(lowered):
        return None

    if _has_any_word(lowered, ["hello", "hi", "hey", "listening"]):
        state["intent"] = "book"
        return "Yes, I am listening. I can help you book a doctor appointment. What is the reason for your visit?"

    wants_booking = _has_any_word(lowered, ["appointment", "book", "schedule", "doctor"])
    if wants_booking and not state.get("intent"):
        state["intent"] = "book"
        return "Sure. What is the reason for your visit?"

    if state.get("intent") == "book" and not state.get("symptom"):
        state["symptom"] = text
        specialization = _detect_specialization(text) or "General Physician"
        state["specialization"] = specialization
        return f"Based on your reason, the doctor type is {specialization}. Shall I continue with this doctor type?"

    if _is_yes(text) and state.get("specialization") and not state.get("patient_name"):
        return "Please tell me the patient full name."

    if state.get("specialization") and not state.get("patient_name"):
        state["patient_name"] = text
        if state.get("patient_phone"):
            return "Please share the patient email address for the appointment confirmation."
        return "Please share the patient phone number."

    if state.get("patient_name") and not state.get("patient_phone"):
        normalized_phone = _normalize_phone(text)
        if not _looks_like_phone(normalized_phone):
            return "Please provide a valid phone number with at least 10 digits."
        state["patient_phone"] = normalized_phone
        return "Please share the patient email address for the appointment confirmation."

    if state.get("patient_name") and not state.get("patient_email"):
        normalized_email = _normalize_spoken_email(text)
        if not _looks_like_email(normalized_email):
            return "Please provide a valid email address, for example name@example.com. You can also say it like name dot test at gmail dot com."
        state["patient_email"] = normalized_email
        return "What date and time would you prefer? You can say 'tomorrow 10 AM' or '2026-07-10 10:00'."

    if state.get("patient_email") and not state.get("preferred_time"):
        requested_dt = _parse_requested_datetime(text)
        if not requested_dt:
            return "Please provide date and time like 'tomorrow 10 AM' or '2026-07-10 10:00'."
        state["preferred_time"] = text
        date_str = requested_dt.strftime("%d %B %Y")
        time_str = requested_dt.strftime("%I:%M %p")
        return (
            f"Please confirm: {state['patient_name']} with a {state['specialization']} "
            f"on {date_str} at {time_str}. Confirmation will be sent to {state['patient_email']}. Should I book it?"
        )

    if _is_yes(text) and state.get("preferred_time") and not state.get("confirmed"):
        try:
            patient, doctor, appointment = await _create_real_appointment_from_state(state)
            state["confirmed"] = True
            state["appointment_id"] = appointment.appointment_id
            return (
                f"Appointment booked successfully. Appointment ID is {appointment.appointment_id}. "
                f"Doctor: {doctor.full_name}, {doctor.specialization}. A professional confirmation email has been sent to {patient.email}."
            )
        except Exception as exc:
            logger.error(f"Appointment booking failed: {exc}")
            state.pop("preferred_time", None)
            return f"I could not book that appointment: {exc} Please provide another date and time."

    return None

class SimpleVoiceMessage(BaseModel):
    """Simple API message for testing and custom integrations."""
    message: str
    phone_number: Optional[str] = None
    session_id: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None


class VoiceResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
    is_complete: bool = False
    audio_url: Optional[str] = None


@router.post("/webhook", response_model=VoiceResponse)
async def vapi_webhook(request: Request):
    """
    Vapi AI Webhook Handler:
    Supports standard Vapi AI payload format AND simple test payload.
    """
    try:
        body = await request.json()
        logger.info(f"🎙️ Voice Webhook Payload: {body}")

        # Extract user speech and phone number from payload
        user_speech = ""
        phone_number = None
        session_id = body.get("session_id") or body.get("call", {}).get("id")

        if "message" in body and isinstance(body["message"], str):
            user_speech = body["message"]
            phone_number = body.get("phone_number")
        elif "message" in body and isinstance(body["message"], dict):
            # Standard Vapi AI payload structure
            msg_obj = body["message"]
            user_speech = msg_obj.get("transcript") or msg_obj.get("text") or ""
            phone_number = body.get("call", {}).get("customer", {}).get("number")
        elif "transcript" in body:
            user_speech = body["transcript"]
            phone_number = body.get("customer_phone")

        if not user_speech:
            user_speech = "Hello, I want to book an appointment."

        if not session_id:
            session_id = phone_number or "default_voice_session"

        fast_reply = await _fast_simulator_reply(user_speech, None, session_id or "default")
        if fast_reply:
            logger.info(f"Fast simulator response: '{fast_reply}'")
            return VoiceResponse(response=fast_reply, session_id=session_id, is_complete=False)

        general_reply = _general_inquiry_reply(user_speech)
        if general_reply:
            logger.info(f"General inquiry response: '{general_reply}'")
            return VoiceResponse(response=general_reply, session_id=session_id, is_complete=False)

        # Initialize agent state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_speech)],
            "intent": None,
            "patient_id": None,
            "patient_name": None,
            "patient_phone": phone_number,
            "patient_email": None,
            "patient_found": None,
            "doctor_id": None,
            "doctor_name": None,
            "specialization": None,
            "symptoms": None,
            "preferred_date": None,
            "preferred_time": None,
            "selected_slot": None,
            "appointment_id": None,
            "confirmed": None,
            "next_step": None,
            "error_message": None,
            "is_complete": False,
        }

        # Execute LangGraph Agent
        result = await appointment_graph.ainvoke(initial_state)

        # Extract last AIMessage
        last_message = "I'm here to help you schedule, reschedule, or cancel your doctor appointment. How can I assist you today?"
        if result.get("messages"):
            for m in reversed(result["messages"]):
                if hasattr(m, "content") and m.content:
                    last_message = m.content
                    break

        logger.info(f"🤖 Agent Voice Response: '{last_message}'")

        return VoiceResponse(
            response=last_message,
            session_id=session_id,
            is_complete=result.get("is_complete", False),
        )

    except Exception as e:
        logger.error(f"❌ Voice Webhook Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts")
async def text_to_speech(payload: TTSRequest):
    """
    Generate MP3 voice audio from text using ElevenLabs TTS.
    """
    audio_bytes = await elevenlabs_service.text_to_speech(payload.text, voice_id=payload.voice_id)
    if not audio_bytes:
        raise HTTPException(status_code=503, detail="ElevenLabs TTS audio generation unvailable or key missing.")

    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """
    Transcribe audio file to text using ElevenLabs Scribe STT.
    """
    audio_content = await file.read()
    text = await elevenlabs_service.speech_to_text(audio_content, filename=file.filename or "speech.wav")
    if not text:
        raise HTTPException(status_code=503, detail="ElevenLabs STT transcription unavailable or key missing.")

    return {"transcript": text}


@router.get("/status")
async def voice_status():
    """Check voice pipeline integration status."""
    return {
        "status": "online",
        "stt": "ElevenLabs Scribe STT",
        "tts": "ElevenLabs TTS",
        "elevenlabs_configured": elevenlabs_service.enabled,
        "orchestration": "Vapi AI + LangGraph",
        "llm": "Groq LLama3-70B",
    }












