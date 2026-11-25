# 24 — SIGNOFF v3 (critic, read-only, 2026-11-24)

**Scope read:** `17-resignoff.md` (GO-WITH-FIXES) + files 18–23 + `frontend.html` + submission state.
Files 18–23: **absent** (verify-final ends at 17; no new evidence since 17 except the two
deltas below). No cheerleading.

**Deltas since 17 (verified this pass):**
- D1 — `demo/SHOTLIST.md` FIXED to canonical choreography (9,730 B, 2026-11-24 15:17):
  CAND-002 / LT-1005 / EMP-021 / 13→14, cue-card "no FAIL-first, no uncomment", L1 always-on.
  Zero hits for `CAND-1147|LT-4420|10→11` inside SHOTLIST. 17's F2 is done *for SHOTLIST*.
- D2 — `submission/BENCHMARKS.md` seed/reset now MEASURED (edited 21:59):
  seed 34.1 ms median, reset 14.4 ms median (`ALLOW_DEMO_SEED=true`, counts 20/20/20/20/8/6/5).
  Still `[VENUE-UNMEASURED]`: network, TTFT-hosted, AI-cache, discover-median, VRAM target pair,
  Lighthouse, ngrok.
- Unchanged: `frontend.html` exists (42,746 B, wired per 17 — not re-audited line-by-line this pass);
  `demo/` = SHOTLIST only, zero `*.mp4` repo-wide; `submission/README.md:13,15,49` still
  `[UPLOAD PENDING]` + `<PASTE-REPO-URL-HERE>`; `assets/quota-proof/` = txt + README only, zero PNGs;
  `LIMITS.md:7,10,18` still `[AWAITING]` / `[UNMEASURED]`; `eval/live_scorecard.csv` +
  `deck/pitch.pdf` + `captions/demo.srt` present as in 17.

## Oracle 5 kills — re-scored

| # | Kill | Status v3 | Delta vs 17 |
|---|---|---|---|
| K1 | 96.8% rigged mock | **PARTIAL** (unchanged) | No new eval evidence. 5 live measured cases stand; 40-case headline still regex-over-JSON with `+ 11.0 MOCK`. Judge framing "eval tests shipped code" still only 5 deep. |
| K2 | Zero Synapse artifacts | **CLOSED** (unchanged) | IDs + quota-log + same-ID ×3 stand. Screenshots still owed → tracked under packet fix, not a reopen. |
| K3 | `/demo/*` missing | **CLOSED (code)** (unchanged) | Seed v14 + validate 0-fail stand. Venue stale-proc reboot + serialize-seed hazard still owed (venue-day fix). |
| K4 | Discover 404 moment | **CLOSED (substance) + CLOSED (SHOTLIST script)** / residual in history docs | UPGRADE on script: SHOTLIST no longer stages the old flow (D1). Residual: `research/*/03-demo-look.md`, `08-demo-ux.md`, `16-judge-score.md`, `25-step-discover.md` still describe H5-uncomment/FAIL-first/10→11 — history, not judge-facing; do not touch pre-freeze except a one-line pointer if cheap. |
| K5 | Two write paths, safety theater | **CLOSED** (unchanged) | 17/18 PASS stands. Nits unchanged: zero `available` laptop-category asset, single-worker audit-lock assumption. |

## Demo-critic (16/17 list) — re-scored

| # | Item | Status v3 |
|---|---|---|
| K1 | `demo/golden.mp4` missing | **OPEN** (unchanged) — P0 rung absent; runbook ready, captions ready. Sole blocker to GO. |
| K2 | Packet TODO shell | **PARTIAL (improved)** — seed/reset measured (D2). Still open: 7 × VENUE-UNMEASURED, `LIMITS.md` AWAITING rows, zero quota-proof PNGs, no `benchmark/run.js` (PowerShell repro documented instead — acceptable, stop relitigating). |
| K3 | `frontend.html` | **CLOSED (file + wired)** (unchanged) — live click-through at record time still owed, folded into record fix. |
| K4 | Synapse builds rehearsed | **CLOSED** (unchanged). |
| K5 | Script ID drift | **PARTIAL (narrowed)** — SHOTLIST clean. Residual, judge-visible: `submission/PITCH.md:11-12` + `captions/demo.srt:19` still say `R-0091/R-0092` while shipped code mints `EMP-021` (14). 10-min fix: align PITCH + srt to `EMP-021` (or pin receipt convention once, everywhere). |
| K6 | Physical layer | **OPEN** (unchanged, unobservable from repo) — USB ×2, hotspot, second-device playback owed at record. |
| K7 | Minor tripwires | **PARTIAL** (unchanged) — `UPLOAD PENDING`, `<PASTE-REPO-URL-HERE>`, `origin → pcb_designing.git`, 5-vs-3-cmd mismatch, `96.8%` residuals in `outline.md:10`/deck slide 6 vs README badge 97.5%. |

## Verdict: GO-WITH-FIXES

17's verdict stands: everything a judge touches exists except the video. D1+D2 closed two
sub-items (SHOTLIST choreography, seed/reset numbers) and opened nothing new. One recording
session + one packet pass + venue reboot = shippable. Not GO (no mp4, no links, no PNGs).
Not NO-GO (no kill reopened).

## Fix list (≤5, in order)

1. **Record P0 (90 min):** per fixed SHOTLIST; `demo/golden.mp4` (74–76 s) + USB ×2 + unlisted
   YouTube + `demo.srt` captions; live-click frontend once on camera (closes demo-critic K3-owed).
   Play back on second device on venue Wi-Fi. Unblocks K1/K6.
2. **Receipt-convention + placeholder sweep (20 min):** pin `EMP-021` in `submission/PITCH.md:11-12`
   + `captions/demo.srt:19` (drop `R-009x` unless code reverts — pick ONE); replace `UPLOAD PENDING`
   / `<PASTE-REPO-URL-HERE>` with real links at publish; reconcile 5-vs-3-cmd; fix `outline.md:10` +
   deck slide 6 `96.8%` → badge value 97.5% (or measured guarded-acc with M05 note). Unblocks K5/K7.
3. **Packet screenshots + VENUE fills (45 min, freeze day):** `synapse info` before/after PNG,
   `ollama ps`, ngrok session, AI-dashboard (all showing ₹0/$0) into `assets/quota-proof/`;
   paste speedtest, TTFT-hosted, AI-cache, discover-median ×5, Lighthouse into `BENCHMARKS.md`;
   update `LIMITS.md` AWAITING rows to match `quota-log.md`. Unblocks K2.
4. **Venue reboot + prewarm (15 min, venue day):** kill stale `:8001/:8002`, boot from disk, assert
   `GET /it/oncall-coverage?team=support-night` 200 (EMP-014) + prewarm rows; serialize seed/reset;
   add `prewarm.bat` twin. Unblocks K3-owed.
5. **Safety data nit + key hygiene (20 min):** seed one `available` laptop-category asset (retire
   monitor stand-in); document single-worker audit-lock; rotate `SYNAPSE_API_KEY` if `.env` ever
   staged; never publish `.env`.

## Single next command

```powershell
Get-ChildItem demo -Filter *.mp4; Select-String -Pattern 'R-009\d|UPLOAD PENDING|PASTE-REPO-URL' submission/PITCH.md, submission/captions/demo.srt, submission/README.md
```

(Expect: no mp4 = record still owed; R-009x/pending hits = fix-2 work list; zero hits = fix-2 done, proceed to fix-1 record.)
