# 03 — Seed Data Verification (v14, end-to-end)

Date: 2026-11-24 · Scope: `seed/` CLI (`seed.py` + `validate.py`) + live-service probe of `POST /demo/seed` / `POST /demo/reset`.

## Commands + outputs

### 1. Full reload — `python seed/seed.py`
```
seeded v14 anchored 2026-11-23T00:00:00Z counts={'candidates': 20, 'employees': 20, 'equipment': 20, 'tickets': 20, 'shifts': 8, 'subscriptions': 6, 'api_keys': 5}
timings_ms={'schema': 12, 'clear': 4, 'insert': 6, 'validate': 1, 'total': 31, 'snapshot': 3} SLA_5000ms=PASS
warnings=['CAND-003 visa expires in 27d', '3 SLA-breached tickets staged', '1 double-hold conflict staged (LT-1005)', 'KEY-01 stale 295d blocks provision', 'SUB-01 renews 2026-11-25 (auto-renew ON)']
```
In-txn `validate.check_all` passed (no ROLLBACK); snapshot `seed-snapshot.db` rewritten via `VACUUM INTO`.

### 2. Gate — `python seed/validate.py --db seed/demo.db` and `--csv seed/`
Both modes: **0 failures**. Every `ok:` line printed in both modes, including:
- `ok: counts[…]=20/20/20/20/8/6/5`
- all 11 FK checks resolve (0 orphans; `PRAGMA foreign_key_check` returns `[]`)
- `ok: breached=3 with shift_id (['T-5001', 'T-5002', 'T-5019'])`
- `ok: weekend starts=4 (['CAND-004', 'CAND-005', 'CAND-011', 'CAND-020'])`
- `ok: double-hold LT-1005 present` · `ok: LT-1012 retired (trap intact)`
- `ok: rehire match=1 (EMP-007<->CAND-006)` · `ok: stale key KEY-01 (295d…)` · `ok: SUB-01 renews in 2d…`

### 3. Trap spot-checks (direct SQLite reads on `seed/demo.db`)
| Check | Result |
|---|---|
| Counts 20/20/20/20/8/6/5 | PASS (79 rows) |
| 0 FK orphans | PASS (`foreign_key_check` empty) |
| 3 breached, each with `shift_id` | PASS — T-5001 (breached, SH-02), T-5002 (breached, SH-03), T-5019 (open past-due, SH-01) |
| 4 weekend starts | PASS — CAND-004 Sat 12-05, CAND-005 Sun 12-06, CAND-011 Sat 12-12, CAND-020 Sun 12-13 |
| LT-1005 double-hold | PASS — `equipment` row `on_hold`/`CAND-002` + 2 open `equipment_holds` rows (HOLD-004/CAND-002, HOLD-005/CAND-005) |
| KEY-01 stale | PASS — `last_rotated 2026-02-01` (295d > 90d), expired 2026-05-01; KEY-02 healthy (7d) |
| SUB-01 ≤7d | PASS — renews 2026-11-25 (seeded+2d), `auto_renew=1` |
| Rehire exactly 1 | PASS — terminated EMP-007 `rahul.verma@…` ↔ CAND-006 `rahul.verma06@…` (email-root match) |

### 4. Timing (assert <5s)
| Op | Wall clock (`Measure-Command`, incl. interpreter) | In-tool |
|---|---|---|
| Full `seed.py` reload | ~136 ms | total 15–31 ms |
| `seed.py --reset` (snapshot copy) | ~129 ms | duration 10–13 ms |
| `validate --db` after reset | 0 failures | — |
Both **PASS** with >30× headroom vs the 5000 ms SLA.

### 5. Idempotency (CLI analogue of double `POST /demo/seed`)
Ran `seed.py` twice, dumped full DB state (counts, holds, keys, subs, tickets, IDs) after each run → **byte-identical** (`IDEMPOTENT: True`). Fixed IDs + fixed `seeded_at=2026-11-23T00:00:00Z` confirmed (CAND-001…CAND-020 stable).

### 6. Live-service probe (servers ARE up)
- `GET /demo/status` on :8001 and :8002 → `{"detail":"Not Found"}` (both)
- `POST /demo/seed`, `POST /demo/reset` (with `x-demo-confirm: yes`) on :8001 → `{"detail":"Not Found"}`
- HR openapi routes: `/health, /hr/candidates, /hr/candidates/{id}, /hr/employees, /hr/shifts` — **no `/demo/*` routes registered** in either service (grep confirms no `demo` route in `hr_service/` or `it_service/` routers).
- **Conclusion:** the `POST /demo/seed` idempotency and endpoint-timing checks are **not executable against live services — routes unimplemented**. CLI equivalents above cover the same loader logic (`seed.py` is the documented reference implementation per `seed/README.md` §Demo-endpoint contract), but the HTTP contract (guards `ALLOW_DEMO_SEED`/`x-demo-confirm`/6-per-min, response envelope) is unverified and must be covered when the hr/it lanes implement the routes.

## Verdict
Seed data **GREEN end-to-end via CLI**: counts, 0 orphans, all 7 staged traps, <5 s timings, idempotent re-runs. **GAP:** `POST /demo/seed`, `POST /demo/reset`, `GET /demo/status` return 404 on both live services — endpoint verification blocked until implemented.
