# app/schemas/__init__.py
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorResponse, AvailableSlot
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentResponse, AppointmentConfirmation

__all__ = [
    "PatientCreate", "PatientUpdate", "PatientResponse",
    "DoctorCreate", "DoctorUpdate", "DoctorResponse", "AvailableSlot",
    "AppointmentCreate", "AppointmentUpdate", "AppointmentResponse", "AppointmentConfirmation",
]
