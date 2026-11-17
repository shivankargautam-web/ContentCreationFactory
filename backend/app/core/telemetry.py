"""OpenTelemetry bootstrap for traces across FastAPI, SQLAlchemy, httpx, Redis and Celery."""

from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_configured = False


def configure_telemetry(settings: Settings, app: Any | None = None, engine: Any | None = None) -> None:
    global _configured
    if not settings.otel_enabled:
        return
    if not _configured:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        provider = TracerProvider(
            resource=Resource.create(
                {SERVICE_NAME: settings.otel_service_name, "deployment.environment": settings.environment}
            )
        )
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True))
        )
        trace.set_tracer_provider(provider)
        HTTPXClientInstrumentor().instrument()
        RedisInstrumentor().instrument()
        _configured = True
        logger.info("otel.configured", endpoint=settings.otel_exporter_otlp_endpoint)

    if app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
    if engine is not None:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


def instrument_celery(settings: Settings) -> None:
    if not settings.otel_enabled:
        return
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    configure_telemetry(settings)
    CeleryInstrumentor().instrument()


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
