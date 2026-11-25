# 01 — ORACLE KILL ATTEMPT: Track 3 Onboard Copilot (HR :8001 + IT :8002)

**Verdict: CONDITIONAL NO-GO. The APIs + seed + safety file are real. The Synapse integration, the eval number, the demo-reset story, and the benchmark packet are not. A judge who reads two files kills you in 90 seconds.**

Scope read: `plan.md`, `reconcile/RECONCILE.md`, `research/build/49-master-plan.md`, plus ground truth in `hr_service/`, `it_service/`, `eval/`, `safety_check_server.py`, `evidence/quota-log.md`, `submission/{BENCHMARKS,LIMITS}.md`, `guide.txt`.

---

## KILL 1 — The 96.8% is a rigged mock that tests the wrong code (fastest judge kill)

**Claim:** plan.md §5/§7/G5: "guarded 96.8% block / 0% FP @ ~11ms mock", "measured ✅".

**Evidence:**

- `eval/run.py:71` — latency is fabricated: `dt_ms = ... + 11.0  # simulated policy cost`. It is not a measurement. `submission/BENCHMARKS.md:19` then launders it as a benchmark row ("96.8% block / 0% FP @ ~11ms").
- `eval/run.py:32,40,46,57,66` — `guarded()` branches on the answer key: `if c["category"]=="pii" and c["expected_verdict"]=="BLOCK"`, `if c["id"] in ("I08","I09")`, `if c["id"].startswith("P") and c["expected_verdict"]=="ALLOW"`, `if ... c["expected_verdict"]=="BLOCK"`. The guard reads the label it is being scored against. Any judge who opens `run.py` calls this cheating/overfit. Repro: `grep -n expected_verdict eval/run.py` → 4+ hits inside the "policy".
- `eval/run.py:74-81` — `baseline()` is `ALLOW` unless `tool=="exec_sql"` (a tool that appears in zero cases). Baseline 0% is therefore a tautology, not a comparison. `tests/test_guards_smoke.py:118-120` even brags about it ("baseline is allow-all: proves suite is non-trivial" — it proves the opposite).
- `eval/scorecard.csv:40` — M05 (expected BLOCK) returns `WARN`, counted nowhere. 30/31 = 96.8% only if WARN is silently dropped; true accuracy is 39/40 with one miss on a citation-integrity case — the exact category a safety judge cares about. `test_guards_smoke.py:111-117` asserts WARN "by design", i.e. the test locks in the miss.
- **The evaluated code is not the shipped code.** `run.py:guarded()` is regexes over synthetic JSON. The actual enforcement artifact, `safety_check_server.py:onboard()` (597 lines, sqlite ledger + hash chain), is never called by the eval. Command proof: `grep -rn "safety_check_server\|verify_audit_chain\|_ledger" eval/ tests/ seed/` → zero hits outside the server file itself. Claim "safety measured" with zero coverage of the safety server.
- Live budget "≤500ms" (plan.md §5, LIMITS.md:22) has no measurement anywhere; `BENCHMARKS.md:7-21` is all `TODO_s`/`TODO_ms`/`TODO_GB`.

**What the judge asks:** "Show me the eval running against your real MCP tool, not a regex over its own answer key." There is no answer.
**Fix:** promote eval to call `safety_check_server.onboard` + real FastAPI writes in-process; delete label-dependent branches; replace fake baseline with last-year/no-guard prompt passthrough; measure wall-clock p50/p95. Cost: **3-5h** (rewrite `eval/run.py` + 20 live cases + rerun scorecard).

## KILL 2 — Zero Synapse artifacts: the core track requirement is unproven

**Claim:** plan.md §§1/4/6, 49-master-plan D5/D8: "10 tools baseline / 11 post-discover", quota-logged, same-server-ID live rebuild.

**Evidence:**

- `evidence/quota-log.md:18-22` — all three rows are `TODO_YYYY-MM-DD / TODO / TODO% / TODO/10 / TODO.png`. No `synapse info`, no `surface_cache.json`, no server IDs have ever been recorded. Command proof: `dir .synapse 2>nul || echo NO_SYNAPSE_DIR`, `findstr /s surface_cache *.md` → only aspirational mentions.
- `glob **/*.py` (repo root listing) — no `synapse_auto_server.py`, no `<tool>_server.py`, no generated file of any kind. Yet `.cursor/mcp.json:4-5` points the `hr-api` server at `"args": ["${workspaceFolder}/synapse_auto_server.py"]` — **the live client config points at a file that does not exist**. Repro: `python synapse_auto_server.py` → `No such file`. Inspector/Cursor boot fails on the documented path.
- `safety_check_server.py:1-20` is hand-written FastMCP, not `synapse build --custom` output. Track 3 allows Custom-optional, but the guide (`guide.txt:60-70`) judges "how central Synapse is" and demands "both MCP servers, the agent, and a demo with at least two questions that need both systems, plus the live update." Today you can show zero Synapse servers. The strongest question — "run `synapse info` right now" — cannot be answered.
- Tool-count arithmetic is already wrong before any build. `RECONCILE.md:57-60` counts HR=5 + IT=7 = 12 `operation_id`s because both `hr_health_check` (`hr_service/main.py:10`) and `it_health_check` (`it_service/main.py:9`) are exposed. Plan's "10 baseline / 11 post-discover" silently excludes health endpoints Synapse Auto will happily ingest (`--all-endpoints`). Expect 12/13 on stage, breaking G2/G6 gates and the "8 tools deleted. 1 decision" pitch line (`plan.md:131`).
- Quota story is fiction: `LIMITS.md:7` is `TODO / 10 servers, TODO / 100k lines`, proof PNGs are `(TODO)`. T8 tripwire ("freeze if <40%") cannot fire because nothing is logged.

**What the judge asks:** "Paste your two `SYNAPSE_SERVER_ID`s and rebuild one live." There is nothing to paste.
**Fix:** run the three hosted builds now, log `synapse info` before/after, exclude or pin health endpoints, correct all docs to 12/13 or filter. Cost: **2-4h** (needs API key issuance + network) + 30min doc sweep. If key issuance is slow, this alone slips D5.

## KILL 3 — `POST /demo/seed|reset` does not exist: the "judge rerun in 60s" is fiction

**Claim:** plan.md §3/§1: "`POST /demo/seed` (single txn) + `POST /demo/reset` + `GET /demo/status`", "judge rerun: pip install → uvicorn hr:8001 + it:8002 (3 cmds, <60s)"; `submission/README.md:54` repeats it.

**Evidence:**

- `grep -rn "demo" --include=*.py hr_service/ it_service/` → zero route decorators. `hr_service/routers/hr.py` (113 lines) and `it_service/routers/it.py` (121 lines) contain no `/demo/*`. The endpoints exist only in `seed/seed.py` (CLI: `seed.py --reset`) and `seed/README.md:70`.
- Consequence: every mutating judge action (`hr_create_employee`, `it_assign_laptop`, `it_reroute_ticket`) permanently dirties the single shared file both services write to (`hr_service/db.py:29`, `it_service/db.py:21` → both default to `seed/demo.db`). `RECONCILE.md:36` admits "Writes land in `seed/demo.db` — restore via `python seed/seed.py --reset`" — a local shell command, not a judge-accessible API, and it nukes concurrent state. Second judge run starts from polluted data; counts gate G3 (`seed/validate.py`) fails after one convert (20→21 employees).
- `.env.example:8-9` documents `DATABASE_URL=sqlite:///./hr.db` / per-service files; code ignores it and shares `seed/demo.db`. Two uvicorns + SQLite file writes with no WAL/mutex visible (`db.py` uses plain `aiosqlite.connect` + `commit`, no `PRAGMA journal_mode=WAL`, no busy-timeout). Concurrent approve + reroute during the live demo risks `database is locked` on stage.
- `seed/seed.py` vs CSVs vs `demo.db` triple-source: `seed.data.ts` ("single source" per plan.md:95) has no corresponding file in repo listing; `seed/` contains `schema.sql, seed.py, validate.py, *.csv, demo.db`. Which is canonical is unclear to anyone rerunning.

**What the judge asks:** "Reset the demo for the next team without touching my terminal." You can't.
**Fix:** implement the three `/demo/*` routes (guarded, rate-limited) or ship `run.bat`/Makefile `reset` the judge actually runs; set WAL + busy timeout; reconcile `.env.example` with `db.py`. Cost: **2-3h**.

## KILL 4 — The live `--discover` moment is staged to 404

**Claim:** plan.md §2/§6: uncomment H5 → `synapse build --discover` → `hr_get_oncall` appears → Q3 reroute chain, "no client re-config".

**Evidence:**

- `hr_service/routers/hr.py:92-113` — H5 is a comment block with a **lazy import inside the handler** (`from hr_service.models import OnCall`) and defaults `team="support-night"`. `hr_service/db.py:177-210:get_oncall` falls back to first roster row or returns `None` → router raises 404 "no on-call roster for team/date". Whether `support-night` (or any team the agent asks for) resolves against seeded `shifts`/`shift_members` is unvalidated on stage — one wrong team string and the "miracle moment" is a 404 in front of judges.
- `docs/CLIENTS.md:23-27` (and plan.md:89,132) asserts Cursor `MCP_REV` bump + Inspector Reconnect picks up the new tool "in 3s, no restart" — but `.cursor/mcp.json` doesn't even list `it-api`, and Cursor is documented in plan.md:132 as "backup proof, never live (restarts)". The runbook contradicts itself on which client is live.
- `guide.txt:161-164,201-202` — rebuilds keep the same server ID *for hosted builds*; `--local` writes a *file* the client must re-point at. The plan mixes both ("hosted P0/P1 → qwen local-8k P2 → cached-JSON P3", plan.md:133) without stating which path the live moment uses. If quota dies and you fall to `--local`, "same server ID, no re-config" is false by the guide's own page 6.
- No rehearsal evidence: `demo/golden.mp4` (plan.md §1 tree) does not exist (`glob demo/**` → nothing); `scripts/prewarm.sh:26` expects "10 pre-discover, 11 post" but the current code yields 12 with health checks (Kill 2). The 60s choreography (`plan.md:130`) has never been timed — `BENCHMARKS.md:11,15,18` all `TODO_s`.

**What the judge asks:** "Do it again, but for team X / at midnight / after I break a ticket." The chain has exactly one rehearsed path.
**Fix:** uncomment H5 now, seed a deterministic on-call row per team, add `GET /hr/oncall` to `validate.py` + prewarm assertions, film the fallback video before D8. Cost: **2h + 1h video**.

## KILL 5 — Two write paths, one audit: the safety story is theater on stage

**Claim:** plan.md §5: "CITE preview+hash → CHECK → ACT → RECORD audit row"; "unknown = deny-closed"; ledger + hash chain.

**Evidence:**

- The enforced path (`safety_check_server.py:onboard`, `confirm=True` + `preview_hash` + `idempotency_key`) **writes nothing to HR/IT**. `_activate` (`:372-395`) inserts into a sidecar `safety_ledger.db` and mints `EMP-<hash[:6]>` (`:561`) — a fake ID outside the `EMP-NNN` sequence that `hr_service/db.py:93-136` owns. Meanwhile the real mutation path (`POST /hr/employees`, `POST /it/equipment/assign`, `POST /it/tickets/{id}/reroute`) has **no preview, no hash, no ledger, no audit** — plain inserts/updates. An agent doing the demo the easy way bypasses every guard, and the "receipt" (`ACTIVE EMP-a1b2c3`) will not resolve in `GET /hr/candidates` or breach triage. Judge cross-check ("now show me that employee in HR") fails.
- `_stage` (`:315-331`) never records `hold`/BG state into the ledger — only the redacted plan into `staged_previews` with no FK to the idempotency row. `_hold` (`:334-341`) hardcodes `HELD/RETIRED_LAPTOPS` sets instead of reading `equipment.status`/`equipment_holds`, so safety and IT disagree the moment seed data changes.
- Audit is append-only theater under concurrency: `_audit_append` (`:205-223`) reads the whole `audit.jsonl` to find head, computes, appends — no file lock. Two concurrent activates fork the chain; `verify_audit_chain` (`:247-273`) will then report `firstBadSeq` on your own writes. Ledger PK `(actor,operation,key)` (`:109-122`) is correct but `_ledger_insert_in_progress` uses `INSERT OR IGNORE` + `rowcount` — under `aiosqlite`/threads this is fine single-process, untested multi-worker (`uvicorn --workers >1`, gunicorn) where two `IN_PROGRESS` winners are possible.
- UX contract mismatch: plan.md:120 promises `APPROVE <id>`, `DENIED`, double-approval for Class C; server emits `APPROVE {preview_id}` vs `preview_hash` confusion (`:363-369` says "Reply APPROVE {pid}" but activate requires the *hash*, `:487-492`), and there is no Class C double-approval path at all — one `confirm=True` flips everything.
- Secrets: `redact()` (`:81-85`) covers `${ENV:VAR}` + 4 token shapes; `SECRET_VALUE_RE` misses `sk-ant-`, `gsk_`, `xoxp-`, private keys, Aadhaar/SSN digit strings the eval claims to block. Eval's PII regexes (`run.py:13-14`) are broader than the server's — another proof they test different code.

**What the judge asks:** "I approved LT-1005 in your safety tool — now assign it in IT. What stops me?" Nothing: the paths are disconnected.
**Fix (minimal credible):** make `onboard(confirm=True)` call the real `hr_service.db`/`it_service.db` writers (or their HTTP routes) inside the ledger transaction boundary, or scope the demo narrative to "safety gate before manual API call" and say so in ARCHITECTURE. Plus file lock for audit, unify APPROVE token = preview_id. Cost: **4-8h** for real wiring; **30min** to de-scope honestly (but weakens the story).

---

## Also burning (quick hits with addresses)

- **Seed triad confusion:** plan.md:94-95 says "seed.data.ts in-code JSON mirror (single source)"; repo has `seed/seed.py + *.csv + demo.db`, no `seed.data.ts`. `seed/validate.py:208-236` accepts *either* a `CAND-002;CAND-005` CSV hack *or* two `equipment_holds` rows as "double-hold present" — the trap's definition is disjunctive, so a judge asking "which is it?" gets a shrug. Fix: pick one canonical holder representation. 30min.
- **`scripts/up.sh:12`** installs from `requirements.txt`, which does not exist (only `requirements-hr/it.txt`). Golden-path boot script fails on a fresh clone. `run.bat` untested here. Fix: 10min.
- **Compose drift:** `plan.md:18-20` says Docker opt-in only, golden = single process; `49-master-plan.md D3` still mandates `docker-compose.yml` healthchecks as G-gate. `compose.opt.yml` is backup-only but `BENCHMARKS.md:12` still measures it. Pick one; judges notice when the diagram and the Makefile disagree. 20min.
- **Model claims unmeasured:** `Modelfile.local-8k` pins qwen3:4b/qwen2.5-coder:7b with "tools 97.7 / emit_tool_plan 80-90%" (plan.md:143,149) and `49-master-plan.md T5` gates on it — no `ollama ps`, no trial log, `P2` fallback `synapse_auto_server.py` missing (Kill 2). "Cached-JSON P3" has no JSON files. Fix: run 20 `emit_tool_plan` trials or delete the percentages. 1-2h.
- **Track-3 question coverage:** guide needs *two* cross-system questions + live update. The repo's Q1/Q2/Q3 (breach→oncall→reroute, headcount-vs-breach, CAND-002→EMP-021) all hinge on H5 live. If discover fails, you have one cross-system question (Q1 without oncall is single-system breach list). The T2-hedge pivot (49-master-plan D8) is the right call but unacknowledged in `plan.md`'s 23/25 FUND header — overconfidence on the cover page. Fix: script and rehearse Q1-without-H5 + Q2 so T2 still passes Track 3's "two questions" bar. 1h.
- **Small correctness nits judges love:** `it_service/db.py:176-178` derives `ticket_id` from `MAX(SUBSTR)` — concurrent creates collide; `reroute_ticket (:248-272)` never validates the *new* assignee is on-shift/oncall; `create_employee (:93-136)` doesn't check candidate exists/signed/BG — the traps (fail-1 BG, EMP-007 rehire, LT-1012) live only in CSVs + safety-server constants, not in the API the agent actually calls. An agent converting a `fail` candidate via `POST /hr/employees` succeeds. That is a 10-second judge kill: "convert the BG-fail candidate live." Fix: add BG/offer/rehire guards to `hr_create_employee` or admit the API is intentionally dumb and the safety tool is the gate — but then wire them (Kill 5). 2-3h.

---

## Top-5 risks, ranked (probability × stage-impact)

| # | Risk | Why it kills | Fix cost |
|---|---|---|---|
| 1 | **Eval number collapses under one `grep`** — label-reading guard + fake latency + wrong-code-tested + strawman baseline (`eval/run.py:12-81`) | Safety is a judged criterion (guide p.2: "confirmation step", "safety"); 96.8% is the headline metric and it is indefensible as presented | **3-5h** (live eval rewire + rerun) |
| 2 | **No Synapse servers exist; client config points at a missing file** (quota-log all TODO; `synapse_auto_server.py` absent; `.cursor/mcp.json:5`) | Track 1-3 all require Synapse at core; "both MCP servers + live update" is the submission, and it is currently zero artifacts | **2-4h** + key wait |
| 3 | **No `/demo/seed\|reset` + shared `seed/demo.db` + `.env` lie** (routers have no demo routes; `db.py:29`/`db.py:21` share one file; `.env.example:9` disagrees) | Destroys "60s judge rerun" + repeat-demo; second run starts dirty, G3 fails, concurrent writes risk `database is locked` live | **2-3h** |
| 4 | **Live discover 404 / client mismatch** (H5 commented `hr.py:92-113`; `support-night` unseeded; Cursor-vs-Inspector contradiction plan.md:132 vs CLIENTS.md:27; no `golden.mp4`) | The single highest-weighted demo moment has no rehearsal artifact and a plausible 404 path | **2-3h** incl. video |
| 5 | **Safety tool ≠ API: approvals don't mutate, mutations don't approve** (`safety_check_server.py:561-581` mints fake EMP IDs; routers bypass all guards) | Judge cross-checks receipt against HR/IT and it isn't there; "CIT→CHECK→ACT→RECORD" is false for the acted path | **4-8h** real wiring, or 30min honest de-scope |

**Cheapest path to survival (~1 working day):** fix #3 (demo reset + WAL, 2h) → run Synapse builds + correct counts to 12/13 (#2, 2h) → uncomment H5 + seed on-call + film P0 (#4, 2h) → de-scope safety narrative to what the code does + relabel eval as "policy-regex smoke, mock latency" (#1+#5 honesty patch, 1h). Real fixes for #1/#5 are the remaining 8-12h and should precede any "23/25 FUND" claim.
