# 49 — Master Build Plan: 15-Day Solo Sprint to Judging (Track 3 + T2 Hedge)

**Date:** 2026-11-22 | **Role:** solo builder, ~6h/day (~90h total) | **Goal:** WIN Track 3 (HR+IT onboard copilot), T2 pivot-ready by D8
**Synthesizes:** `research/build/01-05, 08-12, 15, 18-20` + `research/final/01-20` (esp. 04, 15, 16, 17, 20) | **Gaps:** build docs 06-07, 13-14, 16-17, 21-48 not yet written — covered here by final/ sources, marked [SYNTH].

## 0. D1 P0 Gate — Quota / Language / Team (do not skip)

Answer before any `synapse init` (from `final/20` Q1-Q4, Q8-Q9):

| # | Question | Command / evidence | Pass → proceed |
|---|---|---|---|
| Q1 | Quota = 10 servers + 100k lines? Local bypasses? | `synapse info` before/after 1 hosted + 1 `--local` build → `evidence/quota-log.md` | hosted decrements, local does not; ≥8 servers free |
| Q2/Q3 | Python-only for `--local` file + Custom? | `synapse build --local` in `hr_service/` (expect `synapse_auto_server.py`) + in dummy TS repo (expect tool-names-only) | confirms Python-only → both systems Python/FastAPI |
| Q4 | Team cap? | Check event site/Devpost + organizer DM → `team.md` | freeze roles (solo = all three hats, time-boxed) |
| Q8 | `--discover` preserves server ID, <60s? | build → add route → rebuild w/o `--discover` (missing) → with `--discover` (present, same ID), time 3× | median <60s or trigger tripwire T3 |
| Q9 | Hosted Auto = no file, npx runner only? | 1 hosted Auto + 1 Custom build, record artifacts | npx snippet + `ENDPOINT_BASE_URL` wired |

**D1 exit:** `evidence/` folder with quota screenshot, both `--local` results, team cap note, `--discover` timings. If Q8 fails → downgrade T3→T2 within 48h (tripwire T3).

## 1. Day-by-Day Plan (15 days)

### D1 — P0 questions + repo skeleton (5h)
- AM: Q1-Q4, Q8-Q9 evidence runs (§0). Request Synapse API key now (issuance latency unknown).
- PM: scaffold `hr_service/`, `it_service/` (FastAPI + `operation_id hr_*/it_*` + Pydantic, per build/02); `.env.example` (HR_BASE_URL, IT_BASE_URL, ENDPOINT_BASE_URL, SYNAPSE_SERVER_ID, DEMO_MODE, ALLOW_DEMO_SEED).
- **Gate G1:** `ruff check + black --check` pass; `/openapi.json` parses; both `/health` 200. Else stop.

### D2 — FastAPIs green (6h)
- Implement HR 5 routes (H5 commented out) + IT 6 routes per build/02 §2-3. Route order: `/tickets/breaches` before `/{ticket_id}`.
- `uvicorn hr_service.main:app --port 8001` + `:8002`; curl every route; snapshot `openapi.json` × 2.
- **Gate G2:** `lint + openapi + validate + pytest` (see §4) all green.

### D3 — Docker + seed infra (6h)
- `docker-compose.yml` (build/01 §3): hr-directory:8001, ticketing-sla:8002, ollama:11434. Healthchecks: `curl -f .../hr/candidates?limit=1`, `.../it/tickets/breaches`.
- Port `build/03` DDL → `seed/schema.sql`; write `seed/seed.data.ts` codegen stub (fixed IDs, `seeded_at=2026-11-23T00:00:00Z`).
- **Tripwire check T1:** `docker compose up --build` cold start >90s on hotspot → trim image (slim, `--workers 1`).

### D4 — Seed data (6h)
- Implement `POST /demo/seed|reset`, `GET /demo/status` per build/18 (guards `ALLOW_DEMO_SEED` + `x-demo-confirm: yes`, 6/min/IP, single txn, `_snap_*` snapshot).
- Load 79 rows (20/20/20/20/8/6/5); run count + FK-orphan + invariant bundle (build/03 §6).
- **Gate G3:** counts exact; 3 breached; 4 weekend starts; LT-1005 conflict present; `/reset` p95 <1.5s; total `/seed` ≤5s SLA.

### D5 — Synapse builds (6h)
- `synapse init` → `synapse build --auto --all-endpoints --server-name hr-api` (4 tools) → `--server-name it-api --new` (6 tools). Capture both `SYNAPSE_SERVER_ID` + npx snippets (build/19 §4-5).
- `synapse info` → quota log; `cat .synapse/surface_cache.json | grep operation_id` vs allowlist IDs — 11/11 functional baseline match (13/13 with health).
- **Tripwire T2:** any gap = anti-pattern (dynamic route, missing include_router) → fix same day.

### D6 — Agent loop + safety tool (7h)
- AM: Custom `safety_check_server.py` (single `@mcp.tool`, stage→confirm→activate + idempotency ledger, per build/01 §4 + 04-auth §4-6). Scope map `read:all/write:all/admin:all` (build/04 §3-4).
- PM: agent Q1-Q3 script (coverage → oncall → reroute; headcount vs breach; convert CAND-002 → EMP-021). Wire `.cursor/mcp.json` (`MCP_REV:1`) + Claude Desktop config + Inspector CLI verify (13 tools baseline).
- **Gate G4:** 5/5 live runs green; TTFT p50 <10s.

### D7 — Safety evals v1 (6h)
- Generate 30-50 cases (`prompt_injection, jailbreak, pii_leak, ungrounded, tool_abuse, citation_precision, toxicity`) via AI; human-label expected pass/block.
- Harness `eval/run.py → scorecard.csv` (build/12 §5). Targets: overall ≥95%, per-category ≥80%, high-sev block ≥90%, FP <10%.
- **Gate G5:** scorecard committed; any red category → fix guard, not thresholds.

### D8 — Pivot decision + `--discover` rehearsal (6h) ⚠️ PIVOT GATE
- Live moment drill ×5: uncomment H5 → `synapse build --discover --auto --all-endpoints --server-name hr-api` → Cursor refresh → `get_oncall`/`hr_get_oncall` appears, same server ID → Q3 chain live.
- **PIVOT CHECK (final/17 §6 + final/20 R1):** pivot T3→T2 if ANY: (a) federation/2-API green fails 2 days, (b) hosted gRPC unreachable on venue-like NAT, (c) `--local` `no emit_tool_plan` on 2 models, (d) TTFT >20s, (e) `--discover` median >90s or <3/5 success. T2 MVP already exists (Custom tool + evals) → <1wk reframe.
- Record `demo-fallback.mp4` v1 (60s, timestamped, both servers visible).

### D9 — Fallback ladder P0-P4 (6h)
- P0 video + 3 canned JSON (OnCall, sla_breach_list, reroute result). P1 `--mode=live|cached|local` flag + narration line. P2 `synapse_auto_server.py` curated 5-8 tools + FastMCP + `ollama ps` CONTEXT=8192 check + `SYNAPSE_TELEMETRY=0`. P3 hotspot + spare laptop (pre-pulled `qwen2.5-coder:7b` + `gemma3:4b`). P4 narrative flip.
- **Drill:** airplane-mode → P2 tool result on screen <90s (log seconds-to-fallback).

### D10 — Packet skeleton (6h)
- `submission/` per build/15 §2: README, ARCHITECTURE (mermaid + PNG), BENCHMARKS (cold-start, p50/p95, TTFT, VRAM `ollama ps`), LIMITS (₹0, quota screenshot, 2+ proof PNGs), PITCH script 75s, deck outline 8 slides, `benchmark/run.js`.
- Quota-proof: `synapse info` (servers 2/10, indexed lines), Render $7 vs free-sleep note (build/05 §4).

### D11 — Video record (6h)
- OBS 1080p30 + CapCut: 0-10s hook (Priya/CAND-002 Monday story) → 10-50s live Q1-Q3 + safety badge → 50-75s resilience flip (P2) → 75-90s why-Synapse. Auto-captions → `captions/demo.srt`. YouTube unlisted.
- **Tripwire T6:** video >90s or inaudible on phone speaker → re-cut same day.

### D12 — Hardening + FREEZE (6h) 🔒
- Cold-start on fresh machine/clone; trim tools ≤10; CORS/server-card check; `quota-proof.md`; kill-network + wrong-model + quota-exceeded + Ctrl-C `--resume` drills.
- **FEATURE FREEZE end of D12.** After this: only fallback/docs/rehearsal (final/17 §7).

### D13 — Rehearsal block (5h)
- 10 dry runs (5 live, 3 P1/P2 fallback, 2 P0 video-only). Log each: mode, TTFT, pass/fail, fallback seconds. Fix only narration + cache-bust (`MCP_REV` bump, toggle off/on), no code.

### D14 — Packet final + submission dry-run (5h)
- All README links open incognito; ARCHITECTURE renders in GitHub + PDF; LIMITS numbers match screenshots; fresh-clone run works; deck PDF + QR scannable.
- Portal dry-run upload (video format/length, write-up, server IDs, comparison table for T2-hedge, 2 dual-system questions + live-update clip for T3).

### D15 — Judging day (3h + buffer)
- T-60min pre-warm: `scripts/up.sh cloud` loop + `/docs` tab open + `ollama ps` check + Inspector `tools/list` (expect 10 or 11). USB + `demo/golden.mp4` + hotspot + spare laptop staged.
- Stage choreography: open with P0 playing *while* first live curl runs (covers 30s cold window). 3 scripted Q&A (centrality / privacy-what-leaves / safety-denial) rehearsed.

## 2. Dependency Graph (critical path)

```
D1 P0(Q1-Q4,Q8-Q9) ──→ D2 FastAPI(8001/8002, openapi clean) ──→ D3 Docker compose ──→ D4 seed(79 rows, /reset<1.5s)
                                                                                            ↓
D5 synapse builds (hr-api, it-api --new, 13/13 tools via allowlist) ──→ D6 agent Q1-Q3 + Custom safety tool ──→ D7 evals scorecard
                                                                    ↓ (parallel ok D6-D7)
D8 --discover ×5 + PIVOT GATE ──→ D9 P0-P4 fallback ──→ D10 packet skeleton ──→ D11 video ──→ D12 FREEZE
                                                                                            ↓
                                                              D13 10 dry runs ──→ D14 submit dry-run ──→ D15 stage
NEVER INVERT: no Synapse before APIs green · no video before 5/5 live runs · no eval claims without scorecard.csv (final/17 §5)
```

## 3. File Map (repo layout to create)

```
track3/
├── hr_service/{main.py, routers/hr.py, models.py, db.py}   # :8001, build/02 §2
├── it_service/{main.py, routers/it.py, models.py, db.py}   # :8002, build/02 §3
├── seed/{schema.sql (build/03 §2), seed.data.ts, reset.sql, validate.py}
├── server/src/demo/{seed.controller.ts, seed.service.ts}   # build/18 (or FastAPI equiv)
├── safety_check_server.py    # Custom 1-tool (build/04 + build/01 §4)
├── synapse_auto_server.py    # --local fallback (build/01 §7 P2)
├── .cursor/mcp.json          # MCP_REV:1 (build/01 §6, build/20 §2)
├── docker-compose.yml        # build/01 §3 (NOT build/05 :8000 single — frozen 8001/8002)
├── Modelfile.local-8k        # FROM qwen2.5-coder:7b, num_ctx 8192 (build/10 §3)
├── eval/{run.py, cases/safety_*.json (30-50), expected/, scorecard.csv}  # build/12 §5
├── submission/{README, ARCHITECTURE, BENCHMARKS, LIMITS, PITCH, captions/demo.srt, assets/quota-proof/, deck/outline.md, benchmark/run.js}  # build/15 §2
├── scripts/{up.sh, prewarm.sh}  # build/05 §3
├── evidence/{quota-log.md, quota-local-matrix.md, federation-proof.png}  # final/20 R7
├── .env.example  # HR_BASE_URL, IT_BASE_URL, ENDPOINT_BASE_URL, DATABASE_URL, SYNAPSE_SERVER_ID, MCP_REV, OLLAMA_HOST
└── research/build/{01-50}   # this plan = 49, index = 50
```

## 4. Anti-Hallucination Gates (must pass in order, before next step)

```
G1 lint:        ruff check . && black --check . && ruff format --check .   # no lint → no commit
G2 openapi:     python -c "import hr_service.main, it_service.main" &&
                curl -s localhost:8001/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); assert all('operationId' in o for p in d['paths'].values() for o in p.values())"  # same :8002
G3 validate:    python seed/validate.py  # counts 20/20/20/20/8/6/5 + 0 orphans + 3 breached + 4 weekend + LT-1005 hold
G4 pytest:      coverage run -m pytest tests/ -m "not llm_judge" && coverage report -m  # fail_under=80
G5 eval:        python eval/run.py --cases eval/cases --out eval/scorecard.csv  # overall ≥95%, category ≥80%
G6 discover:    synapse build --discover --auto --all-endpoints --server-name hr-api && Inspector tools/list == 11
```

Rule: **lint → openapi → validate → pytest → eval → discover.** Any gate red = stop, fix, re-run from that gate. Never demo past a red gate. Never edit eval thresholds to pass.

## 5. Eight Numeric Drop Tripwires (kill the scope, not the demo)

| # | Metric | Tripwire (drop if breached) | Fallback |
|---|---|---|---|
| T1 | Cold start (fresh `docker compose up --build` → healthy) | **>90s** on hotspot | Trim image/workers; else P2 local-only |
| T2 | Tool coverage (allowlist operationIds in surface_cache) | **<11/11 functional baseline, <12/12 post-discover** | Fix anti-pattern same day; no Synapse progress until 11/11 |
| T3 | `--discover` latency / reliability (5 trials) | **median >90s OR success <3/5** | Downgrade T3→T2 primary within 48h |
| T4 | Agent TTFT p50 (Q1-Q3 median, pinned model) | **>20s** (pivot); **>60s p95 happy-path** (cut scope to p95 ≤45s) | Stronger model or cached-JSON mode; cut fields/seed |
| T5 | Local model `emit_tool_plan` (20 trials, temp 0-0.2) | **success <60% OR ≥3 consecutive failures** | Stop debugging models → cached-JSON fallback |
| T6 | Video length / intelligibility | **>90s OR inaudible on phone speaker** | Re-cut same day; P0 video is ship-blocking |
| T7 | Safety scorecard | **overall <95% OR any category <80% OR high-sev block <90% OR FP >10%** | Fix guard + re-run; never ship red scorecard |
| T8 | Hosted quota before demo week | **remaining <40% (i.e. >6/10 servers or >60k lines used)** | Freeze hosted builds; `--local` only; 2nd account contingency |

Plus scope trips from final/20: tool-selection accuracy <70% on 10 tasks → cut to ≤8 tools → hand-write Custom tool; team <2 by Wk1 end → abandon T3→T2 solo-safe.

## 6. Risks → Mitigations (top 5)

1. Venue Wi-Fi death → P0-P4 ladder rehearsed; airplane-mode drill <90s; hotspot + spare laptop (build/05 §5, build/01 §7).
2. Cold-start 30-60s sleep → Render Starter $7 or pre-warm loop + P0 video plays during boot (build/05 §4).
3. Stale tool cache (`surface_cache.json`, Cursor hash) → always `--discover`; `MCP_REV` bump; Inspector CLI as ground truth (build/19-20).
4. Small-model JSON fail → pin `qwen2.5-coder:7b` + retry-with-repair; `gemma3:4b` low-VRAM; never default `llama3.2:3b` for tools (build/10).
5. Burnout/sunk-cost → freeze D12; pivot branch T2 green by D10 regardless; no T3 chase past D8 (final/17 §6).

*Next: `50-index.md` (MOC). Then execute D1.*
