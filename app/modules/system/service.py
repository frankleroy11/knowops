"""Read-only, bounded dependency probes; never return provider error details."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from pymilvus import MilvusClient
from redis import Redis
from sqlalchemy import func, select, text

from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.modules.knowledge.models import DocumentVersion, VectorIndex
from app.workers.celery_app import celery_app


def probe_mysql():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "detail": "数据库查询成功"}


def probe_redis():
    with Redis.from_url(
        get_settings().redis_url, socket_connect_timeout=3, socket_timeout=3
    ) as client:
        client.ping()
    return {"status": "ok", "detail": "缓存与消息代理连通"}


def probe_milvus():
    client = MilvusClient(uri=get_settings().milvus_uri, timeout=3, alias=f"health-{uuid4().hex}")
    try:
        client.list_collections(timeout=3)
    finally:
        client.close()
    return {"status": "ok", "detail": "向量库连通；未执行嵌入或检索"}


def probe_worker():
    replies = celery_app.control.inspect(timeout=2).registered() or {}
    required = {"knowops.ingest_document", "knowops.index_document"}
    count = sum(required.issubset(set(tasks)) for tasks in replies.values())
    return {
        "status": "ok" if count else "unknown",
        "workers": count,
        "detail": "KnowOps Worker 控制通道响应；未执行测试任务"
        if count
        else "未收到 KnowOps Worker 响应，可能繁忙、离线或控制通道异常",
    }


def probe_jobs():
    with SessionLocal() as db:
        parsing = dict(
            db.execute(
                select(DocumentVersion.status, func.count()).group_by(DocumentVersion.status)
            ).all()
        )
        indexing = dict(
            db.execute(select(VectorIndex.status, func.count()).group_by(VectorIndex.status)).all()
        )
    return {
        "status": "ok",
        "detail": "业务状态快照，不代表消息队列长度",
        "parsing": parsing,
        "indexing": indexing,
    }


def measured(probe):
    started = perf_counter()
    try:
        result = probe()
    except Exception:  # noqa: BLE001 - sanitize infrastructure failures
        result = {"status": "unavailable", "detail": "检查失败，请查看服务日志"}
    return {**result, "latency_ms": round((perf_counter() - started) * 1000)}


def snapshot():
    probes = {
        "mysql": probe_mysql,
        "redis": probe_redis,
        "milvus": probe_milvus,
        "worker": probe_worker,
        "jobs": probe_jobs,
    }
    with ThreadPoolExecutor(max_workers=len(probes)) as pool:
        futures = {name: pool.submit(measured, probe) for name, probe in probes.items()}
        checks = {name: future.result() for name, future in futures.items()}
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "ok" if all(c["status"] == "ok" for c in checks.values()) else "degraded",
        "checks": checks,
    }
