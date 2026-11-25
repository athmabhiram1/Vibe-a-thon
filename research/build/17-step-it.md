# Step 17 — Scaffold IT Service (`ticketing-sla`, port 8002)

> Source: `research/final/15-endpoints.md` §3 + `research/final/14-seed-data.md` §2.4 + `research/final/03-it-provision.md` §3.
> Goal: runnable FastAPI `it_service` with 6 agent-ready endpoints on `http://localhost:8002`. Pairs with HR service (port 8001) for Track 3 Q1/Q2/Q3. Time: ~20 min.

## 0. Topology + endpoint table (memorize)

| # | Method + Path | `operation_id` | `response_model` | Agent job |
|---|---|---|---|---|
| I1 | `GET /it/equipment` | `it_list_equipment` | `list[Laptop]` | free-laptop pool |
| I2 | `POST /it/equipment/assign` | `it_assign_laptop` | `Assignment` | laptop → employee (needs HR `employee_id`) |
| I3 | `POST /it/tickets` | `it_create_ticket` | `Ticket` | intake, `deadline = now + sla_hours` |
| I6 | `GET /it/tickets/breaches` | `it_sla_breach_list` | `list[Ticket]` | pre-computed breach anti-join — start of Q1/Q2/Q3 |
| I4 | `GET /it/tickets/{ticket_id}` | `it_get_ticket` | `Ticket` | single-ticket forensics |
| I5 | `POST /it/tickets/{ticket_id}/reroute` | `it_reroute_ticket` | `Ticket` | reassign to on-call (needs live H5 `get_oncall`) |

> **Order rule (critical):** declare `GET /tickets/breaches` **BEFORE** `GET /tickets/{ticket_id}` in `routers/it.py`. Otherwise FastAPI matches `breaches` as `{ticket_id}="breaches"` and Synapse static parse collapses the two routes. See `15-endpoints.md` NOTE + `19-H4-operation-id-detection.md`.

## 1. Exact commands — scaffold from zero

```powershell
# from repo root (C:\...\VIBE_CODE or your track-3 folder)
mkdir it_service\routers
type nul > it_service\__init__.py
type nul > it_service\routers\__init__.py
type nul > it_service\models.py
type nul > it_service\seed_data.py
type nul > it_service\routers\it.py
type nul > it_service\main.py

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi "uvicorn[standard]" pydantic email-validator
pip freeze > requirements.txt
```

Bash equivalent:

```bash
mkdir -p it_service/routers
touch it_service/__init__.py it_service/routers/__init__.py
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi "uvicorn[standard]" pydantic email-validator
```

## 2. Copy-paste — `it_service/models.py`

```python
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class Laptop(BaseModel):
    serial: str
    model: str
    status: str = "free"  # free | assigned

class AssignLaptop(BaseModel):
    serial: str
    employee_id: str

class Assignment(BaseModel):
    serial: str
    employee_id: str
    assigned_at: datetime

class TicketCreate(BaseModel):
    title: str
    assignee_email: EmailStr
    team: str = "support-night"
    sla_hours: int = Field(default=24, ge=1, le=720)

class Reroute(BaseModel):
    to_email: EmailStr
    reason: str = "sla-breach-reroute-to-oncall"

class Ticket(BaseModel):
    ticket_id: str  # e.g. T-551
    title: str
    assignee_email: EmailStr
    team: str
    status: str = "open"  # open | resolved
    created_at: datetime
    deadline_at: datetime
    breached: bool = False
```

## 3. Copy-paste — `it_service/seed_data.py` (seed hooks source)

Deterministic, no `now()` at import. `seeded_at` anchor = `2026-11-23T00:00:00Z` per `14-seed-data.md`.

```python
from datetime import datetime, timezone, timedelta

SEEDED_AT = datetime(2026, 11, 23, tzinfo=timezone.utc)

SEED_LAPTOPS = [
    {"serial": "SN-MBP14-1001", "model": "MacBook Pro 14", "status": "free"},
    {"serial": "SN-MBP14-1002", "model": "MacBook Pro 14", "status": "free"},
    {"serial": "SN-T14-1003", "model": "ThinkPad T14", "status": "free"},
    {"serial": "SN-DU27-1004", "model": "Dell U2723QE", "status": "assigned"},
    {"serial": "SN-MBP14-1005", "model": "MacBook Pro 14", "status": "free"},
]

# 3 breached + 2 healthy. T-551 is the Q1 demo ticket.
SEED_TICKETS = [
    {"ticket_id": "T-551", "title": "VPN down for night shift",
     "assignee_email": "priya.nair@demo.example.com", "team": "support-night",
     "status": "open", "created_at": SEEDED_AT - timedelta(hours=30),
     "deadline_at": SEEDED_AT - timedelta(hours=6), "breached": True},
    {"ticket_id": "T-552", "title": "Laptop no-boot",
     "assignee_email": "arjun.singh@demo.example.com", "team": "support-night",
     "status": "open", "created_at": SEEDED_AT - timedelta(hours=20),
     "deadline_at": SEEDED_AT - timedelta(hours=2), "breached": True},
    {"ticket_id": "T-553", "title": "Badge reader fail",
     "assignee_email": "meera.pillai@demo.example.com", "team": "platform",
     "status": "open", "created_at": SEEDED_AT - timedelta(hours=50),
     "deadline_at": SEEDED_AT - timedelta(hours=2), "breached": True},
    {"ticket_id": "T-554", "title": "Password reset",
     "assignee_email": "priya.nair@demo.example.com", "team": "support-night",
     "status": "open", "created_at": SEEDED_AT - timedelta(hours=2),
     "deadline_at": SEEDED_AT + timedelta(hours=22), "breached": False},
    {"ticket_id": "T-555", "title": "Old resolved issue",
     "assignee_email": "vikram.rao@demo.example.com", "team": "platform",
     "status": "resolved", "created_at": SEEDED_AT - timedelta(hours=72),
     "deadline_at": SEEDED_AT - timedelta(hours=48), "breached": False},
]

def is_breached(t: dict, now: datetime) -> bool:
    return t["status"] != "resolved" and t["deadline_at"] < now
```

## 4. Copy-paste — `it_service/routers/it.py` (order matters)

```python
from datetime import datetime, timezone
from fastapi import APIRouter, Query, Path
from typing import Annotated
from models import Laptop, AssignLaptop, Assignment, TicketCreate, Ticket, Reroute
from seed_data import SEED_LAPTOPS, SEED_TICKETS, is_breached
# NOTE: run as `uvicorn it_service.main:app`; if import error use
# `from it_service.models import ...` and `from it_service.seed_data import ...`

router = APIRouter(prefix="/it", tags=["it"])

LAPTOPS: list[dict] = [dict(r) for r in SEED_LAPTOPS]
TICKETS: list[dict] = [dict(r) for r in SEED_TICKETS]
_COUNTER = 556

def _now() -> datetime:
    return datetime.now(timezone.utc)

# I1
@router.get("/equipment", operation_id="it_list_equipment",
            description="List laptops, filter status=free for assignable pool.",
            response_model=list[Laptop])
def list_equipment(status: Annotated[str | None, Query()] = None,
                   limit: Annotated[int, Query(le=100)] = 50) -> list[Laptop]:
    rows = [r for r in LAPTOPS if status is None or r["status"] == status]
    return [Laptop(**r) for r in rows[:limit]]

# I2
@router.post("/equipment/assign", operation_id="it_assign_laptop",
             description="Assign a free laptop to an employee. Confirm serial + employee with user first.",
             response_model=Assignment, status_code=201)
def assign_laptop(body: AssignLaptop) -> Assignment:
    for r in LAPTOPS:
        if r["serial"] == body.serial:
            if r["status"] != "free":
                from fastapi import HTTPException
                raise HTTPException(409, f"{body.serial} not free (status={r['status']})")
            r["status"] = "assigned"
            return Assignment(serial=r["serial"], employee_id=body.employee_id, assigned_at=_now())
    from fastapi import HTTPException
    raise HTTPException(404, f"laptop {body.serial} not found")

# I3
@router.post("/tickets", operation_id="it_create_ticket",
             description="Create an incident ticket with SLA deadline = now + sla_hours.",
             response_model=Ticket, status_code=201)
def create_ticket(body: TicketCreate) -> Ticket:
    global _COUNTER
    now = _now()
    t = {"ticket_id": f"T-{_COUNTER}", "title": body.title,
         "assignee_email": body.assignee_email, "team": body.team,
         "status": "open", "created_at": now,
         "deadline_at": now + __import__("datetime").timedelta(hours=body.sla_hours),
         "breached": False}
    _COUNTER += 1
    TICKETS.append(t)
    return Ticket(**t)

# I6 — MUST stay BEFORE /tickets/{ticket_id}
@router.get("/tickets/breaches", operation_id="it_sla_breach_list",
            description="Tickets past SLA deadline and unresolved. Filter by team/since. Start here for breach triage.",
            response_model=list[Ticket])
def sla_breach_list(team: Annotated[str | None, Query()] = None,
                    since: Annotated[datetime | None, Query()] = None) -> list[Ticket]:
    now = _now()
    out = [t for t in TICKETS if is_breached(t, now)]
    if team:
        out = [t for t in out if t["team"] == team]
    if since:
        out = [t for t in out if t["created_at"] >= since]
    return [Ticket(**t) for t in out]

# I4 — AFTER breaches
@router.get("/tickets/{ticket_id}", operation_id="it_get_ticket",
            description="Get one ticket with SLA timestamps and breach flag.",
            response_model=Ticket)
def get_ticket(ticket_id: Annotated[str, Path()]) -> Ticket:
    now = _now()
    for t in TICKETS:
        if t["ticket_id"] == ticket_id:
            t = dict(t)
            t["breached"] = is_breached(t, now)
            return Ticket(**t)
    from fastapi import HTTPException
    raise HTTPException(404, f"ticket {ticket_id} not found")

# I5
@router.post("/tickets/{ticket_id}/reroute", operation_id="it_reroute_ticket",
             description="Reassign ticket to on-call owner (resolve email via get_oncall first). Confirm before calling.",
             response_model=Ticket)
def reroute_ticket(ticket_id: Annotated[str, Path()], body: Reroute) -> Ticket:
    for t in TICKETS:
        if t["ticket_id"] == ticket_id:
            t["assignee_email"] = body.to_email
            t["breached"] = is_breached(t, _now())
            return Ticket(**t)
    from fastapi import HTTPException
    raise HTTPException(404, f"ticket {ticket_id} not found")

# --- seed hooks (demo-only) ---
@router.post("/demo/seed", operation_id="it_demo_seed",
             description="Reload deterministic demo dataset. Demo-only.",
             response_model=dict)
def demo_seed() -> dict:
    global TICKETS, LAPTOPS, _COUNTER
    LAPTOPS = [dict(r) for r in SEED_LAPTOPS]
    TICKETS = [dict(r) for r in SEED_TICKETS]
    _COUNTER = 556
    return {"ok": True, "laptops": len(LAPTOPS), "tickets": len(TICKETS)}

@router.post("/demo/reset", operation_id="it_demo_reset",
             description="Reset to post-seed snapshot (same as seed for in-memory store).",
             response_model=dict)
def demo_reset() -> dict:
    return demo_seed()
```

## 5. Copy-paste — `it_service/main.py`

```python
from fastapi import FastAPI
from routers.it import router as it_router
# import-error alt: from it_service.routers.it import router as it_router

app = FastAPI(title="ticketing-sla")
app.include_router(it_router)  # must precede any Synapse/MCP mount

@app.get("/health", operation_id="it_health", description="Liveness probe.")
def health() -> dict:
    return {"ok": True, "service": "ticketing-sla"}

# uvicorn it_service.main:app --port 8002 --reload
```

## 6. Run + verify (exact)

```powershell
# terminal 1 — IT service
.\.venv\Scripts\Activate.ps1
uvicorn it_service.main:app --port 8002 --reload

# terminal 2 — verification (PowerShell; curl.exe = real curl)
curl.exe -s http://localhost:8002/health
curl.exe -s http://localhost:8002/it/equipment | head -c 300
curl.exe -s "http://localhost:8002/it/equipment?status=free"
curl.exe -s http://localhost:8002/it/tickets/breaches
curl.exe -s http://localhost:8002/it/tickets/T-551
curl.exe -s -X POST http://localhost:8002/it/tickets/T-551/reroute -H "Content-Type: application/json" -d '{\"to_email\":\"oncall@demo.example.com\",\"reason\":\"test\"}'
curl.exe -s -X POST http://localhost:8002/it/tickets -H "Content-Type: application/json" -d '{\"title\":\"test\",\"assignee_email\":\"a@demo.example.com\",\"team\":\"support-night\",\"sla_hours\":24}'
curl.exe -s http://localhost:8002/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print([p for p in d['paths']])"
```

Expected:

- `/health` → `{"ok":true,...}`
- `/it/tickets/breaches` → 3 rows (T-551, T-552, T-553), each `breached:true`
- `/it/tickets/T-551` → single ticket (proves `{id}` route didn't swallow `breaches`)
- openapi paths order contains `/it/tickets/breaches` **and** `/it/tickets/{ticket_id}` as separate keys
- `operationIds` = `it_list_equipment, it_assign_laptop, it_create_ticket, it_sla_breach_list, it_get_ticket, it_reroute_ticket` (+ `it_demo_seed/reset`, `it_health`)

Fail check — route-shadow test:

```powershell
# must NOT return T-551 shape with ticket_id="breaches"
curl.exe -s http://localhost:8002/it/tickets/breaches | python -c "import json,sys; d=json.load(sys.stdin); assert isinstance(d,list) and len(d)==3, d; print('order OK:', [t['ticket_id'] for t in d])"
```

Docs check: open `http://localhost:8002/docs` → 6 IT rows + 2 demo rows visible.

## 7. Synapse expose (Auto, pre-demo 13 tools via allowlist)

```bash
# HR (8001) + IT (8002) both running
synapse build --auto --all-endpoints --smart-names
# expect 13 tools pre-demo (H1-H5 + I1-I6 + 2 health via --endpoints allowlist); L1 it_oncall_coverage comes live via --discover with expanded allowlist
synapse build --discover   # after adding GET /hr/oncall mid-demo
```

If Synapse mangles names, assert explicit `operation_id` survived: `openapi.json` → `operationId` startswith `it_` for all 6.

## 8. Checklist

- [ ] `breaches` defined before `{ticket_id}` in file (grep: `breaches` line < `ticket_id}` line)
- [ ] all 6 `operation_id` start with `it_`, all 6 have `response_model`
- [ ] `POST /it/demo/seed` + `/demo/reset` return `{"ok":true}` in <1s
- [ ] breach list = 3, T-551 fetch works, reroute changes `assignee_email`
- [ ] both servers up (8001 + 8002) before `synapse build`
