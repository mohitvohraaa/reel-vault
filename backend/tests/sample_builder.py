"""Build a synthetic Instagram DM export for tests and the sample-data script.

The export deliberately includes the tricky cases the parser must handle:
- the ``share.link`` shape and inline-URL shape for shared reels
- duplicate reels (same shortcode shared twice)
- a non-reel profile link and a generic web link (must NOT be counted as reels)
- mojibake (double-encoded) text
- a malformed message_2.json part (must be skipped without crashing)
- a second, smaller conversation (so conversation selection matters)
"""
from __future__ import annotations

import json
from pathlib import Path


def _mojibake(text: str) -> str:
    """Encode text the way Instagram's export does (utf-8 bytes seen as latin-1)."""
    return text.encode("utf-8").decode("latin-1")


def _msg(sender, ts, *, content=None, share=None, videos=None):
    m = {"sender_name": sender, "timestamp_ms": ts}
    if content is not None:
        m["content"] = content
    if share is not None:
        m["share"] = share
    if videos is not None:
        m["videos"] = videos
    return m


def write_sample_export(root: Path) -> Path:
    root = Path(root)
    inbox = root / "your_instagram_activity" / "messages" / "inbox"

    # --- Conversation 1: the alt account (lots of reels) ---
    alt = inbox / "my_alt_account_17b2f9"
    alt.mkdir(parents=True, exist_ok=True)

    part1 = {
        "participants": [{"name": "my_alt_account"}, {"name": _mojibake("José Núñez")}],
        "title": _mojibake("my_alt_account"),
        "thread_path": "inbox/my_alt_account_17b2f9",
        "messages": [
            # share.link shape, with creator
            _msg("me", 1_700_000_100_000, share={
                "link": "https://www.instagram.com/reel/CzAbc12345X/",
                "share_text": _mojibake("Great AI agents explainer 🤖"),
                "original_content_owner": "ai_daily",
            }, videos=[{"uri": "media/v1.mp4"}]),
            # inline URL shape
            _msg("me", 1_700_000_200_000,
                 content="Check this python tip https://instagram.com/reel/CzPy67890Y/ so useful"),
            # duplicate of the first reel (different wrapping)
            _msg("me", 1_700_000_300_000, share={
                "link": "https://www.instagram.com/reel/CzAbc12345X/?igshid=abc",
                "original_content_owner": "ai_daily",
            }),
            # a /tv/ (IGTV) reel
            _msg("me", 1_700_000_400_000, share={
                "link": "https://www.instagram.com/tv/CzTvWxyz999/",
            }),
            # a non-reel profile link (must be ignored)
            _msg("me", 1_700_000_500_000, content="follow https://www.instagram.com/some_creator/"),
            # a generic non-instagram link (must be ignored)
            _msg("me", 1_700_000_600_000, content="read this https://example.com/article"),
            # plain text message (no reel)
            _msg(_mojibake("José Núñez"), 1_700_000_700_000, content=_mojibake("haha nice 😄")),
        ],
    }
    (alt / "message_1.json").write_text(json.dumps(part1), encoding="utf-8")

    # multi-part: a second file with one more reel
    part2 = {
        "participants": [{"name": "my_alt_account"}],
        "messages": [
            _msg("me", 1_700_000_800_000, share={
                "link": "https://www.instagram.com/reel/CzFitABC222/",
                "original_content_owner": "fitcoach",
            }),
        ],
    }
    (alt / "message_2.json").write_text(json.dumps(part2), encoding="utf-8")

    # --- Conversation 2: a friend (fewer reels) ---
    friend = inbox / "friend_chat_99aa11"
    friend.mkdir(parents=True, exist_ok=True)
    fjson = {
        "participants": [{"name": "friend"}, {"name": "me"}],
        "title": "friend",
        "messages": [
            _msg("friend", 1_700_000_050_000, content="hey"),
            _msg("me", 1_700_000_060_000, share={
                "link": "https://www.instagram.com/reel/CzTravel777/",
                "original_content_owner": "wanderlust",
            }),
        ],
    }
    (friend / "message_1.json").write_text(json.dumps(fjson), encoding="utf-8")

    # --- Conversation 3: malformed part (must be tolerated) ---
    broken = inbox / "broken_chat_000"
    broken.mkdir(parents=True, exist_ok=True)
    (broken / "message_1.json").write_text(
        json.dumps({"participants": [{"name": "x"}], "messages": [
            _msg("me", 1_700_000_900_000, share={"link": "https://www.instagram.com/reel/CzOkOne111/"}),
        ]}),
        encoding="utf-8",
    )
    (broken / "message_2.json").write_text("{ this is not valid json ", encoding="utf-8")

    return root


if __name__ == "__main__":  # manual smoke
    import tempfile

    out = write_sample_export(Path(tempfile.mkdtemp()))
    print("wrote sample export to", out)
