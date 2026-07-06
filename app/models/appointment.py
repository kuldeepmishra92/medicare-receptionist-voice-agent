"""
Appointment Model — SQLAlchemy ORM (SQLite + PostgreSQL compatible)
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AppointmentStatus(str, PyEnum):
    PENDING     = "pending"
    CONFIRMED   = "confirmed"
    CANCELLED   = "cancelled"
    COMPLETED   = "completed"
    RESCHEDULED = "rescheduled"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Foreign Keys
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    doctor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False
    )

    # Schedule
    appointment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    appointment_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Status
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, native_enum=False),
        default=AppointmentStatus.CONFIRMED,
        index=True,
    )

    # Google Calendar
    google_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    patient: Mapped["Patient"] = relationship(  # noqa: F821
        "Patient", back_populates="appointments", foreign_keys=[patient_id]
    )
    doctor: Mapped["Doctor"] = relationship(  # noqa: F821
        "Doctor", back_populates="appointments", foreign_keys=[doctor_id]
    )

    def __repr__(self) -> str:
        return f"<Appointment {self.appointment_id} — {self.status}>"
