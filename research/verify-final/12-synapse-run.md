# 12 — Synapse D5 Run (executed 2026-11-24)

**Date:** 2026-11-24 09:36–09:41 UTC | **Runner:** subagent (D5 runbook) | **Scope:** Track 3 live-moment rehearsal
**Verdict:** ✅ **PASS** — 8/8 hosted builds exit 0; 13 baseline / 14 post-discover asserted via Inspector `tools/list`; same server IDs on every rebuild; quota 2/10 servers, 775/100 K lines (frozen after first build).

Key was loaded from `.env` into `$env:SYNAPSE_API_KEY` for the session only. **The key is not recorded anywhere in this repo or report.**

## 1. Runtime + init + quota baseline

| Check | Result |
|---|---|
| `synapse --version` | ✅ `0.1.9` (expect 0.1.9) |
| `node --version` | ✅ `v24.11.0` (≥20 required) |
| `synapse init` | ✅ `Using existing API key from the SYNAPSE_API_KEY environment variable` → `API key verified` |
| `synapse info` BEFORE | servers **0/10**, lines **0/100.0K** (100% remaining) |
| `synapse info` AFTER hr-api | servers **1/10**, lines **775/100.0K** (99.2 K remaining) |
| `synapse info` AFTER it-api + all rehearsals | servers **2/10**, lines **775/100.0K** (99.2 K remaining) — rebuilds cost nothing, even `--discover` added 0 lines |

## 2. Allowlist correction (load-bearing finding)

`docs/CLIENTS.md` §7 lists the allowlist with service prefixes (`GET /hr/candidates`, …). **CLI 0.1.9 detects prefix-stripped paths** (verified in build output: `GET /candidates … hr_list_candidates`, `GET /oncall-coverage … it_oncall_coverage`, …). The prefixed form fails hard:

```text
✖ Endpoints Not Found — No detected endpoint matches: GET /hr/candidates, …
```

Working allowlists actually used (both health endpoints share `GET /health`, so tool names disambiguate):

- **Baseline (13):** `GET /candidates,GET /candidates/{candidate_id},POST /employees,GET /shifts,GET /oncall,GET /equipment,POST /equipment/assign,POST /tickets,GET /tickets/breaches,GET /tickets/{ticket_id},POST /tickets/{ticket_id}/reroute,hr_health_check,it_health_check`
- **Post-discover (14):** baseline + `GET /oncall-coverage`
- `docs/CLIENTS.md` §7 should be patched to the prefix-stripped form before D8.

## 3. Baseline builds (tool counts asserted, not assumed)

Counts below are live `tools/list` results via `inspector --cli --method tools/list` (stdio runner `@2ndbrainlabs-ai/synapse-mcp`), **not** build-output inference.

| Build | Session | server_id | Tools (asserted) |
|---|---|---|---|
| `synapse build --auto --endpoints "<13>" --server-name hr-api` | `sess_da78b1a6_mwui39br_c571c0` | `6269969f-3f80-4a9f-a6e1-43237197dc42` | **13** ✅ (`hr_list_candidates, hr_get_candidate, hr_create_employee, hr_shift_calendar, hr_get_oncall, it_list_equipment, it_assign_laptop, it_create_ticket, it_sla_breach_list, it_get_ticket, it_reroute_ticket, hr_health_check, it_health_check`) |
| `synapse build --auto --endpoints "<13>" --server-name it-api --new` (~8.4 s) | `sess_da78b1a6_mwui3xgf_ac0eaf` | `5fe96a56-ccb4-4483-a7e2-5a9cd2588b15` | **13** ✅ (identical tool set) |

## 4. Live rehearsal ×3 (hr-api; it-api untouched, final re-check 13)

Choreography per round: move `it_service/routers/live_moment.py` to `%TEMP%` → timed baseline build (scan drops 20→19 endpoints) → Inspector assert 13 → restore file (byte-identical, `ast.parse` clean) → timed `--discover` build with 14-allowlist → Inspector assert 14 + `it_oncall_coverage` present. **Every rebuild printed `same server id`.**

| Round | Baseline (13) | Discover (14, +L1) | Server ID stable | L1 live |
|---|---|---|---|---|
| R1 | **2.36 s** (`sess_…mwui6qfw_3bb154`, `0 added, 0 updated, 0 removed, 13 unchanged`) | **4.78 s** (`sess_…mwui73lj_568d41`, `1 added, 6 updated, 0 removed, 7 unchanged`) | ✅ `6269969f-…` both builds | ✅ |
| R2 | **4.75 s** (`sess_…mwui7k8j_c70a90`, `1 removed` = L1 out) | **4.72 s** (`sess_…mwui802u_d915e1`, `1 added` = L1 back) | ✅ `6269969f-…` both builds | ✅ |
| R3 | **4.83 s** (`sess_…mwui8gj6_cd7253`) | **4.82 s** (`sess_…mwui8uaq_cf4a1f`) | ✅ `6269969f-…` both builds | ✅ |

Discover medians: baseline-rebuild ≈ 4.8 s, discover ≈ 4.8 s — far inside the T3 90 s tripwire. it-api final `tools/list`: **13** (ID `5fe96a56-…` untouched).

## 5. Tooling bugs found (do not block D5, fix before D8)

1. **`synapse logs <sessionId>` crashes** — `TypeError: Cannot read properties of undefined (reading 'length')` at `fmtCounts (logs-TXYAWOMP.js)`. All 8 sessions affected; quoted session IDs above for the upstream report.
2. **Inspector CLI sanitizes stdio env** — `$env:SYNAPSE_*` set in PowerShell did NOT reach the runner (`…environment variables are required`). Workaround used: temp `--config` JSON (written by script reading `.env`, **deleted after**). Never pass the key via `-e KEY=VALUE` (lands in process args/history).
3. **`synapse info` shows `API key (not set) (project)`** even after verified `init` from env var — cosmetic only; hosted builds authenticate via `SYNAPSE_API_KEY` env.

## 6. State + follow-ups

- `.synapse/surface_cache.json` created (no secrets inside — repo hash + file list only). Leave on disk; decide commit vs gitignore on D6.
- `it_service/routers/live_moment.py` restored; `%TEMP%` config (held key) + helper script both deleted.
- Quota rows appended to `evidence/quota-log.md` (8 hosted builds, before/after from real `synapse info`).
- Remaining D5→D8: patch `docs/CLIENTS.md` §7 to prefix-stripped paths; re-run this file's §3–§4 commands to re-verify (expect same IDs, 13/14).
