"""
Pydantic Schemas — Patient (SQLite + PostgreSQL compatible)
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class PatientCreate(BaseModel):
    full_name: str
    phone_number: str
    email: Optional[EmailStr] = None


class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class PatientResponse(BaseModel):
    id: str
    full_name: str
    phone_number: str
    email: Optional[str] = None
    patient_code: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
