# 25 — Reseed: recording-clean database

Date: 2026-11-25T20:15:57+05:30 (IST)
Scope: DB reset ONLY. No code touched.
Intended side effect: E2E test rows (EMP-021/022/023 etc.) wiped.

## Commands

```
python seed/seed.py --reset
python seed/validate.py --db seed/demo.db
```

## Reset output (run 1)

```
reset to v14 counts={'candidates': 20, 'employees': 20, 'equipment': 20, 'tickets': 20, 'shifts': 8, 'subscriptions': 6, 'api_keys': 5} duration_ms=12
EXIT: 0
```

## Timing (run 2, post-verify)

- Internal `duration_ms=10` (seed.py self-report)
- Wall `Measure-Command { python seed/seed.py --reset }` → **0.1126 s**
- Assert reset < 5 s → **PASS** (~44x margin)

## Validate output (expect 0 failures, 20/20/20/20/8/6/5, 3 breached — all met)

```
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

0 failure(s).
EXIT: 0
```

## E2E-wipe confirmation (INTENDED)

```
employees total: (20,)
EMP-021+: (0,)            -- no EMP-021/022/023 leftovers
max employee: ('EMP-020',)
audit rows: (2,)          -- 2 exemplar seed rows only
idempotency rows: (0,)    -- empty at seed
```

## Code untouched

- `git status --porcelain` → only pre-existing `M eval/scorecard.csv` + untracked `.vscode/`, parallel-agent research files. No source files modified by this task.
- `seed/demo.db` is gitignored (`.gitignore:3: *.db`), so the rebuilt DB does not dirty the tree. Verified via `git check-ignore -v`.
- One temp probe script (`scripts/tmp_check_e2e.py`) was created for the sqlite check and deleted afterwards; `git status` confirms it is gone.

## Result

RECORDING-CLEAN: schema v14, counts 20/20/20/20/8/6/5, 0 validation failures, 3 breached (T-5001/T-5002/T-5019), all trap rows intact. DB ready for recording.
