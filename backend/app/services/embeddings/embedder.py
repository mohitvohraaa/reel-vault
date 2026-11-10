"""Chunk-and-embed orchestration for reels + query embedding."""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.services.embeddings.provider import get_embedding_provider
from app.utils.text import chunk_text


@dataclass
class Chunk:
    index: int
    source: str
    content: str
    embedding: list[float]


def build_chunks(*, transcript: str | None, summary: str | None, caption: str | None) -> list[tuple[str, str]]:
    """Return (source, content) chunks to embed, preferring richer sources."""
    pieces: list[tuple[str, str]] = []
    for source, text in (("transcript", transcript), ("summary", summary), ("caption", caption)):
        if text and text.strip():
            for c in chunk_text(text, settings.chunk_chars, settings.chunk_overlap):
                pieces.append((source, c))
    return pieces


def embed_reel(*, transcript: str | None, summary: str | None, caption: str | None) -> list[Chunk]:
    pieces = build_chunks(transcript=transcript, summary=summary, caption=caption)
    if not pieces:
        return []
    provider = get_embedding_provider()
    vectors = provider.embed([content for _src, content in pieces])
    return [
        Chunk(index=i, source=src, content=content, embedding=vec)
        for i, ((src, content), vec) in enumerate(zip(pieces, vectors))
    ]


def embed_query(text: str) -> list[float]:
    provider = get_embedding_provider()
    return provider.embed([text])[0]
