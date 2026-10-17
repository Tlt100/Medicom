"""Splits normalized page text into passages while keeping exact character offsets.

PDF text extraction loses paragraph breaks and wraps sentences across lines, so passages are rebuilt
from line structure: short unpunctuated lines at a paragraph boundary are headings, "Label: value" lines
stand alone, and everything else is joined into blocks that are then split into sentences.
Every Passage satisfies: page_text[start:end] == text.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class Passage:
    page: int
    start: int
    end: int
    text: str
    kind: str  # "heading" | "label" | "sentence"

    @property
    def flat(self) -> str:
        """Whitespace-collapsed text for matching and display."""
        return re.sub(r"\s+", " ", self.text).strip()


# "Member ID: X", "Claim Number: 123", "Date: September 15, 2026": 1-5 words, then a colon and a value.
_LABEL_LINE = re.compile(r"^[A-Z][A-Za-z0-9.#&/()'-]*(?: [A-Za-z0-9.#&/()'-]+){0,4}:\s+\S")
_TERMINAL = re.compile(r"[.!?:;]$")
_ABBREVIATIONS = {
    "no",
    "dr",
    "mr",
    "mrs",
    "ms",
    "st",
    "ave",
    "inc",
    "co",
    "corp",
    "ltd",
    "jr",
    "sr",
    "vs",
    "etc",
    "e.g",
    "i.e",
    "u.s",
    "n.j",
    "a.m",
    "p.m",
    "p.o",
    "dept",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
    "fig",
    "sec",
    "approx",
}
_SENTENCE_END = re.compile(r"[.!?](?=\s+[\"'(\[A-Z0-9])")


def _lines(text: str) -> List[Tuple[int, int]]:
    spans, pos = [], 0
    for line in text.split("\n"):
        spans.append((pos, pos + len(line)))
        pos += len(line) + 1
    return spans


def _trimmed(text: str, start: int, end: int) -> Tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _split_sentences(text: str, start: int, end: int) -> List[Tuple[int, int]]:
    spans, cursor = [], start
    for match in _SENTENCE_END.finditer(text, start, end):
        cut = match.end()
        token = re.search(r"([A-Za-z.]+)\.?$", text[cursor : cut - 1] + text[cut - 1])
        word = (token.group(1) if token else "").rstrip(".").lower()
        if word in _ABBREVIATIONS or (len(word) == 1 and word.isalpha()):
            continue  # "No. 123", "Dr. Smith", "J. Doe"
        spans.append((cursor, cut))
        cursor = cut
    spans.append((cursor, end))
    return [s for s in (_trimmed(text, a, b) for a, b in spans) if s[1] > s[0]]


def _wrap_threshold(text: str) -> int:
    """Lines at least this long probably wrapped onto the next line rather than ending a paragraph."""
    lengths = sorted(len(line.strip()) for line in text.split("\n") if line.strip())
    if not lengths:
        return 60
    typical = lengths[int(len(lengths) * 0.9) - 1 if len(lengths) > 1 else 0]
    return max(40, int(typical * 0.8))


def segment_page(page_number: int, text: str) -> List[Passage]:
    passages: List[Passage] = []
    block_start = None
    block_end = 0
    open_block = False
    threshold = _wrap_threshold(text)

    def flush():
        nonlocal block_start, open_block
        if block_start is not None:
            for a, b in _split_sentences(text, block_start, block_end):
                passages.append(Passage(page_number, a, b, text[a:b], "sentence"))
        block_start, open_block = None, False

    def standalone(a: int, b: int, kind: str):
        flush()
        s, e = _trimmed(text, a, b)
        passages.append(Passage(page_number, s, e, text[s:e], kind))

    spans = _lines(text)
    for index, (a, b) in enumerate(spans):
        line = text[a:b].strip()
        if not line:
            flush()
            continue
        next_line = text[spans[index + 1][0] : spans[index + 1][1]].strip() if index + 1 < len(spans) else ""
        if _LABEL_LINE.match(line) and len(line) <= 120:
            standalone(a, b, "label")
            continue
        is_heading = (
            not open_block
            and len(line) < threshold
            and not _TERMINAL.search(line)
            and not line.endswith(",")
            and (line[0].isupper() or line[0].isdigit())
        )
        if is_heading:
            standalone(a, b, "heading")
            continue
        if block_start is None:
            block_start = a
        block_end = b
        ends_sentence = bool(re.search(r"[.!?:]$", line))
        wrapped = not ends_sentence and len(line) >= threshold
        open_block = wrapped or (next_line[:1].islower())
        if not open_block:
            flush()
    flush()
    return passages


def segment_document(pages: List[str]) -> List[Passage]:
    out: List[Passage] = []
    for number, text in enumerate(pages, start=1):
        out.extend(segment_page(number, text))
    return out
