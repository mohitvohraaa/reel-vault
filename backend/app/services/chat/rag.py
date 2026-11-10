"""Retrieval-augmented chat over a knowledge base (or the whole vault).

Retrieve → ground → answer with citations. Answers are grounded ONLY in the
retrieved reels; the stub (no-API) mode returns an honest extractive answer so
the feature works offline.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge_base import KnowledgeBase, knowledge_base_reels
from app.models.reel import Reel
from app.models.reel_chunk import ReelChunk
from app.services.embeddings.embedder import embed_query
from app.services.search.service import ReelFilters, semantic_reel_ids
from app.services.summarization.llm import chat_complete

SYSTEM = (
    "You are ReelVault's knowledge assistant. Answer the user's question using ONLY "
    "the provided reel excerpts. Cite reels inline as [#<id>]. If the excerpts do not "
    "contain the answer, say so plainly. Be concise and specific."
)


@dataclass
class Citation:
    reel_id: int
    title: str | None
    url: str
    snippet: str


@dataclass
class ChatAnswer:
    content: str
    citations: list[dict]


def _member_ids(db: Session, kb: KnowledgeBase | None) -> list[int] | None:
    if kb is None:
        return None  # whole vault
    rows = db.execute(
        select(knowledge_base_reels.c.reel_id).where(knowledge_base_reels.c.knowledge_base_id == kb.id)
    ).all()
    return [r[0] for r in rows]


def _gather_context(db: Session, query: str, restrict_ids: list[int] | None, top_k: int):
    qvec = embed_query(query)
    ranked = semantic_reel_ids(db, qvec, ReelFilters(), limit=top_k, restrict_ids=restrict_ids)
    reel_ids = [rid for rid, _ in ranked]
    if not reel_ids:
        return [], []
    reels = {r.id: r for r in db.scalars(select(Reel).where(Reel.id.in_(reel_ids))).all()}
    # Best matching chunk per reel for the snippet.
    snippets: dict[int, str] = {}
    for rid in reel_ids:
        chunk = db.scalars(
            select(ReelChunk).where(ReelChunk.reel_id == rid).order_by(ReelChunk.chunk_index).limit(1)
        ).first()
        if chunk:
            snippets[rid] = chunk.content[:500]
        elif rid in reels and reels[rid].summary:
            snippets[rid] = reels[rid].summary[:500]

    citations: list[Citation] = []
    context_blocks: list[str] = []
    for rid, sim in ranked:
        reel = reels.get(rid)
        if reel is None:
            continue
        snip = snippets.get(rid, reel.summary or "")
        citations.append(Citation(reel_id=rid, title=reel.title, url=reel.normalized_url, snippet=snip))
        context_blocks.append(
            f"[#{rid}] {reel.title or 'Untitled'} (by {reel.creator_username or 'unknown'})\n{snip}"
        )
    return context_blocks, citations


def answer(db: Session, *, kb: KnowledgeBase | None, query: str) -> ChatAnswer:
    context_blocks, citations = _gather_context(
        db, query, _member_ids(db, kb), settings.chat_top_k
    )
    citation_dicts = [
        {"reel_id": c.reel_id, "title": c.title, "url": c.url, "snippet": c.snippet} for c in citations
    ]

    if not context_blocks:
        return ChatAnswer(
            content="I couldn't find any reels in this knowledge base relevant to that question.",
            citations=[],
        )

    context = "\n\n".join(context_blocks)
    user = f"Question: {query}\n\nReel excerpts:\n{context}\n\nAnswer with inline [#id] citations."
    text = chat_complete(SYSTEM, user)

    if text is None:
        # Offline stub: extractive, grounded, honest.
        lead = (
            f"Here are the most relevant reels for “{query}” "
            f"(offline mode — configure an LLM provider for synthesized answers):"
        )
        bullets = "\n".join(
            f"- [#{c.reel_id}] {c.title or 'Untitled'}: {c.snippet[:160].strip()}" for c in citations
        )
        text = f"{lead}\n{bullets}"

    return ChatAnswer(content=text.strip(), citations=citation_dicts)
