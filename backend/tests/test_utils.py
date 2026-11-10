"""Timestamp parsing, mojibake repair and chunking tests."""
from __future__ import annotations

from datetime import timezone

from app.utils.text import chunk_text, fix_mojibake, word_count
from app.utils.time import ms_to_datetime


def test_ms_to_datetime_milliseconds():
    dt = ms_to_datetime(1_700_000_100_000)
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.year == 2023


def test_ms_to_datetime_seconds_and_invalid():
    assert ms_to_datetime(1_700_000_100).year == 2023  # seconds
    assert ms_to_datetime(None) is None
    assert ms_to_datetime("not-a-number") is None
    assert ms_to_datetime(0) is None


def test_fix_mojibake_roundtrip():
    original = "José Núñez 🤖"
    corrupted = original.encode("utf-8").decode("latin-1")
    assert corrupted != original
    assert fix_mojibake(corrupted) == original


def test_fix_mojibake_passthrough_on_plain_ascii():
    assert fix_mojibake("hello world") == "hello world"
    assert fix_mojibake(None) is None


def test_word_count():
    assert word_count("one two three") == 3
    assert word_count("") == 0
    assert word_count(None) == 0


def test_chunk_text_overlap():
    text = "sentence. " * 200  # ~2000 chars
    chunks = chunk_text(text, chunk_chars=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 600 for c in chunks)


def test_chunk_text_short_returns_single():
    assert chunk_text("short", 500, 50) == ["short"]
    assert chunk_text("", 500, 50) == []
