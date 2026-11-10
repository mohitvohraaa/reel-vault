"""Configurable LLM summarization with validation, retries and an offline stub."""
from __future__ import annotations

import json
import re
import time

from app.core.config import settings
from app.core.constants import DEFAULT_CATEGORIES
from app.core.logging import get_logger
from app.services.summarization.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.summarization.schema import ReelSummary
from app.utils.text import word_count

log = get_logger("summarization")


# --------------------------------------------------------------------- providers
class JsonLLM:
    """Interface: given system+user prompts, return a parsed JSON object."""

    def complete_json(self, system: str, user: str) -> dict:  # pragma: no cover - interface
        raise NotImplementedError


class OpenAILLM(JsonLLM):
    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        self.model = settings.llm_model

    def complete_json(self, system: str, user: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=settings.llm_timeout_sec,
        )
        return json.loads(resp.choices[0].message.content or "{}")


class GeminiLLM(JsonLLM):
    def __init__(self):
        import google.generativeai as genai

        genai.configure(api_key=settings.llm_api_key)
        self.model = genai.GenerativeModel(settings.llm_model)

    def complete_json(self, system: str, user: str) -> dict:
        resp = self.model.generate_content(
            f"{system}\n\n{user}",
            generation_config={"response_mime_type": "application/json", "temperature": 0.2},
        )
        return json.loads(resp.text or "{}")


def get_json_llm() -> JsonLLM | None:
    """Return a network LLM provider, or None when running in stub mode."""
    if settings.llm_provider == "openai" and settings.llm_api_key:
        return OpenAILLM()
    if settings.llm_provider == "gemini" and settings.llm_api_key:
        return GeminiLLM()
    return None


def chat_complete(system: str, user: str) -> str | None:
    """Free-text completion for RAG chat. Returns None in stub mode so callers
    can fall back to a deterministic extractive answer."""
    model = settings.chat_model or settings.llm_model
    if settings.llm_provider == "openai" and settings.llm_api_key:
        from openai import OpenAI

        client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
            timeout=settings.llm_timeout_sec,
        )
        return resp.choices[0].message.content
    if settings.llm_provider == "gemini" and settings.llm_api_key:
        import google.generativeai as genai

        genai.configure(api_key=settings.llm_api_key)
        gm = genai.GenerativeModel(model)
        return gm.generate_content(f"{system}\n\n{user}").text
    return None


# ------------------------------------------------------------------- stub engine
_CATEGORY_KEYWORDS = {
    "AI / Machine Learning": ["ai", "machine learning", "llm", "model", "neural", "gpt", "agent"],
    "Programming": ["python", "javascript", "code", "function", "api", "developer", "framework"],
    "Technology": ["tech", "software", "hardware", "gadget", "app", "device"],
    "Startups / Business": ["startup", "business", "revenue", "founder", "customer", "market", "saas"],
    "Finance": ["money", "invest", "stock", "crypto", "budget", "finance", "tax"],
    "Productivity": ["productivity", "workflow", "habit", "focus", "notion", "organize"],
    "Fitness": ["workout", "fitness", "exercise", "muscle", "diet", "gym"],
    "Travel": ["travel", "trip", "flight", "hotel", "destination", "city"],
    "Learning / Education": ["learn", "course", "study", "tutorial", "lesson", "explain"],
    "Entertainment": ["movie", "music", "game", "show", "funny", "meme"],
}


def _guess_category(text: str) -> str:
    low = text.lower()
    best, best_score = "Interesting / Miscellaneous", 0
    for cat, kws in _CATEGORY_KEYWORDS.items():
        score = sum(low.count(k) for k in kws)
        if score > best_score:
            best, best_score = cat, score
    return best


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return parts[0][:200] if parts and parts[0] else ""


def stub_summary(*, transcript: str | None, caption: str | None, metadata: dict, language: str | None) -> ReelSummary:
    """Deterministic, offline summary so the stack runs without API keys.

    Grounded in the actual input text — it never fabricates claims — but it is a
    placeholder; configure a real provider for quality output."""
    text = (transcript or "").strip() or (caption or "").strip()
    sufficient = word_count(text) >= 4
    if not sufficient:
        return ReelSummary(
            title=(caption or "Shared Reel")[:80] or "Shared Reel",
            one_liner="Not enough transcript or caption text to summarize.",
            summary="",
            category="Interesting / Miscellaneous",
            has_sufficient_content=False,
            language=language or "en",
        )
    words = text.split()
    title = " ".join(words[:8]).strip().rstrip(".,")
    title = (title[:1].upper() + title[1:]) if title else "Shared Reel"
    one_liner = _first_sentence(text) or title
    summary = text[:500].strip()
    low = text.lower()
    content_type = "tutorial" if any(k in low for k in ["how to", "step", "tutorial", "guide"]) else "explainer"
    entities = list(dict.fromkeys(re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", text)))[:8]
    return ReelSummary(
        title=title[:120],
        one_liner=one_liner,
        summary=summary,
        category=_guess_category(text),
        subcategories=[],
        key_takeaways=[s for s in re.split(r"(?<=[.!?])\s+", summary) if s][:3],
        entities=entities,
        actionable_insights=[],
        content_type=content_type,
        importance="medium",
        language=language or "en",
        has_sufficient_content=True,
    )


# ----------------------------------------------------------------- orchestration
def summarize_reel(*, transcript: str | None, caption: str | None, metadata: dict,
                   language: str | None = None) -> ReelSummary:
    """Summarize a reel into a validated ReelSummary.

    Uses the configured provider with exponential-backoff retries; falls back to
    the deterministic stub when no provider/key is configured."""
    llm = get_json_llm()
    if llm is None:
        return stub_summary(transcript=transcript, caption=caption, metadata=metadata, language=language)

    system = SYSTEM_PROMPT
    user = build_user_prompt(transcript=transcript, caption=caption, metadata=metadata)
    last_error: Exception | None = None
    for attempt in range(settings.llm_max_retries):
        try:
            raw = llm.complete_json(system, user)
            return ReelSummary.model_validate(raw)
        except Exception as exc:
            last_error = exc
            wait = min(2 ** attempt, 10)
            log.warning("summarization attempt %s failed: %s (retrying in %ss)", attempt + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"summarization failed after {settings.llm_max_retries} attempts: {last_error}")
