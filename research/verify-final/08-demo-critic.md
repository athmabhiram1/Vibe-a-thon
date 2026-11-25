# 08 — Demo Critic: Track 3 Stage-Readiness Attack

**Date:** 2026-11-24 · **Role:** hostile judge / stage-manager · **Scope:** 60s script (`research/frontend/03-demo-look.md` + `submission/PITCH.md`), P0–P4 ladder, pre-flight, 3× Q&A, packet (`research/build/15-lib-packet.md` file list vs `submission/`), `plan.md` §6–§8 + `reconcile/RECONCILE.md`.
**Method:** read-only inspection. Verified live on disk: `submission/` tree, `demo.srt`, `deck/outline.md`, `BENCHMARKS.md`, `LIMITS.md`, `README.md`, `ARCHITECTURE.md`; `Test-Path` for `demo/`, `frontend.html`, `.synapse/`; recursive `*.mp4` search (zero hits).

## Verdict: NOT stage-ready. Code is green (RECONCILE: boot/validate/eval/smoke all PASS), demo assets are not. P0 — the rung the whole ladder hangs from — does not exist.

## Kill-list, ranked by likelihood × impact (fix-time attached)

### K1 — `demo/golden.mp4` does not exist. No `demo/` dir at all. (LIKELY × FATAL · fix 1–2h)
- Recursive `*.mp4` search: **zero files**. `Test-Path demo` = False. P0 cue ("Here's the golden path recorded this morning") is a lie until recorded.
- Escalation rule in §4 (`P1 fail <15s → P0 plays while P2 attempted`) **cannot execute** — any live failure drops straight to P4 narrative flip.
- `submission/README.md` links `../demo/golden.mp4` + `TODO_YOUTUBE_URL` → broken on arrival for async judges.
- **Fix:** OBS 1080p30 per 15-lib-packet §7 → record §2 beats → trim ≤90s → `demo/golden.mp4` + desktop copy + USB copy + unlisted YouTube (captions `demo.srt` already exist and match the 75s script — reuse, don't re-caption).

### K2 — Packet is a TODO shell. Async judges score this first. (CERTAIN × HIGH · fix 2–4h)
Against 15-lib-packet §2 file list:
| Expected | Actual |
|---|---|
| `README.md` (live links) | present but `TODO_GITHUB_URL` ×2, `TODO_YOUTUBE_URL`, run cmds cite `requirements.txt` which **doesn't exist** (repo has `requirements-hr.txt` + `requirements-it.txt` per RECONCILE D1 — judge rerun breaks on cmd 2) |
| `BENCHMARKS.md` + `benchmark/run.js` | MD present, **every number TODO** (only eval row filled: 96.8%/0%); `benchmark/` dir **missing** so the documented repro crashes |
| `LIMITS.md` + `assets/quota-proof/` (≥2 screenshots) | MD present, TODOs throughout (servers, lines, tunnels, req/demo, VRAM, TTL); `assets/` **missing entirely** — zero screenshots, ₹0 unproven |
| `ARCHITECTURE.md` + `assets/arch.png` | MD complete (best file in packet) but PNG fallback TODO |
| `deck/outline.md` → PDF backup | outline present, `deck/pitch.pdf` TODO |
| `captions/demo.srt` | ✅ present, 6 cues 0:00–1:15, matches PITCH script |
- **Fix:** run the five measurements tonight (cold start, p50/p95 via a 20-line `benchmark/run.js` you must write, TTFT hosted+local, `discover` median ×5, `ollama ps` VRAM) → fill tables → 2 phone photos of dashboards (`synapse info`, billing ₹0) → export deck PDF → replace the 3 TODO URLs.

### K3 — `frontend.html` (LEFT pane = the demo) does not exist. (CERTAIN-if-live × HIGH · fix 1–3h or descoped 30min)
- `Test-Path frontend.html` = False repo-wide. Spec exists (`research/frontend/02-frontend-spec.md`) but no implementation. The 60s §2 beat table is unperformable as written (preview pane, staged→ACTIVE flip, receipt R-0092 render).
- **Fix A (preferred):** build the minimal static page from the §1 ASCII mock (candidate card + preview list + Approve button → receipt div; no backend needed, hardcode canonical IDs).
- **Fix B (descope):** rewrite §2/PITCH to terminal-only (curl staged JSON + audit tail) and delete LEFT-pane references. Do NOT walk on stage hoping a page appears.

### K4 — Zero Synapse builds ever run from this checkout. Live `--discover` moment is unrehearsed. (HIGH × HIGH · fix 30–60min)
- `Test-Path .synapse` = False → no `surface_cache.json`, no server ID, no measured `discover` latency. T3 tripwire (`discover` median >90s / <3-of-5 → T3→T2 in 48h) **cannot be evaluated**.
- `evidence/quota-log.md` exists but with no builds logged, T8 headroom (`Servers: 2/10` claimed in pre-flight) is unverified — quota 429 on stage is the exact death the ladder assumes you've hedged.
- **Fix:** tonight: `synapse info` (log it) → baseline build 10 tools → uncomment H5 → fail-first rebuild (confirm stale-cache line) → `--discover` rebuild ×5, record medians → re-comment H5, reset `MCP_REV` to "1". This single session retires K4 and half of K2's table.

### K5 — Script ID drift: two scripts, two casts. (MEDIUM × MEDIUM · fix 15min)
- `03-demo-look.md` §1–2 stages **CAND-1147 / LT-4420 / T-551 / R-0091**; `PITCH.md` + `demo.srt` + RECONCILE-validated seed stage **CAND-002 / LT-1005 / T-5001**. A judge cross-checking seed (`CAND-002 Priya`, LT-1005 double-hold trap, 3 breached incl. T-5001) against the performed demo catches fiction instantly.
- **Fix:** unify everything on canonical seed IDs (CAND-002, LT-1005, T-5001/T-5002, R-0091/R-0092). One `grep` + edit pass over `03-demo-look.md`.

### K6 — Physical layer unverifiable from repo (and therefore assumed absent). (MED-HIGH × HIGH · fix 30min night-before)
- USB stick with golden.mp4, hotspot pairing, spare laptop, taped cue-card block (§6 code fence), DND/notifications, 18pt terminal font, `ollama pull qwen2.5:7b` pre-pull — none confirmable here. Venue Wi-Fi death without a paired hotspot + local model = P2 fails too.
- **Fix:** pre-flight §6 is a good list — print it, add three lines (USB tested in a second machine · hotspot paired + 200MB free · `ollama list` shows model), initial every box with a timestamped photo.

### K7 — Minor tripwires (fold into K2/K4 session, 15min total)
- `PITCH.md` is a 75s script; plan §6 demands a <60s cut — decide which runtime the video ships and label `demo.srt` accordingly (current srt runs to 1:15; fine for 75s, mislabeled if you promise 60s).
- Pre-flight assumes `.cursor/mcp.json` with `MCP_REV` — verify the file exists before showtime or the D6 live beat has no bump to perform.
- `ngrok.yml` exists at root (good for P1) but no ngrok tunnel proof in packet — one screenshot closes it.

## What survives contact (keep)
- RECONCILE state: boot/validate/eval/smoke green, H5 correctly absent at baseline, LT-1005/T-5001 traps live — the *code* half of every demo beat is real.
- Fallback *doctrine* (§4 announce-don't-apologize, 15s/20s fail-fast rules, Inspector-only live verdict) is correct and reconciled with measured constraints. Only the P0 *asset* is missing, not the plan.
- 3× Q&A (§5) are the strongest text in the demo package: each answer points at a performed beat + a measured number (1-vs-8 fusion, `${VAR}` secrecy, 96.8%/0% eval). No fix needed beyond K5 ID unification.
- `demo.srt` + `PITCH.md` + `deck/outline.md` are show-ready; they are the template the rest of the packet must rise to.

##240-min order (do tonight, in this sequence)
1. **K4** Synapse session (60min) → yields server ID, quota log, discover medians — unblocks K2 numbers.
2. **K1** record golden.mp4 (90min incl. 3 takes) → P0 exists; upload unlisted; USB ×2.
3. **K3** Fix A page or Fix B descope (60–180min; decide in first 10min — no half-built page on stage).
4. **K5** ID unification grep pass (15min) → re-read both scripts aloud once.
5. **K2** fill tables + screenshots + `benchmark/run.js` + deck PDF + URLs (remainder).
6. **K6** physical kit + printed pre-flight, initialed.
