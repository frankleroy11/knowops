"""数据集入库与索引链路验证（不依赖题集）。

用途：在跑完整评估之前，先确认真实链路能正确处理这批语料：
上传 → 解析 → 索引 → 检索命中，并输出可复现的真实耗时证据。

用法：
    python scripts/check_dataset_pipeline.py --run-label dryrun
    python scripts/check_dataset_pipeline.py --run-label dryrun --reuse   # 复用已入库的数据
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.adapters.vectorstore.milvus import collection_name
from app.core.config import ROOT

EVALS = ROOT / "evals"
DOMAINS = ("it", "hr", "product")
LABEL = {"it": "IT 支持", "hr": "人事制度", "product": "产品与客服"}


def corpus_files(domain: str) -> list[Path]:
    return sorted(
        p
        for p in (EVALS / "corpus" / domain).iterdir()
        if p.suffix.lower() in {".md", ".txt", ".pdf"}
    )


def mime(path: Path) -> str:
    return {".md": "text/markdown", ".txt": "text/plain", ".pdf": "application/pdf"}[
        path.suffix.lower()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8010/api/v1")
    parser.add_argument("--run-label", default="dryrun")
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()

    expected = sum(len(corpus_files(domain)) for domain in DOMAINS)
    print(f"语料文件：{expected} 份（{' + '.join(f'{d}={len(corpus_files(d))}' for d in DOMAINS)}）")
    print(f"collection：{collection_name()}")
    started = time.perf_counter()

    with httpx.Client(base_url=args.base_url, timeout=180) as client:
        listed = client.get("/knowledge-bases", params={"limit": 100}).json()
        by_name = {item["name"]: item["id"] for item in listed}
        kbs: dict[str, int] = {}
        for domain in DOMAINS:
            name = f"评估-{args.run_label}-{LABEL[domain]}"
            if name in by_name:
                kbs[domain] = by_name[name]
                continue
            response = client.post(
                "/knowledge-bases",
                json={"name": name, "description": "星桥科技合成语料，非真实企业制度"},
            )
            if response.status_code == 409:
                listed = client.get("/knowledge-bases", params={"limit": 100}).json()
                kbs[domain] = next(i["id"] for i in listed if i["name"] == name)
            else:
                response.raise_for_status()
                kbs[domain] = response.json()["id"]
        print("知识库：", {d: kbs[d] for d in DOMAINS})

        upload_seconds = 0.0
        if not args.reuse:
            upload_started = time.perf_counter()
            for domain in DOMAINS:
                for path in corpus_files(domain):
                    response = client.post(
                        f"/knowledge-bases/{kbs[domain]}/documents",
                        files={"file": (path.name, path.read_bytes(), mime(path))},
                    )
                    if response.status_code == 409:
                        continue
                    response.raise_for_status()
                    if not response.json().get("queued"):
                        raise RuntimeError(f"未入队：{path.name}")
            upload_seconds = round(time.perf_counter() - upload_started, 1)
            print(f"上传完成：{upload_seconds}s")

        deadline = time.monotonic() + args.timeout
        documents: list[dict] = []
        while time.monotonic() < deadline:
            documents = []
            for domain in DOMAINS:
                response = client.get(
                    f"/knowledge-bases/{kbs[domain]}/documents", params={"limit": 100}
                )
                response.raise_for_status()
                documents.extend(response.json())
            failed = [d for d in documents if d["status"] == "failed" or d["index_status"] == "failed"]
            if failed:
                for item in failed[:10]:
                    print(
                        f"失败：{item['filename']} 解析={item['status']} 索引={item['index_status']} "
                        f"错误={item.get('error') or item.get('index_error')}"
                    )
                return 1
            if len(documents) >= expected and all(d["index_status"] == "indexed" for d in documents):
                break
            time.sleep(3)
        else:
            pending = [d["filename"] for d in documents if d["index_status"] != "indexed"]
            print(f"超时：仍有 {len(pending)} 份未索引，例如 {pending[:5]}")
            return 1

        index_seconds = round(time.perf_counter() - started - upload_seconds, 1)
        chunks = sum(d.get("chunk_count") or 0 for d in documents)
        by_domain = defaultdict(lambda: {"documents": 0, "chunks": 0})
        for domain in DOMAINS:
            names = {p.name for p in corpus_files(domain)}
            for document in documents:
                if document["filename"] in names:
                    by_domain[domain]["documents"] += 1
                    by_domain[domain]["chunks"] += document.get("chunk_count") or 0
        print(
            f"入库+索引完成：{len(documents)} 份文档 / {chunks} 个切片 ｜ "
            f"索引耗时 {index_seconds}s（上传 {upload_seconds}s）"
        )
        for domain, stats in by_domain.items():
            print(f"  {domain}: {stats['documents']} 份 / {stats['chunks']} 切片")

        pdf_report = {}
        for document in documents:
            if not document["filename"].lower().endswith(".pdf"):
                continue
            rows = client.get(
                f"/document-versions/{document['version_id']}/chunks", params={"limit": 100}
            ).json()
            pages = sorted({row["page"] for row in rows if row["page"] is not None})
            pdf_report[document["filename"]] = {"chunks": len(rows), "pages": pages}
        print("PDF 页码溯源：", json.dumps(pdf_report, ensure_ascii=False))

        probe = client.post(
            "/search",
            json={"query": "动态验证码过期了怎么办", "knowledge_base_id": kbs["it"], "top_k": 3},
        )
        probe.raise_for_status()
        hits = probe.json()["hits"]
        print("检索探针（IT 库，问“动态验证码过期了怎么办”）：")
        for hit in hits:
            print(f"  {hit['score']:.4f}  {hit['filename']}  pos={hit['position']}  page={hit['page']}")
        if not hits:
            print("检索探针没有返回结果，链路可能未真正生效", file=sys.stderr)
            return 1

    print(f"总耗时 {round(time.perf_counter() - started, 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
