#!/usr/bin/env python
"""KnowOps 产品/客服知识库 事实标注自检脚本（task-7）。

只校验 evals/facts/product.jsonl 与 evals/corpus/product/，不写任何文件。

校验项：
  1. JSONL 逐行合法、UTF-8 无 BOM、正好 56 行。
  2. id 唯一且连续（PD-01..PD-56）。
  3. kind 数量：answerable 34 / refusal 16 / cross_kb 6。
  4. answerable 难度分布：easy 8 / paraphrase 10 / numeric 10 / multi_source 6。
  5. expected_sources 文件名真实存在于 evals/corpus/product/。
  6. terms 每个片段逐字出现在对应源文件正文中（纯子串匹配）。
  7. refusal 行字段约束；cross_kb 行字段约束（source_kb / ask_kb 各 3 条）。
  8. 数字/错误码题的 terms 必须包含数字。
  9. question 不得与源文档整句高度重合。
 10. 语料统计：文件数、总字符数、最短/最长、区间占比。

用法：/opt/anaconda3/envs/knowops/bin/python evals/facts/check_product.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = ROOT / "evals" / "corpus" / "product"
FACTS_FILE = ROOT / "evals" / "facts" / "product.jsonl"

TOTAL_ROWS = 56
EXPECTED_KIND = {"answerable": 34, "refusal": 16, "cross_kb": 6}
EXPECTED_DIFF = {"easy": 8, "paraphrase": 10, "numeric": 10, "multi_source": 6}
CORPUS_FILES = 40
CORPUS_MIN_CHARS = 1200
CORPUS_MAX_CHARS = 4000
ALLOWED_ASK_KB = {"it", "hr"}

REQUIRED_FIELDS = [
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
DIGIT_RE = re.compile(r"[0-9]")
# 错误码形态：全大写 + 下划线（如 ROOM_LICENSE_EXHAUSTED / GATEWAY_RATE_LIMITED）
CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")


class Check:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def load_corpus(check: Check) -> dict[str, str]:
    if not CORPUS_DIR.is_dir():
        check.err(f"语料目录不存在：{CORPUS_DIR}")
        return {}
    files = sorted(p for p in CORPUS_DIR.glob("*.md") if p.is_file())
    docs: dict[str, str] = {}
    for p in files:
        raw = p.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            check.err(f"[语料] 存在 BOM：{p.name}")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            check.err(f"[语料] 非 UTF-8：{p.name}（{exc}）")
            continue
        docs[p.name] = text
        n = len(text)
        if not (CORPUS_MIN_CHARS <= n <= CORPUS_MAX_CHARS):
            check.err(
                f"[语料] {p.name} 字符数 {n} 超出 {CORPUS_MIN_CHARS}-{CORPUS_MAX_CHARS}"
            )
    if len(files) != CORPUS_FILES:
        check.err(f"[语料] 文件数 {len(files)} != {CORPUS_FILES}")
    return docs


def load_rows(check: Check) -> list[dict]:
    if not FACTS_FILE.is_file():
        check.err(f"facts 文件不存在：{FACTS_FILE}")
        return []
    raw = FACTS_FILE.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        check.err("[facts] 文件含 BOM，应为无 BOM 的 UTF-8")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        check.err(f"[facts] 非 UTF-8：{exc}")
        return []

    lines = text.splitlines()
    if text and not text.endswith("\n"):
        check.warn("[facts] 文件末尾没有换行符")
    rows: list[dict] = []
    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            check.err(f"[facts] 第 {idx} 行为空行")
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            check.err(f"[facts] 第 {idx} 行不是合法 JSON：{exc}")
            continue
        if not isinstance(obj, dict):
            check.err(f"[facts] 第 {idx} 行不是 JSON 对象")
            continue
        rows.append(obj)
    if len(rows) != TOTAL_ROWS:
        check.err(f"[facts] 行数 {len(rows)} != {TOTAL_ROWS}")
    return rows


def question_overlaps_source(question: str, text: str) -> str | None:
    """若问题整句照搬源文档，返回命中的那一行。"""
    q = question.strip()
    if len(q) < 10:
        return None
    for line in text.splitlines():
        s = line.strip().strip("#").strip()
        if len(s) < 10:
            continue
        if q == s or (len(q) >= 14 and q in s):
            return s
    return None


def main() -> int:
    check = Check()
    docs = load_corpus(check)
    rows = load_rows(check)

    seen_ids: list[str] = []
    kinds: Counter[str] = Counter()
    diffs: Counter[str] = Counter()
    ask_kbs: Counter[str] = Counter()

    for i, row in enumerate(rows, start=1):
        tag = f"第 {i} 行（{row.get('id', '?')}）"

        for field in REQUIRED_FIELDS:
            if field not in row:
                check.err(f"[{tag}] 缺少必填字段 {field}")

        rid = row.get("id", "")
        if not isinstance(rid, str) or not re.fullmatch(r"PD-\d{2}", rid):
            check.err(f"[{tag}] id 格式非法：{rid!r}")
        else:
            seen_ids.append(rid)

        kind = row.get("kind")
        if kind not in EXPECTED_KIND:
            check.err(f"[{tag}] kind 非法：{kind!r}")
            continue
        kinds[kind] += 1

        if row.get("generation") != "synthetic_corpus":
            check.err(f"[{tag}] generation 应为 synthetic_corpus")

        question = row.get("question", "")
        sources = row.get("expected_sources", [])
        terms = row.get("terms", [])
        difficulty = row.get("difficulty")

        if not isinstance(question, str) or len(question.strip()) < 8:
            check.err(f"[{tag}] question 过短或非字符串")

        if not isinstance(sources, list):
            check.err(f"[{tag}] expected_sources 必须是数组")
            sources = []
        if not isinstance(terms, list):
            check.err(f"[{tag}] terms 必须是数组")
            terms = []

        # ---- 按 kind 校验 ----
        if kind == "answerable":
            diffs[difficulty] += 1
            if difficulty not in EXPECTED_DIFF:
                check.err(f"[{tag}] answerable 的 difficulty 非法：{difficulty!r}")
            if not sources:
                check.err(f"[{tag}] answerable 必须至少有 1 个 expected_sources")
            if not terms:
                check.err(f"[{tag}] answerable 的 terms 不能为空")
            if not row.get("reference_answer"):
                check.err(f"[{tag}] answerable 的 reference_answer 不能为空")
            if not row.get("keywords"):
                check.err(f"[{tag}] answerable 的 keywords 不能为空")
            if difficulty == "multi_source" and len(sources) != 2:
                check.err(
                    f"[{tag}] multi_source 必须正好 2 个 expected_sources，实际 {len(sources)}"
                )
            if difficulty in {"numeric", "multi_source"} and not any(
                DIGIT_RE.search(t) or CODE_RE.search(t) for t in terms if isinstance(t, str)
            ):
                check.err(f"[{tag}] {difficulty} 题的 terms 必须包含数字或错误码")
            if difficulty in {"easy", "paraphrase"} and len(sources) != 1:
                check.err(
                    f"[{tag}] {difficulty} 题应为 1 个 expected_sources，实际 {len(sources)}"
                )
        elif kind == "refusal":
            diffs[difficulty] += 1
            if difficulty != "refusal":
                check.err(f"[{tag}] refusal 行的 difficulty 必须为 refusal")
            if sources != []:
                check.err(f"[{tag}] refusal 的 expected_sources 必须为 []")
            if row.get("reference_answer") != "":
                check.err(f"[{tag}] refusal 的 reference_answer 必须为空字符串")
            if row.get("keywords") != []:
                check.err(f"[{tag}] refusal 的 keywords 必须为 []")
            if terms != []:
                check.err(f"[{tag}] refusal 的 terms 必须为 []")
        else:  # cross_kb
            diffs[difficulty] += 1
            if difficulty != "cross_kb":
                check.err(f"[{tag}] cross_kb 行的 difficulty 必须为 cross_kb")
            if row.get("source_kb") != "product":
                check.err(f"[{tag}] cross_kb 的 source_kb 必须为 product")
            ask_kb = row.get("ask_kb")
            if ask_kb not in ALLOWED_ASK_KB:
                check.err(f"[{tag}] cross_kb 的 ask_kb 非法：{ask_kb!r}")
            else:
                ask_kbs[ask_kb] += 1
            if not sources:
                check.err(f"[{tag}] cross_kb 必须有真实 expected_sources")
            if not terms:
                check.err(f"[{tag}] cross_kb 的 terms 不能为空")
            if not row.get("reference_answer"):
                check.err(f"[{tag}] cross_kb 的 reference_answer 不能为空")
            if not row.get("keywords"):
                check.err(f"[{tag}] cross_kb 的 keywords 不能为空")
            if "拒答" not in str(row.get("notes", "")):
                check.warn(f"[{tag}] cross_kb 的 notes 未说明应拒答")

        # ---- 源文件存在性与 terms 逐字命中 ----
        resolved: list[tuple[str, str]] = []
        for name in sources:
            if not isinstance(name, str):
                check.err(f"[{tag}] expected_sources 出现非字符串项：{name!r}")
                continue
            if name not in docs:
                check.err(f"[{tag}] expected_sources 文件名不存在：{name}")
                continue
            resolved.append((name, docs[name]))

        for term in terms:
            if not isinstance(term, str) or not term.strip():
                check.err(f"[{tag}] terms 出现空片段")
                continue
            if term != term.strip():
                check.err(f"[{tag}] terms 片段首尾有空白：{term!r}")
            if any(ch in term for ch in "|#*`[]<>\n\t"):
                check.err(f"[{tag}] terms 片段含 Markdown/控制字符：{term!r}")
            if not any(term in text for _, text in resolved):
                where = " / ".join(n for n, _ in resolved) or "<无有效源文件>"
                check.err(f"[{tag}] terms 未逐字命中 {where}：{term!r}")

        # ---- 问题与原文重合度 ----
        for name, text in resolved:
            hit = question_overlaps_source(question, text)
            if hit:
                check.err(f"[{tag}] question 与 {name} 原文高度重合：{hit[:40]}...")
                break

    # ---- 汇总断言 ----
    expected_ids = [f"PD-{i:02d}" for i in range(1, TOTAL_ROWS + 1)]
    if seen_ids != expected_ids:
        if sorted(seen_ids) == sorted(expected_ids):
            check.err("[facts] id 存在但顺序不符合 PD-01..PD-56")
        else:
            missing = sorted(set(expected_ids) - set(seen_ids))
            dup = [k for k, v in Counter(seen_ids).items() if v > 1]
            check.err(f"[facts] id 不连续；缺失={missing} 重复={dup}")

    for kind, want in EXPECTED_KIND.items():
        if kinds[kind] != want:
            check.err(f"[facts] kind={kind} 数量 {kinds[kind]} != {want}")
    for diff, want in EXPECTED_DIFF.items():
        if diffs[diff] != want:
            check.err(f"[facts] difficulty={diff} 数量 {diffs[diff]} != {want}")
    if kinds["answerable"] != sum(diffs[d] for d in EXPECTED_DIFF):
        check.err("[facts] answerable 行数与难度分布之和不一致")
    for kb in ALLOWED_ASK_KB:
        if ask_kbs[kb] != 3:
            check.err(f"[facts] cross_kb 中 ask_kb={kb} 数量 {ask_kbs[kb]} != 3")

    # ---- 语料统计 ----
    sizes = sorted(((len(t), n) for n, t in docs.items()), key=lambda x: x[0])
    print("=" * 68)
    print("语料统计（evals/corpus/product/）")
    print(f"  文件数          : {len(docs)}")
    print(f"  总字符数        : {sum(s for s, _ in sizes)}")
    if sizes:
        print(f"  最短文件        : {sizes[0][0]} 字符  {sizes[0][1]}")
        print(f"  最长文件        : {sizes[-1][0]} 字符  {sizes[-1][1]}")
        print(f"  平均字符数      : {sum(s for s, _ in sizes) / len(sizes):.1f}")
        print(f"  >=2000 字符文件 : {sum(1 for s, _ in sizes if s >= 2000)}/{len(sizes)}")
        print(f"  1200-4000 区间  : {sum(1 for s, _ in sizes if 1200 <= s <= 4000)}/{len(sizes)}")
        print(f"  最短文件名与 2000 差值: {sizes[0][0] - 2000}")
    print("-" * 68)
    print("facts 统计（evals/facts/product.jsonl）")
    print(f"  总行数          : {len(rows)}")
    print(f"  answerable      : {kinds['answerable']}")
    print(f"  refusal         : {kinds['refusal']}")
    print(f"  cross_kb        : {kinds['cross_kb']}")
    print(
        "  难度分布        : "
        + ", ".join(f"{k}={diffs[k]}" for k in (*EXPECTED_DIFF, "refusal", "cross_kb"))
    )
    print(f"  cross_kb ask_kb : it={ask_kbs['it']}, hr={ask_kbs['hr']}")
    print("=" * 68)

    if check.warnings:
        print(f"警告 {len(check.warnings)} 条：")
        for w in check.warnings:
            print(f"  WARN  {w}")

    if check.errors:
        print(f"校验失败：{len(check.errors)} 个错误")
        for e in check.errors:
            print(f"  ERROR {e}")
        return 1

    print("校验通过：语料 40 份、facts 56 行、三种 kind 与难度分布、terms 逐字命中均符合要求。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
