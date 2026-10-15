# 中文导读：
# 真实上传与异步解析验收，会写入数据库和文件
# 脚本顶层包含执行逻辑，不要通过导入来读取工具函数

"""Live HTTP / Celery / MySQL verification; leaves a named demo knowledge base."""

import sys
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import httpx
from pypdf import PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.modules.ingestion.service import process_version

client = httpx.Client(base_url="http://127.0.0.1:8010/api/v1", timeout=20)
kb = client.post("/knowledge-bases", json={"name": "入库验证-" + uuid4().hex[:8]})
assert kb.status_code == 201, kb.text
kb_id = kb.json()["id"]
endpoint = f"/knowledge-bases/{kb_id}/documents"


def upload(name, content):
    response = client.post(endpoint, files={"file": (name, content)})
    assert response.status_code == 202, response.text
    assert response.json()["queued"] is True
    return response.json()


def wait(doc):
    for _ in range(40):
        response = client.get(f"/documents/{doc['document_id']}")
        assert response.status_code == 200
        if response.json()["status"] in {"parsed", "failed"}:
            return response.json()
        time.sleep(0.25)
    raise AssertionError("worker did not finish")


body = ("# VPN 使用说明\n员工通过公司账号登录 VPN，连接失败时先检查网络。\n" * 40).encode()
doc = upload("VPN使用说明.md", body)
status = wait(doc)
assert status["status"] == "parsed", status
chunks = client.get(f"/document-versions/{doc['version_id']}/chunks").json()
assert chunks and "VPN" in chunks[0]["content"]
assert process_version(doc["version_id"])["duplicate"] is True
assert len(client.get(f"/document-versions/{doc['version_id']}/chunks").json()) == len(chunks)
print("Markdown upload -> real Celery -> persisted chunks + duplicate delivery: OK")
plain = wait(upload("操作流程.txt", "第一步登录，第二步查询。".encode()))
assert plain["status"] == "parsed"
print("TXT: OK")
assert client.post(endpoint, files={"file": ("bad.exe", b"bad")}).status_code == 415
assert client.post(endpoint, files={"file": ("empty.txt", b"")}).status_code == 422
assert (
    client.post(endpoint, files={"file": ("large.txt", b"a" * (10 * 1024 * 1024 + 1))}).status_code
    == 413
)
assert client.get("/documents/99999999").status_code == 404
bad = upload("invalid.txt", b"\xff\xfe")
assert wait(bad)["status"] == "failed"
assert client.post(f"/document-versions/{bad['version_id']}/retry").json()["queued"]
assert wait(bad)["status"] == "failed"
print("Invalid type / empty / size cap / missing / failed parse + retry: OK")
writer = PdfWriter()
writer.add_blank_page(width=100, height=100)
stream = BytesIO()
writer.write(stream)
blank = upload("扫描件示例.pdf", stream.getvalue())
assert wait(blank)["status"] == "failed"
print("PDF without extractable text rejected: OK")
print(f"Demo KB id: {kb_id}; parsed document id: {doc['document_id']}")
client.close()
