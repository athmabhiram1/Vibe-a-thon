# 18 — Full Green Re-verification Pass

Date (UTC): 2026-11-24 ~17:15Z (server clock; local IST 22:45) · Workdir: `C:\Users\athma\OneDrive\Desktop\my projects\VIBE_CODE`
Scope: reboot :8001/:8002 from disk (kill stale first) → health ×2 → demo status seeded v14 exact counts → H5 + L1 live → `validate --db` 0 failures → `eval/run.py` gates PASS → pytest smoke green → `frontend.html` probe (queue CAND-002, 3 breaches).

## Verdict: GREEN — 8/8 gates PASS, 0 reds

| # | Gate | Expect | Got | Result |
|---|------|--------|-----|--------|
| 1 | Kill stale :8001/:8002 | ports closed | both PIDs terminated, no LISTENING | PASS |
| 2 | Reboot from disk | LISTENING on :8001 + :8002 | HR PID 47964, IT PID 23696 | PASS |
| 3 | Health ×2 | `{"ok":true}` ×2 | `{"ok":true}` / `{"ok":true}` | PASS |
| 4 | Demo status seeded v14 | 20/20/20/20/8/6/5, v14 | exact on both services | PASS |
| 5 | H5 + L1 live | H5 EMP-014, L1 breach_count=3 | both 200, EMP-014, 3 breaches | PASS |
| 6 | `seed/validate.py --db` + `--csv` | 0 failures | 0 + 0 failures | PASS |
| 7 | `eval/run.py` | block≥90% PASS, fp≤15% PASS | 96.8% / 0.0%, exit 0 | PASS |
| 8 | pytest smoke + frontend probe | green; queue CAND-002 + 3 breaches | 11 passed; queue 20 w/ CAND-002, breaches [T-5001,T-5002,T-5019] | PASS |

## Command log (every command + output)

### 0. Pre-check: repo + interpreter

```
$ git log --oneline -5; python --version; pip show uvicorn fastapi | (Name/Version)
e41db76 feat: Task 1 skeleton healthz + lifespan queue stub (TDD RED-GREEN)
2222f63 first commit
c2faa33 Add AI PCB backend with proper .gitignore
7fddf10 first commit
Python 3.11.0
Name: uvicorn / Version: 0.54.0
Name: fastapi / Version: 0.165.0
```

### 1. Find stale listeners

```
$ netstat -ano | Select-String ":8001 |:8002 "
TCP  127.0.0.1:8001  LISTENING  7772
TCP  127.0.0.1:8002  LISTENING  17372
(+ TIME_WAIT rows omitted)
$ Get-CimInstance Win32_Process -Filter "Name='python.exe'" | (PID, CommandLine)
7772  "...python.exe" -m uvicorn hr_service.main:app --port 8001
17372 "...python.exe" -m uvicorn it_service.main:app --port 8002
```

Stale: PID 7772 = HR :8001, PID 17372 = IT :8002 (pre-existing background uvicorn, not from this session).

### 2. Kill stale (reboot prerequisite)

```
$ taskkill /PID 7772 /F
SUCCESS: The process with PID 7772 has been terminated.
$ taskkill /PID 17372 /F
SUCCESS: The process with PID 17372 has been terminated.
$ netstat -ano | Select-String ":8001 |:8002 " | Select-String "LISTENING"
(no output — both ports closed)   PASS
```

### 3. Reboot from disk (fresh uvicorn off current tree)

```
$ Start-Process python -ArgumentList "-m","uvicorn","hr_service.main:app","--port","8001" -WindowStyle Hidden
$ Start-Process python -ArgumentList "-m","uvicorn","it_service.main:app","--port","8002" -WindowStyle Hidden
$ Start-Sleep -Seconds 6; netstat -ano | Select-String ":8001 |:8002 " | Select-String "LISTENING"
TCP  127.0.0.1:8001  LISTENING  47964
TCP  127.0.0.1:8002  LISTENING  23696     PASS (new PIDs, served from disk)
```

### 4. Health ×2 + OpenAPI operation counts

```
$ curl.exe -s http://127.0.0.1:8001/health
{"ok":true}    PASS
$ curl.exe -s http://127.0.0.1:8002/health
{"ok":true}    PASS

$ (HR openapi operationIds)
9
['hr_create_employee','hr_demo_reset','hr_demo_seed','hr_demo_status','hr_get_candidate',
 'hr_get_oncall','hr_health_check','hr_list_candidates','hr_shift_calendar']

$ (IT openapi operationIds)
11
['it_assign_laptop','it_create_ticket','it_demo_reset','it_demo_seed','it_demo_status',
 'it_get_ticket','it_health_check','it_list_equipment','it_oncall_coverage',
 'it_reroute_ticket','it_sla_breach_list']
```

HR 9 ops (5 functional + H5 + health + 3 demo) / IT 11 ops (7 functional + L1 + health + 3 demo) = 20 total. H5 `hr_get_oncall` present, L1 `it_oncall_coverage` present, 6 demo ops present (Synapse-allowlist-excluded per `plan.md` §2). Matches `probe_live.py` assertions exactly.

### 5. Demo status (seeded v14, exact counts) + H5 + L1

```
$ curl.exe -s http://127.0.0.1:8001/hr/demo/status
{"seeded":true,"counts":{"candidates":20,"employees":20,"equipment":20,"tickets":20,
"shifts":8,"subscriptions":6,"api_keys":5},"seed_version":"v14",
"seeded_at":"2026-11-23T00:00:00Z","last_reset_ms":null}    PASS

$ curl.exe -s http://127.0.0.1:8002/it/demo/status
{"seeded":true,"counts":{"candidates":20,"employees":20,"equipment":20,"tickets":20,
"shifts":8,"subscriptions":6,"api_keys":5},"seed_version":"v14",
"seeded_at":"2026-11-23T00:00:00Z","last_reset_ms":null}    PASS

$ curl.exe -s "http://127.0.0.1:8001/hr/oncall?team=support-night"      (H5)
{"team":"support-night","employee_id":"EMP-014","name":"Kiran Desai",
"email":"kiran.desai@demo.example.com",...}    PASS (200, on-call EMP-014, never 404 on staged team)

$ curl.exe -s "http://127.0.0.1:8002/it/oncall-coverage?team=support-night"   (L1)
{"team":"support-night",...,"oncall":{"employee_id":"EMP-014",...},
"breaching_tickets":[
 {"ticket_id":"T-5001",...,"status":"breached","owned_by_oncall":true},
 {"ticket_id":"T-5019",...,"status":"open","owned_by_oncall":true},
 {"ticket_id":"T-5002",...,"status":"breached","owned_by_oncall":false}],
"owned_by_oncall":["T-5001","T-5019"],"needs_reroute":["T-5002"],"breach_count":3}  PASS
```

L1: exactly 3 breaching tickets, owned vs needs_reroute split correct (T-5002 owned by farhan.sheikh, needs reroute to on-call). NOTE (by design, not red): unprefixed `/demo/status` returns `{"detail":"Not Found"}` on both services — demo routes live under service prefixes (`/hr/demo/*`, `/it/demo/*`; openapi paths confirm). The 03-seed.md-era 404 was against the unprefixed path, which was never a registered route.

### 6. Seed gate — `validate.py` (DB + CSV modes)

```
$ python seed/validate.py --db seed/demo.db
ok: counts[candidates]=20
ok: counts[employees]=20
ok: counts[equipment]=20
ok: counts[tickets]=20
ok: counts[shifts]=8
ok: counts[subscriptions]=6
ok: counts[api_keys]=5
ok: FK employees.candidate_id resolves
ok: FK employees.manager_id resolves
ok: FK employees.rehire_of resolves
ok: FK equipment.assigned_to resolves
ok: equipment.hold_for_candidate single canonical (no ;-list hack)
ok: FK equipment.hold_for_candidate resolves
ok: FK tickets.requester_id resolves
ok: FK tickets.requester_candidate resolves
ok: every ticket has a requester
ok: FK tickets.assignee_id resolves
ok: FK tickets.shift_id resolves
ok: FK subscriptions.owner_id resolves
ok: signed->date, visa->expiry, bg->completed_at, start>=signed
ok: breached=3 with shift_id (['T-5001', 'T-5002', 'T-5019']) vs ref 2026-11-24T15:28:49+00:00
ok: weekend starts=4 (['CAND-004', 'CAND-005', 'CAND-011', 'CAND-020'])
ok: visa-risk=5
ok: bg-pending=7
ok: serials unique (near-dupe 991A/991B distinct)
ok: double-hold LT-1005 canonical hold CAND-002 (equipment row single)
ok: double-hold LT-1005 ledger pair CAND-002+CAND-005 (equipment_holds)
ok: LT-1012 retired (trap intact)
ok: rehire match=1 (EMP-007<->CAND-006)
ok: stale key KEY-01 (295d, blocks provision)
ok: SUB-01 renews in 2d (auto-renew trap armed)
ok: on-call support-night resolves (1 roster row(s): SH-08/EMP-014)

0 failure(s).    PASS (exit 0)

$ python seed/validate.py --csv seed/
(identical ok: lines; breached=3 vs CSV ref; ledger check skipped in CSV mode by design)

0 failure(s).    PASS (exit 0)
```

All 7 staged traps intact (breach trio, weekend×4, LT-1005 double-hold pair, LT-1012 retired, EMP-007↔CAND-006 rehire, KEY-01 stale, SUB-01 auto-renew). Breach predicate is data-anchored (`_ref_time` from newest ticket), so no wall-clock drift (cf. 02-boot-endpoints.md §7 old 14-vs-3 FAIL — resolved by the pinned reference).

### 7. Eval gates — `eval/run.py`

```
$ python eval/run.py
cases=40 malicious=31 benign=9
guarded  accuracy=97.5% (39/40 strict) block-rate=96.8% fp=0.0% latency(MOCK) p50=11.0ms p95=11.0ms [+11.0ms simulated, NOT measured]
baseline block-rate=29.0% fp=11.1% (weak-by-design single-signal comparator)
note: M05 WARN-as-designed - citation-flag means block-intent (flag + require real doc link)
wrote C:\Users\athma\OneDrive\Desktop\my projects\VIBE_CODE\eval\scorecard.csv
  abuse: 9/9 blocked
  ambiguous_scope: 4/5 blocked
  duplicate: 5/5 blocked
  injection: 7/7 blocked
  pii: 5/5 blocked
GATE block>=90%: PASS  GATE fp<=15%: PASS    (exit 0)
```

The 1 strict miss is the known M05 WARN-as-designed (citation-flag = block-intent, scored as miss vs BLOCK label) — disclosed in-harness, not a regression.

### 8. Pytest smoke

```
$ python -m pytest tests/ -q
...........  [100%]
11 passed in 0.03s    PASS
```

(`tests/test_guards_smoke.py`, 11/11.)

### 9. `probe_live.py` (in-repo live-endpoint script)

```
$ python probe_live.py
HR ops (9): [...]
IT ops (11): [...]
DEMO ops excluded from Synapse allowlist (6): [...]
GET /it/oncall-coverage -> 200
coverage: team=support-night oncall=kiran.desai@demo.example.com breaches=3 owned=['T-5001', 'T-5019'] reroute=['T-5002']
unknown team 404 (consistent with H5): OK
H5 GET /hr/oncall -> 200 EMP-014
ALL LIVE-ENDPOINT CHECKS PASSED    (exit 0)
```

### 10. Frontend probe (what `frontend.html` fetches at load)

Mimics the page's boot sequence — H1 queue → H2 CAND-002 detail → I6 breaches — plus static wiring grep:

```
queue_n=20
CAND-002 in queue=True
detail CAND-002=CAND-002 Priya Nair signed
breaches_n=3
breach_ids=['T-5001', 'T-5002', 'T-5019']
HIT /hr/candidates
HIT /hr/candidates/
HIT /it/tickets/breaches
HIT /hr/oncall
HIT CAND-002
MISS it_oncall_coverage
HIT hr_get_oncall
frontend_bytes=42312
```

Queue shows CAND-002 (Priya Nair, signed) selected by default; breach board shows exactly 3. PASS on the stated probe criteria.

## Reds: none (0)

No FAIL lines in any gate. Two notes, both informational (severity: info, no file/line defect):

1. **INFO — unprefixed `/demo/status` 404s by design.** Routers mount demo endpoints under service prefixes (`hr_service/routers/hr.py`, `it_service/routers/it.py` → `/hr/demo/*`, `/it/demo/*`; confirmed in live openapi `paths`). The 03-seed.md 404 observation predates the prefixed implementation. No action.
2. **INFO — `frontend.html` TOOLS registry (lines 301–316) has no `it_oncall_coverage` entry.** The Discovery pane drives on-call via H5 (`GET /hr/oncall`, `checkOncall`, line 664) and does the breach×on-call join client-side before I5 reroute — L1 is verified live server-side (§5) and exercised by `probe_live.py`. If the stage script wants a one-click L1 call in-page, add one TOOLS row + fetch; cosmetic, not a gate.

## Residuals carried (unchanged, not re-probed here)

Per 17-resignoff.md: `demo/golden.mp4` still owed (P0), quota-proof PNGs pending, SHOTLIST ID/choreography sweep (F2) pending, `benchmark/run.js` + UNMEASURED fill pending. None are greenpass gates; listed so this report doesn't overclaim.
