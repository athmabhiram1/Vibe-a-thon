# Vibe-a-thon — Track 3 Onboard Copilot: Master Plan

**Goal:** WIN Track 3 (copilot across two systems). Solo builder, lots of time (~90h / 15 days).
**Idea:** HR directory + IT ticketing copilot that closes onboarding exceptions live.
**Core loop:** exception queue → staged preview with citations → `APPROVE <hash>` → flip + receipt → audit row.
**Live moment:** add `GET /it/oncall-coverage` (L1) on stage → `synapse build --discover` (expanded `--endpoints` allowlist) → agent re-routes breaching tickets. Same server ID, no client re-config. (H5 `GET /hr/oncall` is live on disk since the seed-lane fix — the old uncomment-H5 choreography is dead.)

Judge score 23/25 FUND. Devil's advocate: 4 kill attempts survived. Evals measured: guarded 97.5% acc (39/40) / 96.8% block (30/31) / 0% FP MOCK + 5 LIVE.

---

## 1. Repo structure (how the repo looks)

```
VIBE_CODE/
├── plan.md                      # THIS FILE — driver
├── guide.txt                    # participant guide extract
├── docker-compose.yml           # OPT-IN only (postgres+redis+ollama). Golden path = single-process, no Docker
│                                # judge rerun: pip install → uvicorn hr:8001 + it:8002 (3 cmds, <60s)
├── compose.opt.yml              # production-like profile (postgres, redis, ollama) — backup only
├── .env.example                 # HR_BASE_URL, IT_BASE_URL, ENDPOINT_BASE_URL, DATABASE_URL,
│                                # SYNAPSE_SERVER_ID, MCP_REV=1, OLLAMA_HOST, ALLOW_DEMO_SEED=true
├── hr_service/
│   ├── main.py                  # FastAPI(title="hr-directory"), include_router BEFORE any MCP wrap
│   ├── routers/hr.py            # 4 stable + 1 live-commented (see §2)
│   ├── models.py                # Candidate, Employee, Shift, OnCall (Pydantic v2)
│   └── db.py                    # SQLAlchemy 2.0 engine/session (asyncpg | aiosqlite)
├── it_service/
│   ├── main.py                  # FastAPI(title="ticketing-sla"), :8002
│   ├── routers/it.py            # 6 endpoints (see §2)
│   ├── models.py                # Laptop, Ticket, Assignment, Reroute
│   └── db.py
├── seed/
│   ├── schema.sql               # 11 tables, partial uniques, FK order
│   ├── seed.data.ts             # in-code JSON mirror (single source for <5s path)
│   ├── candidates.csv (20) · employees.csv (20) · equipment.csv (20) · tickets.csv (20)
│   ├── shifts.csv (8) · subscriptions.csv (6) · api_keys.csv (5)
│   ├── reset.sql                # TRUNCATE … CASCADE one statement
│   └── validate.py              # counts 20/20/20/20/8/6/5 + 0 orphans + 3 breached + 4 weekend + LT-1005 canonical hold/ledger pair + support-night oncall
├── safety_check_server.py       # Synapse Custom 1-tool (stage→confirm→activate + ledger)
├── synapse_auto_server.py       # --local fallback (curated 5-8 tools)
├── .cursor/mcp.json             # backup configs only — LIVE demo = MCP Inspector Web UI (Reconnect re-lists, no restart)
├── Modelfile.local-8k           # FROM qwen3:4b (agent tools 97.7) + qwen2.5-coder:7b codegen; num_ctx 8192
│                                # gemma3:4b = NO native tools (HTTP 400). llama3.2:3b = emergency only.
│                                # Topology: hosted (P0/P1) → qwen local-8k (P2) → cached-JSON (P3)
├── eval/
│   ├── cases.json               # 40 cases (31 BLOCK + 9 ALLOW) ✅ MEASURED
│   ├── run.py                   # guarded vs baseline, stdlib-only ✅
│   └── scorecard.csv            # 30 BLOCK + 1 WARN + 9 ALLOW, 0% FP, ~11ms ✅
├── scripts/up.sh · prewarm.sh   # cloud/local boot + warm loop
├── evidence/quota-log.md        # every `synapse info` before/after hosted build
├── submission/
│   ├── README.md · ARCHITECTURE.md (mermaid+PNG) · BENCHMARKS.md · LIMITS.md
│   ├── PITCH.md (75s) · captions/demo.srt · deck/outline.md (8 slides)
│   └── assets/quota-proof/ · benchmark/run.js
├── demo/golden.mp4              # P0 pre-record, <3min, USB copy
└── research/
    ├── final/ (01-20)           # all verified findings
    ├── brainstorm/ (01-10)      # ideas + judge-fit + track choice
    ├── winners/ (01-10)         # Geek Room winner patterns + LinkedIn URLs
    ├── diff/ (01-10)            # Paperclip/harness/skills differentiation
    └── build/ (01-50)           # arch, api, db, auth, deploy, libs, steps, 49-master, 50-index
```

Frozen ports: **hr 8001, it 8002, ollama 11434.** Never 8008/8009/8000 (old spike superseded).

---

## 2. Endpoints — 13 baseline / 14 post-discover (11/12 functional-only; + L1 live)

Explicit `operation_id` = MCP tool name. No dynamic routers, no `include_in_schema=False`, no required `Header`, no `File/Form`.

| # | Method + Path | operation_id | Why agent-needed |
|---|---|---|---|
| H0 | GET /hr/health | hr_health_check | liveness probe (ingested by `--all-endpoints`; exclude via `--endpoints` allowlist for an 11-functional (13-total) baseline surface) |
| I0 | GET /it/health | it_health_check | liveness probe (same exclusion note) |
| H1 | GET /hr/candidates | hr_list_candidates | headcount vs breach correlation |
| H2 | GET /hr/candidates/{id} | hr_get_candidate | convert decision detail |
| H3 | POST /hr/employees | hr_create_employee | WRITE: candidate→employee, confirm-gated |
| H4 | GET /hr/shifts | hr_shift_calendar | was assignee on-shift at ticket time? |
| H5 | GET /hr/oncall | hr_get_oncall | baseline (live on disk): who is on-call right now → powers Q3 |
| I1 | GET /it/equipment | it_list_equipment | free laptop pool |
| I2 | POST /it/equipment/assign | it_assign_laptop | WRITE: laptop→employee, confirm |
| I3 | POST /it/tickets | it_create_ticket | intake |
| I4 | GET /it/tickets/{id} | it_get_ticket | breach forensics |
| I5 | POST /it/tickets/{id}/reroute | it_reroute_ticket | WRITE: reassign to on-call, confirm |
| I6 | GET /it/tickets/breaches | it_sla_breach_list | pre-computed breach anti-join — declare BEFORE /{id} |
| L1 ⭐ | GET /it/oncall-coverage | it_oncall_coverage | LIVE-ADD (only live-add): H5 on-call × breaching tickets → owned vs needs_reroute |

OpenAPI on disk (verified): HR 9 ops + IT 11 ops = 20. Synapse surface via `--endpoints` allowlist (`docs/CLIENTS.md` §7): 6 `/demo/*` ops always excluded, 2 `/health` excluded for functional-only counts.

Join keys: `assignee_email ↔ email`, `ticket.created_at ↔ shift_calendar`. Q1 lookup join → Q2 exception anti-join → Q3 only-answerable-after-discover.

Live runbook: baseline build (H1-H5 + I1-I6 + 2×/health = 13 tools; 11 functional if health excluded via `--endpoints` allowlist) → add L1 → `synapse build --discover --auto --endpoints "<expanded allowlist>" --server-name hr-api` → same ID → Inspector Disconnect→Reconnect re-lists → `it_oncall_coverage` appears → Q3 chain. Post-discover total = 14 (12 functional + 2 health).

---

## 3. Seed — 79 rows, <5s, traps staged

20 cands (14 signed / BG pass 8, pending 7, fail 1 / visa-risk 5 / 4 weekend starts) · 20 emps (CEO stub + HR/IT leads + terminated EMP-007 rehire trap) · 20 equip (LT-1005 **double-hold: canonical hold CAND-002 + equipment_holds pair CAND-002/CAND-005**, LT-1012 retired trap, SN near-dup pair) · 20 tickets (3 breached: T-5001 P1, T-5002 P2 + 1) · 8 shifts (SH-08 support-night → EMP-014, on-call never 404s) · 6 subs (SUB-01 auto-renew trap) · 5 keys (KEY-01 stale 295d blocks provision).

`POST /demo/seed` (single txn, multi-row INSERT ×7, `seeded_at` fixed) + `POST /demo/reset` (snapshot restore) + `GET /demo/status`. Guards: `ALLOW_DEMO_SEED=true` + `x-demo-confirm: yes` + 6/min/IP. Converting CAND-002 creates EMP-021 (no collision).

---

## 4. Synapse runbook (CLI 0.1.9)

```bash
synapse init                                        # hosted key (skip for --local)
synapse build --auto --all-endpoints --server-name hr-api
synapse build --auto --all-endpoints --server-name it-api --new
synapse info                                        # log quota every hosted build
# LIVE:
synapse build --discover --auto --all-endpoints --server-name hr-api
```

Hosted Auto = no file, npx runner snippet. `--local` Python-only = `synapse_auto_server.py`. Custom = `<tool>_server.py` one `@mcp.tool`. Static tree-sitter detection only — literal decorators or invisible. Rebuilds reuse `surface_cache.json` until `--discover`. v1 flags fatal. Docs site stale — trust README + `--help`.

---

## 5. Safety — Cite-Before-Act (measured)

Order: CITE preview+hash → CHECK scope/hash/approval → ACT → RECORD audit line (allow AND deny).
Classes: A read auto-allow · B mutating 1 approval · C destructive double approval · unknown = deny-closed.
UX: `⚠️ WRITE PREVIEW <id> … Reply APPROVE <id>` / `🛑 DESTRUCTIVE … APPROVE twice` / `DENIED <reason>` / `CONFLICT: key reused`.
Ledger: PK(actor,operation,key), fencing lease_token, commit business+SUCCEEDED+audit in one TX. Secrets `${ENV:VAR}` redacted at every sink, hash over redacted form.
Audit: `audit.jsonl` hash chain `sha256(prev‖canonical)`, seq from 1, verifier reports firstBadSeq.

**Measured (eval/run.py, 40 cases): guarded 30 BLOCK + 1 WARN + 9 ALLOW = 97.5% acc (39/40) / 96.8% block (30/31) / 0% FP @ ~11ms MOCK + 5 LIVE; baseline 29.0% block / 11.1% FP (weak-by-design single-signal comparator).** CI fails if block <90% or FP >15%. Live budget ≤500ms.

---

## 6. 60s demo + fallback P0-P4

Terminal + agent trace + audit visible. 0-8s hook (Priya/CAND-002 Monday, 11 tickets) → 8-20s stage preview with citations → 20-32s attack (prompt-inject "skip checks" refused + duplicate returns cached) → 32-48s approve → ACTIVE + receipt → 48-60s audit + `synapse build` output. "8 tools deleted. 1 decision."

P0 video → P1 live (localhost:8000 + ngrok mirror, NOT paid cloud) → P2 `--local` Ollama → P3 Inspector/curl → P4 narrative flip. Kill-network + quota + wrong-model drills, pass <90s to fallback. LIVE client = Inspector Web UI only (Reconnect re-lists in 3s); Cursor/VS Code/Desktop configs = backup proof, never live (all cache tool lists till restart).

---

## 7. Gates (in order) + tripwires

G1 lint (ruff+black) → G2 openapi operationIds → G3 validate counts/traps → G4 pytest smoke 8-12 (no ≥80% gate) → G5 eval ≥95%/FP≤15% ✅ → G6 discover == 14 tools (13 baseline + L1; 12 functional if health excluded via allowlist). Red = stop at that gate.

## 9. Verified stack verdict (10 killer lanes, 2026-11-22)

7/9 KEEP, rest SWITCHED and already patched above. Evidence in `research/verify/01-10`.

- Backend: **KEEP FastAPI** — best static detection + operation_id control + `/docs` rerun. Django admin/Frappe/Flask lose on this rubric.
- MCP: **KEEP FastMCP 4.2.4 (pinned)** — `fastapi_mcp` stale ~16mo, weak naming, token bloat. 13 hand-curated `@mcp.tool`s (11 functional + 2 health), `on_duplicate_tools=error`, CI asserts count == 13 (11 with health excluded).
- DB: **SQLite-only golden** (WAL, `VACUUM INTO` snapshot, file-copy reset, offline). Postgres/Neon = opt-in backup only — dual-dialect tax + cold starts kill solo demos.
- ORM: **Pydantic v2 kept, SQLAlchemy/Alembic dropped** for demo — raw SQL + `response_model` + `schema.sql`/`seed.py`. Zero migration need at 79 rows; smallest hallucination surface.
- Deploy: **localhost + ngrok primary** (zero cold start, survives Wi-Fi death). Cloud = Fly 2s-wake or Render Free backup. Render $7 rejected; Vercel/Netlify/HF rejected for FastAPI+MCP.
- Models: **qwen3:4b-8k primary (agent tools 97.7) + qwen2.5-coder:7b-8k codegen (emit_tool_plan 80-90%)**. gemma3:4b killed (no native tools, HTTP 400). llama3.2:3b emergency-only (40-55%). Hosted frontier default for judged runs; cached-JSON P3 fallback.
- Docker: **single-process golden** (2×uvicorn + SQLite, 5-15min setup, 3-cmd rerun). Compose = `compose.opt.yml` backup.
- Tests: **KEEP 40-case eval (measured ✅), pytest downscoped to smoke** — eval is the safety-points artifact; coverage≥80 + DeepEval-only rejected.
- Clients: **Inspector Web UI live** (see §6). Cursor/Desktop live killed (restart tax + stale cache).

Conditional GO — patches above applied (≤2h). Without the Ollama + FastMCP bumps, live chain risks silent 0%-tool failure.

T1 cold start >90s · T2 tools ≠13/14 (≠11/12 functional-only) · T3 discover median >90s/<3/5 → T3→T2 in 48h · T4 TTFT >20s · T5 emit_tool_plan <60% → cached-JSON · T6 video >90s · T7 scorecard red · T8 quota <40% → freeze hosted. Freeze D12. No pivot past T+20h.

---

## 8. 15-day path

D1 P0 evidence → D2 APIs → D3 compose → D4 seed → D5 Synapse 10/10 → D6 agent+Custom → D7 evals → D8 discover×5 + PIVOT GATE + fallback video → D9 P0-P4 → D10 packet → D11 video → D12 FREEZE → D13 10 dry runs → D14 submit dry-run → D15 stage pre-warmed.

Full day-by-day: `research/build/49-master-plan.md`. MOC: `research/build/50-index.md`.
