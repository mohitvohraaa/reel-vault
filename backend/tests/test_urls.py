"""URL classification, normalization and reel-detection tests."""
from __future__ import annotations

from app.services.instagram.urls import (
    canonical_reel_url,
    classify_url,
    extract_reel_urls,
    is_reel,
)


def test_reel_url_is_classified_and_normalized():
    c = classify_url("https://www.instagram.com/reel/CzAbc12345X/?igshid=xyz")
    assert c.kind == "reel"
    assert c.shortcode == "CzAbc12345X"
    assert c.normalized == "https://www.instagram.com/reel/CzAbc12345X/"
    assert is_reel(c) is True


def test_reels_and_tv_segments_are_reels():
    assert classify_url("https://instagram.com/reels/AbCdEf123/").kind == "reel"
    assert classify_url("https://www.instagram.com/tv/AbCdEf123/").kind == "reel"


def test_profile_link_is_not_a_reel():
    c = classify_url("https://www.instagram.com/some_creator/")
    assert c.kind == "profile"
    assert is_reel(c) is False


def test_generic_link_is_other():
    c = classify_url("https://example.com/reel/abc/")
    assert c.kind == "other"
    assert is_reel(c) is False


def test_post_link_only_reel_with_video_attachment():
    c = classify_url("https://www.instagram.com/p/CzPost9999/")
    assert c.kind == "post"
    assert is_reel(c, has_video_attachment=False) is False
    assert is_reel(c, has_video_attachment=True) is True


def test_extract_reel_urls_from_text_dedups():
    text = (
        "watch https://instagram.com/reel/AAAA11111/ and "
        "again https://www.instagram.com/reel/AAAA11111/?x=1 plus "
        "profile https://instagram.com/someone/"
    )
    found = extract_reel_urls(text)
    assert len(found) == 1
    assert found[0].normalized == canonical_reel_url("AAAA11111")


def test_trailing_punctuation_is_stripped():
    c = classify_url("https://www.instagram.com/reel/CzAbc12345X/).")
    assert c.shortcode == "CzAbc12345X"
