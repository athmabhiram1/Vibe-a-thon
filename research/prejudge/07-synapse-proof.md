# 07 — Synapse Centrality Proof (repo-alone audit, 2026-11-25)

Scope: is Synapse centrality PROVABLE from the repo alone, read-only. Today = 2026-11-25 UTC.

## 1. What the repo does prove (file:line)

- `.synapse/config.json:1-21` — hosted mode, initialised 2026-11-24, two servers: `hr-api → 6269969f-…` (updated 09:41), `it-api → 5fe96a56-…`. Matches IDs quoted in `research/verify-final/12-synapse-run.md:39-40` and `28-discover.md:19`.
- `.synapse/surface_cache.json:178` — `lines_scanned 775`, `repo_hash db7e…`; `statistics.prev.json:1` — 775/775. Matches every quota-log AFTER cell (775/100K) and `LIMITS.md:7`.
- `.synapse/discover/` — 9 × `sess_*.jsonl` (2026-11-24 15:06–15:11 local = 09:36–09:41 UTC window). 8 map to the 8 hosted builds in `12-synapse-run.md:37-50` (39br, 3xgf, 6qfw, 73lj, 7k8j, 802u, 8gj6, 8uaq); 9th (330l) is an extra session open with no documented build. Session records carry endpoint scans incl. `it_oncall_coverage` (`sess_…802u…:4`) and full H1–H5 lists — scan half of the story is on disk.
- `evidence/quota-log.md:20-25` — fresh: last row 2026-11-25 14:48 (read-only no-build check, 0 burned). Rows 11-24→11-25 show 0→1→2/10 servers, 775 lines frozen after first build, tools 13/13, 13→14 ×3. Numbers match `config.json`, `synapse-info.txt:21-23`, `LIMITS.md:7`.
- `submission/assets/quota-proof/synapse-info.txt:1-29` — redacted `synapse info` text capture 2/10 + 775/100K; `README.md:5` honestly admits no `.png` was ever taken. `ollama-ps.txt/.png` present; `ngrok.png`, `ai-dashboard.png`, `fly.png` explicitly pending/user-owned.
- `safety_check_server.py:1-938` — present, single `@mcp.tool(name="onboard")` (`:582-590`) composing 8 private helpers in documented order, stage→activate, ledger PK, hash chain, Class-B/C gates. Matches Custom shape (Python-only single-tool file). Filename deviates from guide convention (`<tool>_server.py` → `onboard_server.py` expected).
- `operation_id == tool name` — code-proven by inspection: `hr_service/routers/hr.py:116,133,150,171,189,211,251,280` (H1–H5 + 3 demo), `it_service/routers/it.py:118,134,152,174,190,205,220,260,289` (I1–I6 + 3 demo), `live_moment.py:61` (L1), mains (`hr_service/main.py:20`, `it_service/main.py:20`). The 13 names in `12-synapse-run.md:39-40` and 14 in `28-discover.md:22-36` match these strings verbatim (health disambiguation documented in `CLIENTS.md:140-141`).
- Runbook commands exact — but only in `docs/CLIENTS.md:25-28` (§1 + §7 allowlists, prefix-stripped) and cue card `demo/SHOTLIST.md:48`. `plan.md:108-115` §4 instead prints `--all-endpoints`, which was never executed and would ingest 20 ops. `guide.txt:91-115,157-164` carries the canonical `init/build/--discover/--server-name/--new/info` grammar the repo relies on.

## 2. Claim-by-claim backing

| Claim | Backing in repo | Strength |
|---|---|---|
| 13 baseline / 14 post-discover (11/12 functional) | `12-synapse-run.md` §3–§4 tables, `quota-log.md` rows, `28-discover.md` §2 list of 14 | Markdown testimony only — no raw transcript (see gaps) |
| Same server ID on rebuild | `config.json` IDs + `12-…` §4 "same server id" ×6 | Asserted, no raw build stdout |
| `--discover` ~5s (median ~4.8s) | `12-…` §4 timings 2.36/4.75/4.83 vs 4.78/4.72/4.82 | Markdown only; `28-…` §3 measured nothing new |
| Quota 2/10, 775 lines, ₹0 | `quota-log.md` + `synapse-info.txt` + `LIMITS.md:7` | Strongest leg (3-way match) |
| Live-add is L1, H5 already live | `28-…` §3 + `hr.py:186-206` uncommented + `surface_cache.json` containing L1 | Strong (disk + cache agree) |

## 3. Gaps — centrality claims with NO repo-alone proof

1. **No raw `synapse build` stdout** (the "same server id / 1 added / 0 removed / N unchanged" lines): only retyped into `12-…` tables. `discover/*.jsonl` records contain no `server_id` field; `synapse logs` crashes per `12-…` §5.1, so server-side history is unverifiable offline.
2. **No raw Inspector `tools/list` JSON**: 13/14 counts are markdown tables (`12-…` §3, `28-…` §2). No committed `--cli tools/list` output file.
3. **No screenshots**: quota-proof admits text-only (`quota-proof/README.md:5`); `ngrok/ai-dashboard/fly` pending; `demo/golden.mp4` is `[UPLOAD PENDING]` — SHOTLIST/PITCH tail claims (13→14, same ID, ~5s, ₹0) point at a video that does not exist in the repo.
4. **Session proof is gitignored**: `.gitignore:22` ignores `.synapse/discover/` — a fresh clone loses all 9 session files; only `config.json`/`surface_cache.json`/`statistics.prev.json` survive (committed in `2973b0f`).
5. **`surface_cache.json` contradicts the 14-tool claim on its face**: it holds 10 endpoints (2 health + H1–H5 + 3 HR demo + L1) and zero I1–I6 rows — it reflects the last hr-api scan, not the combined surface. The 14-tool surface exists only on hosted infra + markdown.
6. **`synapse_auto_server.py` does not exist** (glob: zero hits): every stdio reference — `.cursor/mcp.json:5`, `.vscode/mcp.json:6`, `CLIENTS.md:14,38,42,122`, `docs/VENUE.md:83` — points at a missing file. `--local` fallback is unproven (no file, no local-build log); `01-oracle-kill.md:32` already flagged this.
7. **Custom provenance unlogged**: `safety_check_server.py` could be hand-written; no `synapse build --custom` session, log, or snippet in the repo proves Synapse generated it, and the filename breaks the `<tool_name>_server.py` convention (`guide.txt:143-152`).
8. **Timings are single-source**: `12-…` §4 medians have no timestamped logs; jsonl `elapsed_ms` (~65ms) covers scan only. `28-…` explicitly ran zero builds, so "~5s" has exactly one rehearsal-day source.
9. **Judge cannot re-verify hosted state from the repo**: key lives in gitignored `.env`; `synapse info` needs key + network + quota. Offline, IDs and counts are trust-me markdown atop two small committed JSON files.
10. **No committed `openapi.json` snapshot**: operationId==tool-name proof needs running APIs (`:8001/:8002`) or code reading; G2/G6 gates cite a live `/openapi.json` that is not vendored.
11. **Runbook inconsistency**: `plan.md` §4 (`--all-endpoints`) vs executed allowlists (`CLIENTS.md` §7) — a judge following `plan.md` alone gets 20 tools, not 13/14, and breaks G2/G6.
12. **Quota-log row 2026-11-25 is `M evidence/quota-log.md` (uncommitted)** — freshness exists on disk but is not yet committed.

## Verdict

Synapse centrality is **substantially documented but not self-proving**: quota/IDs/shapes/allowlist logic triangulate across `config.json` + `surface_cache.json` + `quota-log.md` + `12-/28-…md`, and the L1-vs-H5 correction in `28-…` §3 is honest. But the three load-bearing demo claims — **13→14 tools, same server ID, ~5s discover** — rest on markdown tables with **no raw build transcript, no tools/list JSON, no screenshot, no video**, and the session files backing them are **gitignored**. Close the gap with: (a) commit raw `synapse build` + `inspector --cli tools/list` outputs, (b) un-ignore or vendor one session log, (c) fix `plan.md` §4 to the executed allowlist, (d) generate or remove `synapse_auto_server.py` references.
