# 04 — ORM Pick: Kill Pydantic v2 + SQLAlchemy 2.0 + Alembic?

**Question:** For the 79-row Synapse demo, is `Pydantic v2 + SQLAlchemy 2.0 + Alembic` overkill vs Tortoise / Django ORM / Prisma / supabase-js / direct asyncpg, or vs no-ORM (SQLite + dataclasses)? Does dropping Alembic/SQLAlchemy ship Cloudflare D1 faster?

**Verdict: YES — kill Alembic + SQLAlchemy for the demo. Keep Pydantic v2. Ship `SQLite (aiosqlite) + raw SQL + Pydantic response_models`, with a 1-file `schema.sql` + `seed.py`, and defer Drizzle (D1) to deploy day.**

- 79 rows = zero migration need, zero concurrency need, zero multi-table-join need. Alembic's value (autogenerate, reversible history, rename handling) is $0 here and costs ~2-4h setup + most LLM-hallucinated surface (env.py, target_metadata, async template).
- Pydantic v2 is **not** the problem — keep it. It is the typed contract for Synapse `response_model`, costs nothing extra under FastAPI, and is 4–50× faster than v1 via Rust `pydantic-core` (Context7 `/pydantic/pydantic` → `why.md`/`performance.md`). Do not drop it for dataclasses.
- For D1 ship speed, neither SQLAlchemy nor Tortoise helps — D1 is SQLite-over-HTTP in Workers; Python cannot run there. The D1-native path is TS: Drizzle (first-class) > Prisma (Preview, drops transaction semantics per Flarestarter/Prisma docs). So SQLAlchemy work is throwaway at the edge; raw SQLite schema ports 1:1 to Drizzle/D1, SQLAlchemy models do not.

## Comparison (79-row demo lens)

| Option | Migration need? | Typed schemas for Synapse `response_model`? | Validation speed | Hallucination surface | D1 ship speed | Verdict |
|---|---|---|---|---|---|---|
| **Pydantic v2 + SQLAlchemy 2.0 (`Mapped[]`/`mapped_column`) + Alembic** | Alembic `init -t async`, `env.py`, naming conventions, `--autogenerate` (misses renames, server defaults). Needed at 10+ tables / team / prod Postgres. | Excellent: `ConfigDict(from_attributes=True)` reads ORM objects; `EmailStr`, `Annotated[int, Field(gt..)]`, `model_validator`. Native `Mapped[]` typing passes mypy strict. | Pydantic v2 Rust core: ~17× v1 typical, 3.45× hand-rolled JSON+URL validation (Context7). SQLAlchemy Core ~raw SQL; ORM overhead irrelevant at 79 rows. | **Largest.** Session/engine/async_sessionmaker, `expire_on_commit=False` trap, relationship lazy-load in async, Alembic async env, duplicate Pydantic↔Table models (or immature SQLModel 0.0.x). LLMs mix 1.x `Column` with 2.0 `mapped_column` constantly. | **Slowest.** None of this runs on Workers/D1. Rewrite to Drizzle/Prisma anyway. | ❌ Kill for demo; revisit at prod Postgres |
| **Tortoise ORM + Aerich** | Aerich = Alembic-lite; fine for basic, incorrect SQL on complex migrations (community reports). Tortoise 1.0 just added built-in migrations. | Mediocre: Django-like API, Pydantic plugin is serialize-only, no deserialization. Weaker than native Pydantic. | Async-native, but no Rust validation win; roughly = SQLAlchemy for tiny N. | Medium. Smaller API than SQLAlchemy, but Aerich is low-example-count for LLMs → more invented APIs. Async misuse still possible. | Same D1 dead-end as SQLAlchemy (Python-only). | ❌ No advantage over raw SQL at 79 rows |
| **Django ORM** | Built-in `makemigrations` + rename detection, best migration UX. | Poor fit: tied to Django settings/apps/admin/forms/DRF; awkward under FastAPI; needs `django-stubs`. | Sync-first; async wrapper doesn't free threads. Fine at 79 rows, wrong framework. | Medium-high if forced into FastAPI (two pools, two model defs). Zero if you go full-Django — but then you lose FastAPI+Synapse. | Dead-end for D1. | ❌ Framework mismatch; only if you abandon FastAPI |
| **Prisma (TS)** | `prisma migrate` excellent, but D1 support = Preview, silently drops transaction semantics. | Excellent in TS, irrelevant in Python demo. | Fast (Rust engines) but adds engine sidecar; overkill for 79 rows. | Low in TS, high if LLM must bridge Python→Prisma. | ⚠️ Viable but second to Drizzle on D1. | Defer; consider only if demo goes full-TS |
| **supabase-js / direct asyncpg** | supabase-js: no migrations (managed Postgres + SQL editor). asyncpg: no ORM, you own SQL. | supabase-js: PostgREST infers types, weak vs Pydantic `response_model`. asyncpg: zero validation — must add Pydantic back. | asyncpg = fastest PG driver; supabase-js = HTTPS+PostgREST overhead. Both irrelevant at 79 rows (SQLite <1ms). | Low: one client, plain SQL/REST. But supabase-js adds network + auth + RLS policy surface LLMs hallucinate. | Supabase is hosted Postgres — not D1; fine alternative to D1, not a path to D1. asyncpg can't talk to D1. | ⚠️ Supabase = legit D1 *alternative*; asyncpg = keep only if prod stays on Postgres without ORM |
| **No-ORM: SQLite + `sqlite3`/aiosqlite + dataclasses/Pydantic** ✅ | **None.** `schema.sql` (CREATE TABLE IF NOT EXISTS) + `seed.py` (79 inserts) + `db.reset()` is the migration. Git-diffable, reviewable, zero tool. | **Best for effort:** Pydantic `BaseModel` *is* the schema; `response_model=` enforces Synapse contract. Dataclasses alone lose `EmailStr/HttpUrl/Field(gt..)` + JSON-schema generation — so use Pydantic, not plain dataclasses. | Fastest path: SQLite in-process, no pool, Pydantic v2 Rust validation dominates cost and it's already paid under FastAPI. msgspec 5–6.5× faster than Pydantic v2 exists but FastAPI is welded to Pydantic — ignore. | **Smallest.** `SELECT … WHERE id=?` has nothing to hallucinate. No session, no env.py, no lazy-load, no rename-trap. Only SQL-injection rule: always parameterized `?`. | **Fastest.** `schema.sql` (SQLite dialect) ports to D1/Drizzle in <1h; Drizzle-kit generates D1 migrations from same DDL. Zero throwaway ORM code. | ✅ **Ship this** |

## Why keep Pydantic, drop SQLAlchemy/Alembic

1. **Synapse needs `response_model`, not an ORM.** FastAPI serializes `response_model` via Pydantic regardless of DB layer. `model_config = ConfigDict(from_attributes=True)` works with ORM objects *or* `Row`→`model_validate(dict(row))`. Keeping Pydantic preserves typed I/O, OpenAPI schema, and client codegen with ~5 lines per model.
2. **Alembic pays off at schema churn, not at 79 static rows.** Standard production pattern (`DeclarativeBase` + naming conventions + async `env.py` + `target_metadata = Base.metadata`) is real work and the #1 source of paste-errors in LLM-generated FastAPI repos. For a frozen demo seed, `Base.metadata.create_all()` — or plain `schema.sql` — strictly dominates.
3. **SQLModel doesn't save you.** It merges Pydantic+SQLAlchemy to kill duplication, but stays `0.0.x` (unstable API per maintainer), and the single-class win evaporates once you need Create/Read/Update shapes — which Synapse does.
4. **Hallucination ranking (most→least):** SQLAlchemy 1.x/2.0 mixups + async session traps > Django-in-FastAPI > Aerich invented APIs > Prisma-on-Python > supabase RLS policies > raw parameterized SQLite. At hackathon speed, pick the bottom.

## D1-specific note

- D1 docs list Prisma + Drizzle as first-class, but practitioner reports (Flarestarter 2026, Makerkit, Prisma v7 comparison): **Drizzle has full D1/bun:sqlite/HTTP-proxy support with native transactional batches; Prisma-on-D1 is Preview with degraded transactions.** If the demo must run on Workers, write TS + Drizzle from the start.
- Python + SQLAlchemy/Tortoise/asyncpg **cannot run inside a Worker**; you'd keep a Python API (Render/Fly) talking to D1 over HTTP — adding latency for no gain. Either (a) demo stays Python+SQLite locally, port schema to Drizzle on deploy day, or (b) go full-TS now. Don't build a Python ORM layer you will delete.
- Supabase-js is the fastest *non-D1* ship (no migrations, instant REST), but it commits you to hosted Postgres + RLS, not the edge. Choose Supabase *or* D1, not both.

## Ship recipe (recommended)

```
db/
  schema.sql   # CREATE TABLE synapses (...); CREATE INDEX …;
  seed.py      # reads 79 rows (csv/json) → INSERT OR REPLACE; prints count
  store.py     # ~60 lines: get_db(), fetch_synapses(filters) -> list[SynapseOut]
api/
  schemas.py   # class SynapseOut(BaseModel): id, name, args_schema, … + from_attributes
  routes.py    # @app.get("/synapses", response_model=list[SynapseOut])
```

- `store.py` uses `aiosqlite` + `?` placeholders, returns `SynapseOut.model_validate(dict(r))`. No engine, no session, no Alembic.
- Reset = `rm demo.db && python db/seed.py`. "Migration" = edit `schema.sql` + re-seed. Document that this expires at ~5 tables / concurrent writers / prod auth — then adopt SQLAlchemy 2.0 async + Alembic (Postgres) or Drizzle (D1).
- Pydantic stays pinned `pydantic>=2.10,<3`; add `pydantic-settings` for config. No `SQLModel`, no `Tortoise`, no `Alembic` in `requirements.txt`.

## Sources

- Context7 `/pydantic/pydantic` — `why.md` (Rust `pydantic-core`, 3.45× pure-Python benchmark), `concepts/performance.md`; `/sqlalchemy/sqlalchemy` — 2.0 `mapped_column`/`Mapped[]` typing, declarative tables.
- Web: pythonresources.com + Chat2DB (Django ORM vs SQLAlchemy decision table, Alembic rename trap); rajpoot.dev (FastAPI+Pydantic v2+SQLAlchemy 2.0 production pattern, `expire_on_commit=False`, naming conventions); alexsikand.com (2026 stack: SQLAlchemy async default, Tortoise runner-up, Alembic only option, msgspec vs Pydantic); Cloudflare D1 + Drizzle docs + Prisma v7 Drizzle comparison + Flarestarter (Prisma-on-D1 Preview/transaction caveat); Pydantic v2 vs msgspec benchmarks (17× v1, msgspec ~6.5× Pydantic v2, FastAPI welded to Pydantic).
