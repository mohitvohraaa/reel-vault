"""Shared enums and constants for the processing pipeline."""
from __future__ import annotations

try:  # StrEnum is stdlib on Python 3.11+
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python 3.10 fallback
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore[no-redef]
        def __str__(self) -> str:  # match 3.11 StrEnum behavior
            return str(self.value)


class ProcessingStatus(StrEnum):
    # Happy-path progression
    DISCOVERED = "discovered"
    METADATA_EXTRACTED = "metadata_extracted"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    # Failure / terminal-ish states (a reel stays useful in these states)
    MEDIA_UNAVAILABLE = "media_unavailable"
    TRANSCRIPTION_FAILED = "transcription_failed"
    SUMMARIZATION_FAILED = "summarization_failed"
    EMBEDDING_FAILED = "embedding_failed"
    INSUFFICIENT_CONTENT = "insufficient_content"


# Statuses that represent a failure a user may retry.
RETRYABLE_STATUSES = {
    ProcessingStatus.MEDIA_UNAVAILABLE,
    ProcessingStatus.TRANSCRIPTION_FAILED,
    ProcessingStatus.SUMMARIZATION_FAILED,
    ProcessingStatus.EMBEDDING_FAILED,
    ProcessingStatus.INSUFFICIENT_CONTENT,
}

# Statuses considered "pending / in-flight" for stats.
PENDING_STATUSES = {
    ProcessingStatus.DISCOVERED,
    ProcessingStatus.METADATA_EXTRACTED,
    ProcessingStatus.DOWNLOADING,
    ProcessingStatus.TRANSCRIBING,
    ProcessingStatus.SUMMARIZING,
    ProcessingStatus.EMBEDDING,
}

FAILED_STATUSES = {
    ProcessingStatus.MEDIA_UNAVAILABLE,
    ProcessingStatus.TRANSCRIPTION_FAILED,
    ProcessingStatus.SUMMARIZATION_FAILED,
    ProcessingStatus.EMBEDDING_FAILED,
    ProcessingStatus.INSUFFICIENT_CONTENT,
}


class Stage(StrEnum):
    METADATA = "metadata"
    MEDIA = "media"
    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"
    EMBEDDING = "embedding"


class JobStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    IMPORTING = "importing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class KBSourceType(StrEnum):
    CONVERSATION = "conversation"
    COLLECTION = "collection"
    MANUAL = "manual"
    FILTER = "filter"


# Default taxonomy suggested to the LLM. Users can extend via the categories API.
DEFAULT_CATEGORIES = [
    "Technology",
    "Programming",
    "AI / Machine Learning",
    "Startups / Business",
    "Productivity",
    "Learning / Education",
    "Finance",
    "Fitness",
    "Travel",
    "Entertainment",
    "Lifestyle",
    "Interesting / Miscellaneous",
]

CONTENT_TYPES = [
    "tutorial",
    "explainer",
    "opinion",
    "news",
    "review",
    "demo",
    "story",
    "promotion",
    "other",
]

IMPORTANCE_LEVELS = ["low", "medium", "high"]
