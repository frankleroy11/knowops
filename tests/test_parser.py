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


def test_pdf_preserves_page_numbers(tmp_path):
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
    chunks = parse_chunks(path)
    assert [c["page"] for c in chunks] == [1, 2]
    assert "VPN instructions" in chunks[0]["content"]
    assert "Reset password" in chunks[1]["content"]
