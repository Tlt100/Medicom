"""Minimal, dependency-free PDF writer for synthetic sample documents (letters, EOBs, bills).

It produces simple text-only PDFs (Helvetica, ASCII) so demo mode exercises the real PDF parsing path
without committing binary files. It is not a general-purpose PDF library.
"""

import textwrap
from typing import List, Protocol, Tuple


class Renderable(Protocol):
    """Anything with an id, a title and pages of paragraphs (a paragraph starting with "## " is a heading).

    It may also set `footer` to replace the default synthetic-sample footer line.
    """

    id: str
    title: str
    pages: List[List[str]]


PAGE_W, PAGE_H = 612, 792
MARGIN_X, TOP_Y, BOTTOM_Y = 72, 720, 72
SIZE, LEADING = 10.5, 15
WRAP = 92
FOOTER = "SYNTHETIC SAMPLE - NOT A REAL LETTER - created for PatientShield demo mode"


def _escape(text: str) -> str:
    if not text.isascii():
        raise ValueError("sample letters must be ASCII")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _layout(paragraphs: List[str]) -> List[Tuple[str, str]]:
    """Returns (font, line) pairs; an empty line is a paragraph gap."""
    lines: List[Tuple[str, str]] = []
    for para in paragraphs:
        bold = para.startswith("## ")
        body = para[3:] if bold else para
        for raw in body.split("\n"):
            for wrapped in textwrap.wrap(raw, WRAP) or [""]:
                lines.append(("F2" if bold else "F1", wrapped))
        lines.append(("F1", ""))
    return lines


def _page_stream(lines: List[Tuple[str, str]], page_no: int, page_count: int, footer_text: str = FOOTER) -> bytes:
    out = [f"BT /F1 {SIZE} Tf {LEADING} TL {MARGIN_X} {TOP_Y} Td"]
    current = "F1"
    for font, line in lines:
        if font != current:
            out.append(f"/{font} {SIZE} Tf")
            current = font
        out.append(f"({_escape(line)}) Tj T*" if line else "T*")
    out.append("ET")
    footer = f"{footer_text} - Page {page_no} of {page_count}"
    out.append(f"BT /F1 8 Tf {MARGIN_X} 40 Td ({_escape(footer)}) Tj ET")
    return "\n".join(out).encode("ascii")


def render_pdf(letter: Renderable) -> bytes:
    max_lines = int((TOP_Y - BOTTOM_Y) / LEADING)
    pages = [_layout(p) for p in letter.pages]
    for laid_out in pages:
        if len(laid_out) > max_lines:
            raise ValueError(f"{letter.id}: page overflows ({len(laid_out)} lines > {max_lines})")

    objects: List[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    catalog = add(b"")  # placeholder, filled after pages are known
    pages_obj = add(b"")
    f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    kids = []
    for i, laid_out in enumerate(pages, start=1):
        stream = _page_stream(laid_out, i, len(pages), getattr(letter, "footer", FOOTER))
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page = add(
            (
                f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Resources << /Font << /F1 {f1} 0 R /F2 {f2} 0 R >> >> /Contents {content} 0 R >>"
            ).encode("ascii")
        )
        kids.append(page)

    objects[catalog - 1] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("ascii")
    kid_refs = " ".join(f"{k} 0 R" for k in kids)
    objects[pages_obj - 1] = f"<< /Type /Pages /Kids [{kid_refs}] /Count {len(kids)} >>".encode("ascii")
    title = _escape(f"Synthetic sample: {letter.title}")

    info = add(f"<< /Title ({title}) /Producer (PatientShield synthetic sample generator) >>".encode("ascii"))

    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf += f"{n} 0 obj\n".encode("ascii") + body + b"\nendobj\n"
    xref = len(buf)
    buf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")
    for off in offsets:
        buf += f"{off:010d} 00000 n \n".encode("ascii")
    buf += f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R /Info {info} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    return bytes(buf)
