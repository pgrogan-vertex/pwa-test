"""Print every row in habits.db. Run locally, or remotely via:
railway ssh --service pleasing-nurturing -- python3 < scripts/dump_habits.py
"""
import os
import sqlite3
from pathlib import Path

HABITS_DB = Path(os.environ.get("DATA_DIR", ".")) / "habits.db"

conn = sqlite3.connect(HABITS_DB)
cols = [d[0] for d in conn.execute("SELECT * FROM metric_entries").description]
print(f"{HABITS_DB} — columns: {cols}")
for row in conn.execute("SELECT * FROM metric_entries ORDER BY entry_date, metric_key").fetchall():
    print(tuple(row))
