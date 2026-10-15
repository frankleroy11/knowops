from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.deps import current_principal
from app.modules.auth.principal import LOCAL_ADMIN, Principal
from app.modules.system import service


@pytest.mark.parametrize(
    "principal",
    [Principal(1, "viewer", "viewer"), Principal(2, "tenant-admin", "admin", tenant_id=1)],
)
def test_status_forbidden_before_probes(principal):
    app.dependency_overrides[current_principal] = lambda: principal
    try:
        with patch("app.modules.system.router.snapshot") as snapshot:
            assert TestClient(app).get("/api/v1/admin/system/status").status_code == 403
            snapshot.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_status_returns_degraded_snapshot_for_platform_admin():
    app.dependency_overrides[current_principal] = lambda: LOCAL_ADMIN
    try:
        with patch("app.modules.system.router.snapshot", return_value={"status": "degraded"}):
            response = TestClient(app).get("/api/v1/admin/system/status")
            assert response.status_code == 200
            assert response.json()["status"] == "degraded"
    finally:
        app.dependency_overrides.clear()


def test_snapshot_isolates_failure_and_hides_provider_details():
    with (
        patch.object(service, "probe_mysql", side_effect=RuntimeError("password=secret")),
        patch.object(service, "probe_redis", return_value={"status": "ok"}),
        patch.object(service, "probe_milvus", return_value={"status": "ok"}),
        patch.object(service, "probe_worker", return_value={"status": "unknown"}),
        patch.object(service, "probe_jobs", return_value={"status": "ok", "parsing": {}}),
    ):
        result = service.snapshot()
    assert result["status"] == "degraded"
    assert result["checks"]["mysql"]["status"] == "unavailable"
    assert result["checks"]["redis"]["status"] == "ok"
    assert result["checks"]["worker"]["status"] == "unknown"
    assert "password" not in str(result)
    assert all(item["latency_ms"] >= 0 for item in result["checks"].values())


@pytest.mark.parametrize(
    "replies,expected",
    [
        ({}, 0),
        ({"other-app": ["other.task"]}, 0),
        ({"partial": ["knowops.ingest_document"]}, 0),
        ({"knowops": ["knowops.ingest_document", "knowops.index_document"]}, 1),
    ],
)
def test_only_knowops_workers_count(replies, expected):
    with patch.object(service.celery_app.control, "inspect") as inspect:
        inspect.return_value.registered.return_value = replies
        result = service.probe_worker()
    assert result["workers"] == expected
    assert result["status"] == ("ok" if expected else "unknown")


def test_status_requires_login_in_enforced_mode():
    from app.core.config import get_settings

    with (
        patch.object(get_settings(), "auth_mode", "enforced"),
        patch("app.modules.system.router.snapshot") as snapshot,
    ):
        assert TestClient(app).get("/api/v1/admin/system/status").status_code == 401
        snapshot.assert_not_called()
