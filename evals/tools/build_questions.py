"""把三组 facts JSONL 装配成评估题集，并对标注做可执行的 grounding 校验。

设计原则：题集不是"手写的 json"，而是从语料事实标注推导出来的产物，且每一项标注都必须
能在语料里被机械验证。任何校验失败都会非零退出，避免把"看起来对"的数据带进评估。

用法：
    python evals/tools/build_questions.py            # 校验 + 生成 questions.json 与 manifest.json
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpus

ROOT = Path(__file__).resolve().parents[2]
EVALS = ROOT / "evals"
CORPUS = EVALS / "corpus"
FACTS = EVALS / "facts"
DOMAINS = corpus.DOMAINS
ANSWERABLE_PER_DOMAIN = 34
REFUSAL_PER_DOMAIN = 16
CROSS_KB_PER_DOMAIN = 6
#: 稳定且可复现的 dev/test 切分：按 golden ratio 分桶，保证同一难度在不同库里抽样比例接近。
DEV_BUCKET = 0.618


class ValidationError(RuntimeError):
    pass


def read_jsonl(path: Path) -> list[dict]:
    """读取 JSONL；坏行会带上行号，便于直接定位修复。"""
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{path.name} 第 {number} 行不是合法 JSON：{exc}") from exc
    return rows


def corpus_files(domain: str) -> list[Path]:
    return corpus.corpus_files(domain)


def normalize(text: str) -> str:
    """折叠空白便于逐字比对（语料里可能有全角空格与换行）。"""
    return " ".join(text.split())


def longest_common_substring(left: str, right: str) -> int:
    """最长公共子串长度，用于检测"提问直接抄原文"。

    提问抄原文会让检索指标虚高：向量模型只要匹配到同样措辞就能命中，
    无法反映真实用户换词提问时的表现。阈值取 15 个字符。
    """
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    best = 0
    for i in range(1, len(left) + 1):
        current = [0] * (len(right) + 1)
        for j in range(1, len(right) + 1):
            if left[i - 1] == right[j - 1]:
                current[j] = previous[j - 1] + 1
                best = max(best, current[j])
        previous = current
    return best


#: 提问与源文的最长公共子串上限。超过说明提问几乎是原文复述。
MAX_QUESTION_OVERLAP = 15


#: 这些是跨主题通用表述，不能作为"两个库同主题"的证据。
GENERIC_TITLE_TOKENS = {
    "管理办法", "规定", "流程", "说明", "指南", "手册", "对照表", "一览表", "登记表",
    "接入与", "分级与", "与规范", "操作指南", "常见问题", "排查指南", "保留策略",
}


def title_tokens(name: str) -> set[str]:
    """从文件名提取 2 字以上的中文片段，用于判断两个知识库是否存在同主题文档。"""
    stem = name.rsplit(".", 1)[0]
    cleaned = re.sub(r"[（）()【】\[\]、，,。 ._\-–—]", " ", stem)
    tokens: set[str] = set()
    for part in cleaned.split():
        for size in (4, 3, 2):
            for start in range(max(len(part) - size + 1, 0)):
                tokens.add(part[start : start + size])
    return tokens - GENERIC_TITLE_TOKENS


def asking_kb_neighbours(domain: str, sources: list[str]) -> list[str]:
    """找出提问库里与答案文档同主题的文件。

    跨库隔离题必须是"提问所在库确实没有同主题资料"，否则拒答并不是唯一正确答案：
    模型基于提问库里相邻主题的资料作答可能是合理的，这类题按"应拒答"计分就是标注缺陷。

    判定要求共享事实主题词（长度 ≥3 且非通用表述），避免"接入与""对照表"这类措辞误报。
    """
    tokens: set[str] = set()
    for name in sources:
        tokens |= title_tokens(name)
    tokens = {token for token in tokens if len(token) >= 3}
    neighbours = []
    for path in corpus_files(domain):
        if path.suffix.lower() not in corpus.TEXT_SUFFIXES:
            continue
        shared = {token for token in (tokens & title_tokens(path.name)) if len(token) >= 3}
        if shared:
            neighbours.append(f"{path.name}（共享片段 {sorted(shared)[:3]}）")
    return neighbours


def validate_domain(domain: str, rows: list[dict]) -> list[str]:
    problems: list[str] = []
    files = {p.name: p for p in corpus_files(domain)}
    if not files:
        problems.append(f"{domain}: 语料目录为空")
    kinds = Counter(row.get("kind") for row in rows)
    expected_counts = {
        "answerable": ANSWERABLE_PER_DOMAIN,
        "refusal": REFUSAL_PER_DOMAIN,
        "cross_kb": CROSS_KB_PER_DOMAIN,
    }
    for kind, count in expected_counts.items():
        if kinds.get(kind, 0) != count:
            problems.append(f"{domain}: kind={kind} 应为 {count} 条，实际 {kinds.get(kind, 0)} 条")

    contents = {
        name: normalize(path.read_text(encoding="utf-8"))
        for name, path in files.items()
        if path.suffix.lower() in corpus.TEXT_SUFFIXES  # PDF 是二进制，不参与 terms 逐字比对
    }
    seen_ids: set[str] = set()
    for row in rows:
        qid = row.get("id")
        if not qid:
            problems.append(f"{domain}: 存在缺少 id 的行")
            continue
        if qid in seen_ids:
            problems.append(f"{domain}: id 重复 {qid}")
        seen_ids.add(qid)
        kind = row.get("kind")
        if not str(row.get("question", "")).strip():
            problems.append(f"{qid}: question 为空")
        sources = row.get("expected_sources")
        if not isinstance(sources, list):
            problems.append(f"{qid}: expected_sources 必须是列表")
            continue
        if kind == "refusal":
            if sources:
                problems.append(f"{qid}: refusal 的 expected_sources 必须为空")
            if row.get("reference_answer"):
                problems.append(f"{qid}: refusal 的 reference_answer 必须为空")
            if row.get("difficulty") != "refusal":
                problems.append(f"{qid}: refusal 的 difficulty 必须是 refusal")
            continue
        if kind not in {"answerable", "cross_kb"}:
            problems.append(f"{qid}: 未知 kind={kind}")
            continue
        if not sources:
            problems.append(f"{qid}: {kind} 必须有 expected_sources")
        for name in sources:
            if name not in files:
                problems.append(f"{qid}: 源文件不存在 evals/corpus/{domain}/{name}")
        terms = row.get("terms")
        if not isinstance(terms, list) or not terms:
            problems.append(f"{qid}: terms 必须是非空列表")
            continue
        blob = " ".join(contents.get(name, "") for name in sources)
        for term in terms:
            if not str(term).strip():
                problems.append(f"{qid}: terms 含空字符串")
            elif normalize(str(term)) not in blob:
                problems.append(f"{qid}: terms 片段未在源文件中逐字出现 -> {term!r}")
        if not str(row.get("reference_answer", "")).strip():
            problems.append(f"{qid}: {kind} 的 reference_answer 不能为空")
        if kind == "cross_kb":
            ask_kb = row.get("ask_kb")
            if ask_kb not in {"it", "hr", "product"}:
                problems.append(f"{qid}: cross_kb 需要合法的 ask_kb")
            elif ask_kb != domain:
                neighbours = asking_kb_neighbours(ask_kb, sources)
                if neighbours and not str(row.get("overlap_note", "")).strip():
                    problems.append(
                        f"{qid}: 提问库 {ask_kb} 存在与答案同主题的文档，拒答不是唯一正确答案；"
                        f"请改问一个该库确实没有的主题、把它改成 answerable 题，"
                        f"或用 overlap_note 字段说明为何该交叉重叠不影响评测。命中：{neighbours[:2]}"
                    )
        overlap = longest_common_substring(
            normalize(str(row.get("question", ""))),
            normalize(" ".join(contents.get(name, "") for name in sources)),
        )
        if overlap > MAX_QUESTION_OVERLAP:
            problems.append(
                f"{qid}: 提问与源文最长公共子串 {overlap} 字符（上限 {MAX_QUESTION_OVERLAP}），"
                "疑似直接复述原文，请换词改写"
            )
    return problems


def difficulty_marker_stats(domain: str) -> dict:
    """统计难度埋点是否真实存在于语料中（防止只在 facts 里声称）。"""
    paths = corpus_files(domain)
    texts = {p.name: p.read_text(encoding="utf-8") for p in paths if p.suffix.lower() in corpus.TEXT_SUFFIXES}
    deprecated = [n for n, t in texts.items() if "废止" in t or "不再支持" in t or "废弃" in t]
    numbers = [n for n, t in texts.items() if sum(c.isdigit() for c in t) >= 20]
    tables = [n for n, t in texts.items() if "|" in t and "---" in t]
    return {
        "files": len(paths),
        "text_files": len(texts),
        "pdf_files": sum(1 for p in paths if p.suffix.lower() in corpus.PDF_SUFFIXES),
        "chars": sum(len(t) for t in texts.values()),
        "deprecated_files": sorted(deprecated),
        "number_dense_files": sorted(numbers),
        "table_files": sorted(tables),
    }


def assign_split(rows: list[dict]) -> dict[str, str]:
    """按 (kind, difficulty) 分组后按 golden ratio 分桶，确保 dev/test 难度分布接近。"""
    split: dict[str, str] = {}
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        groups.setdefault((row["kind"], row.get("difficulty")), []).append(row)
    for (kind, _difficulty), items in groups.items():
        ordered = sorted(items, key=lambda r: r["id"])
        for index, row in enumerate(ordered):
            if kind == "refusal":
                # 拒答能力是最终汇报重点，全部进 test，避免被 dev 调参"优化掉"。
                split[row["id"]] = "test"
            else:
                split[row["id"]] = "dev" if (index * DEV_BUCKET) % 1 < DEV_BUCKET else "test"
    return split


def main() -> int:
    all_rows: list[dict] = []
    problems: list[str] = []
    stats: dict[str, dict] = {}
    for domain in DOMAINS:
        facts_path = FACTS / f"{domain}.jsonl"
        if not facts_path.exists():
            problems.append(f"{domain}: 缺少 facts 文件 {facts_path.relative_to(ROOT)}")
            continue
        try:
            rows = read_jsonl(facts_path)
        except ValidationError as exc:
            problems.append(str(exc))
            continue
        problems.extend(validate_domain(domain, rows))
        stats[domain] = difficulty_marker_stats(domain)
        all_rows.extend(rows)
    if problems:
        print(f"校验失败，共 {len(problems)} 处问题：", file=sys.stderr)
        for item in problems[:80]:
            print("  -", item, file=sys.stderr)
        return 1

    split_map = assign_split(all_rows)
    questions = []
    for row in sorted(all_rows, key=lambda r: r["id"]):
        kind = row["kind"]
        entry = {
            "id": row["id"],
            "kind": "answerable" if kind in {"answerable", "cross_kb"} else "refusal",
            "question": row["question"],
            "expected_sources": [] if kind == "cross_kb" else row["expected_sources"],
            "reference_answer": row["reference_answer"],
            "keywords": row["keywords"],
            "terms": row.get("terms", []),
            "difficulty": row["difficulty"],
            "split": split_map[row["id"]],
            "domain": row.get("source_kb") or row["id"].split("-")[0].lower().replace("pd", "product"),
            "generation": row.get("generation", "synthetic_corpus"),
        }
        if kind == "cross_kb":
            entry["isolation"] = {
                "answer_in": row["source_kb"],
                "ask_in": row["ask_kb"],
                "reason": "跨库提问，答案只存在于 source_kb，期望拒答",
            }
            entry["expected_sources_in_source_kb"] = row["expected_sources"]
            # 评估时必须把问题投到 ask_domain，否则检验不到知识库过滤
            entry["ask_domain"] = row["ask_kb"]
            neighbours = asking_kb_neighbours(row["ask_kb"], row["expected_sources"])
            if neighbours:
                # 提问库里存在同主题文档（文件名为证据），该题只作为"隔离题"参考，统计上单独说明
                entry["neighbour_overlap"] = {
                    "neighbours": neighbours[:5],
                    "note": row.get("overlap_note", ""),
                }
        questions.append(entry)

    questions_path = EVALS / "questions.json"
    questions_path.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    corpus_hashes = {
        corpus.relative_key(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in corpus.all_corpus_files()
    }
    counts = Counter((q["domain"], q["kind"]) for q in questions)
    difficulties = Counter(q["difficulty"] for q in questions)
    splits = Counter(q["split"] for q in questions)
    manifest = {
        "dataset": "knowops-synthetic-enterprise-v1",
        "company": "星桥科技（虚构）",
        "disclaimer": "全部语料为合成内容，不对应任何真实企业制度、产品或人员；不得作为真实企业准确率依据。",
        "knowledge_bases": {
            "it": "IT 支持（40 份）",
            "hr": "人事制度（40 份）",
            "product": "产品与客服（40 份）",
        },
        "corpus": {
            "files": len(corpus_hashes),
            "text_files": sum(item["text_files"] for item in stats.values()),
            "pdf_files": sum(item["pdf_files"] for item in stats.values()),
            "chars": sum(item["chars"] for item in stats.values()),
            "sha256": corpus_hashes,
            "per_domain": stats,
        },
        "questions": {
            "total": len(questions),
            "by_domain_kind": {f"{d}/{k}": v for (d, k), v in sorted(counts.items())},
            "by_difficulty": dict(sorted(difficulties.items())),
            "by_split": dict(sorted(splits.items())),
            "sha256": hashlib.sha256(questions_path.read_bytes()).hexdigest(),
        },
        "generation": {"method": "template+human-written synthetic corpus", "seeded": True},
    }
    (EVALS / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"校验通过：{len(questions)} 题（含跨库隔离 18），{len(corpus_hashes)} 份语料")
    print("kind 分布：", dict(Counter(q["kind"] for q in questions)))
    print("难度分布：", dict(sorted(difficulties.items())))
    print("dev/test：", dict(splits))
    for domain in DOMAINS:
        item = stats[domain]
        print(
            f"  {domain}: {item['files']} 份（文本 {item['text_files']} / PDF {item['pdf_files']}）"
            f" / {item['chars']} 字符 / 废止类 {len(item['deprecated_files'])}"
            f" / 数字密集 {len(item['number_dense_files'])} / 表格 {len(item['table_files'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
