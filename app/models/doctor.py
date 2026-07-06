"""
Doctor Model — SQLAlchemy ORM (SQLite + PostgreSQL compatible)
"""
import uuid
from datetime import datetime, time
from sqlalchemy import String, DateTime, Boolean, JSON, Time, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    specialization: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    # Schedule
    working_days: Mapped[list] = mapped_column(
        JSON, nullable=False,
        default=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    )
    work_start_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(9, 0))
    work_end_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(17, 0))
    slot_duration_minutes: Mapped[int] = mapped_column(default=30)

    # Google Calendar
    google_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    appointments: Mapped[list["Appointment"]] = relationship(  # noqa: F821
        "Appointment", back_populates="doctor", cascade="all, delete-orphan"
    )
    leaves: Mapped[list["DoctorLeave"]] = relationship(
        "DoctorLeave", back_populates="doctor",
        foreign_keys="DoctorLeave.doctor_id",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Doctor {self.full_name} — {self.specialization}>"


class DoctorLeave(Base):
    __tablename__ = "doctor_leaves"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    doctor: Mapped["Doctor"] = relationship(
        "Doctor", back_populates="leaves", foreign_keys=[doctor_id]
    )
