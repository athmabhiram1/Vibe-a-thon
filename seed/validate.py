"""Seed invariant gate — v14. Exit 0 = all pass, 1 = any fail. Stdlib only (csv+sqlite3).

Dual mode with identical checks:
  python seed/validate.py --csv seed/        # CI, no DB
  python seed/validate.py --db seed/demo.db  # DB parity (mirrors /demo/seed in-txn checks)

Also importable: `from validate import check_all, load_csvs, load_sqlite` (seed.py reuses it
inside the seed transaction: any failure -> ROLLBACK).
"""
import argparse
import csv
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SEEDED_AT = datetime(2026, 11, 23, tzinfo=timezone.utc)  # legacy CSV anchor
SLA_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 48}
EXPECTED = {"candidates": 20, "employees": 20, "equipment": 20,
            "tickets": 20, "shifts": 8, "subscriptions": 6, "api_keys": 5}


# ---------- loaders ----------
def load_csvs(d: Path) -> dict[str, list[dict]]:
    tables: dict[str, list[dict]] = {}
    for name in EXPECTED:
        p = d / f"{name}.csv"
        if not p.exists():
            tables[name] = []
            continue
        with p.open(newline="", encoding="utf-8") as f:
            tables[name] = [dict(r) for r in csv.DictReader(f)]
    return tables


def load_sqlite(db_path: str | Path) -> dict[str, list[dict]]:
    """Read the 7 counted tables from a SQLite file. Extra infra tables
    (shift_members, equipment_holds, audit_log) are attached for trap checks."""
    tables: dict[str, list[dict]] = {}
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        for t in EXPECTED:
            try:
                tables[t] = [dict(r) for r in conn.execute(f"SELECT * FROM {t}")]
            except sqlite3.Error:
                tables[t] = []
        # infra tables (optional in CSV mode, present in DB mode)
        try:
            tables["equipment_holds"] = [dict(r) for r in conn.execute("SELECT * FROM equipment_holds")]
        except sqlite3.Error:
            tables["equipment_holds"] = []
        try:
            tables["shift_members"] = [dict(r) for r in conn.execute("SELECT * FROM shift_members")]
        except sqlite3.Error:
            tables["shift_members"] = []
    finally:
        conn.close()
    return tables


# ---------- checks (each appends to `failures`, prints ok:/FAIL:) ----------
def check_counts(t: dict, failures: list[str]) -> None:
    for name, want in EXPECTED.items():
        got = len(t.get(name, []))
        if got != want:
            failures.append(f"counts[{name}]={got} want {want}")
            print(f"FAIL: counts[{name}]={got} want {want}")
        else:
            print(f"ok: counts[{name}]={got}")


def check_fks(t: dict, failures: list[str]) -> None:
    def fail(msg: str) -> None:
        failures.append(msg)
        print(f"FAIL: {msg}")

    cands = {r.get("candidate_id", "") for r in t["candidates"]}
    emps = {r.get("employee_id", "") for r in t["employees"]}
    shifts = {r.get("shift_id", "") for r in t["shifts"]}

    def fk(table: str, col: str, target: set, label: str = "") -> None:
        bad = [r.get("candidate_id") or r.get("employee_id") or r.get("ticket_id")
               or r.get("asset_tag") or r.get("sub_id") or r.get("key_id") or "?"
               for r in t[table] if (r.get(col) or "").strip() and r[col].strip() not in target]
        if bad:
            fail(f"FK {table}.{col} orphans: {bad[:5]} {label}")
        else:
            print(f"ok: FK {table}.{col} resolves")

    # employees.candidate_id (nullable)
    bad_cand = [r["employee_id"] for r in t["employees"]
                if (r.get("candidate_id") or "").strip() and r["candidate_id"] not in cands]
    if bad_cand:
        fail(f"FK employees.candidate_id orphans: {bad_cand[:5]}")
    else:
        print("ok: FK employees.candidate_id resolves")
    fk("employees", "manager_id", emps | {""}, "(CEO EMP-001 exempt)")
    fk("employees", "rehire_of", emps)
    fk("equipment", "assigned_to", emps)
    # equipment.hold_for_candidate is the SINGLE canonical hold id.
    # The full conflict pair lives in equipment_holds (DB infra). Multi-hold
    # CSV hacks ("CAND-002;CAND-005") are rejected: exactly one answer.
    bad_multi = [r.get("asset_tag") for r in t["equipment"]
                 if ";" in (r.get("hold_for_candidate") or "")
                 or "," in (r.get("hold_for_candidate") or "")]
    if bad_multi:
        fail(f"equipment.hold_for_candidate must be single canonical id (multi-hold CSV hack on {bad_multi[:5]}; pair lives in equipment_holds)")
    else:
        print("ok: equipment.hold_for_candidate single canonical (no ;-list hack)")
    bad_holds = sorted({(r.get("hold_for_candidate") or "").strip() for r in t["equipment"]
                        if (r.get("hold_for_candidate") or "").strip()}
                       - cands)
    if bad_holds:
        fail(f"FK equipment.hold_for_candidate orphans: {bad_holds[:5]} ")
    else:
        print("ok: FK equipment.hold_for_candidate resolves")
    fk("tickets", "requester_id", emps | cands)
    # requester_candidate (nullable; exactly one of requester_id/requester_candidate must be set)
    bad_req = [r.get("ticket_id") for r in t["tickets"]
               if (r.get("requester_candidate") or "").strip() and r["requester_candidate"] not in cands]
    if bad_req:
        fail(f"FK tickets.requester_candidate orphans: {bad_req[:5]}")
    else:
        print("ok: FK tickets.requester_candidate resolves")
    missing_req = [r.get("ticket_id") for r in t["tickets"]
                   if not (r.get("requester_id") or "").strip()
                   and not (r.get("requester_candidate") or "").strip()]
    if missing_req:
        fail(f"tickets without requester: {missing_req[:5]}")
    else:
        print("ok: every ticket has a requester")
    fk("tickets", "assignee_id", emps)
    fk("tickets", "shift_id", shifts)
    fk("subscriptions", "owner_id", emps)


def check_offer_visa(t: dict, failures: list[str]) -> None:
    def fail(msg: str) -> None:
        failures.append(msg)
        print(f"FAIL: {msg}")

    for r in t["candidates"]:
        cid = r.get("candidate_id", "?")
        if r.get("offer_status") == "signed" and not (r.get("offer_signed_at") or "").strip():
            fail(f"{cid} signed without offer_signed_at")
        if r.get("visa_status") != "citizen" and not (r.get("visa_expiry") or "").strip():
            fail(f"{cid} visa={r.get('visa_status')} without visa_expiry")
        if r.get("bg_status") in ("pass", "fail") and not (r.get("bg_completed_at") or "").strip():
            fail(f"{cid} bg={r.get('bg_status')} without bg_completed_at")
        if r.get("offer_status") == "signed" and r.get("offer_signed_at") and r.get("start_date"):
            try:
                if date.fromisoformat(r["start_date"].strip()) < date.fromisoformat(r["offer_signed_at"].strip()):
                    fail(f"{cid} start_date {r['start_date']} < offer_signed_at {r['offer_signed_at']}")
            except ValueError as e:
                fail(f"{cid} bad date: {e}")
    print("ok: signed->date, visa->expiry, bg->completed_at, start>=signed")


def _parse_ts(s: str) -> datetime:
    s = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        dt = datetime.strptime(s, "%Y-%m-%d")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _ref_time(t: dict) -> datetime:
    """Seed-time reference inferred from the data (not wall-clock).

    seed.py anchors every timestamp relative to its run time, so the check
    must compare against the dataset's own clock: the newest ticket
    created_at (≈ seed time). Falls back to the legacy SEEDED_AT constant
    when no parseable ticket exists (empty tables). Because the reference is
    frozen in the data, breach/stale-key/renewal counts are identical whether
    validated today or 30 days later, and identical across re-seeds on any
    date (still exactly 3 breached).
    """
    latest: datetime | None = None
    for r in t.get("tickets", []):
        try:
            dt = _parse_ts(r.get("created_at", ""))
        except Exception:
            continue
        if latest is None or dt > latest:
            latest = dt
    return latest if latest is not None else SEEDED_AT


def check_breached(t: dict, failures: list[str]) -> None:
    ref = _ref_time(t)
    breached = []
    for r in t["tickets"]:
        try:
            due = _parse_ts(r["due_at"])
        except Exception:
            failures.append(f"{r.get('ticket_id')} unparseable due_at={r.get('due_at')!r}")
            print(f"FAIL: {r.get('ticket_id')} unparseable due_at={r.get('due_at')!r}")
            continue
        is_breach = due < ref and (r.get("status") or "").strip().lower() != "resolved" \
            and not (r.get("resolved_at") or "").strip()
        if is_breach:
            breached.append(r)
            if not (r.get("shift_id") or "").strip():
                failures.append(f"{r.get('ticket_id')} breached but shift_id missing")
                print(f"FAIL: {r.get('ticket_id')} breached but shift_id missing")
    if len(breached) != 3:
        failures.append(f"breached tickets={len(breached)} want 3 (ids={[r.get('ticket_id') for r in breached]})")
        print(f"FAIL: breached tickets={len(breached)} want 3 (ids={[r.get('ticket_id') for r in breached]})")
    else:
        print(f"ok: breached=3 with shift_id ({[r.get('ticket_id') for r in breached]}) vs ref {ref.isoformat()}")


def check_weekends(t: dict, failures: list[str]) -> None:
    wknd = [r["candidate_id"] for r in t["candidates"]
            if (r.get("start_date") or "").strip()
            and date.fromisoformat(r["start_date"].strip()).weekday() >= 5]
    if len(wknd) != 4:
        failures.append(f"weekend starts={len(wknd)} want 4 (got {wknd})")
        print(f"FAIL: weekend starts={len(wknd)} want 4 (got {wknd})")
    else:
        print(f"ok: weekend starts=4 ({wknd})")
    visa_risk = [r["candidate_id"] for r in t["candidates"]
                 if r.get("visa_status") in ("h1b_expiring_30d", "opt_expiring_15d", "requires_sponsorship")]
    if len(visa_risk) < 3:
        failures.append(f"visa-risk={len(visa_risk)} want >=3")
        print(f"FAIL: visa-risk={len(visa_risk)} want >=3")
    else:
        print(f"ok: visa-risk={len(visa_risk)}")
    bg_pending = [r["candidate_id"] for r in t["candidates"] if r.get("bg_status") == "pending"]
    if len(bg_pending) < 5:
        failures.append(f"bg-pending={len(bg_pending)} want >=5")
        print(f"FAIL: bg-pending={len(bg_pending)} want >=5")
    else:
        print(f"ok: bg-pending={len(bg_pending)}")


def check_serials_doublehold(t: dict, failures: list[str]) -> None:
    serials = [r.get("serial", "") for r in t["equipment"]]
    dupes = [s for s, n in Counter(serials).items() if s and n > 1]
    if dupes:
        failures.append(f"serials duplicated: {dupes}")
        print(f"FAIL: serials duplicated: {dupes}")
    else:
        print("ok: serials unique (near-dupe 991A/991B distinct)")
    # Canonical double-hold: equipment.LT-1005 carries the SINGLE canonical hold
    # (CAND-002, status on_hold); the conflict pair (CAND-002 + CAND-005) lives
    # in equipment_holds as two open ledger rows. One answer, no disjunction.
    lt = [r for r in t["equipment"] if r.get("asset_tag") == "LT-1005"]
    if not lt or (lt[0].get("status") or "").strip() != "on_hold" \
            or (lt[0].get("hold_for_candidate") or "").strip() != "CAND-002":
        failures.append("double-hold LT-1005 missing canonical hold (want on_hold + hold_for_candidate=CAND-002)")
        print("FAIL: double-hold LT-1005 missing canonical hold (want on_hold + hold_for_candidate=CAND-002)")
    else:
        print("ok: double-hold LT-1005 canonical hold CAND-002 (equipment row single)")
    holds = t.get("equipment_holds", [])
    if holds:
        # DB mode: ledger must hold the pair.
        open_pair = sorted((r.get("candidate_id") or "") for r in holds
                           if r.get("asset_tag") == "LT-1005"
                           and not (r.get("released_at") or "").strip())
        if open_pair != ["CAND-002", "CAND-005"]:
            failures.append(f"double-hold LT-1005 ledger={open_pair} want ['CAND-002', 'CAND-005'] (2 open equipment_holds rows)")
            print(f"FAIL: double-hold LT-1005 ledger={open_pair} want ['CAND-002', 'CAND-005'] (2 open equipment_holds rows)")
        else:
            print("ok: double-hold LT-1005 ledger pair CAND-002+CAND-005 (equipment_holds)")
    else:
        # CSV mode: no holds ledger file; canonical single row is the assertion
        # (seed.py expands it to the ledger pair in DB mode).
        print("ok: double-hold ledger check skipped in CSV mode (canonical single asserted; DB expands to pair)")
    retired = [r for r in t["equipment"] if r.get("asset_tag") == "LT-1012"]
    if retired and (retired[0].get("status") or "").strip() != "retired":
        failures.append("LT-1012 must stay retired")
        print("FAIL: LT-1012 must stay retired")
    else:
        print("ok: LT-1012 retired (trap intact)")


def check_rehire(t: dict, failures: list[str]) -> None:
    def root(email: str) -> str:
        return email.split("@")[0].rstrip("0123456789.").lower()

    terminated = [r for r in t["employees"] if (r.get("status") or "").strip() == "terminated"]
    matches = []
    for c in t["candidates"]:
        for e in terminated:
            if root(c.get("email", "")) and root(c["email"]) == root(e.get("work_email", "")):
                matches.append((c["candidate_id"], e["employee_id"]))
    if len(matches) != 1:
        failures.append(f"rehire matches={matches} want exactly 1 (EMP-007<->CAND-006)")
        print(f"FAIL: rehire matches={matches} want exactly 1 (EMP-007<->CAND-006)")
    else:
        print(f"ok: rehire match=1 ({matches[0][1]}<->{matches[0][0]})")


def check_stale_key_sub(t: dict, failures: list[str]) -> None:
    ref = _ref_time(t)

    def age_days(r: dict) -> float:
        for col in ("last_rotated_at", "created_at"):
            if (r.get(col) or "").strip():
                try:
                    return (ref - _parse_ts(r[col])).total_seconds() / 86400
                except Exception:
                    continue
        return -1

    prod = [r for r in t["api_keys"] if str(r.get("is_prod", r.get("scope", ""))).lower()
            in ("true", "1", "prod", "prod:deploy")]
    if not prod:
        prod = t["api_keys"]  # fallback: rank all keys
    stalest = max(prod, key=age_days) if prod else None
    if stalest is None or stalest.get("key_id") != "KEY-01":
        failures.append(f"stalest prod key={stalest.get('key_id') if stalest else None} want KEY-01")
        print(f"FAIL: stalest prod key={stalest.get('key_id') if stalest else None} want KEY-01")
    elif age_days(stalest) <= 90:
        failures.append(f"KEY-01 age {age_days(stalest):.0f}d want >90d (stale prod key)")
        print(f"FAIL: KEY-01 age {age_days(stalest):.0f}d want >90d (stale prod key)")
    else:
        print(f"ok: stale key KEY-01 ({age_days(stalest):.0f}d, blocks provision)")
    subs = {r.get("sub_id"): r for r in t["subscriptions"]}
    s1 = subs.get("SUB-01")
    if not s1:
        failures.append("SUB-01 missing")
        print("FAIL: SUB-01 missing")
    else:
        try:
            delta = (date.fromisoformat(s1["renewal_date"].strip()) - ref.date()).days
            if not (0 <= delta <= 7):
                failures.append(f"SUB-01 renews in {delta}d want 0..7d (auto-renew trap)")
                print(f"FAIL: SUB-01 renews in {delta}d want 0..7d (auto-renew trap)")
            else:
                print(f"ok: SUB-01 renews in {delta}d (auto-renew trap armed)")
        except Exception as e:
            failures.append(f"SUB-01 bad renewal_date: {e}")
            print(f"FAIL: SUB-01 bad renewal_date: {e}")


# One deterministic on-call row per demo team (mirrors hr_service.db.get_oncall:
# roster row matches when s.name == team OR member dept == team; get_oncall
# falls back to the first roster row, so any exact s.name match resolves).
# GET /hr/oncall?team=<team> must never 404 on stage.
ONCALL_TEAMS = ["support-night"]


def _roster_rows(t: dict, team: str) -> list[tuple[str, str]]:
    """Resolve (shift_id, employee_id) roster rows for `team` in CSV or DB mode."""
    shifts = {r.get("shift_id"): r for r in t.get("shifts", [])}
    emps = {r.get("employee_id"): r for r in t.get("employees", [])}
    members: list[tuple[str, str]]
    if t.get("shift_members"):
        members = [(m.get("shift_id", ""), m.get("employee_id", ""))
                   for m in t["shift_members"]]
    else:
        # CSV mode: junction lives in shifts.csv:member_ids.
        members = [(r.get("shift_id", ""), m.strip())
                   for r in t.get("shifts", [])
                   for m in (r.get("member_ids") or "").split(";") if m.strip()]
    rows = []
    for sid, eid in members:
        s = shifts.get(sid, {})
        e = emps.get(eid, {})
        if s.get("name") == team or (e.get("dept") or "") == team:
            rows.append((sid, eid))
    return rows


def check_oncall(t: dict, failures: list[str]) -> None:
    for team in ONCALL_TEAMS:
        rows = _roster_rows(t, team)
        if not rows:
            failures.append(f"on-call {team}: 0 roster rows (GET /hr/oncall would 404; want >=1 shift/shift_members row)")
            print(f"FAIL: on-call {team}: 0 roster rows (GET /hr/oncall would 404; want >=1 shift/shift_members row)")
            continue
        det = sorted(f"{sid}/{eid}" for sid, eid in rows)
        print(f"ok: on-call {team} resolves ({len(rows)} roster row(s): {det[0]}{'...' if len(det) > 1 else ''})")


def check_all(t: dict) -> list[str]:
    """Run every invariant; return list of failure strings (empty = green)."""
    failures: list[str] = []
    check_counts(t, failures)
    check_fks(t, failures)
    check_offer_visa(t, failures)
    check_breached(t, failures)
    check_weekends(t, failures)
    check_serials_doublehold(t, failures)
    check_rehire(t, failures)
    check_stale_key_sub(t, failures)
    check_oncall(t, failures)
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed invariant gate (v14, stdlib only)")
    ap.add_argument("--csv", type=Path, help="seed/ dir with *.csv")
    ap.add_argument("--db", help="sqlite file path")
    a = ap.parse_args()
    if a.db:
        t = load_sqlite(a.db)
    else:
        t = load_csvs(a.csv or Path(__file__).resolve().parent)
    failures = check_all(t)
    print(f"\n{len(failures)} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
