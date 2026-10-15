from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.ingestion import service as ingestion
from app.modules.ingestion.parser import parse_chunks
from app.modules.knowledge import router
from app.modules.knowledge.models import Chunk, DocumentVersion
from tests.test_kb_management import env as kb_env


@pytest.fixture
def env(tmp_path):
    yield from kb_env.__wrapped__(tmp_path)


def test_upload_captures_policy_and_worker_ignores_later_setting_changes(env):
    factory, client, _, _, storage = env
    settings = get_settings()
    text = "# 条款\n\n" + "".join(f"第{i}条需要审核。\n\n" for i in range(180))
    with (
        patch.object(settings, "chunk_strategy", "structure"),
        patch.object(settings, "chunk_size", 600),
        patch.object(settings, "chunk_overlap", 80),
        patch.object(router, "dispatch", return_value={"queued": False, "task_id": None}),
    ):
        response = client.post(
            "/api/v1/documents/1/versions", files={"file": ("policy.md", text.encode())}
        )
    assert response.status_code == 202
    version_id = response.json()["version_id"]
    with factory() as db:
        v = db.get(DocumentVersion, version_id)
        assert (v.chunk_strategy, v.chunk_size, v.chunk_overlap) == ("structure", 600, 80)
        path = storage.path(v.storage_path)
    with (
        patch.object(settings, "chunk_strategy", "fixed"),
        patch.object(settings, "chunk_size", 900),
        patch.object(ingestion, "SessionLocal", factory),
        patch.object(ingestion, "ROOT", storage.root),
    ):
        result = ingestion.process_version(version_id)
        assert result["status"] == "parsed"
        assert ingestion.process_version(version_id)["duplicate"]
    expected = parse_chunks(path, size=600, overlap=80, strategy="structure")
    with factory() as db:
        actual = list(
            db.scalars(
                select(Chunk.content).where(Chunk.version_id == version_id).order_by(Chunk.position)
            )
        )
    assert actual == [c["content"] for c in expected]
    versions = client.get("/api/v1/documents/1/versions").json()
    assert versions[0]["chunk_strategy"] == "structure"
    assert versions[1]["chunk_strategy"] == "fixed"
