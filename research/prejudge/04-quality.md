# 04 — Code-Quality Sweep (read-only, 2026-11-25)

Scope: `hr_service/`, `it_service/`, `seed/`, `eval/`, `tests/`, `reconcile/`, `scripts/`; TS/JS, ruff, prints, comments, constants drift (ports 8001/8002, operationIds), requirements pins. **No source edits made.**

## 1. TypeScript / ESLint — NOT APPLICABLE

| Check | Result | Severity |
|---|---|---|
| `npx tsc --noEmit` | **N/A — no `tsconfig.json` in workspace root; tsc prints help and exits 1.** Repo is Python-first (FastAPI); only TS/JS artifact is `submission/deck/pitch.html` (static slide deck, no TS). Error count by file: 0 (no project to check). | ⓘ Info |
| `npx eslint .` | **N/A — no `eslint.config.*` / `.eslintrc.*` in repo; ESLint v10 errors (exit 2, "couldn't find config").** Nothing to lint. If judges expect JS lint, add minimal flat config or drop the gate. | ⓘ Info |
| `pitch.html` debug leftovers | Grep `console.log\|debugger\|TODO` over `submission/deck/`: **0 matches.** | ✅ Pass |

## 2. Python lint (ruff) — 27 errors, all outside live services

`python -m ruff check hr_service it_service seed eval tests reconcile scripts` → **27 errors, 14 auto-fixable**. `black` is **not installed** (`No module named black`) so the plan's G1 "ruff+black" gate is half-unverifiable — either pin `black` in requirements or drop it from the gate.

| File | Count | Rules | Severity |
|---|---|---|---|
| `eval/run.py` | 12 | I001 imports; FURB167 ×5 `re.I` alias; SIM114 ×2; SIM102; RUF059 unused `br`; F541 empty f-string; C401 generator→set | 🟡 Low (eval harness only, not served) |
| `seed/validate.py` | 8 | F401 unused `timedelta`; DTZ007 naive `strptime`; S112 ×2 try-except-continue; BLE001 ×4 blind `except Exception` | 🟡 Low (dev/verify script; BLE001 worth a comment, not a judging risk) |
| `eval/live_run.py` | 3 | RUF100 stale `noqa: E402`; RUF059 ×2 unused `rr`, `st3` | 🟡 Low (one-line cleanups) |
| `seed/seed.py` | 2 | RUF100 stale `noqa`; F841 unused `prio_of` | 🟡 Low |
| `hr_service/routers/hr.py` | 1 | I001 import sort | 🟢 Trivial (single-line, `ruff --fix`) |
| `it_service/routers/it.py` | 1 | I001 import sort | 🟢 Trivial |
| `hr_service/main.py`, `it_service/main.py`, `live_moment.py`, `tests/`, `reconcile/`, `scripts/` | 0 | — | ✅ Pass |

`python -m compileall` over `hr_service it_service seed eval tests safety_check_server.py probe_live.py`: **exit 0, no syntax errors.**

Recommended fixes (report-only, not applied): run `ruff check --fix` (fixes 14: I001, FURB167, SIM114, F541, F401, RUF100); manually prefix `rr/st3/br` with `_`, drop `prio_of` or use it, add `logger.exception` or `BLE001` rationale comments in `validate.py`.

## 3. Debug leftovers / TODOs

| Check | Result | Severity |
|---|---|---|
| `print(` in **served code** (`hr_service/`, `it_service/`) | **0 matches.** Clean. | ✅ Pass |
| `console.log / pdb / breakpoint() / TODO / FIXME` in served code | **0 matches.** | ✅ Pass |
| `print(` elsewhere | ~40 hits, all legitimate CLI output: `seed/seed.py` + `seed/validate.py` (ok:/FAIL: diagnostics), `eval/run.py` + `eval/live_run.py` (metrics + `wrote …`), `probe_live.py`, `submission/deck/build_pdf.py`, `submission/assets/render-pngs.py`, docs `CLIENTS.md` (one-liner `python -c … print(…)` checks), `research/` snippets. No forgotten debug dumps. | ⓘ Info |
| `TODO/FIXME/XXX/HACK` | Only hits: `evidence/quota-log.md` template placeholders (`TODO/10`, `server_id=TODO`) and `research/ui/readiness.md` quoting its own denylist. No source TODOs. | 🟡 Low — `quota-log.md` still has unfilled TODOs; fill or mark `[UPLOAD PENDING]` before judging |
| `frontend.html` (README claims "exists") | **Missing** — no `frontend*` at root; only `submission/deck/pitch.html`. | 🟡 Low — doc drift; fix README line or restore file |

## 4. Commented-out blocks >5 lines

| Check | Result | Severity |
|---|---|---|
| Regex `^\s*#\s*(import\|from\|def \|class \|return\|app\.\|router\.\|@app)` repo-wide | 9 matches, **all in `research/build/*.md` docs** (2-line snippets max), none in `hr_service/`, `it_service/`, `seed/`, `eval/`, `tests/`. | ✅ Pass — no dead-code blocks in shippable code |

## 5. Duplicates / constants drift — ports, titles, operationIds

| Check | Result | Severity |
|---|---|---|
| Ports 8001/8002 | **Consistent everywhere.** `.env.example`, `.cursor/mcp.json`, `.vscode/mcp.json`, `claude_desktop_config.example.json`, `compose.opt.yml`, `run.bat`, `ngrok.yml`, `README.md`, `plan.md`, `docs/VENUE.md`, `eval/live_run.py` defaults, `hr_service/main.py` docstring (:8001), `it_service/main.py` (:8002) all agree: HR=8001, IT=8002. No 8008/8009/8000 stragglers. | ✅ Pass |
| FastAPI titles | `hr-directory` vs `ticketing-sla` — distinct, match README/submission docs. No drift. | ✅ Pass |
| operationIds (live `app.openapi()`) | HR 9: `hr_create_employee, hr_demo_reset, hr_demo_seed, hr_demo_status, hr_get_candidate, hr_get_oncall, hr_health_check, hr_list_candidates, hr_shift_calendar`. IT 11: `it_assign_laptop, it_create_ticket, it_demo_reset, it_demo_seed, it_demo_status, it_get_ticket, it_health_check, it_list_equipment, it_oncall_coverage, it_reroute_ticket, it_sla_breach_list`. **Zero overlap, zero intra-service dupes, zero missing.** Prefix discipline `hr_*`/`it_*` holds; `sla_breach_list` is namespaced as `it_sla_breach_list` (docs in `research/build/01` note bare-name history — resolved). | ✅ Pass |
| Demo routes in openapi | `hr_demo_*` / `it_demo_*` + health are included in schema (counted above). If Synapse allowlist excludes health/demo, that is by `--endpoints` selection, not schema drift — consistent with `docs/CLIENTS.md`. | ⓘ Info |

## 6. Requirements pins

| Check | Result | Severity |
|---|---|---|
| `fastapi` | `requirements-hr.txt` == `requirements-it.txt` == `requirements.txt`: **`fastapi==0.165.0`** ✓ | ✅ Pass |
| `fastmcp` | All three files: **`fastmcp==4.2.4`** ✓ | ✅ Pass |
| `uvicorn / aiosqlite / pydantic` | `uvicorn==0.54.0`, `aiosqlite==0.22.1`, `pydantic>=2.10,<3` identical across all three files ✓ | ✅ Pass |
| `email-validator` | In `requirements-it.txt` + root `requirements.txt` (`==2.2.0`), **absent from `requirements-hr.txt`** | ⓘ Info — intentional (IT-only dep) but root header says "combines" both; fine as-is, do not "fix" by adding to HR |
| Verdict | **No version drift.** Root `requirements.txt` is the union + verified PyPI comment. | ✅ Pass |

## 7. Fix list (priority order, none applied)

1. 🟢 `ruff check --fix` the 14 auto-fixable (import sorts, `re.I`→`re.IGNORECASE`, SIM114, F541, F401, stale `noqa`) — 2 min.
2. 🟡 Underscore-prefix `rr/st3/br`, remove or use `prio_of` (`seed/seed.py:228`) — 5 min.
3. 🟡 Decide `black`: install+pin or remove from G1 gate wording (`plan.md:143` says "ruff+black", black absent) — judging-hygiene risk, not functional.
4. 🟡 Fill `evidence/quota-log.md` TODOs or mark `[UPLOAD PENDING]`; fix README `frontend.html exists` claim.
5. ⓘ Consider adding `tsconfig.json`+`eslint.config.js` stubs or explicitly scoping quality gates to Python so a judge's `npx tsc/eslint` doesn't read as failure.
