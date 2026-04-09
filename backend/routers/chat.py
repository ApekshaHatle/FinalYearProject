"""Chat/Query endpoints — with confidence scoring + feedback learning"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Literal
from uuid import UUID
import time
from backend.db.database import get_db
from backend.core.models import ChatSession, Message
from backend.services.ollama_service import ollama_service
from backend.services.rag_manager import rag_manager
from backend.routers.auth import get_current_user
from backend.services.feedback_learning import fl_service, compute_confidence, FeedbackRecord

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[UUID] = None
    use_rag: bool = True
    stream: bool = False
    db_scope: Literal["local", "shared"] = "local"

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    session_id: UUID
    response_time_ms: int
    db_scope: str = "local"
    feedback_record_id: Optional[UUID] = None
    confidence: Optional[dict] = None

class SessionResponse(BaseModel):
    id: UUID
    title: str
    message_count: int
    created_at: str

class UpdateSessionRequest(BaseModel):
    title: str

class FeedbackRequest(BaseModel):
    record_id: UUID
    vote: Literal[1, -1]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    start_time = time.time()

    # ── DEBUG: confirm what scope and URL are being used ─────────────────────
    print(f"DEBUG scope received: '{request.db_scope}'")
    print(f"DEBUG rag_manager shared URL: {rag_manager._http.base_url}")

    # ── Session ───────────────────────────────────────────────────────────────
    if request.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(title=request.query[:50], user_id=current_user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

    # Save user message
    user_message = Message(
        session_id=session.id,
        role="user",
        content=request.query,
        db_scope=request.db_scope,
    )
    db.add(user_message)
    db.commit()

    # ── RAG retrieval ─────────────────────────────────────────────────────────
    sources = []
    context_docs = []
    raw_similarity_scores = []

    if request.use_rag:
        if request.db_scope == "local" and rag_manager.local.is_initialized:
            search_results = await rag_manager.search(query=request.query, k=5, scope="local")
        elif request.db_scope == "shared":
            search_results = await rag_manager.search(query=request.query, k=5, scope="shared")
        else:
            search_results = []

        # ── FIX 4: Filter out negative/zero relevance scores ─────────────────
        # Negative scores from ChromaDB mean the chunk is not relevant at all.
        # Passing them to the LLM as context causes wrong/hallucinated answers.
        if search_results:
            valid_results = [
                r for r in search_results
                if (r.get("relevance_score") is None or r.get("relevance_score", 0) > 0.0)
            ]
            print(f"DEBUG: {len(search_results)} results from '{request.db_scope}' scope, "
                  f"{len(valid_results)} passed score filter (score > 0.0)")
            search_results = valid_results

        if search_results:
            context_docs = [r["content"] for r in search_results]
            for r in search_results:
                score = r.get("relevance_score") or r.get("similarity_score")
                if score is not None:
                    raw_similarity_scores.append(float(score))
            sources = [
                {
                    "content": r["content"][:200] + "...",
                    "source": r.get("source", "unknown"),
                    "document_id": r.get("metadata", {}).get("document_id", "unknown"),
                    "relevance_score": r.get("relevance_score"),
                }
                for r in search_results
            ]

    # ── Confidence ────────────────────────────────────────────────────────────
    conf_data = compute_confidence(raw_similarity_scores, len(context_docs))

    # ── Generation ────────────────────────────────────────────────────────────
    success = True
    try:
        if context_docs:
            answer = await ollama_service.generate_with_context(
                question=request.query,
                context=context_docs,
                chat_history=_get_history(db, session.id),
                db_scope=request.db_scope,   # ← FIX: pass scope into cache key
            )
        else:
            # ── FIX 3: Tell the LLM not to hallucinate when shared returns nothing
            if request.db_scope == "shared":
                system_prompt = (
                    "You are a helpful assistant. "
                    "IMPORTANT: The shared team database returned no results for this query. "
                    "This may mean the shared RAG server is unreachable, or no relevant "
                    "documents exist for this question. "
                    "Do NOT answer from your own knowledge. Instead, tell the user that "
                    "no relevant shared documents were found and suggest they check "
                    "whether the correct documents have been uploaded to the shared database."
                )
            else:
                system_prompt = (
                    "You are a helpful coding assistant. "
                    "Note: No relevant documents were found in your personal database."
                )
            answer = await ollama_service.generate(
                prompt=request.query,
                system_prompt=system_prompt,
                temperature=0.7,
            )
    except Exception as e:
        success = False
        answer = f"Sorry, an error occurred: {str(e)}"

    response_time = int((time.time() - start_time) * 1000)

    # ── Save assistant message ────────────────────────────────────────────────
    assistant_message = Message(
        session_id=session.id,
        role="assistant",
        content=answer,
        sources=sources,
        response_time_ms=response_time,
        db_scope=request.db_scope,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    # ── QueryMetrics ──────────────────────────────────────────────────────────
    from backend.core.models import QueryMetrics
    metrics = QueryMetrics(
        message_id=assistant_message.id,
        query=request.query,
        response_time_ms=response_time,
        num_sources=len(sources),
        model_used=ollama_service.model,
        success=success,
    )
    db.add(metrics)
    db.commit()

    # ── FeedbackRecord ────────────────────────────────────────────────────────
    feedback_record = fl_service.record_response(
        db=db,
        query=request.query,
        similarity_scores=raw_similarity_scores,
        num_sources=len(context_docs),
        message_id=assistant_message.id,
        user_id=current_user.id,
        db_scope=request.db_scope,
    )

    assistant_message.feedback_record_id = feedback_record.id
    assistant_message.confidence_score   = feedback_record.confidence_score
    assistant_message.confidence_label   = feedback_record.confidence_label
    db.commit()

    return ChatResponse(
        answer=answer,
        sources=sources,
        session_id=session.id,
        response_time_ms=response_time,
        db_scope=request.db_scope,
        feedback_record_id=feedback_record.id,
        confidence={
            "score": feedback_record.confidence_score,
            "label": feedback_record.confidence_label,
            "top_source_score": conf_data.get("top_score"),
            "avg_source_score": conf_data.get("avg_score"),
        },
    )


# ── Feedback endpoint ─────────────────────────────────────────────────────────

@router.post("/feedback")
def submit_feedback(request, db, current_user):
    record = fl_service.apply_feedback(db, request.record_id, request.vote)
    if not record:
        raise HTTPException(status_code=404, detail="Feedback record not found")
    return {
        "message": "Feedback recorded.",
        "record_id": str(record.id),
        "vote": request.vote,
        "updated_confidence": record.confidence_score,
        "keywords_updated": record.query_keywords or [],
    }


# ── Session endpoints ─────────────────────────────────────────────────────────

@router.get("/sessions", response_model=List[SessionResponse])
def get_sessions(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.created_at.desc()).limit(20).all()

    result = []
    for session in sessions:
        message_count = db.query(Message).filter(Message.session_id == session.id).count()
        result.append({
            "id": session.id,
            "title": session.title,
            "message_count": message_count,
            "created_at": session.created_at.isoformat()
        })
    return result


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at).all()

    result = []
    for msg in messages:
        row = {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "sources": msg.sources,
            "response_time_ms": msg.response_time_ms,
            "created_at": msg.created_at.isoformat(),
            "db_scope": msg.db_scope or "local",
            "feedback_record_id": msg.feedback_record_id,
            "feedback_vote": msg.feedback_vote,
            "confidence": (
                {
                    "score": msg.confidence_score,
                    "label": msg.confidence_label,
                }
                if msg.confidence_score is not None
                else None
            ),
        }
        result.append(row)

    return result


@router.put("/sessions/{session_id}")
def update_session(
    session_id: UUID,
    request: UpdateSessionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = request.title
    db.commit()
    return {"message": "Session updated", "title": request.title}


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}


@router.post("/code/generate")
async def generate_code(description: str, language: str = "python"):
    code = await ollama_service.generate_code(description, language)
    return {"code": code, "language": language}


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_history(db: Session, session_id: UUID):
    chat_history = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at.desc()).limit(10).all()
    return [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(chat_history[1:])
    ]