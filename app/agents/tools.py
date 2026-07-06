"""
LangChain Tools — Real Database Connected Agent Tool Definitions (Async Native)
"""
from typing import Optional
from datetime import datetime, date
from langchain_core.tools import tool

from app.database import AsyncSessionLocal
from app.services import patient_service, doctor_service, appointment_service
from app.schemas.patient import PatientCreate
from app.schemas.appointment import AppointmentCreate


@tool
async def get_patient_by_phone_tool(phone_number: str) -> dict:
    """Look up a patient record by phone number."""
    async with AsyncSessionLocal() as db:
        p = await patient_service.get_patient_by_phone(db, phone_number)
        if p:
            return {
                "found": True,
                "patient_id": p.id,
                "full_name": p.full_name,
                "phone_number": p.phone_number,
                "patient_code": p.patient_code,
                "email": p.email,
            }
        return {"found": False, "message": f"No profile found for phone {phone_number}."}


@tool
async def create_patient_tool(full_name: str, phone_number: str, email: Optional[str] = None) -> dict:
    """Create a new patient record in the database."""
    async with AsyncSessionLocal() as db:
        try:
            p = await patient_service.create_patient(db, PatientCreate(
                full_name=full_name, phone_number=phone_number, email=email
            ))
            await db.commit()
            return {
                "success": True,
                "patient_id": p.id,
                "full_name": p.full_name,
                "patient_code": p.patient_code,
                "message": f"Registered new patient profile for {full_name}.",
            }
        except ValueError as e:
            return {"success": False, "message": str(e)}


@tool
def map_symptom_to_specialization_tool(symptom: str) -> dict:
    """
    Map patient symptoms to the appropriate medical specialization.
    Chest pain -> Cardiologist
    Skin rash/allergy -> Dermatologist
    Eye problem/irritation -> Ophthalmologist
    Ear pain/hearing -> ENT Specialist
    """
    symptom_map = {
        "chest pain": "Cardiologist",
        "heart": "Cardiologist",
        "skin": "Dermatologist",
        "rash": "Dermatologist",
        "allergy": "Dermatologist",
        "eye": "Ophthalmologist",
        "vision": "Ophthalmologist",
        "ear": "ENT Specialist",
        "hearing": "ENT Specialist",
        "bone": "Orthopedist",
        "joint": "Orthopedist",
        "stomach": "Gastroenterologist",
        "digestive": "Gastroenterologist",
        "mental": "Psychiatrist",
        "anxiety": "Psychiatrist",
        "child": "Pediatrician",
        "kid": "Pediatrician",
        "fever": "General Physician",
        "cold": "General Physician",
    }
    s_lower = symptom.lower()
    spec = "General Physician"
    for key, mapped_spec in symptom_map.items():
        if key in s_lower:
            spec = mapped_spec
            break
    return {"symptom": symptom, "specialization": spec}


@tool
async def get_doctors_by_specialization_tool(specialization: str) -> dict:
    """Get all available doctors matching a specialization."""
    async with AsyncSessionLocal() as db:
        doctors = await doctor_service.list_doctors(db, specialization=specialization)
        if not doctors:
            return {"found": False, "message": f"No doctors found for specialization '{specialization}'."}
        return {
            "found": True,
            "specialization": specialization,
            "doctors": [
                {
                    "doctor_id": d.id,
                    "full_name": d.full_name,
                    "specialization": d.specialization,
                    "working_days": d.working_days,
                }
                for d in doctors
            ]
        }


@tool
async def get_doctor_by_name_tool(doctor_name: str) -> dict:
    """Get doctor profile details by doctor's full or partial name."""
    async with AsyncSessionLocal() as db:
        d = await doctor_service.get_doctor_by_name(db, doctor_name)
        if d:
            return {
                "found": True,
                "doctor_id": d.id,
                "full_name": d.full_name,
                "specialization": d.specialization,
                "working_days": d.working_days,
            }
        return {"found": False, "message": f"No doctor found with name '{doctor_name}'."}


@tool
async def get_available_slots_tool(doctor_id: str, date_str: str) -> dict:
    """
    Get available appointment slots for a doctor on a specific date (YYYY-MM-DD).
    Returns up to 3 available slots as required by prompt rules.
    """
    async with AsyncSessionLocal() as db:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()

        slots = await doctor_service.get_available_slots(db, doctor_id, target_date)
        formatted_slots = [s.formatted for s in slots[:3]]
        return {
            "doctor_id": doctor_id,
            "date": str(target_date),
            "total_available": len(slots),
            "suggested_slots": formatted_slots,  # up to 3 slots
        }


@tool
async def book_appointment_tool(patient_id: str, doctor_id: str, appointment_datetime_str: str, notes: Optional[str] = None) -> dict:
    """
    Book an appointment after validating all conflicts.
    appointment_datetime_str format: 'YYYY-MM-DD HH:MM' (e.g., '2026-07-10 11:00').
    """
    async with AsyncSessionLocal() as db:
        try:
            dt = datetime.strptime(appointment_datetime_str, "%Y-%m-%d %H:%M")
            apt = await appointment_service.create_appointment(db, AppointmentCreate(
                patient_id=patient_id,
                doctor_id=doctor_id,
                appointment_date=dt,
                notes=notes
            ))
            await db.commit()
            doc = await doctor_service.get_doctor_by_id(db, doctor_id)
            pat = await patient_service.get_patient_by_id(db, patient_id)
            return {
                "success": True,
                "appointment_id": apt.appointment_id,
                "patient_name": pat.full_name if pat else "",
                "doctor_name": doc.full_name if doc else "",
                "specialization": doc.specialization if doc else "",
                "date": dt.strftime("%d %B %Y"),
                "time": dt.strftime("%I:%M %p"),
                "message": f"Appointment successfully booked! Appointment ID: {apt.appointment_id}",
            }
        except ValueError as e:
            return {"success": False, "conflict": True, "message": str(e)}


@tool
async def cancel_appointment_tool(appointment_id: str, reason: Optional[str] = None) -> dict:
    """Cancel an appointment by appointment ID (e.g. APT-10234)."""
    async with AsyncSessionLocal() as db:
        try:
            apt = await appointment_service.cancel_appointment(db, appointment_id, reason=reason)
            await db.commit()
            return {"success": True, "appointment_id": apt.appointment_id, "message": f"Appointment {apt.appointment_id} has been cancelled."}
        except ValueError as e:
            return {"success": False, "message": str(e)}


@tool
async def reschedule_appointment_tool(appointment_id: str, new_datetime_str: str) -> dict:
    """Reschedule an existing appointment to a new date and time ('YYYY-MM-DD HH:MM')."""
    async with AsyncSessionLocal() as db:
        try:
            dt = datetime.strptime(new_datetime_str, "%Y-%m-%d %H:%M")
            apt = await appointment_service.reschedule_appointment(db, appointment_id, new_date=dt)
            await db.commit()
            return {
                "success": True,
                "appointment_id": apt.appointment_id,
                "new_date": dt.strftime("%d %B %Y"),
                "new_time": dt.strftime("%I:%M %p"),
                "message": f"Appointment {apt.appointment_id} successfully rescheduled to {dt.strftime('%I:%M %p on %d %b %Y')}.",
            }
        except ValueError as e:
            return {"success": False, "message": str(e)}


# ── Registered Tools ──────────────────────────────────────
ALL_TOOLS = [
    get_patient_by_phone_tool,
    create_patient_tool,
    map_symptom_to_specialization_tool,
    get_doctors_by_specialization_tool,
    get_doctor_by_name_tool,
    get_available_slots_tool,
    book_appointment_tool,
    cancel_appointment_tool,
    reschedule_appointment_tool,
]
