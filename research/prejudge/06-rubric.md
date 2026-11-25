# Prejudge Rubric — Track 3 Onboard Copilot (repo-only, hostile, no video)

> Scope: local `VIBE_CODE` + claimed `https://github.com/athmabhiram1/Vibe-a-thon` (unpublished). No video watched. `demo/golden.mp4` absent. All `[UPLOAD PENDING]` / `[VENUE-UNMEASURED]` treated as missing.

| # | Dimension | Score /10 | One-line evidence (file/URL) | What would +1 |
|---|---|---|---|---|
| 1 | Task usefulness | 7 | `README.md:3` — Day-1 readiness blocked by join-dependent steps; staged drafts + `APPROVE <hash>` is a real toil-killer | Prove toil saved vs manual HR+IT clicks: 1 timed before/after run in `BENCHMARKS.md` |
| 2 | Endpoint choice + why | 8 | `submission/ARCHITECTURE.md:47-65` + `it_service/routers/live_moment.py:59-62` — 13→14 tools, explicit `operation_id`=tool name, breach anti-join + live `it_oncall_coverage` | Fix count confusion (13 vs 11-functional vs 20 OpenAPI) with one `tools/list` transcript in `docs/CLIENTS.md §7` |
| 3 | Reliability (Track 1 lens) + cross-system answers | 6 | `eval/scorecard.csv:2-41` + `BENCHMARKS.md:21` — 39/40 guarded but latency is `MOCK 11.0ms simulated, NOT measured`, baseline weak-by-design | Replace MOCK with 40 real server-timed runs + publish `live_scorecard.csv` pass rate; M05 WARN→explicit BLOCK/ALLOW |
| 4 | Real use case | 7 | `seed/candidates.csv` + `seed/tickets.csv` — CAND-002 Priya Monday start, LT-1005 double-hold, 3 breached T-5001/T-5002/T-5019 | One anonymized real onboarding ticket trace (redacted) mapped to same joins |
| 5 | Clean update (Track 3 lens) + originality | 7 | `.synapse/surface_cache.json:29-46` + `evidence/quota-log.md:22-24` — L1 added live, 13→14 same ID ×3 rehearsals ~4.8s | Single `synapse build --discover` diff log showing only `+it_oncall_coverage`, no client re-config, Inspector re-list screenshot |
| 6 | Synapse centrality | 8 | `plan.md:106-117` + `LIMITS.md:7` — 2/10 servers, 775/100K lines, Auto+discover is the only ingestion path | Remove `--local`/cached-JSON fallback as equal path; show agent failing without Synapse MCP (ablation) |
| 7 | Execution | 5 | `README.md:10-21` claims 5-cmd `<60s` but `origin→pcb_designing.git — DO NOT push`, `<PASTE-REPO-URL>`, `frontend.html` missing at root (only `submission/deck/pitch.html` found), `compose.opt.yml` N/A no-Docker | Publish repo URL, fix `run.bat`+`frontend.html` at root, green CI log for `seed/validate.py→0 failure(s)` |
| 8 | Demo (Open lens) | 3 | `demo/` contains only `SHOTLIST.md`; `submission/PITCH.md:7-14` 75s script + `submission/captions/demo.srt` exist but `demo/golden.mp4` absent, `submission/README.md:14` `[UPLOAD PENDING]` | Upload unlisted ≤90s `golden.mp4` + QR link; hostile judge cannot score storyboards |

## Verdict (hostile)
Strong API/Synapse engineering (explicit IDs, allowlists, quota logs, 79-row trap seed) undermined by publish gaps: no repo URL, no video artifact, MOCK latency, 6+ `[VENUE-UNMEASURED]`. As judged from repo alone this is a **well-documented prototype, not yet a runnable submission**. Fix publish + measured eval + 1 real trace and it contends for Track 3 podium; today it reads 48/80 with demo as the cap.

## Biggest risks
1. `submission/README.md:15` — Live links are `localhost:8001/docs` only; no public URL for judges.
2. `BENCHMARKS.md:17,20` — TTFT + discover median unmeasured; live moment timing is asserted, not benched.
3. `eval/run.py` — guarded logic is policy-simulation, not server-enforced (bypassable via direct POST without `preview_hash` — confirm in `hr_service/routers/hr.py:150-166`).
