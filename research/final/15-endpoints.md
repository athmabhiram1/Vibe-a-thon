# 15 — Endpoint Spec: HR + IT FastAPIs (Track 3, Agent-Ready)

**Date:** 2026-11-22 | **Track:** 3 (copilot across two systems) | **Stack:** Python FastAPI only (Synapse `--local` writes files only for Python; hosted Auto forwards to live API)
**Synapse mode:** Auto (`synapse build --auto --endpoints "<allowlist>"` pre-demo; `synapse build --discover` live with expanded allowlist). **Pair:** HR + Ticketing with SLA Twist (Pair 4, 19/20).
**Rule honored:** fewer well-named tools — 14 total post-discover (13 baseline + 1 live-discover; 11/12 functional-only). Each has explicit `operation_id` (= MCP tool name), `description` (= tool description), `response_model` (typed return). H5 `GET /hr/oncall` is live on disk (baseline includes it); L1 `GET /it/oncall-coverage` is the live-add. 6 `/demo/*` ops always excluded via allowlist (`docs/CLIENTS.md` §7).

> Why explicit `operation_id`: Synapse static parse keys off decorators (`@router.get/post`, `api_route`, `add_url_rule`); auto-generated IDs mangle names and risk collisions. Explicit IDs guarantee 1:1 tool mapping. See `19-H4-operation-id-detection.md`. Always rebuild with `--discover` after code change — builds reuse `.synapse/surface_cache.json` otherwise.

---

## 1. Service topology

| System | Base URL (demo) | Router prefix | File | `ENDPOINT_BASE_URL` |
|---|---|---|---|---|
| `hr-directory` | `http://localhost:8001` | `/hr` | `hr_service/routers/hr.py` | `HR_BASE_URL=http://localhost:8001` |
| `ticketing-sla` | `http://localhost:8002` | `/it` | `it_service/routers/it.py` | `IT_BASE_URL=http://localhost:8002` |

Join keys: `assignee_email ↔ employee_id`; twist join `ticket.created_at ↔ shift_calendar` (was assignee on-shift?).

Cross questions (need both):
- **Q1:** "Ticket T-551 breached SLA — was assignee on shift, and who was on-call backup?"
- **Q2:** "Which team has worst breach rate / ticket volume, correlated with understaffed nights?"
- **Q3 (needs live endpoint):** "Re-route all currently-breaching tickets to whoever is on call *right now*."

---

## 2. HR service — 5 endpoints

| # | Method + Path | `operation_id` | Params | `response_model` | Why agent-needed (not CRUD noise) |
|---|---|---|---|---|---|
| H1 | `GET /hr/candidates` | `list_candidates` | `team: str \| None = Query(None)`, `limit: int = 20` | `list[Candidate]` | Hiring funnel lookup for Q2 headcount-vs-breach correlation; filtered list beats raw table dump. |
| H2 | `GET /hr/candidates/{candidate_id}` | `get_candidate` | `candidate_id: str = Path(...)` | `Candidate` | Detail for offer/convert decision; pairs with H3. |
| H3 | `POST /hr/employees` | `create_employee` | `body: EmployeeCreate` | `Employee` | Write action: candidate→employee conversion. Confirmation-gated in agent prompt (Track 2 safety pattern). |
| H4 | `GET /hr/shifts` | `shift_calendar` | `team: str`, `date: date = Query(...)` | `list[Shift]` | Twist-join source: was assignee on-shift at `ticket.created_at`? Required for Q1/Q2. |
| H5 ⭐ LIVE | `GET /hr/oncall` | `get_oncall` | `at: datetime \| None = Query(None)` | `OnCall` | **Added live mid-demo for `--discover`.** Answers "who is on call *right now*" → powers Q3 reroute. Without it Q3 is unanswerable. |

> ⭐ L1 is the `--discover` moment: baseline build exposes H1–H5 + all 6 IT endpoints via allowlist (13 tools with health, 11 functional-only). Mid-demo add `GET /it/oncall-coverage`, run `synapse build --discover` with the expanded allowlist, new tool `it_oncall_coverage` appears without restart, agent answers Q3. (H5 `GET /hr/oncall` is live on disk — the old uncomment-H5 choreography is dead.)

### HR Pydantic models

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

class OnCall(BaseModel):  # ⭐ live-discover response_model
    team: str
    employee_id: str
    name: str
    email: EmailStr
    at: datetime
```

### HR router stub (`hr_service/routers/hr.py`)

```python
from datetime import date, datetime, timezone
from fastapi import APIRouter, Query, Path
from typing import Annotated
from models import Candidate, Employee, EmployeeCreate, Shift, OnCall

router = APIRouter(prefix="/hr", tags=["hr"])

@router.get("/candidates", operation_id="list_candidates",
            description="List hiring candidates, optionally filtered by team. Use for headcount vs breach analysis.",
            response_model=list[Candidate])
def list_candidates(team: Annotated[str | None, Query()] = None,
                    limit: Annotated[int, Query(le=100)] = 20) -> list[Candidate]:
    ...  # SELECT ... WHERE team = :team LIMIT :limit

@router.get("/candidates/{candidate_id}", operation_id="get_candidate",
            description="Get one candidate by ID prior to converting to employee.",
            response_model=Candidate)
def get_candidate(candidate_id: Annotated[str, Path()]) -> Candidate:
    ...

@router.post("/employees", operation_id="create_employee",
             description="Convert hired candidate to employee. Confirm with user before calling.",
             response_model=Employee, status_code=201)
def create_employee(body: EmployeeCreate) -> Employee:
    ...

@router.get("/shifts", operation_id="shift_calendar",
            description="Shift calendar for a team on a date. Join tickets.created_at against this to check on-shift status.",
            response_model=list[Shift])
def shift_calendar(team: Annotated[str, Query()],
                   date: Annotated[date, Query()]) -> list[Shift]:
    ...

# ⭐ ADDED LIVE mid-demo — triggers `synapse build --discover`
@router.get("/oncall", operation_id="get_oncall",
            description="Who is on call for a team at time `at` (default now). Use to reroute breaching tickets.",
            response_model=OnCall)
def get_oncall(team: Annotated[str, Query()] = "support-night",
               at: Annotated[datetime | None, Query()] = None) -> OnCall:
    at = at or datetime.now(timezone.utc)
    ...  # lookup roster: team + at -> person
```

### HR app wiring (routers included before MCP wrap)

```python
# hr_service/main.py
from fastapi import FastAPI
from routers.hr import router as hr_router

app = FastAPI(title="hr-directory")
app.include_router(hr_router)  # must precede any Synapse/MCP mount

# uvicorn hr_service.main:app --port 8001
```

---

## 3. IT service — 6 endpoints

| # | Method + Path | `operation_id` | Params | `response_model` | Why agent-needed |
|---|---|---|---|---|---|
| I1 | `GET /it/equipment` | `list_equipment` | `status: str \| None = Query(None)` (`free \| assigned`), `limit: int = 50` | `list[Laptop]` | Find free laptop pool for onboarding/replacement; avoids full-inventory dump. |
| I2 | `POST /it/equipment/assign` | `assign_laptop` | `body: AssignLaptop` | `Assignment` | Write action: laptop → employee. Needs `employee_id` join from HR (H3). Confirm before calling. |
| I3 | `POST /it/tickets` | `create_ticket` | `body: TicketCreate` | `Ticket` | Intake for new incidents; seeded demo tickets exist so agent mostly reads. |
| I4 | `GET /it/tickets/{ticket_id}` | `get_ticket` | `ticket_id: str = Path(...)` | `Ticket` | Single-ticket forensics for Q1 (breach + assignee + timestamps). |
| I5 | `POST /it/tickets/{ticket_id}/reroute` | `reroute_ticket` | `ticket_id: Path`, `body: Reroute` | `Ticket` | Write action: reassign to on-call person (needs H5). Core of Q3. Confirm before calling. |
| I6 | `GET /it/tickets/breaches` | `sla_breach_list` | `team: str \| None`, `since: datetime \| None` | `list[Ticket]` | Pre-computed breach anti-join (deadline < now AND status != resolved). Without it agent would page all tickets and compute — unreliable. Powers Q1/Q2/Q3. |

### IT Pydantic models

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

### IT router stub (`it_service/routers/it.py`)

```python
from datetime import datetime
from fastapi import APIRouter, Query, Path
from typing import Annotated
from models import Laptop, AssignLaptop, Assignment, TicketCreate, Ticket, Reroute

router = APIRouter(prefix="/it", tags=["it"])

@router.get("/equipment", operation_id="list_equipment",
            description="List laptops, filter status=free for assignable pool.",
            response_model=list[Laptop])
def list_equipment(status: Annotated[str | None, Query()] = None,
                   limit: Annotated[int, Query(le=100)] = 50) -> list[Laptop]:
    ...

@router.post("/equipment/assign", operation_id="assign_laptop",
             description="Assign a free laptop to an employee. Confirm serial + employee with user first.",
             response_model=Assignment)
def assign_laptop(body: AssignLaptop) -> Assignment:
    ...

@router.post("/tickets", operation_id="create_ticket",
             description="Create an incident ticket with SLA deadline = now + sla_hours.",
             response_model=Ticket, status_code=201)
def create_ticket(body: TicketCreate) -> Ticket:
    ...

@router.get("/tickets/breaches", operation_id="sla_breach_list",
            description="Tickets past SLA deadline and unresolved. Filter by team/since. Start here for breach triage.",
            response_model=list[Ticket])
# NOTE: declare BEFORE /tickets/{ticket_id} so static parse keeps both routes distinct.
def sla_breach_list(team: Annotated[str | None, Query()] = None,
                    since: Annotated[datetime | None, Query()] = None) -> list[Ticket]:
    ...

@router.get("/tickets/{ticket_id}", operation_id="get_ticket",
            description="Get one ticket with SLA timestamps and breach flag.",
            response_model=Ticket)
def get_ticket(ticket_id: Annotated[str, Path()]) -> Ticket:
    ...

@router.post("/tickets/{ticket_id}/reroute", operation_id="reroute_ticket",
             description="Reassign ticket to on-call owner (resolve email via get_oncall first). Confirm before calling.",
             response_model=Ticket)
def reroute_ticket(ticket_id: Annotated[str, Path()], body: Reroute) -> Ticket:
    ...
```

### IT app wiring

```python
# it_service/main.py
from fastapi import FastAPI
from routers.it import router as it_router

app = FastAPI(title="ticketing-sla")
app.include_router(it_router)

# uvicorn it_service.main:app --port 8002
```

---

## 4. Live `--discover` runbook (the arena moment)

1. **Pre-demo build (13 tools):** implement everything *except* L1 `GET /it/oncall-coverage`. Run `synapse build --auto --endpoints "<11 functional + health allowlist>" --smart-names`. Paste one MCP snippet per server. Demo Q1 (lookup join) → Q2 (breach-rate exception join).
2. **Live add:** L1 block in `it_service/routers/live_moment.py` is already on disk — baseline allowlist excludes it. Show diff on projector.
3. **Rescan:** `synapse build --discover` with the expanded allowlist (+`GET /it/oncall-coverage`) — only changed files reparsed; same server IDs so client config keeps working. New tool `it_oncall_coverage` appears.
4. **Q3 (only new tool can answer):** *"Re-route all currently-breaching tickets to whoever is on call right now"* → agent calls `it_oncall_coverage?team=support-night` (returns owned vs needs_reroute) → `reroute_ticket` per needs_reroute ticket, confirming before writes.
5. **Fallbacks:** if `--discover` stalls: (a) 60s pre-recorded video, (b) canned `OnCall` JSON, (c) `SYNAPSE_TELEMETRY=0` + local Ollama replica. Never show a spinner.

## 5. Tool-count justification (judging line)

> Exposed 10 + 1 — not 30. No raw CRUD (`update/delete employee`, `delete ticket`), no pagination helpers, no auth endpoints. Each tool maps to one agent verb in the demo script; breach logic lives server-side (`sla_breach_list`) so the agent joins instead of computing. `--smart-names` reads handler source + README for descriptions above.
