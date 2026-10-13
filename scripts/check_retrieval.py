"""Real HTTP/Worker/Milvus verification; retains the indexed demo version."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.adapters.vectorstore.milvus import MilvusStore


def main():
    with httpx.Client(base_url="http://127.0.0.1:8010/api/v1", timeout=180) as client:
        doc = client.get("/documents/3").raise_for_status().json()
        version = doc["version_id"]
        for _ in range(2):
            queued = client.post(f"/document-versions/{version}/index").raise_for_status().json()
            from app.workers.celery_app import celery_app

            result = celery_app.AsyncResult(queued["task_id"]).get(timeout=300)
            assert result["status"] == "indexed", result
            store = MilvusStore()
            try:
                rows = store.client.query(
                    store.name,
                    filter=f"version_id == {version}",
                    output_fields=["chunk_id"],
                    limit=100,
                )
                assert len(rows) == doc["chunk_count"], rows
            finally:
                store.close()
        found = client.post(
            "/search",
            json={
                "query": "在家办公如何连接公司内网？",
                "knowledge_base_id": doc["knowledge_base_id"],
                "top_k": 3,
            },
        )
        found.raise_for_status()
        hits = found.json()["hits"]
        assert hits and any("VPN" in hit["content"] for hit in hits), hits
        other = client.post("/search", json={"query": "VPN", "knowledge_base_id": 1})
        other.raise_for_status()
        assert all(hit["document_id"] != doc["id"] for hit in other.json()["hits"])
        assert (
            client.post("/search", json={"query": " ", "knowledge_base_id": 2}).status_code == 422
        )
        assert client.post("/document-versions/999999/index").status_code == 404
        print(
            {
                "status": "passed",
                "chunks": doc["chunk_count"],
                "top_filename": hits[0]["filename"],
                "top_score": hits[0]["score"],
                "verified": ["worker", "real_embeddings", "idempotence", "kb_filter"],
            }
        )


if __name__ == "__main__":
    main()
