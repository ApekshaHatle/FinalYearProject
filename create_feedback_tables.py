"""
create_feedback_tables.py
─────────────────────────
Run ONCE to create the two new tables in Supabase.

    python create_feedback_tables.py

Uses the same DATABASE_URL as the rest of your app (already set in .env).
All 3 laptops write to Supabase, so the learning data is automatically shared.
"""

import sys
import os

# Make sure backend package is importable when run from project root
sys.path.insert(0, os.path.dirname(__file__))

from backend.db.database import engine
from backend.core.models import Base           # existing tables
from backend.services.feedback_learning import FeedbackRecord, QueryClusterWeight

# SQLAlchemy will only CREATE tables that don't exist yet — safe to re-run
Base.metadata.create_all(bind=engine)

# Create our two new tables explicitly (they inherit from Base via the imports above)
from sqlalchemy import inspect
inspector = inspect(engine)
existing = inspector.get_table_names()

print("Tables in database:")
for t in sorted(existing):
    marker = "✅" if t in ("feedback_records", "query_cluster_weights") else "  "
    print(f"  {marker} {t}")

if "feedback_records" in existing and "query_cluster_weights" in existing:
    print("\n✅ Both feedback learning tables are ready.")
else:
    print("\n⚠️  Tables may not have been created — check DATABASE_URL in your .env")