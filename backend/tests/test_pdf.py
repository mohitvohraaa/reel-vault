"""PDF HTML-template tests (no WeasyPrint required)."""
from __future__ import annotations

from types import SimpleNamespace

from app.services.pdf.renderer import build_html


def _reel(**kw):
    base = dict(
        title="Building AI Agents", creator_username="ai_daily", shared_at=None,
        processing_status="completed", category="AI / Machine Learning",
        subcategories=["Agents"], one_liner="A guide to agents.",
        summary="Agents use tools and planning.", key_takeaways=["Use tools"],
        actionable_insights=["Try function calling"], entities=["Python"],
        normalized_url="https://www.instagram.com/reel/X1/", transcript="full transcript text",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_build_html_includes_core_fields():
    html = build_html(heading="Export", subtitle="1 reels", reels=[_reel()], config={"include_qr": False})
    assert "Building AI Agents" in html
    assert "AI / Machine Learning" in html
    assert "A guide to agents." in html
    assert "full transcript text" in html
    assert "instagram.com/reel/X1" in html


def test_template_config_can_hide_transcript():
    html = build_html(heading="Export", subtitle="", reels=[_reel()],
                      config={"include_transcript": False, "include_qr": False})
    assert "full transcript text" not in html
    assert "Building AI Agents" in html
