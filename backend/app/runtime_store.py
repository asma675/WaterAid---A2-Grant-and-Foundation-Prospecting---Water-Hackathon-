from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from .config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn():
    c = sqlite3.connect(settings.pipeline_db_path)
    c.row_factory = sqlite3.Row
    c.execute('''CREATE TABLE IF NOT EXISTS target_countries (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      country TEXT UNIQUE NOT NULL,
      region TEXT NOT NULL DEFAULT '',
      source TEXT NOT NULL DEFAULT 'User configured',
      source_url TEXT,
      active INTEGER NOT NULL DEFAULT 1,
      custom INTEGER NOT NULL DEFAULT 0,
      updated_at TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS country_tombstones (
      country TEXT PRIMARY KEY,
      removed_at TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS planning_settings (
      id INTEGER PRIMARY KEY CHECK(id=1),
      remaining_fundraising_hours REAL NOT NULL DEFAULT 45,
      blended_fundraising_cost REAL NOT NULL DEFAULT 63,
      program_cost REAL NOT NULL DEFAULT 65,
      default_win_probability REAL NOT NULL DEFAULT 0.30,
      default_owner TEXT NOT NULL DEFAULT 'Foundations Officer',
      default_due_days INTEGER NOT NULL DEFAULT 14,
      weekly_review_limit INTEGER NOT NULL DEFAULT 5,
      effort_json TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS brief_overrides (
      opportunity_id TEXT PRIMARY KEY,
      likely_ask_cad REAL,
      application_type TEXT,
      fundraising_hours REAL,
      program_hours REAL,
      win_probability REAL,
      owner TEXT,
      due_date TEXT,
      relationship_strength TEXT,
      relationship_consent TEXT,
      relationship_note TEXT,
      updated_at TEXT NOT NULL
    )''')
    # Lightweight schema migration for users upgrading an existing persistent volume.
    planning_cols={r[1] for r in c.execute("PRAGMA table_info(planning_settings)")}
    if "weekly_review_limit" not in planning_cols:
        c.execute("ALTER TABLE planning_settings ADD COLUMN weekly_review_limit INTEGER NOT NULL DEFAULT 5")
    c.execute('''CREATE TABLE IF NOT EXISTS data_issues (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      opportunity_id TEXT,
      page TEXT,
      description TEXT NOT NULL,
      source_url TEXT,
      status TEXT NOT NULL DEFAULT 'Open',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )''')
    return c


DEFAULT_EFFORT = {
    "Cultivation": {"fundraising_hours": 4, "program_hours": 0},
    "EOI": {"fundraising_hours": 12, "program_hours": 2},
    "LOI": {"fundraising_hours": 8, "program_hours": 0},
    "Short application": {"fundraising_hours": 24, "program_hours": 6},
    "Full proposal": {"fundraising_hours": 60, "program_hours": 20},
    "Government call": {"fundraising_hours": 220, "program_hours": 80},
    "Partnership concept": {"fundraising_hours": 16, "program_hours": 4},
}


def ensure_country_seed(seed_rows: list[dict[str, Any]]) -> None:
    with _conn() as c:
        existing = {r[0] for r in c.execute("SELECT country FROM target_countries")}
        removed = {r[0] for r in c.execute("SELECT country FROM country_tombstones")}
        now = _now()
        for row in seed_rows:
            country = str(row.get("country") or "").strip()
            if not country or country in existing or country in removed:
                continue
            c.execute(
                "INSERT INTO target_countries(country,region,source,source_url,active,custom,updated_at) VALUES(?,?,?,?,1,0,?)",
                (country, row.get("region") or "", row.get("source") or "WaterAid website", row.get("source_url"), now),
            )
        c.commit()


def list_countries(seed_rows: list[dict[str, Any]], include_inactive: bool = True) -> list[dict[str, Any]]:
    ensure_country_seed(seed_rows)
    with _conn() as c:
        sql = "SELECT * FROM target_countries"
        if not include_inactive:
            sql += " WHERE active=1"
        sql += " ORDER BY region, country"
        return [dict(r) for r in c.execute(sql)]


def active_country_names(seed_rows: list[dict[str, Any]]) -> set[str]:
    return {r["country"] for r in list_countries(seed_rows, include_inactive=False)}


def add_country(seed_rows: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    ensure_country_seed(seed_rows)
    country = str(payload.get("country") or "").strip()
    if not country:
        raise ValueError("country is required")
    now = _now()
    with _conn() as c:
        # Re-adding a previously removed baseline country is an explicit user choice.
        c.execute("DELETE FROM country_tombstones WHERE country=?", (country,))
        c.execute('''INSERT INTO target_countries(country,region,source,source_url,active,custom,updated_at)
          VALUES(?,?,?,?,?,?,?)
          ON CONFLICT(country) DO UPDATE SET region=excluded.region,source=excluded.source,
          source_url=excluded.source_url,active=excluded.active,custom=1,updated_at=excluded.updated_at''',
          (country, payload.get("region") or "Other", payload.get("source") or "User configured",
           payload.get("source_url"), 1 if payload.get("active", True) else 0, 1, now))
        c.commit()
        return dict(c.execute("SELECT * FROM target_countries WHERE country=?", (country,)).fetchone())


def patch_country(country_id: int, changes: dict[str, Any]) -> dict[str, Any] | None:
    valid = {k: v for k, v in changes.items() if v is not None and k in {"country","region","source","source_url","active"}}
    if not valid:
        return None
    if "active" in valid:
        valid["active"] = 1 if valid["active"] else 0
    valid["custom"] = 1
    valid["updated_at"] = _now()
    sets = ",".join(f"{k}=?" for k in valid)
    vals = list(valid.values()) + [country_id]
    with _conn() as c:
        c.execute(f"UPDATE target_countries SET {sets} WHERE id=?", vals)
        c.commit()
        row = c.execute("SELECT * FROM target_countries WHERE id=?", (country_id,)).fetchone()
        return dict(row) if row else None


def delete_country(country_id: int) -> bool:
    """Remove a country persistently, including baseline seed countries.

    Baseline countries would otherwise be re-seeded on the next request. A tombstone
    records the user's explicit removal. Re-adding the country through add_country()
    clears the tombstone.
    """
    with _conn() as c:
        row = c.execute("SELECT country FROM target_countries WHERE id=?", (country_id,)).fetchone()
        if not row:
            return False
        country = row[0]
        c.execute("INSERT OR REPLACE INTO country_tombstones(country,removed_at) VALUES(?,?)", (country, _now()))
        cur = c.execute("DELETE FROM target_countries WHERE id=?", (country_id,))
        c.commit()
        return cur.rowcount > 0


def _ensure_planning() -> None:
    with _conn() as c:
        row = c.execute("SELECT id FROM planning_settings WHERE id=1").fetchone()
        if not row:
            c.execute('''INSERT INTO planning_settings(id,remaining_fundraising_hours,blended_fundraising_cost,program_cost,
              default_win_probability,default_owner,default_due_days,weekly_review_limit,effort_json,updated_at)
              VALUES(1,45,63,65,0.30,'Foundations Officer',14,5,?,?)''',
              (json.dumps(DEFAULT_EFFORT), _now()))
            c.commit()


def get_planning() -> dict[str, Any]:
    _ensure_planning()
    with _conn() as c:
        row = dict(c.execute("SELECT * FROM planning_settings WHERE id=1").fetchone())
    row["effort"] = json.loads(row.pop("effort_json"))
    row["assumption_note"] = (
        "Demo planning defaults are seeded from the Water Challenge pack (for example 45 hours remaining and typical proposal effort). "
        "They are not WaterAid facts. Confirm or replace them in Scope & settings before operational use."
    )
    return row


def patch_planning(changes: dict[str, Any]) -> dict[str, Any]:
    _ensure_planning()
    valid = {k: v for k, v in changes.items() if v is not None and k in {
        "remaining_fundraising_hours","blended_fundraising_cost","program_cost","default_win_probability",
        "default_owner","default_due_days","weekly_review_limit"
    }}
    if changes.get("effort") is not None:
        valid["effort_json"] = json.dumps(changes["effort"])
    valid["updated_at"] = _now()
    sets = ",".join(f"{k}=?" for k in valid)
    vals = list(valid.values())
    with _conn() as c:
        c.execute(f"UPDATE planning_settings SET {sets} WHERE id=1", vals)
        c.commit()
    return get_planning()


def get_override(opportunity_id: str) -> dict[str, Any]:
    with _conn() as c:
        row = c.execute("SELECT * FROM brief_overrides WHERE opportunity_id=?", (opportunity_id,)).fetchone()
        return dict(row) if row else {}


def set_override(opportunity_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    fields = ["likely_ask_cad","application_type","fundraising_hours","program_hours","win_probability","owner","due_date",
              "relationship_strength","relationship_consent","relationship_note"]
    payload = {k: changes.get(k) for k in fields}
    payload.update({"opportunity_id": opportunity_id, "updated_at": _now()})
    with _conn() as c:
        c.execute('''INSERT INTO brief_overrides(opportunity_id,likely_ask_cad,application_type,fundraising_hours,program_hours,
          win_probability,owner,due_date,relationship_strength,relationship_consent,relationship_note,updated_at)
          VALUES(:opportunity_id,:likely_ask_cad,:application_type,:fundraising_hours,:program_hours,:win_probability,:owner,
          :due_date,:relationship_strength,:relationship_consent,:relationship_note,:updated_at)
          ON CONFLICT(opportunity_id) DO UPDATE SET likely_ask_cad=excluded.likely_ask_cad,
          application_type=excluded.application_type,fundraising_hours=excluded.fundraising_hours,program_hours=excluded.program_hours,
          win_probability=excluded.win_probability,owner=excluded.owner,due_date=excluded.due_date,
          relationship_strength=excluded.relationship_strength,relationship_consent=excluded.relationship_consent,
          relationship_note=excluded.relationship_note,updated_at=excluded.updated_at''', payload)
        c.commit()
    return get_override(opportunity_id)


def list_issues() -> list[dict[str, Any]]:
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM data_issues ORDER BY created_at DESC, id DESC")]


def add_issue(payload: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    data = {
        "opportunity_id": payload.get("opportunity_id"),
        "page": payload.get("page"),
        "description": str(payload.get("description") or "").strip(),
        "source_url": payload.get("source_url"),
        "status": payload.get("status") or "Open",
        "created_at": now,
        "updated_at": now,
    }
    if not data["description"]:
        raise ValueError("description is required")
    with _conn() as c:
        cur = c.execute('''INSERT INTO data_issues(opportunity_id,page,description,source_url,status,created_at,updated_at)
          VALUES(:opportunity_id,:page,:description,:source_url,:status,:created_at,:updated_at)''', data)
        c.commit()
        return dict(c.execute("SELECT * FROM data_issues WHERE id=?", (cur.lastrowid,)).fetchone())


def patch_issue(issue_id: int, changes: dict[str, Any]) -> dict[str, Any] | None:
    valid = {k: v for k, v in changes.items() if v is not None and k in {"description","source_url","status"}}
    if not valid:
        return None
    valid["updated_at"] = _now()
    sets = ",".join(f"{k}=?" for k in valid)
    vals = list(valid.values()) + [issue_id]
    with _conn() as c:
        c.execute(f"UPDATE data_issues SET {sets} WHERE id=?", vals)
        c.commit()
        row = c.execute("SELECT * FROM data_issues WHERE id=?", (issue_id,)).fetchone()
        return dict(row) if row else None
