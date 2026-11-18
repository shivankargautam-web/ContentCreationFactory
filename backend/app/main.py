from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.container import Container, get_container
from app.core.exceptions import DomainError
from app.core.logging import configure_logging, get_logger
from app.core.telemetry import configure_telemetry
from app.middleware import RequestContextMiddleware

logger = get_logger(__name__)


def create_app(container: Container | None = None) -> FastAPI:
    container = container or get_container()
    settings = container.settings
    configure_logging(settings.log_level, settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("app.startup", environment=settings.environment)
        yield
        await container.database.dispose()
        logger.info("app.shutdown")

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Generate and publish short-form videos from natural-language instructions.",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        lifespan=lifespan,
    )
    app.state.container = container

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message}}
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {"code": "validation_error", "message": "Request validation failed"},
                "details": jsonable_errors(exc),
            },
        )

    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    if settings.storage_backend == "local":
        Path(settings.local_storage_path).mkdir(parents=True, exist_ok=True)
        app.mount("/media", StaticFiles(directory=settings.local_storage_path), name="media")
    configure_telemetry(settings, app=app, engine=container.database.engine)
    return app


def jsonable_errors(exc: RequestValidationError) -> list[dict]:
    return [{"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]


app = create_app()
