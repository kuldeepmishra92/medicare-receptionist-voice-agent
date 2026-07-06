"""
Application Configuration — Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────
    APP_NAME: str = "Voice Appointment Agent"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-secret-key"

    # ── Database ──────────────────────────────────────────
    # SQLite (default for development — change to PostgreSQL for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./voice_agent.db"
    # DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/voice_agent_db"
    DATABASE_ECHO: bool = False

    # ── Admin API Key (for dashboard only) ──────────────────
    ADMIN_API_KEY: str = "change-this-admin-key"

    # ── Groq LLM ─────────────────────────────────────────
    GROQ_API_KEY: str = ""

    # ── OpenAI (Whisper) ──────────────────────────────────
    OPENAI_API_KEY: str = ""

    # ── ElevenLabs ───────────────────────────────────────
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = ""

    # ── Vapi AI ───────────────────────────────────────────
    VAPI_API_KEY: str = ""
    VAPI_PHONE_NUMBER_ID: str = ""

    # ── Google Calendar ───────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    GOOGLE_CALENDAR_ID: str = "primary"

    # ── Twilio ────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""

    # ── Resend ────────────────────────────────────────────
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = ""

    # ── SMTP ──────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # ── Sentry ───────────────────────────────────────────
    SENTRY_DSN: str = ""

    # ── CORS ─────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
