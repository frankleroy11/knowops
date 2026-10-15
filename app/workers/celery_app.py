# 中文导读：
# Celery 配置及解析、索引任务入口
# 任务可能重复投递，业务层需保持幂等；修改 Worker 代码后必须重启 Worker，API 热重载不会重启它

from celery import Celery
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings

s = get_settings()
celery_app = Celery("knowops", broker=s.redis_url, backend=s.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    broker_connection_retry_on_startup=True,
    task_publish_retry=False,
    broker_transport_options={"socket_connect_timeout": 3, "socket_timeout": 3},
)


@celery_app.task(name="knowops.ping")
def ping():
    return "pong"


@celery_app.task(
    name="knowops.ingest_document",
    acks_late=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    max_retries=3,
)
def ingest_document(version_id: int):
    from app.modules.ingestion.service import process_version

    result = process_version(version_id)
    if result.get("status") == "parsed":
        try:
            task = index_document.delay(version_id)
            result["index_queued"] = True
            result["index_task_id"] = task.id
        except Exception:  # noqa: BLE001 - parsed data persists; manual index remains available
            result["index_queued"] = False
    return result


@celery_app.task(
    name="knowops.index_document",
    acks_late=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    max_retries=3,
)
def index_document(version_id: int):
    from app.modules.retrieval.service import index_version

    return index_version(version_id)
