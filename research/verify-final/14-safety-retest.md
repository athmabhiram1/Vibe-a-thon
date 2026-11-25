# 14 — Safety Retest: Wired `safety_check_server.py` End-to-End (post-fix)

Date (UTC): 2026-11-24 · Workdir: `C:\Users\athma\OneDrive\Desktop\my projects\VIBE_CODE`
Scope: read-only run, no code edits. Driver scripts lived in `%TEMP%\opencode\` (never in repo).

## Verdict: PASS (17/18 live assertions; 1 miss = driver expectation error, corrected below)

The Kill-5 wiring fix is real: `onboard(confirm=True)` now mints **real** `EMP-NNN`
ids from HR, writes a **real** IT assignment, reroutes a **real** ticket, and records
ledger + hash-chained audit rows. Deny paths (injection, BG-fail) hold. Replay is cached.

## Command log (all times UTC 2026-11-24)

### 1. Baseline
- `:8001`/`:8002` already up (PIDs 30700/38660, Python 3.11). Code verified via
  `GET /openapi.json`: both expose `/demo/*` routes and HR exposes `/oncall`
  (`hr_get_oncall`) — post-fix code confirmed running, so instances were reused.
- `GET /hr/demo/status` → `seeded:true`, counts `20/20/20/20/8/6/5`. Pristine.
- `safety_ledger.db` / `audit.jsonl` absent. Clean slate.
- `GET /hr/oncall?team=support-night` → `EMP-014 Kiran Desai`. Q3 anchor resolves.

### 2. Full cycle against `safety_check_server.onboard` (in-process, HR/IT over HTTP)
CAND-002 (Priya Nair, bg `pass`, start 2026-11-30 Monday → Class B), laptop `MN-2002`
(only `available` asset class left; all laptop-category rows are on_hold/assigned —
see §Failure analysis #1), key `retest-key-002`:

| # | Step | Result |
|---|------|--------|
| 1 | stage (`confirm=False`) | `preview`, `risk_class B`, `prv_b77b4eba` — PASS |
| 2 | approve (`confirm=True` + hash + key) | `applied`, receipt `ACTIVE EMP-021` — PASS |
| 3 | HR cross-check `/hr/demo/status` | employees `20→21` — PASS |
| 4 | IT cross-check `GET /it/equipment` | `MN-2002` `available→assigned` — PASS |
| 5 | receipt assignment | `employee_id EMP-021` — PASS |
| 6 | `verify_audit_chain()` | `ok:true`, dense seq, `firstBadSeq None` — PASS |
| 7 | ledger lookup `(demo-agent,onboard.execute,key)` | `SUCCEEDED`, `resource_id EMP-021` — PASS |
| 8 | duplicate approve (same key+hash) | `already_applied`, counts identical — PASS |
| 9 | injection (`attacker@evil.com`) | `denied … injection_blocked` — PASS |
| 10 | BG-fail CAND-009 stage + activate | both `denied … bg_fail_blocked` — PASS |
| 11 | Q3: breaches → oncall → reroute | breaches contain T-5001; oncall EMP-014; reroute to hire `200` then to on-call `200`; final `assignee_email=kiran…` — PASS ×4 |
| 12 | `python eval/run.py` | `39/40 (97.5%), block 96.8%, FP 0.0%`, both gates PASS — PASS |
| 13 | `pytest tests/test_guards_smoke.py -q` | `11 passed` — PASS |

### 3. Reset
- `python seed/seed.py --reset` → v14 `20/20/20/20/8/6/5`, `duration 13ms`; validator
  `seed/validate.py --db` → **0 failures**; live `/hr/demo/status` → `seeded:true`.
- Deleted `safety_ledger.db`, `audit.jsonl` (Test-Path False/False). No repo edits
  (`git` shows VIBE_CODE untracked as a whole; no tracked file touched except the
  deterministic `eval/scorecard.csv` regen).
- Both services were found **down** post-reset (sibling lane killed PIDs 30700/38660);
  rebooted via `python -m uvicorn hr_service.main:app --port 8001` /
  `it_service.main:app --port 8002`, health `{"ok":true}` ×2, breaches exactly
  `[T-5001, T-5002, T-5019]` (matches `validate.py`), on-call resolves. Left running.

## Failure analysis (2 items, neither is product code)

1. **No `available` laptop-category asset exists.** Seed has zero `available` laptops,
   so the live cycle used monitor `MN-2002` (asset_tag in `serial` field). Safety `_hold`
   checks asset_tags (`safety_check_server.py:62-64`) while IT `assign_laptop`
   matches `WHERE asset_tag=?` (`it_service/db.py`), so the path is coherent — but a
   judge demo wanting a laptop assign needs one seeded `available` laptop or an
   honest "monitor-as-stand-in" line. Data nit, not a wiring bug.
2. **Driver assertion errors (mine, corrected):** `Ticket` exposes `assignee_email`,
   not `assignee_id`; `Laptop` exposes `serial` (= asset tag), not `asset_tag`.
   First driver run scored 15/18 on these two shapes; rerun with corrected assertions:
   17/18, the last "FAIL" being my hardcoded `EMP-022` guess — the concurrent reseed
   (§3 below) had recycled the sequence, so the second run correctly minted `EMP-021`
   again. All product assertions passed.

## Environment hazard (for the coordinator)
- A **concurrent lane reseeded `seed/demo.db` at ~15:08 IST mid-run**
  (file mtime 15:08:09; first run's EMP-021 vanished while `audit.jsonl` survived),
  and later **killed both uvicorns**. Evidence re-captured in one tight run; final
  state verified pristine afterwards. Sibling lanes should announce
  seed/reset + kill operations (or serialize on the DB file).
- Two orphaned `hygiene-venv2` uvicorn processes (PIDs 48032/51216) hold no ports
  (bind failed); harmless but worth reaping.

## Re-check routing
- PASS stands unless `safety_check_server.py`, `hr/it_service/db.py`, or seed CSVs
  change — then rerun `%TEMP%` driver `safety_retest_14b.py` (keys `retest-key-002`…)
  with fresh keys and re-verify `verify_audit_chain`.
