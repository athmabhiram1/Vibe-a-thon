# 17 — Effort Plan: Solo Builder, Lots of Time (3-Week Win Plan)

**Date:** 2026-11-22 | **Assumption:** 1 solo builder, high hours (~25-35 hrs/week, ~80-100 hrs total) | **Goal:** WIN, not participate
**Primary:** Track 3 (2 systems + live `--discover`) | **Backup:** Track 2 (Python Custom safety tool, <1 wk pivot)
**Stack:** FastAPI + Docker (2× Synapse/Matrix homeservers) + Synapse CLI 0.1.9 + Ollama `--local` + FastMCP fallback

---

## 1. TL;DR — Where Time Actually Goes

FastAPI is NOT the bottleneck (10 min scaffold → 1 hr usable API → weekend prod). Synapse builds + demo hardening + evals + video/packet win.

| Block | Solo Hours | AI / Tooling Leverage | Human-Judgment Core |
|---|---|---|---|
| FastAPI scaffold + 2-server Docker | 8-12h | 70% AI (scaffold, compose, routers) | 30% human (ports, federation keys, well-known) |
| Seed data + 2-system federation | 8-10h | 40% AI | 60% human (verify federate, rooms, users) |
| Synapse builds (auto + custom + local) | 10-14h | 30% AI | 70% human (endpoint selection, `--discover` discipline) |
| Agent / `--discover` live path + Ollama matrix | 12-16h | 50% AI | 50% human (prompt tuning, TTFT/accuracy bench) |
| Safety evals (30-50 cases) + scorecard | 10-14h | 60% AI (generate cases) | 40% human (label, red-team, false-positive review) |
| Fallback modes + venue hardening | 6-8h | 30% AI | 70% human (kill-network drills) |
| Video (60-90s) + judging packet + README | 10-14h | 50% AI (script, edit assist) | 50% human (narrative, on-camera, quota proof) |
| Buffer / rehearsal (10 dry runs) | 8-10h | 10% AI | 90% human |
| **Total** | **~72-98h = 3 weeks** | | |

> Rule: AI drafts code/cases/video script. Human verifies federation, live demo, safety labels, and story. Never outsource the "arena moment."

---

## 2. Baseline Anchors (from research)

1. **FastAPI scaffold:** 10-min CRUD (`FastAPI + uvicorn`, `/docs` free) → <60 min 4-endpoint validated API → weekend full CRUD + SQLite + JWT + tests + Docker. Solo cost: **0.5-2 days**. Source: `10-track-choice.md §1`.
2. **Synapse quota:** No hard 10-server/100k-line default in Synapse OSS docs — treat as **competition rule**. Stay at 2-3 homeservers, small rooms, disable presence, document compliance. Source: `10-track-choice.md §1`, `03-synapse-technical.md §2.5`.
3. **`--local` models:** Start `gemma3:4b` (laptop default) + fallback `llama3.2:3b` (~2GB); 7-8B needs ~16GB RAM/8GB VRAM; 27B+ needs DGX. Pre-pull 2 tags, pin tags, test 10-20 prompts, `ollama ps` for GPU-split, conservative `num_ctx`. Source: `10-track-choice.md §1`.
4. **Synapse CLI reality (0.1.9):** Python-or-nothing for files; `.js/.jsx` invisible; Auto = dumb HTTP forwards to your *deployed* API; Custom = one `@mcp.tool` per build; cache reuses `surface_cache.json` until `--discover`; v1 flags fatal. Source: `03-synapse-technical.md §3`.
5. **Winner bias:** Overall → visceral consumer demo; infra → honorable/track. Lead T3 with user story, hide federation as superpower. Source: `10-track-choice.md §1`.

---

## 3. Week-by-Week Plan

### WK1 — APIs + Seed + 2-Server Docker (Goal: federated, demo-able base)

**Target exit:** `docker compose up` → 2 federated homeservers + 1 FastAPI app + seeded users/rooms, federation verified.

- [ ] **D1 (4-6h): FastAPI scaffold.** `FastAPI(title, description)` + `operation_id="snake_case"` on every route + Pydantic models. Routes: `/ping`, `/directory/search`, `/rooms/{id}`, `/safety/check`, `/discover`. Verify `/openapi.json` + `/docs` clean. Pin `fastapi, uvicorn[standard], pydantic>=2, fastmcp>=4.1, fastapi-mcp>=0.4.0`. AI scaffolds; human fixes `operation_id` + auth headers (`Authorization` passthrough, no `Header()`-required traps).
- [ ] **D2 (4-6h): 2-server Docker.** `docker-compose.yml`: `synapse-a` (8008), `synapse-b` (8009), `fastapi` (8000), `ollama` (11434). `homeserver-a.yaml` / `-b.yaml`, `serve_server_wellknown: true`, shared signing-key flow, Tailscale/static IPs if remote. Disable presence, set MAU/complexity headroom. Health: `/_matrix/federation/v1/version` both ways.
- [ ] **D3 (4-6h): Seed + federation proof.** Script `seed.py`: 6-10 users, 4-6 rooms (public/private/direct), 30+ messages, 2 cross-server rooms. Screenshot `matrix-federation-tester` green + Element cross-server chat. Save `federation-proof.png` for packet.
- [ ] **D4 (2-4h): Ollama registry.** Pull `gemma3:4b` + `llama3.2:3b` (or `qwen2.5-coder:7b` for codegen). Set `num_ctx 8192+` via Modelfile, verify `ollama ps` CONTEXT + GPU%. Record 10-prompt baseline (correctness, fields-present, TTFT, total, RAM).
- **Deliverable:** repo runs on fresh clone with 3 commands; `docs/WK1-DEMO.md` with curl proofs.

**Dependencies:** Nothing blocks WK1. Do NOT touch Synapse CLI until federation is green.

### WK2 — Synapse + Agent + Safety (Goal: live `--discover` + T2 branch)

**Target exit:** `synapse build --discover` live path works E2E + local fallback file exists + 30-50 safety evals scored.

- [ ] **D5-6 (8-10h): Synapse builds.**
  - `synapse init` (hosted key) + `synapse analyze` → check `project_schema.txt` / `statistics.json` / indexed lines vs 100k quota.
  - Hosted Auto: `synapse build --auto --all-endpoints --discover` → capture `SYNAPSE_SERVER_ID` + runner config (`npx -y @2ndbrainlabs-ai/synapse-mcp`). Confirm tools call *deployed* FastAPI (`ENDPOINT_BASE_URL` set).
  - `--local` Auto: `synapse build --local --discover` (Python only → `synapse_auto_server.py`). Expect dumb forwards; curate allowlist to ≤10 tools via `include_operations`.
  - Custom: 1 composed safety tool (`safety_check_server.py`: classify→shape→render→verify, single `@mcp.tool`). Hand-harden error/retry paths (generator only does happy-path).
  - Gotcha drills: stale-cache (`--discover` always in demo), headless flags, v1-flag fatal, `.js` invisibility.
- [ ] **D7-8 (8-10h): Agent / `--discover` live path.**
  - CLI: `synapse build --auto --discover --mode=live` + `--smart-names`; agent loop `model → tool → exec → result → response` <10s target.
  - Consumer framing: *"Type a name → live federated discovery across 2 servers → local-model-verified badge."* Tune prompts, pin Ollama tags in Verified Registry, log TTFT/accuracy.
  - Curate to FastMCP if auto-bloat: `FastMCP.from_fastapi(app)` → hand-picked 5-8 tools (vendors warn auto-REST→MCP underperforms).
- [ ] **D9-10 (8-10h): Safety evals (Track 2 reuse + T3 trust badge).**
  - Generate 30-50 cases with AI (abuse, injection, PII leak, spam-flood, impersonation, NSFW, exfil via `${VAR}`, federation-spoof), human labels expected pass/block + severity.
  - Harness `eval/run.py`: per-case prompt → tool → verdict; scorecard: block-rate, false-positive rate, latency, vs-baseline (no-check). Target: ≥90% block on high-severity, <10% FP.
  - Save `eval/scorecard.csv` + `eval/TRANSCRIPT.md` (3 live abuse demos for judges).
- **Deliverable:** live demo script (3 queries) green 5/5 runs; eval scorecard; T2-branch MVP done (this IS the pivot artifact).

**Dependencies:** WK1 federation green → Synapse builds → agent path → evals. Evals can parallelize with agent tuning if time-pressed.

### WK3 — Fallback + Polish + Packet (Goal: unkillable demo + winning packet)

**Target exit:** judges never see a spinner; video + packet submitted.

- [ ] **D11-12 (6-8h): Fallback + hardening (P0-P4).**
  - P0: 60s timestamped video of successful `--discover` (both servers visible) + 3 canned JSON responses baked in.
  - P1: `--mode=live|cached|local` flag; rehearsed line: *"Venue Wi-Fi flaky — switching to local replica, same code path."*
  - P2: local-only stack (both Synapse on one laptop + pre-pulled models + `localhost:11434` health check + `SYNAPSE_TELEMETRY=0` for offline claim).
  - P3: hotspot + venue Wi-Fi + offline; hot-spare laptop with cloned images; `serve_server_wellknown` preconfigured.
  - P4: narrative flip — *"This is why local-first matters — discovery works partitioned."*
  - Drills: kill-network, wrong-model, quota-exceeded, Ctrl-C `--resume` ledger check.
- [ ] **D13 (4-6h): Polish.** Cold-start test on fresh machine (keys, env, `pip install mcp`, `ast.parse`, Claude Desktop handshake via `npx synapse-mcp`). Trim tools to ≤10. Fix CORS/server-card exposure. `quota-proof.md` (servers=2, lines indexed, MAU screenshot from `synapse info`).
- [ ] **D14-15 (8-10h): Video + judging packet.**
  - Video 60-90s: 0-10s hook (user story) → 10-50s live discovery + safety badge → 50-75s resilience flip → 75-90s "why Synapse" (federation + discovery + local). Captions + timestamps.
  - Packet: `README.md` (3-command quickstart), `ARCHITECTURE.md` (diagram: 2 servers + FastAPI + Ollama + Synapse CLI), `QUOTA.md`, `BENCHMARKS.md` (TTFT/accuracy/VRAM table), `SAFETY.md` (scorecard + 3 transcripts), `REPRO.md` (judge rerun steps), `FALLBACK.md`.
  - 10 dry runs, 3 scripted Q&A (centrality / privacy / safety).
- **Deliverable:** `/research/final/` packet + video link + frozen tag `v1.0-judging`.

---

## 4. Human vs AI Split (Solo-Max Leverage)

| Task | AI does | Human does |
|---|---|---|
| FastAPI routes, Docker compose, seed script | Draft 80% | Fix ports, keys, federation verify |
| Synapse endpoint naming, tool descriptions | `--smart-names` draft | Curate to ≤10, rewrite judge-facing strings |
| Safety cases (30-50) | Generate variants + harness | Label expected, adjudicate FPs, run red-team |
| Agent prompts, Ollama bench | Sweep params | Pick operating point (accuracy vs TTFT) |
| Video script, README, packet prose | Draft + tighten | Story, on-camera, quota screenshots |
| Live demo, drills, Q&A | — | 100% human (rehearse 10×) |

**Solo rule:** batch AI work (mornings: generate), human verify (afternoons: run + record). No untested AI output enters the demo path.

---

## 5. Dependency Order (Critical Path)

```
WK1: FastAPI (/openapi clean) → Docker 2-server → federation green → Ollama registry
                                            ↓
WK2: synapse analyze → hosted Auto → --local Auto → Custom 1-tool → agent --discover live
                                            ↓                    ↘ evals (parallelizable)
WK3: fallback modes → venue hardening → polish/cold-start → video + packet → 10 dry runs
```

**Never invert:** no Synapse before federation green; no video before live path green 5/5; no eval claims without `scorecard.csv`.

---

## 6. Pivot Trigger — Track 2 Reuse (<1 Week)

**Trigger (check end of WK2 D8):** if ANY of (a) federation ungreen after 2 days, (b) hosted gRPC unreachable on venue-like NAT, (c) `--local` codegen fails (`no emit_tool_plan call`) on 2 models, (d) TTFT >20s on available HW — **pivot to Track 2.**

**Why <1 wk works:** T2 MVP is already built as WK2 branch:
- FastAPI (`/safety/check` + 4 endpoints) → `FastMCP.from_fastapi` curated server — 1 day.
- Custom safety tool (`safety_check_server.py`) + 30-50 evals + scorecard — 2-3 days.
- Packet reframe (safety rubric + abuse demo + FP story) + 60s video — 2 days.

**Pivot checklist:** freeze `t3-attempt/` branch, retitle README to safety tool, add `THREAT-MODEL.md`, rerun evals 3× for variance, record abuse-demo video. Do NOT chase T3 live infra past D8 — sunk-cost kills wins.

**Emergency (<48h left):** Track 1 only — reuse FastAPI + 1 server + canned discovery.

---

## 7. Solo Risks + Mitigations

| Risk | Mitigation |
|---|---|
| Venue Wi-Fi kills federation | P0-P4 fallback; local-only Docker; hotspot; canned JSON |
| Synapse hosted quota/rate-limit | `--local` branch + `synapse info` quota screenshot; delta-rebuilds |
| Small model codegen fail | Stronger model (`qwen3-coder:30b` if RAM allows, else hosted frontier for final pass) |
| Tool-bloat confuses agent | Allowlist ≤10, then hand-curate FastMCP |
| Safety subjectivity (T2) | Quantified scorecard + baseline + transcripts |
| Burnout (solo ~90h) | WK1 heaviest; WK3 is drills+packet, no new features after D12 (feature freeze) |

**Feature freeze: end of D12.** After that, only fallback, docs, rehearsal.

---

## 8. Definition of Done

- [ ] `docker compose up` + `seed.py` + federation proof green on fresh machine
- [ ] `synapse build --discover` live 5/5 + `synapse_auto_server.py` + 1 custom tool file
- [ ] Agent TTFT <10s median on pinned models, benchmark table saved
- [ ] 30-50 evals scored, `scorecard.csv` + 3 transcripts
- [ ] P0-P4 fallback rehearsed (kill-network drill passed)
- [ ] 60-90s video + judging packet (quota, benchmarks, safety, repro)
- [ ] Pivot branch (T2) green by D10 regardless — insurance is done, not extra

*Companion docs: `10-track-choice.md` (strategy), `08-tech-feasibility.md` (FastAPI/MCP patterns), `03-synapse-technical.md` (CLI limits).*
