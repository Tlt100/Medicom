"""Turns untrusted uploaded bytes into page-numbered plain text.

Security posture:
- File type is decided from the bytes (magic number), not the client's filename or Content-Type.
- Size, page, character and time budgets bound the work an attacker can force.
- PDFs are parsed for text only with pypdf: nothing in the file is executed, rendered or followed
  (no JavaScript, forms, links or embedded files). Encrypted PDFs are rejected.
- Nothing is written to disk. Callers hold the bytes only for the duration of one request.
"""

import io
import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import List

MAX_BYTES = 4 * 1024 * 1024
MAX_PAGES = 30
MAX_CHARS_PER_PAGE = 20_000
MAX_TOTAL_CHARS = 150_000
TIME_BUDGET_SECONDS = 8.0

logger = logging.getLogger("patientshield")


class DocumentError(ValueError):
    """A safe, user-facing problem with an uploaded file."""

    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass
class ParsedDocument:
    name: str
    kind: str  # "pdf" | "text"
    size_bytes: int
    pages: List[str]
    truncated: bool = False


_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤⁦-⁩﻿]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_PAGE_MARKER = re.compile(r"^-{2,}\s*page\s+\d+\s*-{2,}\s*$", re.I | re.M)


def safe_name(name: str) -> str:
    cleaned = "".join(ch for ch in (name or "") if ch.isprintable() and ch not in '<>"\\/')
    return (cleaned.strip() or "document")[:120]


def detect_kind(name: str, data: bytes) -> str:
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    if data[:5] == b"%PDF-":
        return "pdf"
    if ext == "pdf":
        raise DocumentError("unsupported_type", "This file is named .pdf but isn't a valid PDF.")
    if ext in {"txt", "text", "md"} or not ext:
        return "text"
    raise DocumentError("unsupported_type", "PatientShield accepts PDF (.pdf) and plain-text (.txt) files only.")


def normalize_text(text: str) -> str:
    """Canonical page text. All citation offsets refer to this normalized form."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _INVISIBLE.sub("", text)
    text = _CONTROL.sub("", text)
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _cap(pages: List[str]) -> "tuple[List[str], bool]":
    out, total, truncated = [], 0, False
    for page in pages:
        if len(page) > MAX_CHARS_PER_PAGE:
            page, truncated = page[:MAX_CHARS_PER_PAGE], True
        if total + len(page) > MAX_TOTAL_CHARS:
            page, truncated = page[: max(0, MAX_TOTAL_CHARS - total)], True
        total += len(page)
        out.append(page)
        if total >= MAX_TOTAL_CHARS:
            break
    return out, truncated


def parse_text(data: bytes) -> List[str]:
    if b"\x00" in data[:8192]:
        raise DocumentError("binary_content", "This file looks like binary data, not text.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentError("bad_encoding", "This text file isn't valid UTF-8. Save it as UTF-8 text and try again.") from exc
    parts = re.split(r"\f|" + _PAGE_MARKER.pattern, text, flags=re.I | re.M)
    pages = [normalize_text(p) for p in parts]
    pages = [p for p in pages if p] or [""]
    if len(pages) > MAX_PAGES:
        raise DocumentError("too_many_pages", f"This file has {len(pages)} pages. The limit is {MAX_PAGES}.")
    return pages


def parse_pdf(data: bytes) -> List[str]:
    from pypdf import PdfReader  # imported lazily: only PDF requests pay for it
    from pypdf.errors import PdfReadError

    started = time.monotonic()
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise DocumentError("encrypted", "This PDF is password-protected. Remove the password and try again.")
        count = len(reader.pages)
    except DocumentError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError, RecursionError) as exc:
        logger.info("pdf open failed: %s", type(exc).__name__)
        raise DocumentError("parse_failed", "We couldn't read this PDF. It may be damaged or use an unsupported format.") from exc

    if count == 0:
        raise DocumentError("parse_failed", "This PDF has no pages.")
    if count > MAX_PAGES:
        raise DocumentError("too_many_pages", f"This PDF has {count} pages. The limit is {MAX_PAGES}. Upload just the denial letter.")

    pages: List[str] = []
    for index in range(count):
        if time.monotonic() - started > TIME_BUDGET_SECONDS:
            raise DocumentError("too_slow", "This PDF took too long to read. Try a shorter or simpler file.")
        try:
            raw = reader.pages[index].extract_text() or ""
        except Exception as exc:  # noqa: BLE001 - one bad page shouldn't hide the rest
            logger.info("pdf page %d failed: %s", index + 1, type(exc).__name__)
            raw = ""
        pages.append(normalize_text(raw[: MAX_CHARS_PER_PAGE * 2]))
    return pages


def parse_document(name: str, data: bytes) -> ParsedDocument:
    if not data:
        raise DocumentError("empty", "This file is empty.")
    if len(data) > MAX_BYTES:
        raise DocumentError("too_large", f"This file is {len(data) / 1024 / 1024:.1f} MB. The limit is 4 MB.", status=413)

    kind = detect_kind(name, data)
    pages = parse_pdf(data) if kind == "pdf" else parse_text(data)
    pages, truncated = _cap(pages)

    if not any(p.strip() for p in pages):
        raise DocumentError(
            "no_text",
            "We couldn't find any text in this file. If it's a scanned image, PatientShield can't read it yet. "
            "Try a text-based PDF or a .txt file.",
        )
    return ParsedDocument(name=safe_name(name), kind=kind, size_bytes=len(data), pages=pages, truncated=truncated)
