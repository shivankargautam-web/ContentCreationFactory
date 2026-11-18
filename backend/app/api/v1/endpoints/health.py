from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import ContainerDep

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(container: ContainerDep) -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        async with container.database.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ok" if healthy else "degraded", "checks": checks},
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
