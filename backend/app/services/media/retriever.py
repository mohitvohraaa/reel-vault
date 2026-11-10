"""Modular media retrieval.

Retrieves *publicly accessible* reel audio via yt-dlp (audio-only for speed).
Never attempts to bypass authentication or access private content. Private,
deleted, or sound-withheld reels fail cleanly and the reel is retained.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.files import ensure_dir, remove_quietly

log = get_logger("media")


@dataclass
class MediaResult:
    ok: bool
    media_path: str | None = None
    duration_sec: float | None = None
    error: str | None = None
    # "ok" | "disabled" | "unavailable" | "timeout" | "no_tool"
    reason: str = "ok"


def _ytdlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def _ffprobe_duration(path: Path) -> float | None:
    if shutil.which("ffprobe") is None:
        return None
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            ],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip())
    except (subprocess.SubprocessError, ValueError):
        return None


class MediaRetriever:
    def __init__(self, media_dir: str | None = None):
        self.media_dir = Path(media_dir or settings.media_dir)

    @staticmethod
    def build_command(normalized_url: str, out_template: str) -> list[str]:
        """Build the yt-dlp command. Adds ``--cookies`` only when a cookies file
        is configured and actually exists on disk."""
        cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "-x", "--audio-format", "mp3",
            "--no-playlist",
            "--no-warnings",
            "--socket-timeout", "30",
            "--max-filesize", f"{settings.media_max_filesize_mb}M",
        ]
        cookies = settings.ytdlp_cookies_file
        if cookies and os.path.exists(cookies):
            cmd += ["--cookies", cookies]
        cmd += ["-o", out_template, normalized_url]
        return cmd

    def retrieve_audio(self, normalized_url: str, shortcode: str | None) -> MediaResult:
        if not settings.media_download_enabled:
            return MediaResult(ok=False, reason="disabled", error="media download disabled")
        if not _ytdlp_available():
            return MediaResult(ok=False, reason="no_tool", error="yt-dlp not installed")

        key = shortcode or str(abs(hash(normalized_url)))
        out_dir = ensure_dir(self.media_dir / key)
        out_template = str(out_dir / "audio.%(ext)s")

        cmd = self.build_command(normalized_url, out_template)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.media_download_timeout_sec,
            )
        except subprocess.TimeoutExpired:
            remove_quietly(out_dir)
            return MediaResult(ok=False, reason="timeout", error="download timed out")
        except OSError as exc:  # pragma: no cover
            remove_quietly(out_dir)
            return MediaResult(ok=False, reason="unavailable", error=str(exc))

        if proc.returncode != 0:
            remove_quietly(out_dir)
            msg = (proc.stderr or "").strip().splitlines()
            tail = msg[-1] if msg else "download failed"
            # Private / deleted / login-required / sound-withheld all land here.
            return MediaResult(ok=False, reason="unavailable", error=tail[:500])

        audio_files = list(out_dir.glob("audio.*"))
        if not audio_files:
            remove_quietly(out_dir)
            return MediaResult(ok=False, reason="unavailable", error="no audio produced")

        media_path = audio_files[0]
        return MediaResult(
            ok=True,
            media_path=str(media_path),
            duration_sec=_ffprobe_duration(media_path),
            reason="ok",
        )

    @staticmethod
    def cleanup(media_path: str | None) -> None:
        """Remove downloaded media (called after processing when configured)."""
        if media_path:
            remove_quietly(Path(media_path).parent)
