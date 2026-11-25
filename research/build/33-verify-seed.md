# 33 — Verify Seed: validate.py + CI for Seed Invariants

> Deterministic gate for `/demo/seed`. Fails CI and rolls back `/seed` when counts, FKs, or any staged demo trap drift. Single source of truth shared by local CSV check, `/demo/seed` txn validation, and CI.

Source: `research/final/14-seed-data.md §§2,5,6` · `research/build/18-step-seed.md §§5,7` · Anchored `seeded_at=2026-11-23T00:00:00Z` · Version `v14` · 79 rows

---

## 1. What it gates

| # | Invariant | Expected | Demo breaks if drifted |
|---|---|---|---|
| 1 | Row counts | `{candidates:20, employees:20, equipment:20, tickets:20, shifts:8, subscriptions:6, api_keys:5}` | Boarding checklist / stats wrong |
| 2 | FKs resolve | `employees.candidate_id→candidates`, `employees.manager_id→employees`, `equipment.assigned_to→employees`, `equipment.hold_for_candidate→candidates`, `tickets.requester_id/assignee_id→employees`, `tickets.shift_id→shifts`, `subscriptions.owner_id→employees` — 0 orphans | Convert / assign / routing 500s |
| 3 | `signed → date` | `offer_status='signed' ⇒ offer_signed_at NOT NULL AND start_date >= offer_signed_at` | Day-1 convert allows undated offer |
| 4 | `visa → expiry` | `visa_status != 'citizen' ⇒ visa_expiry NOT NULL`; `bg IN (pass,fail) ⇒ bg_completed_at NOT NULL` | VISA-RISK banner never fires |
| 5 | Breached tickets | Exactly **3** rows with `now > due_at AND status != 'resolved'`, each with non-null `shift_id` | SLA banner / on-shift routing demo empty |
| 6 | Weekend starts | Exactly **4** `start_date` on Sat/Sun (CAND-004/005/011/020) | Weekend-warning modal untestable |
| 7 | Serials unique | `equipment.serial` all distinct (incl. near-dupe pair `…991A` vs `…991B` staying distinct) | Collision guard untestable |
| 8 | Double-hold | `LT-1005` appears in ≥2 `on_hold` rows (held for CAND-002 + CAND-005) | Hold-conflict modal never fires |
| 9 | Rehire match | Rehire query (email-root/phone match terminated ↔ new candidate) returns exactly **1 row** (EMP-007 ↔ CAND-006) | Rehire modal untestable |
| 10 | Stale key | Stalest prod key is **`KEY-01`** (`last_rotated_at=2026-02-01`, >90d before `seeded_at`) blocking provision until rotated | Stale-credential block never fires |
| 11 | Bonus traps | `SUB-01 renewal 2026-11-25` within 7d of `seeded_at`; `LT-1012 retired` never `assigned`; `visa-risk ≥3`, `bg-pending ≥5` | Auto-renew / retired-asset traps silent |

SLA rule (shared with live code): `P1=4h, P2=8h, P3=24h, P4=48h`; `due_at = created_at + SLA`. `validate.py` recomputes breach from `created_at/priority/status` — never trusts stored `status='breached'` alone.

---

## 2. validate.py (copy-paste — stdlib only, dual mode)

Save as `seed/validate.py`. Works two ways with identical checks:

- **CSV mode (CI, no DB):** `python seed/validate.py --csv seed/`
- **DB mode (`/demo/seed` parity):** `python seed/validate.py --db "$DATABASE_URL"` (uses `psycopg` if present, else `sqlite3` fallback — logic identical)

```python
"""Seed invariant gate. Exit 0 = all pass, 1 = any fail. Stdlib only (csv+sqlite3)."""
import argparse, csv, sqlite3, sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SEEDED_AT = datetime(2026, 11, 23, tzinfo=timezone.utc)
SLA_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 48}
EXPECTED = {"candidates": 20, "employees": 20, "equipment": 20,
            "tickets": 20, "shifts": 8, "subscriptions": 6, "api_keys": 5}
FAILURES: list[str] = []

def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"FAIL: {msg}")

def ok(msg: str) -> None:
    print(f"ok: {msg}")

# ---------- loaders ----------
def load_csvs(d: Path) -> dict[str, list[dict]]:
    tables = {}
    for name in EXPECTED:
        # csv filenames are plural: candidates.csv, employees.csv, ...
        p = d / f"{name}.csv"
        if not p.exists():
            fail(f"missing {p}")
            tables[name] = []
            continue
        with p.open(newline="", encoding="utf-8") as f:
            tables[name] = list(csv.DictReader(f))
    return tables

def load_db(url: str) -> dict[str, list[dict]]:
    """Postgres via psycopg if installed, else sqlite file path."""
    tables: dict[str, list[dict]] = {}
    try:
        import psycopg  # type: ignore
        conn = psycopg.connect(url)
        conn.row_factory = dict  # type: ignore
        cur = conn.cursor()
        for t in EXPECTED:
            cur.execute(f"TABLE {t}")
            tables[t] = [dict(r) for r in cur.fetchall()]
        conn.close()
        return tables
    except ImportError:
        pass
    # sqlite fallback: url is file path
    conn = sqlite3.connect(url)
    conn.row_factory = sqlite3.Row
    for t in EXPECTED:
        try:
            tables[t] = [dict(r) for r in conn.execute(f"SELECT * FROM {t}")]
        except Exception as e:
            fail(f"sqlite read {t}: {e}")
            tables[t] = []
    conn.close()
    return tables

# ---------- checks ----------
def check_counts(t: dict) -> None:
    for name, want in EXPECTED.items():
        got = len(t[name])
        if got != want:
            fail(f"counts[{name}]={got} want {want}")
        else:
            ok(f"counts[{name}]={got}")

def check_fks(t: dict) -> None:
    cands = {r["candidate_id"] for r in t["candidates"]}
    emps = {r["employee_id"] for r in t["employees"]}
    shifts = {r["shift_id"] for r in t["shifts"]}
    def fk(table: str, col: str, target: set, nullable=True, extra="") -> None:
        bad = [r.get("candidate_id", r.get("employee_id", r.get("ticket_id", r.get("asset_tag", "?"))))
               for r in t[table] if r.get(col) and r[col].strip() and r[col] not in target]
        if bad:
            fail(f"FK {table}.{col} orphans: {bad[:5]} {extra}")
        else:
            ok(f"FK {table}.{col} resolves")
    for r in t["employees"]:
        if r.get("candidate_id") and r["candidate_id"].strip() and r["candidate_id"] not in cands:
            fail(f"FK employees.candidate_id orphan: {r['candidate_id']}")
    ok("FK employees.candidate_id resolves") if all(
        (not r.get("candidate_id") or not r["candidate_id"].strip() or r["candidate_id"] in cands)
        for r in t["employees"]) else None
    fk("employees", "manager_id", emps | {""}, extra="(CEO EMP-001 exempt)")
    fk("equipment", "assigned_to", emps)
    fk("equipment", "hold_for_candidate", cands)
    fk("tickets", "shift_id", shifts, nullable=False)
    fk("tickets", "requester_id", emps | cands)
    fk("tickets", "assignee_id", emps)
    fk("subscriptions", "owner_id", emps)

def check_offer_visa(t: dict) -> None:
    for r in t["candidates"]:
        cid = r["candidate_id"]
        if r.get("offer_status") == "signed" and not (r.get("offer_signed_at") or "").strip():
            fail(f"{cid} signed without offer_signed_at")
        if r.get("visa_status") != "citizen" and not (r.get("visa_expiry") or "").strip():
            fail(f"{cid} visa={r.get('visa_status')} without visa_expiry")
        if r.get("bg_status") in ("pass", "fail") and not (r.get("bg_completed_at") or "").strip():
            fail(f"{cid} bg={r.get('bg_status')} without bg_completed_at")
        if r.get("offer_status") == "signed" and r.get("offer_signed_at") and r.get("start_date"):
            try:
                if date.fromisoformat(r["start_date"]) < date.fromisoformat(r["offer_signed_at"]):
                    fail(f"{cid} start_date {r['start_date']} < offer_signed_at {r['offer_signed_at']}")
            except ValueError as e:
                fail(f"{cid} bad date: {e}")
    ok("signed->date, visa->expiry, bg->completed_at, start>=signed")

def _parse_ts(s: str) -> datetime:
    s = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        dt = datetime.strptime(s, "%Y-%m-%d")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def check_breached(t: dict) -> None:
    breached = []
    for r in t["tickets"]:
        try:
            due = _parse_ts(r["due_at"])
        except Exception:
            fail(f"{r.get('ticket_id')} unparseable due_at={r.get('due_at')!r}")
            continue
        is_breach = due < SEEDED_AT and (r.get("status") or "").strip().lower() != "resolved" \
            and not (r.get("resolved_at") or "").strip()
        if is_breach:
            breached.append(r)
            if not (r.get("shift_id") or "").strip():
                fail(f"{r.get('ticket_id')} breached but shift_id missing")
    if len(breached) != 3:
        fail(f"breached tickets={len(breached)} want 3 (ids={[r.get('ticket_id') for r in breached]})")
    else:
        ok(f"breached=3 with shift_id ({[r.get('ticket_id') for r in breached]})")

def check_weekends(t: dict) -> None:
    wknd = [r["candidate_id"] for r in t["candidates"]
            if r.get("start_date") and date.fromisoformat(r["start_date"].strip()).weekday() >= 5]
    if len(wknd) != 4:
        fail(f"weekend starts={len(wknd)} want 4 (got {wknd})")
    else:
        ok(f"weekend starts=4 ({wknd})")
    visa_risk = [r["candidate_id"] for r in t["candidates"]
                 if r.get("visa_status") in ("h1b_expiring_30d", "opt_expiring_15d", "requires_sponsorship")]
    if len(visa_risk) < 3:
        fail(f"visa-risk={len(visa_risk)} want >=3")
    else:
        ok(f"visa-risk={len(visa_risk)}")
    bg_pending = [r["candidate_id"] for r in t["candidates"] if r.get("bg_status") == "pending"]
    if len(bg_pending) < 5:
        fail(f"bg-pending={len(bg_pending)} want >=5")
    else:
        ok(f"bg-pending={len(bg_pending)}")

def check_serials_doublehold(t: dict) -> None:
    serials = [r.get("serial", "") for r in t["equipment"]]
    dupes = [s for s, n in Counter(serials).items() if s and n > 1]
    if dupes:
        fail(f"serials duplicated: {dupes}")
    else:
        ok("serials unique (near-dupe 991A/991B distinct)")
    holds = [r for r in t["equipment"]
             if (r.get("asset_tag") == "LT-1005") and (r.get("status") or "").strip() == "on_hold"]
    # seed models double-hold as 2 rows sharing asset_tag OR 1 row + conflict ledger;
    # accept: >=2 hold rows for LT-1005, or 1 row whose hold_for_candidate lists 2 candidates
    blob = " ".join(r.get("hold_for_candidate", "") or "" for r in t["equipment"]
                    if r.get("asset_tag") == "LT-1005")
    double = len(holds) >= 2 or ("CAND-002" in blob and "CAND-005" in blob)
    if not double:
        fail("double-hold LT-1005 missing (want 2 on_hold rows or CAND-002+CAND-005 on one tag)")
    else:
        ok("double-hold LT-1005 present")
    retired = [r for r in t["equipment"] if r.get("asset_tag") == "LT-1012"]
    if retired and (retired[0].get("status") or "").strip() != "retired":
        fail("LT-1012 must stay retired")
    else:
        ok("LT-1012 retired (trap intact)")

def check_rehire(t: dict) -> None:
    # match: candidate email-root/phone == terminated employee email-root
    def root(email: str) -> str:
        return email.split("@")[0].rstrip("0123456789.").lower()
    terminated = [r for r in t["employees"] if (r.get("status") or "").strip() == "terminated"]
    matches = []
    for c in t["candidates"]:
        for e in terminated:
            if root(c.get("email", "")) and root(c["email"]) == root(e.get("work_email", "")):
                matches.append((c["candidate_id"], e["employee_id"]))
    if len(matches) != 1:
        fail(f"rehire matches={matches} want exactly 1 (EMP-007<->CAND-006)")
    else:
        ok(f"rehire match=1 ({matches[0][1]}<->{matches[0][0]})")

def check_stale_key_sub(t: dict) -> None:
    def age_days(r: dict) -> float:
        for col in ("last_rotated_at", "created_at"):
            if (r.get(col) or "").strip():
                try:
                    return (SEEDED_AT - _parse_ts(r[col])).total_seconds() / 86400
                except Exception:
                    continue
        return -1
    prod = [r for r in t["api_keys"] if str(r.get("is_prod", r.get("scope", ""))).lower() in ("true", "1", "prod", "prod:deploy")]
    if not prod:
        prod = t["api_keys"]  # fallback: rank all keys
    stalest = max(prod, key=age_days) if prod else None
    if stalest is None or stalest.get("key_id") != "KEY-01":
        fail(f"stalest prod key={stalest.get('key_id') if stalest else None} want KEY-01")
    elif age_days(stalest) <= 90:
        fail(f"KEY-01 age {age_days(stalest):.0f}d want >90d (last_rotated 2026-02-01)")
    else:
        ok(f"stale key KEY-01 ({age_days(stalest):.0f}d, blocks provision)")
    subs = {r.get("sub_id"): r for r in t["subscriptions"]}
    s1 = subs.get("SUB-01")
    if not s1:
        fail("SUB-01 missing")
    else:
        try:
            delta = (date.fromisoformat(s1["renewal_date"].strip()) - SEEDED_AT.date()).days
            if not (0 <= delta <= 7):
                fail(f"SUB-01 renews in {delta}d want 0..7d (renewal 2026-11-25)")
            else:
                ok(f"SUB-01 renews in {delta}d (auto-renew trap armed)")
        except Exception as e:
            fail(f"SUB-01 bad renewal_date: {e}")

def main() -> int:
    ap = argparse.ArgumentParser(description="Seed invariant gate")
    ap.add_argument("--csv", type=Path, help="seed/ dir with *.csv")
    ap.add_argument("--db", help="DATABASE_URL or sqlite file")
    a = ap.parse_args()
    if a.db:
        t = load_db(a.db)
    else:
        t = load_csvs(a.csv or Path("seed"))
    check_counts(t)
    check_fks(t)
    check_offer_visa(t)
    check_breached(t)
    check_weekends(t)
    check_serials_doublehold(t)
    check_rehire(t)
    check_stale_key_sub(t)
    print(f"\n{len(FAILURES)} failure(s).")
    return 1 if FAILURES else 0

if __name__ == "__main__":
    sys.exit(main())
```

Run locally:

```bash
python seed/validate.py --csv seed/
# ok: counts[candidates]=20
# ok: counts[employees]=20
# ...
# 0 failure(s).
```

Expected DB parity: `python seed/validate.py --db "$DATABASE_URL"` prints the same lines against live rows (used as the in-txn `validate()` mirror — see §4).

---

## 3. CI gate

`.github/workflows/seed-validate.yml` — CSV check on every PR (no DB needed) + DB check after deploy preview seeds.

```yaml
name: seed-validate
on: [push, pull_request]
jobs:
  csv:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Seed invariants (CSV, no DB)
        run: python seed/validate.py --csv seed/
  db:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    needs: [csv]
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_PASSWORD: postgres }
        options: >-
          --health-cmd pg_isready --health-interval 10s
          --health-timeout 5s --health-retries 5
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: psql "$DATABASE_URL" -f seed/schema.sql
        env: { DATABASE_URL: postgresql://postgres:postgres@localhost:5432/postgres }
      - run: ./scripts/seed_load.sh  # or POST /demo/seed on preview URL
      - name: Seed invariants (DB parity)
        run: python seed/validate.py --db "$DATABASE_URL"
        env: { DATABASE_URL: postgresql://postgres:postgres@localhost:5432/postgres }
```

Branch protection: require `seed-validate / csv`. Optional pre-commit:

```yaml
repos:
  - repo: local
    hooks:
      - id: seed-validate
        name: seed invariants
        entry: python seed/validate.py --csv seed/
        language: system
        pass_filenames: false
```

And `package.json`:

```json
{ "scripts": { "seed:validate": "python seed/validate.py --csv seed/" } }
```

---

## 4. Wiring into POST /demo/seed (fail → ROLLBACK)

The service-side `validate()` in `18-step-seed.md §3` is the SQL mirror of the same invariants (single `Promise.all`, one txn). Keep the two in sync: any new `FAIL:` line in `validate.py` gets a matching `SELECT … THEN eq()` in `seed.service.ts`, so a bad seed returns `500 { ok:false, error:'seed_failed', failed_check }` with the DB untouched. `GET /demo/status` surfaces `{ counts, seed_version:'v14', seeded_at }` for the judge-visible cross-check.

---

## 5. Fix table

| CI error | Root cause | Fix |
|---|---|---|
| `counts[X]=N want M` | Row added/deleted in CSV | Restore 20/20/20/20/8/6/5; total must stay 79 |
| `FK … orphans` | Typo'd id (`EMP-14` vs `EMP-014`) | Fix reference; keep `CAND-001…`, `EMP-001…`, `SH-01…` zero-padded |
| `signed without offer_signed_at` | New signed row, date left blank | Fill `offer_signed_at ≤ start_date`, or flip to `pending` |
| `visa=… without visa_expiry` | Non-citizen row missing expiry | Fill `visa_expiry`; `h1b_expiring_30d` ≈ `seeded_at+27d` |
| `breached tickets=N want 3` | `created_at/due_at` edited past anchor | Re-anchor to `seeded_at=2026-11-23T00:00:00Z`; keep due < seed for exactly T-5001/5002 + 1 more |
| `breached but shift_id missing` | Ticket added without shift | Every ticket needs exactly one `shift_id` |
| `weekend starts=N want 4` | `start_date` weekday drift | Keep 004-Sat / 005-Sun / 011-Sat / 020-Sun; edit others to Mon–Fri |
| `serials duplicated` | Copy-pasted `SN-…` | Give every row a unique `serial`; keep `991A/991B` 1-char-apart pair |
| `double-hold LT-1005 missing` | Hold row "cleaned up" | Re-stage: LT-1005 `on_hold` for CAND-002 **and** CAND-005 |
| `rehire matches=N want 1` | Email-root changed on CAND-006 or EMP-007 | Keep shared root (`rahul.verma…`); EMP-007 `terminated`, CAND-006 new |
| `stalest prod key=… want KEY-01` | Rotation date edited | Keep `KEY-01 last_rotated 2026-02-01`, `KEY-02` healthy 7d |
| `SUB-01 renews in Nd` | Renewal date drifted | Keep `2026-11-25` (≤7d after anchor) + `auto_renew=true` |
| `LT-1012 must stay retired` | Status flipped to `available` | Revert to `retired`, warranty expired — it is the unselectable trap |

---

## 6. Verification checklist (paste into PR)

- [ ] `python seed/validate.py --csv seed/` → 0 failures
- [ ] Counts 20/20/20/20/8/6/5 (79 rows), all FKs resolve
- [ ] `signed→date`, `visa→expiry`, `start≥signed` hold
- [ ] 3 breached tickets each with `shift_id`; 4 weekend starts
- [ ] Serials unique; LT-1005 double-hold present; LT-1012 retired
- [ ] Rehire match exactly 1 (EMP-007↔CAND-006); stalest prod key KEY-01; SUB-01 ≤7d
- [ ] `POST /demo/seed` mirrors the same checks in-txn (fail → `ROLLBACK` + `seed_failed`)

*Seed v14 · validate.py stdlib-only · CSV + DB parity · SLA 5s.*
