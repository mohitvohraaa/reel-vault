"""Build the human-facing ingestion report."""
from __future__ import annotations

from app.services.instagram.parser import ConversationParseResult, ConversationSummary


def conversations_report(summaries: list[ConversationSummary]) -> dict:
    return {
        "total_conversations": len(summaries),
        "total_messages": sum(s.message_count for s in summaries),
        "total_reels_detected": sum(s.reel_count for s in summaries),
        "conversations": [
            {
                "thread_id": s.thread_id,
                "title": s.title,
                "participants": s.participants,
                "message_count": s.message_count,
                "reel_count": s.reel_count,
            }
            for s in summaries
        ],
    }


def import_report(result: ConversationParseResult, new_reels: int, existing_skipped: int) -> dict:
    return {
        "conversation": result.title,
        "thread_id": result.thread_id,
        "messages_scanned": result.messages_scanned,
        "reel_urls_discovered": result.reel_urls_found,
        "unique_reels_in_conversation": len(result.reels),
        "duplicates_skipped_within_conversation": result.duplicates_skipped,
        "already_in_vault_skipped": existing_skipped,
        "new_reels_imported": new_reels,
        "unsupported_messages": result.unsupported,
        "parse_errors": result.parse_errors,
    }
