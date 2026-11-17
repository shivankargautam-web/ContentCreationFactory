"""LLM abstraction (dependency inversion) and the OpenAI GPT implementation."""

import json
from typing import Any, Protocol, TypeVar

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.core.telemetry import get_tracer

SchemaT = TypeVar("SchemaT", bound=BaseModel)
logger = get_logger(__name__)
tracer = get_tracer(__name__)


class LLMClient(Protocol):
    async def complete_json(
        self, *, system: str, prompt: str, schema: type[SchemaT], context: dict[str, Any] | None = None
    ) -> SchemaT: ...

    async def generate_image(self, prompt: str) -> bytes | None: ...


class OpenAILLMClient:
    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        if client is None:
            if settings.openai_api_key is None:
                raise ValueError("OPENAI_API_KEY is required for OpenAILLMClient")
            client = AsyncOpenAI(
                api_key=settings.openai_api_key.get_secret_value(), timeout=settings.openai_timeout_seconds
            )
        self._client = client
        self._model = settings.openai_model
        self._image_model = settings.openai_image_model
        self._images_enabled = settings.enable_image_generation

    @retry(
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError, ValidationError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def complete_json(
        self, *, system: str, prompt: str, schema: type[SchemaT], context: dict[str, Any] | None = None
    ) -> SchemaT:
        schema_json = json.dumps(schema.model_json_schema())
        with tracer.start_as_current_span("llm.complete_json") as span:
            span.set_attribute("llm.model", self._model)
            span.set_attribute("llm.schema", schema.__name__)
            response = await self._client.chat.completions.create(
                model=self._model,
                temperature=0.7,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": f"{system}\nRespond ONLY with a JSON object matching this JSON schema:\n"
                        f"{schema_json}",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content or "{}"
            if response.usage:
                span.set_attribute("llm.total_tokens", response.usage.total_tokens)
        try:
            return schema.model_validate_json(content)
        except ValidationError:
            logger.warning("llm.invalid_json", schema=schema.__name__)
            raise

    async def generate_image(self, prompt: str) -> bytes | None:
        if not self._images_enabled:
            return None
        import base64

        try:
            result = await self._client.images.generate(
                model=self._image_model, prompt=prompt, size="1024x1536", n=1
            )
        except Exception as exc:  # image generation is best-effort; renderer falls back to solid scenes
            logger.warning("llm.image_failed", error=str(exc))
            return None
        data = result.data[0] if result.data else None
        if data is not None and data.b64_json:
            return base64.b64decode(data.b64_json)
        return None


def ensure_llm_error(exc: Exception) -> ExternalServiceError:
    return ExternalServiceError(f"LLM provider error: {exc}")
