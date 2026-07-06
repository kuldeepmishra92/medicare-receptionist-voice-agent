"""
Pydantic Schemas — Appointment (SQLite + PostgreSQL compatible)
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_date: datetime
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: str
    appointment_id: str
    patient_id: str
    doctor_id: str
    appointment_date: datetime
    appointment_end: datetime
    status: AppointmentStatus
    google_event_id: Optional[str] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AppointmentConfirmation(BaseModel):
    appointment_id: str
    patient_name: str
    doctor_name: str
    specialization: str
    date: str
    time: str
    status: str
