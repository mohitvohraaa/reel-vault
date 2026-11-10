"""ORM models. Importing this package registers all tables on Base.metadata."""
from app.models.category import Category
from app.models.chat import ChatMessage, ChatSession
from app.models.collection import Collection, reel_collections
from app.models.ingestion_job import IngestionJob
from app.models.knowledge_base import KnowledgeBase, knowledge_base_reels
from app.models.pdf_template import PdfTemplate
from app.models.processing_log import ProcessingLog
from app.models.reel import Reel
from app.models.reel_chunk import ReelChunk

__all__ = [
    "Category",
    "ChatMessage",
    "ChatSession",
    "Collection",
    "reel_collections",
    "IngestionJob",
    "KnowledgeBase",
    "knowledge_base_reels",
    "PdfTemplate",
    "ProcessingLog",
    "Reel",
    "ReelChunk",
]
