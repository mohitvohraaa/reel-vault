"""RAG chat endpoints over knowledge bases (or the whole vault)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.knowledge_base import KnowledgeBase
from app.schemas.chat import (
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    ChatSessionDetail,
    ChatSessionOut,
)
from app.services.chat.rag import answer as rag_answer

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    if not payload.query.strip():
        raise HTTPException(400, "query must not be empty")

    kb = None
    if payload.knowledge_base_id is not None:
        kb = db.get(KnowledgeBase, payload.knowledge_base_id)
        if kb is None:
            raise HTTPException(404, "Knowledge base not found")

    # Reuse or create a session.
    if payload.session_id is not None:
        session = db.get(ChatSession, payload.session_id)
        if session is None:
            raise HTTPException(404, "Chat session not found")
    else:
        session = ChatSession(
            knowledge_base_id=kb.id if kb else None,
            title=payload.query[:80],
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.query))
    db.commit()

    result = rag_answer(db, kb=kb, query=payload.query)
    assistant = ChatMessage(
        session_id=session.id, role="assistant", content=result.content, citations=result.citations
    )
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return ChatResponse(session_id=session.id, answer=ChatMessageOut.model_validate(assistant))


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(db: Session = Depends(get_db)):
    return db.scalars(select(ChatSession).order_by(ChatSession.id.desc())).all()


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(404, "Chat session not found")
    return session
