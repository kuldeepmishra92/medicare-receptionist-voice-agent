"""
API Route — Patients
Full CRUD + phone & code lookup for voice agent
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.services import patient_service

router = APIRouter()


# ── Create Patient ─────────────────────────────────────────
@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(data: PatientCreate, db: AsyncSession = Depends(get_db)):
    """Register a new patient record. Auto-generates patient code."""
    try:
        patient = await patient_service.create_patient(db, data)
        return patient
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# ── List Patients ──────────────────────────────────────────
@router.get("/", response_model=list[PatientResponse])
async def list_patients(
    active_only: bool = Query(True, description="Only return active patients"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List all registered patients."""
    return await patient_service.list_patients(db, limit=limit, active_only=active_only)


# ── Lookup by Phone Number ────────────────────────────────
@router.get("/phone/{phone_number}", response_model=PatientResponse)
async def get_patient_by_phone(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Look up a patient by phone number (used by Voice Agent)."""
    patient = await patient_service.get_patient_by_phone(db, phone_number)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No patient profile found for phone number '{phone_number}'",
        )
    return patient


# ── Lookup by Patient Code ────────────────────────────────
@router.get("/code/{patient_code}", response_model=PatientResponse)
async def get_patient_by_code(patient_code: str, db: AsyncSession = Depends(get_db)):
    """Look up a patient by unique patient code (e.g. PAT-10234)."""
    patient = await patient_service.get_patient_by_code(db, patient_code)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient code '{patient_code}' not found",
        )
    return patient


# ── Get Patient by ID ─────────────────────────────────────
@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Get patient by primary key ID."""
    patient = await patient_service.get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


# ── Update Patient ────────────────────────────────────────
@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: str, data: PatientUpdate, db: AsyncSession = Depends(get_db)):
    """Update patient profile details."""
    patient = await patient_service.update_patient(db, patient_id, data)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient
