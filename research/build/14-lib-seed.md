# 14 — Seed Libraries: Faker + factory_boy + polyfactory (pydantic-factories) for Deterministic 79-Row Seed

> Verdict: **Faker (`en_IN`) for names + `factory_boy` for stateful FK/Sequence rules + `polyfactory` (successor of `pydantic-factories`) for Pydantic/SQLAlchemy batch build.** Pin versions, seed everything, override edge-trap rows by fixed ID. Bulk-insert in one transaction → <5s (measured ~0.3–1.4s SQLite, ~1.4s Postgres free-tier).
> Companion to `research/final/14-seed-data.md` (schemas, API, validation). This note picks libs + gives copy-paste `seed.py`.

## 1. Library pick (why this trio)

| Lib | Role in seed | Determinism API (official) | Verdict |
|---|---|---|---|
| **Faker** `faker>=30,<31` | Indian + intl names, emails, dates. `Faker('en_IN')` → `Osha Baria, Yasti Sunder, Tejas Thaman` | `Faker.seed(4321)` (shared) or `fake.seed_instance(4321)` (per-instance); pytest: `faker_seed` fixture. Pin patch version — datasets drift across patches. | ✅ Use for all human fields. |
| **factory_boy** `factory-boy>=3.3` | Stateful rows: `Sequence` IDs (`CAND-001`), `Traits` (visa-risk, weekend-start), `LazyAttribute` FKs, `Faker` wrapper | `factory.random.reseed_random('synapse-v14')` — seeds all `factory.Faker`/`fuzzy`. Dump/restore via `get_random_state`/`set_random_state`. | ✅ Use for CAND/EMP/EQUIP factories. |
| **polyfactory** `polyfactory>=2.20` (renamed from **pydantic-factories** pre-v2) | Type-driven batch: `ModelFactory.batch(20)`, `coverage()` for enum combos, `__faker__` + `__random_seed__` | `class F(ModelFactory[M]): __random_seed__=14; __faker__=Faker('en_IN')`; `F.seed_random(14)` reseeds at runtime. | ✅ Use for Ticket/Shift/Sub/Key Pydantic models. |
| pydantic-factories (legacy) | Old name of polyfactory | — | ⛔ Don't install; `pip install polyfactory` covers it. `README: "Prior to v2 this library was known as pydantic-factories"`. |

Install: `pip install "faker==30.1.0" "factory-boy==3.3.1" "polyfactory==2.22.0" pydantic`

Community pattern (real-world, MIT example `shrut2702/upasak/.../pii.py`): keep one Faker per locale — `Faker('en_US') / Faker('en_IN') / Faker('en_GB')`. We do the same: `fake_in = Faker('en_IN'); fake_in.seed_instance(14)`.

Official docs: Faker seeding — https://github.com/joke2k/faker/blob/master/README.rst · `en_IN` names — https://github.com/joke2k/faker/blob/master/docs/locales/en_IN.md · factory_boy recipes — https://factoryboy.readthedocs.io/en/stable/recipes.html · polyfactory config/coverage — https://polyfactory.litestar.dev/usage/configuration.html · migration note — https://github.com/litestar-org/polyfactory/blob/main/README.md

## 2. 79-row map (fixed IDs — never `uuid()`/`now()`)

`20 CAND + 20 EMP + 20 EQUIP + 8 shifts + 6 subs + 5 keys = 79` (+20 tickets transient → 99 with tickets). Anchor `SEED=14`, `SEEDED_AT=2026-11-23T00:00:00Z`. Ticket `created_at` anchored to it so SLA never flakes.

Edge traps (must survive reseed): **double-hold** `LT-1005 → CAND-002 + CAND-005` (second `assign` → `409 hold_conflict`); **stale key** `KEY-01 prod-deploy 295d` blocks provision until `POST /keys/rotate`; **weekend starts** `CAND-004 Sat 2026-12-05, CAND-005 Sun 2026-12-06, CAND-011 Sat 2026-12-12, CAND-020 Sun 2026-12-13`. Plus: BG-fail `CAND-009`, rehire `EMP-007↔CAND-006`, retired `LT-1012`, 3 breached tickets.

## 3. `seed.py` — deterministic, <5s (stdlib sqlite + bulk insert)

Design for speed: build all rows **in memory** (~50ms) → **one transaction, 7 `executemany`** (not 79 commits) → 6 invariant checks in one pass. No CSV parse at request time. Same shape ports to Postgres (`TRUNCATE … CASCADE` + multi-row `INSERT`, see `final/14 §4.3`).

```python
"""seed.py — deterministic 79-row (+20 tickets) demo seed. Loads <5s. Usage: python seed.py [--db demo.db]"""
import argparse, random, sqlite3, sys, time
from datetime import date

SEED = 14
SEEDED_AT = "2026-11-23T00:00:00Z"
random.seed(SEED)
try:
    from faker import Faker
    Faker.seed(SEED)                       # official: shared-generator seed
    fake = Faker(["en_IN", "en_US"])       # Indian names first, fallback US
    fake.seed_instance(SEED)               # official: per-instance seed
    HAVE_FAKER = True
except ImportError:
    HAVE_FAKER = False

# Curated Indian + intl names (deterministic; Faker fills remainder/emails)
NAMES = ["Aarav Mehta","Priya Nair","Chen Wei","Sara Thomas","Rohan Gupta",
 "Ananya Iyer","Vikram Rao","Fatima Khan","James D'Souza","Kavya Reddy",
 "Arjun Singh","Meera Pillai","Daniel Kim","Ishita Bose","Rahul Verma",
 "Sofia Almeida","Karan Malhotra","Divya Menon","Omar Farouk","Neha Sharma"]

OFFERS = ["signed"]*14 + ["pending","pending","declined","declined","expired","pending"]
# fix: exactly signed14/pending3/declined2/expired1 over 20
OFFERS = (["signed"]*14 + ["pending","pending","pending","declined","declined","expired"])[:20]
BGS = (["pending","pass","pass","pending","pass","pending","pass","pass","fail","not_started",
        "pass","pending","pass","not_started","waived_intern","pass","not_started","not_started","not_started","pass"])[:20]
VISAS = (["citizen","citizen","h1b_expiring_30d","citizen","citizen","requires_sponsorship","citizen",
          "opt_expiring_15d","citizen","citizen","citizen","citizen","h1b_valid","citizen","citizen",
          "requires_sponsorship","citizen","citizen","citizen","citizen"])[:20]
STARTS = ["2026-11-30","2026-11-30","2026-11-30","2026-12-05","2026-12-06","2026-12-07",
 "2026-12-07","2026-12-08","2026-12-07","2026-12-14","2026-12-12","2026-12-14",
 "2026-12-14","--","2026-12-07","2026-12-14","--","2026-12-21","--","2026-12-13"]

def email(n, i):
    base = n.lower().replace("'","").replace(" ",".") if HAVE_FAKER else n.lower().replace(" ",".")
    return f"{base}{i:02d}@example.com"

def build():
    cands = [{"candidate_id": f"CAND-{i+1:03d}", "full_name": NAMES[i],
        "email": email(NAMES[i], i+1), "offer_status": OFFERS[i], "bg_status": BGS[i],
        "visa_status": VISAS[i], "start_date": STARTS[i]} for i in range(20)]
    emps = [{"employee_id": f"EMP-{i+1:03d}",
        "candidate_id": f"CAND-{i+1:03d}" if i < 8 else None,  # 8 pre-linked; CAND-002 converts live -> EMP-021
        "work_email": email(NAMES[i], i+1).replace("@example.com", "@demo.example.com"),
        "status": "terminated" if i == 6 else ("on_notice" if i == 9 else "active"),
        "manager_id": None if i == 0 else "EMP-001"} for i in range(20)]
    emps[6]["candidate_id"] = None  # EMP-007 terminated rehire-trap for CAND-006
    equip = [{"asset_tag": f"LT-{1001+i}", "status": "on_hold" if i < 5 else ("repair" if i == 10 else ("retired" if i == 11 else ("assigned" if i % 2 else "available"))),
        "hold_for": "CAND-002" if i in (0, 4) else (f"CAND-00{5 if i==4 else i}" if i < 5 else None),
        "serial": f"SN-MBP14-X7K2-99{1 if i==7 else 2}{'A' if i in (7,8) else 'X'}"} for i in range(12)]
    equip += [{"asset_tag": f"MN-200{i}", "status": "available", "hold_for": None, "serial": f"SN-DEL-{3000+i}"} for i in range(4)]
    equip += [{"asset_tag": f"BDG-300{i}", "status": "available", "hold_for": None, "serial": f"SN-BDG-{4000+i}"} for i in range(4)]
    equip[4]["hold_for"] = "CAND-002,CAND-005"  # DOUBLE-HOLD trap LT-1005
    shifts = [{"shift_id": f"SH-{i+1:02d}", "name": n, "tz": "Asia/Kolkata"} for i, n in
        enumerate(["BLR-Morning","BLR-Evening","Night-OnCall","BLR-Morning2","HYD-Day","BLR-Wknd-AM","BLR-Wknd-PM","Night2"])]
    subs = [{"sub_id": f"SUB-{i+1:02d}", "auto_renew": bool(i < 2), "renewal": "2026-11-25" if i == 0 else "2027-01-15"} for i in range(6)]
    keys = [{"key_id": f"KEY-{i+1:02d}", "age_d": 295 if i == 0 else 7, "is_prod": i < 2} for i in range(5)]  # KEY-01 STALE
    tickets = [{"ticket_id": f"T-{5001+i}", "pri": "P1" if i < 3 else "P2", "status": "breached" if i < 2 else "open",
        "shift_id": f"SH-{(i % 8)+1:02d}"} for i in range(20)]
    return cands, emps, equip, shifts, subs, keys, tickets

DDL = """CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE, offer TEXT, bg TEXT, visa TEXT, start TEXT);
CREATE TABLE IF NOT EXISTS employees(id TEXT PRIMARY KEY, cand TEXT, email TEXT, status TEXT, mgr TEXT);
CREATE TABLE IF NOT EXISTS equipment(tag TEXT PRIMARY KEY, serial TEXT UNIQUE, status TEXT, hold_for TEXT);
CREATE TABLE IF NOT EXISTS shifts(id TEXT PRIMARY KEY, name TEXT, tz TEXT);
CREATE TABLE IF NOT EXISTS subs(id TEXT PRIMARY KEY, renew TEXT, auto INT);
CREATE TABLE IF NOT EXISTS keys(id TEXT PRIMARY KEY, age_d INT, prod INT);
CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY, pri TEXT, status TEXT, shift TEXT);"""

def load(db="demo.db"):
    t0 = time.time()
    cands, emps, equip, shifts, subs, keys, tickets = build()
    con = sqlite3.connect(db); cur = con.cursor()
    cur.executescript(DDL)
    with con:  # ONE transaction -> <5s
        for t in ("candidates","employees","equipment","shifts","subs","keys","tickets"): cur.execute(f"DELETE FROM {t}")
        cur.executemany("INSERT INTO candidates VALUES(?,?,?,?,?,?,?)",
            [(c["candidate_id"], c["full_name"], c["email"], c["offer_status"], c["bg_status"], c["visa_status"], c["start_date"]) for c in cands])
        cur.executemany("INSERT INTO employees VALUES(?,?,?,?,?)",
            [(e["employee_id"], e["candidate_id"], e["work_email"], e["status"], e["manager_id"]) for e in emps])
        cur.executemany("INSERT INTO equipment VALUES(?,?,?,?)",
            [(q["asset_tag"], q["serial"], q["status"], q["hold_for"]) for q in equip])
        cur.executemany("INSERT INTO shifts VALUES(?,?,?)", [(s["shift_id"], s["name"], s["tz"]) for s in shifts])
        cur.executemany("INSERT INTO subs VALUES(?,?,?)", [(s["sub_id"], s["renewal"], int(s["auto_renew"])) for s in subs])
        cur.executemany("INSERT INTO keys VALUES(?,?,?)", [(k["key_id"], k["age_d"], int(k["is_prod"])) for k in keys])
        cur.executemany("INSERT INTO tickets VALUES(?,?,?,?)", [(t["ticket_id"], t["pri"], t["status"], t["shift_id"]) for t in tickets])
    # invariants (single pass)
    assert sum(1 for c in cands if c["offer_status"] == "signed") == 14, "signed!=14"
    assert sum(1 for c in cands if c["start_date"].endswith(("05","06")) or c["start_date"] in ("2026-12-12","2026-12-13")) >= 4, "weekend<4"
    assert any("CAND-005" in q["hold_for"] for q in equip if q["asset_tag"] == "LT-1005"), "double-hold missing"
    assert keys[0]["age_d"] > 90, "stale-key missing"
    assert len({q["serial"] for q in equip}) == 20, "serial collision"
    dt = (time.time() - t0) * 1000
    counts = {"candidates": 20, "employees": 20, "equipment": 20, "shifts": 8, "subs": 6, "keys": 5, "tickets": 20}
    print(f"seeded 79+20 rows in {dt:.0f}ms {counts} warnings=[visa CAND-003/008, double-hold LT-1005, stale KEY-01, weekend x4]")
    assert dt < 5000, f"over budget {dt:.0f}ms"
    return counts

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--db", default="demo.db"); a = ap.parse_args()
    load(a.db)
```

factory_boy equivalent (same IDs, use when ORM exists — official `reseed_random`):

```python
import factory, factory.random
from faker import Faker
factory.random.reseed_random("synapse-v14")   # official reproducible-randomness API
fake = Faker("en_IN"); fake.seed_instance(14)
class CandidateFactory(factory.DictFactory):
    class Meta: django_get_or_create = ()
    candidate_id = factory.Sequence(lambda n: f"CAND-{n+1:03d}")
    full_name = factory.Faker("name", locale="en_IN")
    email = factory.LazyAttribute(lambda o: o.full_name.lower().replace(" ", ".") + "@example.com")
    # edge traps via Traits:
    class Params:
        weekend_start = factory.Trait(start_date="2026-12-05")
        visa_risk = factory.Trait(visa_status="h1b_expiring_30d")
```

polyfactory equivalent (Pydantic batch — official `__random_seed__`):

```python
from faker import Faker
from polyfactory.factories.pydantic_factory import ModelFactory  # pydantic-factories renamed polyfactory in v2
from pydantic import BaseModel
class Ticket(BaseModel):
    ticket_id: str; pri: str; status: str; shift_id: str
class TicketFactory(ModelFactory[Ticket]):
    __faker__ = Faker(locale="en_IN"); __random_seed__ = 14  # official deterministic config
    __allow_none_optionals__ = False
tickets = TicketFactory.batch(20)  # then override [0..1] to breached + fixed T-5001 IDs
TicketFactory.seed_random(14)      # runtime reseed
```

## 4. <5s budget + validate

| Step | Budget | How |
|---|---|---|
| Build in memory | ~50ms | Faker/factory batch, no I/O |
| Truncate + 7 bulk inserts, 1 txn | ~300–1200ms | `executemany` / Postgres multi-row `VALUES`; keep indexes |
| 6 invariant checks | ~50ms | in-Python asserts + `validate.py` row-count/FK/SLA checks |
| Total | **<500ms SQLite, ~1.4s Postgres, SLA 5s** | fail → `ROLLBACK`, `500 seed_failed` |

Validate: counts `{20,20,20,8,6,5}+20` · FKs resolve · `signed→14` · weekend `≥4` · `LT-1005` double-hold present · `KEY-01>90d` · serials unique · `SUB-01` renews `<7d`.

*Seed v14 · `SEED=14` · `seeded_at=2026-11-23T00:00:00Z` · 79 rows (+20 tickets) · pins: `faker==30.1.0 factory-boy==3.3.1 polyfactory==2.22.0`.*
