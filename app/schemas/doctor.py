"""
Pydantic Schemas — Doctor (SQLite-compatible)
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime, time
from typing import Optional, List


class DoctorCreate(BaseModel):
    full_name: str
    specialization: str
    phone_number: str
    email: Optional[EmailStr] = None
    working_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    work_start_time: time = time(9, 0)
    work_end_time: time = time(17, 0)
    slot_duration_minutes: int = 30


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = None
    specialization: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    working_days: Optional[List[str]] = None
    work_start_time: Optional[time] = None
    work_end_time: Optional[time] = None
    slot_duration_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class DoctorResponse(BaseModel):
    id: str
    full_name: str
    specialization: str
    phone_number: str
    email: Optional[str]
    working_days: List[str]
    work_start_time: time
    work_end_time: time
    slot_duration_minutes: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AvailableSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    formatted: str
