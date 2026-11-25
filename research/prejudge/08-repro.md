# 08 — Reproducibility dry run (root README quickstart, verbatim)

Date: 2026-11-25 (UTC) · Cwd: repo root (`VIBE_CODE/`) · Interpreter: system Python 3.11.0
(no venv dir exists; "reuse existing venv" = system interpreter) · Shell: PowerShell (no `tail`, `&&`).

Backends were **already running on arrival**: `:8001` (PID 32420), `:8002` (PID 12100),
`:3000` (PID 10812). Full `run.bat` re-boot was **deliberately not executed** (would spawn
duplicate uvicorn instances → `address already in use` orphan windows); its two probe lines
were run verbatim instead. Nothing was edited; one side effect noted (§7).

## Command log (README order)

| # | README cmd (verbatim) | Result |
|---|---|---|
| 1 | `git clone <PASTE-REPO-URL-HERE> && cd VIBE_CODE` | **NOT RUNNABLE — placeholder URL.** No publishable URL exists (known `[UPLOAD PENDING]`). Substituted read-only check: `git remote -v` → `origin https://github.com/athmabhiram1/Vibe-a-thon.git`. Note: README warns origin points at `pcb_designing.git` — **stale**, actual remote is `Vibe-a-thon.git`. `cd VIBE_CODE` n/a (already at root). |
| 2 | `pip install -r requirements.txt` | **PASS.** All 6 pins already satisfied (`fastapi 0.165.0`, `fastmcp 4.2.4`, `uvicorn 0.54.0`, `aiosqlite 0.22.1`, `pydantic 2.14.4`, `email-validator 2.2.0`). Matches README Verification pins. |
| 3 | `run.bat` | **PARTIAL — boot skipped (port conflict), probes PASS.** `HR candidates [200 0.053s]`, `IT breaches [200 0.044s]` (exact `curl` lines from `run.bat:29,32`). `where uvicorn` prerequisite satisfied. `run.bat` never 8008/8009/8000 — confirmed. |
| 4 | `start frontend.html` | **FAIL.** `Start-Process: The system cannot find the file specified.` Root has **zero** `.html` files. Nuance: `frontend.html` (781 lines) exists in `HEAD` but is **deleted in the working tree** (`git status: D frontend.html`, pre-existing — not caused by this run). |
| 5 | `python seed/validate.py` (bare, no flags) | **PASS.** `0 failure(s)` — breached=3 `[T-5001, T-5002, T-5019]`, on-call `support-night`→`SH-08/EMP-014`, SUB-01 +3d, KEY-01 295d stale. Bare invocation works (defaults to script's own dir). |

## Extended chain (boot → health → seed → validate → eval → smoke → frontend :3000)

| Step | Cmd / probe | Result |
|---|---|---|
| health | `GET /hr/candidates?limit=1`, `GET /it/tickets/breaches` | 200 / 200 (§cmd3). `GET /openapi.json` + `/docs` not probed (browsers cover it; `run.bat` doesn't probe them either). |
| seed (read) | `GET /hr/demo/status`, `GET /it/demo/status` | 200 both. **But README path is wrong**: bare `GET /demo/status` → `404 {"detail":"Not Found"}` on both. Real routes are `/hr/demo/*`, `/it/demo/*` (`hr.py:210,250,279`, `it.py:219,259,288`; routers carry `prefix="/hr"`, `"/it"`). Doc says `POST /demo/seed` — must be `POST /hr/demo/seed` (or `/it/...`). |
| seed (write) | `POST /hr|/it/demo/seed` + `/demo/reset` | **Deliberately NOT fired.** Live `seed/demo.db` holds a real convert (`employees=21`, EMP-021); a seed cycle would wipe it. Status shows `seeded:false, last_reset_ms:12.55 (IT), null (HR)`, `seeded_at: 2026-11-23` (stale vs live state). |
| validate `--db` | `python seed/validate.py --db seed/demo.db` | **1 failure (expected, live-drift):** `counts[employees]=21 want 20`. All other checks green incl. `equipment_holds` ledger pair CAND-002+CAND-005. Cause: live EMP-021 convert on top of seed (matches `eval/live_cases.json` L01). CSV-mode gate unaffected. |
| eval | `python eval/run.py` | **PASS, gate green:** guarded 97.5% (39/40 strict), block 96.8%, fp 0.0%, MOCK latencies labeled; M05 WARN-as-designed. Rewrote `eval/scorecard.csv` (see §7). |
| smoke | `python -m pytest tests/test_guards_smoke.py -q` | **PASS:** `11 passed in 0.03s`. |
| frontend :3000 | `GET /` | **200** — but it is **not** `frontend.html`. It's the Next.js dev app (`Onboard Copilot — Track 3`, `/console`, `/audit`) served from `workspace-25f2ad75-4340-469c-8a6d-0acc097f4f32/` (`npx next dev -p 3000`). Root README documents **only** `frontend.html` and never mentions `:3000`, the workspace dir, or `bun install`/`npx next dev`. |

## Other deviations found while running verbatim

1. `run.bat:12` says DBs are `hr_service/hr.db`, `it_service/it.db` — **neither file exists**. Canonical store is the single shared `seed/demo.db` (both services; `db.py` headers + router comments confirm). Also contradicts `.env.example` (`HR_DB_PATH`/`IT_DB_PATH`, which the code reads) vs `run.bat`.
2. `README Verification` claims `frontend.html` "exists (single-file UI…)" — false in this working tree (deleted; in HEAD only).
3. `run.bat:35` references `%NGROK_DOMAIN%` — env var undocumented anywhere in root README / `.env.example` (only `ngrok.yml` hints).
4. `eval/live_scorecard.csv` + `eval/live_run.py` exist but no doc points at them (judge path unclear; root README omits eval entirely — only `submission/README` badge mentions 97.5%).
5. First attempt at piping eval output through `tail` failed — Windows has no `tail`; cosmetic, my error, not a repo bug. (PowerShell `Select-Object -Last N` works.)

## Doc-fix list (exact patches needed, nothing applied)

1. `README.md` + `submission/README.md` quickstart cmd 1: replace `<PASTE-REPO-URL-HERE>` with real URL once published; until then mark the block `["UPLOAD PENDING" — clone manually]` so copy-paste visibly can't work.
2. Both READMEs: `git clone` note — origin currently `https://github.com/athmabhiram1/Vibe-a-thon.git`; remove/replace the stale `pcb_designing.git` warning.
3. Both READMEs seed/reset line: `POST /demo/seed` → `POST /hr/demo/seed` (or `/it/demo/seed`); same for `/demo/reset`, `GET /demo/status`. Prefix matters — bare path 404s.
4. `README.md` cmd 4: `start frontend.html` is dead in a fresh clone without that file present at root. Either restore `frontend.html` to the working tree (`git checkout -- frontend.html` — it's in HEAD) or rewrite cmd 4 as the Next.js path: `cd workspace-*/ && (bun install && bun run dev | npx next dev -p 3000)` → open `http://localhost:3000`. Pick ONE canonical UI; today two are implied and neither command works as written.
5. `run.bat:12` + README §3: `hr_service/hr.db / it_service/it.db` → `seed/demo.db` (single shared file). Document that live converts (EMP-021) make `--db` validation report `employees=21` — i.e. `--csv` is the CI gate, `--db` is parity-after-seed, and any live demo dirties it until `/demo/seed` re-runs.
6. Add to quickstart (or a `ports/env` table): frozen ports `8001 / 8002 / 3000`, `ALLOW_DEMO_SEED=true` + `x-demo-confirm: yes` requirement, `NGROK_DOMAIN` (or drop the ngrok line from `run.bat`), and the fact that `run.bat` spawns two new windows and must NOT be re-run while servers are up (port conflict; probe-only recovery).
7. `eval/run.py` rewrites `eval/scorecard.csv` **in place** with wall-clock latency jitter (this run's diff: verdicts identical 39/40, only `11.0x` decimals changed). Docs should direct reruns to `--out /tmp/...` (flag already exists) or git-ignore the artifact, else every judge rerun dirties the tree.
8. Root README `Verification` section: re-verify or reword — `frontend.html exists` is currently false in-tree; `submission/README` badge `39/40 0% FP MOCK` still matches this run (confirmed).

## Verdict

Golden path reproduces **except the UI step**: install ✓, boot/probes ✓ (on already-running backends), CSV gate ✓ (0 failures), eval ✓ (97.5%), smoke ✓ (11 passed), `:3000` ✓ (200, undocumented Next app). **Blockers for a fresh judge clone:** cmd 1 unpublishable URL, cmd 4 `frontend.html` missing from working tree, `/demo/*` paths 404 as documented (prefix omitted), `run.bat` DB filenames wrong. Live DB drift (`employees=21`) is by-design demo state, but no doc tells the judge that.
