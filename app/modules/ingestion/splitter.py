# 中文导读：
# 按字符切分原文：提供固定窗口与结构感知策略
# 输出保持原文子串，以便引用摘录核验；长度按字符计算，不是模型 token 数

"""Boundary-aware character chunks; all output remains exact source substrings."""

import re
from bisect import bisect_left, bisect_right


# 固定字符窗口：步长为窗口长度减重叠长度，末尾不足一窗时保留原文尾段。
def windows(text, size, overlap):
    for start in range(0, len(text), size - overlap):
        yield text[start : start + size]
        if start + size >= len(text):
            break


# 结构切分优先选择标题、段落、句子和换行边界；找不到合适边界时退回长度上限，保证推进。
def structured(text, size, overlap):
    headings = {m.start() for m in re.finditer(r"(?m)^#{1,6}[ \t]+\S", text)}
    paragraphs = {m.end() for m in re.finditer(r"\n[ \t]*\n", text)}
    sentences = {m.end() for m in re.finditer(r'[。！？!?；;][”’"\']?|\.(?=\s|$)', text)}
    lines = {m.end() for m in re.finditer(r"\n", text)}
    # Small Markdown tables/fences remain whole; oversized blocks fall back to
    # bounded windows. No generated table headers or heading prefixes are added.
    spans = []
    for pattern in (
        r"(?ms)^```[^\n]*\n.*?^```[^\n]*(?:\n|$)",
        r"(?m)^\|[^\n]*\|[^\n]*(?:\n\|[^\n]*\|[^\n]*)+",
    ):
        spans.extend((m.start(), m.end()) for m in re.finditer(pattern, text))
    merged = []
    for a, b in sorted(spans):
        if merged and a < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    protected = [(a, b) for a, b in merged if b - a <= size]
    block_starts = [a for a, _ in protected]
    starts = set(block_starts)
    ends = {b for _, b in protected}

    # 只允许在受保护的短表格或代码块外切分，避免把一个完整结构从中间截断。
    def safe(position):
        i = bisect_right(block_starts, position) - 1
        return i < 0 or not protected[i][0] < position < protected[i][1]

    groups = [
        sorted(p for p in group if safe(p))
        for group in (headings | starts, paragraphs | ends, sentences, lines)
    ]
    boundaries = sorted(set().union(*groups))
    start = 0
    while start < len(text):
        limit = min(start + size, len(text))
        if limit == len(text):
            yield text[start:limit]
            break
        i = bisect_right(block_starts, limit) - 1
        crossing = i >= 0 and start < protected[i][0] < limit < protected[i][1]
        floor = start + max(overlap + 1, size // 3)
        cut = protected[i][0] if crossing else None
        if cut is None:
            for group in groups:
                index = bisect_right(group, limit) - 1
                if index >= 0 and group[index] >= floor:
                    cut = group[index]
                    break
        hard = cut is None
        cut = limit if hard else cut
        yield text[start:cut]
        if cut in headings or cut in starts:
            next_start = cut
        elif hard:
            next_start = cut - overlap
        else:
            index = bisect_left(boundaries, max(start + 1, cut - overlap))
            next_start = (
                boundaries[index] if index < len(boundaries) and boundaries[index] < cut else cut
            )
        start = next_start
