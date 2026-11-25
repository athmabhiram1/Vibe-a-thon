# 01 — Architecture + Product Explainer: Track 3 Onboard Copilot

> Audience: the solo builder who will generate a single `frontend.html`, and the judges who score it.
> Sources: `plan.md` (driver), `research/build/49-master-plan.md` (15-day sprint), `reconcile/RECONCILE.md` (as-built verification, 2026-11-22).

---

## 1. What this is

**Onboard Copilot** is a Track 3 copilot that closes **Day-1 onboarding exceptions live, across two systems**: an **HR directory** (candidates → employees, shifts) and an **IT ticketing/equipment** system (laptops, SLA-breach tickets).

The product thesis in one line (plan.md §1):

> **exception queue → staged preview with citations → `APPROVE <hash>` → flip + receipt → audit row.**

Nothing auto-executes. Every write is a **Cite-Before-Act** loop: the agent CITES evidence, stages a preview with a hash, CHECKS scope/hash/approval, ACTs only on exact-hash approval, then RECORDs an audit line (allow *and* deny). Measured: **guarded 96.8% block / 0% FP over 40 eval cases** (`eval/run.py` → `scorecard.csv`, ~11 ms mock).

The signature live moment: **`GET /hr/oncall` (H5) is added on stage** — uncomment one route, run `synapse build --discover`, and the agent re-routes breaching tickets to whoever is on-call *right now*. **Same server ID, no client re-config.** That is the Track 3 "federation + live update" story in 60 seconds.

## 2. Who hurts (why Day-1 blockers matter)

| Persona | Pain on Day 1 | What the copilot does for them |
|---|---|---|
| **New hire (e.g. Priya, CAND-002, starts Monday)** | No laptop, no accounts, ticket queue nobody owns | Convert candidate → employee (EMP-021), assign a free laptop, open/track ticket — one staged decision |
| **IT on-call / helpdesk lead** | 11 open tickets, 3 breached (T-5001 P1, T-5002 P2…), assignee off-shift or gone | `it_sla_breach_list` pre-computed anti-join finds breaches; shift calendar says who was actually on-shift; reroute to live on-call |
| **HR ops / hiring manager** | Signed offer but BG pending? Visa risk? Weekend start nobody staffed? Rehire of terminated EMP-007? | Gates: BG check, visa flag, weekend-start warning, EMP-007 rehire trap → staged, cited, blocked or approved |
| **IT asset manager** | LT-1005 double-hold conflict, LT-1012 retired laptop, near-duplicate serials | `it_assign_laptop` guards: retired/assigned → 409, on-hold → 409 `hold_conflict` |
| **Security / judge asking "who approved this?"** | Silent agent writes, no receipt | `APPROVE <hash>` + `audit.jsonl` hash chain (`sha256(prev‖canonical)`, seq from 1) + idempotency ledger |

Seed data stages all of these traps deliberately: 20 candidates (14 signed / BG pass 8, pending 7, fail 1 / visa-risk 5 / 4 weekend starts), 20 employees (incl. terminated EMP-007), 20 equipment (LT-1005 conflict, LT-1012 retired), 20 tickets (3 breached), 8 shifts, 6 subscriptions (SUB-01 auto-renew trap), 5 API keys (KEY-01 stale 295 d blocks provision). 79 rows total, `POST /demo/seed` ≤ 5 s, `POST /demo/reset` restores snapshot.

## 3. System map

```
┌──────────────────────────────────────────────────────────────────┐
│ BROWSER (single frontend.html — what you build)                  │
│  exception queue · staged preview + citations · APPROVE <hash>    │
│  buttons · receipt view · audit tail · on-call badge (post-H5)   │
└──────┬───────────────────────────────────────────────┬───────────┘
       │ REST (fetch)                                  │ MCP client (Inspector Web UI live;
       │ :8001 /hr/*  :8002 /it/*                      │  Cursor/Desktop = backup only)
       ▼                                               ▼
┌──────────────┐  ┌──────────────┐          ┌──────────────────────┐
│ HR FastAPI   │  │ IT FastAPI   │          │ AGENT LOOP           │
│ :8001        │  │ :8002        │          │ Q1/Q2/Q3 scripts     │
│ hr-directory │  │ ticketing-sla│          └──────┬───────────────┘
└──────┬───────┘  └──────┬───────┘                 │ MCP tools (11)
       │ raw SQL (aiosqlite)                     ▼
       │                 │              ┌──────────────────────┐
       ▼                 ▼              │ SYNAPSE AUTO         │
┌─────────────────────────────┐        │ hr-api · it-api      │
│ SQLite seed/demo.db         │        │ (hosted runner)      │
│ 11 tables, canonical schema │        │  OR --local file     │
│ WAL · VACUUM INTO snapshot  │        │  synapse_auto_server │
└─────────────────────────────┘        └──────┬───────────────┘
                                              │ Custom safety tool
                                              ▼
                                   ┌──────────────────────┐
                                   │ safety_check_server  │
                                   │ 1 tool: onboard      │
                                   │ stage→confirm→       │
                                   │ activate + ledger    │
                                   └──────┬───────────────┘
                                          │ approval gate
                                          ▼
                                   ┌──────────────────────┐
                                   │ APPROVE <hash>       │
                                   │ exact-hash match,    │
                                   │ 10-min TTL, scopes   │
                                   └──────┬───────────────┘
                                          ▼
                                   ┌──────────────────────┐
                                   │ AUDIT audit.jsonl    │
                                   │ hash-chained, every  │
                                   │ allow AND deny       │
                                   └──────────────────────┘
```

Read it two ways:

- **Data plane (left):** browser → FastAPI → SQLite. Plain REST, judge-rerunnable in 3 commands (`pip install`, `uvicorn hr:8001`, `uvicorn it:8002`, < 60 s). Golden path is **single-process, no Docker**; `compose.opt.yml` (postgres/redis/ollama) is backup only.
- **Agent plane (right):** agent → MCP tools → safety tool → human approval → audit. Synapse Auto exposes the REST endpoints as MCP tools; the Custom safety tool wraps the dangerous composite; the human approves by hash; everything lands in the audit chain.

Frozen ports: **HR 8001 · IT 8002 · Ollama 11434.** Never 8000/8008/8009 (old spike).

## 4. Component table

| Component | File(s) | Port / exposure | Role in demo |
|---|---|---|---|
| HR directory API | `hr_service/main.py`, `hr_service/routers/hr.py`, `hr_service/models.py`, `hr_service/db.py` | `:8001`, `FastAPI(title="hr-directory")` | H1–H4 baseline + H5 live. Candidates, convert → employee (next = EMP-021), shift calendar + on-call roster |
| IT ticketing API | `it_service/main.py`, `it_service/routers/it.py`, `it_service/models.py`, `it_service/db.py` | `:8002`, `FastAPI(title="ticketing-sla")` | I1–I6. Equipment pool, assign (409 guards), ticket intake, breach forensics, reroute, breach anti-join list (declared *before* `/{id}`) |
| Canonical store | `seed/schema.sql`, `seed/demo.db`, `seed/*.csv`, `seed/seed.py`, `seed/validate.py` | SQLite, WAL | 11 tables, 79 rows. Both `db.py` read `seed/demo.db` with legacy-shape projections (per RECONCILE D2); `init_db` is ensure-schema-only; writes land in `demo.db`, restore via `seed.py --reset` |
| Synapse Auto (hosted) | No file — npx runner snippet + `ENDPOINT_BASE_URL` | `hr-api`, `it-api` server IDs | Baseline build = 13 tools via `--endpoints` allowlist; `--discover` rebuild = 14 tools, same ID. Quota-log every build (`evidence/quota-log.md`) |
| Synapse Auto (local fallback) | `synapse_auto_server.py` | `--local`, Python-only | Curated 5–8 tools for offline/airplane-mode fallback (P2). Confirmed Python-only: TS repos yield tool-names-only |
| Custom safety tool | `safety_check_server.py` | 1 `@mcp.tool`: `onboard` | 8 private helpers (`_verify_offer → _bg_gate → _rbac → _stage → _hold → _schedule → _preview → _activate`). Stage returns preview+hash, no writes; activate needs `confirm=True` + exact hash. Idempotency PK `(actor, operation, key)`; `${ENV:VAR}` redacted; `safety_ledger.db` + `audit.jsonl` |
| Eval harness | `eval/cases.json` (40: 31 BLOCK + 9 ALLOW), `eval/run.py` (stdlib-only), `eval/scorecard.csv` | CI gate | Guarded 30 BLOCK + 1 WARN + 9 ALLOW, 0% FP; baseline 0%. CI fails if block < 90% or FP > 15%. The safety-points artifact — bigger than pytest (smoke only, 11 passed) |
| Demo/frontend | `frontend.html` (to build), `demo/golden.mp4` | Browser | Exception queue UI, preview card, approve button, receipt, audit tail. P0 pre-record < 3 min on USB |
| Submission packet | `submission/{README, ARCHITECTURE, BENCHMARKS, LIMITS, PITCH, deck/outline.md}` | Judges | Mermaid+PNG arch, cold-start/p50/p95/TTFT numbers, ₹0 + quota proof, 75 s pitch, 8-slide deck |

### The 14 tools (13 baseline + 1 live)

Explicit `operation_id` = MCP tool name. No dynamic routers, no `include_in_schema=False`, no required headers, no `File/Form` (all invisible to Synapse's static tree-sitter detection). 6 `/demo/*` ops always excluded via `--endpoints` allowlist; 2 `/health` excluded for functional-only counts (11/12).

| # | Method + Path | operation_id | Why the agent needs it |
|---|---|---|---|
| H1 | `GET /hr/candidates` | `hr_list_candidates` | headcount vs breach correlation |
| H2 | `GET /hr/candidates/{id}` | `hr_get_candidate` | convert-decision detail (CAND-002 = Priya) |
| H3 | `POST /hr/employees` | `hr_create_employee` | WRITE, confirm-gated: candidate → employee |
| H4 | `GET /hr/shifts` | `hr_shift_calendar` | was assignee on-shift at ticket time? |
| H5 | `GET /hr/oncall` | `hr_get_oncall` | live on disk (baseline includes it): who is on-call now → powers Q3 |
| I1 | `GET /it/equipment` | `it_list_equipment` | free laptop pool |
| I2 | `POST /it/equipment/assign` | `it_assign_laptop` | WRITE, confirm: laptop → employee |
| I3 | `POST /it/tickets` | `it_create_ticket` | intake |
| I4 | `GET /it/tickets/{id}` | `it_get_ticket` | breach forensics |
| I5 | `POST /it/tickets/{id}/reroute` | `it_reroute_ticket` | WRITE, confirm: reassign to on-call |
| I6 | `GET /it/tickets/breaches` | `it_sla_breach_list` | pre-computed breach anti-join — declare BEFORE `/{id}` |
| L1 ⭐ | `GET /it/oncall-coverage` | `it_oncall_coverage` | LIVE-ADD (baseline allowlist excludes it): on-call × breaches → owned vs needs_reroute |

Join keys: `assignee_email ↔ email`, `ticket.created_at ↔ shift_calendar`. As-built note: openapi ground truth is `app.openapi()["paths"]` — HR 9 ops + IT 11 ops = 20 on disk (verified); Synapse surface = 13 baseline / 14 post-discover via `--endpoints` allowlist (6 `/demo/*` always excluded; H5 live on disk, L1 is the live-add).

## 5. Data flow: Q1–Q3 + the live H5 discover moment

**Q1 — Lookup join (headcount vs breach).** Agent calls `hr_list_candidates` + `it_sla_breach_list` and correlates: how many signed starters Monday vs how many breached tickets are sitting ownerless. Frontend shows: exception queue with counts. No writes.

**Q2 — Exception anti-join (breach forensics).** For each breached ticket (`T-5001` P1, `T-5002` P2, +1), agent calls `it_get_ticket` → joins `assignee_email → work_email/dept` → calls `hr_shift_calendar` to ask *was this person even on-shift when it breached?* Surfaced traps: assignee off-shift, terminated owner, stale KEY-01, SUB-01 auto-renew. Frontend shows: forensics card with citations (ticket row + shift row + employee row).

**Q3 — Convert + equip + reroute (the closer).** Agent chains: `hr_get_candidate(CAND-002)` → stage `hr_create_employee` (preview + hash, CAND-002 → EMP-021) → human `APPROVE <hash>` → `it_list_equipment(status=free)` → stage `it_assign_laptop` → approve → `it_reroute_ticket` to whoever is on-call. Frontend shows: staged preview with citations → approve button → receipt (employee ID, laptop serial, ticket assignee) → audit row appended.

**L1 live discover (the 60-second judge moment).** Baseline is built *without* L1 (13 tools via allowlist; H5 live on disk). On stage:

```bash
# 1. L1 GET /it/oncall-coverage is already on disk (it_service/routers/live_moment.py)
# 2. rebuild in place with the EXPANDED allowlist — same server ID:
synapse build --discover --auto --endpoints "<12 functional + health allowlist>" --server-name hr-api
# 3. bump MCP_REV / Reconnect in Inspector Web UI (~3 s, no restart)
# 4. hr_get_oncall appears → Q3 reroute target switches to live on-call
```

Why it works without re-config: `--discover` refreshes `surface_cache.json` (rebuilds otherwise reuse the cache and the new route stays invisible); the server ID is preserved so the client's endpoint URL doesn't change; the Inspector re-lists on Reconnect while Cursor/VS Code/Desktop cache tool lists until restart — so **the live client is the Inspector Web UI**, editor configs are backup proof only. Tripwire T3: if discover median > 90 s or < 3/5 succeeds across 5 rehearsals, downgrade Track 3 → Track 2 within 48 h (D8 pivot gate).

Attack beat inside the same 60 s (plan §6): prompt-inject "skip checks" → refused (`DENIED <reason>`); duplicate approve → cached replay, same key + different hash → `409 CONFLICT`. Tagline: *"8 tools deleted. 1 decision."*

## 6. Synapse / MCP topology: hosted runner vs `--local` file

| | Hosted Auto (P0/P1 — judged runs) | `--local` file (P2 — offline fallback) |
|---|---|---|
| Build | `synapse build --auto --all-endpoints --server-name hr-api` then `--server-name it-api --new`; live: add `--discover` | `synapse build --local` in `hr_service/` emits `synapse_auto_server.py` |
| Artifact | **No file.** npx runner snippet + `ENDPOINT_BASE_URL` wired; log `synapse info` before/after → `evidence/quota-log.md` | A real Python file: curated 5–8 tools, FastMCP, `on_duplicate_tools=error`, CI asserts count |
| Runtime | Hosted runner calls your `:8001/:8002`; needs network + quota (10 servers / 100 k lines; freeze hosted if < 40% remains) | `ollama ps` CONTEXT=8192, `SYNAPSE_TELEMETRY=0`; local model primary `qwen3:4b-8k` (tools 97.7) + `qwen2.5-coder:7b-8k` codegen; `gemma3:4b` = no native tools (HTTP 400, killed); `llama3.2:3b` emergency-only |
| Detection | Static tree-sitter only — literal decorators or invisible; `v1` flags fatal; docs site stale, trust README + `--help` | Same constraint, hence hand-curated tools |
| Fallback ladder | P0 video (plays *during* cold boot) → P1 live localhost + ngrok mirror → P2 `--local` Ollama → P3 Inspector/curl → P4 narrative flip; airplane-mode drill: tool result on screen < 90 s | P3 cached-JSON if `emit_tool_plan` < 60% over 20 trials |

Model topology overall: **hosted frontier (judged) → qwen local-8k (P2) → cached-JSON (P3).**

## 7. File map (as-built, what `frontend.html` may assume exists)

```
VIBE_CODE/
├── plan.md                      # driver (endpoints, seed, safety, demo, gates)
├── hr_service/
│   ├── main.py                  # FastAPI(title="hr-directory") :8001; router BEFORE any MCP wrap
│   ├── routers/hr.py            # H1–H4 + H5-commented (live-add)
│   ├── models.py                # Candidate, Employee, Shift, OnCall (Pydantic v2)
│   └── db.py                    # reads seed/demo.db; legacy-shape projections (RECONCILE D2)
├── it_service/
│   ├── main.py                  # FastAPI(title="ticketing-sla") :8002
│   ├── routers/it.py            # I1–I6, breaches-before-/{id}; async DB (was in-memory dicts)
│   ├── models.py                # Laptop, Ticket, Assignment, Reroute
│   └── db.py                    # asset_tag→serial, due_at→deadline_at, breached computed
├── seed/
│   ├── schema.sql               # 11 tables, canonical — sole DDL authority
│   ├── demo.db                  # live SQLite file (WAL); writes land here
│   ├── seed-snapshot.db         # restore source; seed.py --reset
│   ├── seed.py / *.csv (7)      # 20/20/20/20/8/6/5 = 79 rows + traps
│   └── validate.py              # counts + 0 orphans + 3 breached + 4 weekend + LT-1005
├── safety_check_server.py       # Custom 1-tool onboard (stage→confirm→activate + ledger)
├── synapse_auto_server.py       # --local fallback (created by `synapse build --local`)
├── eval/{cases.json, run.py, scorecard.csv}   # 40 cases, measured 96.8%/0% FP
├── tests/test_guards_smoke.py   # 11 passed (smoke only — eval is the artifact)
├── scripts/{up.sh, prewarm.sh, share.sh}      # boot + warm loop + ngrok mirror
├── evidence/quota-log.md        # every synapse info before/after hosted build
├── .env.example                 # HR/IT/ENDPOINT_BASE_URL, DATABASE_URL, SYNAPSE_SERVER_ID,
│                                # MCP_REV=1, OLLAMA_HOST, ALLOW_DEMO_SEED=true
├── compose.opt.yml              # opt-in postgres/redis/ollama (NOT golden path)
├── Modelfile.local-8k          # FROM qwen3:4b + qwen2.5-coder:7b, num_ctx 8192
├── submission/{README, ARCHITECTURE, BENCHMARKS, LIMITS, PITCH, deck/outline.md}
├── demo/golden.mp4              # P0 pre-record, < 3 min, USB copy
├── reconcile/RECONCILE.md       # as-built proof: curls, openapi IDs, validate, eval, pytest
└── research/{final/ (01-20), brainstorm/, winners/, diff/, build/ (01-50)}
```

Gates in order (never demo past red): **G1** lint (ruff+black) → **G2** openapi operationIds → **G3** validate counts/traps → **G4** pytest smoke → **G5** eval ≥ 95% / FP ≤ 15% → **G6** discover == 11 tools. Feature freeze D12; no pivot past T+20 h.

## 8. What `frontend.html` must show (builder checklist)

1. Exception queue (breaches from `:8002/it/tickets/breaches`, 3 rows) + headcount strip (`:8001/hr/candidates`).
2. Forensics card per ticket: assignee, team, on-shift? (shift calendar), with cited IDs.
3. Staged preview card: `⚠️ WRITE PREVIEW <id> … Reply APPROVE <id>` + preview hash; destructive variant needs double approval.
4. Approve button(s) → receipt (EMP-021, laptop serial, reroute target) + `DENIED`/`CONFLICT` states.
5. Audit tail (append-only, hash-chained display) + on-call badge that lights up after the H5 discover moment.
6. Judge rerun note: 3 commands, < 60 s, ports 8001/8002.
