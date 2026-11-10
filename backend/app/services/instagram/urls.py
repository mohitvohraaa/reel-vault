"""Deterministic Instagram URL extraction, classification and normalization.

We deliberately do NOT treat every instagram.com link as a Reel. Reels are
identified by their path (``/reel/``, ``/reels/``, ``/tv/``). ``/p/`` links are
ambiguous "posts" and are only treated as reels when accompanying attachment
metadata indicates a video.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

# Matches bare and wrapped Instagram URLs inside free text.
_URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+", re.IGNORECASE)

_INSTAGRAM_HOSTS = {
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
    "l.instagram.com",  # link-shim host
    "ig.me",
}

# path segment -> content kind
_REEL_SEGMENTS = {"reel", "reels", "tv"}
_POST_SEGMENTS = {"p"}

_SHORTCODE_RE = re.compile(r"^[A-Za-z0-9_-]{5,}$")


@dataclass(frozen=True)
class ClassifiedUrl:
    url: str
    kind: str  # "reel" | "post" | "profile" | "other"
    shortcode: str | None
    normalized: str | None  # canonical reel URL when kind in {reel, post}


def find_urls(text: str | None) -> list[str]:
    if not text:
        return []
    return _URL_RE.findall(text)


def _host_matches(host: str) -> bool:
    host = (host or "").lower()
    return host in _INSTAGRAM_HOSTS or host.endswith(".instagram.com")


def classify_url(url: str) -> ClassifiedUrl:
    """Classify a single URL. Non-Instagram URLs classify as ``other``."""
    raw = (url or "").strip().strip(".,);]")
    try:
        parsed = urlparse(raw)
    except ValueError:
        return ClassifiedUrl(raw, "other", None, None)

    if not _host_matches(parsed.netloc):
        return ClassifiedUrl(raw, "other", None, None)

    segments = [s for s in parsed.path.split("/") if s]
    if not segments:
        return ClassifiedUrl(raw, "profile", None, None)

    first = segments[0].lower()
    if first in _REEL_SEGMENTS and len(segments) >= 2:
        code = segments[1]
        if _SHORTCODE_RE.match(code):
            return ClassifiedUrl(raw, "reel", code, canonical_reel_url(code))
    if first in _POST_SEGMENTS and len(segments) >= 2:
        code = segments[1]
        if _SHORTCODE_RE.match(code):
            # Ambiguous: a /p/ link may be a photo or a video post.
            return ClassifiedUrl(raw, "post", code, canonical_reel_url(code))
    # Single-segment path that isn't a known content type → a profile handle.
    if len(segments) == 1:
        return ClassifiedUrl(raw, "profile", None, None)
    return ClassifiedUrl(raw, "other", None, None)


def canonical_reel_url(shortcode: str) -> str:
    return f"https://www.instagram.com/reel/{shortcode}/"


def is_reel(classified: ClassifiedUrl, has_video_attachment: bool = False) -> bool:
    """Decide whether a classified URL should be ingested as a Reel.

    - ``reel`` kind is always a reel.
    - ``post`` kind is a reel only when attachment metadata indicates video.
    """
    if classified.kind == "reel":
        return True
    if classified.kind == "post" and has_video_attachment:
        return True
    return False


def extract_reel_urls(text: str | None, has_video_attachment: bool = False) -> list[ClassifiedUrl]:
    """Return classified URLs from free text that qualify as reels."""
    out: list[ClassifiedUrl] = []
    seen: set[str] = set()
    for u in find_urls(text):
        c = classify_url(u)
        if is_reel(c, has_video_attachment) and c.normalized and c.normalized not in seen:
            seen.add(c.normalized)
            out.append(c)
    return out
