"""
API Route — Admin Auth (API Key only, no user login)
Patients are identified by phone number via voice — no login required.
"""
from fastapi import APIRouter, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

router = APIRouter()

# ── Admin API Key Header ───────────────────────────────────
api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def verify_admin_key(api_key: str = Security(api_key_header)):
    """Dependency to protect admin-only endpoints with an API key."""
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin API key. Include 'X-Admin-Key' header.",
        )
    return api_key


@router.get("/ping")
async def ping():
    """Public ping — confirms API is alive (no auth needed)."""
    return {"message": "Voice Appointment Agent API is running 🏥"}
