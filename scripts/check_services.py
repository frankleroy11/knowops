"""Development smoke checks. Uses disposable data and cleans up after itself."""

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pymilvus import MilvusClient
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

s = get_settings()
with engine.begin() as conn:
    conn.execute(text("CREATE TEMPORARY TABLE knowops_smoke (value INT)"))
    conn.execute(text("INSERT INTO knowops_smoke VALUES (42)"))
    assert conn.execute(text("SELECT value FROM knowops_smoke")).scalar_one() == 42
    conn.execute(text("DROP TEMPORARY TABLE knowops_smoke"))
print("MySQL read/write: OK")
with Redis.from_url(s.redis_url) as redis:
    key = f"knowops:smoke:{uuid4().hex}"
    try:
        redis.set(key, "ok", ex=60)
        assert redis.get(key) == b"ok"
    finally:
        redis.delete(key)
print("Redis read/write: OK")
client = MilvusClient(uri=s.milvus_uri, timeout=15)
name = "knowops_smoke_" + uuid4().hex
try:
    client.create_collection(collection_name=name, dimension=4, metric_type="COSINE")
    client.insert(collection_name=name, data=[{"id": 1, "vector": [1.0, 0.0, 0.0, 0.0]}])
    result = client.search(
        collection_name=name, data=[[1.0, 0.0, 0.0, 0.0]], limit=1, consistency_level="Strong"
    )
    assert result[0][0]["id"] == 1
finally:
    if client.has_collection(name):
        client.drop_collection(name)
    client.close()
print("Milvus insert/search: OK")
