"""Versioned, isolated LLM prompts for reel summarization.

Keep prompt text here (not inline in code) so prompts are versioned and
auditable. Bump PROMPT_VERSION on any semantic change.
"""
from __future__ import annotations

import json

from app.core.constants import CONTENT_TYPES, DEFAULT_CATEGORIES, IMPORTANCE_LEVELS

PROMPT_VERSION = "2026-11-10.v1"

SYSTEM_PROMPT = """You are ReelVault's analysis engine. You turn the transcript and \
metadata of a single Instagram Reel into a precise, structured knowledge record.

Rules:
- Use ONLY information present in the transcript and provided metadata. Never invent \
facts, names, numbers, or claims that are not supported by the input.
- Distinguish factual claims from opinions in the summary when relevant.
- Prefer specific, useful summaries over generic descriptions. Preserve technical \
terminology exactly as stated.
- Generate an original, descriptive title. Do NOT simply copy the caption.
- If the transcript is empty, rely on the caption and metadata. If neither the \
transcript nor the caption contains enough information to understand the reel, set \
"has_sufficient_content" to false and keep other fields minimal and honest.
- Respond with a SINGLE JSON object only. No prose, no markdown fences."""


def _schema_hint() -> str:
    return json.dumps(
        {
            "title": "A concise, original descriptive title",
            "one_liner": "One sentence on what this reel is about and why it matters",
            "summary": "A concise but informative explanation grounded in the input",
            "category": f"One of: {DEFAULT_CATEGORIES}",
            "subcategories": ["More specific tags, e.g. AI, Agentic Systems"],
            "key_takeaways": ["Important point 1", "Important point 2"],
            "entities": ["Technologies, companies, people, or concepts mentioned"],
            "actionable_insights": ["Concrete things worth implementing or trying"],
            "content_type": f"One of: {CONTENT_TYPES}",
            "importance": f"One of: {IMPORTANCE_LEVELS}",
            "language": "ISO code of the reel's primary language, e.g. en",
            "has_sufficient_content": True,
        },
        indent=2,
    )


def build_user_prompt(*, transcript: str | None, caption: str | None, metadata: dict) -> str:
    transcript = (transcript or "").strip()
    caption = (caption or "").strip()
    meta_lines = "\n".join(f"- {k}: {v}" for k, v in metadata.items() if v)
    return f"""Analyze this Instagram Reel.

METADATA:
{meta_lines or "- (none)"}

CAPTION:
{caption or "(no caption available)"}

TRANSCRIPT:
{transcript or "(no transcript available — the audio may be music-only, private, or unavailable)"}

Return a JSON object with exactly these fields:
{_schema_hint()}
"""
