# 01 — Fresh-clone first-impression review (AI-judge simulation, 2026-11-25)

Simulated `git clone https://github.com/athmabhiram1/Vibe-a-thon.git` against local mirror
`C:\Users\athma\OneDrive\Desktop\my projects\VIBE_CODE` (branch `main`). No code edits.
Read-only: `README.md`, `submission/*`, `run.bat`, `requirements.txt`, `.env.example`,
`seed/*`, `eval/*`, `evidence/*`, `demo/`, `hr_service/main.py`, `it_service/main.py`,
`git status / ls-files`.

## Verdict: NOT SUBMITTABLE as cloned — core green, packet red

A hostile judge stops at the two READMEs: no pasteable repo URL, no video URL, no
copy-pasteable Synapse client snippet. Backend/seed/eval are the only green part.
Fix order: publish URLs + video first (user-only), then 60 min of agent packet fixes.

## 1. README renders? YES, with stale warnings

- Renders: root `README.md:1-62` + `submission/README.md:1-71` parse; relative links
  (`./submission/README.md`, `ARCHITECTURE.md`, `PITCH.md`, `../evidence/quota-log.md`,
  `assets/quota-proof/synapse-info.txt`) all resolve. `submission/assets/arch.png` now
  exists (was missing in older audits). Badges render (shields.io).
- Defect D1 — stale origin warning: `README.md:25-27` + `submission/README.md:16` say
  "`origin` points at unrelated `pcb_designing.git` — do NOT push". `git remote -v`
  is now `https://github.com/athmabhiram1/Vibe-a-thon.git`. Warning is stale and
  scares a judge. Fix: delete/replace with real URL. Cost: 2 min.

## 2. 5-cmd quickstart true? NO — 2/5 fail on copy-paste

Quickstart (`README.md:15-21`, duplicated `submission/README.md:51-57`):
```bat
git clone <PASTE-REPO-URL-HERE> && cd VIBE_CODE
pip install -r requirements.txt
run.bat
start frontend.html
python seed/validate.py
```
- D2 — D2a `README.md:16` / `submission/README.md:52`: `<PASTE-REPO-URL-HERE>` is not
  pasteable. Fresh clone folder is `Vibe-a-thon`, not `VIBE_CODE`, so `cd VIBE_CODE`
  fails too. Fix: paste real URL + `cd Vibe-a-thon` (or rename). Cost: 2 min.
- Cmd2 PASS: `requirements.txt:1-11` exists (fastapi 0.165.0, fastmcp 4.2.4,
  uvicorn 0.54.0, aiosqlite, pydantic, email-validator). Old "missing requirements"
  audit is fixed.
- Cmd3 PARTIAL: `run.bat:1-36` boots HR `:8001` + IT `:8002`, probes
  `GET /hr/candidates?limit=1` (`hr_service/routers/hr.py:23` prefix `/hr`) and
  `GET /it/tickets/breaches` (`it_service/routers/it.py:25` prefix `/it`) — routes
  exist. But: Windows-only (`start`, `where`, `timeout`), spawns 2 windows, needs
  `curl` + `uvicorn` on PATH, adds 5s settle (~6–7s wall despite 1.3s boot claim).
  Header says "3 cmds" (`run.bat:4-7`) while README says "5 cmds" — judge confusion.
  Fix: clarify boot-vs-full, add mac/linux one-liner. Cost: 10 min.
- D3 — Cmd4 FAILS in mirror, Windows-only in fresh clone: `start frontend.html`
  (`README.md:19,33`). `git status` = ` D frontend.html`; `Test-Path frontend.html`
  = False locally, but `git show HEAD:frontend.html` = 781 lines / 41947 chars.
  Fresh clone gets the file, local mirror does not — dirty worktree. Plus `start`
  is Windows-only; mac/linux judge needs `open`/`xdg-open` or double-click note.
  Fix: `git checkout -- frontend.html` + OS-agnostic line. Cost: 5 min.
- Cmd5 PASS (with caveat): `python seed/validate.py` with no args defaults to its
  own dir (`seed/validate.py:404` `a.csv or Path(__file__).parent`) so bare command
  works; `--csv`/`--db` variants documented in `seed/README.md:32-35`. Keep as-is.

## 3. Structure obvious? NO — cluttered root, stale plan tree

- D4 — root has ~20 entries (`.cursor`, `demo`, `docs`, `eval`, `evidence`,
  `hr_service`, `it_service`, `reconcile`, `research`, `scripts`, `seed`,
  `submission`, `tests`, `workspace-*`, `.env`, `guide.txt`, `plan.md`,
  `probe_live.py`, `safety_check_server.py`, …). No top-level map; judge must read
  `plan.md:12-63` tree which is stale: lists `docker-compose.yml` (absent — only
  `compose.opt.yml` exists), `synapse_auto_server.py` (absent), `scripts/up.sh`
  (exists) / `prewarm.sh` (exists) but tree omits `share.sh`, `research/final`
  numbering drift. Fix: 10-line root map in README. Cost: 15 min.
- `submission/` is the judge entry and is complete as files
  (`README, ARCHITECTURE, BENCHMARKS, LIMITS, PITCH, deck/, captions/`) — good.
  Duplication root-README vs submission-README (same 5 cmds twice) drifts easily.

## 4. Server IDs + video link present? NO — IDs scattered, video zero

- D5 — video missing (FATAL): `README.md:61` + `submission/README.md:13` are both
  `[UPLOAD PENDING — record per PITCH.md, save USB copy to demo/golden.mp4, upload
  unlisted, paste URL here]`. `demo/` contains only `SHOTLIST.md`; recursive
  `*.mp4` = zero hits. `.gitignore:15` even reserves `!demo/golden.mp4`. No YouTube
  URL anywhere. P0 fallback unperformable. Fix (user-only): OBS 1080p30 ≤90s +
  USB×2 + unlisted upload + paste URL + QR. Cost: 90 min.
- D6 — repo URL missing (FATAL): `README.md:62` + `submission/README.md:15` are
  `[UPLOAD PENDING]` + `<PASTE-REPO-URL-HERE>`. Publish checklist exists
  (`submission/README.md:16`) but URLs never filled, despite `origin` now correct.
  Live links are `localhost:8001/docs + :8002/docs` — not clickable for async judge.
  Fix (user-only): `gh repo create`, push, paste URL in both READMEs. Cost: 15 min.
- D7 — server IDs not pasteable: `SYNAPSE_SERVER_ID=hr-api` in `.env.example:15`
  (only one; `it-api` second ID only implied by `--new` comment + `quota-log:20-24`
  + `synapse-info.txt:21-22` showing `2/10 servers, 775/100K lines`). No
  copy-pasteable MCP client JSON (`npx @2ndbrainlabs…` + server ID) in
  `submission/README.md` — judge cannot connect agent. `evidence/quota-log.md:9-13`
  template TODO block left in file alongside real log rows. Fix: paste both IDs +
  exact `synapse build … --endpoints "<allowlist>" --server-name …` strings + client
  snippet; delete TODO template. Cost: 15 min.

## 5. Scores claimed with evidence? CLAIMED, evidence partial + MOCK caveat buried

Claimed everywhere: guarded `97.5% acc (39/40) / 96.8% block (30/31) / 0% FP @ ~11ms
MOCK + 5 LIVE` (`README` badge, `plan.md:8,129`, `submission/README.md:7,24`,
`submission/BENCHMARKS.md:7,21`, `deck/outline.md:10`, `deck/build_pdf.py:70-72`).
- Evidence EXISTS: `eval/run.py:1-147` (MOCK honesty notice, `+11.0ms simulated`
  `run.py:93-94,113`), `eval/scorecard.csv:1-41` (40 rows), `eval/live_run.py`,
  `eval/live_scorecard.csv` (5 live), `probe_live.py`. Good that MOCK is labeled.
- D8 — latency is simulated, not measured (`eval/run.py:93-94` `+11.0`, `113`
  `+1.2`; `BENCHMARKS.md:21` admits "MOCK (wall-clock + 11.0ms simulated, NOT
  measured)"). Headline "11ms" reads as benchmark. Baseline is weak-by-design
  single-signal comparator (`29.0% block / 11.1% FP`) — honest but judge may call
  strawman. M05 `WARN` (`scorecard.csv:40`, expected BLOCK) counts as miss for acc
  (39/40=97.5%) but excluded from block (30/31=96.8%) — two denominators, one
  badge; needs one spoken line. Fix: single headline + spoken caveat
  "regex-over-JSON MOCK + 11ms simulated, 5 live measured pass". Cost: 10 min.
- D9 — `submission/BENCHMARKS.md` has 5 `[VENUE-UNMEASURED]` rows: network
  (`:5`), TTFT hosted (`:17`), AI call cached/fresh (`:19`), `discover` median ×5
  (`:20`), Lighthouse (`:23`); `:18` substitutes `qwen3:8b` for spec'd `qwen3:4b`;
  `:7` references `submission/benchmark/run.js` which does not exist (repro is
  PowerShell one-liner in `:28-34`). `LIMITS.md:8-10` ngrok/AI-dashboard screenshots
  pending; `:18` `CACHE_TTL` unmeasured. Fix: fill on freeze day or mark
  out-of-scope. Cost: 20 min agent + freeze-day captures (user).
- D10 — `submission/ARCHITECTURE.md:24` PNG fallback `assets/arch.png` now exists
  (fixed) but note says "redrawn via matplotlib, not Mermaid export" — fine, keep.

## Full defect list (file:line + fix cost)

| # | File:line | Defect | Cost |
|---|---|---|---|
| D1 | `README.md:25-27`, `submission/README.md:16` | Stale `pcb_designing.git` warning; origin is now `Vibe-a-thon` | 2 min |
| D2 | `README.md:16`, `submission/README.md:52` | `<PASTE-REPO-URL-HERE>` + `cd VIBE_CODE` (real folder `Vibe-a-thon`) | 2 min |
| D3 | `README.md:19,33,47`, `frontend.html` (worktree deleted, HEAD 781 lines) | `start frontend.html` fails locally; Windows-only; dirty worktree | 5 min |
| D4 | `README.md`, `plan.md:12-63` | No root map; plan tree stale (`docker-compose.yml`, `synapse_auto_server.py` absent) | 15 min |
| D5 | `README.md:61`, `submission/README.md:13`, `demo/` (only `SHOTLIST.md`, 0×`*.mp4`) | No video URL, no `golden.mp4` | 90 min user-only |
| D6 | `README.md:62`, `submission/README.md:15` | No repo URL; localhost links not public | 15 min user-only |
| D7 | `.env.example:15`, `submission/README.md` (no snippet), `evidence/quota-log.md:9-13` | Only 1 ID listed, no client JSON, TODO template left | 15 min |
| D8 | `eval/run.py:93-94,113`, `eval/scorecard.csv:40`, `submission/README.md:7,24` | Simulated latency, dual denominators (97.5% vs 96.8%), weak baseline | 10 min + spoken caveat |
| D9 | `submission/BENCHMARKS.md:5,17,19,20,23,7`, `submission/LIMITS.md:8,10,18` | 5 VENUE-UNMEASURED, missing `run.js`, missing screenshots/TTL | 20 min + freeze-day |
| D11 | `run.bat:4-7` vs `README.md:12-13` | "3 cmds" vs "5 cmds" confusion; Windows-only `run.bat:15-32` | 10 min |
| D12 | `research/prejudge/10-verdict.md` exists | Prior verdict notes already cover FATALs; do not resubmit without F2+F1 | — |

No code edits made. Highest-EV next step: record `demo/golden.mp4` + publish repo
URLs (user-only, ~105 min); agent packet fixes total ~60 min.
