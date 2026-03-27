"""
feedback_learning.py
─────────────────────
Adaptive confidence learning system.

Stores in Supabase (shared across ALL laptops on Tailscale).
Learns from:
  - Similarity score (ChromaDB cosine distance → confidence)
  - User feedback (👍 = 1, 👎 = -1)

The learning part:
  - Maintains a per-query-pattern "trust weight" using exponential moving average
  - Adjusts future confidence scores based on historical feedback
  - Detects query clusters that consistently perform well/poorly
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
import uuid
import math
from typing import Optional, Dict, List
from backend.db.database import Base


# ── SQLAlchemy Models (go into Supabase via existing DATABASE_URL) ────────────

class FeedbackRecord(Base):
    """
    Every query that gets a response stores a record here.
    Feedback (thumbs) is updated post-response.
    Confidence is computed from ChromaDB similarity scores.
    """
    __tablename__ = "feedback_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to existing tables
    message_id = Column(UUID(as_uuid=True), nullable=True)   # → messages.id
    user_id    = Column(UUID(as_uuid=True), nullable=True)   # → users.id
    
    # Query info
    query          = Column(Text, nullable=False)
    query_keywords = Column(JSON, default=list)   # top 5 words for clustering
    db_scope       = Column(String(20), default="local")   # "local" | "shared"
    
    # Confidence (computed from ChromaDB similarity)
    raw_similarity_scores = Column(JSON, default=list)   # list of floats [0..1]
    confidence_score      = Column(Float, default=0.0)   # 0.0 – 1.0
    confidence_label      = Column(String(10), default="low")  # high/medium/low
    num_sources           = Column(Integer, default=0)
    
    # User feedback
    feedback        = Column(Integer, default=0)   # 0=none, 1=👍, -1=👎
    feedback_at     = Column(DateTime(timezone=True), nullable=True)
    
    # Learned weight (updated by learning loop)
    trust_weight = Column(Float, default=1.0)   # multiplier for future confidence
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QueryClusterWeight(Base):
    """
    Per-keyword-cluster learned trust weights.
    Updated each time feedback arrives on a matching query.
    Shared in Supabase → all laptops benefit from each other's feedback.
    """
    __tablename__ = "query_cluster_weights"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword     = Column(String(100), unique=True, nullable=False, index=True)
    
    # Exponential moving average of feedback signal
    ema_signal  = Column(Float, default=0.0)     # range roughly -1..+1
    sample_count = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ── Pure functions (no DB dependency) ─────────────────────────────────────────

def compute_confidence(similarity_scores: List[float], num_sources: int) -> Dict:
    """
    Derive a confidence score from ChromaDB similarity scores.
    
    similarity_scores: list of floats already in [0, 1] (cosine similarity,
        normalized so 1 = perfect match). ChromaDB returns distance [0,2] for
        non-normalised embeddings; the RAG service uses normalize_embeddings=True
        so the scores already live in [0,1].
    
    Returns:
        {
          "score": 0.73,            # 0..1
          "label": "medium",        # "high" / "medium" / "low"
          "top_score": 0.85,
          "avg_score": 0.73,
        }
    """
    if not similarity_scores or num_sources == 0:
        return {"score": 0.0, "label": "low", "top_score": 0.0, "avg_score": 0.0}

    scores = [max(0.0, min(1.0, s)) for s in similarity_scores]
    top   = scores[0]
    avg   = sum(scores) / len(scores)

    # Weighted: top score matters more than average
    raw = 0.6 * top + 0.4 * avg

    # Penalise very few sources (1 source → 80 % of raw score)
    source_factor = 1.0 - 0.2 * math.exp(-0.5 * (num_sources - 1))
    score = round(raw * source_factor, 4)

    if score >= 0.70:
        label = "high"
    elif score >= 0.45:
        label = "medium"
    else:
        label = "low"

    return {
        "score": score,
        "label": label,
        "top_score": round(top, 4),
        "avg_score": round(avg, 4),
    }


def extract_keywords(query: str, n: int = 5) -> List[str]:
    """
    Naive keyword extractor — removes stopwords, returns top-n tokens.
    No NLTK dependency; works offline.
    """
    STOP = {
        "a","an","the","is","it","in","on","at","to","for","of","and","or",
        "what","how","why","when","where","who","which","does","do","can",
        "i","my","me","we","our","you","your","be","been","was","are","were",
        "with","this","that","these","those","from","about","please","help",
    }
    tokens = query.lower().split()
    keywords = [t.strip("?.,!;:") for t in tokens if t not in STOP and len(t) > 2]
    return keywords[:n]


_EMA_ALPHA = 0.3   # learning rate for exponential moving average


def _ema_update(current: float, new_signal: float) -> float:
    """
    Exponential moving average update.
    current: existing EMA value
    new_signal: latest observation (+1 positive, -1 negative)
    """
    return _EMA_ALPHA * new_signal + (1 - _EMA_ALPHA) * current


def apply_trust_weight(confidence: float, trust_weight: float) -> float:
    """
    Adjust confidence score using the learned trust weight.
    trust_weight > 1 → boost confidence  (historically accurate cluster)
    trust_weight < 1 → dampen confidence (historically unreliable cluster)
    Result is clamped to [0, 1].
    """
    adjusted = confidence * trust_weight
    return round(max(0.0, min(1.0, adjusted)), 4)


# ── Service class (DB operations) ─────────────────────────────────────────────

class FeedbackLearningService:
    """
    Call this from chat.py after every RAG response:
      record = await fl_service.record_response(...)
    
    Call when user submits feedback:
      await fl_service.apply_feedback(record_id, vote)
    """

    # ── record a new response ─────────────────────────────────────────────────

    def record_response(
        self,
        db: Session,
        query: str,
        similarity_scores: List[float],
        num_sources: int,
        message_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        db_scope: str = "local",
    ) -> FeedbackRecord:
        """
        Save a FeedbackRecord for this response.
        Confidence is computed here; trust weight is looked up from cluster history.
        Returns the saved record (caller gets the id to send to frontend).
        """
        conf = compute_confidence(similarity_scores, num_sources)
        keywords = extract_keywords(query)

        # Look up average cluster trust for these keywords
        cluster_trust = self._get_cluster_trust(db, keywords)
        adjusted_conf = apply_trust_weight(conf["score"], cluster_trust)

        # Re-label after adjustment
        if adjusted_conf >= 0.70:
            label = "high"
        elif adjusted_conf >= 0.45:
            label = "medium"
        else:
            label = "low"

        record = FeedbackRecord(
            message_id=message_id,
            user_id=user_id,
            query=query,
            query_keywords=keywords,
            db_scope=db_scope,
            raw_similarity_scores=similarity_scores,
            confidence_score=adjusted_conf,
            confidence_label=label,
            num_sources=num_sources,
            trust_weight=cluster_trust,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    # ── apply user feedback ───────────────────────────────────────────────────

    def apply_feedback(
        self,
        db: Session,
        record_id: uuid.UUID,
        vote: int,           # +1 or -1
    ) -> Optional[FeedbackRecord]:
        """
        Store feedback on the record and update cluster weights.
        vote: 1 = thumbs up, -1 = thumbs down
        """
        record = db.query(FeedbackRecord).filter(FeedbackRecord.id == record_id).first()
        if not record:
            return None

        record.feedback = vote
        record.feedback_at = func.now()
        db.commit()

        # Update cluster weights for each keyword in this query
        self._update_cluster_weights(db, record.query_keywords or [], vote)

        return record

    # ── learning: get trust for a set of keywords ─────────────────────────────

    def _get_cluster_trust(self, db: Session, keywords: List[str]) -> float:
        """
        Average EMA signal for given keywords → map to trust multiplier [0.5, 1.5].
        No data = neutral trust = 1.0.
        """
        if not keywords:
            return 1.0

        rows = db.query(QueryClusterWeight).filter(
            QueryClusterWeight.keyword.in_(keywords)
        ).all()

        if not rows:
            return 1.0

        avg_ema = sum(r.ema_signal for r in rows) / len(rows)
        # Map [-1, +1] → [0.5, 1.5]
        trust = 1.0 + 0.5 * avg_ema
        return round(max(0.5, min(1.5, trust)), 4)

    # ── learning: update weights after feedback ───────────────────────────────

    def _update_cluster_weights(
        self, db: Session, keywords: List[str], vote: int
    ) -> None:
        """
        For each keyword, update (or create) its EMA signal with the new vote.
        This is the ML "learning" step — runs on every feedback submission.
        """
        for kw in keywords:
            row = db.query(QueryClusterWeight).filter(
                QueryClusterWeight.keyword == kw
            ).first()

            if row is None:
                row = QueryClusterWeight(
                    keyword=kw,
                    ema_signal=float(vote),
                    sample_count=1,
                )
                db.add(row)
            else:
                row.ema_signal = _ema_update(row.ema_signal, float(vote))
                row.sample_count += 1

        db.commit()

    # ── analytics ─────────────────────────────────────────────────────────────

    def get_learning_summary(self, db: Session) -> Dict:
        """Dashboard: how well is the system learning?"""
        total    = db.query(FeedbackRecord).count()
        with_fb  = db.query(FeedbackRecord).filter(FeedbackRecord.feedback != 0).count()
        positive = db.query(FeedbackRecord).filter(FeedbackRecord.feedback == 1).count()
        negative = db.query(FeedbackRecord).filter(FeedbackRecord.feedback == -1).count()

        clusters = db.query(QueryClusterWeight).order_by(
            QueryClusterWeight.ema_signal.desc()
        ).limit(10).all()

        avg_conf = db.query(func.avg(FeedbackRecord.confidence_score)).scalar() or 0.0

        return {
            "total_responses": total,
            "feedback_received": with_fb,
            "feedback_rate_pct": round(with_fb / total * 100, 1) if total else 0,
            "positive_feedback": positive,
            "negative_feedback": negative,
            "avg_confidence": round(float(avg_conf), 3),
            "top_trusted_keywords": [
                {"keyword": r.keyword, "ema": round(r.ema_signal, 3), "samples": r.sample_count}
                for r in clusters if r.ema_signal > 0
            ],
            "least_trusted_keywords": [
                {"keyword": r.keyword, "ema": round(r.ema_signal, 3), "samples": r.sample_count}
                for r in reversed(clusters) if r.ema_signal < 0
            ],
        }


# Singleton
fl_service = FeedbackLearningService()