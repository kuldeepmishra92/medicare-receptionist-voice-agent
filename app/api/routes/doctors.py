"""
API Route — Doctors
Full CRUD + availability slots + leave management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.database import get_db
from app.schemas.doctor import DoctorCreate, DoctorResponse, DoctorUpdate, AvailableSlot
from app.services import doctor_service

router = APIRouter()


# ── Create Doctor ─────────────────────────────────────────
@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(data: DoctorCreate, db: AsyncSession = Depends(get_db)):
    """Register a new doctor with schedule details."""
    try:
        doctor = await doctor_service.create_doctor(db, data)
        return doctor
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# ── List Doctors ──────────────────────────────────────────
@router.get("/", response_model=list[DoctorResponse])
async def list_doctors(
    specialization: str | None = Query(None, description="Filter by specialization (partial match)"),
    active_only: bool = Query(True, description="Only return active doctors"),
    db: AsyncSession = Depends(get_db),
):
    """List all doctors. Filter by specialization (e.g. Cardiologist, Dermatologist)."""
    return await doctor_service.list_doctors(db, specialization=specialization, active_only=active_only)


# ── Get Doctor by ID ──────────────────────────────────────
@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(doctor_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single doctor's full profile."""
    doctor = await doctor_service.get_doctor_by_id(db, doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor


# ── Update Doctor ─────────────────────────────────────────
@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(doctor_id: str, data: DoctorUpdate, db: AsyncSession = Depends(get_db)):
    """Update doctor details (partial update supported)."""
    doctor = await doctor_service.update_doctor(db, doctor_id, data)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor


# ── Deactivate Doctor ─────────────────────────────────────
@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_doctor(doctor_id: str, db: AsyncSession = Depends(get_db)):
    """Deactivate a doctor (soft delete — does not remove from DB)."""
    from app.schemas.doctor import DoctorUpdate
    doctor = await doctor_service.update_doctor(db, doctor_id, DoctorUpdate(is_active=False))
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")


# ── Get Available Slots ───────────────────────────────────
@router.get("/{doctor_id}/slots", response_model=list[AvailableSlot])
async def get_available_slots(
    doctor_id: str,
    date: date = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get available appointment slots for a doctor on a specific date.
    Returns only future slots that are not already booked.
    """
    slots = await doctor_service.get_available_slots(db, doctor_id, date)
    return slots


# ── Add Doctor Leave ──────────────────────────────────────
@router.post("/{doctor_id}/leave", status_code=status.HTTP_201_CREATED)
async def add_leave(
    doctor_id: str,
    leave_date: date = Query(..., description="Leave date in YYYY-MM-DD"),
    reason: str | None = Query(None, description="Optional reason for leave"),
    db: AsyncSession = Depends(get_db),
):
    """Mark a doctor as on leave for a specific date."""
    doctor = await doctor_service.get_doctor_by_id(db, doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    leave = await doctor_service.add_doctor_leave(db, doctor_id, leave_date, reason)
    return {
        "message": f"{doctor.full_name} marked on leave for {leave_date}",
        "leave_date": str(leave_date),
        "reason": reason,
    }


# ── Get Doctor Leaves ─────────────────────────────────────
@router.get("/{doctor_id}/leave", response_model=list[dict])
async def get_leaves(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all leave dates for a doctor."""
    doctor = await doctor_service.get_doctor_by_id(db, doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    leaves = await doctor_service.get_doctor_leaves(db, doctor_id)
    return [
        {"leave_date": str(l.leave_date.date()), "reason": l.reason}
        for l in leaves
    ]
