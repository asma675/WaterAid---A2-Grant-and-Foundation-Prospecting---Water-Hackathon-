from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from .config import settings


def _conn():
    c=sqlite3.connect(settings.pipeline_db_path)
    c.row_factory=sqlite3.Row
    c.execute('''CREATE TABLE IF NOT EXISTS decision_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      opportunity_id TEXT NOT NULL,
      system_decision TEXT NOT NULL,
      human_decision TEXT NOT NULL,
      reason TEXT,
      note TEXT,
      created_at TEXT NOT NULL
    )''')
    return c


def list_items():
    with _conn() as c:
        return [dict(r) for r in c.execute('SELECT * FROM decision_log ORDER BY created_at DESC, id DESC')]


def add(item: dict):
    now=datetime.now(timezone.utc).isoformat()
    payload={**item,'created_at':now}
    with _conn() as c:
        cur=c.execute('''INSERT INTO decision_log(opportunity_id,system_decision,human_decision,reason,note,created_at)
            VALUES(:opportunity_id,:system_decision,:human_decision,:reason,:note,:created_at)''',payload)
        c.commit()
        return dict(c.execute('SELECT * FROM decision_log WHERE id=?',(cur.lastrowid,)).fetchone())
