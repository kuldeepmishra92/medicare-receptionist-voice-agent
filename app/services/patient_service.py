"""
Patient Service — Business Logic for Patient Management
"""
import uuid
import random
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


def generate_patient_code() -> str:
    """Generate a unique patient code, e.g., PAT-84920."""
    return f"PAT-{random.randint(10000, 99999)}"


def normalize_phone(phone: str) -> str:
    """Normalize phone number by removing spaces, dashes, parentheses."""
    if not phone:
        return ""
    # Retain digits and leading '+'
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    return cleaned


async def create_patient(db: AsyncSession, data: PatientCreate) -> Patient:
    """Create a new patient record with an auto-generated patient code."""
    # Check if patient with phone already exists
    phone_clean = normalize_phone(data.phone_number)
    existing = await get_patient_by_phone(db, phone_clean)
    if existing:
        raise ValueError(f"Patient with phone number '{data.phone_number}' already exists.")

    patient_code = generate_patient_code()
    # Ensure code uniqueness
    while await get_patient_by_code(db, patient_code):
        patient_code = generate_patient_code()

    patient = Patient(
        id=str(uuid.uuid4()),
        full_name=data.full_name,
        phone_number=phone_clean,
        email=data.email,
        patient_code=patient_code,
        is_active=True,
    )
    db.add(patient)
    try:
        await db.flush()
        await db.refresh(patient)
    except IntegrityError as e:
        await db.rollback()
        raise ValueError(f"Failed to create patient: Phone or email already registered.") from e

    return patient


async def get_patient_by_id(db: AsyncSession, patient_id: str) -> Optional[Patient]:
    """Look up patient by primary key ID."""
    result = await db.execute(
        select(Patient).where(Patient.id == str(patient_id))
    )
    return result.scalar_one_or_none()


async def get_patient_by_phone(db: AsyncSession, phone_number: str) -> Optional[Patient]:
    """Look up patient by phone number."""
    phone_clean = normalize_phone(phone_number)
    if not phone_clean:
        return None

    # Check exact clean match or ends-with match (last 10 digits)
    query = select(Patient).where(
        or_(
            Patient.phone_number == phone_clean,
            Patient.phone_number.like(f"%{phone_clean[-10:]}") if len(phone_clean) >= 10 else Patient.phone_number == phone_clean
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_patient_by_code(db: AsyncSession, patient_code: str) -> Optional[Patient]:
    """Look up patient by unique PAT-XXXXX code."""
    result = await db.execute(
        select(Patient).where(Patient.patient_code.ilike(patient_code.strip()))
    )
    return result.scalar_one_or_none()


async def list_patients(db: AsyncSession, limit: int = 100, active_only: bool = True) -> list[Patient]:
    """List all patients."""
    query = select(Patient)
    if active_only:
        query = query.where(Patient.is_active == True)  # noqa: E712
    query = query.order_by(Patient.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_patient(db: AsyncSession, patient_id: str, data: PatientUpdate) -> Optional[Patient]:
    """Update patient information."""
    patient = await get_patient_by_id(db, patient_id)
    if not patient:
        return None

    update_dict = data.model_dump(exclude_unset=True)
    if "phone_number" in update_dict and update_dict["phone_number"]:
        update_dict["phone_number"] = normalize_phone(update_dict["phone_number"])

    for field, value in update_dict.items():
        setattr(patient, field, value)

    await db.flush()
    await db.refresh(patient)
    return patient
