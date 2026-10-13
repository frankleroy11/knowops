"""星桥科技合成数据集评估：分知识库入库 + 切片级检索指标 + 生成质量指标。

与 scripts/evaluate.py（v1，旧的 6 文件单库流程，已归档到 evals/legacy/）的区别：
1. 三个知识库各自入库，题目按 domain 路由到对应知识库；
2. 增加切片级 Recall@k、MRR@3、nDCG@5、按难度与 dev/test 分组的指标；
3. 修复 v1 的两个问题：不再是 git 仓库也能跑；知识库按稳定名称复用，不重复堆积；
4. 记录数据集哈希、模型配置、索引耗时，索引阶段不混入生成阶段。

用法：
    python scripts/evaluate_v2.py                 # 全量（dev+test）
    python scripts/evaluate_v2.py --split dev     # 只跑 dev
    python scripts/evaluate_v2.py --reuse         # 复用已入库且已索引的知识库
    python scripts/evaluate_v2.py --skip-chat     # 只评检索，不调用大模型
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import select

from app.adapters.vectorstore.milvus import collection_name
from app.core.config import ROOT, get_settings
from app.db.session import SessionLocal
from app.modules.knowledge.models import Document, DocumentVersion, VectorIndex

EVALS = ROOT / "evals"
DOMAINS = ("it", "hr", "product")
DOMAIN_LABEL = {"it": "IT 支持", "hr": "人事制度", "product": "产品与客服"}
SPLIT_CHOICES = ("all", "dev", "test")
METRIC_VERSION = "evidence-v3"


def percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(quantile * len(ordered)) - 1)], 2)


def normalize(text: str) -> str:
    return " ".join(str(text).split())


def ratio(hits: int, total: int):
    return round(hits / total, 4) if total else None


def ndcg(relevances: list[int], k: int, total_relevant: int) -> float:
    """Distinct evidence-source gain; ideal uses all annotated sources, including missing ones."""
    dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances[:k]))
    idcg = sum(1 / math.log2(i + 2) for i in range(min(k, total_relevant)))
    return round(dcg / idcg, 4) if idcg else 0.0


def evaluation_kind(question):
    return "isolation" if "isolation" in question else question["kind"]


def evidence_metrics(question, hits):
    expected = set(question["expected_sources"])
    if not expected:
        return {}
    terms = [normalize(t) for t in question.get("terms", []) if str(t).strip()]
    required = {}
    for filename in expected:
        path = EVALS / "corpus" / question["domain"] / filename
        text = normalize(path.read_text(encoding="utf-8"))
        required[filename] = [term for term in terms if term in text]
        if terms and not required[filename]:
            return {
                "doc_recall_at_k": expected.issubset({h["filename"] for h in hits}),
                "evidence_label_error": f"来源缺少标注证据: {filename}",
            }

    def coverage(prefix):
        return all(
            any(h["filename"] == name for h in prefix)
            and all(
                any(h["filename"] == name and term in normalize(h["content"]) for h in prefix)
                for term in source_terms
            )
            for name, source_terms in required.items()
        )

    seen = set()
    gains = []
    first = None
    for rank, hit in enumerate(hits, 1):
        name = hit["filename"]
        relevant = name in required and (
            not required[name] or any(term in normalize(hit["content"]) for term in required[name])
        )
        if relevant and first is None:
            first = rank
        gains.append(int(relevant and name not in seen))
        if relevant:
            seen.add(name)
    return {
        "doc_recall_at_k": expected.issubset({h["filename"] for h in hits}),
        "chunk_recall_at_1": coverage(hits[:1]),
        "chunk_recall_at_k": coverage(hits),
        "evidence_complete_at_k": coverage(hits),
        "mrr_at_k": round(1 / first, 4) if first else 0.0,
        "ndcg_at_k": ndcg(gains, len(hits), len(expected)),
        "answer_slice_found": coverage(hits),
    }


def corpus_files(domain: str) -> list[Path]:
    """语料文件：Markdown 为正文，PDF 为附录（用于验证分页与页码溯源）。"""
    folder = EVALS / "corpus" / domain
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in {".md", ".txt", ".pdf"})


def corpus_sha256() -> dict:
    return {
        f"{domain}/{path.name}": hashlib.sha256(path.read_bytes()).hexdigest()
        for domain in DOMAINS
        for path in corpus_files(domain)
    }


def git_info() -> tuple[str | None, bool | None]:
    """v1 用 subprocess 调用 git，非 git 仓库会直接崩溃；这里降级为不可用。"""
    import subprocess

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
            ).strip()
        )
        return commit, dirty
    except Exception:  # noqa: BLE001 - 项目当前不是 git 仓库
        return None, None


class Harness:
    def __init__(self, client: httpx.Client, label: str, reuse: bool):
        self.client = client
        self.label = label
        self.reuse = reuse
        self.kbs: dict[str, int] = {}
        self.documents: list[dict] = []
        self.max_chunks_per_version: dict[int, int] = {}

    # ---------- 知识库 ----------
    def kb_name(self, domain: str) -> str:
        return f"评估-{self.label}-{DOMAIN_LABEL[domain]}"

    def ensure_kbs(self):
        listed = self.client.get("/knowledge-bases", params={"limit": 100}).json()
        by_name = {item["name"]: item["id"] for item in listed}
        for domain in DOMAINS:
            name = self.kb_name(domain)
            if name in by_name:
                self.kbs[domain] = by_name[name]
                continue
            response = self.client.post(
                "/knowledge-bases",
                json={"name": name, "description": "星桥科技合成语料，非真实企业制度"},
            )
            if response.status_code == 409:
                listed = self.client.get("/knowledge-bases", params={"limit": 100}).json()
                self.kbs[domain] = next(i["id"] for i in listed if i["name"] == name)
            else:
                response.raise_for_status()
                self.kbs[domain] = response.json()["id"]

    # ---------- 上传与索引 ----------
    def upload_all(self):
        for domain in DOMAINS:
            kb_id = self.kbs[domain]
            for path in corpus_files(domain):
                mime = {
                    ".md": "text/markdown",
                    ".txt": "text/plain",
                    ".pdf": "application/pdf",
                }[path.suffix.lower()]
                response = self.client.post(
                    f"/knowledge-bases/{kb_id}/documents",
                    files={"file": (path.name, path.read_bytes(), mime)},
                )
                if response.status_code == 409:
                    continue
                response.raise_for_status()
                body = response.json()
                if not body.get("queued"):
                    raise RuntimeError(f"上传成功但未入队：{path.name}")

    def list_documents(self) -> list[dict]:
        documents = []
        for kb_id in self.kbs.values():
            response = self.client.get(f"/knowledge-bases/{kb_id}/documents", params={"limit": 100})
            response.raise_for_status()
            documents.extend(response.json())
        return documents

    def wait_indexed(self, expected_docs: int, timeout: int) -> tuple[list[dict], float]:
        deadline = time.monotonic() + timeout
        started = time.monotonic()
        last: list[dict] = []
        while time.monotonic() < deadline:
            last = self.list_documents()
            failed = [d for d in last if d["status"] == "failed" or d["index_status"] == "failed"]
            if failed:
                names = ", ".join(
                    f"{d['filename']}({d['status']}/{d['index_status']})" for d in failed[:5]
                )
                raise RuntimeError(f"入库或索引失败：{names}")
            if len(last) >= expected_docs and all(d["index_status"] == "indexed" for d in last):
                self.documents = last
                return last, round(time.monotonic() - started, 1)
            time.sleep(3)
        pending = [d["filename"] for d in last if d["index_status"] != "indexed"]
        raise RuntimeError(f"入库/索引超时，仍有 {len(pending)} 份未完成：{pending[:5]}")

    def check_pdf_pages(self) -> dict:
        """验证 PDF 附录真的被解析出页码（chunks.page），而不是与文本文件同等对待。"""
        report = {}
        for document in self.documents:
            if not document["filename"].lower().endswith(".pdf"):
                continue
            chunks = self.client.get(
                f"/document-versions/{document['version_id']}/chunks", params={"limit": 100}
            ).json()
            pages = [chunk["page"] for chunk in chunks]
            report[document["filename"]] = {
                "chunks": len(chunks),
                "pages": pages,
                "has_page_numbers": bool(pages) and all(page is not None for page in pages),
                "max_page": max((p for p in pages if p is not None), default=None),
            }
        report["_summary"] = {
            "pdf_documents": len(report),
            "all_pages_traced": bool(report)
            and all(item["has_page_numbers"] for key, item in report.items() if key != "_summary"),
        }
        return report

    def reindex_failed(self) -> dict:
        """把已解析但索引非 indexed 的版本重新投递，用于验证重试幂等。"""
        with SessionLocal() as db:
            rows = db.execute(
                select(DocumentVersion.id, VectorIndex.status).outerjoin(
                    VectorIndex,
                    (VectorIndex.version_id == DocumentVersion.id)
                    & (VectorIndex.collection == collection_name()),
                )
            ).all()
        retried = []
        for version_id, status in rows:
            if status == "indexed":
                continue
            response = self.client.post(f"/document-versions/{version_id}/index")
            if response.status_code == 202:
                retried.append(version_id)
        return {"retried_versions": len(retried), "sample": retried[:5]}

    def chunk_counts(self) -> dict[int, int]:
        with SessionLocal() as db:
            documents = db.scalars(select(Document)).all()
            versions = db.scalars(select(DocumentVersion)).all()
            from app.modules.knowledge.models import Chunk

            counts = defaultdict(int)
            for chunk in db.scalars(select(Chunk)).all():
                counts[chunk.version_id] += 1
        self.max_chunks_per_version = dict(counts)
        assert documents and versions
        return dict(counts)

    # ---------- 单题 ----------
    def run_question(self, question: dict, top_k: int, skip_chat: bool) -> dict:
        row = {
            **question,
            "evaluation_kind": evaluation_kind(question),
            "error": None,
            "human_correct": None,
            "human_supported": None,
        }
        # 跨库隔离题必须投到 ask_domain（另一个知识库），否则检验不到知识库过滤
        ask_domain = question.get("ask_domain") or question["domain"]
        kb_id = self.kbs[ask_domain]
        row["asked_in"] = ask_domain
        expected = set(question["expected_sources"])
        try:
            started = time.perf_counter()
            retrieved = self.client.post(
                "/search",
                json={"query": question["question"], "knowledge_base_id": kb_id, "top_k": top_k},
            )
            retrieved.raise_for_status()
            row["retrieval_ms"] = round((time.perf_counter() - started) * 1000, 2)
            hits = retrieved.json()["hits"]
            row["retrieved_sources"] = [hit["filename"] for hit in hits]
            row["retrieved_scores"] = [round(hit["score"], 4) for hit in hits]
            row["retrieved_chunk_ids"] = [hit["chunk_id"] for hit in hits]
            row["retrieved_pages"] = [hit["page"] for hit in hits]

            row.update(evidence_metrics(question, hits))
            if "isolation" in question:
                with SessionLocal() as db:
                    owners = dict(
                        db.execute(
                            select(Document.id, Document.knowledge_base_id).where(
                                Document.id.in_([h["document_id"] for h in hits])
                            )
                        ).all()
                    )
                row["cross_kb_leakage"] = any(owners.get(h["document_id"]) != kb_id for h in hits)

            if skip_chat:
                return row
            started = time.perf_counter()
            response = self.client.post(
                "/chat/ask",
                json={"question": question["question"], "knowledge_base_id": kb_id, "top_k": top_k},
            )
            response.raise_for_status()
            row["chat_ms"] = round((time.perf_counter() - started) * 1000, 2)
            answer = response.json()
            row.update(answer)
            cited = [citation["filename"] for citation in answer["citations"]]
            row["citation_filenames"] = cited
            if expected:
                row["citation_match"] = (
                    bool(cited) and expected.issubset(set(cited)) and set(cited).issubset(expected)
                )
                row["keyword_pass"] = bool(answer["answerable"]) and all(
                    keyword.casefold() in answer["answer"].casefold()
                    for keyword in question["keywords"]
                )
            else:
                row["correct_refusal"] = answer["answerable"] is False and not answer["citations"]
            return row
        except httpx.HTTPError as error:
            row["error"] = (
                f"HTTP {error.response.status_code}"
                if isinstance(error, httpx.HTTPStatusError)
                else type(error).__name__
            )
            return row


def summarize(rows: list[dict], skip_chat: bool) -> dict:
    answerable = [r for r in rows if evaluation_kind(r) == "answerable"]
    refusal = [r for r in rows if evaluation_kind(r) != "answerable"]
    isolation = [r for r in rows if evaluation_kind(r) == "isolation"]
    evidence_valid = [r for r in answerable if not r.get("evidence_label_error")]
    successful = [r for r in rows if not r.get("error")]

    def rate(group, key):
        values = [r.get(key, False) for r in group]
        return ratio(sum(bool(value) for value in values), len(values))

    def mean(group, key):
        values = [r.get(key, False) for r in group]
        return round(sum(values) / len(values), 4) if values else None

    summary = {
        "questions": len(rows),
        "successful_requests": len(successful),
        "answerable_questions": len(answerable),
        "refusal_questions": len(refusal),
        "isolation_questions": len(isolation),
        "isolation_checked_requests": sum("cross_kb_leakage" in r for r in isolation),
        "evidence_evaluable_questions": len(evidence_valid),
        "evidence_label_errors": len(answerable) - len(evidence_valid),
        "isolation_leakage_rate": rate(isolation, "cross_kb_leakage"),
        "isolation_refusal_accuracy": rate(isolation, "correct_refusal"),
        "evidence_complete_at_k": rate(evidence_valid, "evidence_complete_at_k"),
        "source_recall_at_k": rate(answerable, "doc_recall_at_k"),
        "chunk_recall_at_1": rate(evidence_valid, "chunk_recall_at_1"),
        "chunk_recall_at_k": rate(evidence_valid, "chunk_recall_at_k"),
        "mrr_at_k": mean(evidence_valid, "mrr_at_k"),
        "ndcg_at_k": mean(evidence_valid, "ndcg_at_k"),
        "refusal_accuracy": rate(refusal, "correct_refusal"),
        "answerable_response_rate": rate(answerable, "answerable"),
        "citation_source_match_rate": rate(answerable, "citation_match"),
        "keyword_pass_rate_heuristic_only": rate(answerable, "keyword_pass"),
        "timings_ms": {
            stage: {"p50": percentile(values, 0.5), "p95": percentile(values, 0.95)}
            for stage, values in (
                ("retrieval", [r["retrieval_ms"] for r in successful if "retrieval_ms" in r]),
                ("chat", [r["chat_ms"] for r in successful if "chat_ms" in r]),
            )
        },
    }
    if skip_chat:
        summary.pop("isolation_refusal_accuracy", None)
        for key in (
            "refusal_accuracy",
            "answerable_response_rate",
            "citation_source_match_rate",
            "keyword_pass_rate_heuristic_only",
        ):
            summary.pop(key, None)
    return summary


def grouped(rows: list[dict], key: str, skip_chat: bool) -> dict:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(key))].append(row)
    return {name: summarize(items, skip_chat) for name, items in sorted(buckets.items())}


def write_report(folder: Path, payload: dict, skip_chat: bool):
    (folder / "results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = payload["summary"]
    lines = [
        "# KnowOps 星桥科技合成数据集评估",
        "",
        (
            "**重要声明**：本数据集全部为合成内容（虚构企业「星桥科技」），不对应任何真实企业制度、"
            "产品或人员。指标只代表在该合成语料上的表现，**不能**作为真实企业准确率或生产性能依据。"
        ),
        "",
        f"- 运行标识：{payload['metadata']['run_label']}",
        (
            f"- 题数：{summary['questions']}（{summary.get('answerable_questions')} 有答案 / "
            f"{summary.get('refusal_questions')} 期望拒答）"
        ),
        f"- 知识库：{', '.join(f'{k}={v}' for k, v in payload['metadata']['knowledge_bases'].items())}",
        "- 证据覆盖：分别在各标注来源的切片中匹配该来源的 terms；允许跨切片联合覆盖。",
        "- Recall@1 仅检查第一条；MRR 检查首个支持证据；nDCG 按不同来源去重，理想值包含未召回来源。",
        "- 隔离题单列，计入期望拒答题；无泄漏与正确拒答是两个不同指标。",
        "",
        "## 自动指标",
        "",
        "```json",
        json.dumps(summary, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 按难度分组（有答案题）",
        "",
        "```json",
        json.dumps(payload["by_difficulty"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 按 dev / test 分组",
        "",
        "```json",
        json.dumps(payload["by_split"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 按知识库分组",
        "",
        "```json",
        json.dumps(payload["by_domain"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 逐题结果",
        "",
        "|题号|库|难度|类型|文档命中|切片命中|MRR|引用匹配|正确拒答|",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in payload["rows"]:
        lines.append(
            "|"
            + "|".join(
                str(row.get(key, "-"))
                for key in [
                    "id",
                    "domain",
                    "difficulty",
                    "kind",
                    "doc_recall_at_k",
                    "chunk_recall_at_k",
                    "mrr_at_k",
                    "citation_match",
                    "correct_refusal",
                ]
            )
            + "|"
        )
    lines += [
        "",
        "## 人工复核",
        "",
        "逐题核对答案正确性与原文支持程度；未复核题目的人工分数留空。",
        "",
    ]
    for row in payload["rows"]:
        lines += [
            f"### {row['id']} {row['question']}",
            "",
            f"难度：{row.get('difficulty')} ｜ 库：{row.get('domain')} ｜ split：{row.get('split')}",
            "",
            f"标注来源：{', '.join(row.get('expected_sources') or []) or '（期望拒答）'}",
            "",
            f"检索来源：{', '.join(row.get('retrieved_sources') or []) or '无'}",
            "",
            f"参考：{row.get('reference_answer') or '（无）'}",
            "",
            f"实际：{row.get('answer', '请求失败' if row.get('error') else '未调用生成')}",
            "",
            f"引用：{', '.join(row.get('citation_filenames') or []) or '无'}",
            "",
            "人工结论：待复核",
            "",
        ]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8010/api/v1")
    parser.add_argument("--run-label", default=None, help="知识库名称标识，默认取数据集名")
    parser.add_argument("--split", choices=SPLIT_CHOICES, default="all")
    parser.add_argument("--top-k", type=int, choices=range(1, 51), default=3)
    parser.add_argument("--skip-chat", action="store_true", help="只评检索，不调用大模型")
    parser.add_argument("--reuse", action="store_true", help="复用已入库且已索引的知识库，跳过上传")
    parser.add_argument("--index-timeout", type=int, default=1800)
    args = parser.parse_args()

    questions_path = EVALS / "questions.json"
    if not questions_path.exists():
        print(
            "缺少 evals/questions.json，请先运行 python evals/tools/build_questions.py",
            file=sys.stderr,
        )
        return 2
    raw = questions_path.read_bytes()
    questions = [q for q in json.loads(raw) if args.split == "all" or q["split"] == args.split]
    if not questions:
        print("筛选后没有题目", file=sys.stderr)
        return 2
    corpus_files = corpus_sha256()
    label = args.run_label or "knowops-synthetic-v1"
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    folder = EVALS / "runs" / stamp
    folder.mkdir(parents=True)
    settings = get_settings()
    commit, dirty = git_info()
    metadata = {
        "timestamp": stamp,
        "metric_version": METRIC_VERSION,
        "run_label": label,
        "dataset": "knowops-synthetic-enterprise-v1",
        "dataset_name": "星桥科技（虚构）合成语料",
        "disclaimer": "全部语料为合成内容，不对应任何真实企业；指标不得作为真实企业准确率依据。",
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "dataset_manifest_sha256": hashlib.sha256(
            (EVALS / "manifest.json").read_bytes()
        ).hexdigest()
        if (EVALS / "manifest.json").exists()
        else None,
        "corpus_files": len(corpus_files),
        "corpus_sha256": corpus_files,
        "split_filter": args.split,
        "top_k": args.top_k,
        "skip_chat": args.skip_chat,
        "embedding_model": settings.embedding_model,
        "embedder_provider": settings.embedder_provider,
        "embedding_max_length": settings.embedding_max_length,
        "collection": collection_name(),
        "llm_model": None if args.skip_chat else settings.llm_model,
        "git_commit": commit,
        "working_tree_dirty": dirty,
    }
    payload = {"metadata": metadata, "rows": [], "summary": {}}
    (folder / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("Run:", folder, flush=True)
    print(f"题目 {len(questions)} ｜ split={args.split} ｜ skip_chat={args.skip_chat}", flush=True)

    with httpx.Client(base_url=args.base_url, timeout=180) as client:
        harness = Harness(client, label, args.reuse)
        harness.ensure_kbs()
        metadata["knowledge_bases"] = {d: harness.kb_name(d) for d in DOMAINS}
        metadata["knowledge_base_ids"] = harness.kbs
        if not args.reuse:
            upload_started = time.perf_counter()
            harness.upload_all()
            metadata["upload_seconds"] = round(time.perf_counter() - upload_started, 1)
        expected_docs = len(corpus_files)
        documents, index_seconds = harness.wait_indexed(expected_docs, args.index_timeout)
        metadata["index_seconds"] = index_seconds
        metadata["indexed_documents"] = len(documents)
        metadata["chunks_total"] = sum(d.get("chunk_count") or 0 for d in documents)
        metadata["pdf_pages"] = harness.check_pdf_pages()
        (folder / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"入库完成：{len(documents)} 份文档 / {metadata['chunks_total']} 个切片 / "
            f"索引耗时 {index_seconds}s",
            flush=True,
        )

        for question in questions:
            row = harness.run_question(question, args.top_k, args.skip_chat)
            payload["rows"].append(row)
            payload["summary"] = summarize(payload["rows"], args.skip_chat)
            payload["by_difficulty"] = grouped(payload["rows"], "difficulty", args.skip_chat)
            payload["by_split"] = grouped(payload["rows"], "split", args.skip_chat)
            payload["by_domain"] = grouped(payload["rows"], "domain", args.skip_chat)
            write_report(folder, payload, args.skip_chat)
            print(question["id"], "ERROR" if row.get("error") else "done", flush=True)

    payload["metadata"] = metadata
    write_report(folder, payload, args.skip_chat)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
