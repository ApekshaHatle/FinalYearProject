"""Admin dashboard endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.database import get_db
from backend.core.models import User, Document, ChatSession, Message
from backend.services.rag_service import rag_service
from backend.services.ollama_service import ollama_service

router = APIRouter()

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    
    # User stats
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    
    # Document stats
    total_documents = db.query(func.count(Document.id)).scalar()
    completed_docs = db.query(func.count(Document.id)).filter(Document.status == "completed").scalar()
    
    # Chat stats
    total_sessions = db.query(func.count(ChatSession.id)).scalar()
    total_messages = db.query(func.count(Message.id)).scalar()
    
    # RAG stats
    rag_stats = {}
    if rag_service.is_initialized:
        rag_stats = rag_service.get_statistics()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "documents": {
            "total": total_documents,
            "completed": completed_docs,
            "processing": total_documents - completed_docs
        },
        "chat": {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_messages_per_session": round(total_messages / total_sessions, 2) if total_sessions > 0 else 0
        },
        "rag": rag_stats,
        "services": {
            "ollama": ollama_service.is_connected,
            "rag": rag_service.is_initialized
        }
    }

@router.get("/recent-activity")
def get_recent_activity(db: Session = Depends(get_db)):
    """Get recent system activity"""
    
    # Recent documents
    recent_docs = db.query(Document).order_by(Document.uploaded_at.desc()).limit(5).all()
    
    # Recent sessions
    recent_sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).limit(5).all()
    
    return {
        "recent_documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "status": doc.status,
                "uploaded_at": doc.uploaded_at.isoformat()
            }
            for doc in recent_docs
        ],
        "recent_sessions": [
            {
                "id": session.id,
                "title": session.title,
                "created_at": session.created_at.isoformat()
            }
            for session in recent_sessions
        ]
    }