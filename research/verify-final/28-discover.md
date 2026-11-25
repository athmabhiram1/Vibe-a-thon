# 28 — Discover Rehearsal (executed 2026-11-25)

**Date:** 2026-11-25 ~14:40–14:48 UTC | **Runner:** subagent (discover-rehearsal task)
**Scope:** ONE careful `--discover` rehearsal on `hr-api`: quota before/after, Inspector `tools/list`, conditional H5 uncomment → discover → re-comment cycle.
**Verdict:** ⚠️ **NO BUILD EXECUTED — precondition unmet.** `hr-api` is already at **14 tools with H5 live**, not the expected 13 baseline. Per the task guard ("ONLY if baseline is 13"), the uncomment/discover/re-comment cycle was skipped. Zero quota burned. Server and disk untouched.

## 1. Quota (before/after)

| Check | Result |
|---|---|
| `synapse --version` | ✅ `0.1.9` |
| `node --version` | ✅ `v24.11.0` |
| `synapse info` BEFORE (~14:40 UTC) | servers **2/10**, lines **775/100.0K** (99.2K remaining) |
| `synapse info` AFTER (14:48 UTC) | servers **2/10**, lines **775/100.0K** (99.2K remaining) — **identical, 0 burned** |
| Quota-log | Row appended to `evidence/quota-log.md` (reason: `28-discover rehearsal check (NO BUILD)`) |

## 2. Inspector `tools/list` on `hr-api` — 14, H5 already live

Method (no key on disk or in history): temp `--config` JSON (npx stdio runner `@2ndbrainlabs-ai/synapse-mcp` + `SYNAPSE_API_KEY` from `.env`, `SYNAPSE_SERVER_ID=6269969f-3f80-4a9f-a6e1-43237197dc42`, `SYNAPSE_API_URL=https://api.synapse.2ndbrainlabs.ai`), `npx -y @modelcontextprotocol/inspector --cli --config <tmp> --server hr-api --method tools/list` (exit 0), temp config deleted after. Key never printed.

| # | Tool | Notes |
|---|---|---|
| 1 | `it_health_check` | health |
| 2 | `it_list_equipment` | I1 |
| 3 | `it_assign_laptop` | I2 |
| 4 | `it_create_ticket` | I3 |
| 5 | `it_sla_breach_list` | I4 |
| 6 | `it_get_ticket` | I5 |
| 7 | `it_reroute_ticket` | I6 |
| 8 | `it_oncall_coverage` | **L1 live-add — already live** |
| 9 | `hr_health_check` | health |
| 10 | `hr_list_candidates` | H1 |
| 11 | `hr_get_candidate` | H2 |
| 12 | `hr_create_employee` | H3 |
| 13 | `hr_shift_calendar` | H4 |
| 14 | `hr_get_oncall` | **H5 — already live** |

Composition: **14 = 12 functional (H1–H5 + I1–I6 + L1) + 2 health.** All 6 `/demo/*` ops excluded (Header-param detection rule holds). `it-api` untouched (ID `5fe96a56-…`).

## 3. Why no build ran (load-bearing finding)

The task assumed baseline **13 without H5** → uncomment H5 → discover → **14**. Reality differs twice:

1. **H5 is committed uncommented at HEAD** (`hr_service/routers/hr.py:186-206`, "uncommented for the discover build"; `git status` clean on that file) — there was nothing to uncomment.
2. **The live server is post-discover (14), not baseline (13)** — it contains H5 *and* L1. The documented baseline-13 (`research/verify-final/12-synapse-run.md` §3–§4, `docs/CLIENTS.md` §7) is H1–H5 + I1–I6 + health with **L1 excluded**, i.e. the live-add was always L1, never H5.

So the guard "ONLY if baseline is 13" evaluated **false** → zero `synapse build` invocations (the 2-try rule never triggered; nothing failed, the precondition simply didn't hold). **No timings were measured** — nothing was timed. Prior medians (~4.8 s per build, `12-synapse-run.md` §4) remain the reference; do not present them as new measurements.

Deliberately avoided: running `--discover --auto --all-endpoints` against the live server just to get a timing. That flag is **unverified on this repo** (all prior runs used explicit allowlists) and could ingest `/demo/*` → ~19–20 tools, corrupting the recording setup. Risk rejected for zero gain.

## 4. End state + follow-ups

- **Disk:** H5 still uncommented (unchanged from HEAD — nothing of mine to revert; `git status` shows no diff from this session). Server still 14. The "never leave H5 uncommented" clause applied to the skipped branch; commenting H5 now *without* rebuilding would desync disk from server, and rebuilding to 13-without-H5 would produce the **wrong** 13 (H1–H4+I1–I6+L1+health) vs the recording's baseline (H1–H5+I1–I6+health, L1 out).
- **Recording re-plan options:** (a) reset via the proven L1 choreography — move `it_service/routers/live_moment.py` out → rebuild with the 13-allowlist → 13 baseline for recording (`12-synapse-run.md` §4); or (b) redefine the live moment as H5 (requires commenting H5 + discover-rebuild + re-verify, and doc updates to `docs/CLIENTS.md` §7).
- **Fallback stands:** per task, the rehearsal video stands in — no live discover was rehearsed this session.
- Temp Inspector config deleted; key never written to repo, shell history, or this report. Helper scripts live in `%TEMP%\opencode\` (outside repo); repo tree has no new artifacts from this session besides this file + quota-log row.
