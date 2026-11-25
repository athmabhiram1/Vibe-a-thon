# 01 — Build Architecture: Track 3 HR+IT Onboard Copilot

**Date:** 2026-11-22 | **Track:** 3 (copilot across two systems) | **Stack:** 2× FastAPI + SQLite + Synapse Auto + Custom + MCP clients
**Verified against:** `research/final/15-endpoints.md` (11 tools, topology, runbook) + `research/final/17-effort-plan.md` (WK1–WK3, Docker, fallback P0–P4)

---

## 1. Topology diagram

```
                    ┌──────────────────────────────────────────────┐
                    │              MCP CLIENTS (demo surface)       │
                    │  Claude Desktop (restart) │ Cursor (hot-reload│
                    │  MCP Inspector CLI (verify)                   │
                    └──────┬──────────────────────┬────────────────┘
                           │ stdio / npx          │ stdio / npx
              ┌────────────▼──────────┐  ┌────────▼──────────────┐
              │ SYNAPSE SERVER #1     │  │ SYNAPSE SERVER #2     │
              │ id: `hr-api`          │  │ id: `it-api`          │
              │ Auto (hosted)         │  │ Auto (hosted)         │
              │ tools: H1–H4 (+H5 live)│ │ tools: I1–I6            │
              │ runner: npx           │  │ runner: npx           │
              │ @2ndbrainlabs-ai/     │  │ @2ndbrainlabs-ai/     │
              │  synapse-mcp          │  │  synapse-mcp          │
              └────────────┬──────────┘  └────────┬──────────────┘
                           │ HTTP forward          │ HTTP forward
                           │ ENDPOINT_BASE_URL     │ ENDPOINT_BASE_URL
              ┌────────────▼──────────┐  ┌────────▼──────────────┐
              │ FASTAPI #1            │  │ FASTAPI #2            │
              │ `hr-directory` :8001  │  │ `ticketing-sla` :8002 │
              │ prefix /hr            │  │ prefix /it            │
              │ SQLite: hr.db         │  │ SQLite: it.db         │
              └───────────────────────┘  └───────────────────────┘
                           └──────────┬────────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │ CUSTOM SAFETY LAYER     │
                         │ `safety_check_server.py`│
                         │ 1× @mcp.tool (Custom)   │
                         │ stage→confirm→activate  │
                         │ + idempotency ledger    │
                         │ wraps create/assign/    │
                         │ reroute writes          │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │ FALLBACK LOCAL MODE     │
                         │ synapse_auto_server.py  │
                         │ FastMCP curated 5–8     │
                         │ Ollama gemma3:4b /      │
                         │  llama3.2:3b :11434     │
                         │ canned OnCall JSON +    │
                         │ demo-fallback.mp4       │
                         └─────────────────────────┘
```

Join keys (agent does the join, servers pre-compute the hard part):
- `assignee_email ↔ employee email` (HR H3 → IT I2/I5)
- `ticket.created_at ↔ shift_calendar(team,date)` → on-shift? (powers Q1/Q2)
- `sla_breach_list` pre-computes `deadline_at < now AND status != resolved` so agent never pages all tickets.

---

## 2. Ports (frozen — do not drift)

| Process | Port | Mount / URL | Source of truth |
|---|---|---|---|
| HR FastAPI `hr-directory` | **8001** | `http://localhost:8001/hr` · `/docs` · `/openapi.json` | `15-endpoints.md §1` |
| IT FastAPI `ticketing-sla` | **8002** | `http://localhost:8002/it` · `/docs` · `/openapi.json` | `15-endpoints.md §1` |
| HR SQLite | — (file) | `hr_service/hr.db` (Seed: candidates, employees, shifts, oncall roster) | `14-seed-data.md` pattern |
| IT SQLite | — (file) | `it_service/it.db` (Seed: laptops, tickets incl. T-551 breached) | `14-seed-data.md` pattern |
| Ollama (local fallback) | 11434 | `http://localhost:11434` · models `gemma3:4b`, `llama3.2:3b` | `17-effort-plan.md §2.3` |
| Legacy Matrix/Synapse-homeserver refs | 8008/8009 | **NOT USED in final Track 3 build** — superseded; kept only as WK1 federation history per `17 §WK1`. Do not bind. | `17-effort-plan.md §WK1` |
| Legacy single-FastAPI | 8000 | **NOT USED** — split into 8001/8002. | — |

Run:

```bash
uvicorn hr_service.main:app --port 8001
uvicorn it_service.main:app --port 8002
curl -s localhost:8001/hr/shifts?team=support-night&date=2026-11-22 | jq .
curl -s localhost:8002/it/tickets/breaches | jq .
```

---

## 3. Docker Compose (final)

```yaml
# docker-compose.yml — Track 3 final (2 APIs + Ollama; Synapse CLI is hosted, not a container)
services:
  hr-directory:
    build: ./hr_service
    ports: ["8001:8001"]
    command: uvicorn main:app --host 0.0.0.0 --port 8001
    environment:
      - HR_BASE_URL=http://hr-directory:8001
      - ENDPOINT_BASE_URL=http://hr-directory:8001
      - DATABASE_URL=sqlite:///./hr.db
    volumes: ["./hr_service:/app", "hr-data:/app/data"]
    healthcheck: { test: ["CMD", "curl", "-f", "http://localhost:8001/hr/candidates?limit=1"], interval: 10s, retries: 5 }

  ticketing-sla:
    build: ./it_service
    ports: ["8002:8002"]
    command: uvicorn main:app --host 0.0.0.0 --port 8002
    environment:
      - IT_BASE_URL=http://ticketing-sla:8002
      - ENDPOINT_BASE_URL=http://ticketing-sla:8002
      - DATABASE_URL=sqlite:///./it.db
    volumes: ["./it_service:/app", "it-data:/app/data"]
    healthcheck: { test: ["CMD", "curl", "-f", "http://localhost:8002/it/tickets/breaches"], interval: 10s, retries: 5 }

  ollama:  # local-fallback replica only
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: ["ollama-data:/root/.ollama"]

volumes: { hr-data: {}, it-data: {}, ollama-data: {} }
```

> `17-effort-plan.md §WK1-D2` lists `synapse-a:8008/synapse-b:8009/fastapi:8000` — that was the **federation-spike layout**. Final compose above replaces it. Keep wellknown/federation notes out of this file; they belong to the backup narrative only.

---

## 4. ENDPOINT_BASE_URL wiring (hosted Auto forwards to LIVE API)

Synapse Auto (hosted) generates **no local logic** — it emits endpoint config served by the `npx` runner that HTTP-forwards to your deployed FastAPI (`04-synapse-auto.md §1`). The runner resolves the target from env:

| Synapse server ID | Forwards to | Env the runner reads | Build command |
|---|---|---|---|
| `hr-api` | HR FastAPI :8001 | `ENDPOINT_BASE_URL=http://localhost:8001` (local demo) / `HR_BASE_URL=http://localhost:8001` | `synapse build --auto --all-endpoints --smart-names --server-name hr-api` |
| `it-api` | IT FastAPI :8002 | `ENDPOINT_BASE_URL=http://localhost:8002` / `IT_BASE_URL=http://localhost:8002` | `synapse build --auto --all-endpoints --smart-names --server-name it-api --new` |
| `onboarding-safety` (Custom, 1 tool) | Wraps both (preview→activate) | `HR_BASE_URL` + `IT_BASE_URL` | `synapse build --custom -q "stage then activate employee onboarding with confirm and idempotency"` → hand-add `confirm/preview_hash/idempotency_key` |

Rules (from `04 §3–§4` + `15 §4`):
1. One repo, **two server IDs** — rebuilds update the same ID (`.synapse/config.json`); client config keeps working.
2. Second server needs `--new` on first build, `--server-name <id>` thereafter.
3. **Always `--discover` after any route edit** — builds reuse `.synapse/surface_cache.json` otherwise. Live moment: add `GET /it/oncall-coverage` (L1, `it_service/routers/live_moment.py`) → `synapse build --discover --auto --endpoints "<expanded allowlist>" --server-name hr-api` → tool `it_oncall_coverage` appears, no client restart (Inspector Reconnect). H5 `GET /hr/oncall` is live on disk (baseline includes it); the old uncomment-H5 choreography is dead. Full allowlists in `docs/CLIENTS.md` §7.
4. Explicit `operation_id` on every route (= MCP tool name); prefix `hr_*`/`it_*` mentally — `15` uses bare names (`list_candidates`, `sla_breach_list`) which are already collision-free across the pair; do **not** rename mid-build.
5. `SYNAPSE_SERVER_ID` + runner snippet captured per server at build time; paste into client config below.

---

## 5. Synapse server IDs + tool inventory (14 total post-discover)

Baseline build = **13 tools** (H1-H5 + I1-I6 + 2 health; 11 functional-only); live `--discover` adds **L1 = 14th** (12 functional-only). 6 `/demo/*` ops always excluded via `--endpoints` allowlist (`docs/CLIENTS.md` §7).

**`hr-api` (HR :8001):**

| Tool (`operation_id`) | Route | Mode |
|---|---|---|
| `list_candidates` | `GET /hr/candidates` | baseline |
| `get_candidate` | `GET /hr/candidates/{candidate_id}` | baseline |
| `create_employee` | `POST /hr/employees` ⚠️ confirm-gated | baseline |
| `shift_calendar` | `GET /hr/shifts` | baseline |
| `hr_get_oncall` | `GET /hr/oncall` ⭐ | baseline (live on disk) |

**`it-api` (IT :8002):**

| Tool (`operation_id`) | Route | Mode |
|---|---|---|
| `list_equipment` | `GET /it/equipment` | baseline |
| `assign_laptop` | `POST /it/equipment/assign` ⚠️ confirm-gated | baseline |
| `create_ticket` | `POST /it/tickets` ⚠️ confirm-gated | baseline |
| `get_ticket` | `GET /it/tickets/{ticket_id}` | baseline |
| `reroute_ticket` | `POST /it/tickets/{ticket_id}/reroute` ⚠️ confirm-gated | baseline |
| `sla_breach_list` | `GET /it/tickets/breaches` (declare **before** `/{ticket_id}`) | baseline |
| `it_oncall_coverage` | `GET /it/oncall-coverage` ⭐ | **live `--discover` only** (expanded allowlist) |

Custom (separate file, Track 2 reuse + T3 trust badge): `safety_check_server.py` — single `@mcp.tool` composing classify→shape→render→verify; safety triple `onboard_preview` / `onboard_activate(preview_hash, confirm, idempotency_key)` per `05-fastmcp-custom.md §(b)`.

---

## 6. MCP client wiring

Cursor project file (`.cursor/mcp.json`) — hot-reload, preferred for live `--discover` (per `06-mcp-clients.md §3–§4`):

```json
{
  "mcpServers": {
    "hr-api": {
      "command": "npx",
      "args": ["-y", "@2ndbrainlabs-ai/synapse-mcp", "--server-id", "hr-api"],
      "env": { "ENDPOINT_BASE_URL": "http://localhost:8001", "MCP_REV": "1" }
    },
    "it-api": {
      "command": "npx",
      "args": ["-y", "@2ndbrainlabs-ai/synapse-mcp", "--server-id", "it-api"],
      "env": { "ENDPOINT_BASE_URL": "http://localhost:8002", "MCP_REV": "1" }
    }
  }
}
```

- **Cursor:** refresh icon hot-reloads; if the new tool (`it_oncall_coverage`) doesn't appear, bump `MCP_REV` 1→2 (hash-bust), toggle off→on.
- **Claude Desktop:** same JSON in `claude_desktop_config.json` → **full Quit + relaunch** required.
- **Verify independent of clients:** `npx -y @modelcontextprotocol/inspector --cli … --method tools/list` (expect 13 baseline, 14 post-discover; 11/12 functional-only).
- **Local fallback stdio:** `"onboard-local": { "command": "uv", "args": ["--directory", "C:\\ABS\\PATH\\TO\\track3", "run", "synapse_auto_server.py"] }` + `SYNAPSE_TELEMETRY=0`.

---

## 7. Fallback local mode (P0–P4, per `17 §WK3` + `15 §4.5`)

| Level | What | When |
|---|---|---|
| P0 | 60s timestamped `demo-fallback.mp4` (both servers visible) + 3 canned JSON (`OnCall`, `sla_breach_list`, `reroute_ticket` result) | `--discover` stalls → play video, narrate, never spinner |
| P1 | `--mode=live\|cached\|local` flag; line: *"Venue Wi-Fi flaky — switching to local replica, same code path."* | network flicker |
| P2 | Local-only: `synapse_auto_server.py` (`--local` build, Python passthrough) + FastMCP curated 5–8 tools + `localhost:11434` health check + `SYNAPSE_TELEMETRY=0` | offline |
| P3 | Hotspot + spare laptop with pre-pulled images/models | venue Wi-Fi dead |
| P4 | Narrative flip: *"This is why local-first matters — discovery works partitioned."* | judges probe resilience |

Feature freeze end of D12; after that only fallback/docs/rehearsal.

---

## 8. Env table (single copy-paste source)

| Var | Value (local demo) | Consumed by |
|---|---|---|
| `HR_BASE_URL` | `http://localhost:8001` | agent joins, Custom safety tool, seed scripts |
| `IT_BASE_URL` | `http://localhost:8002` | agent joins, Custom safety tool, seed scripts |
| `ENDPOINT_BASE_URL` | per-server value above (set per runner invocation) | Synapse hosted runner forward target |
| `DATABASE_URL` | `sqlite:///./hr.db` / `sqlite:///./it.db` | each FastAPI service |
| `SYNAPSE_SERVER_ID` | `hr-api` / `it-api` | `npx synapse-mcp` runner args |
| `SYNAPSE_TELEMETRY` | `0` (offline/fallback claim) | Synapse CLI local |
| `MCP_REV` | `1` → bump to `2` live | Cursor cache-bust |
| `OLLAMA_HOST` | `http://localhost:11434` | local model replica |

`.env.example` commits placeholder names only — never real tokens (per `05 §(c)` secret-hygiene posture).

---

## 9. Verification vs `15` + `17`

- [x] Topology `hr-directory :8001 /hr` + `ticketing-sla :8002 /it` matches `15 §1`; join keys + Q1–Q3 preserved.
- [x] 11 `operation_id`s verbatim from `15 §2–§3` (incl. `sla_breach_list` before `/{ticket_id}`, H5 live-only).
- [x] `--discover` runbook + fallbacks match `15 §4` (pre-build 10 → live add H5 → rescan → Q3 chain `sla_breach_list → get_oncall → reroute_ticket`).
- [x] Effort-plan critical path honored: no Synapse before APIs green; no video before 5/5 live runs; `scorecard.csv` required (`17 §5–§8`). Docker ports **intentionally diverged** from `17 §WK1-D2` (8008/8009/8000 was federation-spike; this doc freezes 8001/8002) — flagged in §2, not a silent drift.
- [x] Server IDs `hr-api` / `it-api` per `04 §2/§6`; Custom safety triple per `05 §(b)`; client restart/cache rules per `06 §3–§4`.

*Next docs: `02-endpoints-build.md` (router code) → `03-synapse-builds.md` (exact CLI transcript) → `04-agent-demo.md` (Q1–Q3 script).*
