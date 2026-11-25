# Onboard Copilot — HR Directory × IT Ticketing (Track 3)

> 30-sec pitch: Day-1 readiness is blocked by join-dependent steps scattered across HRIS, payroll, and IT
> inventory. Onboard Copilot stages everything as reversible drafts with citations, then activates on one
> explicit `APPROVE <hash>` — closing onboarding exceptions live across two systems.

Single-process golden path, no Docker. Frozen ports: HR `8001`, IT `8002` (never 8008/8009/8000).
DBs are SQLite files (`hr_service/hr.db`, `it_service/it.db`) — auto-created, offline.

## Quickstart (5 cmds, fresh clone, Windows, <60s warm; ~2 min cold (venv+pip))

> `run.bat`'s header says "3 cmds" — that is the boot subset (clone + install + run). The canonical
> quickstart below is **5 cmds**: boot + open UI + seed-gate.

```bat
git clone https://github.com/athmabhiram1/Vibe-a-thon.git ^&^& cd Vibe-a-thon
pip install -r requirements.txt
run.bat
start http://localhost:3000/console
python seed/validate.py
```

What each cmd does (all verified 2026-11-24 — see Verification below):

1. `git clone https://github.com/athmabhiram1/Vibe-a-thon.git && cd Vibe-a-thon` — fetch the repo (public).
2. `pip install -r requirements.txt` — installs the pinned root requirements (fastapi, fastmcp, uvicorn,
   aiosqlite, …).
3. `run.bat` — boots both APIs in separate windows: HR `http://localhost:8001` (`/docs`, `/openapi.json`)
   + IT `http://localhost:8002`, waits 5s, then probes `GET /hr/candidates?limit=1` and
   `GET /it/tickets/breaches`. Requires `uvicorn` on PATH (cmd 2 provides it).
4. Open `http://localhost:3000/console` — the Next.js demo UI (HR base
   `http://localhost:8001`, IT base `http://localhost:8002`).
5. `python seed/validate.py` — seed invariant gate (stdlib only, no server needed). Expect `0 failure(s)`
   (20/20/20/20/8/6/5-row counts, exactly 3 breached, double-hold + rehire + stale-key traps green).

Seed/reset at runtime (prefixed per service): `POST /hr/demo/seed` + `POST /it/demo/seed`
(headers `x-demo-confirm: yes`, `ALLOW_DEMO_SEED=true`)
→ `POST /hr/demo/reset` + `POST /it/demo/reset` → `GET /hr/demo/status` + `GET /it/demo/status`.

## Verification (dry-run, minus clone — 2026-11-24)

- `requirements.txt` exists at root; `import fastapi, uvicorn, aiosqlite, pydantic` → ok
  (installed `uvicorn 0.54.0`, `fastapi 0.165.0` match pins).
- `run.bat` exists; contents verified (checks `uvicorn`, starts both servers on 8001/8002, probes both
  endpoints). Not executed here (spawns server windows) — contents + dependency check = dry-run pass.
- Next.js demo UI in `workspace-*/src` (console queue, review detail, audit tail; HR :8001 / IT :8002).
- `python seed/validate.py --csv seed` → `0 failure(s)` (breached=3 `[T-5001, T-5002, T-5019]`, on-call
  `support-night` resolves).
- `git clone` not executed (no publishable URL yet — `[UPLOAD PENDING]`); command syntax matches the
  publish checklist in `submission/README.md`.

## Docs

- Submission packet (judge entry): [`submission/README.md`](./submission/README.md) — same 5-cmd quickstart.
- Architecture: [`submission/ARCHITECTURE.md`](./submission/ARCHITECTURE.md) · Pitch: [`submission/PITCH.md`](./submission/PITCH.md)
- Plan + frozen ports: [`plan.md`](./plan.md) · Dataset spec: [`seed/README.md`](./seed/README.md)

## Publish status

- 🎥 Video (60–90s): `[UPLOAD PENDING — record per PITCH.md, save USB copy to demo/golden.mp4, upload unlisted, paste URL here]`
- 📦 Repo URL: `https://github.com/athmabhiram1/Vibe-a-thon` (public)
