# Seed — v14 demo dataset (SQLite-only, 79 rows + infra)

> One-click deterministic dataset for the HR directory + IT ticketing demo.
> 79 counted rows anchor every risky path: BG block, visa risk, weekend starts,
> equipment holds, SLA breach, auto-renew trap, stale prod key.
> `seeded_at` = seed-run time (`seed_now()`, `SEED_NOW` overrides for tests) —
> every timestamp is stored as a fixed offset from it, so re-seeds on any date
> reproduce identical invariants (3 breached, SUB-01 +2d, KEY-01 295d stale).

## File map

| File | Role |
|---|---|
| `schema.sql` | DDL: 11 tables, FK order, partial uniques `WHERE deleted_at IS NULL`, WAL pragmas |
| `candidates.csv` (20) · `employees.csv` (20) · `equipment.csv` (20) · `tickets.csv` (20) | Core demo rows |
| `shifts.csv` (8) · `subscriptions.csv` (6) · `api_keys.csv` (5) | Roster, auto-renew trap, rotation edge |
| `seed.py` | Loader: single TX, 7 bulk `executemany` batches, in-txn `validate.check_all` (fail → `ROLLBACK`), `VACUUM INTO` snapshot, `--reset` = file copy |
| `validate.py` | Invariant gate, stdlib only: `--csv seed/` (CI) and `--db seed/demo.db` (parity) |
| `demo.db` / `seed-snapshot.db` | Live DB / post-seed snapshot (generated, committed for judge rerun) |

Infra rows (excluded from the 79-count): `shift_members` (~10, from `shifts.csv:member_ids`;
SH-08 `support-night` → EMP-014 is the deterministic on-call row so `GET /hr/oncall?team=support-night` never 404s),
`equipment_holds` (LT-1005 × CAND-002 + CAND-005: the conflict pair lives here; the `equipment` row carries only the single canonical hold CAND-002), `audit_log` (2 exemplars), `idempotency_ledger` (empty).

**Ownership boundary:** this directory is seed-side only (CSVs + `schema.sql` + loader/validator
+ this spec). `hr_service/db.py` and `it_service/db.py` (connection helpers, stores) are owned
by the HR / IT lanes — they read the schema/tables defined here but live in their services.

## Quick start

```bash
python seed/seed.py                    # full reload: schema -> 1 TX -> validate -> snapshot
python seed/seed.py --reset            # fast restore from snapshot (file copy, ~15ms)
python seed/validate.py --csv seed/    # CI gate, no DB
python seed/validate.py --db seed/demo.db   # DB parity
```

Measured (Windows, sqlite 3.38.4): `schema 5ms · clear 0ms · insert 7ms · validate 1ms ·
total 18ms · snapshot 4ms · reset 13ms` — SLA 5000ms **PASS** with ~280x headroom.

## SQLite recipe (why it is this way)

```sql
PRAGMA journal_mode = WAL;   -- persistent per DB file; re-apply after any restore
PRAGMA synchronous = NORMAL; -- per-connection; set on EVERY connection
PRAGMA busy_timeout = 5000;  -- per-connection busy handler (1-writer demo pool)
PRAGMA foreign_keys = ON;    -- per-connection; off by default
```

- **Snapshot:** `VACUUM INTO 'seed-snapshot.db'` (compact, consistent read-txn copy).
  The target **must not exist** (or be empty) — `seed.py` unlinks it first.
- **Restore:** plain file copy `seed-snapshot.db -> demo.db` while **no connection is open**,
  then reopen and re-set `PRAGMA journal_mode = WAL` — because `VACUUM INTO` output is always
  rollback-journal mode even when the source is WAL (verified: restored copy reports `wal`
  after `seed.py --reset`).
- **Live-copy warning:** never `cp demo.db` while the app runs (commits may live only in
  `-wal`, and the copy can straddle a checkpoint). `VACUUM INTO` is the safe online path.
- **Partial uniques** (soft-delete-safe, native on SQLite):
  `ux_candidates_email_active`, `ux_employees_work_email_active`
  (allows terminated `EMP-007` history, blocks a 2nd *active* dupe → Rehire modal),
  `ux_equipment_serial`, `ux_api_keys_prefix`, `ux_holds_open_per_pair
  WHERE released_at IS NULL` (LT-1005 held for 2 candidates, 2nd `assign` → `409`).

## Demo-endpoint contract (for the hr/it service lanes)

Services expose three demo-only routes over this dataset. Guards first (no DB hit on reject):

- `ALLOW_DEMO_SEED !== 'true'` → `403 demo endpoints disabled`
- `x-demo-confirm: yes` header missing → `400 missing x-demo-confirm`
- Rate-limit 6/min/IP (POSTs only). `GET /demo/status` unguarded.

```
POST /demo/seed    { version?: "v14", force?: true, include_attachments?: true }
→ 200 { ok:true, seed_version:"v14",
        counts:{candidates:20,employees:20,equipment:20,tickets:20,shifts:8,subscriptions:6,api_keys:5},
        timings_ms:{truncate,insert,validate,total}, duration_ms,
        warnings:["CAND-003 visa expires in 27d","3 SLA-breached tickets staged",
                  "1 double-hold conflict staged (LT-1005)"] }
→ 500 { ok:false, error:"seed_failed", failed_check }  # any invariant fails, DB untouched

POST /demo/reset   → 200 { ok:true, reset_to_version:"v14", duration_ms }   # <1500ms target
GET  /demo/status  → { seeded, counts, seed_version:"v14",
                       seeded_at:"<seed-run ISO Z>", last_reset_ms }
```

Reference implementation: `python seed/seed.py` (reload) / `python seed/seed.py --reset`.
Service ports stay frozen: **hr 8001, it 8002**.

### SLA rule (seed + live share one function `slaDue`)

`P1=4h · P2=8h · P3=24h · P4=48h`, `due_at = created_at + SLA` computed at seed
time from per-ticket `created_ago` offsets (see `TICKET_CREATED_AGO_H` in
`seed.py`). Exactly **3** rows satisfy `due_at < seed_time AND status != 'resolved'`
(all with `shift_id`): `T-5001` P1 breached (due −6h), `T-5002` P2 breached
(due −3h), `T-5019` P3 open-but-past-due (due −4h, stealth 3rd breach); every
other open/in-progress row is due in the future. `validate.check_breached`
infers `seed_time` from the data (max ticket `created_at`), never wall-clock,
so the count is exactly 3 whether validated today, 30 days later, or reseeded
on any date. Trap rows keep their IDs/priority/status/shift; only the three
date columns are rewritten per run (CSV values are the v14 template).
`SEED_NOW=<ISO>` monkeypatches run time for time-travel tests.

## Staged traps (each row earns its place)

| Trap | Staging | Expected behavior |
|---|---|---|
| BG-pending gate | CAND-001 signed + `bg pending` | Convert blocked |
| Happy path | CAND-002 signed + pass + citizen | Convert live → **EMP-021** (no collision: CAND-002 unlinked in `employees.csv`) |
| VISA-RISK | CAND-003 (H-1B → 2026-12-20), CAND-008 (OPT 15d), CAND-006/016/018 | Banner; CAND-016 spawns sponsorship letter |
| Weekend starts (4) | CAND-004 Sat 12-05, CAND-005 Sun 12-06, CAND-011 Sat 12-12, CAND-020 Sun 12-13 | Shift-cover warning; T-5007 ships to CAND-020 |
| BG-fail override | CAND-009 `fail` | Convert needs typed reason → `audit_log(bg.override)` (exemplar row ships) |
| Rehire | CAND-006 email/phone root == EMP-007 (terminated 2026-06-30) | Modal: reactivate EMP-007 vs override+reason; `validate` asserts exactly 1 match |
| Double-hold race | LT-1005 `on_hold`, canonical hold CAND-002 (single id, no `;`-list) + 2 `equipment_holds` rows (CAND-002/CAND-005, staged by `seed.py`) | 2nd `assign` → `409 hold_conflict` |
| On-call resolvable | SH-08 `support-night` → EMP-014 via `shift_members` (deterministic; `validate.check_oncall` asserts ≥1 roster row per demo team) | `GET /hr/oncall?team=support-night` never 404s on stage |
| Serial collision guard | LT-1008 `…991A` vs LT-1009 `…991B` (unique) | Dupe insert rejected |
| Retired asset | LT-1012 `retired`, warranty expired 2025-06-30 | Unselectable in picker |
| Auto-renew trap | SUB-01 Figma renews **seed+2d** (anchored per run), `auto_renew ON` | Seat-cancel still shows renewal warning; only `auto-renew off + reason` stops billing |
| Stale prod key | KEY-01 `last_rotated` seed−295d (expired); KEY-02 healthy (7d) | Provision blocked >90d until `POST /keys/rotate` (KEY-04 chains `replaces KEY-01`) |

Deliberate deviations from `research/final/14-seed-data.md` §3 names (invariants rule):
CAND-006 is `Rahul Verma` (must share email root with EMP-007 for the rehire match);
CAND-015 is `Aditya Rao` (a second `Rahul Verma` would break the exactly-1 rehire check).

## Validation checklist (paste into PR)

- [ ] `python seed/validate.py --csv seed/` → 0 failures
- [ ] Counts 20/20/20/20/8/6/5 (79 rows); 0 FK orphans
- [ ] `signed→date`, `visa→expiry`, `bg→completed_at`, `start≥signed` hold
- [ ] 3 breached tickets each with `shift_id`; 4 weekend starts
- [ ] Serials unique; LT-1005 canonical hold CAND-002 + 2 open `equipment_holds` rows (CAND-002/CAND-005); LT-1012 retired
- [ ] On-call resolvable: `support-night` → SH-08/EMP-014 (≥1 roster row per demo team)
- [ ] Rehire match exactly 1 (EMP-007↔CAND-006); stalest prod key KEY-01; SUB-01 ≤7d
- [ ] `python seed/seed.py` green, total <5000ms; `--reset` restores + validate green

*Seed v14 · anchored relative to seed-run time (`seed_now()`; CSVs are the v14 template) · raw SQL, no ORM (per verify/04-orm).*
