"""Turn online feedback into offline regression candidates.

差评（`rating="not_helpful"`）本身就是"这条回答有问题"的线上证据。本脚本把它们整理成
**候选集**，供人工复核后决定是否纳入冻结题集。

刻意不做的事：
- 不修改 `evals/questions.json`、`evals/holdout/**` 等冻结题集（`--out` 指向这些路径会被拒绝）；
- 不自动改写历史评测记录；候选集是**新增文件**，每次运行只合并，不丢已有的人工复核状态。

用法：
    python scripts/feedback_to_regression.py --out evals/regressions/feedback_candidates.json
    python scripts/feedback_to_regression.py --list --out evals/regressions/feedback_candidates.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.config import ROOT
from app.db.session import SessionLocal
from app.modules.feedback.models import AnswerFeedback

FROZEN_PATHS = (
    ROOT / "evals" / "questions.json",
    ROOT / "evals" / "holdout",
)
# 每次合并时允许刷新的字段；其余（人工结论）一律保留。
REFRESHABLE = ("feedback_count", "last_seen", "grounding_status", "citation_count", "reason")


def normalize(text: str) -> str:
    return " ".join((text or "").split())


def is_frozen(path: Path) -> bool:
    resolved = path.resolve()
    for frozen in FROZEN_PATHS:
        if resolved == frozen or frozen in resolved.parents:
            return True
    return False


def collect_candidates(rows) -> list[dict]:
    """One entry per distinct question, carrying the newest complaint."""
    grouped: dict[str, dict] = {}
    for row in rows:
        question = normalize(row.question)
        if not question:
            continue
        created = row.created_at
        entry = grouped.get(question)
        if entry is None:
            grouped[question] = {
                "question": question,
                "reason": row.reason or "",
                "grounding_status": row.grounding_status or "",
                "citation_count": row.citation_count or 0,
                "knowledge_base_id": row.knowledge_base_id,
                "feedback_count": 1,
                "first_seen": created.isoformat() if created else None,
                "last_seen": created.isoformat() if created else None,
                "review_status": "pending",
                "source": "feedback",
            }
            continue
        entry["feedback_count"] += 1
        if created and (entry["last_seen"] is None or created.isoformat() > entry["last_seen"]):
            entry["last_seen"] = created.isoformat()
            entry["reason"] = row.reason or entry["reason"]
            entry["grounding_status"] = row.grounding_status or entry["grounding_status"]
            entry["citation_count"] = row.citation_count or entry["citation_count"]
            entry["knowledge_base_id"] = row.knowledge_base_id or entry["knowledge_base_id"]
    return sorted(grouped.values(), key=lambda item: item["question"])


def merge_candidates(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], int]:
    """Merge by question text; human review fields on existing entries win."""
    merged = {normalize(item.get("question", "")): dict(item) for item in existing}
    added = 0
    for candidate in incoming:
        key = normalize(candidate["question"])
        current = merged.get(key)
        if current is None:
            merged[key] = dict(candidate)
            added += 1
            continue
        for field in REFRESHABLE:
            if field in candidate:
                current[field] = candidate[field]
        current.setdefault("review_status", "pending")
        current.setdefault("source", "feedback")
    return sorted(merged.values(), key=lambda item: item["question"]), added


def load_existing(path: Path) -> dict:
    if not path.is_file():
        return {"metadata": {}, "candidates": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SystemExit(f"已有候选文件不是合法 JSON：{path}（{exc}）") from exc
    payload.setdefault("candidates", [])
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="把线上差评整理成离线回归候选集")
    parser.add_argument(
        "--out",
        default="evals/regressions/feedback_candidates.json",
        help="候选集输出路径（不得指向冻结题集）",
    )
    parser.add_argument("--rating", default="not_helpful", choices=["not_helpful", "helpful"])
    parser.add_argument("--knowledge-base-id", type=int, default=None)
    parser.add_argument("--list", action="store_true", help="只打印现有候选集，不写入")
    args = parser.parse_args()

    out = (ROOT / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    if is_frozen(out):
        raise SystemExit("拒绝写入：该路径属于冻结题集，必须人工复核后手动并入")
    payload = load_existing(out)

    if args.list:
        candidates = payload.get("candidates", [])
        pending = [c for c in candidates if c.get("review_status") == "pending"]
        print(f"候选 {len(candidates)} 条，其中待复核 {len(pending)} 条：{out}")
        for candidate in candidates:
            print(f"  [{candidate.get('review_status')}] {candidate['question']}")
        return

    query = select(AnswerFeedback).where(AnswerFeedback.rating == args.rating)
    if args.knowledge_base_id is not None:
        query = query.where(AnswerFeedback.knowledge_base_id == args.knowledge_base_id)
    with SessionLocal() as db:
        rows = list(db.scalars(query.order_by(AnswerFeedback.id)))

    incoming = collect_candidates(rows)
    merged, added = merge_candidates(payload.get("candidates", []), incoming)
    payload["candidates"] = merged
    payload["metadata"] = {
        **payload.get("metadata", {}),
        "source": "answer_feedback",
        "rating": args.rating,
        "knowledge_base_id": args.knowledge_base_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "candidates": len(merged),
        "pending": sum(1 for c in merged if c.get("review_status") == "pending"),
        "note": "候选集仅供人工复核；冻结题集不会被本脚本修改",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"反馈 {len(rows)} 条 → 候选 {len(merged)} 条（新增 {added}）；写出 {out}")


if __name__ == "__main__":
    main()
