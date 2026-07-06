"""
API Route — Appointments
Full appointment booking, conflict validation, rescheduling, and cancellation
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.models.appointment import AppointmentStatus
from app.services import appointment_service

router = APIRouter()


# ── Book Appointment ───────────────────────────────────────
@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(data: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    """
    Book a new appointment.
    Validates: doctor availability, doctor conflict, patient conflict, and duplicate bookings.
    """
    try:
        appointment = await appointment_service.create_appointment(db, data)
        return appointment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# ── List Appointments ──────────────────────────────────────
@router.get("/", response_model=list[AppointmentResponse])
async def list_appointments(
    patient_id: Optional[str] = Query(None, description="Filter by Patient ID"),
    doctor_id: Optional[str] = Query(None, description="Filter by Doctor ID"),
    status_filter: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List all appointments with optional filters."""
    return await appointment_service.list_appointments(
        db, patient_id=patient_id, doctor_id=doctor_id, status_filter=status_filter, limit=limit
    )


# ── Get Patient Appointments ──────────────────────────────
@router.get("/patient/{patient_id}", response_model=list[AppointmentResponse])
async def get_patient_appointments(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Get all appointments for a specific patient."""
    return await appointment_service.list_appointments(db, patient_id=patient_id)


# ── Get Appointment Details ───────────────────────────────
@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """Get appointment details by internal ID or appointment code (e.g., APT-10234)."""
    appointment = await appointment_service.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


# ── Update / Reschedule Appointment ───────────────────────
@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str,
    data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Reschedule or update appointment notes/status."""
    try:
        if data.status == AppointmentStatus.CANCELLED:
            return await appointment_service.cancel_appointment(
                db, appointment_id, reason=data.cancellation_reason
            )
        elif data.appointment_date:
            return await appointment_service.reschedule_appointment(
                db, appointment_id, new_date=data.appointment_date, notes=data.notes
            )
        else:
            appointment = await appointment_service.get_appointment_by_id(db, appointment_id)
            if not appointment:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
            if data.notes:
                appointment.notes = data.notes
            await db.flush()
            await db.refresh(appointment)
            return appointment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# ── Cancel Appointment ────────────────────────────────────
@router.delete("/{appointment_id}", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: str,
    reason: Optional[str] = Query(None, description="Reason for cancellation"),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an appointment."""
    try:
        appointment = await appointment_service.cancel_appointment(db, appointment_id, reason=reason)
        return appointment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
