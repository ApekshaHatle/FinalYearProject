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
    
    # Query Metrics stats
    from backend.core.models import QueryMetrics
    total_queries = db.query(func.count(QueryMetrics.id)).scalar()
    avg_response_time = db.query(func.avg(QueryMetrics.response_time_ms)).scalar() or 0
    success_rate = db.query(func.count(QueryMetrics.id)).filter(QueryMetrics.success == True).scalar()
    
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
        "queries": {
            "total": total_queries,
            "avg_response_time_ms": round(avg_response_time, 2),
            "success_rate": round((success_rate / total_queries * 100), 2) if total_queries > 0 else 0
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

@router.get("/query-metrics")
def get_query_metrics(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent query metrics for analysis"""
    from backend.core.models import QueryMetrics
    
    metrics = db.query(QueryMetrics).order_by(
        QueryMetrics.created_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": m.id,
            "query": m.query,
            "response_time_ms": m.response_time_ms,
            "num_sources": m.num_sources,
            "model_used": m.model_used,
            "success": m.success,
            "created_at": m.created_at.isoformat()
        }
        for m in metrics
    ]

@router.get("/slow-queries")
def get_slow_queries(threshold_ms: int = 3000, db: Session = Depends(get_db)):
    """Get queries that took longer than threshold"""
    from backend.core.models import QueryMetrics
    
    slow_queries = db.query(QueryMetrics).filter(
        QueryMetrics.response_time_ms > threshold_ms
    ).order_by(QueryMetrics.response_time_ms.desc()).limit(20).all()
    
    return [
        {
            "query": q.query,
            "response_time_ms": q.response_time_ms,
            "num_sources": q.num_sources,
            "created_at": q.created_at.isoformat()
        }
        for q in slow_queries
    ]