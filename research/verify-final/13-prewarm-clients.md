# 13 — Prewarm + MCP Clients Verification (e2e)

**Date (UTC):** 2026-11-24 ~09:35–09:40 · **Workdir:** `VIBE_CODE` · **Verifier:** subagent (lane 13)
**Scope:** `scripts/prewarm.sh`, `docs/CLIENTS.md` vs code reality, `.cursor/mcp.json` parse,
Inspector CLI `tools/list`, cold-start timing for T1 tripwire. Routers/seed/eval untouched (read-only probes).

## Verdict

**PASS with 1 doc fix + 2 venue warnings.** `prewarm.sh` counts (13/14) and L1 endpoint agree
with disk code. `docs/CLIENTS.md` had one stale number (fixed). Fresh-code boot verified end to end.
Synapse-server Inspector `tools/list` is **blocked-on-D5** (no local server artifact; hosted builds
owned by parallel lane). Safety-server Inspector `tools/list` **PASSES**.

## 1. What was executed (all real, no invention)

| # | Check | Result |
|---|---|---|
| 1 | `.cursor/mcp.json` parses, top-level `mcpServers` | **PASS** — servers `hr-api`, `safety-custom` |
| 2 | `.vscode/mcp.json` parses, top-level `servers` | **PASS** — same two servers |
| 3 | `claude_desktop_config.example.json` parses, `mcpServers` | **PASS** — same two servers |
| 4 | Cold import `hr_service.main` + `it_service.main` | **0.80s** |
| 5 | Cold boot HR :8101 + IT :8102 (temp ports, own procs, terminated after) | **HR 1.05s, IT 1.09s** to `/health` 200 |
| 6 | Fresh HR openapi | **9 ops** incl `hr_get_oncall` (H5 live on disk) |
| 7 | Fresh IT openapi | **11 ops** incl `it_oncall_coverage` (L1 live on disk) |
| 8 | `GET /it/oncall-coverage?team=support-night` (fresh code) | **200** — on-call Kiran Desai EMP-014, ~0.045s |
| 9 | `GET /it/oncall-coverage?team=no-such-team` (fresh code) | **404** (router-level, mirrors H5 — CLIENTS.md claim holds) |
| 10 | Prewarm-equivalent probes (fresh code) | candidates 200 ~0.035s, breaches 200 ~0.018s, `/docs`+`/openapi.json` 200 both services |
| 11 | Inspector CLI `--version` | **2.13.0** (npx, works) |
| 12 | Inspector CLI `tools/list` vs `safety_check_server.py` | **PASS** — exactly 1 tool: `onboard` (+ full inputSchema verified) |
| 13 | Inspector CLI `tools/list` vs Synapse server | **BLOCKED-on-D5** — no `synapse_auto_server.py`, no local stdio artifact (§4) |

## 2. Count reconciliation (13/14 — NOT stale, confirmed)

Fresh-code openapi totals: HR 9 + IT 11 = **20 ops** = 6×`/demo/*` + 2×health + 12 functional
(H1–H5 + I1–I6 + L1). Both allowlists in `docs/CLIENTS.md` §7 check out:

- Baseline (excl. L1): 11 functional + 2 health = **13 tools** ✓
- Post-discover (+L1): 12 functional + 2 health = **14 tools** ✓
- Functional-only: 11 → 12 ✓

`scripts/prewarm.sh:27` ("Expect 13 tools baseline, 14 post-discover") and `docs/CLIENTS.md`
§7 + §1-header agree with code. **No change needed.**

## 3. Doc fix applied

- `docs/CLIENTS.md:17`: `# 2. Baseline: Tools → List (expect 10)` → **`(expect 13)`**.
  The "10" was stale (pre-H5/pre-health surface); baseline build yields 13 tools.
  Only occurrence of the stale number; rest of file already says 13/14.

## 4. Synapse status (read-only; D5 lane owns mutations)

- `synapse --version` → **0.1.9** (the BLOCKED verdict in `05-synapse.md` §1 no longer holds for CLI).
- `synapse info`: project Initialized, mode **hosted**, quota **2/10 MCP servers, 775/100K lines**.
  `config.json` shows hosted `hr-api` + `it-api` built 09:36–09:37 UTC today.
- `.synapse/surface_cache.json` mentions `oncall-coverage` (analyzed). Cache rewritten
  15:06–15:07 local — **a parallel lane is actively building right now; no builds run from this lane.**
- No local `synapse_auto_server.py` (expected: hosted mode keeps servers in cloud).
  Inspector access = HTTP transport to hosted URL, whose exact runbook is D5's — hence blocked-on-D5.
- `SYNAPSE_API_KEY` **not** in env (key lives in project config; `synapse info` works regardless).

## 5. Venue warnings (T1 tripwire evidence)

1. **STALE RUNNING SERVERS.** The :8001/:8002 processes answering now predate L1:
   live IT openapi shows 10 ops, `GET /it/oncall-coverage` → FastAPI-level `{"detail":"Not Found"}`
   (route absent, NOT the router's `no on-call roster` 404). **Venue must kill + reboot both
   services from current disk code before the demo, then re-run prewarm** — prewarm alone cannot
   add the route. Fresh boot on :8101/:8102 proves disk code serves L1 correctly.
2. **`prewarm.sh` is bash; venue is Windows.** `where bash` finds nothing, so the script runs
   only under git-bash/WSL. All probes were replicated via `curl.exe`/Python with identical
   assertions (§1 rows 5–10). Consider a `prewarm.ps1`/`.bat` twin before venue day (not done here —
   out of this lane's edit scope).

## 6. Cold-start timing (T1 evidence)

| Stage | Time |
|---|---|
| `import hr_service.main + it_service.main` | 0.80s |
| Spawn → HR `/health` 200 | **1.05s** |
| Spawn → IT `/health` 200 | **1.09s** |
| Warm `GET /hr/candidates?limit=1` | ~0.010s (stale srv) / 0.035s (fresh) |
| Warm `GET /it/tickets/breaches` | ~0.013s / 0.018s |
| Warm `GET /it/oncall-coverage?team=support-night` | 0.045s (fresh; 404 on stale) |

Tripwire reading: full cold boot of both services ≈ **~1.1s**; any T-10min prewarm probe taking
>5s or non-200 on candidates/breaches/openapi/docs signals a dead/stale service, not a slow one.

## 7. Re-verify routing (post-D5)

1. D5 finishes hosted builds → confirm `synapse_auto_server.py` exists (local) or publish the
   hosted HTTP URL + auth for Inspector.
2. Inspector CLI `tools/list` → expect 13, then post-discover → 14 with `it_oncall_coverage`.
3. Reboot :8001/:8002 from disk, re-run §1 rows 5–10, close warning #1.
4. Refresh `research/verify-final/05-synapse.md` (CLI now installed, hosted servers exist).
