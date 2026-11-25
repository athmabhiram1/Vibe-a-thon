"""Raw-SQL persistence for the HR directory service.

Reads the canonical 11-table seed schema (seed/schema.sql) in seed/demo.db.
aiosqlite + parameterized `?` placeholders only. No ORM (per research/verify/04-orm).

Column mapping (legacy service shape -> canonical columns):
  candidates: name <- full_name, team <- dept, status <- offer_status
  employees:  name <- full_name, email <- work_email, team <- dept,
              start_date <- join_date
  shifts:     canonical shifts(shift_id,name,start_time,end_time) + junction
              shift_members(shift_id,employee_id); legacy (team,employee_id,
              date,shift,on_call) is projected: team echoes the query arg,
              date echoes the queried day, shift is day|night derived from
              start/end_time, on_call is True for *OnCall shifts.

Signatures are stable: routers call list_candidates / get_candidate /
create_employee / shift_calendar / get_oncall unchanged.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path

import aiosqlite

_REPO = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("HR_DB_PATH", str(_REPO / "seed" / "demo.db"))
SCHEMA_SQL_PATH = _REPO / "seed" / "schema.sql"


@asynccontextmanager
async def _connect(db_path):
    """Open SQLite with WAL + busy-timeout (concurrent uvicorn demo safety)."""
    db = await aiosqlite.connect(db_path)
    try:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA busy_timeout=5000;")
        yield db
    finally:
        await db.close()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db(db_path: str | None = None) -> None:
    """Ensure the canonical schema exists. Seed owns data — no boot inserts here."""
    db_path = db_path or DB_PATH
    async with _connect(db_path) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='candidates'"
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            await db.executescript(SCHEMA_SQL_PATH.read_text(encoding="utf-8"))
            await db.commit()


async def list_candidates(
    team: str | None = None, limit: int = 20, db_path: str | None = None
) -> list[dict]:
    """SELECT candidates from the canonical table, optionally filtered by dept."""
    db_path = db_path or DB_PATH
    await init_db(db_path)
    async with _connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        if team:
            async with db.execute(
                "SELECT candidate_id, full_name AS name, email,"
                " dept AS team, offer_status AS status FROM candidates"
                " WHERE dept = ? LIMIT ?",
                (team, limit),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT candidate_id, full_name AS name, email,"
                " dept AS team, offer_status AS status FROM candidates"
                " LIMIT ?",
                (limit,),
            ) as cur:
                rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_candidate(candidate_id: str, db_path: str | None = None) -> dict | None:
    """SELECT one candidate by ID from the canonical table."""
    db_path = db_path or DB_PATH
    await init_db(db_path)
    async with _connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT candidate_id, full_name AS name, email,"
            " dept AS team, offer_status AS status FROM candidates"
            " WHERE candidate_id = ?",
            (candidate_id,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row is not None else None


async def create_employee(
    name: str,
    email: str,
    team: str,
    start_date: date,
    role: str = "engineer",
    db_path: str | None = None,
) -> dict:
    """INSERT one employee row; employee_id continues the EMP-NNN sequence."""
    db_path = db_path or DB_PATH
    await init_db(db_path)
    async with _connect(db_path) as db:
        async with db.execute(
            "SELECT MAX(CAST(SUBSTR(employee_id, 5) AS INTEGER)) FROM employees"
        ) as cur:
            row = await cur.fetchone()
        seq = (row[0] or 0) + 1
        employee_id = f"EMP-{seq:03d}"
        created_at = _utcnow_iso()
        await db.execute(
            "INSERT INTO employees"
            " (employee_id, full_name, work_email, dept, role,"
            " employment_type, status, join_date, created_at)"
            " VALUES (?, ?, ?, ?, ?, 'full_time', 'active', ?, ?)",
            (
                employee_id,
                name,
                email,
                team,
                role,
                start_date.isoformat(),
                created_at,
            ),
        )
        await db.commit()
    return {
        "employee_id": employee_id,
        "name": name,
        "email": email,
        "team": team,
        "start_date": start_date.isoformat(),
        "role": role,
        "created_at": created_at,
    }


async def shift_calendar(team: str, day: date, db_path: str | None = None) -> list[dict]:
    """SELECT roster rows for a team, projected onto the legacy Shift shape.

    Canonical roster = shifts x shift_members. A row belongs to `team` when
    the shift name matches or the member's dept matches.
    """
    db_path = db_path or DB_PATH
    await init_db(db_path)
    async with _connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT sm.employee_id AS employee_id, s.name AS shift_name,"
            " s.start_time AS start_time, s.end_time AS end_time"
            " FROM shift_members sm"
            " JOIN shifts s ON s.shift_id = sm.shift_id"
            " LEFT JOIN employees e ON e.employee_id = sm.employee_id"
            " WHERE s.name = ? OR e.dept = ?",
            (team, team),
        ) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        overnight = d["end_time"] <= d["start_time"]
        night_named = "night" in d["shift_name"].lower()
        shift_kind = "night" if (overnight or night_named) else "day"
        result.append(
            {
                "team": team,
                "employee_id": d["employee_id"],
                "date": day.isoformat(),
                "shift": shift_kind,
                "on_call": "oncall" in d["shift_name"].lower().replace("-", ""),
            }
        )
    return result


async def get_oncall(
    team: str, moment: datetime, db_path: str | None = None
) -> dict | None:
    """Resolve who is on call for a team at `moment` (raw SQL roster lookup).

    Prefers a shift row flagged on_call; falls back to the first roster
    row. Returns None when no roster exists.
    """
    db_path = db_path or DB_PATH
    rows = await shift_calendar(team=team, day=moment.date(), db_path=db_path)
    if not rows:
        return None
    pick = next((r for r in rows if r.get("on_call")), rows[0])
    await init_db(db_path)
    name = pick["employee_id"]
    email = f"{pick['employee_id']}@example.com"
    async with _connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT full_name AS name, work_email AS email FROM employees"
            " WHERE employee_id = ?",
            (pick["employee_id"],),
        ) as cur:
            emp = await cur.fetchone()
    if emp is not None:
        name = emp["name"]
        email = emp["email"]
    return {
        "team": team,
        "employee_id": pick["employee_id"],
        "name": name,
        "email": email,
        "at": moment.isoformat(),
    }
