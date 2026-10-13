"""数据集语料的唯一定义，供装配、校验与评估脚本共用。

把"哪些文件算语料"集中在这里，避免出现"题集按 120 份装配、评估按 126 份装载"这类漂移
（PDF 附录是否计入，是一个曾经真实踩到的不一致）。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVALS = ROOT / "evals"
CORPUS = EVALS / "corpus"
DOMAINS = ("it", "hr", "product")
#: 正文用 Markdown/纯文本，PDF 为格式保真附录（用于验证解析与页码溯源）。
TEXT_SUFFIXES = {".md", ".txt"}
PDF_SUFFIXES = {".pdf"}
ALL_SUFFIXES = TEXT_SUFFIXES | PDF_SUFFIXES


def corpus_files(domain: str, *, include_pdf: bool = True) -> list[Path]:
    suffixes = ALL_SUFFIXES if include_pdf else TEXT_SUFFIXES
    folder = CORPUS / domain
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in suffixes)


def all_corpus_files(*, include_pdf: bool = True) -> list[Path]:
    return [p for domain in DOMAINS for p in corpus_files(domain, include_pdf=include_pdf)]


def relative_key(path: Path) -> str:
    """manifest 与评估里的稳定键：<domain>/<filename>。"""
    return f"{path.parent.name}/{path.name}"
