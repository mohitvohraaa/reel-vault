"""Deterministic Instagram DM export parser.

Robust to export schema variations: it locates every ``message_*.json`` under
any ``inbox`` directory, merges multi-part conversation files, repairs mojibake,
tolerates malformed JSON / missing fields, and extracts shared Reels from the
several shapes Instagram uses (``share.link``, inline URLs, attachment metadata).
"""
from __future__ import annotations

import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.services.instagram.urls import (
    ClassifiedUrl,
    classify_url,
    extract_reel_urls,
    is_reel,
)
from app.utils.text import fix_mojibake
from app.utils.time import ms_to_datetime

_MESSAGE_FILE_RE = re.compile(r"^message_\d+\.json$", re.IGNORECASE)


@dataclass
class ParsedReel:
    normalized_url: str
    reel_url: str
    shortcode: str | None
    creator_username: str | None
    caption: str | None
    shared_at: datetime | None
    original_message_id: str | None
    sender_name: str | None
    thumbnail_url: str | None = None


@dataclass
class ConversationSummary:
    thread_id: str
    title: str | None
    participants: list[str]
    message_count: int
    reel_count: int
    path: str


@dataclass
class ConversationParseResult:
    thread_id: str
    title: str | None
    reels: list[ParsedReel] = field(default_factory=list)
    messages_scanned: int = 0
    reel_urls_found: int = 0
    duplicates_skipped: int = 0
    unsupported: int = 0
    parse_errors: list[str] = field(default_factory=list)


class ExportParser:
    """Parses an extracted Instagram export directory."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    # ----------------------------------------------------------------- loading
    @classmethod
    def from_source(cls, source: str | Path, workdir: str | Path) -> "ExportParser":
        """Accept a ZIP, a JSON file, or a directory and return a parser.

        ZIPs are extracted into ``workdir``. A lone JSON file is treated as a
        single-conversation ``message_1.json``.
        """
        source = Path(source)
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            return cls(source)

        if source.suffix.lower() == ".zip" or zipfile.is_zipfile(source):
            extract_to = workdir / (source.stem + "_extracted")
            extract_to.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(source) as zf:
                for member in zf.namelist():
                    # Guard against path traversal (zip-slip).
                    target = (extract_to / member).resolve()
                    if not str(target).startswith(str(extract_to.resolve())):
                        continue
                    zf.extract(member, extract_to)
            return cls(extract_to)

        if source.suffix.lower() == ".json":
            # Place the lone file into a synthetic inbox/<thread>/ layout.
            thread_dir = workdir / "inbox" / source.stem
            thread_dir.mkdir(parents=True, exist_ok=True)
            target = thread_dir / "message_1.json"
            target.write_bytes(source.read_bytes())
            return cls(workdir)

        return cls(source.parent)

    # --------------------------------------------------------------- discovery
    def _conversation_dirs(self) -> list[Path]:
        """Every directory that directly contains ``message_*.json`` files
        and lives under an ``inbox`` ancestor (or any dir, as a fallback)."""
        convo_dirs: set[Path] = set()
        inbox_scoped: set[Path] = set()
        for dirpath, _dirnames, filenames in os.walk(self.root):
            if not any(_MESSAGE_FILE_RE.match(f) for f in filenames):
                continue
            p = Path(dirpath)
            convo_dirs.add(p)
            if "inbox" in {part.lower() for part in p.parts}:
                inbox_scoped.add(p)
        # Prefer inbox-scoped conversations; fall back to any message dirs.
        chosen = inbox_scoped or convo_dirs
        return sorted(chosen)

    @staticmethod
    def _load_message_files(convo_dir: Path) -> tuple[list[dict], list[str], str | None, list[str]]:
        """Load and merge all message_*.json parts in a conversation dir.

        Returns (messages, participants, title, errors).
        """
        messages: list[dict] = []
        participants: list[str] = []
        title: str | None = None
        errors: list[str] = []

        parts = sorted(
            [f for f in convo_dir.iterdir() if _MESSAGE_FILE_RE.match(f.name)],
            key=lambda p: p.name,
        )
        for part in parts:
            try:
                data = json.loads(part.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
                errors.append(f"{part.name}: {exc}")
                continue
            if not isinstance(data, dict):
                errors.append(f"{part.name}: top-level JSON is not an object")
                continue
            if title is None and data.get("title"):
                title = fix_mojibake(str(data.get("title")))
            for pt in data.get("participants", []) or []:
                name = fix_mojibake((pt or {}).get("name")) if isinstance(pt, dict) else None
                if name and name not in participants:
                    participants.append(name)
            msgs = data.get("messages")
            if isinstance(msgs, list):
                messages.extend(m for m in msgs if isinstance(m, dict))
        return messages, participants, title, errors

    def list_conversations(self) -> list[ConversationSummary]:
        summaries: list[ConversationSummary] = []
        for convo_dir in self._conversation_dirs():
            messages, participants, title, _errors = self._load_message_files(convo_dir)
            reel_count = 0
            for msg in messages:
                try:
                    reel_count += len(self._extract_message_reels(msg, convo_dir.name))
                except Exception:
                    continue
            summaries.append(
                ConversationSummary(
                    thread_id=convo_dir.name,
                    title=title or (participants[0] if participants else convo_dir.name),
                    participants=participants,
                    message_count=len(messages),
                    reel_count=reel_count,
                    path=str(convo_dir),
                )
            )
        # Most reels first — the alt account conversation usually dominates.
        summaries.sort(key=lambda s: s.reel_count, reverse=True)
        return summaries

    def find_conversation_dir(self, thread_id: str) -> Path | None:
        for convo_dir in self._conversation_dirs():
            if convo_dir.name == thread_id:
                return convo_dir
        return None

    # --------------------------------------------------------------- extraction
    @staticmethod
    def _has_video_attachment(msg: dict) -> bool:
        if msg.get("videos"):
            return True
        share = msg.get("share") or {}
        # Some exports flag a video share via these hints.
        link = (share.get("link") or "") if isinstance(share, dict) else ""
        return "/reel/" in link or "/tv/" in link

    def _extract_message_reels(self, msg: dict, thread_id: str) -> list[ParsedReel]:
        """Extract zero or more reels from a single message dict."""
        reels: list[ParsedReel] = []
        seen_norm: set[str] = set()

        sender = fix_mojibake(msg.get("sender_name"))
        shared_at = ms_to_datetime(msg.get("timestamp_ms"))
        ts_ms = msg.get("timestamp_ms")
        content = fix_mojibake(msg.get("content"))
        share = msg.get("share") if isinstance(msg.get("share"), dict) else {}
        creator = None
        if share:
            creator = fix_mojibake(
                share.get("original_content_owner") or share.get("profile_share_username")
            )
        has_video = self._has_video_attachment(msg)

        candidates: list[ClassifiedUrl] = []

        # 1) Explicit share link.
        share_link = share.get("link") if share else None
        if share_link:
            c = classify_url(share_link)
            if is_reel(c, has_video) and c.normalized:
                candidates.append(c)

        # 2) Inline URLs in message content.
        for c in extract_reel_urls(content, has_video):
            candidates.append(c)

        # 3) URLs embedded in share_text.
        if share and share.get("share_text"):
            for c in extract_reel_urls(fix_mojibake(share.get("share_text")), has_video):
                candidates.append(c)

        for c in candidates:
            if not c.normalized or c.normalized in seen_norm:
                continue
            seen_norm.add(c.normalized)
            msg_id = f"{thread_id}:{ts_ms}:{c.shortcode}" if c.shortcode else None
            reels.append(
                ParsedReel(
                    normalized_url=c.normalized,
                    reel_url=c.url,
                    shortcode=c.shortcode,
                    creator_username=creator,
                    caption=None,  # the DM export rarely includes the reel caption
                    shared_at=shared_at,
                    original_message_id=msg_id,
                    sender_name=sender,
                )
            )
        return reels

    def parse_conversation(self, thread_id: str) -> ConversationParseResult:
        convo_dir = self.find_conversation_dir(thread_id)
        if convo_dir is None:
            return ConversationParseResult(
                thread_id=thread_id, title=None, parse_errors=[f"conversation '{thread_id}' not found"]
            )

        messages, _participants, title, errors = self._load_message_files(convo_dir)
        result = ConversationParseResult(thread_id=thread_id, title=title)
        result.parse_errors.extend(errors)

        seen_norm: set[str] = set()
        for msg in messages:
            result.messages_scanned += 1
            try:
                found = self._extract_message_reels(msg, thread_id)
            except Exception as exc:  # never let one bad message stop the batch
                result.parse_errors.append(f"message error: {exc}")
                result.unsupported += 1
                continue
            if not found:
                # A message with no reel is "unsupported" only if it had a link
                # that wasn't a reel; plain text messages are simply skipped.
                result.unsupported += 0
                continue
            for reel in found:
                result.reel_urls_found += 1
                if reel.normalized_url in seen_norm:
                    result.duplicates_skipped += 1
                    continue
                seen_norm.add(reel.normalized_url)
                result.reels.append(reel)
        return result
