# 15 — Hygiene Re-audit (after fix lanes)

Date (UTC): 2026-11-24 · Scope: re-verify the 8 SHIP-BLOCKERs from `research/verify-final/09-hygiene.md` §Gap-list.
Method: read-only (no installs, no builds, no mutations).

## Verdict summary

| # | 09-blocker | Now | Evidence |
|---|---|---|---|
| 1 | Root `requirements.txt` missing; `fastapi==0.165.0` existence doubt; unpinned `uvicorn`/`aiosqlite` | **CLOSED (file) / install UNVERIFIED** | `requirements.txt` (383 B, 2026-11-24 13:34) exists; combines hr+it; pins `uvicorn==0.54.0`, `aiosqlite==0.22.1`; header comment claims `fastapi==0.165.0` + `fastmcp==4.2.4` "both exist on PyPI (2026-11-24) and install clean". `requirements-hr.txt` / `requirements-it.txt` carry the same pins. Read-only lane could not run `pip install` — treat the header's install claim as author-asserted, not independently confirmed. |
| 2 | No `.gitignore`; DBs/`__pycache__` committable | **CLOSED (file) / root-cause open** | `.gitignore` (321 B, 2026-11-24 13:34) exists: `*.db`, `*.db-journal/-wal/-shm`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.env`, `*.mp4` with `!demo/golden.mp4`. (Earlier glob missed it — dotfile; confirmed via `Get-ChildItem -Force`.) Residual: `seed/demo.db`, `seed/seed-snapshot.db` (205 KB each), `__pycache__/`, `.pytest_cache/`, `.env` (586 B, local, `SYNAPSE_API_KEY` key present — values not inspected beyond key names) still sit on disk, now ignored-not-absent; home-dir-as-repo-root (§9 of 09) is untouched by a `VIBE_CODE/`-local ignore file. |
| 3 | `DATABASE_URL` vs `HR_DB_PATH`/`IT_DB_PATH` vs `DATABASE_URL_HR/_IT` three-scheme mess | **CLOSED (runtime) / stale docs remain** | Single scheme at runtime: `hr_service/db.py:30` reads `HR_DB_PATH` (default `seed/demo.db`); `it_service/db.py:22` reads `IT_DB_PATH`; `compose.opt.yml:17,33` uses `HR_DB_PATH`/`IT_DB_PATH`; `.env.example:8-13` documents both + explicit NOTE that `DATABASE_URL` is NOT read by code. Stale references: `plan.md:21`, `submission/LIMITS.md:19` still list `DATABASE_URL` as the documented var; `research/build/*` docs predate the decision. Minor: `run.bat:12` echo says DBs live at `hr_service/hr.db, it_service/it.db`, code default is `seed/demo.db`. |
| 4 | No root `README.md`; 3-vs-5-cmd conflict; both pointed at missing file; `TODO_*` URLs | **PARTIAL → STILL-OPEN** | Fixed part: both quickstarts now point at a file that exists (`requirements.txt` — `submission/README.md:48`, `run.bat:6`). Still open: (a) no root `README.md` — only `submission/README.md` + `seed/README.md` (dataset spec, not a quickstart; canonical quickstart is de-facto `submission/README.md`); (b) dual claims persist — `submission/README.md:44` "5 cmds" vs `run.bat:4-7` "3 cmds"; (c) `TODO_YOUTUBE_URL` (`submission/README.md:13`), `TODO_GITHUB_URL` (`:14`, `:47`) unresolved. |
| 5 | `submission/deck/pitch.pdf` missing (`outline.md:14` TODO) | **STILL-OPEN** | `submission/deck/` contains only `outline.md`; `outline.md:14` still ends "export PDF backup at `deck/pitch.pdf` (TODO)". No `pitch.pdf` anywhere (only unrelated `Vibe-a-thon-Participant-Guide-*.pdf` at repo root). |
| 6 | `evidence/quota-log.md` all-TODO, zero real rows | **STILL-OPEN** | File (1823 B, 2026-11-24) keeps the template + rules, but the log table is still 3 × `TODO_YYYY-MM-DD` rows with `TODO` before/after/CMD/tool/proof cells. `submission/LIMITS.md:7-12,18` numbers are still `TODO` (consistent with the log — cites nothing because there is nothing). |
| 7 | `demo/golden.mp4` missing; `demo/` absent | **STILL-OPEN** | Recursive `*.mp4` search: zero hits. No `demo/` directory. `submission/README.md:13` still links `../demo/golden.mp4` + `TODO_YOUTUBE_URL`. Only `submission/captions/demo.srt` exists. |
| 8 | Scorecard stale math (`96.8%` badge vs 39/40 = 97.5%) | **CLOSED (README) / stale copies remain** | `eval/scorecard.csv` mtime 2026-11-24 13:57 (newer than `cases.json` 2026-11-23 and `run.py` 2026-11-24 13:37); 40 data rows = 40 `"id"` hits in `cases.json`; 39 × `guarded_correct=1` + M05 `WARN` (`guarded_correct=0`) → 39/40 = **97.5%**. `submission/README.md:7` badge and `:22` body now say `97.5% (39/40)` with M05 WARN-as-designed annotated — correct. Residuals: `submission/deck/outline.md:10` and `plan.md:8` still say `96.8%`. Nice-to-have closed: `seed/_verify_tmp.py` gone from `seed/` listing. Latency columns still uniform `~11ms` mock (labelled mock — fine). |

## CLOSED vs STILL-OPEN

**CLOSED (4):** 1 — root `requirements.txt` (+`uvicorn`/`aiosqlite` pins; install claim author-asserted, not re-run here).
2 — `.gitignore` with DB/`pycache`/`.env`/mp4 coverage (+golden exception).
3 — DB env single-scheme at runtime (code + compose + `.env.example` aligned; `DATABASE_URL` explicitly disowned).
8 — eval badge math in `submission/README.md` (97.5% = 39/40, M05 annotated; scorecard fresh, 40/40 rows).

**STILL-OPEN (4):** 4 — `TODO_YOUTUBE_URL` / `TODO_GITHUB_URL` (`submission/README.md:13-14,47`); no root `README.md` (canonical = `submission/README.md` by default); 5-vs-3-cmd dual claim.
5 — no `submission/deck/pitch.pdf`; `outline.md:14` TODO line intact.
6 — `evidence/quota-log.md` zero real `synapse info` rows; `LIMITS.md` quota numbers all `TODO`.
7 — no `demo/` dir, no `golden.mp4` anywhere; README video link points at air.

**Follow-ups (non-blocking):** update `LIMITS.md:19` + `plan.md:21` var lists to `HR_DB_PATH`/`IT_DB_PATH`; fix `outline.md:10` + `plan.md:8` `96.8%` → `97.5%`; reconcile `run.bat:12` DB path echo with `seed/demo.db` default; home-dir repo root still unaddressed (out of read-only scope — needs `git re-root` decision); `.env` lives on disk (ignored, but contains a `SYNAPSE_API_KEY` key — confirm never staged: `git status` from EPA).
