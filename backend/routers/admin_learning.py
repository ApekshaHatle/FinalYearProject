"""
admin_learning.py  ← ADD these routes to your existing admin.py router
─────────────────
New endpoints exposing the feedback-learning system to the admin dashboard.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from backend.db.database import get_db
from backend.services.feedback_learning import fl_service, FeedbackRecord, QueryClusterWeight
from backend.routers.auth import get_current_user   # or get_current_admin_user if you have it

router = APIRouter()


@router.get("/learning/summary")
def learning_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Overall learning health:
    - how many responses logged
    - feedback rate
    - top trusted / least trusted keyword clusters
    """
    return fl_service.get_learning_summary(db)


@router.get("/learning/confidence-distribution")
def confidence_distribution(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """How many responses fall into each confidence bucket."""
    high   = db.query(FeedbackRecord).filter(FeedbackRecord.confidence_label == "high").count()
    medium = db.query(FeedbackRecord).filter(FeedbackRecord.confidence_label == "medium").count()
    low    = db.query(FeedbackRecord).filter(FeedbackRecord.confidence_label == "low").count()
    total  = high + medium + low

    return {
        "high":   {"count": high,   "pct": round(high   / total * 100, 1) if total else 0},
        "medium": {"count": medium, "pct": round(medium / total * 100, 1) if total else 0},
        "low":    {"count": low,    "pct": round(low    / total * 100, 1) if total else 0},
        "total":  total,
    }


@router.get("/learning/feedback-vs-confidence")
def feedback_vs_confidence(
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Returns recent records with both confidence and feedback for scatter-plot.
    Useful to see whether high-confidence answers actually get 👍.
    """
    rows = (
        db.query(FeedbackRecord)
        .filter(FeedbackRecord.feedback != 0)
        .order_by(FeedbackRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "confidence_score": r.confidence_score,
            "confidence_label": r.confidence_label,
            "feedback": r.feedback,
            "num_sources": r.num_sources,
            "db_scope": r.db_scope,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/learning/cluster-weights")
def cluster_weights(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """All learned keyword trust weights, sorted by EMA signal."""
    rows = db.query(QueryClusterWeight).order_by(
        QueryClusterWeight.ema_signal.desc()
    ).all()
    return [
        {
            "keyword": r.keyword,
            "ema_signal": round(r.ema_signal, 4),
            "trust_multiplier": round(1.0 + 0.5 * r.ema_signal, 4),
            "sample_count": r.sample_count,
        }
        for r in rows
    ]


@router.get("/learning/recent-feedback")
def recent_feedback(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Recent feedback records for audit trail."""
    rows = (
        db.query(FeedbackRecord)
        .filter(FeedbackRecord.feedback != 0)
        .order_by(FeedbackRecord.feedback_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "query": r.query[:100] + ("..." if len(r.query) > 100 else ""),
            "confidence_score": r.confidence_score,
            "confidence_label": r.confidence_label,
            "feedback": "👍" if r.feedback == 1 else "👎",
            "trust_weight_used": r.trust_weight,
            "db_scope": r.db_scope,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]