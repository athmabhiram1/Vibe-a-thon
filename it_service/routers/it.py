# it_service/routers/it.py — 6 endpoints I1-I6, detection-safe.
# Static path /tickets/breaches is declared BEFORE /tickets/{ticket_id} — do not reorder.
# Backed by the canonical seed schema via it_service.db (raw SQL + aiosqlite).
import asyncio
import importlib.util
import os
import pathlib
import sys
import time
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Request, Header

from it_service import db
from it_service.models import (
    AssignLaptop,
    Assignment,
    Laptop,
    Reroute,
    Ticket,
    TicketCreate,
)

router = APIRouter(prefix="/it", tags=["it"])

# --- Demo dataset endpoints (seed/reset/status) ---------------------------
# Contract: seed/seed.py is the reference implementation (single TX reload +
# VACUUM INTO snapshot); these routes call it via import (no subprocess).
# Operate on the canonical shared file seed/demo.db so one POST fixes both
# services (hr_service/db.py and it_service/db.py default to the same file).
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_DEMO_DB = _REPO_ROOT / "seed" / "demo.db"
_DEMO_CSV_DIR = _REPO_ROOT / "seed"
_DEMO_SNAPSHOT = _REPO_ROOT / "seed" / "seed-snapshot.db"
_DEMO_COUNTED_TABLES = (
    "candidates",
    "employees",
    "equipment",
    "tickets",
    "shifts",
    "subscriptions",
    "api_keys",
)
_DEMO_EXPECTED_COUNTS = {
    "candidates": 20,
    "employees": 20,
    "equipment": 20,
    "tickets": 20,
    "shifts": 8,
    "subscriptions": 6,
    "api_keys": 5,
}
_DEMO_WARNINGS = [
    "CAND-003 visa expires in 27d",
    "3 SLA-breached tickets staged",
    "1 double-hold conflict staged (LT-1005)",
    "KEY-01 stale 295d blocks provision",
    "SUB-01 renews 2026-11-25 (auto-renew ON)",
]
_DEMO_RATE: dict[str, list[float]] = {}  # IP -> POST timestamps (sliding 60s)
_DEMO_LAST_RESET_MS: float | None = None
_seed_module_cache: object | None = None
_validate_module_cache: object | None = None


def _demo_guard(request: Request, confirm: str | None) -> None:
    """Guards first, no DB hit on reject: env -> header -> 6/min/IP (POSTs)."""
    if os.environ.get("ALLOW_DEMO_SEED") != "true":
        raise HTTPException(status_code=403, detail="demo endpoints disabled")
    if (confirm or "") != "yes":
        raise HTTPException(status_code=400, detail="missing x-demo-confirm: yes")
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = [t for t in _DEMO_RATE.get(ip, []) if now - t < 60]
    if len(hits) >= 6:
        raise HTTPException(status_code=429, detail="demo rate limit: 6/min/IP")
    hits.append(now)
    _DEMO_RATE[ip] = hits


def _load_seed_module():  # type: ignore[no-untyped-def]
    """Import seed/seed.py by path (no subprocess; cached)."""
    global _seed_module_cache
    if _seed_module_cache is None:
        if str(_DEMO_CSV_DIR) not in sys.path:
            sys.path.insert(0, str(_DEMO_CSV_DIR))
        spec = importlib.util.spec_from_file_location(
            "it_demo_seed_loader", _DEMO_CSV_DIR / "seed.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("seed.py loader spec not found")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _seed_module_cache = mod
    return _seed_module_cache


def _load_validate_module():  # type: ignore[no-untyped-def]
    """Import seed/validate.py by path for status counts (no subprocess)."""
    global _validate_module_cache
    if _validate_module_cache is None:
        if str(_DEMO_CSV_DIR) not in sys.path:
            sys.path.insert(0, str(_DEMO_CSV_DIR))
        spec = importlib.util.spec_from_file_location(
            "it_demo_validate_loader", _DEMO_CSV_DIR / "validate.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("validate.py loader spec not found")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _validate_module_cache = mod
    return _validate_module_cache


@router.get(
    "/equipment",
    operation_id="it_list_equipment",
    summary="List laptops",
    description="List laptops, filter status=free for assignable pool.",
    response_model=list[Laptop],
)
async def it_list_equipment(
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=100)] = 50,
) -> list[Laptop]:
    """List laptops, filter status=free for assignable pool."""
    rows = await db.list_equipment(status=status, limit=limit)
    return [Laptop.model_validate(r) for r in rows]


@router.post(
    "/equipment/assign",
    operation_id="it_assign_laptop",
    summary="Assign laptop to employee",
    description="Assign a free laptop to an employee. Confirm serial + employee with user first.",
    response_model=Assignment,
)
async def it_assign_laptop(body: AssignLaptop) -> Assignment:
    """Assign a free laptop to an employee."""
    try:
        row = await db.assign_laptop(serial=body.serial, employee_id=body.employee_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if row is None:
        raise HTTPException(status_code=404, detail="equipment or employee not found")
    return Assignment.model_validate(row)


@router.post(
    "/tickets",
    operation_id="it_create_ticket",
    summary="Create incident ticket",
    description="Create an incident ticket with SLA deadline = now + sla_hours.",
    response_model=Ticket,
    status_code=201,
)
async def it_create_ticket(body: TicketCreate) -> Ticket:
    """Create an incident ticket with SLA deadline = now + sla_hours."""
    row = await db.create_ticket(
        title=body.title,
        assignee_email=str(body.assignee_email),
        team=body.team,
        sla_hours=body.sla_hours,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="assignee email unknown")
    return Ticket.model_validate(row)


# Static path BEFORE /tickets/{ticket_id} — do not reorder.
@router.get(
    "/tickets/breaches",
    operation_id="it_sla_breach_list",
    summary="List SLA-breached tickets",
    description="Tickets past SLA deadline and unresolved. Filter by team/since. Start here for breach triage.",
    response_model=list[Ticket],
)
async def it_sla_breach_list(
    team: Annotated[str | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
) -> list[Ticket]:
    """Tickets past SLA deadline and unresolved."""
    rows = await db.breach_list(team=team, since=since)
    return [Ticket.model_validate(r) for r in rows]


@router.get(
    "/tickets/{ticket_id}",
    operation_id="it_get_ticket",
    summary="Get one ticket",
    description="Get one ticket with SLA timestamps and breach flag.",
    response_model=Ticket,
)
async def it_get_ticket(ticket_id: Annotated[str, Path()]) -> Ticket:
    """Get one ticket with SLA timestamps and breach flag."""
    row = await db.get_ticket(ticket_id)
    if row is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    return Ticket.model_validate(row)


@router.post(
    "/tickets/{ticket_id}/reroute",
    operation_id="it_reroute_ticket",
    summary="Reroute ticket to on-call",
    description="Reassign ticket to on-call owner (resolve email via hr_get_oncall first). Confirm before calling.",
    response_model=Ticket,
)
async def it_reroute_ticket(ticket_id: Annotated[str, Path()], body: Reroute) -> Ticket:
    """Reassign ticket to on-call owner."""
    row = await db.reroute_ticket(ticket_id, str(body.to_email))
    if row is None:
        raise HTTPException(status_code=404, detail="ticket or email not found")
    return Ticket.model_validate(row)


@router.post(
    "/demo/seed",
    operation_id="it_demo_seed",
    summary="Reload demo dataset",
    description="Reload deterministic demo dataset (truncate + 79 rows, one transaction)."
    " Demo-only: needs ALLOW_DEMO_SEED=true + x-demo-confirm: yes.",
    response_model=dict,
)
async def it_demo_seed(
    request: Request,
    x_demo_confirm: Annotated[str | None, Header()] = None,
) -> dict:
    """Reload deterministic demo dataset (truncate + 79 rows, one transaction)."""
    _demo_guard(request, x_demo_confirm)
    t0 = time.perf_counter()
    try:
        result = await asyncio.to_thread(
            _load_seed_module().load,
            _DEMO_DB,
            _DEMO_CSV_DIR,
            _DEMO_SNAPSHOT,
            True,
        )
    except HTTPException:
        raise
    except SystemExit as exc:
        raise HTTPException(status_code=500, detail=f"seed_failed: {exc}")
    except Exception as exc:  # noqa: BLE001 — surface loader errors as 500
        raise HTTPException(status_code=500, detail=f"seed_failed: {exc}")
    duration_ms = (time.perf_counter() - t0) * 1000
    return {
        "ok": True,
        "seed_version": result["seed_version"],
        "counts": result["counts"],
        "timings_ms": result["timings_ms"],
        "duration_ms": round(duration_ms, 1),
        "warnings": _DEMO_WARNINGS,
    }


@router.post(
    "/demo/reset",
    operation_id="it_demo_reset",
    summary="Reset demo dataset from snapshot",
    description="Fast restore of the post-seed snapshot (file copy)."
    " Demo-only: needs ALLOW_DEMO_SEED=true + x-demo-confirm: yes.",
    response_model=dict,
)
async def it_demo_reset(
    request: Request,
    x_demo_confirm: Annotated[str | None, Header()] = None,
) -> dict:
    """Fast restore of the post-seed snapshot (file copy)."""
    global _DEMO_LAST_RESET_MS
    _demo_guard(request, x_demo_confirm)
    try:
        result = await asyncio.to_thread(
            _load_seed_module().reset_from_snapshot, _DEMO_DB, _DEMO_SNAPSHOT
        )
    except HTTPException:
        raise
    except SystemExit as exc:
        raise HTTPException(status_code=500, detail=f"reset_failed: {exc}")
    except Exception as exc:  # noqa: BLE001 — surface restore errors as 500
        raise HTTPException(status_code=500, detail=f"reset_failed: {exc}")
    _DEMO_LAST_RESET_MS = result.get("duration_ms")
    return {"ok": True, **result}


@router.get(
    "/demo/status",
    operation_id="it_demo_status",
    summary="Demo dataset status",
    description="Seeded flag, per-table counts, seed version. Unguarded.",
    response_model=dict,
)
async def it_demo_status() -> dict:
    """Seeded flag, per-table counts, seed version."""
    try:
        tables = await asyncio.to_thread(
            _load_validate_module().load_sqlite, _DEMO_DB
        )
    except Exception as exc:  # noqa: BLE001 — unreadable DB means unseeded
        return {
            "seeded": False,
            "counts": {},
            "seed_version": "v14",
            "seeded_at": "2026-11-23T00:00:00Z",
            "last_reset_ms": _DEMO_LAST_RESET_MS,
            "error": str(exc),
        }
    counts = {t: len(tables.get(t, [])) for t in _DEMO_COUNTED_TABLES}
    return {
        "seeded": counts == _DEMO_EXPECTED_COUNTS,
        "counts": counts,
        "seed_version": "v14",
        "seeded_at": "2026-11-23T00:00:00Z",
        "last_reset_ms": _DEMO_LAST_RESET_MS,
    }
