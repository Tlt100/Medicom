"""Builders for hostile-but-valid PDFs used by the security tests. Everything is generated in memory."""

import zlib
from typing import Dict, List


def _assemble(objects: List[bytes]) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def _stream(data: bytes, extra: str = "") -> bytes:
    packed = zlib.compress(data, 9)
    return f"<< {extra} /Filter /FlateDecode /Length {len(packed)} >>\nstream\n".encode() + packed + b"\nendstream"


def single_page(content: bytes) -> bytes:
    """One page whose content stream is `content` (compressed, so the file stays tiny)."""
    return _assemble(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            _stream(content),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
    )


def text_ops(n: int, chars: int = 200) -> bytes:
    return (b"BT /F1 9 Tf 10 700 Td (" + b"A" * chars + b") Tj ET\n") * n


def xobject_amplified(inner_ops: int, invocations: int, depth: int = 1) -> bytes:
    """A page that draws a Form XObject `invocations` times; the form nests `depth` levels deep."""
    objects: Dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    # Build the chain of forms: object 10 is the innermost; each outer form draws the one inside it once.
    form_ids = list(range(10, 10 + depth))
    for i, oid in enumerate(form_ids):
        if i == 0:
            body = text_ops(inner_ops, 20)
            res = "/Resources << /Font << /F1 5 0 R >> >>"
        else:
            body = b"/Fx Do\n"
            res = f"/Resources << /XObject << /Fx {form_ids[i - 1]} 0 R >> >>"
        objects[oid] = _stream(body, f"/Type /XObject /Subtype /Form /BBox [0 0 612 792] {res}")
    outer = form_ids[-1]
    objects[3] = (
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        f"/Resources << /Font << /F1 5 0 R >> /XObject << /Fx {outer} 0 R >> >> /Contents 4 0 R >>"
    ).encode()
    objects[4] = _stream(b"/Fx Do\n" * invocations)
    ordered = [objects.get(i, b"null") for i in range(1, max(objects) + 1)]
    return _assemble(ordered)


def multi_page(contents: List[bytes]) -> bytes:
    """One page per entry in `contents`, all sharing one font."""
    n = len(contents)
    font = 3 + 2 * n
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode())
    for i, content in enumerate(contents):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font} 0 R >> >> "
            f"/Contents {4 + 2 * i} 0 R >>".encode()
        )
        objects.append(_stream(content))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    return _assemble(objects)


def per_glyph_text(text: str) -> bytes:
    """Draws `text` one character per operator, as some printer drivers and PDF converters do."""
    ops = [b"BT /F1 9 Tf"]
    x, y = 40, 750
    for ch in text:
        if ch == "\n" or x > 560:
            x, y = 40, y - 11
            if ch == "\n":
                continue
        glyph = ch.encode("latin-1")
        if glyph in (b"\\", b"(", b")"):
            glyph = b"\\" + glyph
        ops.append(b"1 0 0 1 %d %d Tm (%s) Tj" % (x, y, glyph))
        x += 5
    ops.append(b"ET")
    return b"\n".join(ops)
