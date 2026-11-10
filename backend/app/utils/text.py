"""Text utilities: Instagram mojibake repair, chunking, slugging."""
from __future__ import annotations

import re
import unicodedata

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def fix_mojibake(value: str | None) -> str | None:
    """Repair Instagram's double-encoded export text.

    Instagram encodes JSON string content as UTF-8 bytes that were then
    decoded as latin-1, producing sequences like ``\\u00c3\\u00a9`` for ``é``.
    Re-encoding latin-1 → decoding utf-8 restores the original text. If the
    round-trip fails, the original value is returned unchanged.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    try:
        repaired = value.encode("latin-1").decode("utf-8")
        return repaired
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def slugify(value: str, max_len: int = 80) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = _SLUG_RE.sub("-", value.lower()).strip("-")
    return value[:max_len] or "untitled"


def word_count(text: str | None) -> int:
    if not text:
        return 0
    return len(re.findall(r"\w+", text))


def chunk_text(text: str, chunk_chars: int, overlap: int) -> list[str]:
    """Split text into overlapping character windows on sentence-ish boundaries."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_chars, n)
        # Try to break on a whitespace boundary near the window end.
        if end < n:
            window = text[start:end]
            cut = max(window.rfind(". "), window.rfind("\n"), window.rfind(" "))
            if cut > chunk_chars * 0.5:
                end = start + cut + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks
