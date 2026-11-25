# 42 — Fast Compose: Single `compose.yaml` (api-hr + api-it + postgres + redis + ollama)

> Goal: one file to boot the whole VIBE_CODE backend locally. Copy-paste ready. Includes healthchecks, volumes, env files, seed-on-boot, and hot-spare notes.

## 0. Layout assumed

```
VIBE_CODE/
  compose.yaml
  .env.example  -> cp to .env
  services/api-hr/Dockerfile
  services/api-it/Dockerfile
  services/api-hr/src/... (FastAPI)
  services/api-it/src/... (FastAPI)
  scripts/seed.py
  postgres-init/01-extensions.sql
```

## 1. `compose.yaml` (copy-paste)

```yaml
name: vibe-code

services:
  postgres:
    image: postgres:16-alpine
    container_name: vibe-postgres
    restart: unless-stopped
    env_file: [.env]
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-vibe}
      POSTGRES_USER: ${POSTGRES_USER:-vibe}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}
      PGDATA: /var/lib/postgresql/data/pgdata
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./postgres-init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER:-vibe} -d $${POSTGRES_DB:-vibe}"]
      interval: 5s
      timeout: 3s
      retries: 20
      start_period: 10s
    networks: [vibe]
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }

  redis:
    image: redis:7-alpine
    container_name: vibe-redis
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes", "--requirepass", "${REDIS_PASSWORD:?set REDIS_PASSWORD}"]
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20
      start_period: 5s
    networks: [vibe]

  ollama:
    image: ollama/ollama:0.6.5
    container_name: vibe-ollama
    restart: unless-stopped
    ports:
      - "${OLLAMA_PORT:-11434}:11434"
    volumes:
      - ollama:/root/.ollama
    # GPU: uncomment for NVIDIA
    # deploy:
    #   resources:
    #     reservations:
    #       devices: [{ driver: nvidia, count: 1, capabilities: [gpu] }]
    healthcheck:
      test: ["CMD-SHELL", "ollama list || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 10
      start_period: 20s
    networks: [vibe]
    profiles: ["llm"]  # `docker compose --profile llm up` to include; omit profile to always run

  api-hr:
    build:
      context: ./services/api-hr
      dockerfile: Dockerfile
    container_name: vibe-api-hr
    restart: unless-stopped
    env_file: [.env, ./services/api-hr/.env.example]
    environment:
      SERVICE_NAME: api-hr
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-vibe}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-vibe}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      OLLAMA_HOST: http://ollama:11434
      PORT: "8001"
    ports:
      - "${API_HR_PORT:-8001}:8001"
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    command: >
      sh -c "python scripts/seed.py || true &&
             uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
    # NOTE: for prod remove --reload, use Dockerfile CMD instead
    volumes:
      - ./services/api-hr/src:/app/app:ro
      - ./scripts:/app/scripts:ro
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8001/health || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 10
      start_period: 15s
    networks: [vibe]

  api-it:
    build:
      context: ./services/api-it
      dockerfile: Dockerfile
    container_name: vibe-api-it
    restart: unless-stopped
    env_file: [.env, ./services/api-it/.env.example]
    environment:
      SERVICE_NAME: api-it
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-vibe}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-vibe}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/1
      OLLAMA_HOST: http://ollama:11434
      PORT: "8002"
    ports:
      - "${API_IT_PORT:-8002}:8002"
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    command: >
      sh -c "uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload"
    volumes:
      - ./services/api-it/src:/app/app:ro
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8002/health || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 10
      start_period: 15s
    networks: [vibe]

  # One-shot seeder — runs migrations + seed, then exits. Preferred over seed-in-api.
  seed:
    build: { context: ./services/api-hr, dockerfile: Dockerfile }
    env_file: [.env]
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-vibe}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-vibe}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      SEED_ON_BOOT: "${SEED_ON_BOOT:-true}"
    volumes:
      - ./scripts:/app/scripts:ro
    depends_on:
      postgres: { condition: service_healthy }
    command: ["python", "scripts/seed.py"]
    networks: [vibe]
    profiles: ["seed"]  # auto-run: `docker compose --profile seed up seed`, or call from api-hr entrypoint

volumes:
  pgdata:
  redisdata:
  ollama:

networks:
  vibe:
    driver: bridge
```

> Pick ONE seed strategy: (a) `seed` profile service (clean), or (b) `api-hr` inline `seed.py || true` (fast dev). Don't do both in prod — disable inline seed with `SEED_ON_BOOT=false`.

## 2. Dockerfiles (copy-paste)

**`services/api-hr/Dockerfile` (= api-it, change `app` path only):**

```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# system deps for asyncpg + healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev wget curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/app ./app
COPY scripts ./scripts

EXPOSE 8001
# dev override in compose uses --reload; prod default:
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD wget -qO- http://localhost:8001/health || exit 1
```

**`services/api-hr/requirements.txt` (minimal):**

```
fastapi>=0.115
uvicorn[standard]>=0.30
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29
alembic>=1.13
redis>=5.0
pydantic>=2.0
pydantic-settings>=2.0
httpx>=0.27
```

## 3. `.env.example` (copy to `.env`)

```bash
# ---- postgres ----
POSTGRES_DB=vibe
POSTGRES_USER=vibe
POSTGRES_PASSWORD=change-me-32chars
POSTGRES_PORT=5432

# ---- redis ----
REDIS_PASSWORD=change-me-redis
REDIS_PORT=6379

# ---- apis ----
API_HR_PORT=8001
API_IT_PORT=8002
JWT_SECRET=change-me-jwt-64chars-min
SEED_ON_BOOT=true

# ---- ollama ----
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3.1:8b

# ---- spare / prod ----
# DATABASE_URL= (composed in compose.yaml; override for managed PG)
# REDIS_URL=
# SENTRY_DSN=
```

Per-service override example (`services/api-hr/.env.example`):

```bash
LOG_LEVEL=debug
HR_ONLY_FLAG=true
```

## 4. Seed on boot

**`scripts/seed.py` contract** (idempotent — safe to run every boot):

```python
import asyncio, os
# if os.getenv("SEED_ON_BOOT","true").lower() not in ("1","true","yes"): raise SystemExit(0)
# 1. run alembic upgrade head
# 2. upsert roles, demo users, sample tickets
# 3. print("seed ok")
```

Run manually:

```bash
cp .env.example .env
docker compose up -d postgres redis
docker compose --profile seed up seed        # one-shot
docker compose up -d api-hr api-it
docker compose --profile llm up -d ollama     # if profiled
curl localhost:8001/health && curl localhost:8002/health
```

`postgres-init/01-extensions.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

## 5. Hot-spare notes (second machine / failover)

1. **Postgres is the SPOF.** For a hot spare: run `postgres-replica` with streaming replication, or nightly `pg_dump` to spare + `pgdata` volume backup:
   `docker exec vibe-postgres pg_dump -U vibe vibe | gzip > spare/vibe-$(date +%F).sql.gz`
2. **Redis:** spare runs `redis-server --replicaof primary 6379 --masterauth $REDIS_PASSWORD`. Promote with `REPLICAOF NO ONE`.
3. **APIs are stateless** — spare just needs same `.env` (except ports) + `docker compose up api-hr api-it`. Put a tiny reverse proxy (Caddy/Nginx) with `reverse_proxy primary:8001 spare:8001 lb_try_duration` in front.
4. **Ollama:** no replication needed; spare pulls model on demand: `docker exec vibe-ollama ollama pull llama3.1:8b`. Keep spare image pinned to same version.
5. **Volumes to rsync:** only `pgdata` (+ `redisdata` if persistence matters). Never rsync live `pgdata` files — use dump or `pg_basebackup`.
6. **Failover drill:** `docker compose stop postgres && <promote spare> && <flip proxy>` — should be < 5 min with dumps, < 60s with streaming replica.

## 6. Common gotchas

| Symptom | Fix |
|---|---|
| `redis-cli ping` healthcheck always unhealthy | `redis-cli -a $PASS` needs `--raw`; or use `test: ["CMD-SHELL","redis-cli -a $$REDIS_PASSWORD ping \| grep PONG"]` |
| `pg_isready` fails | user/db mismatch — check `POSTGRES_*` in `.env` vs compose interpolation |
| ollama eats disk | `ollama` volume grows ~5 GB/model; prune unused: `ollama rm <model>` |
| seed runs twice | disable inline seed when using `seed` profile: set `SEED_ON_BOOT=false` for api-hr |
| Windows bind-mount `:ro` errors | use WSL2 backend; keep source in Linux FS or set `COMPOSE_CONVERT_WINDOWS_PATHS=1` |

## Commands cheat-sheet

```bash
docker compose up -d --build          # boot all (add --profile llm --profile seed as needed)
docker compose ps && docker compose logs -f api-hr
docker compose exec postgres psql -U vibe -d vibe -c '\dt'
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" info replication
docker compose down && docker compose down -v  # second nukes pgdata!
```
