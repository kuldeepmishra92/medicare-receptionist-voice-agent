"""
Appointment Service — Business Logic for Appointment Scheduling
Implements full conflict validation rules:
  1. Doctor Conflict Check
  2. Patient Conflict Check
  3. Duplicate Appointment Check
Integrated with Google Calendar Service & Notification Service (SMS, WhatsApp, Email).
"""
import uuid
import random
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services import doctor_service, patient_service
from app.services.calendar_service import calendar_service
from app.services.notification_service import notification_service


def generate_appointment_id() -> str:
    """Generate unique appointment ID like APT-10234."""
    return f"APT-{random.randint(10000, 99999)}"


async def get_appointment_by_id(db: AsyncSession, id_or_apt_id: str) -> Optional[Appointment]:
    """Look up appointment by internal UUID or formatted APT-XXXXX ID."""
    result = await db.execute(
        select(Appointment).where(
            or_(
                Appointment.id == id_or_apt_id,
                Appointment.appointment_id.ilike(id_or_apt_id.strip())
            )
        )
    )
    return result.scalar_one_or_none()


async def check_doctor_conflict(
    db: AsyncSession,
    doctor_id: str,
    start_time: datetime,
    end_time: datetime,
    exclude_appointment_id: Optional[str] = None
) -> bool:
    """Returns True if the doctor is ALREADY booked during [start_time, end_time)."""
    query = select(Appointment).where(
        and_(
            Appointment.doctor_id == str(doctor_id),
            Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING]),
            Appointment.appointment_date < end_time,
            Appointment.appointment_end > start_time,
        )
    )
    if exclude_appointment_id:
        query = query.where(Appointment.id != exclude_appointment_id)

    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def check_patient_conflict(
    db: AsyncSession,
    patient_id: str,
    start_time: datetime,
    end_time: datetime,
    exclude_appointment_id: Optional[str] = None
) -> bool:
    """Returns True if the patient ALREADY has another appointment during [start_time, end_time)."""
    query = select(Appointment).where(
        and_(
            Appointment.patient_id == str(patient_id),
            Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING]),
            Appointment.appointment_date < end_time,
            Appointment.appointment_end > start_time,
        )
    )
    if exclude_appointment_id:
        query = query.where(Appointment.id != exclude_appointment_id)

    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def check_duplicate_appointment(
    db: AsyncSession,
    patient_id: str,
    doctor_id: str,
    start_time: datetime,
    exclude_appointment_id: Optional[str] = None
) -> bool:
    """Returns True if the patient ALREADY has an active appointment with the SAME doctor at that exact time."""
    query = select(Appointment).where(
        and_(
            Appointment.patient_id == str(patient_id),
            Appointment.doctor_id == str(doctor_id),
            Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING]),
            Appointment.appointment_date == start_time,
        )
    )
    if exclude_appointment_id:
        query = query.where(Appointment.id != exclude_appointment_id)

    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def create_appointment(db: AsyncSession, data: AppointmentCreate) -> Appointment:
    """
    Book a new appointment with full conflict validation, Google Calendar sync, and multi-channel notifications:
      - Validates Patient & Doctor existence
      - Validates Doctor working days & working hours
      - Validates Doctor leaves
      - Doctor conflict check
      - Patient conflict check
      - Duplicate appointment check
      - Google Calendar event creation
      - Trigger SMS, WhatsApp, and Email confirmation notifications
    """
    # 1. Verify Patient exists
    patient = await patient_service.get_patient_by_id(db, data.patient_id)
    if not patient or not patient.is_active:
        raise ValueError("Patient not found or inactive.")

    # 2. Verify Doctor exists
    doctor = await doctor_service.get_doctor_by_id(db, data.doctor_id)
    if not doctor or not doctor.is_active:
        raise ValueError("Doctor not found or inactive.")

    start_time = data.appointment_date
    duration = timedelta(minutes=doctor.slot_duration_minutes)
    end_time = start_time + duration

    # 3. Check Doctor Working Day
    day_name = start_time.strftime("%A")
    if day_name not in (doctor.working_days or []):
        raise ValueError(f"{doctor.full_name} does not work on {day_name}s.")

    # 4. Check Doctor Working Hours
    slot_time = start_time.time()
    slot_end_time = end_time.time()
    if slot_time < doctor.work_start_time or slot_end_time > doctor.work_end_time:
        raise ValueError(
            f"Selected time ({start_time.strftime('%I:%M %p')}) is outside {doctor.full_name}'s "
            f"working hours ({doctor.work_start_time.strftime('%I:%M %p')} - {doctor.work_end_time.strftime('%I:%M %p')})."
        )

    # 5. Check Doctor Leave
    target_date = start_time.date()
    leaves = await doctor_service.get_doctor_leaves(db, doctor.id, from_date=target_date)
    for leave in leaves:
        if leave.leave_date.date() == target_date:
            raise ValueError(f"{doctor.full_name} is on leave on {target_date.strftime('%d %B %Y')}.")

    # 6. Conflict Check — Duplicate Booking
    if await check_duplicate_appointment(db, patient.id, doctor.id, start_time):
        raise ValueError(
            f"You already have an appointment with {doctor.full_name} at {start_time.strftime('%I:%M %p on %d %b %Y')}."
        )

    # 7. Conflict Check — Doctor Overlap
    if await check_doctor_conflict(db, doctor.id, start_time, end_time):
        raise ValueError(
            f"{doctor.full_name} is already booked at {start_time.strftime('%I:%M %p')}. Please select another slot."
        )

    # 8. Conflict Check — Patient Overlap
    if await check_patient_conflict(db, patient.id, start_time, end_time):
        raise ValueError(
            f"You already have another appointment scheduled at {start_time.strftime('%I:%M %p')}. Please select a non-overlapping time."
        )

    # Generate unique APT-XXXXX code
    apt_code = generate_appointment_id()
    while await get_appointment_by_id(db, apt_code):
        apt_code = generate_appointment_id()

    # Create Google Calendar Event
    summary = f"Medical Appointment: {patient.full_name} with {doctor.full_name}"
    description = (
        f"Appointment ID: {apt_code}\n"
        f"Patient: {patient.full_name} ({patient.phone_number})\n"
        f"Doctor: {doctor.full_name} ({doctor.specialization})\n"
        f"Notes: {data.notes or 'None'}"
    )
    google_event_id = await calendar_service.create_event(
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        description=description,
        attendee_email=patient.email,
    )

    appointment = Appointment(
        id=str(uuid.uuid4()),
        appointment_id=apt_code,
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=start_time,
        appointment_end=end_time,
        status=AppointmentStatus.CONFIRMED,
        google_event_id=google_event_id,
        notes=data.notes,
    )

    db.add(appointment)
    await db.flush()
    await db.refresh(appointment)

    # Trigger Multi-channel Notifications (SMS, WhatsApp, Email)
    await notification_service.send_appointment_confirmation(
        patient_name=patient.full_name,
        phone=patient.phone_number,
        email=patient.email,
        doctor_name=doctor.full_name,
        specialization=doctor.specialization,
        date_str=start_time.strftime("%d %B %Y"),
        time_str=start_time.strftime("%I:%M %p"),
        appointment_id=apt_code,
    )

    return appointment


async def reschedule_appointment(
    db: AsyncSession,
    appointment_id: str,
    new_date: datetime,
    notes: Optional[str] = None
) -> Appointment:
    """Reschedule an existing appointment with conflict validation, Google Calendar sync, and notifications."""
    appointment = await get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise ValueError(f"Appointment '{appointment_id}' not found.")

    if appointment.status == AppointmentStatus.CANCELLED:
        raise ValueError("Cannot reschedule a cancelled appointment.")

    doctor = await doctor_service.get_doctor_by_id(db, appointment.doctor_id)
    patient = await patient_service.get_patient_by_id(db, appointment.patient_id)
    if not doctor or not patient:
        raise ValueError("Associated doctor or patient not found.")

    duration = timedelta(minutes=doctor.slot_duration_minutes)
    new_end = new_date + duration

    # Conflict Check — Doctor Overlap
    if await check_doctor_conflict(db, doctor.id, new_date, new_end, exclude_appointment_id=appointment.id):
        raise ValueError(f"{doctor.full_name} is not available at {new_date.strftime('%I:%M %p')}.")

    # Conflict Check — Patient Overlap
    if await check_patient_conflict(db, appointment.patient_id, new_date, new_end, exclude_appointment_id=appointment.id):
        raise ValueError(f"Patient has another appointment at {new_date.strftime('%I:%M %p')}.")

    appointment.appointment_date = new_date
    appointment.appointment_end = new_end
    appointment.status = AppointmentStatus.RESCHEDULED
    if notes:
        appointment.notes = notes

    # Sync with Google Calendar
    if appointment.google_event_id:
        await calendar_service.update_event(
            event_id=appointment.google_event_id,
            start_time=new_date,
            end_time=new_end,
        )

    await db.flush()
    await db.refresh(appointment)

    # Trigger Notifications
    await notification_service.send_appointment_reschedule(
        patient_name=patient.full_name,
        phone=patient.phone_number,
        email=patient.email,
        doctor_name=doctor.full_name,
        date_str=new_date.strftime("%d %B %Y"),
        time_str=new_date.strftime("%I:%M %p"),
        appointment_id=appointment.appointment_id,
    )

    return appointment


async def cancel_appointment(
    db: AsyncSession,
    appointment_id: str,
    reason: Optional[str] = None
) -> Appointment:
    """Cancel an appointment, update Google Calendar, and send notifications."""
    appointment = await get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise ValueError(f"Appointment '{appointment_id}' not found.")

    if appointment.status == AppointmentStatus.CANCELLED:
        raise ValueError("Appointment is already cancelled.")

    doctor = await doctor_service.get_doctor_by_id(db, appointment.doctor_id)
    patient = await patient_service.get_patient_by_id(db, appointment.patient_id)

    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancellation_reason = reason or "Cancelled by patient"

    # Delete Google Calendar Event
    if appointment.google_event_id:
        await calendar_service.delete_event(event_id=appointment.google_event_id)

    await db.flush()
    await db.refresh(appointment)

    # Trigger Notifications
    if patient and doctor:
        await notification_service.send_appointment_cancellation(
            patient_name=patient.full_name,
            phone=patient.phone_number,
            email=patient.email,
            doctor_name=doctor.full_name,
            date_str=appointment.appointment_date.strftime("%d %B %Y"),
            time_str=appointment.appointment_date.strftime("%I:%M %p"),
            appointment_id=appointment.appointment_id,
            reason=reason,
        )

    return appointment


async def list_appointments(
    db: AsyncSession,
    patient_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    status_filter: Optional[AppointmentStatus] = None,
    limit: int = 100
) -> list[Appointment]:
    """List appointments with optional filters."""
    query = select(Appointment)
    if patient_id:
        query = query.where(Appointment.patient_id == str(patient_id))
    if doctor_id:
        query = query.where(Appointment.doctor_id == str(doctor_id))
    if status_filter:
        query = query.where(Appointment.status == status_filter)

    query = query.order_by(Appointment.appointment_date.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
