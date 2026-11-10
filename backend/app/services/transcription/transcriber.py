"""Audio transcription via faster-whisper.

The model is lazy-loaded and cached. faster-whisper reads audio directly via
its bundled ffmpeg bindings, so we pass the downloaded audio file straight in.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("transcription")

_MODEL = None


@dataclass
class TranscriptResult:
    ok: bool
    text: str = ""
    language: str | None = None
    segments: list[dict] = field(default_factory=list)
    error: str | None = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel  # lazy import

        log.info("loading faster-whisper model=%s device=%s", settings.whisper_model, settings.whisper_device)
        _MODEL = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _MODEL


class Transcriber:
    def transcribe(self, audio_path: str) -> TranscriptResult:
        try:
            model = _get_model()
        except Exception as exc:  # faster-whisper or model unavailable
            log.exception("failed to load whisper model")
            return TranscriptResult(ok=False, error=f"model load failed: {exc}")

        try:
            segments_iter, info = model.transcribe(
                audio_path,
                beam_size=settings.whisper_beam_size,
                vad_filter=True,
            )
            segments: list[dict] = []
            parts: list[str] = []
            for seg in segments_iter:
                segments.append(
                    {"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()}
                )
                parts.append(seg.text.strip())
            text = " ".join(p for p in parts if p).strip()
            return TranscriptResult(
                ok=True,
                text=text,
                language=getattr(info, "language", None),
                segments=segments,
            )
        except Exception as exc:
            log.exception("transcription failed for %s", audio_path)
            return TranscriptResult(ok=False, error=str(exc))
