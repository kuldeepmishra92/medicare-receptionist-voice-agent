"""
Voice Appointment Agent — FastAPI Application Entry Point
"""
import os
import asyncio
import httpx
try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from loguru import logger

from app.config import settings
from app.database import engine, Base
from app.core.logging import setup_logging
from app.api.routes import auth, patients, doctors, appointments, voice

# ── Setup Logging ─────────────────────────────────────────
setup_logging()

# ── Setup Sentry ──────────────────────────────────────────
if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=1.0)


# ── Keep-Alive Task (HF Spaces Anti-Sleep) ────────────────
async def keep_alive_ping():
    """Background task to self-ping /health every 5 mins so Hugging Face Space stays active."""
    await asyncio.sleep(15)  # Wait for server startup
    port = os.getenv("PORT") or os.getenv("APP_PORT") or settings.APP_PORT
    space_host = os.getenv("SPACE_HOST")
    
    if space_host:
        target_url = f"https://{space_host}/health"
    else:
        target_url = f"http://127.0.0.1:{port}/health"

    logger.info(f"🔄 Keep-Alive Ping Service started targeting: {target_url}")
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(target_url)
                logger.info(f"🟢 Keep-Alive Self-Ping: [{resp.status_code}] on {target_url}")
        except Exception as e:
            logger.warning(f"⚠️ Keep-Alive Self-Ping note: {e}")
        await asyncio.sleep(300)  # Ping every 5 minutes


# ── Lifespan ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables (auto-create for dev convenience)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    ping_task = asyncio.create_task(keep_alive_ping())
    yield
    # Shutdown
    ping_task.cancel()
    await engine.dispose()


# ── App Instance ──────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Multi-Doctor Voice Appointment Scheduling Agent API.\n\n"
        "**No login required for patients** — they are identified by phone number via voice.\n\n"
        "Admin Dashboard available at `/dashboard`."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS Middleware ───────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ──────────────────────────────────────
app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["System"])
app.include_router(patients.router,     prefix="/api/v1/patients",     tags=["Patients"])
app.include_router(doctors.router,      prefix="/api/v1/doctors",      tags=["Doctors"])
app.include_router(appointments.router, prefix="/api/v1/appointments", tags=["Appointments"])
app.include_router(voice.router,        prefix="/api/v1/voice",        tags=["Voice Agent"])

# ── Health Check ──────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "dashboard": "/dashboard",
        "auth": "phone-number based (no login)",
    }


# ── Mount Frontend Static Admin Dashboard ─────────────────
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/dashboard", StaticFiles(directory=frontend_dir, html=True), name="frontend_dash")
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend_root")
