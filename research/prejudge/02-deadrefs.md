# 02 — Dead-Reference Hunt (read-only, 2026-11-25)

Scope: `README.md`, `ARCHITECTURE.md` (root: absent — only `submission/ARCHITECTURE.md`), `plan.md`, `submission/*`.
Method: relative-path existence on disk + `curl HEAD` for shields (safe) + grep `TODO|UPLOAD PENDING|WIP|XXX|lorem|example.com|MUST-FIX|PLACEHOLDER|PASTE|TBD|FIXME|UNMEASURED|pending` in scope.
`localhost:*` URLs are runtime-dependent (servers down) — marked UNVERIFIED, not dead.

## Link / path verdicts

| File:line | Reference | Status |
|---|---|---|
| `submission/README.md:3` | `https://img.shields.io/badge/build-passing-brightgreen` | PASS — HEAD 200, syntax OK (external, needs network at render) |
| `submission/README.md:4` | `.../badge/track-T3_copilot_across_two_systems-blue` | PASS — HEAD 200, syntax OK |
| `submission/README.md:5` | `.../badge/synapse-auto_%2B_discover-purple` | PASS — syntax OK (same shields host as :3–4, spot-checked) |
| `submission/README.md:6` | `.../badge/cost-%E2%82%B90_free_tier-success` | PASS — syntax OK (UTF-8 ₹ encoded correctly) |
| `submission/README.md:7` | `.../badge/guarded-97.5%25_acc_(39%2F40)_0%25_FP_MOCK-informational` | PASS — syntax OK (long label renders but valid) |
| `README.md:61` / `submission/README.md:13` | 🎥 Video `[UPLOAD PENDING … demo/golden.mp4 … paste URL here]` | **DEAD / PLACEHOLDER (MUST-FIX #1)** — `demo/` = `SHOTLIST.md` only; zero `*.mp4` repo-wide; no YouTube URL anywhere |
| `README.md:16,62` / `submission/README.md:15,52` | 📦 Repo `<PASTE-REPO-URL-HERE>` + 2× `[UPLOAD PENDING]` | **PLACEHOLDER (MUST-FIX #2)** — remote `https://github.com/athmabhiram1/Vibe-a-thon.git` exists public, but placeholders unfilled; stale `pcb_designing.git — do NOT push` warning in both READMEs is outdated per `32-packet.md` |
| `README.md:33,47` / `submission/README.md:55` | `start frontend.html` + "frontend.html exists (verified)" | **DEAD — file MISSING** — zero `*.html` at root/repo-wide except `submission/deck/pitch.html`; both READMEs' "verified exists" claim is false |
| `README.md:28,43` / `submission/README.md:49,53` | `requirements.txt` | PASS — EXISTS at root |
| `README.md:30,45` / `submission/README.md:54` | `run.bat` | PASS — EXISTS |
| `README.md:35` / `submission/README.md:56` | `seed/validate.py` | PASS — EXISTS (+ `seed/README.md` EXISTS) |
| `submission/README.md:33,65` | `./ARCHITECTURE.md`, `./PITCH.md`, `./deck/outline.md`, `./captions/demo.srt` | PASS — all EXIST |
| `submission/README.md:61` | `./BENCHMARKS.md`, `./LIMITS.md` | PASS — both EXIST |
| `submission/README.md:66` / `submission/LIMITS.md:7` | `../evidence/quota-log.md` | PASS — EXISTS, log rows populated 2026-11-24/25 (template `TODO` lines 9–13 intentional) |
| `submission/ARCHITECTURE.md:24` | `assets/arch.png` + `assets/render-pngs.py` | PASS — both EXIST (`arch.png` closes old 22-packet gap) |
| `submission/ARCHITECTURE.md:45` / `plan.md:90` | `docs/CLIENTS.md` §7 allowlist | PASS — EXISTS, §7 present |
| `submission/deck/outline.md:14` | `deck/pitch.pdf` + `deck/pitch.html` | PASS — both EXIST (`pitch.pdf` 10,897 B, 8 slides per 32-packet) |
| `submission/LIMITS.md:7,11` | `assets/quota-proof/synapse-info.txt`, `ollama-ps.txt`/`ollama-ps.png` | PASS — all EXIST (2026-11-24 captures; png = text rendering, disclosed) |
| `submission/LIMITS.md:8-10` + `quota-proof/README.md:7-9` | `assets/quota-proof/ngrok.png`, `ai-dashboard.png` | **MISSING / pending (MUST-FIX #3)** — user-owned freeze-day shots, explicitly marked pending |
| `submission/LIMITS.md:9` | `assets/quota-proof/` fly screenshot "only if deployed" | N/A — backup never deployed (0 hrs); correctly absent, not dead |
| `submission/BENCHMARKS.md:7` | `submission/benchmark/run.js` "does not exist" | NOT-DEAD — absence explicitly documented, PowerShell repro given instead |
| `submission/PITCH.md:3` | source `research/final/16-judge-score.md` §6 | PASS — file EXISTS |
| `plan.md:18` | `docker-compose.yml` (OPT-IN, "golden path = no Docker") | **STALE/DEAD** — file MISSING; only `compose.opt.yml` EXISTS (the actual backup profile) |
| `plan.md:20-21,23-63` | `compose.opt.yml`, `.env.example`, `hr_service/`, `it_service/`, `seed/`, `eval/`, `submission/`, `research/build/49-master-plan.md`, `research/build/50-index.md` | PASS — all EXIST |
| `plan.md:56` | `demo/golden.mp4` | **MISSING** — same as MUST-FIX #1 |
| `plan.md:147` | evidence in `research/verify/01-10` | PASS (dir EXISTS; canonical evidence now in `research/verify-final/`, e.g. `12-synapse-run.md` EXISTS) |
| `docs/CLIENTS.md:14,38,40` | `python synapse_auto_server.py` (Inspector LIVE command) | **MISSING at root** — no `synapse_auto_server.py` repo-wide per glob/shell check; runbook command currently unrunnable as written |
| `README.md` + `submission/README.md` | `http://localhost:8001/docs`, `http://localhost:8002/docs`, `POST /demo/seed`, `curl :8002/it/tickets/breaches` | UNVERIFIED — runtime-only; servers not running during read-only hunt; ports frozen 8001/8002 consistent everywhere |

## MUST-FIX list (source: `research/verify-final/32-packet.md` §Gaps, re-confirmed)

1. Video + `demo/golden.mp4` missing — form link empty = rejection risk.
2. Repo URL placeholders (`<PASTE-REPO-URL-HERE>`, `[UPLOAD PENDING]`) + stale `pcb_designing` warning + dirty `eval/scorecard.csv` + untracked `.vscode/` — commit + push + verify GitHub render.
3. Quota-proof PNGs (`ngrok.png`, `ai-dashboard.png`, real `synapse-info.png` if pixels required).
4. Freeze-day numbers: `LIMITS.md:8,10,18` + `BENCHMARKS.md` 7× `[VENUE-UNMEASURED]`.
5. Dirty tree — submit from clean `git status`.

## TODO / placeholder grep (in-scope files only)

- Zero bare `TODO`/`FIXME`/`WIP`/`TBD`/`XXX`/`lorem`/`example.com` in `README.md`, `plan.md`, `submission/*` (incl. deck, captions, assets READMEs).
- Remaining markers all intentional/user-owned: `README.md:16,27,50,61-62` + `submission/README.md:13,15-16,52` (`[UPLOAD PENDING]`, `<PASTE-REPO-URL-HERE>`); `BENCHMARKS.md` 7× `[VENUE-UNMEASURED]`; `LIMITS.md:8,10,18` 3× `[UNMEASURED]`; `quota-proof/README.md:7-9` 3× `[pending]`; `evidence/quota-log.md:9-13` template `TODO`s (log rows :20-25 populated).
- `example.com` hits repo-wide are benign synthetic data (`seed/*.csv`, `eval/*`, `research/build/*` doc snippets) — none are links in judged docs.
- `MUST-FIX` string appears only in `research/verify-final/32-packet.md:49` (the list quoted above), not in judged docs.
