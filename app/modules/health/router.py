from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pymilvus import MilvusClient
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("/live")
def live():
    return {"status": "ok", "service": "knowops", "stage": "scaffold"}


@router.get("/ready")
def ready():
    s = get_settings()
    checks = {}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["mysql"] = "ok"
    except Exception:  # noqa: BLE001 - dependency probe must report degraded status
        checks["mysql"] = "unavailable"
    try:
        with Redis.from_url(s.redis_url, socket_connect_timeout=3, socket_timeout=3) as client:
            client.ping()
        checks["redis"] = "ok"
    except Exception:  # noqa: BLE001 - dependency probe must report degraded status
        checks["redis"] = "unavailable"
    try:
        client = MilvusClient(uri=s.milvus_uri, timeout=3, alias=f"health-{uuid4().hex}")
        try:
            client.list_collections(timeout=3)
        finally:
            client.close()
        checks["milvus"] = "ok"
    except Exception:  # noqa: BLE001 - dependency probe must report degraded status
        checks["milvus"] = "unavailable"
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ok" if ok else "degraded", "checks": checks}, status_code=200 if ok else 503
    )
