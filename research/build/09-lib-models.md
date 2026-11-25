# 09 — Premade Validation / ORM Stack: Pydantic v2 + SQLAlchemy 2.0 + Alembic

> Decision: **Pydantic v2** (validation/serialisation) + **SQLAlchemy 2.0 async** (ORM) + **Alembic** (migrations) + **asyncpg** (prod Postgres driver) / **psycopg[binary,pool]** (sync fallback + scripts) + **aiosqlite + WAL** (demo/offline). No Django ORM, no Tortoise, no raw-sql-only.

## 1. Picks (copy-paste `requirements.txt`)

```txt
# core
fastapi==0.116.*
pydantic==2.10.*
pydantic-settings==2.7.*
sqlalchemy[asyncio]==2.0.*
alembic==1.14.*
# prod postgres (pick ONE primary; keep other as fallback)
asyncpg==0.30.*          # primary: fastest async driver, native prepared statements
psycopg[binary,pool]==3.2.*  # fallback: sync scripts, pg_dump helpers, COPY
# demo / offline
aiosqlite==0.20.*
# utils
uuid-utils==0.8.*
python-ulid==3.0.*
```

**Why this combo (hackathon-optimised):**

| Concern | Choice | Rationale |
|---|---|---|
| Validation | Pydantic v2 | 5–50× faster than v1 (Rust core); `TypeAdapter`, `computed_field`, strict mode ideal for ATS parsing + webhook payloads |
| ORM | SQLAlchemy 2.0 (`Mapped[]` + `mapped_column`) | Fully typed, async-native, best Alembic + FastAPI integration; avoids Django heft |
| Migrations | Alembic | `alembic revision --autogenerate`, branches cleanly per-squad; render `naming_convention` for SQLiteALTER |
| Prod driver | **asyncpg** | Fastest asyncio Postgres driver; `prepared_statement_cache_size=0` avoids pgbouncer transaction-mode errors; JSONB/`LISTEN` support for outbox |
| Fallback driver | **psycopg v3** | Sync + `pool`, `COPY ... FROM STDIN` for bulk CSV import (candidates), easiest local debugging without async boilerplate |
| Demo DB | SQLite + WAL + aiosqlite | Zero-install judging demo; WAL gives concurrent read/write; single file to submit |

**asyncpg vs psycopg — rule of thumb:**
- App runtime (FastAPI async engine): `postgresql+asyncpg://...`
- One-off scripts / Alembic offline / CSV bulk load: `postgresql+psycopg://...`
- Never mix both pools in one process; select via `DB_DRIVER` env.

```python
# app/db.py — driver switch
import os
DRIVER = os.getenv("DB_DRIVER", "asyncpg")  # asyncpg | psycopg | sqlite
URLS = {
    "asyncpg": "postgresql+asyncpg://user:pass@localhost:5432/hrms",
    "psycopg": "postgresql+psycopg://user:pass@localhost:5432/hrms",
    "sqlite": "sqlite+aiosqlite:///./demo.db",
}
DATABASE_URL = os.getenv("DATABASE_URL", URLS[DRIVER])
```

## 2. SQLite WAL Mode for Demo (copy-paste)

```python
# app/db_sqlite.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine("sqlite+aiosqlite:///./demo.db", echo=False)

async def init_sqlite():
    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        await conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON;")
        await conn.exec_driver_sql("PRAGMA busy_timeout=5000;")

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

> Commit `demo.db-wal` handling: ship only `demo.db`; WAL replays on open. For judging zip, run `PRAGMA wal_checkpoint(TRUNCATE);` before freeze.

## 3. Shared Base + Mixins (copy-paste)

```python
# app/models/base.py
import uuid, datetime as dt
from sqlalchemy import MetaData, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)

class UUIDPK(Base):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

class TimestampMixin:
    __abstract__ = True
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

## 4. SQLAlchemy 2.0 Models (copy-paste → `app/models/*.py`)

```python
# app/models/hrms.py
import uuid, datetime as dt, enum
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Text, Integer, Numeric, Date, DateTime, Boolean, ForeignKey, UniqueConstraint, Index, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDPK, TimestampMixin

# NOTE: for SQLite demo, UUID/JSONB compile via TypeDecorator fallback — see §6.

class CandidateStage(str, enum.Enum):
    applied = "applied"; screening = "screening"; interview = "interview"
    offer = "offer"; hired = "hired"; rejected = "rejected"

class Candidate(UUIDPK, TimestampMixin, Base):
    __tablename__ = "candidates"
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    resume_url: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64), default="referral")
    stage: Mapped[CandidateStage] = mapped_column(SAEnum(CandidateStage), default=CandidateStage.applied, index=True)
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)  # skills, parsing output
    employees: Mapped[list["Employee"]] = relationship(back_populates="candidate")

class Employee(UUIDPK, TimestampMixin, Base):
    __tablename__ = "employees"
    candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("candidates.id", ondelete="SET NULL"))
    emp_code: Mapped[str] = mapped_column(String(32), unique=True)  # e.g. EMP-2026-0042
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    dept: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    candidate: Mapped[Optional[Candidate]] = relationship(back_populates="employees")
    laptops: Mapped[list["Laptop"]] = relationship(back_populates="assignee")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="assignee")

class LaptopStatus(str, enum.Enum):
    in_stock = "in_stock"; assigned = "assigned"; repair = "repair"; retired = "retired"

class Laptop(UUIDPK, TimestampMixin, Base):
    __tablename__ = "laptops"
    asset_tag: Mapped[str] = mapped_column(String(64), unique=True)  # LAP-00123
    serial: Mapped[str] = mapped_column(String(128), unique=True)
    model: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[LaptopStatus] = mapped_column(SAEnum(LaptopStatus), default=LaptopStatus.in_stock, index=True)
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), index=True)
    specs: Mapped[dict] = mapped_column(JSONB, default=dict)
    assignee: Mapped[Optional[Employee]] = relationship(back_populates="laptops")
    __table_args__ = (Index("ix_laptops_status_assignee", "status", "assignee_id"),)

class TicketStatus(str, enum.Enum):
    open = "open"; in_progress = "in_progress"; blocked = "blocked"; resolved = "resolved"; closed = "closed"
class TicketPriority(str, enum.Enum):
    low = "low"; medium = "medium"; high = "high"; urgent = "urgent"

class Ticket(UUIDPK, TimestampMixin, Base):
    __tablename__ = "tickets"
    ticket_no: Mapped[int] = mapped_column(Integer, unique=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(240))
    body: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(SAEnum(TicketStatus), default=TicketStatus.open, index=True)
    priority: Mapped[TicketPriority] = mapped_column(SAEnum(TicketPriority), default=TicketPriority.medium, index=True)
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), index=True)
    due_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    assignee: Mapped[Optional[Employee]] = relationship(back_populates="tickets")
    __table_args__ = (Index("ix_tickets_status_priority", "status", "priority"),)

class Shift(UUIDPK, TimestampMixin, Base):
    __tablename__ = "shifts"
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    starts_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str] = mapped_column(String(120), default="HQ")
    __table_args__ = (
        UniqueConstraint("employee_id", "starts_at", name="uq_shifts_emp_start"),
        Index("ix_shifts_emp_time", "employee_id", "starts_at", "ends_at"),
    )

class OnCall(UUIDPK, TimestampMixin, Base):
    __tablename__ = "oncall"
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[dt.date] = mapped_column(Date, index=True)  # Monday
    rotation: Mapped[str] = mapped_column(String(80), default="primary")
    __table_args__ = (UniqueConstraint("week_start", "rotation", name="uq_oncall_week_rotation"),)
```

## 5. Pydantic v2 Schemas (copy-paste → `app/schemas/*.py`)

```python
# app/schemas/hrms.py
import uuid, datetime as dt
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class Strict(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True, use_enum_values=True)

# --- Candidate ---
class CandidateIn(Strict):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9\- ]{7,20}$")
    source: str = "referral"
    score: Decimal | None = Field(default=None, ge=0, le=100)

class CandidateOut(CandidateIn):
    id: uuid.UUID
    stage: str = "applied"
    created_at: dt.datetime

# --- Employee ---
class EmployeeIn(Strict):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    dept: str
    title: str
    candidate_id: uuid.UUID | None = None

class EmployeeOut(EmployeeIn):
    id: uuid.UUID
    emp_code: str
    is_active: bool = True

# --- Laptop ---
class LaptopIn(Strict):
    asset_tag: str = Field(pattern=r"^LAP-[0-9]{4,}$")
    serial: str = Field(min_length=4)
    model: str
    specs: dict = Field(default_factory=dict)

class LaptopAssign(Strict):
    assignee_id: uuid.UUID  # server flips status in_stock -> assigned in one txn

# --- Ticket ---
class TicketIn(Strict):
    title: str = Field(min_length=4, max_length=240)
    body: str | None = None
    priority: str = "medium"
    assignee_id: uuid.UUID | None = None
    due_at: dt.datetime | None = None
    @field_validator("priority")
    @classmethod
    def _prio(cls, v): return v if v in {"low","medium","high","urgent"} else "medium"

# --- Shift / OnCall ---
class ShiftIn(Strict):
    employee_id: uuid.UUID
    starts_at: dt.datetime
    ends_at: dt.datetime
    location: str = "HQ"
    @field_validator("ends_at")
    @classmethod
    def _order(cls, v, info):
        if info.data.get("starts_at") and v <= info.data["starts_at"]:
            raise ValueError("ends_at must be after starts_at")
        return v

class OnCallIn(Strict):
    employee_id: uuid.UUID
    week_start: dt.date
    rotation: str = "primary"
```

## 6. Idempotency Table DDL + Helper (copy-paste)

```sql
-- Postgres (prod)
CREATE TABLE IF NOT EXISTS idempotency_keys (
  key         TEXT PRIMARY KEY,
  endpoint    TEXT NOT NULL,
  status_code INT NOT NULL DEFAULT 200,
  body        JSONB NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at  TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '24 hours'
);
CREATE INDEX IF NOT EXISTS ix_idem_expires ON idempotency_keys (expires_at);
-- janitor: DELETE FROM idempotency_keys WHERE expires_at < now();

-- SQLite (demo)
CREATE TABLE IF NOT EXISTS idempotency_keys (
  key TEXT PRIMARY KEY,
  endpoint TEXT NOT NULL,
  status_code INTEGER NOT NULL DEFAULT 200,
  body TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at TEXT NOT NULL DEFAULT (datetime('now','+1 day'))
);
```

```python
# SQLAlchemy model (works both dialects — JSON-as-TEXT on SQLite)
from sqlalchemy import Text
from .base import Base, TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column
import datetime as dt

class IdempotencyKey(TimestampMixin, Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text)
    status_code: Mapped[int] = mapped_column(default=200)
    body: Mapped[str] = mapped_column(Text, default="{}")
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
```

```python
# FastAPI dependency sketch
import json, hashlib
from fastapi import Request
async def idempotent(request: Request, session, key: str, handler):
    h = hashlib.sha256(f"{request.url.path}:{key}".encode()).hexdigest()[:32]
    if row := await session.get(IdempotencyKey, h):
        return json.loads(row.body), row.status_code
    data, code = await handler()
    session.add(IdempotencyKey(key=h, endpoint=request.url.path, status_code=code, body=json.dumps(data)))
    await session.commit()
    return data, code
```

## 7. Alembic Quickstart (copy-paste)

```bash
alembic init -t async alembic
# alembic.ini → sqlalchemy.url = driver:// (overridden by env in env.py)
# alembic/env.py:
#   from app.models.hrms import Base; target_metadata = Base.metadata
#   from app.db import DATABASE_URL; config.set_main_option("sqlalchemy.url", DATABASE_URL)
alembic revision --autogenerate -m "hrms init"
alembic upgrade head
```

**SQLite portability tip:** `UUID`/`JSONB` don't exist in SQLite — add in `base.py`:

```python
import uuid as _uuid
from sqlalchemy import CHAR, TypeDecorator, Text
import json
class GUID(TypeDecorator):
    impl = CHAR(36); cache_ok = True
    def process_bind_param(self, v, d): return str(v) if v else None
    def process_result_value(self, v, d): return _uuid.UUID(v) if v else None
# then: PK = GUID on sqlite via variant: mapped_column(GUID().with_variant(postgresql.UUID(as_uuid=True), "postgresql"))
```

---
*Refs: Pydantic v2 docs (strict mode, TypeAdapter), SQLAlchemy 2.0 async + `mapped_column`, Alembic async template, asyncpg prepared-statement/cache notes, SQLite WAL (`PRAGMA journal_mode=WAL`).*
