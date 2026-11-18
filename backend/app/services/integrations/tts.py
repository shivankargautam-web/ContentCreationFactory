"""Text-to-speech abstraction with ElevenLabs implementation."""

from typing import Protocol

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.core.telemetry import get_tracer

tracer = get_tracer(__name__)


class TextToSpeech(Protocol):
    async def synthesize(self, text: str) -> bytes | None: ...


class NullTextToSpeech:
    """Used when no TTS provider is configured: the renderer produces a silent track."""

    async def synthesize(self, text: str) -> bytes | None:
        return None


class ElevenLabsTextToSpeech:
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        if settings.elevenlabs_api_key is None:
            raise ValueError("ELEVENLABS_API_KEY is required")
        self._api_key = settings.elevenlabs_api_key.get_secret_value()
        self._voice_id = settings.elevenlabs_voice_id
        self._model_id = settings.elevenlabs_model_id
        self._http = http or httpx.AsyncClient(timeout=120)

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        wait=wait_exponential(min=1, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _post(self, text: str) -> bytes:
        response = await self._http.post(
            f"{self.BASE_URL}/text-to-speech/{self._voice_id}",
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": self._api_key, "accept": "audio/mpeg"},
            json={
                "text": text,
                "model_id": self._model_id,
                "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3},
            },
        )
        if response.status_code == 429 or response.status_code >= 500:
            response.raise_for_status()
        if response.status_code >= 400:
            raise ExternalServiceError(f"ElevenLabs error {response.status_code}: {response.text[:200]}")
        return response.content

    async def synthesize(self, text: str) -> bytes | None:
        with tracer.start_as_current_span("tts.elevenlabs.synthesize") as span:
            span.set_attribute("tts.chars", len(text))
            return await self._post(text)
