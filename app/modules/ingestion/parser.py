# 中文导读：
# 文档解析入口：读取文本或 PDF，再按版本切分策略生成块
# 扫描件没有可提取文本时会失败，目前不能视为已实现 OCR

"""Deterministic fixed/structure-aware splitting; preserve PDF page provenance."""

from pathlib import Path

from pypdf import PdfReader

from app.modules.ingestion.splitter import structured, windows


class ParseError(ValueError):
    pass


def parse_chunks(path: Path, size: int = 800, overlap: int = 100, *, strategy: str = "fixed"):
    if strategy not in {"fixed", "structure"}:
        raise ValueError("unknown chunk strategy")
    if not 0 <= overlap < size:
        raise ValueError("overlap must be smaller than chunk size")
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ParseError("暂不支持加密 PDF")
        pages = [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    else:
        try:
            pages = [(None, path.read_text(encoding="utf-8-sig"))]
        except UnicodeDecodeError as exc:
            raise ParseError("文本文件必须使用 UTF-8 编码") from exc
    result = []
    for page, text in pages:
        text = text.replace("\x00", "").strip()
        splitter = windows if strategy == "fixed" else structured
        for content in splitter(text, size, overlap):
            content = content.strip()
            if content:
                result.append({"position": len(result), "page": page, "content": content})
    if not result:
        raise ParseError("未提取到文本；扫描 PDF 需后续接入 OCR")
    return result
