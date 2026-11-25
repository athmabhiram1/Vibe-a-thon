# 17 — RE-SIGNOFF (critic, read-only, 2026-11-24)

**Scope read:** `01-oracle-kill.md` (5 kills) + `16-signoff.md` (old NO-GO) + new evidence
`12-synapse-run.md`, `13-prewarm-clients.md`, `14-safety-retest.md`, `15-hygiene-reaudit.md`,
`eval/live_scorecard.csv` (5 LIVE cases, measured latency), `frontend.html` (42,746 B, wired),
`submission/` packet (`BENCHMARKS.md` measured, `LIMITS.md`, `deck/pitch.pdf` 8 pp, valid `%PDF-1.4`),
`demo/SHOTLIST.md` (runbook only), `.synapse/config.json`, `evidence/quota-log.md` (5 real rows).
No cheerleading.

## Oracle 5 kills — re-adjudicated against new evidence

| # | Kill | Status | Proof |
|---|---|---|---|
| K1 | 96.8% rigged mock | **PARTIAL** | Honesty fixed, substance half-fixed. `eval/run.py:93-94` still `+ 11.0  # MOCK: simulated policy cost`, scoring read at `:127` is legitimate (scoring, not policy). New: `eval/live_run.py` drives the REAL `safety_check_server.onboard` over HTTP + `live_scorecard.csv` 5/5 PASS with MEASURED latencies (135.3 / 9.8 / 7.9 / 18.3 / 166.1 ms). But the 40-case headline eval is still regex-over-JSON, never calls `onboard`. Judge grep-kit is blunted (MOCK labels everywhere, live supplement exists); "eval tests shipped code" is still only 5 cases deep. |
| K2 | Zero Synapse artifacts | **CLOSED** | `.synapse/config.json`: `hr-api 6269969f-3f80-4a9f-a6e1-43237197dc42` (built 09:36, updated 09:41), `it-api 5fe96a56-ccb4-4483-a7e2-5a9cd2588b15`; `quota-log.md` 5 real rows (0→1→2 servers, 775/100K lines, 99.2K left); `surface_cache.json` on disk; 13/13 baseline asserted via Inspector `tools/list`, discover 13→14 ×3 rounds, same server ID every rebuild, medians ~4.8 s (12 §4). Residual (fix F3): zero PNGs in `assets/quota-proof/` — screenshots still owed. |
| K3 | `/demo/*` missing | **CLOSED (code)** | 14 §1–§3: `/hr|/it/demo/seed\|reset\|status` live, seed v14 `20/20/20/20/8/6/5`, `validate.py` 0 failures, status 200 in ~7 ms. Caveats → F4: venue `:8001/:8002` processes predate L1 (13 §5.1: route absent at FastAPI level on stale procs — must kill + reboot from disk); concurrent lane reseeded DB mid-run (14 §Env hazard — serialize seed/reset). Single shared `seed/demo.db` explicit/intentional. |
| K4 | Discover 404 moment | **CLOSED (substance) / PARTIAL (script)** | Substance done: H5 + L1 live on disk, fresh-boot L1 → 200 with EMP-014 (13 §1 row 8), 404 only for unknown team (router-level, as choreographed); discover rehearsed ×3, `it_oncall_coverage` present, same-ID (12 §4). Script stale → F2: `SHOTLIST.md` still stages the OLD flow (H5 commented out, `build --auto` FAIL-first, `10→11`, `srv_xxxx`) while code ships L1 always-on and counts are 13→14; cue-card block would fail verbatim today. |
| K5 | Two write paths, safety theater | **CLOSED** | 14 verdict PASS 17/18: `confirm=True` mints real `EMP-021` (HR 20→21), real IT assign (`MN-2002` available→assigned), real reroute to on-call, ledger `SUCCEEDED`, `verify_audit_chain ok:true` dense, replay `already_applied` no-2nd-write, injection + BG-fail denied, Q3 chain 4/4. The 1 miss was driver-shape error (`assignee_email` vs `assignee_id`, `serial` vs `asset_tag`), not product. Residual nits → F5: zero `available` laptop-category assets (monitor-as-stand-in used), audit file-lock still single-worker-assumed. |

## Demo-critic (16 §Demo-critic) — re-adjudicated

| # | Item | Status |
|---|---|---|
| K1 | `demo/golden.mp4` missing | **OPEN** — `demo/` = `SHOTLIST.md` only; zero `*.mp4` repo-wide; `submission/README.md:13` still `[UPLOAD PENDING …]`. P0 rung absent; runbook + `captions/demo.srt` ready. |
| K2 | Packet TODO shell | **PARTIAL** — `BENCHMARKS.md` now measured: cold start 1.3 s ×3, p50 10.6 / p95 11.6 ms (3×20 curl), bundle 3.3 KB, local TTFT 0.24 s (wrong model `qwen3:8b`, disclosed), safety row disclosed MOCK; `deck/pitch.pdf` exists (10,897 B, `%PDF-1.4`, 8 pages). Still open: seed/reset/TTFT-hosted/AI-cache/discover-median/Lighthouse `[UNMEASURED]`, no `benchmark/run.js`, `LIMITS.md:7,10` `[AWAITING …]` + all quota-proof screenshots pending, `DATABASE_URL` stale refs (`LIMITS.md:19`, `plan.md:21`). |
| K3 | `frontend.html` missing | **CLOSED (file + wired)** — exists (42.7 KB), `fetch()` against real `/hr/*` + `/it/*` incl. breaches literal-string (route-order trap noted in-file), approve POSTs `/hr/employees` + `/it/equipment/assign`, reroute + on-call chain wired. Owed: one live click-through at record time (not yet evidenced). |
| K4 | Zero Synapse builds rehearsed | **CLOSED** — see K2 above (T3/T8 evaluable: quota 2/10, 99.2K lines left). |
| K5 | Script ID drift | **PARTIAL** — `PITCH.md` + `deck/pitch.html`/`build_pdf.py` canonical (`CAND-002`, `INV-HOLD LT-1005`); **`SHOTLIST.md` still drifts** (`CAND-1147`, `LT-4420`, `R-0091/R-0092`, `tools 10→11`). 15-min grep fix, still undone. |
| K6 | Physical layer | **OPEN** (unverifiable from repo; assume absent — USB ×2, hotspot, second device playback all owed at record time). |
| K7 | Minor tripwires | **PARTIAL** — placeholders renamed but present (`UPLOAD PENDING`, `<PASTE-REPO-URL-HERE>`, `origin` → unrelated `pcb_designing.git` noted); `submission/README.md:46` "5 cmds" vs `run.bat` "3 cmds" persists (both now point at real `requirements.txt`); breach-count drift PINNED (14 §3: post-reset breaches exactly `[T-5001, T-5002, T-5019]`, matches `validate.py`); `96.8%` residuals in `outline.md:10`/`plan.md:8` per 15 (README badge correct at 97.5%). |

## Verdict: GO-WITH-FIXES

16's NO-GO rested on "nothing a judge sees exists." That is no longer true: 2 hosted servers with
pasteable IDs, same-ID discover ×3, wired safety (real EMP/ledger/audit), wired 42 KB frontend,
measured benchmarks, valid 8-page deck, honest MOCK labels + 5 live measured cases. What remains is
a 1-day close-out, not a rebuild: the P0 video, screenshots/placeholders, one ID/choreography sweep,
one venue reboot, one data nit. Ship the fixes, then ship the demo.

## Fix list (≤5, in order)

1. **Record P0 (90 min):** per `SHOTLIST.md` after F2; `demo/golden.mp4` + USB ×2 + unlisted YouTube +
   captions upload; replace `README.md:13` pending link. Unblocks demo-critic K1/K6.
2. **Canonical-ID + choreography sweep (30 min):** `SHOTLIST.md` `CAND-1147/LT-4420/R-009x/10→11` →
   `CAND-002/LT-1005/EMP-NNN/13→14`, rewrite tail cue-card for always-on L1 (drop FAIL-first H5 flow);
   patch `docs/CLIENTS.md:25,27` to prefix-stripped allowlist (12 §2: prefixed form hard-fails on CLI
   0.1.9 — venue copy-paste breaks otherwise); reconcile 5-vs-3-cmd claims; replace
   `UPLOAD PENDING` / `<PASTE-REPO-URL-HERE>`; fix `outline.md:10`/`plan.md:21` residuals. Unblocks K4-script/K5/K7.
3. **Packet screenshots + UNMEASURED fill (45 min):** `synapse info` before/after PNG, `ollama ps`,
   ngrok + AI-dashboard at freeze into `assets/quota-proof/` (must show ₹0/$0); measure seed/reset
   with `ALLOW_DEMO_SEED=true`, discover median ×5 into `BENCHMARKS.md:20`; update `LIMITS.md`
   AWAITING rows to match `quota-log.md`. Unblocks K2-packet.
4. **Venue reboot + prewarm (15 min, venue day):** kill stale `:8001/:8002`, boot from disk, assert
   `GET /it/oncall-coverage?team=support-night` 200 + prewarm rows (13 §1.5–10); serialize seed/reset
   across operators (14 hazard); add `prewarm.ps1`/`.bat` twin (bash absent on venue Windows).
5. **Safety data nit + key hygiene (20 min):** seed one `available` laptop-category asset (retire
   monitor stand-in); document single-worker audit-lock constraint; **rotate `SYNAPSE_API_KEY`** if
   `.env` was ever staged/pushed — never publish `.env` (ignored but live on disk).

## Single next command

```bash
grep -rn "CAND-1147\|LT-4420\|R-009\|10→11\|TODO\|UPLOAD PENDING\|PASTE-REPO-URL" demo/SHOTLIST.md submission/README.md submission/deck/outline.md docs/CLIENTS.md plan.md
```

(Expect hits = F2 work list; zero hits = F2 done, proceed to F1 record.)
