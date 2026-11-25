# 27 — Step Deploy: Both APIs to Render / Railway (Exact Clicks + CLI)

> Sources: `research/build/05-deploy.md` (topology, cold-start, pre-warm) · `research/build/01-architecture.md` (ports 8001/8002 frozen, env table) · `research/build/02-api-design.md` (health contract, `/health` + `/readyz`).
> Goal: two live public URLs — HR (`hr-directory`) + IT (`ticketing-sla`) — that Synapse hosted runners can forward to. Time: ~30 min first time, ~5 min repeat.
> Solo default: **Render (live URL) + local compose mirror**. Add Railway only if you need Postgres/worker.

---

## 0. What "both APIs" means on cloud

| # | Local | Cloud equivalent | Health | Notes |
|---|---|---|---|---|
| HR `hr-directory` | `http://localhost:8001` (`hr_service/main.py:app`) | Service 1 → e.g. `https://vibe-hr.onrender.com` | `GET /health` + `GET /readyz` | prefix `/hr`, SQLite file `hr.db` |
| IT `ticketing-sla` | `http://localhost:8002` (`it_service/main.py:app`) | Service 2 → e.g. `https://vibe-it.onrender.com` | `GET /health` + `GET /readyz` | prefix `/it`, SQLite file `it.db` |

Synapse hosted runners then point at cloud (demo mode):

```bash
# after deploy, Synapse forwards to LIVE instead of localhost
ENDPOINT_BASE_URL=https://vibe-hr.onrender.com  # hr-api runner env
ENDPOINT_BASE_URL=https://vibe-it.onrender.com  # it-api runner env
```

> Two FastAPIs = **two web services** on Render/Railway. Do NOT merge into one process — operation_ids (`hr_*` / `it_*`) and `--server-name hr-api / it-api` assume two base URLs (`01 §4`).

---

## 1. Pre-flight (5 min, do once — fixes 90% of boot crashes)

### 1.1 Health endpoints (must exist in BOTH `main.py` files)

Copy-paste contract from `05 §1`. Replace the toy `{"ok": True}` health with this:

```python
# hr_service/main.py  (mirror in it_service/main.py with title="ticketing-sla")
from fastapi import FastAPI
from hr_service.routers.hr import router as hr_router

APP_VERSION = "1.0.0"  # bump on every schema change -> catches surface_cache drift
app = FastAPI(title="hr-directory")

@app.get("/health", operation_id="hr_health_check", summary="Liveness probe")
def health():
    return {"status": "ok", "version": APP_VERSION, "servers": 1}

@app.get("/readyz", operation_id="hr_ready_check", summary="Readiness gate")
def readyz():
    # assert db_ok() and index_warmed(); for SQLite demo: try a 1-row select
    return {"ready": True, "version": APP_VERSION}

app.include_router(hr_router)  # must precede any Synapse/MCP mount
# start: uvicorn hr_service.main:app --host 0.0.0.0 --port ${PORT:-8001}
```

Verify locally:

```powershell
uvicorn hr_service.main:app --port 8001 &
uvicorn it_service.main:app --port 8002 &
curl.exe -s http://localhost:8001/health  # -> {"status":"ok","version":"1.0.0",...}
curl.exe -s http://localhost:8001/readyz  # -> {"ready":true,...}
curl.exe -s http://localhost:8002/health
curl.exe -s http://localhost:8002/readyz
```

### 1.2 `$PORT` binding (boot-crash #1 on Render/Railway)

- Both platforms inject a **dynamic `$PORT`** (e.g. `10000`). Never hardcode `8001`/`8002` in `startCommand`.
- Never bind `127.0.0.1` on cloud — must be `0.0.0.0`.
- `main:app` import path must match repo root (boot-crash #2). If `hr_service/main.py` is at repo root, the module is `hr_service.main:app`, NOT `main:app`.

Correct patterns:

```bash
# Render starter (single service example — repeat per API):
uvicorn hr_service.main:app --host 0.0.0.0 --port $PORT --workers 1
uvicorn it_service.main:app --host 0.0.0.0 --port $PORT --workers 1
# Railway alt (hypercorn handles Railway's :::PORT form):
hypercorn it_service.main:app --bind "0.0.0.0:$PORT" --workers 1
```

### 1.3 Env vars (set in dashboard, never in repo)

| Var | HR service value | IT service value | Consumed by |
|---|---|---|---|
| `APP_MODE` | `cloud` | `cloud` | app switch (`--local` flips to `local`) |
| `DATABASE_URL` | `sqlite:///./hr.db` (or Render Postgres `fromDatabase`) | `sqlite:///./it.db` | each FastAPI |
| `HR_BASE_URL` / `IT_BASE_URL` | `https://vibe-hr.onrender.com` | `https://vibe-it.onrender.com` | agent joins, Custom safety tool |
| `MODEL_URL` | *(leave empty on API box; model lives in Ollama/HF)* | same | — |
| Secrets (`SYNAPSE_*`, tokens) | **dashboard only**, `sync: false` | same | runner |

Commit `.env.example` with placeholder names only — never real tokens.

### 1.4 `requirements.txt` sanity

```bash
pip freeze | findstr /i "fastapi uvicorn pydantic email-validator"
# must contain: fastapi, uvicorn[standard], pydantic, email-validator
# if missing: pip install fastapi "uvicorn[standard]" pydantic email-validator && pip freeze > requirements.txt
```

---

## 2. Option A — Render (recommended live URL, $7/mo kills sleep)

Why Render first: fixed price, `render.yaml` blueprint, `healthCheckPath`, cheapest predictable demo URL (`05 §2.1`).

### 2.1 `render.yaml` — both APIs (commit at repo root)

```yaml
# render.yaml — Track 3 final: 2 web services (HR + IT)
services:
  - type: web
    name: vibe-hr
    runtime: python
    plan: starter        # $7/mo = no sleep; free sleeps after ~15 min idle -> 30-60s boot
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn hr_service.main:app --host 0.0.0.0 --port $PORT --workers 1"
    healthCheckPath: /health
    autoDeploy: true
    envVars:
      - key: APP_MODE
        value: cloud
      - key: DATABASE_URL
        value: sqlite:///./hr.db
      # - key: DATABASE_URL           # Postgres variant (optional):
      #   fromDatabase:
      #     name: vibe-db
      #     property: connectionString

  - type: web
    name: vibe-it
    runtime: python
    plan: starter
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn it_service.main:app --host 0.0.0.0 --port $PORT --workers 1"
    healthCheckPath: /health
    autoDeploy: true
    envVars:
      - key: APP_MODE
        value: cloud
      - key: DATABASE_URL
        value: sqlite:///./it.db

# Optional shared Postgres (only if you outgrow SQLite):
# databases:
#   - name: vibe-db
#     plan: free
```

> `--workers 1` on Starter (512 MB). Use `--workers 2` only on Standard+. Slim image: no torch-CUDA on API box.

### 2.2 Exact clicks — Render dashboard (Blueprint flow)

1. Push `render.yaml` to GitHub `main`: `git add render.yaml hr_service it_service requirements.txt && git commit -m "deploy: render blueprint both APIs" && git push`.
2. Go to **https://dashboard.render.com** → **New +** → **Blueprint** → connect your GitHub repo → select repo.
3. Render previews **2 services**: `vibe-hr` + `vibe-it` → click **Apply**.
4. For EACH service → **Environment** tab → add (if not in yaml):
   - `APP_MODE=cloud`, `DATABASE_URL=sqlite:///./hr.db` (HR) / `sqlite:///./it.db` (IT).
   - Any secret (`MODEL_URL`, tokens) → **Add Environment Variable**, never commit.
5. **Settings** → confirm **Health Check Path = `/health`**, **Auto-Deploy = Yes**.
6. Free-tier only: note **Sleep** behavior — free sleeps after ~15 min idle. Starter ($7/mo/service) = no sleep. **Pay $7 to delete the problem if the demo matters** (`05 §4.1`).
7. Wait for **Live** (green) on both → copy URLs:
   - `https://vibe-hr.onrender.com`, `https://vibe-it.onrender.com` (yours will differ).

### 2.3 Exact CLI — Render (alternative / CI)

```bash
# Render has no official deploy CLI; blueprint-via-git is the path.
# Install community CLI only if you want log tailing:
npm i -g render-cli  # community; dashboard remains source of truth
# Deploy = git push (autoDeploy:true):
git push origin main
# Then verify (see §4 pre-warm loop):
API=https://vibe-hr.onrender.com; curl -s -w "\n[%{http_code} %{time_total}s]\n" $API/health
API=https://vibe-it.onrender.com; curl -s -w "\n[%{http_code} %{time_total}s]\n" $API/health
```

### 2.4 Render gotchas

- `$PORT` is injected — your `startCommand` must reference `$PORT`, not `8001`.
- `main:app` path mismatch = instant crash loop. Test locally with `$PORT` set: `PORT=10000 uvicorn hr_service.main:app --host 0.0.0.0 --port $PORT`.
- Every push rebuilds. Time pushes, don't push mid-demo.

---

## 3. Option B — Railway (DB + worker topology)

When to pick Railway over Render: you want Postgres + Redis + worker in one project with private networking (`05 §2.2`). Billing is per-second CPU/RAM — Render is cheaper for a static demo URL.

### 3.1 `railway.json` — one per service (repo root, or per-service dir)

Railway deploys **one service per `railway.json`**. With a monorepo (HR + IT folders), create two Railway services pointing at the same repo with different `startCommand`s:

```json
// railway.json — HR service (duplicate for IT with it_service.main:app)
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "startCommand": "uvicorn hr_service.main:app --host 0.0.0.0 --port $PORT --workers 1",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "numReplicas": 1
  }
}
```

IT variant: same file with `"startCommand": "uvicorn it_service.main:app --host 0.0.0.0 --port $PORT --workers 1"`.

`Dockerfile` (unified — works Render + Railway + local; from `05 §2.4`):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY . .
ENV PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=3 CMD curl -f http://localhost:${PORT:-8000}/health || exit 1
CMD ["sh","-c","uvicorn hr_service.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
# IT service overrides CMD/startCommand to it_service.main:app
```

### 3.2 Exact clicks — Railway dashboard

1. Go to **https://railway.app** → **New Project** → **Deploy from GitHub repo** → select repo.
2. Service 1 (HR): **New Service → GitHub Repo** (same repo) → **Settings → Build** → confirm Builder = `DOCKERFILE`, Dockerfile Path = `Dockerfile`.
3. **Settings → Deploy** → Start Command = `uvicorn hr_service.main:app --host 0.0.0.0 --port $PORT --workers 1` → Health Check Path = `/health`, Timeout = `30`, Restart Policy = `ON_FAILURE`.
4. **Settings → Networking → Generate Domain** (no public URL by default — you must click this). Copy HR URL.
5. **Variables** tab → add `APP_MODE=cloud`, `DATABASE_URL=sqlite:///./hr.db` (or **New → Database → Postgres** → reference `${{Postgres.DATABASE_URL}}` as `DATABASE_URL`, add deploy hook `set -e; alembic upgrade head` if using migrations).
6. Repeat steps 2–5 for Service 2 (IT) with `it_service.main:app` + `it.db`. Two services = two domains.
7. **Volumes** (free ephemeral disk is 1 GB): **New → Volume** → mount for persistence if you need SQLite to survive restarts; otherwise Postgres.
8. Keep `WORKERS=1` on ≤0.5 GB (OOMs otherwise). Expect peak-hour free-deploy bans + sleep.

### 3.3 Exact CLI — Railway

```bash
npm i -g @railway/cli
railway login
railway init            # link repo -> project (or railway link <project-id>)
# Service 1 (HR):
railway up --service vibe-hr
railway variables --service vibe-hr --set "APP_MODE=cloud" --set "DATABASE_URL=sqlite:///./hr.db"
railway domain --service vibe-hr   # generates public URL; copy it
# Service 2 (IT):
railway up --service vibe-it
railway variables --service vibe-it --set "APP_MODE=cloud" --set "DATABASE_URL=sqlite:///./it.db"
railway domain --service vibe-it
railway logs --service vibe-hr     # tail boot; look for "Uvicorn running on 0.0.0.0:$PORT"
railway logs --service vibe-it
```

---

## 4. Cold-start 30–60s handling (the #1 demo killer)

Free tiers (Render Free, Railway Serverless/Hobby-idle, HF) **sleep after ~15 min idle → first request pays 30–60s boot** (`05 §4`, `final/12-demo-risk.md`).

### 4.1 Pre-warm loop (run T-60min AND T-10min, leave running in Terminal 1)

```bash
# Bash:
HR=${HR:-https://vibe-hr.onrender.com}
IT=${IT:-https://vibe-it.onrender.com}
for i in 1 2 3; do
  echo "--- HR pass $i ---"; curl -s -w "\n[%{http_code} %{time_total}s]\n" $HR/health; sleep 5
  echo "--- IT pass $i ---"; curl -s -w "\n[%{http_code} %{time_total}s]\n" $IT/health; sleep 5
done
curl -s $HR/readyz; echo
curl -s $IT/readyz; echo
```

```powershell
# PowerShell equivalent:
$HR="https://vibe-hr.onrender.com"; $IT="https://vibe-it.onrender.com"
1..3 | % { Write-Host "--- HR pass $_ ---"; curl.exe -s -w "`n[%{http_code} %{time_total}s]`n" "$HR/health"; Start-Sleep 5 }
1..3 | % { Write-Host "--- IT pass $_ ---"; curl.exe -s -w "`n[%{http_code} %{time_total}s]`n" "$IT/health"; Start-Sleep 5 }
curl.exe -s "$HR/readyz"; echo ""; curl.exe -s "$IT/readyz"; echo ""
```

Keep a **`/docs` tab open per API** in the browser — traffic prevents sleep. First curl of the day WILL be slow (note cold-boot seconds); passes 2–3 must be **200 in <2s warm**.

`scripts/prewarm.sh` (commit this):

```bash
#!/usr/bin/env bash
set -e
HR=${HR:-https://vibe-hr.onrender.com}
IT=${IT:-https://vibe-it.onrender.com}
for i in 1 2 3; do curl -s -o /dev/null -w "hr %{http_code} %{time_total}s\n" "$HR/health"; sleep 5; done
for i in 1 2 3; do curl -s -o /dev/null -w "it %{http_code} %{time_total}s\n" "$IT/health"; sleep 5; done
curl -s "$HR/readyz"; echo; curl -s "$IT/readyz"; echo
```

### 4.2 Cron warmer (free-tier only, demo week)

- **UptimeRobot**: https://uptimerobot.com → Add Monitor → HTTP(s) → URL = `$HR/health` + second monitor for `$IT/health` → interval **5 min** (or 10 min).
- Or **GitHub Actions** (`.github/workflows/warm.yml`):

```yaml
name: warm
on:
  schedule: [{ cron: "*/10 * * * *" }]  # every 10 min during demo week; disable after
  workflow_dispatch: {}
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - run: |
          curl -fsS -o /dev/null -w "hr %{http_code} %{time_total}s\n" "${{ secrets.HR_URL }}/health" || true
          curl -fsS -o /dev/null -w "it %{http_code} %{time_total}s\n" "${{ secrets.IT_URL }}/health" || true
```

> Note: Render honors traffic-based wake; Railway Serverless + HF rebuild-on-push still cold-boot — time them. Cron reduces but does not eliminate cold starts.

### 4.3 Trim boot (do before demo day)

1. `--workers 1` (Starter / 512 MB), max 2 on bigger plans.
2. Lazy index/seed load + `/readyz` gate (return 200 `/health` fast, heavy load behind `/readyz`).
3. Pre-download anything heavy at **build** time, not first request.
4. Slim image: no torch-CUDA on API box.

### 4.4 Stage choreography (when cold-start hits live anyway)

Open with **P0 `golden.mp4` playing WHILE the first live `curl` runs** — audience sees motion during the 30s cold window (`05 §4.5`: P1→P0→P2). Script line: *"That's a cold container waking up — about 30 seconds on free tier; the recording covers the gap."* Never stare at a spinner.

---

## 5. Post-deploy verification (copy into demo runbook)

```bash
HR=https://vibe-hr.onrender.com
IT=https://vibe-it.onrender.com

# 1. Liveness (warm <2s; note first-boot seconds separately)
curl -s -w "\n[%{http_code} %{time_total}s]\n" $HR/health   # -> {"status":"ok","version":"1.0.0"}
curl -s -w "\n[%{http_code} %{time_total}s]\n" $IT/health

# 2. Readiness (DB/seed loaded)
curl -s $HR/readyz  # -> {"ready":true}
curl -s $IT/readyz

# 3. Real data (proves seed survived deploy)
curl -s "$HR/hr/candidates?limit=1" | head -c 300; echo
curl -s "$IT/it/tickets/breaches" | python -c "import json,sys; d=json.load(sys.stdin); print('breaches:', [t['ticket_id'] for t in d])"

# 4. Swagger up (keep tabs open = implicit warmer)
# $HR/docs  and  $IT/docs  -> 200

# 5. Point Synapse runners at cloud, re-verify tools/list
ENDPOINT_BASE_URL=$HR npx -y @modelcontextprotocol/inspector --cli $HR/mcp --method tools/list --format json | head -c 500; echo
```

`- [ ]` `curl $HR/health` → 200 warm <2s (cold-boot seconds noted: ___s)
`- [ ]` `curl $IT/health` → 200 warm <2s (cold-boot seconds noted: ___s)
`- [ ]` both `/readyz` → `{"ready":true}`
`- [ ]` breaches list = 3 (T-551, T-552, T-553)
`- [ ]` both `/docs` tabs open
`- [ ]` trivial-commit auto-deploy tested (`echo # touch >> README && git push`, both services rebuild green)

---

## 6. What to commit (checklist)

- [ ] `render.yaml` (2 services, `healthCheckPath: /health`, `$PORT`, `--workers 1`)
- [ ] `railway.json` (+ IT variant / second service config) + unified `Dockerfile`
- [ ] Both `main.py` with `/health` + `/readyz` + `APP_VERSION`
- [ ] `scripts/prewarm.sh` (+ `scripts/up.sh` from `05 §3`)
- [ ] `.env.example` (placeholder names only) + `.github/workflows/warm.yml` (demo-week only)
- [ ] Auto-deploy from `main` tested with trivial commit

*Next: point `ENDPOINT_BASE_URL` at cloud URLs → `synapse build --auto --endpoints "<allowlist>"` → Inspector `tools/list` (expect 13 baseline, 14 post-L1) → rehearse P0→P1→P2 fallback drill.*
