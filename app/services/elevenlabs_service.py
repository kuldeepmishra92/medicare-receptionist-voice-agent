"""
ElevenLabs Service — Handles both Text-to-Speech (TTS) and Speech-to-Text (STT)
"""
import httpx
from typing import Optional
from loguru import logger

from app.config import settings


class ElevenLabsService:
    """ElevenLabs Service for STT (Speech-to-Text) & TTS (Text-to-Speech)."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.default_voice_id = settings.ELEVENLABS_VOICE_ID or "EXAVITQu4vr4xnSDxMaL"  # Default Sarah (works for Free & Paid plans)
        self.enabled = bool(self.api_key)

        if self.enabled:
            logger.info("🎙️ ElevenLabs Service initialized with API Key for STT & TTS.")
        else:
            logger.info("ℹ️ ElevenLabs API Key not set in .env — using smart fallback mode.")

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_format: str = "mp3_44100_128",
    ) -> Optional[bytes]:
        """
        Convert text to audio speech bytes using ElevenLabs TTS.
        """
        if not text:
            return None

        target_voice = voice_id or self.default_voice_id

        if self.enabled:
            try:
                url = f"{self.BASE_URL}/text-to-speech/{target_voice}"
                headers = {
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                }
                payload = {
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    if response.status_code == 200:
                        logger.info(f"🔊 ElevenLabs TTS Generated Audio for: '{text[:40]}...' ({len(response.content)} bytes)")
                        return response.content
                    else:
                        logger.error(f"❌ ElevenLabs TTS API Error {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"❌ ElevenLabs TTS Exception: {e}")

        logger.info(f"🔊 [MOCK TTS] Synthesized text: '{text[:40]}...'")
        return None

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
    ) -> Optional[str]:
        """
        Transcribe audio speech bytes to text using ElevenLabs Scribe / Speech-to-Text API.
        """
        if not audio_bytes:
            return None

        if self.enabled:
            try:
                url = f"{self.BASE_URL}/speech-to-text"
                headers = {
                    "xi-api-key": self.api_key,
                }
                files = {
                    "file": (filename, audio_bytes, "audio/wav"),
                }
                data = {
                    "model_id": "scribe_v1",
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, data=data, files=files, headers=headers)
                    if response.status_code == 200:
                        res_json = response.json()
                        text = res_json.get("text", "")
                        logger.info(f"🎙️ ElevenLabs STT Transcribed Text: '{text}'")
                        return text
                    else:
                        logger.error(f"❌ ElevenLabs STT API Error {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"❌ ElevenLabs STT Exception: {e}")

        return None


# Global singleton instance
elevenlabs_service = ElevenLabsService()
