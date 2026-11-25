"""SQLite-only demo storage (raw SQL + aiosqlite, no ORM per plan §9).

Reads the canonical 11-table seed schema (seed/schema.sql) in seed/demo.db.

Column mapping (legacy API shape -> canonical columns):
  equipment: serial <- asset_tag (keeps LT-XXXX ids incl. LT-1005/LT-1012 traps)
  tickets:   assignee_email <- employees.work_email via assignee_id,
             team <- assignee dept, deadline_at <- due_at,
             breached <- computed (due_at < now AND unresolved)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

_REPO = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("IT_DB_PATH", str(_REPO / "seed" / "demo.db")))
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

SLA_PRIORITY = {4: "P1", 8: "P2", 24: "P3"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(v: str) -> datetime:
    dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def init_db(db_path: str | Path | None = None) -> None:
    """Ensure the canonical schema exists. Seed owns data — no boot inserts here."""
    db_path = Path(db_path) if db_path else DB_PATH
    async with _connect(db_path) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='equipment'"
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            await db.executescript(SCHEMA_SQL_PATH.read_text(encoding="utf-8"))
            await db.commit()


def _ticket_from_row(r: dict, now: datetime) -> dict:
    due = _parse_ts(r["due_at"])
    breached = (
        r["status"] != "resolved" and r["resolved_at"] is None and due < now
    )
    return {
        "ticket_id": r["ticket_id"],
        "title": r["title"],
        "assignee_email": r["assignee_email"] or "",
        "team": r["team"] or "",
        "status": r["status"],
        "created_at": _parse_ts(r["created_at"]).isoformat(),
        "deadline_at": due.isoformat(),
        "breached": breached,
    }


_TICKET_SELECT = (
    "SELECT t.ticket_id AS ticket_id, t.title AS title,"
    " e.work_email AS assignee_email, e.dept AS team,"
    " t.status AS status, t.created_at AS created_at,"
    " t.due_at AS due_at, t.resolved_at AS resolved_at"
    " FROM tickets t LEFT JOIN employees e ON e.employee_id = t.assignee_id"
)


async def list_equipment(
    status: str | None = None,
    limit: int = 50,
    db_path: str | Path | None = None,
) -> list[dict]:
    """SELECT equipment rows; legacy `free` maps to canonical `available`."""
    db_path = Path(db_path) if db_path else DB_PATH
    await init_db(db_path)
    if status == "free":
        status = "available"
    async with _connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        if status is not None:
            async with db.execute(
                "SELECT asset_tag AS serial, model, status FROM equipment"
                " WHERE status = ? LIMIT ?",
                (status, limit),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT asset_tag AS serial, model, status FROM equipment LIMIT ?",
                (limit,),
            ) as cur:
                rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def assign_laptop(
    serial: str, employee_id: str, db_path: str | Path | None = None
) -> dict | None:
    """Assign an available asset. Returns None when equipment/employee missing.

    Raises ValueError on conflict (retired / already assigned / on hold),
    letting the router map to 409 with the canonical trap reason.
    """
    db_path = Path(db_path) if db_path else DB_PATH
    await init_db(db_path)
    now = _utcnow().isoformat()
    async with _connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT asset_tag, status FROM equipment WHERE asset_tag = ?",
            (serial,),
        ) as cur:
            item = await cur.fetchone()
        if item is None:
            return None
        async with db.execute(
            "SELECT employee_id FROM employees WHERE employee_id = ?",
            (employee_id,),
        ) as cur:
            emp = await cur.fetchone()
        if emp is None:
            return None
        st = item["status"]
        if st == "retired":
            raise ValueError("asset retired (LT-1012 trap): not assignable")
        if st == "assigned":
            raise ValueError("asset already assigned")
        if st == "on_hold":
            raise ValueError("hold_conflict: asset on hold for a candidate")
        if st != "available":
            raise ValueError(f"asset not assignable (status={st})")
        await db.execute(
            "UPDATE equipment SET status='assigned', assigned_to=?,"
            " hold_for_candidate=NULL WHERE asset_tag=?",
            (employee_id, serial),
        )
        await db.commit()
    return {"serial": serial, "employee_id": employee_id, "assigned_at": now}


async def create_ticket(
    title: str,
    assignee_email: str,
    team: str,
    sla_hours: int = 24,
    db_path: str | Path | None = None,
) -> dict | None:
    """INSERT a ticket; assignee resolved via work_email. Returns None if unknown."""
    db_path = Path(db_path) if db_path else DB_PATH
    await init_db(db_path)
    created = _utcnow()
    priority = SLA_PRIORITY.get(sla_hours, "P4")
    async with _connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT employee_id FROM employees WHERE lower(work_email)=lower(?)",
            (assignee_email,),
        ) as cur:
            emp = await cur.fetchone()
        if emp is None:
            return None
        assignee_id = emp["employee_id"]
        async with db.execute(
            "SELECT shift_id FROM shift_members WHERE employee_id=? LIMIT 1",
            (assignee_id,),
        ) as cur:
            sm = await cur.fetchone()
        shift_id = sm["shift_id"] if sm else "SH-01"
        async with db.execute("SELECT MAX(CAST(SUBSTR(ticket_id,3) AS INTEGER)) FROM tickets") as cur:
            row = await cur.fetchone()
        ticket_id = f"T-{(row[0] or 5000) + 1}"
        due = created + timedelta(hours=sla_hours)
        await db.execute(
            "INSERT INTO tickets (ticket_id,title,requester_id,assignee_id,"
            " priority,category,status,created_at,due_at,shift_id,channel)"
            " VALUES (?,?,?,?,?,'other','open',?,?,?,'portal')",
            (
                ticket_id,
                title,
                assignee_id,
                assignee_id,
                priority,
                created.isoformat(),
                due.isoformat(),
                shift_id,
            ),
        )
        await db.commit()
    return {
        "ticket_id": ticket_id,
        "title": title,
        "assignee_email": assignee_email,
        "team": team,
        "status": "open",
        "created_at": created.isoformat(),
        "deadline_at": due.isoformat(),
        "breached": False,
    }


async def get_ticket(
    ticket_id: str, db_path: str | Path | None = None
) -> dict | None:
    """SELECT one ticket with assignee email/dept joined. None when missing."""
    db_path = Path(db_path) if db_path else DB_PATH
    await init_db(db_path)
    async with _connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(_TICKET_SELECT + " WHERE t.ticket_id=?", (ticket_id,)) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    return _ticket_from_row(dict(row), _utcnow())


async def breach_list(
    team: str | None = None,
    since: datetime | None = None,
    db_path: str | Path | None = None,
) -> list[dict]:
    """Tickets past SLA and unresolved (pre-computed breach anti-join)."""
    db_path = Path(db_path) if db_path else DB_PATH
    await init_db(db_path)
    now = _utcnow()
    async with _connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(_TICKET_SELECT + " WHERE t.status<>'resolved'") as cur:
            rows = await cur.fetchall()
    items = [
        _ticket_from_row(dict(r), now)
        for r in rows
        if _parse_ts(dict(r)["due_at"]) < now
    ]
    if team is not None:
        items = [t for t in items if t["team"] == team]
    if since is not None:
        items = [t for t in items if _parse_ts(t["created_at"]) >= since]
    return items


async def reroute_ticket(
    ticket_id: str, to_email: str, db_path: str | Path | None = None
) -> dict | None:
    """Reassign a ticket to the on-call owner. None when ticket/email unknown."""
    db_path = Path(db_path) if db_path else DB_PATH
    await init_db(db_path)
    async with _connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT employee_id FROM employees WHERE lower(work_email)=lower(?)",
            (to_email,),
        ) as cur:
            emp = await cur.fetchone()
        if emp is None:
            return None
        await db.execute(
            "UPDATE tickets SET assignee_id=? WHERE ticket_id=?",
            (emp["employee_id"], ticket_id),
        )
        await db.commit()
        async with db.execute(_TICKET_SELECT + " WHERE t.ticket_id=?", (ticket_id,)) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    return _ticket_from_row(dict(row), _utcnow())
