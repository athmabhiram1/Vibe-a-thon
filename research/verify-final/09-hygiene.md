# 09 — Repo Hygiene Audit (VIBE_CODE)

Date (UTC): 2026-11-24 · Scope: `VIBE_CODE/` (repo root is `C:\Users\athma` — whole home dir, see §8)

## 1. Dependency pins — PASS with warnings

- `requirements-hr.txt` vs `requirements-it.txt`: **match** on `fastapi==0.165.0`, `fastmcp==4.2.4`, unpinned `uvicorn`, `pydantic>=2.10,<3`, unpinned `aiosqlite`. IT-only delta is intentional: `email-validator==2.2.0`.
- ✅ `fastapi==0.165.0` confirmed real PyPI release (0.165.0, 2026-11-18 per `pypi.org/pypi/fastapi/json` + `pip show fastapi` 0.165.0 in `18-greenpass.md` / `07-external.md`) — no typo, keep pin.
- ⚠️ `uvicorn` + `aiosqlite` unpinned → judge-side drift. Pin both. **NICE-TO-HAVE.**
- ❌ **No root `requirements.txt`**, yet both `run.bat:6` and `submission/README.md:48` tell judges `pip install -r requirements.txt`. Broken on fresh clone. **SHIP-BLOCKER** — add `requirements.txt` (or fix docs to the two per-service files).

## 2. `.env.example` — mostly complete, one real mismatch

Present keys (8): `HR_BASE_URL`, `IT_BASE_URL`, `ENDPOINT_BASE_URL`, `DATABASE_URL`, `SYNAPSE_SERVER_ID`, `MCP_REV=1`, `OLLAMA_HOST`, `ALLOW_DEMO_SEED=true`. Matches `plan.md` manifest and `submission/LIMITS.md` claim. No `.env` file committed (checked — absent). Good.
Gaps:
- **SHIP-BLOCKER:** code reads `HR_DB_PATH` (`hr_service/db.py:29`) / `IT_DB_PATH` (`it_service/db.py:21`), defaulting to `seed/demo.db` — but `.env.example` documents only `DATABASE_URL=sqlite:///./hr.db`. `compose.opt.yml` uses yet other names (`DATABASE_URL_HR`/`DATABASE_URL_IT`). Three naming schemes for one concept; a judge setting `DATABASE_URL` changes nothing. Align on one scheme.
- **NICE-TO-HAVE:** `NGROK_AUTHTOKEN`, `NGROK_DOMAIN[_HR|_IT]` (used by `ngrok.yml`, `run.bat:35`) undocumented; `SAFETY_*` (`safety_check_server.py:40-98`) undocumented if that server is in scope.

## 3. Secrets committed — PASS (no live secrets found)

- `grep -rE 'sk-|ghp_|gho_|xox-|AKIA|hf_|AIza|BEGIN (RSA )?PRIVATE KEY'`: all hits are placeholders/synthetic — `guide.txt` + `research/build/*` use `sk-ant-…` / `sk-...` placeholders; `eval/cases.json` uses synthetic `sk-live-abc123xyz` fixtures (expected — the eval tests redaction of exactly these); `SECRET_RE` definitions in `safety_check_server.py` / `eval/run.py`; `SN-…` hardware serials in `seed/equipment.csv` are fake inventory IDs, not credentials.
- `seed/api_keys.csv`: synthetic only — `key_prefix` + sha256 `key_hash`, no secret values. Safe.
- No `.env`, no `PRIVATE KEY`, no `AKIA`/`ghp_` values anywhere.

## 4. README quickstart "3-command" claim — FAIL (SHIP-BLOCKER)

- There is **no root `README.md`** (only `submission/README.md` + `seed/README.md`). Any "README quickstart" judges find is `submission/README.md §Run locally`, which claims "**5 cmds**, fresh clone, <60s" but: (a) references the nonexistent `requirements.txt` (see §1); (b) is actually 5 *lines* containing ~6 commands (`git clone` + `cd` are jammed on line 1); (c) `run.bat` advertises a *different* "3 cmds" (`clone` / `pip install -r requirements.txt` / `run.bat`) — same broken file ref. Two competing claims, both broken.
- Unresolved placeholders in `submission/README.md:13-14,47`: `TODO_YOUTUBE_URL`, `TODO_GITHUB_URL`. **SHIP-BLOCKER** — replace before ship (or drop the clone line and point at the zip).
- Fix: one canonical quickstart (recommend `run.bat` path on Windows), one command count, real URLs.

## 5. `submission/` packet — present but unfinished

Present (7): `README.md`, `ARCHITECTURE.md`, `BENCHMARKS.md`, `LIMITS.md`, `PITCH.md`, `deck/outline.md`, `captions/demo.srt`. Captions file is real (6 cues, 0:00–1:15). Missing/unfinished:
- **SHIP-BLOCKER:** `deck/outline.md:14` ends at "export PDF backup at `deck/pitch.pdf` (TODO)" — no `pitch.pdf` in `deck/`. Build or drop the line.
- **SHIP-BLOCKER:** `TODO_YOUTUBE_URL` / `TODO_GITHUB_URL` (see §4).
- NICE-TO-HAVE: no `submission/assets/quota-proof/*.png` (referenced by `evidence/quota-log.md` template).

## 6. `evidence/quota-log.md` — EXISTS, but empty template (SHIP-BLOCKER)

File exists (`2026-11-23`, 1608 B) with correct template + quota rules, but the log table is 3 × `TODO_YYYY-MM-DD` rows — zero real `synapse info` before/after entries. `submission/LIMITS.md` numbers therefore cite nothing. Append at least the baseline `hr-api` build entry per the file's own header instruction before freezing.

## 7. `demo/golden.mp4` — MISSING (SHIP-BLOCKER)

`demo/` directory does not exist at all; `submission/README.md:13` links `../demo/golden.mp4`. Only `submission/captions/demo.srt` exists. Record 60–90s cut (script + captions already written) or downgrade the README link to "video TODO" — but a track with a live-demo beat and no video ships at a disadvantage.

## 8. `eval/scorecard.csv` — FRESH ✔ with stale math ⚠️

- Fresh: `scorecard.csv` mtime 2026-11-24 13:30, newer than `run.py` / `cases.json` (2026-11-23). 40 data rows = 40 cases in `cases.json`. Row order/categories align.
- ⚠️ Math drift (NICE-TO-HAVE, fix the badge before judges recompute): 39 × `guarded_correct=1` + M05 `WARN` (`guarded_correct=0`) → 39/40 = **97.5%** exact-match, not the `96.8%` claimed in `submission/README.md:7,22`. (96.8% = 30/31, i.e. the old 31-row suite?) Also `M05` expected `BLOCK`, got `WARN` — intentional per red-team citation rule, but the README's "30 BLOCK + 1 WARN + 9 ALLOW" line should say so explicitly. Latency columns are uniform `~11ms` mock timings — label as mock (it does) and keep.
- Stray file: `seed/_verify_tmp.py` (2026-11-24, 1556 B) looks like a scratch verify script — delete or move to `scripts/`. NICE-TO-HAVE.

## 9. Missing `.gitignore` + oversized repo root (SHIP-BLOCKER)

- No `.gitignore` anywhere in `VIBE_CODE/`. Working tree already contains `seed/demo.db` + `seed/seed-snapshot.db` (205 KB each), `__pycache__/`, `seed/_verify_tmp.py` — all committable by accident.
- Worse: `git status` from `C:\Users\athma` shows the **git repo root is the home directory** (status lists `Amber Flux/`, `HACK_GLOBAL/`, `pcb/`, `.aws/`, `.cargo/` …). A judge-side `git clone` of the published repo is unaffected, but any `git add -A` from here would sweep the whole home dir. Minimum fix: `VIBE_CODE/.gitignore` (`*.db`, `__pycache__/`, `.env`, `*.mp4` except `demo/golden.mp4`?) and never stage above `VIBE_CODE/`. Ideally re-root the repo at `VIBE_CODE/`.

## Gap list (sorted)

**SHIP-BLOCKER**
1. `fastapi==0.165.0` confirmed real (PyPI 0.165.0, 2026-11-18; `pip show` 0.165.0 in `18-greenpass.md`) — closed, keep pin (§1).
2. No root `requirements.txt` despite two docs referencing it (§1, §4).
3. `DATABASE_URL` (docs/compose) vs `HR_DB_PATH`/`IT_DB_PATH` (code) mismatch — one scheme (§2).
4. No root `README.md`; two conflicting quickstart claims (3 vs 5 cmds), both pointing at missing file; `TODO_*` URLs unresolved (§4).
5. `submission/deck/pitch.pdf` missing (§5).
6. `evidence/quota-log.md` all-TODO, zero real entries (§6).
7. `demo/golden.mp4` missing; `demo/` doesn't exist (§7).
8. No `VIBE_CODE/.gitignore`; SQLite DBs + `__pycache__` loose; repo root is home dir (§9).

**NICE-TO-HAVE**
9. Pin `uvicorn`, `aiosqlite` (§1).
10. Document `NGROK_*` vars in `.env.example`; `SAFETY_*` if in scope (§2).
11. Scorecard badge math: `96.8%` → actual `97.5%` (or define WARN half-credit); annotate M05 WARN-as-designed (§8).
12. Remove/relocate `seed/_verify_tmp.py`; add `submission/assets/quota-proof/*.png` (§5, §8).
