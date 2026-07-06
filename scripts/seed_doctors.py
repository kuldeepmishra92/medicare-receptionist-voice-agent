"""
Seed Script — Add sample doctors to the database
Run: python scripts/seed_doctors.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal, engine, Base
from app.services.doctor_service import create_doctor
from app.schemas.doctor import DoctorCreate
from datetime import time


SAMPLE_DOCTORS = [
    DoctorCreate(
        full_name="Dr. Rajesh Sharma",
        specialization="Cardiologist",
        phone_number="+91-9001000001",
        email="rajesh.sharma@hospital.com",
        working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        work_start_time=time(9, 0),
        work_end_time=time(17, 0),
        slot_duration_minutes=30,
    ),
    DoctorCreate(
        full_name="Dr. Priya Mehta",
        specialization="Dermatologist",
        phone_number="+91-9001000002",
        email="priya.mehta@hospital.com",
        working_days=["Monday", "Wednesday", "Friday"],
        work_start_time=time(10, 0),
        work_end_time=time(16, 0),
        slot_duration_minutes=20,
    ),
    DoctorCreate(
        full_name="Dr. Anand Verma",
        specialization="Ophthalmologist",
        phone_number="+91-9001000003",
        email="anand.verma@hospital.com",
        working_days=["Tuesday", "Thursday", "Saturday"],
        work_start_time=time(9, 0),
        work_end_time=time(13, 0),
        slot_duration_minutes=15,
    ),
    DoctorCreate(
        full_name="Dr. Sunita Rao",
        specialization="ENT Specialist",
        phone_number="+91-9001000004",
        email="sunita.rao@hospital.com",
        working_days=["Monday", "Tuesday", "Thursday", "Friday"],
        work_start_time=time(11, 0),
        work_end_time=time(18, 0),
        slot_duration_minutes=30,
    ),
    DoctorCreate(
        full_name="Dr. Vikram Singh",
        specialization="General Physician",
        phone_number="+91-9001000005",
        email="vikram.singh@hospital.com",
        working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        work_start_time=time(8, 0),
        work_end_time=time(20, 0),
        slot_duration_minutes=15,
    ),
    DoctorCreate(
        full_name="Dr. Neha Gupta",
        specialization="Pediatrician",
        phone_number="+91-9001000006",
        email="neha.gupta@hospital.com",
        working_days=["Monday", "Wednesday", "Friday", "Saturday"],
        work_start_time=time(9, 0),
        work_end_time=time(15, 0),
        slot_duration_minutes=20,
    ),
    DoctorCreate(
        full_name="Dr. Arjun Patel",
        specialization="Orthopedist",
        phone_number="+91-9001000007",
        email="arjun.patel@hospital.com",
        working_days=["Tuesday", "Thursday", "Saturday"],
        work_start_time=time(10, 0),
        work_end_time=time(17, 0),
        slot_duration_minutes=30,
    ),
    DoctorCreate(
        full_name="Dr. Kavita Desai",
        specialization="Psychiatrist",
        phone_number="+91-9001000008",
        email="kavita.desai@hospital.com",
        working_days=["Monday", "Wednesday", "Friday"],
        work_start_time=time(9, 0),
        work_end_time=time(16, 0),
        slot_duration_minutes=45,
    ),
]


async def seed():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        print("🌱 Seeding doctors...\n")
        seeded = 0
        skipped = 0
        for doc_data in SAMPLE_DOCTORS:
            try:
                doctor = await create_doctor(db, doc_data)
                await db.commit()
                print(f"  ✅ {doctor.full_name:<30} — {doctor.specialization}")
                seeded += 1
            except ValueError as e:
                print(f"  ⚠️  Skipped (already exists): {doc_data.full_name}")
                skipped += 1
            except Exception as e:
                print(f"  ❌ Error for {doc_data.full_name}: {e}")
                await db.rollback()

        print(f"\n🎉 Done! {seeded} doctors seeded, {skipped} skipped.")


if __name__ == "__main__":
    asyncio.run(seed())
