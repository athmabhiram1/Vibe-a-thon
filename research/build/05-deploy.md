# 05 — Deploy Topology: Render vs Railway vs HF Docker vs Local Compose

> Source of truth for demo risk: `research/final/12-demo-risk.md` — cold start is the #1 killer (Render/Railway/HF sleep after ~15 min idle → 30–60s boot), Ollama default `num_ctx` silently truncates (pin 8192 for qwen2.5:7b), fallback ladder P0–P4 (Golden → Live → Local → Protocol → Lesson). This doc turns that into concrete topology, ports, health checks, and single-command up.

## 0. Topology at a glance

```
                    ┌──────────────┐
  Demo laptop ─────▶│ Cloud API    │──▶ P1 live path
   │                │ Render/Railw │     $API=https://<svc>.onrender.com
   │                │ ay/HF :7860  │
   │                └──────────────┘
   │                       │ cold-start? → pre-warm cron + P0 video covers gap
   │
   ├──▶ Local compose ────▶ api:8000 + ollama:11434 + inspector:6274  (P2/P3, --local)
   │         (docker compose up --build, hotspot-safe, zero egress)
   │
   └──▶ P0 golden.mp4 (always on USB + `demo/golden.mp4`, plays if all else dies)
```

**Decision table** (from 12 §1.4):

| Need | Pick | Why |
|---|---|---|
| Cheapest predictable live URL | **Render** ($7/mo Starter avoids sleep) | Fixed price, `render.yaml` blueprint, `healthCheckPath` |
| Postgres + Redis + worker in one project | **Railway** | 1-click DBs, private networking, `railway.json` |
| Model weights + API co-located / GPU story | **HF Spaces Docker** | `sdk: docker`, `app_port: 7860`, ZeroGPU narrative |
| Zero-network guarantee | **Local compose** (`--local`) | Ollama `demo-qwen-8k`, Inspector `--cli`, works on airplane Wi-Fi |

> Solo default: **Render (live URL) + local compose mirror**. Add Railway only if you need DB/worker; add HF only for weights/GPU story.

## 1. Service map, ports, health checks

| Service | Local port | Cloud port | Health endpoint | What "healthy" means |
|---|---|---|---|---|
| FastAPI (`api`) | `8000` | `$PORT` (Render/Railway dynamic) / `7860` (HF) | `GET /health` → `{"status":"ok","version":"x.y.z","servers":N}` + `GET /readyz` (DB/index loaded) | 200 in <2s warm; asserts `serverInfo.version` for surface_cache check (12 §5) |
| MCP endpoint | same as API | same | `POST /mcp` (JSON-RPC `tools/list`) | Valid `serverInfo.version`, no stdout pollution |
| Ollama | `11434` | n/a (local only) | `GET /api/ps` → `context_length==8192` | `ollama ps` CONTEXT=8192, PROCESSOR=100% GPU |
| Inspector | `6274`/`6275` | n/a | web UI + `--cli tools/list` | `tools/list` matches deployed schema |
| Postgres (Railway/local opt) | `5432` | private `DATABASE_URL` | `pg_isready` / `/readyz` | Migrations applied (`set -e` hook) |
| Swagger | `/docs` | `/docs` | 200 | Keep tab open = implicit warmer |

**Health handler contract** (implement once, use everywhere):
```python
@app.get("/health")
def health(): return {"status":"ok","version":APP_VERSION,"servers":len(registry)}
@app.get("/readyz")
def readyz():
    assert db_ok() and index_warmed()
    return {"ready": True, "version": APP_VERSION}
```
Bump `APP_VERSION`/`serverInfo.version` on every schema change → catches surface_cache drift (12 §5).

## 2. Platform recipes

### 2.1 Render (recommended live URL)

`render.yaml` blueprint:
```yaml
services:
  - type: web
    name: vibe-api
    runtime: python
    plan: starter        # $7/mo = no sleep; free sleeps after 15 min idle
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2"
    healthCheckPath: /health
    autoDeploy: true
    envVars:
      - key: APP_MODE
        value: cloud
      - key: DATABASE_URL
        fromDatabase:
          name: vibe-db
          property: connectionString
      - key: MODEL_URL
        sync: false      # set in dashboard, never in repo
databases:
  - name: vibe-db
    plan: free
```
Rules: bind `0.0.0.0` + `$PORT` (never `127.0.0.1:8000`); `main:app` path must match repo root (boot-crash #1); `uvicorn` in `requirements.txt` (#2). Secrets in Environment tab.

### 2.2 Railway (DB + worker topology)

`railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "startCommand": "hypercorn main:app --bind \":::$PORT\" --workers 2",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "numReplicas": 1
  }
}
```
Notes: Settings → Networking → Generate Domain (no public URL by default); keep `UVICORN_WORKERS=2` (0.5 GB Free OOMs otherwise); add deploy hook `set -e; alembic upgrade head`; ephemeral disk 1 GB free → attach Volume for persistence; expect peak-hour free-deploy bans + sleep (12 §1.2). Billing is per-second CPU/RAM — Render is cheaper for a static demo URL.

### 2.3 HF Spaces Docker (weights + API)

`README.md` frontmatter:
```yaml
---
sdk: docker
app_port: 7860
---
```
`Dockerfile.hf` (excerpt — full unified Dockerfile in §3):
```dockerfile
FROM python:3.11-slim
RUN useradd -m -u 1000 user
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV HF_HOME=/app/.cache PORT=7860
USER user
EXPOSE 7860
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","7860","--workers","1"]
```
Rules: non-root `USER user`, single foreground process, listen `0.0.0.0:7860` (not `127.0.0.1`); pre-download weights at build (`RUN python -c "from snapshot_download..."`) or first request pays download+load; every push rebuilds; Docker compute needs PRO on personal (12 §1.3).

### 2.4 Local Docker compose (hotspot / offline fallback, P2–P3)

Single-command up — this is the demo safety net:
```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
    environment:
      APP_MODE: local
      MODEL_URL: http://ollama:11434/v1
      MODEL_NAME: demo-qwen-8k
      DATABASE_URL: sqlite:///./demo.db
    depends_on: [ollama]
    healthcheck:
      test: ["CMD","curl","-f","http://localhost:8000/health"]
      interval: 10s
      retries: 5
  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: [ollama-data:/root/.ollama, ./Modelfile.local-qwen:/Modelfile:ro]
    environment:
      OLLAMA_CONTEXT_LENGTH: 8192
      OLLAMA_NUM_PARALLEL: 1
      OLLAMA_MAX_LOADED_MODELS: 1
volumes:
  ollama-data:
```
Unified `Dockerfile` (works Render + Railway + local; HF overrides CMD/port):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY . .
ENV PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=3 CMD curl -f http://localhost:${PORT:-8000}/health || exit 1
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
```
`Modelfile.local-qwen` (from 12 §3.2):
```
FROM qwen2.5:7b-instruct
PARAMETER num_ctx 8192
PARAMETER temperature 0.2
PARAMETER num_predict 2048
SYSTEM """You are a concise demo assistant. Answer from provided context only."""
```

## 3. Single-command up

```bash
# Live-cloud sanity (run night before + venue):
./scripts/up.sh cloud   # = pre-warm curl loop below + opens /docs

# Full local fallback (hotspot / airplane-safe):
docker compose up --build -d && \
  docker exec $(docker ps -q --filter "name=ollama") ollama create demo-qwen-8k -f /Modelfile 2>/dev/null; \
  curl -s localhost:8000/health && ollama ps
# One-flag app switch:  mycli --local --model demo-qwen-8k   (APP_MODE=local, MODEL_URL=http://127.0.0.1:11434/v1)
```
`scripts/up.sh`:
```bash
#!/usr/bin/env bash
set -e
MODE=${1:-local}
if [ "$MODE" = local ]; then docker compose up --build -d; sleep 5; curl -s localhost:8000/health; echo; ollama ps || true
else for i in 1 2 3; do curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" "$API/health"; sleep 5; done; xdg-open "$API/docs" 2>/dev/null || open "$API/docs" || true
fi
```

## 4. Cold-start mitigation

1. **Pay $7 to delete the problem** (Render Starter) if the demo matters. Free-tier sleep (~15 min idle → 30–60s boot) is the top demo killer (12 §1.1).
2. **Pre-warm ritual (T-1h + T-10min)**: keep `/docs` tab open (traffic prevents sleep) and loop:
```bash
# pre-warm curl — run 10 min before stage, leave running in Terminal 1
API=${API:-https://vibe-api.onrender.com}
for i in 1 2 3; do curl -s -w "\n[%{http_code} %{time_total}s]\n" $API/health; sleep 5; done
curl -s $API/readyz; echo
npx @modelcontextprotocol/inspector --cli $API/mcp --method tools/list --format json | head -c 500; echo
```
3. **Cron warmer** (free-tier only): GitHub Actions / UptimeRobot `GET $API/health` every 10 min during demo week. Note: Render honors traffic-based wake; Railway Serverless + HF rebuild on push still cold-boot — time them.
4. **Trim boot**: `--workers 1–2`, pre-downloaded weights (`HF_HOME` cache), lazy index load + `/readyz` gate, slim image (no torch-CUDA on API box; model lives in Ollama/HF).
5. **Stage choreography**: open with P0 `golden.mp4` playing *while* first live `curl` runs — audience sees motion during the 30s cold window (12 §7: P1→P0→P2).

## 5. Hotspot + network-death fallback

Assume venue Wi-Fi dies (12 §4). Rehearse this order:
1. `APP_MODE=local` flip: `mycli --local --model demo-qwen-8k`; Ollama pre-pulled night before (`ollama pull qwen2.5:7b && ollama create demo-qwen-8k -f Modelfile.local-qwen`).
2. Phone hotspot SSID/pass in clipboard; test `curl $API/health` over hotspot in rehearsal — captive portals break DNS, hotspot bypasses them.
3. Ports to confirm unblocked: `11434` (Ollama), `6274/6275` (Inspector), `8000` (local API). Carry `curl` equivalents for every Inspector click:
```bash
curl -s 127.0.0.1:11434/api/chat -d '{"model":"demo-qwen-8k","messages":[{"role":"user","content":"ping"}]}'
npx @modelcontextprotocol/inspector --cli ./server --method tools/list --format json
npx @modelcontextprotocol/inspector --cli ./server --method tools/call --tool-name <t> --tool-arg k=v --format json | jq .result
```
4. No auth-at-demo-time: static `Authorization: Bearer $TOKEN` from password manager; Inspector Server Settings pre-filled.
5. Drill: airplane-mode + hotspot-only run, reach P2 (local tool result on screen) in <90s; log seconds-to-fallback (12 §8 Drill A).

## 6. Verify matrix (copy into demo runbook)

- [ ] `curl $API/health` → 200 `{"status":"ok"}` warm <2s; note cold-boot seconds
- [ ] `curl $API/readyz` → `{"ready":true}` (DB/index loaded)
- [ ] `curl localhost:8000/health` (compose) → 200
- [ ] `ollama ps` → CONTEXT 8192, 100% GPU; `curl 127.0.0.1:11434/api/ps | jq .`
- [ ] `tools/list` live in Inspector Protocol tab matches `serverInfo.version` (surface_cache check)
- [ ] `docker compose up --build` from clean clone on hotspot only → tool result <90s
- [ ] P0 `demo/golden.mp4` on laptop + USB, <3 min, captioned

## 7. What to commit

`render.yaml` · `railway.json` · `Dockerfile` (+`Dockerfile.hf` if HF) · `docker-compose.yml` · `Modelfile.local-qwen` · `scripts/up.sh` · `scripts/prewarm.sh` · `.env.demo` (`MODEL_URL`/`APP_MODE` flip). Auto-deploy from `main` tested with trivial commit (12 §6 T-24h).
