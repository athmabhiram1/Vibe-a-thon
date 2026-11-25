# 06 — FastAPI Starter Libraries: Pick for Fastest Synapse-Safe Scaffold

**Question:** Which premade FastAPI starter to use for fastest scaffold — `fastapi/full-stack-fastapi-template` vs `tiangolo/full-stack-fastapi-postgresql` vs `fastapi-users` vs `fastapi-pagination` vs `fastapi-filter` — under Synapse detection rules (explicit `operation_id` on every operation, no dynamic routers)?

**Date:** 2026-11-22 | **Sources:** Context7 (`/websites/fastapi_tiangolo`, `/uriyyo/fastapi-pagination`, `/arthurio/fastapi-filter`, `/fastapi-users/fastapi-users`) + websearch (PyPI, GitHub).

## TL;DR Pick

| Library | Verdict | Why |
|---|---|---|
| `fastapi/full-stack-fastapi-template` (new, React+SQLModel+Postgres) | **USE — scaffold base** | Only maintained template. Explicit `@router.get(..., operation_id="...")` style, `APIRouter`, SQLModel, Alembic, JWT example. Copy `backend/` only if you don't need React. |
| `tiangolo/full-stack-fastapi-postgresql` (old, Vue/Angular generator) | **AVOID — deprecated** | Superseded by above. Old Cookiecutter, outdated deps, async patterns. Do not start new projects on it. |
| `fastapi-users==15.0.5` | **AVOID for Synapse** | Maintenance mode since Mar 2026 (security fixes only). `get_auth_router() / get_register_router() / get_users_router()` are **dynamic routers** — you cannot pass `operation_id=` per-route via decorator; IDs are auto-generated. Breaks Synapse detection. Hand-roll JWT instead. |
| `fastapi-pagination==0.16.3` | **AVOID by default, opt-in only** | `add_pagination(app)` mutates all routes at startup, wraps `Page[T]`. Preserves `operation_id` *if* you set it, but magic rewrite + hidden `page/size` params confuse static detection and OpenAPI diff. Use manual `skip/limit` like template does. |
| `fastapi-filter==3.0.0` (`arthurio/fastapi-filter`) | **USE WITH CARE — Synapse-safe** | `FilterDepends()` is just a `Depends()` — does **not** create routers, does **not** touch `operation_id`. Safe provided you keep explicit `operation_id` on the endpoint. Best of the three helper libs. |

**Fastest Synapse-safe scaffold:** clone new template `backend/`, delete frontend, enforce `operation_id` lint, hand-rolled auth + manual pagination, add `fastapi-filter` only when you need `?name__ilike=&age__gte=&order_by=` filtering.

## Synapse Rules Applied

1. Every `@app/router.get/post/put/patch/delete` **must** have literal `operation_id="verb_resource_detail"` — e.g. `operation_id="list_items"`. No reliance on `generate_unique_id_function`.
2. **No dynamic routers:** no `fastapi_users.get_*_router()`, no factory that loops `add_api_route()` without literal `operation_id`, no `add_pagination(app)` global rewrite if avoidable.
3. Verify: `python -c "import json; print([o for p in openapi['paths'].values() for o in p.values() if 'operationId' not in o])"` must be empty + `grep -r "get_.*_router\|add_pagination" backend/` must be empty (except intentional filter use).

From FastAPI docs (Context7 `/websites/fastapi_tiangolo`):

```python
@app.get("/items/", operation_id="some_specific_id_you_define")
async def read_items():
    return [{"item_id": "Foo"}]
```

## Detail

### 1. Template: `fastapi/full-stack-fastapi-template` — USE

- Stack: FastAPI + SQLModel + PostgreSQL + Alembic + Docker + GitHub Actions + React/Vite/Tailwind/shadcn + auto-generated frontend client. Backend: `APIRouter` per domain (`api/routes/login.py`, `users.py`, `items.py`), `core/security.py` (passlib/jose JWT), `core/db.py`, `models.py`.
- Why fastest: auth, DB session, Alembic, Docker Compose, tests already wired. All routes are plain decorators — trivial to add `operation_id=`.
- Action: `git clone https://github.com/fastapi/full-stack-fastapi-template`, copy `backend/`, set `generate_unique_id_function` **off**, add explicit IDs (or codemod).

```bash
# scaffold
npx degit fastapi/full-stack-fastapi-template backend-scaffold
# or
git clone --depth 1 https://github.com/fastapi/full-stack-fastapi-template synapse-api
cp -r synapse-api/backend ./backend
```

- Old `tiangolo/full-stack-fastapi-postgresql`: last meaningful updates pre-2024, Cookiecutter-based, Pydantic v1-era patterns. GitHub now redirects to new template. **Do not use.**

### 2. `fastapi-users` — AVOID

- Status: `15.0.5` (Mar 27 2026, PyPI), now in **maintenance mode** — "no new features, security + dep updates only, successor toolkit in progress" (Context7 `/fastapi-users/fastapi-users`, Discussion #1543).
- Pattern (Context7):
```python
fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
```
- Synapse breakage: routers built inside library, no `operation_id=` param exposed; you get auto `operationId: "auth:jwt.login"` etc. Patching requires iterating `app.routes` post-hoc and assigning `route.operation_id` — fragile, breaks on upgrade, fails static grep detection.
- Instead: keep template's `core/security.py` (OAuth2PasswordBearer + `jose` JWT + `pwdlib`/`passlib`). ~60 lines, fully explicit, Synapse-clean.

### 3. `fastapi-pagination` — AVOID by default

- Latest: `0.16.3` (Nov 12 2026). Usage (Context7 `/uriyyo/fastapi-pagination`):
```python
from fastapi_pagination import Page, add_pagination, paginate
app = FastAPI()
add_pagination(app)

@app.get("/users")  # <- must add operation_id="list_users" yourself
async def get_users() -> Page[UserOut]:
    return paginate(users)
```
- It *preserves* explicit `operation_id` if you set it, but `add_pagination()` rewrites `response_model` globally; `page/size` params injected implicitly (not visible in signature). Static detectors that grep decorators miss them; OpenAPI diff noisy. SQLAlchemy usage requires `paginate(conn, select(...))` per-backend import — more coupling.
- Rule: if you need pagination fast, do manual `skip: int = 0, limit: int = 100` (template default) — 3 lines, zero magic, Synapse-perfect. Only adopt `fastapi-pagination` if you need cursor/page abstractions *and* you add a CI check asserting every `operationId` present.

### 4. `fastapi-filter` — USE WITH CARE

- Latest: `3.0.0` (Jun 3 2026, `arthurio/fastapi-filter`). Usage (Context7 `/arthurio/fastapi-filter`):
```python
from fastapi_filter import FilterDepends
from fastapi_filter.contrib.sqlalchemy import Filter

class UserFilter(Filter):
    name: str | None = None
    name__ilike: str | None = None
    age__gte: int | None = None
    class Constants(Filter.Constants):
        model = User

@app.get("/users", response_model=list[UserOut], operation_id="list_users")
async def get_users(user_filter: UserFilter = FilterDepends(UserFilter)):
    query = user_filter.filter(select(User))
    ...
```
- Synapse-safe: `FilterDepends` is a normal dependency, no router creation, `operation_id` stays exactly as you wrote it. Query params appear in OpenAPI via Pydantic model — good.
- Caveat: `order_by`, `search` helpers add many query params; keep `Constants.model` explicit, avoid `with_prefix` nesting unless needed.

## Pip Pins (Synapse backend, Nov 2026)

Pin exact — template floats; Synapse needs repro:

```txt
# requirements-synapse.txt
fastapi==0.165.0
uvicorn[standard]==0.37.0
sqlmodel==0.0.27
pydantic==2.12.4
pydantic-settings==2.11.0
sqlalchemy==2.0.44
alembic==1.17.1
psycopg[binary]==3.2.9
python-jose[cryptography]==3.5.0
passlib[bcrypt]==1.7.4
pwdlib[argon2,bcrypt]==0.3.0
python-multipart==0.0.20
email-validator==2.3.0
httpx==0.28.1
pytest==8.4.1
httpx-oauth==0.14.0  # only if you insist on OAuth without fastapi-users

# optional, only if needed:
fastapi-filter==3.0.0
# fastapi-pagination==0.16.3  # avoid by default
# fastapi-users==15.0.5  # avoid — listed for audit only
# fastapi-users-db-sqlalchemy==7.0.0  # avoid with above
```

Python `>=3.11,<3.15` (FastAPI 0.165 requires `>=3.11`).

## Scaffold Checklist (5 min)

1. Clone new template `backend/`, `uv venv && uv pip install -r requirements-synapse.txt`.
2. Codemod: add `operation_id="..."` to every decorator; set `FastAPI(generate_unique_id_function=lambda r: r.name)` as backstop only — explicit IDs still required.
3. Delete `get_*_router`, `add_pagination` imports if copilot adds them.
4. Add CI gate: `python scripts/assert_operation_ids.py` (fail if any op missing `operationId`).
5. Add `fastapi-filter` only on list endpoints that need filtering.

## Links

- Template: https://github.com/fastapi/full-stack-fastapi-template | Docs: https://fastapi.tiangolo.com/project-generation/
- Old (avoid): https://github.com/tiangolo/full-stack-fastapi-postgresql
- fastapi-users maintenance: https://github.com/fastapi-users/fastapi-users/discussions/1543 | Docs: https://fastapi-users.github.io/fastapi-users/ | PyPI 15.0.5
- Pagination: https://github.com/uriyyo/fastapi-pagination (0.16.3) | Docs: https://uriyyo-fastapi-pagination.netlify.app/
- Filter: https://github.com/arthurio/fastapi-filter (3.0.0) | Docs: https://fastapi-filter.netlify.app/
- Explicit operation_id: https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/
