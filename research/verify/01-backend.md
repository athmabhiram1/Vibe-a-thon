# Backend Verdict: FastAPI — KEEP (do not switch)

**Verdict: KEEP FastAPI.** No case found where Django/DRF, Flask, Frappe, or NestJS/Express-TS beats FastAPI for the HR+IT Synapse Auto 2-system demo on the criteria that decide judging: static detection quality, operation_id control, seed/demo speed, Docker weight, and rerun ease.

## 1. Synapse static detection quality

FastAPI is the best target for static OpenAPI extraction:

- Routes are explicit decorators (`@app.get/post`, `APIRouter`) + Pydantic `BaseModel` request/response types. Tree-sitter/static tools list FastAPI as first-class supported alongside Flask/DRF: Pydantic models extracted, `router registration is ground truth` (codistill, api2spec docs).
- DRF introspection depends on `GenericAPIView.get_serializer(), pagination_class, filter_backends`; for plain `APIView` it is "essentially limited to URL kwarg path parameters" (DRF `AutoSchema` docs via Context7). Serializers + ViewSets + routers add indirection vs. FastAPI's 1 function = 1 operation.
- Flask/Express have no typed body by default: Flask exposes `request.get_json()` with manual validation; Express "doesn't know what your routes accept or return" — needs zod-to-openapi / tsoa / swagger-jsdoc comments that drift (NativeShip guide).
- NestJS needs `@ApiProperty()` on every DTO field or the Swagger CLI plugin + `@ApiTags` per controller to get usable schemas.

Winner: FastAPI. Synapse gets complete paths + JSON Schemas with zero extra decorators.

## 2. operation_id control

- FastAPI: one line `FastAPI(generate_unique_id_function=lambda route: route.name)` or `f"{route.tags[0]}-{route.name}"`, or per-route `operation_id="..."` (official docs: `path-operation-advanced-configuration`, `generate-clients`). Default verbose `get_contact_contacts__contact_id__get` is fixable in 1 line; requirement is only unique function names.
- NestJS: equivalent `operationIdFactory: (controllerKey, methodKey) => methodKey` in `SwaggerModule.createDocument()`, but requires unique method names AND `@ApiTags` + `@ApiProperty` hygiene + plugin config.
- DRF: `AutoSchema(component_name=...)`, `tags=[...]`, `schema=None` to exclude — per-view objects, no single global `operationId` function; tags default to first URL segment.
- Flask/Express: no native operationIds at all; entirely plugin/comment-driven.

Winner: FastAPI (simplest, best-documented, CI-serializable via `app.openapi()` → `openapi.json`).

## 3. Pydantic / schema story

- FastAPI + Pydantic v2: declaration = validation + serialization + filtering + OpenAPI + 422 errors. `response_model` does docs/validation/filtering in one param (Context7 FastAPI docs). `model_json_schema()` enables offline/CI drift checks without booting server (schema-drift guardrail pattern, DEV 2026-11-06).
- DRF: serializers duplicate model definitions; validation-error payloads smaller (113.5B vs 397B FastAPI in krabarena reproducible battle) but schema larger to maintain and OpenAPI needs `drf-spectacular` / `AutoSchema`.
- Flask: manual — marshmallow/webargs/apispec; FastAPI author notes this combo inspired FastAPI but required YAML-in-docstrings and lost editor support.
- Frappe: DocType-driven, not Pydantic/OpenAPI-first; custom FastAPI alongside Frappe is a known integration pain (Frappe forum: "best practices for integrating custom FastAPI endpoints").
- NestJS: `class-validator` + `class-transformer` + DTOs ≈ Pydantic, but TS build step + decorator boilerplate.

Winner: FastAPI for contract-first Synapse demo.

## 4. Seed / demo speed (2-system HR+IT)

- FastAPI: `seed.py` inserting Pydantic-validated rows + SQLite/Postgres in ~30 lines; no migrations ceremony for demo; interactive `/docs` lets judges click-try without frontend.
- Django: wins only if demo needs login + staff CRUD + permissions on day one — `admin.site.register(Post)` = instant back-office (Django docs, EVNE, runxbuild, Davtyan). For a 2-system *API* demo judged on Synapse graph (HR hires → IT tickets/assets), admin is unused surface: auth, migrations, settings, apps add setup time and judge confusion.
- Flask: 5-line hello-world faster, but you re-pay it writing validation + docs manually.
- Frappe: heavyweight ERPNext stack; overkill for seeded HR (employees, leave) + IT (tickets, assets) toy data; bench setup >> `uvicorn main:app`.
- NestJS: `npm install + build + @nestjs/swagger` scaffolding slower than `pip install fastapi uvicorn`.

Verdict: Django/Frappe auto-admin does **not** beat FastAPI here — no non-technical operator workflow to demo; judges evaluate API contract + Synapse edges, not back-office editing.

## 5. Docker weight

Measured (codingkitchen 2026, `python:3.14-slim`): `flask-app 189MB < django 243MB < fastapi[standard] 300MB` (+120MB over slim due to uvicorn/pydantic-core/httptools/uvloop). Optimized multi-stage `python:3.11-slim` FastAPI → ~150-180MB, <100MB achievable (Wolfi/distroless patterns). Idle RAM: Flask 30-50MB, FastAPI 40-60MB/worker, Django 70-130MB + 2-5s startup (CodeArchaeology 2026). Flask lightest, but gap is <130MB and erased by one `HEALTHCHECK` + judge `docker compose up` convenience. Django heaviest at rest; Frappe/ERPNext image is GB-scale (bench + MariaDB + Redis + Node) — disqualifying for quick rerun. NestJS image ~100-180MB Node — comparable, but adds Node toolchain judges must trust.

Winner on weight alone: Flask. Winner on weight-per-feature: FastAPI.

## 6. Judge rerun ease

FastAPI: `pip install -r requirements.txt → uvicorn app.main:app → /openapi.json + /docs`; deterministic `app.openapi()` dump in CI (`python -c "import json; from app.main import app; ..."`). Single `docker-compose.yml` (api + db + seed) reproduces. DRF needs `migrate + createsuperuser + runserver`; Frappe needs `bench init/get-app/migrate`; NestJS needs `npm ci + build + start`. Fewest steps + most debuggable = FastAPI.

Reproducible benchmarks (krabarena, nunombispo, abdelaziz-mahdy backend-benchmark) confirm all three Python frameworks can serve identical CRUD APIs with <5ms p95 diffs on SQLite — performance is not the decider; contract clarity and setup are.

## When Django/Frappe/Flask *would* win (not this build)

- Choose Django if: need multi-role auth + permissions + audit + operator back-office on day one, or 5+ relational models edited by staff.
- Choose Frappe if: need ERPNext DocTypes, print formats, role permissions, reports out-of-box for HRMS-like production.
- Choose Flask if: single-file micro-mock with no validation/docs needs and <50MB image hard constraint.
- Choose NestJS if: team is TS-only and needs DI/modules/guards for long-lived enterprise codebase.

None apply: Synapse Auto is a 2-service API + static-graph demo, judged on clean OpenAPI, stable operationIds, and one-command rerun.

## Evidence links

- FastAPI vs Django 2026 (Encore, Planeks, Pynions, DjangoCon US 2026 Batteries-vs-Speed, DjangoTV)
- FastAPI vs Flask (Strapi 2025, Encore, Pynions, Codecademy)
- Docker: codingkitchen python tutorial image sizes, pythonapibuilders slim/multi-stage, CodeArchaeology idle-cost, fastapi.tiangolo.com/deployment/docker
- operationId: fastapi.tiangolo.com `path-operation-advanced-configuration` + `generate-clients`, NestJS `openapi/introduction` (`operationIdFactory`), NativeShip openapi-spec guide, vertz/adapters
- Pydantic/static: Context7 FastAPI + DRF AutoSchema docs, api2spec + codistill tree-sitter support matrix, DEV schema-drift guardrails 2026-11-06, pydantic#4816
- Admin moat: Django admin docs, themissingmanual, EVNE SaaS MVP, runxbuild, Davtyan industrial systems, toolchew, Reddit r/FastAPI admin thread
- Reproducible battles: krabarena FastAPI-vs-DRF-vs-Flask, nunombispo comparison, abdelaziz-mahdy backend-benchmark, mahdi0shamlou benchmarks

## Decision

**KEEP FastAPI + Pydantic v2 + Uvicorn + `generate_unique_id_function=lambda r: r.name` (or `tags[0]-name`), pinned `requirements.txt`, `python:3.11-slim` multi-stage Dockerfile, `seed.py`, committed `openapi.json`.**
Do not absorb Django/Frappe admin cost for this demo.
