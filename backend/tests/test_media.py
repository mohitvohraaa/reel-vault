"""Media retriever command-building tests (no network / no yt-dlp needed)."""
from __future__ import annotations

from app.services.media.retriever import MediaRetriever


def test_command_has_no_cookies_by_default():
    cmd = MediaRetriever.build_command("https://www.instagram.com/reel/X1/", "/tmp/audio.%(ext)s")
    assert "yt-dlp" in cmd[0]
    assert "--cookies" not in cmd
    assert cmd[-1] == "https://www.instagram.com/reel/X1/"
    assert "-x" in cmd and "mp3" in cmd  # audio-only extraction


def test_command_adds_cookies_when_file_exists(tmp_path, monkeypatch):
    cookie = tmp_path / "cookies.txt"
    cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    from app.core import config as config_mod

    monkeypatch.setattr(config_mod.settings, "ytdlp_cookies_file", str(cookie))
    # retriever reads settings via the module-level import
    import app.services.media.retriever as retriever_mod

    monkeypatch.setattr(retriever_mod.settings, "ytdlp_cookies_file", str(cookie))

    cmd = MediaRetriever.build_command("https://www.instagram.com/reel/X1/", "/tmp/audio.%(ext)s")
    assert "--cookies" in cmd
    assert str(cookie) in cmd


def test_command_skips_cookies_when_file_missing(monkeypatch):
    import app.services.media.retriever as retriever_mod

    monkeypatch.setattr(retriever_mod.settings, "ytdlp_cookies_file", "/nonexistent/cookies.txt")
    cmd = MediaRetriever.build_command("https://www.instagram.com/reel/X1/", "/tmp/audio.%(ext)s")
    assert "--cookies" not in cmd
