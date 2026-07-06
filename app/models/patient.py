"""
Patient Model — SQLAlchemy ORM (SQLite + PostgreSQL compatible)
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    patient_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    appointments: Mapped[list["Appointment"]] = relationship(  # noqa: F821
        "Appointment", back_populates="patient", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Patient {self.full_name} ({self.phone_number})>"
