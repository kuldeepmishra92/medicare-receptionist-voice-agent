"""
Core Security — Admin API Key verification
No user login required. Patients are identified by phone number via voice.
"""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def verify_admin_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency to protect admin-only endpoints.
    Add 'X-Admin-Key: <your-key>' header to access protected routes.
    """
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin API key.",
        )
    return api_key
