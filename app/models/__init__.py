# app/models/__init__.py
from app.models.patient import Patient
from app.models.doctor import Doctor, DoctorLeave
from app.models.appointment import Appointment, AppointmentStatus

__all__ = ["Patient", "Doctor", "DoctorLeave", "Appointment", "AppointmentStatus"]
