#!/usr/bin/env python
"""IT 知识库 facts 自检脚本（task-5 专用）。

校验 evals/facts/it.jsonl（56 行：answerable 34 / refusal 16 / cross_kb 6）
与 evals/corpus/it/ 下 40 份语料的对应关系。

硬约束：
  * expected_sources 中的文件名必须真实存在于 evals/corpus/it/
  * terms 中每个片段必须逐字出现在对应源文件正文中（按 Markdown 原文比对）
  * multi_source / cross_kb 允许多源：每个源文件至少命中 1 个片段，
    且所有片段必须能在这些源文件的并集中逐字命中
  * terms 不得包含 Markdown 标记或项目符号等格式字符

用法：
  /opt/anaconda3/envs/knowops/bin/python evals/facts/check_it.py
退出码 0 表示全部通过，1 表示存在硬约束失败。
"""
from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.join(os.path.dirname(HERE), "corpus", "it")
FACTS_PATH = os.path.join(HERE, "it.jsonl")

EXPECTED_TOTAL_LINES = 56
EXPECTED_KIND_COUNTS = {"answerable": 34, "refusal": 16, "cross_kb": 6}
EXPECTED_ANSWERABLE_DIFFICULTY = {
    "easy": 8,
    "paraphrase": 10,
    "numeric": 10,
    "multi_source": 6,
}
ANSWERABLE_DIFFICULTIES = set(EXPECTED_ANSWERABLE_DIFFICULTY)
CORPUS_MIN_CHARS = 1200
CORPUS_TARGET_MIN = 1500
CORPUS_MAX_CHARS = 4000
CROSS_KB_EXPECTED = {"hr": 3, "product": 3}
TERM_FORBIDDEN = ["**", "|", "`", "##", "\n", "\r", "\t", "•", "\u00a0", "- "]
REQUIRED_KEYS = [
    "id",
    "kind",
    "question",
    "expected_sources",
    "reference_answer",
    "keywords",
    "terms",
    "difficulty",
    "generation",
]

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def load_corpus() -> dict[str, str]:
    docs: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(CORPUS_DIR, "*.md"))):
        with open(path, encoding="utf-8") as fh:
            docs[os.path.basename(path)] = fh.read()
    return docs


def longest_common_substring(a: str, b: str) -> int:
    """最长公共子串长度，用于提示 question 与原文过度重合。"""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def check_terms_against_sources(row: dict, docs: dict[str, str]) -> None:
    rid = row.get("id", "<no-id>")
    sources = row["expected_sources"]
    terms = row["terms"]

    for name in sources:
        if name not in docs:
            err(f"{rid}: expected_sources 中的文件不存在于 evals/corpus/it/ -> {name}")
    valid_sources = [n for n in sources if n in docs]
    if not valid_sources:
        return

    for term in terms:
        if not isinstance(term, str) or not term.strip():
            err(f"{rid}: terms 中存在空片段")
            continue
        for bad in TERM_FORBIDDEN:
            if bad in term:
                err(f"{rid}: terms 片段含格式字符 {bad!r} -> {term!r}")
        if not any(term in docs[n] for n in valid_sources):
            err(f"{rid}: terms 片段未在任一 expected_sources 中逐字命中 -> {term!r}")

    if len(valid_sources) > 1:
        for name in valid_sources:
            if not any(term in docs[name] for term in terms):
                err(
                    f"{rid}: multi_source 要求每个源文件至少命中 1 个片段，"
                    f"但 {name} 未命中任何片段"
                )


def main() -> int:
    docs = load_corpus()

    # ---------- 语料统计 ----------
    file_count = len(docs)
    lengths = {name: len(text) for name, text in docs.items()}
    total_chars = sum(lengths.values())
    if file_count != 40:
        err(f"语料文件数应为 40，实际 {file_count}")

    # ---------- 文件级检查 ----------
    with open(FACTS_PATH, "rb") as fh:
        raw = fh.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        err("it.jsonl 含 UTF-8 BOM，需为无 BOM 的 UTF-8")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover
        err(f"it.jsonl 不是合法 UTF-8：{exc}")
        text = raw.decode("utf-8", errors="replace")

    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if len(lines) != EXPECTED_TOTAL_LINES:
        err(f"it.jsonl 应为 {EXPECTED_TOTAL_LINES} 行，实际 {len(lines)}")

    # ---------- 逐行解析与校验 ----------
    rows: list[dict] = []
    kind_counts: dict[str, int] = {}
    difficulty_counts: dict[str, int] = {}
    ask_kb_counts: dict[str, int] = {}
    seen_ids: set[str] = set()
    seen_questions: dict[str, str] = {}

    for idx, line in enumerate(lines, start=1):
        expected_id = f"IT-{idx:02d}"
        if line.strip() == "":
            err(f"第 {idx} 行为空行")
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            err(f"第 {idx} 行不是合法 JSON：{exc}")
            continue
        if not isinstance(row, dict):
            err(f"第 {idx} 行不是 JSON 对象")
            continue
        rows.append(row)

        rid = row.get("id", f"<第 {idx} 行无 id>")
        if row.get("id") != expected_id:
            err(f"第 {idx} 行 id 应为 {expected_id}，实际 {row.get('id')!r}")
        if row.get("id") in seen_ids:
            err(f"{rid}: id 重复")
        seen_ids.add(row.get("id"))

        for key in REQUIRED_KEYS:
            if key not in row:
                err(f"{rid}: 缺少字段 {key}")

        kind = row.get("kind")
        if kind not in EXPECTED_KIND_COUNTS:
            err(f"{rid}: kind 非法 -> {kind!r}")
            continue
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

        if row.get("generation") != "synthetic_corpus":
            err(f"{rid}: generation 应为 synthetic_corpus")

        question = row.get("question", "")
        if not isinstance(question, str) or not question.strip():
            err(f"{rid}: question 为空")
        elif question in seen_questions:
            warn(f"{rid}: question 与 {seen_questions[question]} 完全重复")
        else:
            seen_questions[question] = rid

        difficulty = row.get("difficulty")
        difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

        if kind == "refusal":
            if row.get("expected_sources") != []:
                err(f"{rid}: refusal 行 expected_sources 必须为 []")
            if row.get("reference_answer") != "":
                err(f"{rid}: refusal 行 reference_answer 必须为空字符串")
            if row.get("keywords") != []:
                err(f"{rid}: refusal 行 keywords 必须为 []")
            if difficulty != "refusal":
                err(f"{rid}: refusal 行 difficulty 必须为 refusal")
            if row.get("terms") != []:
                warn(f"{rid}: refusal 行 terms 建议为 []（当前非空）")
            continue

        # answerable / cross_kb 共有约束
        if difficulty not in ANSWERABLE_DIFFICULTIES and kind == "answerable":
            err(f"{rid}: answerable 行 difficulty 非法 -> {difficulty!r}")
        if kind == "answerable" and difficulty == "multi_source" and len(row.get("expected_sources", [])) != 2:
            err(f"{rid}: multi_source 行必须给出 2 个 expected_sources")
        if (
            kind == "answerable"
            and difficulty != "multi_source"
            and len(row.get("expected_sources", [])) != 1
        ):
            err(f"{rid}: 非 multi_source 的 answerable 行应给出 1 个 expected_sources")
        if not row.get("expected_sources"):
            err(f"{rid}: expected_sources 不得为空")
        if not row.get("terms"):
            err(f"{rid}: terms 不得为空")
        if not str(row.get("reference_answer", "")).strip():
            err(f"{rid}: reference_answer 不得为空")
        if not row.get("keywords"):
            err(f"{rid}: keywords 不得为空")
        if not str(question).rstrip().endswith(("？", "?")):
            warn(f"{rid}: question 建议以问号结尾")

        if kind == "cross_kb":
            if difficulty != "cross_kb":
                err(f"{rid}: cross_kb 行 difficulty 必须为 cross_kb")
            if row.get("source_kb") != "it":
                err(f"{rid}: cross_kb 行 source_kb 必须为 it")
            ask_kb = row.get("ask_kb")
            if ask_kb not in CROSS_KB_EXPECTED:
                err(f"{rid}: cross_kb 行 ask_kb 必须为 hr 或 product，实际 {ask_kb!r}")
            else:
                ask_kb_counts[ask_kb] = ask_kb_counts.get(ask_kb, 0) + 1
            if "答案只存在于 IT 知识库" not in str(row.get("notes", "")):
                warn(f"{rid}: cross_kb 行 notes 建议说明跨库应拒答")

        check_terms_against_sources(row, docs)

        # paraphrase 类题目与原文重合度提示
        if difficulty == "paraphrase":
            worst = 0
            for name in row["expected_sources"]:
                if name in docs:
                    worst = max(worst, longest_common_substring(question, docs[name]))
            if worst >= 12:
                warn(f"{rid}: paraphrase 题与原文最长公共子串 {worst} 字符，建议改写提问")

    # ---------- 结构与分布 ----------
    for kind, expected in EXPECTED_KIND_COUNTS.items():
        actual = kind_counts.get(kind, 0)
        if actual != expected:
            err(f"kind={kind} 数量应为 {expected}，实际 {actual}")
    for diff, expected in EXPECTED_ANSWERABLE_DIFFICULTY.items():
        actual = difficulty_counts.get(diff, 0)
        if actual != expected:
            err(f"difficulty={diff} 数量应为 {expected}，实际 {actual}")
    for kb, expected in CROSS_KB_EXPECTED.items():
        actual = ask_kb_counts.get(kb, 0)
        if actual != expected:
            err(f"cross_kb ask_kb={kb} 数量应为 {expected}，实际 {actual}")

    # ---------- 报告 ----------
    print("=" * 68)
    print("IT 知识库 facts 自检报告（evals/facts/it.jsonl）")
    print("=" * 68)
    print(f"facts 文件            : {os.path.relpath(FACTS_PATH)}")
    print(f"语料目录              : {os.path.relpath(CORPUS_DIR, os.path.dirname(HERE))}")
    print(f"facts 行数            : {len(lines)}（期望 {EXPECTED_TOTAL_LINES}）")
    print(f"kind 计数             : {dict(sorted(kind_counts.items()))}")
    print(f"difficulty 计数       : {dict(sorted(difficulty_counts.items(), key=lambda kv: str(kv[0])))}")
    print(f"cross_kb ask_kb 计数  : {dict(sorted(ask_kb_counts.items()))}")
    print("-" * 68)
    print(f"语料文件数            : {file_count}（期望 40）")
    print(f"语料总字符数          : {total_chars}")
    if lengths:
        s_name = min(lengths, key=lengths.get)
        l_name = max(lengths, key=lengths.get)
        print(f"最短文档              : {lengths[s_name]} 字符  {s_name}")
        print(f"最长文档              : {lengths[l_name]} 字符  {l_name}")
        under = {n: c for n, c in lengths.items() if c < CORPUS_TARGET_MIN}
        over = {n: c for n, c in lengths.items() if c > CORPUS_MAX_CHARS}
        if under:
            warn(f"有 {len(under)} 份文档低于 1500 字符下限：{under}")
        if over:
            warn(f"有 {len(over)} 份文档超过 4000 字符上限：{over}")
        below_hard = {n: c for n, c in lengths.items() if c < CORPUS_MIN_CHARS}
        if below_hard:
            err(f"有文档低于 1200 字符硬下限：{below_hard}")
    print("-" * 68)
    for msg in warnings:
        print(f"[WARN] {msg}")
    for msg in errors:
        print(f"[FAIL] {msg}")
    if errors:
        print(f"\n结果：失败（{len(errors)} 项硬约束）")
        return 1
    print(f"\n结果：全部通过（{len(rows)} 行 facts，{file_count} 份语料）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
