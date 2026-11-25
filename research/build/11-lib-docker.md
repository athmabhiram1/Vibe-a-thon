# 11 — Docker Library: 2× FastAPI + Postgres + Redis + Ollama

> One-command local/prod-parity stack. Copy-paste ready. Hot-spare laptop clone in <60s.

## 0. Layout

```
app/
  compose.yaml
  .env.example
  .dockerignore
  services/
    api1/
      Dockerfile
      requirements.txt
      app/main.py
    api2/
      Dockerfile
      requirements.txt
      app/main.py
  infra/
    postgres/init.sql        # optional
    caddy/Caddyfile          # only if federating / TLS
volumes: pgdata, redisdata, ollama (managed by Docker)
```

## 1. `compose.yaml` (premade, full)

```yaml
name: vibe-code

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-app}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set in .env}
      POSTGRES_DB: ${POSTGRES_DB:-app}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER:-app} -d $${POSTGRES_DB:-app}"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: ["redis-server", "--appendonly", "yes", "--save", "60", "1"]
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 5s

  ollama:
    image: ollama/ollama:0.6.8
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    # No built-in HEALTHCHECK in upstream image — define one:
    healthcheck:
      test: ["CMD", "sh", "-c", "ollama list >/dev/null 2>&1 || wget -qO- http://localhost:11434/api/tags >/dev/null"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 20s
    # GPU: uncomment for NVIDIA (needs nvidia-container-toolkit)
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

  api1:
    build: ./services/api1
    restart: unless-stopped
    ports:
      - "8001:8000"
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      ollama: { condition: service_healthy }
    environment:
      SERVICE_NAME: api1
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-app}:${POSTGRES_PASSWORD:?set in .env}@postgres:5432/${POSTGRES_DB:-app}
      REDIS_URL: redis://redis:6379/0
      OLLAMA_URL: http://ollama:11434
      OLLAMA_MODEL: ${OLLAMA_MODEL:-llama3.1:8b}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 15s

  api2:
    build: ./services/api2
    restart: unless-stopped
    ports:
      - "8002:8000"
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      ollama: { condition: service_healthy }
    environment:
      SERVICE_NAME: api2
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-app}:${POSTGRES_PASSWORD:?set in .env}@postgres:5432/${POSTGRES_DB:-app}
      REDIS_URL: redis://redis:6379/1
      OLLAMA_URL: http://ollama:11434
      OLLAMA_MODEL: ${OLLAMA_MODEL:-llama3.1:8b}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 15s

  # Optional gateway — only needed for federation / TLS /.well-known
  # caddy:
  #   image: caddy:2-alpine
  #   restart: unless-stopped
  #   ports: ["80:80", "443:443"]
  #   volumes:
  #     - ./infra/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
  #     - caddydata:/data
  #     - caddyconfig:/config
  #   depends_on: [api1, api2]

volumes:
  pgdata:
  redisdata:
  ollama:
  # caddydata:
  # caddyconfig:

networks:
  default:
    name: vibe-code
```

Port map: `8001` api1 · `8002` api2 · `5432` pg · `6379` redis · `11434` ollama.

## 2. Dockerfiles (both APIs, identical except code)

`services/api1/Dockerfile` (copy to `api2/`):

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/* \
  && useradd -m -u 10001 svc

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
USER svc
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

`services/api{1,2}/requirements.txt`:

```
fastapi==0.115.*
uvicorn[standard]==0.30.*
pydantic==2.*
pydantic-settings==2.*
asyncpg==0.29.*
redis[hiredis]==5.*
httpx==0.27.*
```

Minimal `services/api1/app/main.py` (same for api2):

```python
import os
from fastapi import FastAPI

app = FastAPI()
NAME = os.getenv("SERVICE_NAME", "api")

@app.get("/health")
def health():
    return {"ok": True, "service": NAME}

@app.get("/")
def root():
    return {"service": NAME, "docs": "/docs"}
```

`.dockerignore`:

```
__pycache__
*.pyc
.venv
.git
```

`.env.example`:

```bash
POSTGRES_USER=app
POSTGRES_PASSWORD=change-me-32chars
POSTGRES_DB=app
OLLAMA_MODEL=llama3.1:8b
```

## 3. One-command up

```bash
cp .env.example .env  # edit password once
docker compose up -d --build
docker compose exec ollama ollama pull llama3.1:8b
curl localhost:8001/health && curl localhost:8002/health
curl localhost:11434/api/tags
docker compose logs -f api1 api2
```

Update / rebuild: `docker compose up -d --build api1 api2` · Full reset: `docker compose down -v`.

## 4. Well-known / federation — only if needed

Plain APIs need **no** `/.well-known`. Add it only if federating (ActivityPub/WebFinger) or ACME:

```caddyfile
# infra/caddy/Caddyfile (uncomment caddy service above)
example.com {
  handle /.well-known/webfinger* { reverse_proxy api1:8000 }
  handle /.well-known/nodeinfo*  { reverse_proxy api1:8000 }
  handle /api/v1/* { reverse_proxy api1:8000 }
  handle /api/v2/* { reverse_proxy api2:8000 }
  handle { reverse_proxy api1:8000 }
}
```

Then `docker compose up -d caddy`. Caddy auto-TLS satisfies federation's HTTPS requirement.

## 5. Hot-spare laptop clone (<60s + copy time)

No registry needed. Same `compose.yaml` + `.env` on both machines.

```bash
# --- on primary (backup) ---
docker compose exec postgres pg_dump -U app app | gzip > backup.sql.gz
docker run --rm -v vibe-code_redisdata:/data -v $PWD:/b alpine tar czf /b/redisdata.tgz -C /data .
docker run --rm -v vibe-code_ollama:/root/.ollama -v $PWD:/b alpine tar czf /b/ollama.tgz -C /root/.ollama .
# copy: compose.yaml .env backup.sql.gz redisdata.tgz ollama.tgz + services/ via USB/rsync/scp

# --- on spare (restore) ---
cp .env.example .env  # paste SAME passwords
docker compose up -d postgres redis ollama
zcat backup.sql.gz | docker compose exec -T postgres psql -U app -d app
docker run --rm -v vibe-code_redisdata:/data -v $PWD:/b alpine sh -c 'rm -rf /data/* && tar xzf /b/redisdata.tgz -C /data'
docker run --rm -v vibe-code_ollama:/root/.ollama -v $PWD:/b alpine sh -c 'rm -rf /root/.ollama/* && tar xzf /b/ollama.tgz -C /root/.ollama'
docker compose up -d --build
docker compose ps && curl localhost:8001/health && curl localhost:8002/health
```

Live sync alternative: `lsyncd`/`Syncthing` for `services/` + nightly `pg_dump` cron. Keep spare `docker compose pull` fresh weekly so failover is just restore + up.

## 6. Ops notes

- Images pinned: `postgres:16-alpine`, `redis:7-alpine`, `ollama/ollama:0.6.8`, `python:3.12-slim` — reproducible, small.
- Healthchecks gate `api` start; `depends_on` avoids crash-looping on cold boot.
- Volumes are named (survive `up/down`); only `-v` wipes DB.
- Ollama model blobs live in `ollama` volume (~4–5 GB for 8B) — pre-pull before demo/offline.
- Apple Silicon spare: Ollama runs CPU (slow); keep `OLLAMA_MODEL=tinyllama` fallback in `.env`.
- Prod hardening later: remove `ports:` for pg/redis, add Caddy + `BasicAuth`, set `POSTGRES_PASSWORD` via Docker secret.
