"""Chat/Query endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import time
from backend.db.database import get_db
from backend.core.models import ChatSession, Message
from backend.services.ollama_service import ollama_service
from backend.services.rag_service import rag_service

router = APIRouter()

# Schemas
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    use_rag: bool = True
    stream: bool = False

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    session_id: str
    response_time_ms: int

class SessionResponse(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: str

@router.post("/query", response_model=ChatResponse)
async def chat_query(request: ChatRequest, db: Session = Depends(get_db)):
    """Main chat endpoint with RAG"""
    start_time = time.time()
    
    # Get or create session
    if request.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(title=request.query[:50])
        db.add(session)
        db.commit()
        db.refresh(session)
    
    # Save user message
    user_message = Message(
        session_id=session.id,
        role="user",
        content=request.query
    )
    db.add(user_message)
    db.commit()
    
    # RAG retrieval
    sources = []
    context_docs = []
    
    if request.use_rag and rag_service.is_initialized:
        search_results = await rag_service.search(query=request.query, k=5)
        
        if search_results:
            context_docs = [result["content"] for result in search_results]
            sources = [
                {
                    "content": result["content"][:200] + "...",
                    "source": result["source"],
                    "document_id": result["metadata"].get("document_id")
                }
                for result in search_results
            ]
    
    # Get chat history
    chat_history = db.query(Message).filter(
        Message.session_id == session.id
    ).order_by(Message.created_at.desc()).limit(10).all()
    
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(chat_history[1:])
    ]
    
    # Generate response
    if context_docs:
        answer = await ollama_service.generate_with_context(
            question=request.query,
            context=context_docs,
            chat_history=history
        )
    else:
        answer = await ollama_service.generate(
            prompt=request.query,
            system_prompt="You are a helpful coding assistant.",
            temperature=0.7
        )
    
    response_time = int((time.time() - start_time) * 1000)
    
    # Save assistant message
    assistant_message = Message(
        session_id=session.id,
        role="assistant",
        content=answer,
        sources=sources,
        response_time_ms=response_time
    )
    db.add(assistant_message)
    db.commit()
    
    return ChatResponse(
        answer=answer,
        sources=sources,
        session_id=session.id,
        response_time_ms=response_time
    )

@router.get("/sessions", response_model=List[SessionResponse])
def get_sessions(db: Session = Depends(get_db)):
    """Get all chat sessions"""
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).limit(20).all()
    
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
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    """Get messages for a session"""
    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at).all()
    
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "sources": msg.sources,
            "created_at": msg.created_at.isoformat()
        }
        for msg in messages
    ]

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a chat session"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    
    return {"message": "Session deleted"}

@router.post("/code/generate")
async def generate_code(
    description: str,
    language: str = "python"
):
    """Generate code snippet"""
    code = await ollama_service.generate_code(description, language)
    return {"code": code, "language": language}