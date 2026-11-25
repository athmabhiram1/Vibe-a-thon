# 41 — Fast Starters: Copy Verbatim vs Adapt (HR+IT, Synapse-Safe)

> Goal: save 4–10 hours with premade starters without breaking Synapse detection (dedicated `app/synapse/` router + `synapse_` event schemas + unchanged Synapse middleware/order).

## 1. Starter scorecard (fastest first)

| # | Starter | Repo | Best for HR+IT | Time saved | Risk to Synapse |
|---|---------|------|----------------|------------|-----------------|
| S1 | **fastapi/full-stack-fastapi-template** (ex-tiangolo full-stack-fastapi-postgresql) | `github.com/fastapi/full-stack-fastapi-template` | Full HR+IT skeleton: JWT auth, users CRUD, Postgres+SQLModel+Alembic, Docker Compose, React admin, pytest, GH Actions | ~8h | Low if you keep backend-only; Medium if you take frontend (auto-generated client overwrites `/synapse` tags) |
| S2 | **fastapi-users full example (SQLAlchemy)** | `github.com/fastapi-users/fastapi-users` → `examples/sqlalchemy/` + docs `configuration/full-example` | Drop-in auth: register/login/reset/verify + `UserManager.on_after_*` hooks → wire HR onboarding / IT access revoke | ~3h | Very low (isolated `fastapi_users.get_*_router()` mounts) |
| S3 | **Tobi-De/cookiecutter-fastapi** | `github.com/Tobi-De/cookiecutter-fastapi` | Django-style `apps/` split → perfect for `apps/hr/` + `apps/it/` + `apps/synapse/`; health-check, pagination, Typer CLI, SAQ worker | ~5h | Low (apps are self-registering; just don't put Synapse routes inside `users/`) |
| S4 | **gaganpreet/fastapi-starter** | `github.com/gaganpreet/fastapi-starter` | Async SQLAlchemy 2.0 + fastapi-users + React-Admin + OpenAPI TS client — closest to HR+IT CRUD + admin panel need | ~4h | Low-Medium (React-Admin resource names collide if you rename `users` → `employees`) |
| S5 | **awesome-fastapi / boilerplates.directory / starterindex** lists | `github.com/mjhea0/awesome-fastapi`, `boilerplates.directory/stack/fastapi`, `starterindex.com/fastapi-boilerplates` | Pick-augment only: `benavlabs/fastapi-boilerplate` (RBAC+tiers+ratelimit), `fastapi-alembic-sqlmodel-async`, `fastapi-mvc` | ~1–2h each | Varies — copy patterns, not whole repos |

> If you only have 30 min: do **S2 + S1-backend**. If you have 2h: generate **S3** then graft **S2 auth** + **S1 Docker/CI** onto it.

## 2. Golden rule: what Synapse detection needs (do not break)

1. **Path stability:** keep `app/synapse/router.py` mounted at exactly `prefix="/synapse"` with `tags=["synapse"]`. Starters love to auto-prefix everything with `/api/v1` — exempt Synapse.
2. **Schema prefix:** every Synapse Pydantic model / event stays `Synapse*` / `synapse_*` (`SynapseEvent`, `synapse_hr_hired`, `synapse_it_ticket`). Never let a codemod rename `User` → `Employee` touch these files.
3. **Middleware order:** `CORSMiddleware → SynapseContextMiddleware → AuthMiddleware`. tiangolo/S3 templates insert `TrustedHost` / session middleware — append, don't prepend.
4. **Event bus import path:** `from app.synapse.bus import emit` must keep working. Don't nest it under `apps/hr/synapse/`.
5. **Health vs readiness:** keep starter `/health` (public) separate from `/synapse/health` (authenticated). Merging them breaks Synapse monitors.

Violation = Synapse UI/APM stops discovering HR hires + IT tickets. When in doubt, `grep -r "synapse" --include="*.py" | head` after every copy.

## 3. Copy VERBATIM (don't edit — saves hours, zero Synapse risk)

Copy these files byte-for-byte, only changing env values:

- **S1:** `backend/Dockerfile`, `compose.yml`, `compose.override.yml`, `.env.example`, `backend/app/alembic/` (whole dir), `backend/app/tests/` harness (`conftest.py`, `test_api/` runner), `.github/workflows/test.yml`, `backend/README.md` dev commands.
- **S2:** `examples/sqlalchemy/app/db.py` (engine/session/`get_user_db`), `examples/sqlalchemy/app/users.py` minus SECRET (auth_backend, `get_jwt_strategy`, `fastapi_users` object), `requirements` pins for `fastapi-users[sqlalchemy]`.
- **S3:** `app/core/pagination.py`, `app/core/logger.py`, `app/health.py`, `manage.py` (Typer CLI), `.pre-commit-config.yaml`, `gunicorn.conf.py`, `Dockerfile` prod target.
- **S4:** `pytest.ini` / async test fixtures, OpenAPI→TS client generation script (`package.json:generate-client`), React-Admin `dataProvider` wrapper.
- **Lists (S5):** `benavlabs` rate-limit + `@cache` decorator snippets only — vendor them into `app/core/` untouched.

## 4. ADAPT (copy-then-edit — HR+IT domain lives here)

| Starter file | Adapt into | How (15-min edits) |
|---|---|---|
| S1 `backend/app/models.py` (`User`, `Item`) | `app/hr/models.py` (`Employee`, `Leave`), `app/it/models.py` (`Asset`, `Ticket`) | Keep `User` table as-is for login; add FK `employee.user_id`. Never delete `User` — fastapi-users + Synapse expect it. |
| S1 `backend/app/schemas.py` | `app/hr/schemas.py`, `app/it/schemas.py` | Rename `ItemCreate` → `TicketCreate` etc. Keep `UserRead/UserCreate` names exactly (S2 routers import them). |
| S1 `backend/app/api/routes/users.py`, `items.py` | `app/hr/routes.py`, `app/it/routes.py` | Duplicate file, change prefix to `/hr/employees`, `/it/tickets`; keep response_model pattern + `Depends(current_active_user)`. |
| S2 `UserManager.on_after_register/forgot/request_verify` | `app/hr/manager.py : HRUserManager` | Add `await emit(synapse_hr_hired(...))` / `emit(synapse_access_revoked(...))` inside hooks. Keep method signatures. |
| S2 `auth_backend` (BearerTransport + JWTStrategy 3600s) | `app/core/auth.py` | Only change `SECRET` → env `SECRET_KEY`, `lifetime_seconds=3600→28800` (workday). Keep `tokenUrl="auth/jwt/login"` or generated TS client breaks. |
| S3 `app/users/{models,routes,schemas,manager}.py` | `app/hr/`, `app/it/` apps | Keep the 6-file app shape; add `tasks.py` → SAQ jobs (`provision_laptop`, `offboard_wipe`). Don't move `synapse/` into `apps/`. |
| S1/S3 `config.py` (Pydantic Settings) | `app/core/config.py` | Add `HR_DEPT_CODES`, `IT_ASSET_PREFIX`, `SYNAPSE_WEBHOOK_URL`; keep `PROJECT_NAME`, `POSTGRES_*`, `SECRET_KEY` names. |
| Frontend client (S1/S4) | `frontend/src/client/` | Regenerate after backend done (`npm run generate-client`); manually re-add `synapse` tag filter if codegen drops it. |

## 5. Recommended 45-minute graft (HR+IT + Synapse-safe)

```bash
# 1. scaffold (10 min)
cookiecutter https://github.com/Tobi-De/cookiecutter-fastapi  # project: hrit, orm: sqlalchemy, auth: fastapi-users
# — OR backend-only clone:
git clone https://github.com/fastapi/full-stack-fastapi-template hrit && rm -rf hrit/frontend

# 2. auth (10 min) — verbatim from S2 sqlalchemy example
cp fastapi-users/examples/sqlalchemy/app/db.py hrit/app/core/db.py
cp fastapi-users/examples/sqlalchemy/app/users.py hrit/app/core/auth.py  # then $SECRET → env

# 3. domain (15 min) — duplicate, don't rename
cp hrit/app/users/routes.py hrit/app/hr/routes.py        # prefix /hr/employees
cp hrit/app/users/routes.py hrit/app/it/routes.py        # prefix /it/tickets
# add models Employee/Asset/Ticket with user_id FK

# 4. synapse (10 min) — new, isolated
mkdir hrit/app/synapse && touch hrit/app/synapse/{__init__,router,bus,schemas}.py
# mount LAST in main.py: app.include_router(synapse.router, prefix="/synapse", tags=["synapse"])
# verify: ruff check . && pytest -q && grep -rn "synapse" app --include="*.py"
```

## 6. Anti-patterns (how teams break Synapse)

1. **Global rename** `User→Employee` across repo — kills S2 routers + Synapse user joins. Duplicate instead.
2. **Nesting Synapse under HR/IT** (`apps/hr/synapse.py`) — detector scans top-level `app/synapse/`. Keep it top-level.
3. **Taking starter frontend wholesale** — auto-generated client + Traefik labels reroute `/synapse/*` to React. Scaffold backend first, regenerate client after.
4. **Replacing Alembic with `create_db_and_tables()`** from S2 lifespan snippet — fine for demo, breaks S1 migrations in prod. Use S2 code for local dev only; keep Alembic as source of truth.
5. **Copying `main.py` verbatim** — every starter's `main.py` has different lifespan/middleware. Hand-merge: lifespan (S1) + routers (S2/S3) + Synapse mount last.

## 7. Sources

- S1: `github.com/fastapi/full-stack-fastapi-template` (docs: `fastapi.tiangolo.com/project-generation/`), stack: FastAPI+SQLModel+Postgres+React+Docker+GH Actions+JWT.
- S2: `github.com/fastapi-users/fastapi-users` — `examples/sqlalchemy/`, `examples/beanie/`, docs `configuration/full-example` (JWT `SECRET`, `BearerTransport`, `get_*_router` mounts). Note: in maintenance mode 2025+ — pin version, still fine for HR+IT auth.
- S3: `github.com/Tobi-De/cookiecutter-fastapi` — Django-style apps, `core/{auth,config,logger,pagination}.py`, Typer `manage.py`, SAQ worker, health-check pattern.
- S4: `github.com/gaganpreet/fastapi-starter` — async SQLAlchemy 2.0 + fastapi-users + React-Admin + TS client gen.
- S5: `github.com/mjhea0/awesome-fastapi` (Boilerplate section), `boilerplates.directory/stack/fastapi` (20 kits compared), `starterindex.com/fastapi-boilerplates` (84 kits); spotlight: `benavlabs/fastapi-boilerplate` (RBAC/tiers/ratelimit/cache/Taskiq).
