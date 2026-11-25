# 02 — API Design: HR (5) + IT (6) Endpoints for Synapse Auto Detection

**Sources:** `research/final/04-synapse-auto.md` (detection guarantees + anti-patterns) · `research/final/15-endpoints.md` (endpoint semantics, Pair 4 HR + Ticketing-SLA).
**Goal:** 11 endpoints that `synapse build --auto` **always detects** via static tree-sitter parse.
**Rule:** literal decorator + literal path + module-level `APIRouter` + `include_router` + unique prefixed `operation_id` + Pydantic `response_model`. No dynamic registration.

> **Naming note vs `15-endpoints.md`:** that spec uses unprefixed IDs (`list_candidates`, `get_ticket`). Per `04-synapse-auto.md` §4-rule-2 / §5-anti-pattern-#6, two services in one repo collide on auto-generated or identical IDs and `--endpoints get_item` becomes ambiguous. This design **prefixes every ID (`hr_*`, `it_*`)** — the only intentional deviation, and the one `04` mandates.

## 1. Detection contract (from `04-synapse-auto.md` §4–§5)

1. `@router.get("/literal-path")` — string literal only. No f-strings, concatenation, variables, loops, `add_api_route` factories.
2. Unique `operation_id="hr_*"/"it_*"` on **every** route → becomes the MCP tool name and `--endpoints` selector.
3. Pydantic `BaseModel` request body + `response_model=` on every route → typed tool args (never bare `dict`).
4. `APIRouter(prefix="/hr"|"/it", tags=[...])` at module scope + `app.include_router(router)` at import time in the scanned file.
5. `summary=` + `description=` + one-line docstring per route → Synapse falls back to docstring for the tool description the agent reads.
6. Path/query params as typed function args (`str`, `int`, `date`, `datetime | None`). No required `Header(...)`, no `UploadFile`/`Form(...)`, no `include_in_schema=False`.
7. Route order: specific/static paths **before** `/{param}` catch-alls. One app per service, distinct ports + `--server-name`.
8. After any code change: `synapse build --discover` (builds reuse `.synapse/surface_cache.json` otherwise).

```bash
# topology
# hr-directory   http://localhost:8001  hr_service/routers/hr.py  --server-name hr-api
# ticketing-sla  http://localhost:8002  it_service/routers/it.py  --server-name it-api
# baseline build: 13 tools via --endpoints allowlist (H1-H5 + I1-I6 + 2 health; 11 functional-only) | live: +L1 GET /it/oncall-coverage via --discover with expanded allowlist (14 total; 12 functional-only). 6 /demo/* ops always excluded (docs/CLIENTS.md §7).
```

## 2. HR service — 5 endpoints (`hr_service/routers/hr.py`, prefix `/hr`)

| # | Method + Path | `operation_id` | Params | `response_model` | Description (→ tool description) |
|---|---|---|---|---|---|
| H1 | `GET /hr/candidates` | `hr_list_candidates` | `team: str \| None = Query(None)`, `limit: int = Query(20, le=100)` | `list[Candidate]` | List hiring candidates, optionally filtered by team. Use for headcount vs breach analysis. |
| H2 | `GET /hr/candidates/{candidate_id}` | `hr_get_candidate` | `candidate_id: str = Path(...)` | `Candidate` | Get one candidate by ID prior to converting to employee. |
| H3 | `POST /hr/employees` | `hr_create_employee` | `body: EmployeeCreate` (Pydantic) | `Employee` (201) | Convert hired candidate to employee. Confirm with user before calling. |
| H4 | `GET /hr/shifts` | `hr_shift_calendar` | `team: str = Query(...)`, `date: date = Query(...)` | `list[Shift]` | Shift calendar for a team on a date. Join tickets.created_at against this to check on-shift status. |
| H5 ⭐ LIVE | `GET /hr/oncall` | `hr_get_oncall` | `team: str = Query("support-night")`, `at: datetime \| None = Query(None)` | `OnCall` | Who is on call for a team at time `at` (default now). Use to reroute breaching tickets. Added live mid-demo; triggers `--discover`. |

### HR Pydantic models (`hr_service/models.py`)

```python
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field

class Candidate(BaseModel):
    candidate_id: str
    name: str
    email: EmailStr
    team: str  # e.g. "platform", "support-night"
    status: str = "interview"  # interview | offer | hired | rejected

class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    team: str
    start_date: date
    role: str = "engineer"

class Employee(EmployeeCreate):
    employee_id: str
    created_at: datetime

class Shift(BaseModel):
    team: str
    employee_id: str
    date: date
    shift: str = Field(pattern="^(day|night)$")
    on_call: bool = False

class OnCall(BaseModel):  # H5 live-discover response_model
    team: str
    employee_id: str
    name: str
    email: EmailStr
    at: datetime
```

### HR router stub — copy-paste, detection-safe

```python
# hr_service/routers/hr.py
from datetime import date, datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Path, Query

from hr_service.models import Candidate, Employee, EmployeeCreate, OnCall, Shift

router = APIRouter(prefix="/hr", tags=["hr"])

@router.get(
    "/candidates",
    operation_id="hr_list_candidates",
    summary="List hiring candidates",
    description="List hiring candidates, optionally filtered by team. Use for headcount vs breach analysis.",
    response_model=list[Candidate],
)
def hr_list_candidates(
    team: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=100)] = 20,
) -> list[Candidate]:
    """List hiring candidates, optionally filtered by team."""
    ...  # SELECT ... WHERE team = :team LIMIT :limit

@router.get(
    "/candidates/{candidate_id}",
    operation_id="hr_get_candidate",
    summary="Get one candidate",
    description="Get one candidate by ID prior to converting to employee.",
    response_model=Candidate,
)
def hr_get_candidate(candidate_id: Annotated[str, Path()]) -> Candidate:
    """Get one candidate by ID prior to converting to employee."""
    ...

@router.post(
    "/employees",
    operation_id="hr_create_employee",
    summary="Convert candidate to employee",
    description="Convert hired candidate to employee. Confirm with user before calling.",
    response_model=Employee,
    status_code=201,
)
def hr_create_employee(body: EmployeeCreate) -> Employee:
    """Convert hired candidate to employee."""
    ...

@router.get(
    "/shifts",
    operation_id="hr_shift_calendar",
    summary="Shift calendar lookup",
    description="Shift calendar for a team on a date. Join tickets.created_at against this to check on-shift status.",
    response_model=list[Shift],
)
def hr_shift_calendar(
    team: Annotated[str, Query()],
    date: Annotated[date, Query()],
) -> list[Shift]:
    """Shift calendar for a team on a date."""
    ...

# H5 — ADDED LIVE mid-demo (comment out for baseline build, uncomment for --discover moment)
@router.get(
    "/oncall",
    operation_id="hr_get_oncall",
    summary="Who is on call now",
    description="Who is on call for a team at time `at` (default now). Use to reroute breaching tickets.",
    response_model=OnCall,
)
def hr_get_oncall(
    team: Annotated[str, Query()] = "support-night",
    at: Annotated[datetime | None, Query()] = None,
) -> OnCall:
    """Who is on call for a team at time `at` (default now)."""
    at = at or datetime.now(timezone.utc)
    ...  # lookup roster: team + at -> person
```

### HR app wiring (`hr_service/main.py`)

```python
# hr_service/main.py
from fastapi import FastAPI

from hr_service.routers.hr import router as hr_router

app = FastAPI(title="hr-directory")

@app.get("/health", operation_id="hr_health_check", summary="Liveness probe")
def hr_health_check() -> dict:
    """Liveness probe."""
    return {"ok": True}

app.include_router(hr_router)  # must precede any Synapse/MCP mount

# uvicorn hr_service.main:app --port 8001
```

## 3. IT service — 6 endpoints (`it_service/routers/it.py`, prefix `/it`)

| # | Method + Path | `operation_id` | Params | `response_model` | Description (→ tool description) |
|---|---|---|---|---|---|
| I1 | `GET /it/equipment` | `it_list_equipment` | `status: str \| None = Query(None)` (`free`/`assigned`), `limit: int = Query(50, le=100)` | `list[Laptop]` | List laptops, filter status=free for assignable pool. |
| I2 | `POST /it/equipment/assign` | `it_assign_laptop` | `body: AssignLaptop` (Pydantic) | `Assignment` | Assign a free laptop to an employee. Confirm serial + employee with user first. |
| I3 | `POST /it/tickets` | `it_create_ticket` | `body: TicketCreate` (Pydantic) | `Ticket` (201) | Create an incident ticket with SLA deadline = now + sla_hours. |
| I4 | `GET /it/tickets/breaches` | `it_sla_breach_list` | `team: str \| None = Query(None)`, `since: datetime \| None = Query(None)` | `list[Ticket]` | Tickets past SLA deadline and unresolved. Filter by team/since. Start here for breach triage. |
| I5 | `GET /it/tickets/{ticket_id}` | `it_get_ticket` | `ticket_id: str = Path(...)` | `Ticket` | Get one ticket with SLA timestamps and breach flag. |
| I6 | `POST /it/tickets/{ticket_id}/reroute` | `it_reroute_ticket` | `ticket_id: str = Path(...)`, `body: Reroute` (Pydantic) | `Ticket` | Reassign ticket to on-call owner (resolve email via hr_get_oncall first). Confirm before calling. |

> Order note: `GET /tickets/breaches` is declared **before** `GET /tickets/{ticket_id}` so static scan keeps both routes distinct and runtime does not shadow the static path (`04` §5-#5).

### IT Pydantic models (`it_service/models.py`)

```python
from datetime import datetime
from pydantic import BaseModel, EmailStr

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
    team: str
    sla_hours: int = 24

class Reroute(BaseModel):
    to_email: EmailStr
    reason: str = "sla-breach-reroute-to-oncall"

class Ticket(BaseModel):
    ticket_id: str  # e.g. T-551
    title: str
    assignee_email: EmailStr
    team: str
    status: str  # open | resolved
    created_at: datetime
    deadline_at: datetime
    breached: bool = False
```

### IT router stub — copy-paste, detection-safe

```python
# it_service/routers/it.py
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Path, Query

from it_service.models import (
    AssignLaptop,
    Assignment,
    Laptop,
    Reroute,
    Ticket,
    TicketCreate,
)

router = APIRouter(prefix="/it", tags=["it"])

@router.get(
    "/equipment",
    operation_id="it_list_equipment",
    summary="List laptops",
    description="List laptops, filter status=free for assignable pool.",
    response_model=list[Laptop],
)
def it_list_equipment(
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=100)] = 50,
) -> list[Laptop]:
    """List laptops, filter status=free for assignable pool."""
    ...

@router.post(
    "/equipment/assign",
    operation_id="it_assign_laptop",
    summary="Assign laptop to employee",
    description="Assign a free laptop to an employee. Confirm serial + employee with user first.",
    response_model=Assignment,
)
def it_assign_laptop(body: AssignLaptop) -> Assignment:
    """Assign a free laptop to an employee."""
    ...

@router.post(
    "/tickets",
    operation_id="it_create_ticket",
    summary="Create incident ticket",
    description="Create an incident ticket with SLA deadline = now + sla_hours.",
    response_model=Ticket,
    status_code=201,
)
def it_create_ticket(body: TicketCreate) -> Ticket:
    """Create an incident ticket with SLA deadline = now + sla_hours."""
    ...

# Static path BEFORE /tickets/{ticket_id} — do not reorder.
@router.get(
    "/tickets/breaches",
    operation_id="it_sla_breach_list",
    summary="List SLA-breached tickets",
    description="Tickets past SLA deadline and unresolved. Filter by team/since. Start here for breach triage.",
    response_model=list[Ticket],
)
def it_sla_breach_list(
    team: Annotated[str | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
) -> list[Ticket]:
    """Tickets past SLA deadline and unresolved."""
    ...

@router.get(
    "/tickets/{ticket_id}",
    operation_id="it_get_ticket",
    summary="Get one ticket",
    description="Get one ticket with SLA timestamps and breach flag.",
    response_model=Ticket,
)
def it_get_ticket(ticket_id: Annotated[str, Path()]) -> Ticket:
    """Get one ticket with SLA timestamps and breach flag."""
    ...

@router.post(
    "/tickets/{ticket_id}/reroute",
    operation_id="it_reroute_ticket",
    summary="Reroute ticket to on-call",
    description="Reassign ticket to on-call owner (resolve email via hr_get_oncall first). Confirm before calling.",
    response_model=Ticket,
)
def it_reroute_ticket(ticket_id: Annotated[str, Path()], body: Reroute) -> Ticket:
    """Reassign ticket to on-call owner."""
    ...
```

### IT app wiring (`it_service/main.py`)

```python
# it_service/main.py
from fastapi import FastAPI

from it_service.routers.it import router as it_router

app = FastAPI(title="ticketing-sla")

@app.get("/health", operation_id="it_health_check", summary="Liveness probe")
def it_health_check() -> dict:
    """Liveness probe."""
    return {"ok": True}

app.include_router(it_router)

# uvicorn it_service.main:app --port 8002
```

## 4. Pre-build verification (from `04` §6)

```bash
python -c "import hr_service.main, it_service.main; print(len(hr_service.main.app.routes), len(it_service.main.app.routes))"
curl -s localhost:8001/openapi.json | python -c "import json,sys; print(sorted({o.get('operationId','') for m in json.load(sys.stdin)['paths'].values() for o in m.values()}))"
curl -s localhost:8002/openapi.json | python -c "import json,sys; print(sorted({o.get('operationId','') for m in json.load(sys.stdin)['paths'].values() for o in m.values()}))"
# Every operationId printed must appear in the Synapse endpoint picker; any gap = an anti-pattern from 04 §5.
```

## 5. Build / live-`--discover` runbook

```bash
synapse build --auto --all-endpoints --server-name hr-api   # 4 HR tools (H5 commented out)
synapse build --auto --all-endpoints --server-name it-api --new  # 6 IT tools
# mid-demo: uncomment H5 block in hr_service/routers/hr.py, then:
synapse build --discover --auto --all-endpoints --server-name hr-api  # +hr_get_oncall, same server id
```

Cross-system joins: `assignee_email ↔ employee email/employee_id`; twist join `ticket.created_at ↔ hr_shift_calendar(team, date)`; Q3 reroute chain `it_sla_breach_list → hr_get_oncall → it_reroute_ticket`.
