# 02 — Boot + Endpoint Verification

Date (UTC): 2026-11-24 · Workdir: `C:\Users\athma\OneDrive\Desktop\my projects\VIBE_CODE`

## Command log

### 1. Install dependencies
```
pip install -r requirements-hr.txt -r requirements-it.txt
```
Output (tail): all requirements already satisfied (`fastapi==0.165.0`, `uvicorn`,
`pydantic>=2.10,<3`, `aiosqlite`, `fastmcp==4.2.4`, `email-validator==2.2.0`);
only stderr was pip's `26.2.1 -> 26.3` upgrade notice (exit 1 is the notice
surfacing as NativeCommandError in the PowerShell host, not a failed install).
**PASS**

### 2. Boot HR service
```
python -m uvicorn hr_service.main:app --port 8001   (background, PID 37436)
```
Log: `Started server process … Application startup complete. Uvicorn running
on http://127.0.0.1:8001`. **PASS**

### 3. Boot IT service
```
python -m uvicorn it_service.main:app --port 8002   (background, PID 35744)
```
Log: `Started server process … Application startup complete. Uvicorn running
on http://127.0.0.1:8002`. **PASS**

### 4. Health checks
```
curl.exe -s http://127.0.0.1:8001/health  →  {"ok":true}
curl.exe -s http://127.0.0.1:8002/health  →  {"ok":true}
```
**PASS ×2**

### 5. HR candidates
```
curl.exe -s "http://127.0.0.1:8001/hr/candidates?limit=1"
→ [{"candidate_id":"CAND-001","name":"Aarav Mehta",
     "email":"aarav.mehta01@example.com","team":"Engineering","status":"signed"}]
```
First row is CAND-001 as expected. **PASS**

### 6. IT breaches
```
curl.exe -s http://127.0.0.1:8002/it/tickets/breaches
```
Returned **14** tickets, all `"breached":true`:
T-5019, T-5001, T-5002, T-5003, T-5015, T-5005, T-5014, T-5004, T-5016,
T-5007, T-5017, T-5006, T-5018, T-5020. Expected exactly 3. **FAIL**
(see analysis below).

### 7. OpenAPI operationIds
HR (`GET /openapi.json`, 5 ops):
`hr_health_check`, `hr_list_candidates`, `hr_get_candidate`,
`hr_create_employee`, `hr_shift_calendar` — `hr_get_oncall` (H5) absent.
**PASS** (5 with H5 absent)

IT (`GET /openapi.json`, 7 ops):
`it_health_check`, `it_list_equipment`, `it_assign_laptop`,
`it_create_ticket`, `it_sla_breach_list`, `it_get_ticket`,
`it_reroute_ticket`. **PASS** (7)

### 8. Kill servers
```
taskkill /PID 37436 /F  → SUCCESS
taskkill /PID 35744 /F  → SUCCESS
curl.exe --max-time 3 http://127.0.0.1:8001/health  → connection refused
```
**PASS** — both processes terminated, ports closed.

## Pass/fail table

| # | Check | Expect | Got | Result |
|---|-------|--------|-----|--------|
| 1 | pip install both requirements | clean install | already satisfied, only pip-upgrade notice | PASS |
| 2 | boot hr_service :8001 | startup complete | startup complete | PASS |
| 3 | boot it_service :8002 | startup complete | startup complete | PASS |
| 4 | GET /health :8001 | `{"ok":true}` | `{"ok":true}` | PASS |
| 5 | GET /health :8002 | `{"ok":true}` | `{"ok":true}` | PASS |
| 6 | GET /hr/candidates?limit=1 | CAND-001 first | CAND-001 (Aarav Mehta) | PASS |
| 7 | GET /it/tickets/breaches | exactly 3 breached | 14 breached | **FAIL** |
| 8 | HR openapi.json | 5 ops, H5 absent | 5 ops, `hr_get_oncall` absent | PASS |
| 9 | IT openapi.json | 7 ops | 7 ops | PASS |
| 10 | kill servers | ports closed | ports closed | PASS |

## Failure analysis (check #7)

- Exact error: `GET /it/tickets/breaches` returned 14 items instead of the
  expected 3 (list in §6 above).
- Suspected location: `it_service/db.py:223-245` (`breach_list`) +
  `it_service/db.py:49-53` (`_ticket_from_row`). The breach predicate is
  live wall-clock: `now = _utcnow()` (line 231) and
  `due_at < now` (lines 51-53, 239). Seed `due_at` values cluster
  2026-11-21…2026-11-24, so by 2026-11-24 more tickets have aged past SLA
  than at seed time. This is time-drift, not a routing/schema bug: endpoint,
  shape (`Ticket` with `breached:true`), and ordering are all correct.
- If a frozen count of 3 is required, pin `now` (env var / query param) or
  re-seed relative to run time instead of asserting an absolute count.
