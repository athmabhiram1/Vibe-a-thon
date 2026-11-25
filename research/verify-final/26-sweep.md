# 26 — Full endpoint sweep (pre-recording)

Date: 2026-11-25 ~20:20 IST
Scope: boot + GET every HR/IT route + demo/status; ONE test-ticket write attempted. No code touched.

## Boot

- Ports busy on arrival: stale LISTENERS `8001 ← PID 31720`, `8002 ← PID 21564` → both `taskkill /F` (SUCCESS).
- Fresh boots: `python -m uvicorn hr_service.main:app --port 8001` (PID 28132, this sweep), IT side PID 13684 (`it_service.main:app --port 8002`, started 20:15:31 — parallel-boot race, adopted after verifying it serves current code incl. `/it/oncall-coverage`).
- My duplicate IT boot failed to bind (10048) and exited — expected, port already held by the fresh instance. No conflict.
- End state: **both servers LEFT RUNNING** — `8001 ← 28132`, `8002 ← 13684`.

## Health ×2 (all 200 `{"ok":true}`)

| # | Route | Status |
|---|-------|--------|
| 1 | `GET 127.0.0.1:8001/health` ×2 | 200, 200 |
| 2 | `GET 127.0.0.1:8002/health` ×2 | 200, 200 |

## HR routes `:8001` — all 200-live

| Route | Status | Key fields |
|-------|--------|------------|
| `GET /hr/candidates?limit=20` | 200 | 20 rows; keys `candidate_id/name/email/team/status`; first page `CAND-001..003` |
| `GET /hr/candidates/CAND-002` | 200 | Priya Nair, `signed`, Engineering, `priya.nair02@example.com` |
| `GET /hr/shifts?team=support-night&date=2026-11-23` | 200 | 1 row: EMP-014, `night`, `on_call:false` |
| `GET /hr/oncall?team=support-night` | 200 live | EMP-014 Kiran Desai `kiran.desai@demo.example.com`, `at=now` (2026-11-25T14:46Z) |
| `GET /hr/demo/status` | 200 | `seeded:true`, v14, counts 20/20/20/20/8/6/5 exact |

`POST /hr/employees` deliberately NOT called (destructive write, out of scope).

## IT routes `:8002`

| Route | Status | Key fields |
|-------|--------|------------|
| `GET /it/equipment?limit=50` | 200 | 20 rows; keys `serial/model/status`; first `LT-1001 MacBook Pro 14 on_hold` |
| `GET /it/tickets/breaches` | 200 | **12 rows, NOT 3** — `T-5001 T-5019 T-5002 T-5003 T-5014 T-5004 T-5005 T-5015 T-5007 T-5006 T-5016 T-5018` (see § Findings) |
| `GET /it/tickets/T-5001` | 200 | `breached`, assignee `kiran.desai@demo.example.com`, `deadline_at 2026-11-24T10:28:49Z` |
| `GET /it/oncall-coverage?team=support-night` | 200 | on-call EMP-014 Kiran Desai; `breach_count:12`, `owned_by_oncall:[T-5001,T-5019,T-5003,T-5007]` (4), `needs_reroute` (8) |
| `GET /it/demo/status` | 200 | `seeded:true`, v14, counts 20/20/20/20/8/6/5 exact |

`POST /it/equipment/assign` deliberately NOT called (destructive, out of scope).

## Write test — BLOCKED by server bug (no test ticket exists)

1. `POST /it/tickets` (SWEEP-TEST, assignee `kiran.desai@demo.example.com`, team IT, sla_hours 4):
   - Attempt 1 → 422 (client-side PowerShell quoting mangled JSON; retried via body file).
   - Attempt 2 → **500 `Internal Server Error`**, reproducible. No row written.
2. Root cause (verified in-process, exception raises before any write — DB untouched):
   `it_service/db.py:create_ticket` INSERT lists **11 columns** but `VALUES (?,?,?,?,?,'open',?,?,?,?,'portal')` has **9 placeholders** for **8 params**:
   `sqlite3.ProgrammingError: Incorrect number of bindings supplied. The current statement uses 9, and there are 8 supplied.`
   The `'open'` literal lands in the `category` slot; the `status` value is missing. **Every** `POST /it/tickets` call 500s regardless of input.
3. Reroute step **SKIPPED per constraint** ("reroute dry-run on test ticket only") — no test ticket exists, and rerouting a real ticket would be a destructive write on real data. **No test-ticket ID to record; none created.**
4. Post-sweep DB check (read-only): `tickets=20`, both `/demo/status` still `seeded:true`. **No reseed required.** Scratch file `testbody.json` removed.

## Findings / recording risks

1. **P1 — `POST /it/tickets` always 500s.** The "create ticket live" recording beat is broken until fixed. Suggested minimal fix in `it_service/db.py` (`create_ticket`): supply the missing `category` binding so `'open'` lands in `status`, e.g. `VALUES (?,?,?,?,?,?,'open',?,?,?,?,'portal')` with a `category` param (e.g. `'general'`) added to the tuple. Re-sweep POST + reroute after fix.
2. **P2 — breaches returns 12, expectation was exactly 3.** DB is clean (`seeded:true`, tickets=20), so this is **time-decay, not drift**: only 3 rows carry `status='breached'`, but `breach_list` computes past-SLA + unresolved dynamically and seeded `due_at`s (2026-11-22..24) are now all past (live now 2026-11-25). The "3 breaches" beat will show 12 on camera. Mitigate by reseeding immediately before recording (seed.py stamps times relative to run — cf. T-5001 `created_at 2026-11-24T…` vs CSV `2026-11-22`) and re-checking `/it/tickets/breaches`.
3. Otherwise green: every read route 200 with contract-shaped payloads; on-call chain (H5 → L1 coverage, owned 4 / reroute 8) joins correctly live.

## Servers (left RUNNING for recording)

- HR `:8001` ← PID 28132 (this sweep) · IT `:8002` ← PID 13684 (parallel-boot race, adopted) · both `uvicorn …main:app`, health 200 ×2 verified post-sweep.
- **Handover note (post-sweep):** my HR process (28132) was later superseded — a parallel session rebooted both services (HR `:8001` ← PID 35952, IT `:8002` ← PID 36484, both `uvicorn …main:app`). Re-verified: both `/health` 200 and `/it/oncall-coverage` serves current code (`support-night` / EMP-014 / `breach_count:12`, matching this sweep). Recording precondition (servers RUNNING) still holds.
