"""LLM structured-output validation and offline stub summary tests."""
from __future__ import annotations

from app.services.summarization.llm import stub_summary, summarize_reel
from app.services.summarization.schema import ReelSummary


def test_schema_coerces_and_validates_partial_response():
    raw = {
        "title": "  A Title  ",
        "subcategories": "AI",            # string → list
        "key_takeaways": None,            # None → []
        "content_type": "nonsense",       # invalid → "other"
        "importance": "critical",         # invalid → "medium"
    }
    s = ReelSummary.model_validate(raw)
    assert s.title == "A Title"
    assert s.subcategories == ["AI"]
    assert s.key_takeaways == []
    assert s.content_type == "other"
    assert s.importance == "medium"


def test_schema_defaults_on_empty_input():
    s = ReelSummary.model_validate({})
    assert s.title == "Untitled Reel"
    assert s.category == "Interesting / Miscellaneous"
    assert s.has_sufficient_content is True


def test_stub_summary_marks_insufficient_when_no_text():
    s = stub_summary(transcript=None, caption=None, metadata={}, language=None)
    assert s.has_sufficient_content is False


def test_stub_summary_grounded_in_text():
    text = "How to build AI agents in Python using function calling and tools."
    s = stub_summary(transcript=text, caption=None, metadata={}, language="en")
    assert s.has_sufficient_content is True
    assert s.category in ("AI / Machine Learning", "Programming")
    assert s.content_type == "tutorial"
    assert s.summary  # non-empty, drawn from the transcript


def test_summarize_reel_uses_stub_without_provider():
    s = summarize_reel(
        transcript="A quick startup growth tip about customer retention.",
        caption=None,
        metadata={"reel_url": "x"},
    )
    assert isinstance(s, ReelSummary)
    assert s.title
