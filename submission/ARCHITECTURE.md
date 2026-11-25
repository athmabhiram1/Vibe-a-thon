# ARCHITECTURE — Track 3 Onboard Copilot

## Mermaid (T3: two systems → two MCP servers → one copilot)

```mermaid
flowchart LR
  HR[HR Directory<br/>FastAPI :8001<br/>H1-H5]
  IT[Ticketing SLA<br/>FastAPI :8002<br/>I1-I6 + L1]
  HR -->|synapse build --auto --server-name hr-api<br/>--endpoints allowlist| MCP_HR[MCP server hr-api<br/>part of 13-tool baseline combined]
  IT -->|synapse build --auto --server-name it-api --new<br/>--endpoints allowlist| MCP_IT[MCP server it-api<br/>shares allowlist (13 total combined hr+it)]
  MCP_HR --> AGENT[Onboard Copilot agent<br/>Inspector Web UI<br/>Cite-Before-Act gate]
  MCP_IT --> AGENT
  AGENT -->|CITE preview+hash| HUMAN[Human<br/>APPROVE hash]
  HUMAN -->|CHECK + ACT| AGENT
  AGENT -->|RECORD audit.jsonl| LEDGER[(Audit ledger<br/>hash chain)]
  AGENT --> DB[(SQLite WAL<br/>79 rows seed)]

  subgraph LIVE["Live discover moment"]
    L1[GET /it/oncall-coverage<br/>it_oncall_coverage<br/>added on stage] -.->|synapse build --discover<br/>expanded allowlist, same server ID| MCP_HR
  end
  style L1 stroke-dasharray: 5 5
```

PNG fallback: `assets/arch.png` — rendered 2026-11-24 via matplotlib (`assets/render-pngs.py`; no mermaid-cli on this box, so same boxes/arrows redrawn, not a Mermaid export).

## Data flow (5 lines)

1. Agent reads live HR state (`hr_list_candidates`, `hr_shift_calendar`) + IT state (`it_sla_breach_list`, `it_get_ticket`) — join on `assignee_email ↔ email`, `ticket.created_at ↔ shift_calendar`.
2. Q1 lookup join → Q2 exception anti-join (`it_sla_breach_list` pre-computed anti-join, declared BEFORE `/{id}`) → Q3 only-answerable-after-discover (`hr_get_oncall`).
3. Mutating tools (`hr_create_employee`, `it_assign_laptop`, `it_reroute_ticket`) stage reversible drafts + `preview_hash`; execution requires `confirm + preview_hash`.
4. Business + `SUCCEEDED` + audit committed in one TX; ledger PK `(actor, operation, key)` + fencing `lease_token`; secrets `${ENV:VAR}` redacted at every sink.
5. `synapse build --discover` reuses `surface_cache.json` until rescan; same `SYNAPSE_SERVER_ID` → Inspector Reconnect re-lists (3s, no restart).

## Failure fallback (2 lines)

- Cache → canned JSON (P3 cached-JSON fallback; `emit_tool_plan <60%` or TTFT >20s → serve last-good receipt, exit non-zero with `DENIED <reason>`).
- P0 video → P1 live (localhost + ngrok) → P2 `--local` Ollama → P3 Inspector/curl → P4 narrative flip; kill-network/quota/wrong-model drills pass <90s.

## Tool inventory (14 tools post-discover: 13 baseline + 1 live; 11/12 functional-only)

OpenAPI on disk (verified): HR 9 ops + IT 11 ops = 20. Synapse surface via
`--endpoints` allowlist: 6 `/demo/*` ops always excluded, 2 `/health` ops
excluded for functional-only counts. H5 `hr_get_oncall` is live on disk
(baseline includes it); L1 is the live-add. Full allowlists in
`docs/CLIENTS.md` §7.

| # | Method + Path | operation_id | Why agent-needed |
|---|---|---|---|
| H0 | GET /health | hr_health_check | liveness probe (excluded from functional counts) |
| I0 | GET /health | it_health_check | liveness probe (same exclusion) |

| # | Method + Path | operation_id | Why agent-needed |
|---|---|---|---|
| H1 | GET /hr/candidates | hr_list_candidates | headcount vs breach correlation |
| H2 | GET /hr/candidates/{id} | hr_get_candidate | convert decision detail |
| H3 | POST /hr/employees | hr_create_employee | WRITE: candidate→employee, confirm-gated |
| H4 | GET /hr/shifts | hr_shift_calendar | was assignee on-shift at ticket time? |
| H5 | GET /hr/oncall | hr_get_oncall | baseline (live on disk): who is on-call now → powers Q3 |
| I1 | GET /it/equipment | it_list_equipment | free laptop pool |
| I2 | POST /it/equipment/assign | it_assign_laptop | WRITE: laptop→employee, confirm |
| I3 | POST /it/tickets | it_create_ticket | intake |
| I4 | GET /it/tickets/{id} | it_get_ticket | breach forensics |
| I5 | POST /it/tickets/{id}/reroute | it_reroute_ticket | WRITE: reassign to on-call, confirm |
| I6 | GET /it/tickets/breaches | it_sla_breach_list | pre-computed breach anti-join — declare BEFORE /{id} |
| L1 ⭐ | GET /it/oncall-coverage | it_oncall_coverage | LIVE-ADD (only live-add): on-call person × breaching tickets → owned vs needs_reroute |

Constraints: explicit `operation_id` = MCP tool name; no dynamic routers, no `include_in_schema=False`, no required `Header`, no `File/Form`; `include_router` BEFORE any MCP wrap.
