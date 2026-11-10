"""Instagram export parser tests: discovery, selection, extraction, dedup,
mojibake, timestamps and malformed-file tolerance."""
from __future__ import annotations

from app.services.instagram.parser import ExportParser


def test_lists_conversations_sorted_by_reel_count(sample_export):
    parser = ExportParser(sample_export)
    convos = parser.list_conversations()
    thread_ids = [c.thread_id for c in convos]
    assert "my_alt_account_17b2f9" in thread_ids
    assert "friend_chat_99aa11" in thread_ids
    # The alt account has the most reels, so it sorts first.
    assert convos[0].thread_id == "my_alt_account_17b2f9"
    assert convos[0].reel_count >= 3


def test_participants_and_title_mojibake_repaired(sample_export):
    parser = ExportParser(sample_export)
    alt = next(c for c in parser.list_conversations() if c.thread_id == "my_alt_account_17b2f9")
    # The corrupted "José Núñez" participant must be repaired.
    assert any("José" in p for p in alt.participants)


def test_parse_conversation_extracts_unique_reels_and_dedups(sample_export):
    parser = ExportParser(sample_export)
    result = parser.parse_conversation("my_alt_account_17b2f9")
    norms = {r.normalized_url for r in result.reels}
    # Expected unique reels: CzAbc12345X, CzPy67890Y, CzTvWxyz999, CzFitABC222
    assert "https://www.instagram.com/reel/CzAbc12345X/" in norms
    assert "https://www.instagram.com/reel/CzPy67890Y/" in norms
    assert "https://www.instagram.com/reel/CzTvWxyz999/" in norms
    assert "https://www.instagram.com/reel/CzFitABC222/" in norms
    assert len(result.reels) == 4
    # The duplicate share of CzAbc12345X was counted and skipped.
    assert result.duplicates_skipped >= 1


def test_profile_and_generic_links_not_counted_as_reels(sample_export):
    parser = ExportParser(sample_export)
    result = parser.parse_conversation("my_alt_account_17b2f9")
    norms = {r.normalized_url for r in result.reels}
    assert not any("some_creator" in n for n in norms)
    assert not any("example.com" in n for n in norms)


def test_creator_and_timestamp_captured(sample_export):
    parser = ExportParser(sample_export)
    result = parser.parse_conversation("my_alt_account_17b2f9")
    reel = next(r for r in result.reels if r.shortcode == "CzAbc12345X")
    assert reel.creator_username == "ai_daily"
    assert reel.shared_at is not None
    assert reel.original_message_id is not None  # stable id for idempotency


def test_malformed_part_is_tolerated(sample_export):
    parser = ExportParser(sample_export)
    result = parser.parse_conversation("broken_chat_000")
    # The valid part yields one reel; the malformed part is recorded as an error.
    assert len(result.reels) == 1
    assert result.parse_errors  # the bad message_2.json was captured, not crashed


def test_missing_conversation_returns_error():
    import tempfile
    from pathlib import Path

    parser = ExportParser(Path(tempfile.mkdtemp()))
    result = parser.parse_conversation("does_not_exist")
    assert result.reels == []
    assert result.parse_errors


def test_from_source_handles_zip(sample_export, tmp_path):
    import shutil

    zip_base = tmp_path / "export"
    shutil.make_archive(str(zip_base), "zip", root_dir=sample_export)
    parser = ExportParser.from_source(str(zip_base) + ".zip", tmp_path / "work")
    convos = parser.list_conversations()
    assert any(c.thread_id == "my_alt_account_17b2f9" for c in convos)
