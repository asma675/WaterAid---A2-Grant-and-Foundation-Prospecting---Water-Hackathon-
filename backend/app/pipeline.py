from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from .config import settings


def _conn():
    c=sqlite3.connect(settings.pipeline_db_path)
    c.row_factory=sqlite3.Row
    c.execute('''CREATE TABLE IF NOT EXISTS pipeline (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      opportunity_id TEXT UNIQUE NOT NULL,
      title TEXT NOT NULL,
      funder TEXT NOT NULL,
      stage TEXT NOT NULL,
      owner TEXT NOT NULL,
      deadline TEXT,
      amount TEXT,
      next_action TEXT,
      notes TEXT,
      updated_at TEXT NOT NULL
    )''')
    return c


def list_items():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM pipeline ORDER BY updated_at DESC, id DESC")]


def upsert(item: dict):
    now=datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute('''INSERT INTO pipeline(opportunity_id,title,funder,stage,owner,deadline,amount,next_action,notes,updated_at)
          VALUES(:opportunity_id,:title,:funder,:stage,:owner,:deadline,:amount,:next_action,:notes,:updated_at)
          ON CONFLICT(opportunity_id) DO UPDATE SET title=excluded.title,funder=excluded.funder,stage=excluded.stage,
          owner=excluded.owner,deadline=excluded.deadline,amount=excluded.amount,next_action=excluded.next_action,notes=excluded.notes,updated_at=excluded.updated_at''', {**item,"updated_at":now})
        c.commit()
        return dict(c.execute("SELECT * FROM pipeline WHERE opportunity_id=?",(item['opportunity_id'],)).fetchone())


def patch(item_id: int, changes: dict):
    valid={k:v for k,v in changes.items() if v is not None and k in {"stage","owner","deadline","amount","next_action","notes"}}
    if not valid: return None
    valid["updated_at"]=datetime.now(timezone.utc).isoformat()
    sets=",".join(f"{k}=?" for k in valid)
    vals=list(valid.values())+[item_id]
    with _conn() as c:
        c.execute(f"UPDATE pipeline SET {sets} WHERE id=?",vals); c.commit()
        row=c.execute("SELECT * FROM pipeline WHERE id=?",(item_id,)).fetchone()
        return dict(row) if row else None


def delete(item_id: int):
    with _conn() as c:
        cur=c.execute("DELETE FROM pipeline WHERE id=?",(item_id,)); c.commit(); return cur.rowcount>0
