# 16 — FINAL SIGN-OFF (critic, read-only, 2026-11-24)

**Scope read:** `01-oracle-kill.md` (5 kills) + `10-verdict.md` + `02,03,04,05,06,07,08,09` + live ground truth (`hr_service/routers/hr.py`, `eval/run.py`, `safety_check_server.py`, `submission/*`, `evidence/quota-log.md`, `.env`, root listing). **Requested files `12,13,14,15` do not exist** in `research/verify-final/` (only `01–10` present) — nothing to verify there. `frontend.html` does not exist repo-wide (root listing + `**/frontend*.html` = zero hits). No cheerleading.

## Oracle 5 kills — re-adjudicated against current disk state

| # | Kill | Status | Proof |
|---|---|---|---|
| K1 | 96.8% rigged mock | **PARTIAL** | Fixed in honesty, not in substance. `eval/run.py:1-10` now discloses "regex-over-JSON policy demo, NOT the shipped artifact; +11.0ms SIMULATED"; `guarded()` no longer branches on `expected_verdict`/IDs (only scoring at `run.py:127` reads labels — legitimate); baseline is now a weak single-signal comparator (`run.py:97-114`), README claims "29.0% block (weak-by-design… not 0% tautology)" + "97.5% MOCK". Remaining: still regex over JSON, still `category=="ambiguous_scope"` metadata branch (`run.py:86`), still simulated latency, still never calls `safety_check_server.onboard`. Judge grep-kill is blunted by disclosure; substance kill stands. |
| K2 | Zero Synapse artifacts | **PARTIAL** (was OPEN) | Key now staged (`.env:10` has a live `syn-api-…` key — see security note), but **zero builds**: no `.synapse/`, no `surface_cache.json`, no `synapse_auto_server.py`, `quota-log.md:20-22` still all-TODO, `.cursor/mcp.json:5` + `.vscode/mcp.json:6` still point at the missing file. Counts corrected in prose (README: "12 hand-curated, CI asserts 12 functional (14 with health)"), but no server IDs to paste, no `discover` median. |
| K3 | `/demo/*` missing | **CLOSED (code)** | Routes now exist: `hr.py:209-307` (`hr_demo_seed/reset/status` with `ALLOW_DEMO_SEED` + `x-demo-confirm` guard, snapshot restore, timing envelope); `it.py:219+` mirrors. Root `requirements.txt` now exists, `.env` documents `HR_DB_PATH/IT_DB_PATH` (env-mismatch fixed), `.gitignore` exists. Caveat: `03-seed.md:48-51` 404 probe predates the implementation — live re-probe still owed (fix F5). Shared single `seed/demo.db` is now explicit/intentional. |
| K4 | Discover 404 moment | **PARTIAL** | Old 404 path retired: `hr_get_oncall` is now live (`hr.py:188-206`, `db.py:190`), not commented. But the live beat was redefined (README: "add `GET /it/oncall-coverage` (L1) → `--discover`") and **L1 does not exist**; no `discover` rehearsal, no `golden.mp4` (`demo/` = `SHOTLIST.md` only), tool-count prose disagrees with quota-log ("12/14" vs "13 baseline/14"). Choreography still unperformed. |
| K5 | Two write paths, safety theater | **PARTIAL** | Core wiring fixed: `safety_check_server.py:856` now POSTs real `/hr/employees` inside the ledger boundary and stores REAL IDs (`:608,915`); ledger PK fencing + idempotency-conflict path present (`:555-571,809-823`). Remaining nits: file-lock audit under multi-worker, APPROVE-token naming, Class-C double-approval — hardening, not fraud. |

## Demo-critic (08) kill-list — re-adjudicated

| # | Kill | Status |
|---|---|---|
| K1 | `demo/golden.mp4` missing | **OPEN** — `demo/` has only `SHOTLIST.md`; README still `TODO_YOUTUBE_URL`; zero `*.mp4` repo-wide. P0 rung absent; escalation ladder drops to P4. |
| K2 | Packet TODO shell | **OPEN** — `BENCHMARKS.md` all `TODO_s/ms/GB`, `LIMITS.md` all `TODO`, no `submission/benchmark/run.js`, no `assets/quota-proof/`, no `deck/pitch.pdf`. README honesty lines improved (97.5% MOCK, tool counts) but no measured numbers. |
| K3 | `frontend.html` missing | **OPEN** — absent repo-wide; spec + acceptance checklist (06) untouched. |
| K4 | Zero Synapse builds rehearsed | **OPEN** — no `.synapse/`, quota-log all-TODO; T3/T8 unevaluable. Key staged only. |
| K5 | Script ID drift | **OPEN** — `03-demo-look.md` still stages CAND-1147/LT-4420/T-551 while seed/PITCH/srt use CAND-002/LT-1005/T-5001. 15-min grep fix, still undone. |
| K6 | Physical layer | **OPEN** (unverifiable from repo; assume absent). |
| K7 | Minor tripwires | **OPEN** — `TODO_GITHUB_URL`/`TODO_YOUTUBE_URL` remain; "5 cmds" vs `run.bat` "3 cmds" conflict remains; breach-count time-drift from 02 (`/breaches` returns 14, not 3, on 11-24 wall-clock) unpinned. |

## Verdict: NO-GO

Code honesty improved (demo routes built, eval disclosed, safety wired to real HR, env/requirements fixed), but **nothing a judge sees on stage exists**: no Synapse servers, no frontend, no video, no measured packet numbers, no deck PDF, no quota proof. Shipping now = failing the four beats in 10-verdict §1. This is a 1–2 day gap, not a 160-min gap.

## Fix list (≤5, in order)

1. **Synapse session (60–90 min):** install CLI → `synapse info` (log before/after) → baseline builds → `discover` ×5 medians → log server IDs + tools into `quota-log.md`; fix client configs to real runner/file. Unblocks K2/K4, T3/T8.
2. **Record P0 (90 min):** 3 takes per SHOTLIST → `demo/golden.mp4` + USB ×2 + unlisted YouTube → replace `TODO_YOUTUBE_URL`; export `deck/pitch.pdf`.
3. **Frontend decision (10 min decide, then 60–180 min):** either build minimal `frontend.html` per 06/FIX-A, or descope to terminal-only and rewrite §2/PITCH/C3 references. No half-built page on stage.
4. **Packet numbers (60 min):** write 20-line `benchmark/run.js`, fill cold-start/p50/p95/TTFT/VRAM tables, 2 phone photos (`synapse info`, billing ₹0) into `assets/quota-proof/`, replace `TODO_GITHUB_URL`, unify all scripts on canonical IDs (CAND-002/LT-1005/T-5001).
5. **Live re-probe + hygiene (30 min):** boot :8001/:8002, curl `/demo/seed|reset|status`, pin breach-count clock (02 FAIL: 14 vs 3), O'Brien POST round-trip; **rotate the live `SYNAPSE_API_KEY` now in `.env` and never publish `.env`** (working tree holds a real key).

## Single next command

```bash
synapse --version || npm install -g @2ndbrainlabs-ai/synapse-cli; synapse info 2>&1 | tee -a evidence/quota-log.md
```

If this errors (no key/network), execute F1-keyless (`synapse model set ollama` → `synapse build --local`) before writing any more app code.
