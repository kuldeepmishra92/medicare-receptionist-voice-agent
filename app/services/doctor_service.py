"""
Doctor Service — Business Logic for Doctor Management
"""
import uuid
from datetime import datetime, date, time, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError

from app.models.doctor import Doctor, DoctorLeave
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.doctor import DoctorCreate, DoctorUpdate, AvailableSlot


# ── Create Doctor ─────────────────────────────────────────
async def create_doctor(db: AsyncSession, data: DoctorCreate) -> Doctor:
    doctor = Doctor(
        id=str(uuid.uuid4()),
        full_name=data.full_name,
        specialization=data.specialization,
        phone_number=data.phone_number,
        email=data.email,
        working_days=data.working_days,
        work_start_time=data.work_start_time,
        work_end_time=data.work_end_time,
        slot_duration_minutes=data.slot_duration_minutes,
    )
    db.add(doctor)
    try:
        await db.flush()
        await db.refresh(doctor)
    except IntegrityError:
        await db.rollback()
        raise ValueError(f"Doctor with phone {data.phone_number} or email already exists.")
    return doctor


# ── Get Doctor by ID ──────────────────────────────────────
async def get_doctor_by_id(db: AsyncSession, doctor_id: str) -> Optional[Doctor]:
    result = await db.execute(
        select(Doctor).where(Doctor.id == str(doctor_id))
    )
    return result.scalar_one_or_none()


# ── Get Doctor by Name ────────────────────────────────────
async def get_doctor_by_name(db: AsyncSession, name: str) -> Optional[Doctor]:
    result = await db.execute(
        select(Doctor).where(
            Doctor.full_name.ilike(f"%{name}%"),
            Doctor.is_active == True  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


# ── List Doctors ──────────────────────────────────────────
async def list_doctors(
    db: AsyncSession,
    specialization: Optional[str] = None,
    active_only: bool = True,
) -> list[Doctor]:
    query = select(Doctor)
    if active_only:
        query = query.where(Doctor.is_active == True)  # noqa: E712
    if specialization:
        query = query.where(Doctor.specialization.ilike(f"%{specialization}%"))
    query = query.order_by(Doctor.full_name)
    result = await db.execute(query)
    return list(result.scalars().all())


# ── Update Doctor ─────────────────────────────────────────
async def update_doctor(
    db: AsyncSession,
    doctor_id: str,
    data: DoctorUpdate,
) -> Optional[Doctor]:
    doctor = await get_doctor_by_id(db, doctor_id)
    if not doctor:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(doctor, field, value)
    await db.flush()
    await db.refresh(doctor)
    return doctor


# ── Add Doctor Leave ──────────────────────────────────────
async def add_doctor_leave(
    db: AsyncSession,
    doctor_id: str,
    leave_date: date,
    reason: Optional[str] = None,
) -> DoctorLeave:
    leave = DoctorLeave(
        id=str(uuid.uuid4()),
        doctor_id=str(doctor_id),
        leave_date=datetime.combine(leave_date, time(0, 0)),
        reason=reason,
    )
    db.add(leave)
    await db.flush()
    return leave


# ── Get Doctor Leaves ─────────────────────────────────────
async def get_doctor_leaves(
    db: AsyncSession,
    doctor_id: str,
    from_date: Optional[date] = None,
) -> list[DoctorLeave]:
    query = select(DoctorLeave).where(DoctorLeave.doctor_id == str(doctor_id))
    if from_date:
        query = query.where(DoctorLeave.leave_date >= datetime.combine(from_date, time(0, 0)))
    result = await db.execute(query)
    return list(result.scalars().all())


# ── Generate Available Slots ──────────────────────────────
async def get_available_slots(
    db: AsyncSession,
    doctor_id: str,
    target_date: date,
) -> list[AvailableSlot]:
    """
    Generate available appointment slots for a doctor on a given date.
    Accounts for: working days, leaves, and existing appointments.
    """
    doctor = await get_doctor_by_id(db, doctor_id)
    if not doctor or not doctor.is_active:
        return []

    # ── Check working day ─────────────────────────────────
    day_name = target_date.strftime("%A")
    if day_name not in (doctor.working_days or []):
        return []

    # ── Check doctor leave ────────────────────────────────
    start_of_day = datetime.combine(target_date, time(0, 0))
    end_of_day = datetime.combine(target_date, time(23, 59))
    leaves = await db.execute(
        select(DoctorLeave).where(
            and_(
                DoctorLeave.doctor_id == str(doctor_id),
                DoctorLeave.leave_date >= start_of_day,
                DoctorLeave.leave_date <= end_of_day,
            )
        )
    )
    if leaves.scalar_one_or_none():
        return []

    # ── Get existing bookings ─────────────────────────────
    booked = await db.execute(
        select(Appointment.appointment_date, Appointment.appointment_end).where(
            and_(
                Appointment.doctor_id == str(doctor_id),
                Appointment.appointment_date >= start_of_day,
                Appointment.appointment_date <= end_of_day,
                Appointment.status.in_([
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.PENDING,
                ]),
            )
        )
    )
    booked_slots = [(r[0], r[1]) for r in booked.fetchall()]

    # ── Generate all possible slots ───────────────────────
    duration = timedelta(minutes=doctor.slot_duration_minutes)
    work_start = datetime.combine(target_date, doctor.work_start_time)
    work_end = datetime.combine(target_date, doctor.work_end_time)

    available = []
    current = work_start
    now = datetime.now()

    while current + duration <= work_end:
        slot_end = current + duration

        # Skip past slots
        if current <= now:
            current = slot_end
            continue

        # Check overlap with booked slots
        is_free = all(
            slot_end <= booked_start or current >= booked_end
            for booked_start, booked_end in booked_slots
        )

        if is_free:
            available.append(
                AvailableSlot(
                    start_time=current,
                    end_time=slot_end,
                    formatted=current.strftime("%I:%M %p"),
                )
            )
        current = slot_end

    return available
