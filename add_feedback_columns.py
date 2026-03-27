"""
add_feedback_columns.py
────────────────────────
Run ONCE from the project root to:
  1. Add 5 new columns to the existing `messages` table
  2. Create `feedback_records` and `query_cluster_weights` tables (if not present)

    python add_feedback_columns.py

Safe to re-run — every ALTER uses IF NOT EXISTS, and create_all skips existing tables.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from backend.db.database import engine
from sqlalchemy import text, inspect

# Import ALL models so Base.metadata knows about every table
from backend.core.models import Base  # noqa: F401 — registers existing tables
from backend.services.feedback_learning import FeedbackRecord, QueryClusterWeight  # noqa: F401

# ── Step 1: Add new columns to messages ──────────────────────────────────────
NEW_COLUMNS = [
    ("db_scope",           "VARCHAR(20)  DEFAULT 'local'"),
    ("feedback_record_id", "UUID"),
    ("feedback_vote",      "INTEGER"),
    ("confidence_score",   "FLOAT"),
    ("confidence_label",   "VARCHAR(10)"),
]

print("── Step 1: Altering messages table ─────────────────────────────────────")
with engine.connect() as conn:
    for col_name, col_type in NEW_COLUMNS:
        try:
            conn.execute(text(
                f"ALTER TABLE messages ADD COLUMN IF NOT EXISTS {col_name} {col_type};"
            ))
            conn.commit()
            print(f"  ✅ messages.{col_name} ({col_type})")
        except Exception as e:
            print(f"  ⚠️  messages.{col_name} — {e}")

# ── Step 2: Create feedback_records + query_cluster_weights ──────────────────
print("\n── Step 2: Creating feedback learning tables ───────────────────────────")
Base.metadata.create_all(bind=engine)

# ── Step 3: Verify everything ─────────────────────────────────────────────────
print("\n── Step 3: Verification ────────────────────────────────────────────────")
inspector = inspect(engine)
all_tables = inspector.get_table_names()

# Check messages columns
msg_cols = {c["name"] for c in inspector.get_columns("messages")}
for col_name, _ in NEW_COLUMNS:
    status = "✅" if col_name in msg_cols else "❌ MISSING"
    print(f"  {status}  messages.{col_name}")

# Check new tables
for table in ("feedback_records", "query_cluster_weights"):
    status = "✅" if table in all_tables else "❌ MISSING"
    print(f"  {status}  table: {table}")

print("\nDone. Restart your FastAPI server to pick up the new model columns.")