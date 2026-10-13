#!/usr/bin/env python
"""HR 事实标注自检脚本（task-6 D2-HR）。

用法：
    /opt/anaconda3/envs/knowops/bin/python evals/facts/check_hr.py

校验内容：
1. JSONL 合法、无 BOM、恰好 56 行、id 唯一且为 HR-01..HR-56。
2. kind 数量：answerable 34 / refusal 16 / cross_kb 6。
3. answerable 难度分布：easy 8 / paraphrase 10 / numeric 10 / multi_source 6。
4. answerable 与 cross_kb：
   - expected_sources 非空，且每个文件名真实存在于 evals/corpus/hr/。
   - terms 非空，且每个片段逐字出现在至少一个 expected_sources 文件正文中。
   - terms 不含 Markdown 标记字符（|、#、*、`、[、]）。
   - reference_answer / keywords 非空。
   - question 不得与源文件原文高度重合（最长公共子串 < 15）。
5. refusal：expected_sources=[]、reference_answer=""、keywords=[]、difficulty="refusal"。
6. cross_kb：source_kb="hr"，ask_kb 属于 {it, product} 且各 3 条。
7. 语料统计：文件数、总字符数、最短/最长文件。

退出码：全部通过为 0，否则为 1。
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]  # outputs/knowops
CORPUS_DIR = BASE / "evals" / "corpus" / "hr"
FACTS_FILE = BASE / "evals" / "facts" / "hr.jsonl"

EXPECTED_ROWS = 56
EXPECTED_IDS = [f"HR-{i:02d}" for i in range(1, EXPECTED_ROWS + 1)]
EXPECTED_KINDS = {"answerable": 34, "refusal": 16, "cross_kb": 6}
EXPECTED_ANSWERABLE_DIFF = {
    "easy": 8,
    "paraphrase": 10,
    "numeric": 10,
    "multi_source": 6,
}
MARKDOWN_CHARS = set("|#*`[]<>")
QUESTION_OVERLAP_LIMIT = 15

errors: list[str] = []
warnings: list[str] = []


def err(line_no: int | None, msg: str) -> None:
    prefix = f"[行 {line_no}] " if line_no is not None else "[全局] "
    errors.append(prefix + msg)


def longest_common_substring_len(a: str, b: str) -> int:
    """返回两段文本的最长公共子串长度（用于判断提问是否与原文高度重合）。"""
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


def main() -> int:
    # ---------- 语料统计 ----------
    corpus_files = sorted(p for p in CORPUS_DIR.glob("*.md") if p.is_file())
    corpus_text = {
        p.name: p.read_text(encoding="utf-8") for p in corpus_files
    }
    lengths = {name: len(text) for name, text in corpus_text.items()}
    print("=" * 72)
    print("【一、语料统计】")
    print(f"文档数量：{len(corpus_files)}   期望 40")
    if len(corpus_files) != 40:
        err(None, f"语料文件数应为 40，实际 {len(corpus_files)}")
    if lengths:
        total = sum(lengths.values())
        shortest = min(lengths.items(), key=lambda kv: kv[1])
        longest = max(lengths.items(), key=lambda kv: kv[1])
        print(f"总字符数：{total}")
        print(f"最短文档：{shortest[1]} 字符  {shortest[0]}")
        print(f"最长文档：{longest[1]} 字符  {longest[0]}")
        under = [(n, c) for n, c in sorted(lengths.items()) if c < 1500]
        if under:
            err(None, f"存在少于 1500 字符的文档：{under}")
        over = [(n, c) for n, c in sorted(lengths.items()) if c > 4000]
        if over:
            err(None, f"存在超过 4000 字符的文档：{over}")
    else:
        err(None, "语料目录为空")
    print()

    # ---------- 读取 JSONL ----------
    raw = FACTS_FILE.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        err(None, "hr.jsonl 含 UTF-8 BOM，必须去掉")
    text = raw.decode("utf-8")
    raw_lines = text.split("\n")
    # 允许文件末尾有一个换行
    lines = [ln for i, ln in enumerate(raw_lines) if not (i == len(raw_lines) - 1 and ln == "")]
    empty_inside = [i + 1 for i, ln in enumerate(lines) if not ln.strip()]

    print("=" * 72)
    print("【二、JSONL 结构】")
    print(f"总行数：{len(lines)}   期望 {EXPECTED_ROWS}")
    if len(lines) != EXPECTED_ROWS:
        err(None, f"行数应为 {EXPECTED_ROWS}，实际 {len(lines)}")
    if empty_inside:
        err(None, f"存在空行：{empty_inside}")

    records: list[dict] = []
    for idx, ln in enumerate(lines, start=1):
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError as exc:
            err(idx, f"JSON 解析失败：{exc}")
            continue
        if not isinstance(obj, dict):
            err(idx, "每行必须是一个 JSON 对象")
            continue
        obj["__line__"] = idx
        records.append(obj)

    ids = [r.get("id") for r in records]
    dup = [i for i, c in Counter(ids).items() if c > 1]
    if dup:
        err(None, f"id 重复：{dup}")
    if ids != EXPECTED_IDS:
        err(None, f"id 必须为 HR-01..HR-{EXPECTED_ROWS:02d} 且顺序连续；实际：{ids}")

    kind_counter = Counter(r.get("kind") for r in records)
    print(f"kind 分布：{dict(kind_counter)}   期望 {EXPECTED_KINDS}")
    if dict(kind_counter) != EXPECTED_KINDS:
        err(None, f"kind 数量不符合期望：{dict(kind_counter)}")
    print()

    # ---------- 逐行字段校验 ----------
    print("=" * 72)
    print("【三、逐行字段校验】")
    answerable_diff: Counter = Counter()
    ask_kb_counter: Counter = Counter()
    checked_terms = 0
    checked_sources = 0

    for rec in records:
        line_no = rec["__line__"]
        rid = rec.get("id")
        kind = rec.get("kind")
        question = rec.get("question") or ""
        sources = rec.get("expected_sources")
        answer = rec.get("reference_answer")
        keywords = rec.get("keywords")
        terms = rec.get("terms")
        difficulty = rec.get("difficulty")

        base_fields = ["id", "kind", "question", "expected_sources",
                       "reference_answer", "keywords", "terms", "difficulty",
                       "generation"]
        for f in base_fields:
            if f not in rec:
                err(line_no, f"{rid} 缺少字段 {f}")
        if rec.get("generation") != "synthetic_corpus":
            err(line_no, f"{rid} generation 必须为 synthetic_corpus")
        if not isinstance(question, str) or not question.strip():
            err(line_no, f"{rid} question 不能为空")

        if kind == "refusal":
            if sources != []:
                err(line_no, f"{rid} refusal 的 expected_sources 必须为 []")
            if answer != "":
                err(line_no, f"{rid} refusal 的 reference_answer 必须为空字符串")
            if keywords != []:
                err(line_no, f"{rid} refusal 的 keywords 必须为 []")
            if terms != []:
                err(line_no, f"{rid} refusal 的 terms 必须为 []")
            if difficulty != "refusal":
                err(line_no, f"{rid} refusal 的 difficulty 必须为 refusal")
            continue

        if kind not in ("answerable", "cross_kb"):
            err(line_no, f"{rid} 未知 kind：{kind}")
            continue

        # --- answerable / cross_kb 硬约束 ---
        if not isinstance(sources, list) or not sources:
            err(line_no, f"{rid} expected_sources 必须为非空列表")
            continue
        if not isinstance(terms, list) or not terms:
            err(line_no, f"{rid} terms 必须为非空列表")
        if not isinstance(answer, str) or not answer.strip():
            err(line_no, f"{rid} reference_answer 不能为空")
        if not isinstance(keywords, list) or not keywords:
            err(line_no, f"{rid} keywords 不能为空")

        if kind == "answerable":
            answerable_diff[difficulty] += 1
            if difficulty not in EXPECTED_ANSWERABLE_DIFF:
                err(line_no, f"{rid} 非法 difficulty：{difficulty}")
            if difficulty == "multi_source" and len(sources) != 2:
                err(line_no, f"{rid} multi_source 必须指定 2 个 expected_sources，实际 {len(sources)}")
            if difficulty != "multi_source" and len(sources) != 1:
                warnings.append(f"[行 {line_no}] {rid} 非 multi_source 却给出 {len(sources)} 个来源")

        if kind == "cross_kb":
            if difficulty != "cross_kb":
                err(line_no, f"{rid} cross_kb 的 difficulty 必须为 cross_kb")
            if rec.get("source_kb") != "hr":
                err(line_no, f"{rid} cross_kb 的 source_kb 必须为 hr")
            ask_kb = rec.get("ask_kb")
            ask_kb_counter[ask_kb] += 1
            if ask_kb not in ("it", "product"):
                err(line_no, f"{rid} cross_kb 的 ask_kb 必须为 it 或 product，实际 {ask_kb!r}")

        # 源文件存在性 + terms 逐字命中 + 提问重合度
        source_texts = []
        for name in sources:
            checked_sources += 1
            if not isinstance(name, str) or not name.endswith(".md"):
                err(line_no, f"{rid} 非法文件名：{name!r}")
                continue
            if name not in corpus_text:
                err(line_no, f"{rid} expected_sources 中的文件不存在：{name}")
                continue
            source_texts.append(corpus_text[name])

        for term in (terms or []):
            if not isinstance(term, str) or not term:
                err(line_no, f"{rid} term 必须为非空字符串")
                continue
            bad = sorted(set(term) & MARKDOWN_CHARS)
            if bad:
                err(line_no, f"{rid} term 含 Markdown 标记字符 {bad}：{term!r}")
            checked_terms += 1
            if source_texts and not any(term in st for st in source_texts):
                err(line_no, f"{rid} term 未在 expected_sources 中逐字命中：{term!r}")

        for st in source_texts:
            overlap = longest_common_substring_len(question, st)
            if overlap >= QUESTION_OVERLAP_LIMIT:
                err(line_no, f"{rid} question 与源文件原文重合 {overlap} 字（阈值 <{QUESTION_OVERLAP_LIMIT}），需换词")

    print(f"校验的 sources 引用数：{checked_sources}")
    print(f"校验的 terms 片段数：{checked_terms}")
    print(f"answerable 难度分布：{dict(answerable_diff)}   期望 {EXPECTED_ANSWERABLE_DIFF}")
    if dict(answerable_diff) != EXPECTED_ANSWERABLE_DIFF:
        err(None, f"answerable 难度分布不符合期望：{dict(answerable_diff)}")
    print(f"cross_kb ask_kb 分布：{dict(ask_kb_counter)}   期望 it 3 / product 3")
    if ask_kb_counter.get("it") != 3 or ask_kb_counter.get("product") != 3:
        err(None, f"cross_kb 的 ask_kb 必须 it 3 条、product 3 条；实际 {dict(ask_kb_counter)}")
    print()

    # ---------- 结果 ----------
    print("=" * 72)
    if warnings:
        print("【警告】")
        for w in warnings:
            print("  ! " + w)
        print()
    if errors:
        print(f"【校验失败】共 {len(errors)} 项问题：")
        for e in errors:
            print("  - " + e)
        print()
        print("结果：FAIL")
        return 1

    print("【校验通过】")
    print(f"  - 语料：{len(corpus_files)} 份，总 {sum(lengths.values())} 字符，最短 {min(lengths.values())} 字符")
    print(f"  - facts：{len(records)} 行（answerable 34 / refusal 16 / cross_kb 6）")
    print(f"  - id：HR-01..HR-{EXPECTED_ROWS:02d} 唯一且连续，无 BOM")
    print(f"  - sources 引用：{checked_sources} 个全部存在")
    print(f"  - terms：{checked_terms} 个片段全部逐字命中，且无 Markdown 标记")
    print(f"  - 难度：{dict(answerable_diff)}")
    print("  - cross_kb：it 3 / product 3，source_kb 均为 hr")
    print()
    print("结果：PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
