import pytest

from app.modules.ingestion.parser import ParseError, parse_chunks


def test_windows_preserve_text_and_overlap(tmp_path):
    path = tmp_path / "sample.md"
    text = "甲乙丙丁" * 550
    path.write_text(text)
    chunks = parse_chunks(path)
    assert len(chunks) == 3
    assert chunks[0]["content"][-100:] == chunks[1]["content"][:100]
    reconstructed = chunks[0]["content"] + "".join(c["content"][100:] for c in chunks[1:])
    assert reconstructed == text
    assert all(c["page"] is None for c in chunks)


def test_empty_rejected(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("  ")
    with pytest.raises(ParseError):
        parse_chunks(path)


def test_wrong_encoding_rejected(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(ParseError):
        parse_chunks(path)


@pytest.mark.parametrize("strategy", ["fixed", "structure"])
def test_pdf_preserves_page_numbers(tmp_path, strategy):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    for message in ("VPN instructions", "Reset password"):
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 10 200 Td ({message}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    path = tmp_path / "guide.pdf"
    writer.write(path)
    chunks = parse_chunks(path, strategy=strategy)
    assert [c["page"] for c in chunks] == [1, 2]
    assert "VPN instructions" in chunks[0]["content"]
    assert "Reset password" in chunks[1]["content"]


def test_structure_preserves_whole_sentence_near_window_boundary(tmp_path):
    path = tmp_path / "boundary.md"
    sentence = "专项审批需提交" + "完整材料以及经过签字确认的申请文件" * 8 + "。"
    text = "# 审批制度\n\n" + ("背景说明。" * 140) + "\n\n" + sentence + "\n\n结束。"
    path.write_text(text)
    chunks = parse_chunks(path, strategy="structure")
    assert any(sentence in c["content"] for c in chunks)
    assert all(len(c["content"]) <= 800 and c["content"] in text for c in chunks)


def test_structure_keeps_small_table_and_fenced_block_whole(tmp_path):
    path = tmp_path / "blocks.md"
    table = "| 项目 | 金额 |\n| --- | --- |\n" + "| 午餐 | 128 |\n" * 12
    code = "```python\n" + 'print("hello")\n' * 12 + "```\n"
    text = "说明。" * 250 + "\n\n" + table + "\n\n" + code
    path.write_text(text)
    chunks = parse_chunks(path, strategy="structure")
    assert any(table.strip() in c["content"] for c in chunks)
    assert any(code.strip() in c["content"] for c in chunks)
    assert all(len(c["content"]) <= 800 for c in chunks)


@pytest.mark.parametrize(
    "text",
    [
        "".join(f"{i:04d}无标点长文" for i in range(300)),
        "".join(f"{i:04d}一。\n\n二。\n\n" for i in range(200)),
        "".join(f"# 标题{i:04d}\n内容。\n" for i in range(200)),
    ],
    ids=["long", "paragraphs", "headings"],
)
def test_structure_never_loses_nonwhitespace_content(tmp_path, text):
    path = tmp_path / "coverage.txt"
    path.write_text(text)
    chunks = parse_chunks(path, size=200, overlap=30, strategy="structure")
    assert [c["position"] for c in chunks] == list(range(len(chunks)))
    covered = set()
    start = 0
    for c in chunks:
        offset = text.find(c["content"], start)
        assert offset >= 0
        covered.update(range(offset, offset + len(c["content"])))
        start = offset + 1
        assert len(c["content"]) <= 200
    assert all(i in covered for i, char in enumerate(text) if not char.isspace())


def test_structure_unknown_policy_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        parse_chunks(tmp_path / "missing.txt", strategy="unknown")
