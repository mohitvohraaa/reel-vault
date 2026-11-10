"""Application configuration loaded from environment variables.

All configuration is environment-based. No secrets are hardcoded.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "ReelVault"
    environment: Literal["development", "production", "test"] = "development"
    debug: bool = True
    api_prefix: str = "/api"

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg://reelvault:reelvault@localhost:5432/reelvault",
        description="SQLAlchemy database URL (psycopg3 driver).",
    )

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- Storage ---
    upload_dir: str = "/data/uploads"
    media_dir: str = "/data/media"
    max_upload_mb: int = 500

    # --- Media retrieval ---
    media_download_enabled: bool = True
    media_download_timeout_sec: int = 120
    media_max_filesize_mb: int = 200
    ytdlp_format: str = "bv*[height<=720]+ba/b[height<=720]/b"
    # Optional path to a Netscape-format cookies.txt (your own Instagram session)
    # so yt-dlp can fetch reels that are login-walled for anonymous access.
    # This is NOT an API key — it is your own browser cookies. Leave unset to
    # fetch only fully-public reels. Only applied when the file exists.
    ytdlp_cookies_file: str | None = None

    # --- Transcription (faster-whisper) ---
    transcription_enabled: bool = True
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_beam_size: int = 5

    # --- LLM summarization ---
    # provider: "openai" | "gemini" | "stub"
    llm_provider: Literal["openai", "gemini", "stub"] = "stub"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_max_retries: int = 3
    llm_timeout_sec: int = 60

    # --- Embeddings (semantic search + RAG) ---
    # provider: "openai" | "gemini" | "stub"
    embedding_provider: Literal["openai", "gemini", "stub"] = "stub"
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_dim: int = 1536
    chunk_chars: int = 1200
    chunk_overlap: int = 150

    # --- Chat / RAG ---
    chat_top_k: int = 8
    chat_model: str | None = None  # falls back to llm_model when unset

    # --- Transcription speech threshold ---
    min_speech_words: int = 5
    min_speech_chars: int = 15

    # --- Pipeline behavior ---
    # When true, Celery tasks run; when false, pipeline can run inline (useful for tests).
    use_celery: bool = True

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
