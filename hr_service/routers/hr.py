"""HR directory router — 4 stable endpoints (H1-H4) + H5 live moment.

Detection contract (research/build/02-api-design.md):
literal paths, explicit hr_* operation_id, response_model, docstrings.
No dynamic loops, no include_in_schema=False, no required Header,
no File/Form.
"""

import datetime as dt
import asyncio
import importlib.util
import os
import pathlib
import sys
import time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Request, Header

from hr_service import db
from hr_service.models import Candidate, Employee, EmployeeCreate, OnCall, Shift

router = APIRouter(prefix="/hr", tags=["hr"])

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
            "hr_demo_seed_loader", _DEMO_CSV_DIR / "seed.py"
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
            "hr_demo_validate_loader", _DEMO_CSV_DIR / "validate.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("validate.py loader spec not found")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _validate_module_cache = mod
    return _validate_module_cache


@router.get(
    "/candidates",
    operation_id="hr_list_candidates",
    summary="List hiring candidates",
    description="List hiring candidates, optionally filtered by team."
    " Use for headcount vs breach analysis.",
    response_model=list[Candidate],
)
async def hr_list_candidates(
    team: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=100)] = 20,
) -> list[Candidate]:
    """List hiring candidates, optionally filtered by team."""
    rows = await db.list_candidates(team=team, limit=limit)
    return [Candidate.model_validate(r) for r in rows]


@router.get(
    "/candidates/{candidate_id}",
    operation_id="hr_get_candidate",
    summary="Get one candidate",
    description="Get one candidate by ID prior to converting to employee.",
    response_model=Candidate,
)
async def hr_get_candidate(
    candidate_id: Annotated[str, Path()],
) -> Candidate:
    """Get one candidate by ID prior to converting to employee."""
    row = await db.get_candidate(candidate_id)
    if row is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return Candidate.model_validate(row)


@router.post(
    "/employees",
    operation_id="hr_create_employee",
    summary="Convert candidate to employee",
    description="Convert hired candidate to employee."
    " Confirm with user before calling.",
    response_model=Employee,
    status_code=201,
)
async def hr_create_employee(body: EmployeeCreate) -> Employee:
    """Convert hired candidate to employee."""
    row = await db.create_employee(
        name=body.name,
        email=body.email,
        team=body.team,
        start_date=body.start_date,
        role=body.role,
    )
    return Employee.model_validate(row)


@router.get(
    "/shifts",
    operation_id="hr_shift_calendar",
    summary="Shift calendar lookup",
    description="Shift calendar for a team on a date."
    " Join tickets.created_at against this to check on-shift status.",
    response_model=list[Shift],
)
async def hr_shift_calendar(
    team: Annotated[str, Query()],
    date: Annotated[dt.date, Query()],
) -> list[Shift]:
    """Shift calendar for a team on a date."""
    rows = await db.shift_calendar(team=team, day=date)
    return [Shift.model_validate(r) for r in rows]


# H5 — live moment: who is on call (uncommented for the discover build).
@router.get(
    "/oncall",
    operation_id="hr_get_oncall",
    summary="Who is on call now",
    description="Who is on call for a team at time `at` (default now)."
    " Use to reroute breaching tickets.",
    response_model=OnCall,
)
async def hr_get_oncall(
    team: Annotated[str, Query()] = "support-night",
    at: Annotated[dt.datetime | None, Query()] = None,
) -> OnCall:
    """Who is on call for a team at time `at` (default now)."""
    moment = at or dt.datetime.now(dt.timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.timezone.utc)
    row = await db.get_oncall(team=team, moment=moment)
    if row is None:
        raise HTTPException(status_code=404, detail="no on-call roster for team/date")
    return OnCall.model_validate(row)


@router.post(
    "/demo/seed",
    operation_id="hr_demo_seed",
    summary="Reload demo dataset",
    description="Reload deterministic demo dataset (truncate + 79 rows, one transaction)."
    " Demo-only: needs ALLOW_DEMO_SEED=true + x-demo-confirm: yes.",
    response_model=dict,
)
async def hr_demo_seed(
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
    operation_id="hr_demo_reset",
    summary="Reset demo dataset from snapshot",
    description="Fast restore of the post-seed snapshot (file copy)."
    " Demo-only: needs ALLOW_DEMO_SEED=true + x-demo-confirm: yes.",
    response_model=dict,
)
async def hr_demo_reset(
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
    operation_id="hr_demo_status",
    summary="Demo dataset status",
    description="Seeded flag, per-table counts, seed version. Unguarded.",
    response_model=dict,
)
async def hr_demo_status() -> dict:
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
