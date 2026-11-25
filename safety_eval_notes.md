# Safety tool eval notes — `safety_check_server.py` (Synapse Custom 1-tool)

Date: 2026-11-22. FastMCP **4.2.4** verified installed (`pip install fastmcp==4.2.4`).
Spec: plan.md §5 + `research/final/05-fastmcp-custom.md` + `research/final/13-safety-audit.md`
+ `research/brainstorm/04-track2-safety.md`.

## What was built

Single guarded composite `@mcp.tool(name="onboard", …)` in `safety_check_server.py`
(explicit `name=`/`description=`/`tags=`/`meta=`; no mount/namespace).
8 private helpers in pipeline order:
`_verify_offer → _bg_gate → _rbac → _stage → _hold → _schedule → _preview → _activate`.
Params include `confirm`, `preview_hash`, `idempotency_key` (+ offer fields, `actor`).

- Stage (`confirm=False`): read-only, returns `⚠️ WRITE PREVIEW <id>` prompt
  (exact §4 Class-B wording), `preview_id` + `preview_hash`, warnings
  (BG-pending, laptop-hold conflict, weekend start). One audit line (`require_approval`).
- Activate (`confirm=True` + exact hash + key): CHECK (ledger-replay → staged lookup
  bound to actor → 10-min TTL → server-side hold re-derivation) → ACT → RECORD.
- Idempotency ledger: sqlite `onboarding_idempotency`, PK `(actor_id, operation, key)`,
  `IN_PROGRESS/SUCCEEDED/FAILED` + fencing `lease_token`, `expires_at = now+24h`.
  Same key+hash → `already_applied` (cached, never re-executes); same key+drifted
  hash → `IDEMPOTENCY_CONFLICT` 409; `IN_PROGRESS` → wait+retry.
- `${ENV:VAR}` refs + secret-shaped values (`ghp_|xoxb-|sk-|AKIA`) redacted at every
  sink (plans, prompts, ledger bodies, audit lines); `preview_hash` over redacted
  canonical JSON (`sort_keys`, `separators=(",",":")`, `ensure_ascii=False`).
- `audit.jsonl`: `seq` from 1, `hash = sha256(prev_hash ‖ canonical(line))`,
  genesis `0×64`; `verify_audit_chain()` checks seq → prev-link → recomputed hash,
  reports `firstBadSeq` (+ `head_hash`/`count` for external anchoring); unparseable
  lines reported as breaks, not crashes.
- Deny-closed: unknown op / missing scope / bad offer / BG-fail / retired LT-1012 /
  held LT-1005 (at commit → `precondition_failed`) all deny + audit.

## Inline verification (fresh temp ledger+audit per run)

| # | Flow | Result |
|---|---|---|
| 1 | `import safety_check_server` + `get_tool('onboard')` name/params | PASS (10 params incl. confirm/preview_hash/idempotency_key) |
| 2 | Stage → preview + hash, no writes | PASS |
| 3 | Activate minus hash/key → deny (`no_preview` / `missing_idempotency_key`) | PASS |
| 4 | Approve → `applied` + `ACTIVE EMP-…` receipt | PASS |
| 5 | Replay same key+hash → `already_applied`, cached, no re-execution | PASS (after fix: ledger checked **before** staged lookup, per 13 §7) |
| 6 | Same key + different args → `IDEMPOTENCY_CONFLICT` 409 | PASS |
| 7 | Wrong/expired `preview_hash` → deny; missing fields → deny; BG-fail → deny | PASS |
| 8 | `${ENV:…}`/secret shapes absent from sinks; hash over redacted form | PASS |
| 9 | `verify_audit_chain` on 8-line log → ok, `firstBadSeq=None` | PASS |
| 10 | Tampered last line → `ok=False`, `firstBadSeq=3` (incl. JSON-corruption case) | PASS (after fix: JSONDecodeError → break report) |

## Bugs found by the tests (both fixed)

1. Replay-after-consume returned `denied/no_preview` — staged lookup ran before the
   ledger check. Fixed: ledger-first replay/CONFLICT/IN_PROGRESS in activate path.
2. `expires_at` was set to `now` (immediate logical expiry). Fixed: `now+24h`.
3. Verifier crashed (`JSONDecodeError`) on a syntactically corrupted line. Fixed:
   catch → report `firstBadSeq`.

## Probes / environment notes

- `execute`-catalog `search()`/searxng probe: **not available** — the Code Mode tool
  catalog in this session exposes only `opencode.*` tools (session/worktree/models/
  MCP resources); no `search` function exists to call. Logged here instead of run.
- Demo traps honored: BG `fail` blocks, `pending` warns; LT-1005 hold conflict and
  LT-1012 retired enforced; weekend starts flagged in schedule slot.
- Live budget: all gates are local sqlite/file ops (µs–ms); well under the 500 ms budget.
- Scratch test files (`_safety_inline_test.py`, `_safety_check2.py`) removed after use.
