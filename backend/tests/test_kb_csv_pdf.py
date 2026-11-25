"""KB accepts .csv and .pdf next to .md/.txt (no database needed)."""
from app.services import kb_import


def _tiny_pdf(text: str) -> bytes:
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 100] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        None,
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = f"BT /F1 12 Tf 10 50 Td ({text}) Tj ET"
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        if body is None:
            body = f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"
        out += f"{i} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


def test_csv_and_pdf_are_accepted_other_types_are_not():
    assert kb_import._skip_reason("prices.csv") is None
    assert kb_import._skip_reason("guide.PDF") is None
    assert kb_import._skip_reason("photo.png") is not None
    assert kb_import._skip_reason("macro.xlsx") is not None


def test_csv_is_read_as_text():
    assert kb_import._decode(b"name,price\nA,1\n", "prices.csv") == "name,price\nA,1\n"


def test_pdf_text_is_extracted():
    assert "Hello Helix" in (kb_import._decode(_tiny_pdf("Hello Helix"), "guide.pdf") or "")


def test_broken_or_binary_pdf_is_skipped_not_raised():
    assert kb_import._decode(b"not a pdf at all", "bad.pdf") is None
    assert kb_import._decode(b"%PDF-1.4\n\x00\x00garbage", "bad.pdf") is None
