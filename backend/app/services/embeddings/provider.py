"""Embedding providers: OpenAI, Gemini, and an offline deterministic stub."""
from __future__ import annotations

import hashlib
import math
import re

from app.core.config import settings

_TOKEN_RE = re.compile(r"\w+")


class EmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - interface
        raise NotImplementedError


class OpenAIEmbeddings(EmbeddingProvider):
    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.embedding_api_key, base_url=settings.embedding_base_url)
        self.model = settings.embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]


class GeminiEmbeddings(EmbeddingProvider):
    def __init__(self):
        import google.generativeai as genai

        genai.configure(api_key=settings.embedding_api_key)
        self.model = settings.embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        import google.generativeai as genai

        out = []
        for t in texts:
            r = genai.embed_content(model=self.model, content=t)
            out.append(r["embedding"])
        return out


class StubEmbeddings(EmbeddingProvider):
    """Deterministic hashing embedding. Shared vocabulary → similar vectors, so
    semantic search behaves sensibly offline. Not a substitute for a real model."""

    def __init__(self, dim: int | None = None):
        self.dim = dim or settings.embedding_dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _TOKEN_RE.findall((text or "").lower())
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 1) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider == "openai" and settings.embedding_api_key:
        return OpenAIEmbeddings()
    if settings.embedding_provider == "gemini" and settings.embedding_api_key:
        return GeminiEmbeddings()
    return StubEmbeddings()
