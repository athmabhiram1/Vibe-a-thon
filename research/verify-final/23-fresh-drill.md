# 23 — Fresh-Install Drill (judge-rerun simulation, no working-tree mutation)

**Date (UTC):** 2026-11-24 · **Workdir:** `C:\Users\athma\OneDrive\Desktop\my projects\VIBE_CODE`
**Method:** temp venv (`%TEMP%\opencode\fresh-drill-venv`), `pip install -r requirements.txt` from scratch,
fresh-venv imports, `seed/validate.py --csv`, `eval/run.py --out <temp>`, boot both services on **ALT ports
8101/8102** (frozen 8001/8002 left alone), read-only GET probes only (no POSTs), temp venv deleted after.
**DB discipline:** `validate --csv` mode only; live probes were GETs; `seed/demo.db` mtime `21:58:49` predates
the drill (`22:44`+) → not written by this drill. `eval/scorecard.csv` untouched (our run wrote to a temp
`--out`, deleted after). No repo files created/modified.

## Timings (measured, this machine, Python 3.11.0, cold download)

| Step | Result | Seconds |
|---|---|---|
| `python -m venv` (fresh, empty) | ok | **21.5** |
| `pip install -r requirements.txt` (cold, from scratch) | ok, all pins resolve | **79.5** |
| `import hr_service.main + it_service.main` (fresh venv) | `hr-directory` / `ticketing-sla` | **0.7** |
| `seed/validate.py --csv seed` | **0 failures** (breached=3 `[T-5001,T-5002,T-5019]`, on-call `support-night` resolves) | **0.1** |
| `eval/run.py --out <temp>` | 39/40, guarded 96.8% block / 0% FP, gates PASS, exit 0 | **0.1** |
| boot HR :8101 + IT :8102 (parallel) + health probes | both `{"ok":true}` | **7.1** |
| **Cold total (venv + install + import + validate + eval + boot)** | | **≈109** |

## Fix confirmations (vs prior lanes)

1. **`fastapi==0.165.0` EXISTS — hygiene doubt closed.** Cold `pip install` resolved every pin
   (`fastapi 0.165.0`, `fastmcp 4.2.4`, `uvicorn 0.54.0`, `aiosqlite 0.22.1`). `research/verify-final/09-hygiene.md`
   §1 "may not exist" is answered: it installs clean. (Venv pip was bundled 22.3 with an upgrade notice —
   install still succeeded; consider `pip install -U pip` in the quickstart.)
2. **Root `requirements.txt` EXISTS** — the 09-hygiene "SHIP-BLOCKER" (missing file) is fixed.
3. **`/demo/*` routes EXIST** — the 01-oracle-kill KILL-3 ("no POST /demo/seed|reset") is fixed:
   HR openapi = 9 ops incl `hr_demo_seed/reset/status` + `hr_get_oncall` (H5 live);
   IT openapi = 11 ops incl `it_demo_seed/reset/status` + `it_oncall_coverage` (L1 live).
4. **Live breach count = 3** (ALT-port probe), matching `validate.py` — the 02-boot 14-breach wall-clock
   drift appears fixed.

## Verdict on the quickstart claim — CONDITIONAL FAIL (wording, not function)

- `run.bat` "3 cmds, <60s **warm**" and `submission/README.md` "5 cmds, fresh clone, <60s" conflate two
  regimes. Measured: **true cold fresh-clone ≈ 109s** (`pip install` alone 79.5s + venv 21.5s on this
  network/machine) — the **<60s claim FAILS cold**. Everything after install (import + validate + eval +
  boot) totals **<8s**, so the claim PASSES warm (cached wheels/site-packages).
- Nothing is broken — every step exited 0. The defect is the unqualified "<60s" on a fresh-clone path
  whose dominant cost (venv + wheel download) the repo does not control.
- **Fix (docs only, ~5 min):** qualify the claim — "<60s warm (cached deps); ~2 min cold first install",
  and add `python -m pip install -U pip` before the requirements line. Then the card is honest and
  the drill passes as-written.

## Cleanup

Temp venv + temp scorecard deleted (`Test-Path fresh-drill-venv` = False). ALT-port servers killed,
ports closed. No repo mutations.
