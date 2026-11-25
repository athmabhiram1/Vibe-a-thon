"""seed.py — deterministic v14 demo seed (SQLite-only, raw SQL, no ORM).

CSVs are the human-editable source of truth; this loader runs them in ONE
transaction (7 bulk executemany batches + infra rows), validates in-txn via
validate.check_all (any failure -> ROLLBACK), then VACUUM INTO a snapshot.
Reset = file copy of the snapshot (see --reset).

  python seed/seed.py [--db seed/demo.db] [--csv seed/]     # full reload
  python seed/seed.py --reset [--db seed/demo.db]           # snapshot restore
  python seed/validate.py --db seed/demo.db                 # DB parity check

Fixed IDs; timestamps anchored relative to seed run time (seed_now()):
re-runs on any date reproduce identical offsets (3 breached, rest future).
Budget: total < 5000ms SLA (target ~1.5s; SQLite typically < 500ms).
"""
import argparse
import csv
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate  # noqa: E402  (stdlib-only sibling: check_all/load_sqlite)

SEED_VERSION = "v14"
# Legacy anchor (v14 CSV dates are expressed against this instant). The live
# seed time is computed per-run by seed_now(): all ticket created/due,
# subscription renewal, api-key rotation and created_at stamps are shifted so
# their offsets from seed time are identical on every run. SEED_NOW env
# (ISO-8601) monkeypatches "now" for time-travel tests, e.g.
# SEED_NOW=2026-12-24T00:00:00Z python seed/seed.py --db /tmp/t.db
OLD_SEEDED_AT = datetime(2026, 11, 23, tzinfo=timezone.utc)
SCHEMA_SQL = HERE / "schema.sql"

SLA_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 48}
# Hours before seed-time each ticket was created. Breached trio (T-5001 P1,
# T-5002 P2, T-5019 P3-stealth) have created_ago > SLA so due lands 1-6h in
# the past; every other open/in_progress row has created_ago < SLA so due
# lands in the future. Resolved rows are fully in the past (resolved_at set,
# never counted as breached). due_at is ALWAYS created_at + SLA.
TICKET_CREATED_AGO_H = {
    "T-5001": 10, "T-5002": 11, "T-5003": 2, "T-5004": 3, "T-5005": 2,
    "T-5006": 6, "T-5007": 8, "T-5008": 72, "T-5009": 96, "T-5010": 120,
    "T-5011": 72, "T-5012": 120, "T-5013": 48, "T-5014": 1, "T-5015": 2,
    "T-5016": 5, "T-5017": 10, "T-5018": 3, "T-5019": 28, "T-5020": 6,
}
BREACHED_IDS = {"T-5001", "T-5002", "T-5019"}  # unresolved + due < seed time
# Resolved tickets close this many hours BEFORE their due_at (on-time fix).
RESOLVED_LEAD_H = 1.5
# Subscription renewal offsets (days after seed time; mirrors CSV gaps from
# 2026-11-23: SUB-01 +2d trap, SUB-05 +27d, SUB-02 +53d, ...).
SUB_RENEW_IN_DAYS = {"SUB-01": 2, "SUB-02": 53, "SUB-03": 70,
                     "SUB-04": 107, "SUB-05": 27, "SUB-06": 129}


def seed_now() -> datetime:
    raw = os.environ.get("SEED_NOW", "").strip()
    if raw:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _shift_iso(s: str, delta: timedelta) -> str:
    """Shift an ISO-8601 Z timestamp by delta (preserves date-only strings)."""
    s = (s or "").strip()
    if not s:
        return s
    if "T" not in s:
        from datetime import date as _d
        return (_d.fromisoformat(s) + delta).isoformat()
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return _iso(dt + delta)

EXPECTED_ORDER = ["candidates", "employees", "equipment", "tickets",
                  "shifts", "subscriptions", "api_keys"]
# FK-safe insert order (parents first); deletes run in reverse.
DELETE_ORDER = ["idempotency_ledger", "audit_log", "api_keys", "subscriptions",
                "tickets", "equipment_holds", "equipment", "shift_members",
                "employees", "shifts", "candidates"]


def _nil(v: str | None) -> str | None:
    v = (v or "").strip()
    return v if v else None


def read_csvs(csv_dir: Path) -> dict[str, list[dict]]:
    tables: dict[str, list[dict]] = {}
    for name in EXPECTED_ORDER:
        with (csv_dir / f"{name}.csv").open(newline="", encoding="utf-8") as f:
            tables[name] = [dict(r) for r in csv.DictReader(f)]
    return tables


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA journal_mode = WAL;")
    con.execute("PRAGMA synchronous = NORMAL;")
    con.execute("PRAGMA busy_timeout = 5000;")
    con.execute("PRAGMA foreign_keys = ON;")
    con.row_factory = sqlite3.Row
    return con


def load(db_path: Path, csv_dir: Path, snapshot_path: Path,
         make_snapshot: bool = True) -> dict:
    if not (csv_dir / "candidates.csv").exists():
        raise SystemExit(f"CSVs not found in {csv_dir}")
    tables = read_csvs(csv_dir)
    # Anchor: every timestamp is relative to THIS run, so re-seeding on any
    # date yields the same offsets (3 breached, rest future) and live breach
    # counts stay 3 regardless of wall-clock run date.
    NOW = seed_now()
    SEEDED_AT = _iso(NOW)
    delta = NOW - OLD_SEEDED_AT  # shift applied to key/sub absolute dates
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    con = connect(db_path)
    try:
        # 0) schema (outside the seed TX; idempotent CREATE TABLE IF NOT EXISTS)
        s = time.perf_counter()
        con.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))
        timings["schema"] = (time.perf_counter() - s) * 1000

        cur = con.cursor()
        cur.execute("BEGIN IMMEDIATE")

        # 1) clear in FK-reverse order
        s = time.perf_counter()
        for tbl in DELETE_ORDER:
            cur.execute(f"DELETE FROM {tbl}")
        cur.execute("DELETE FROM sqlite_sequence WHERE name='audit_log'")
        timings["clear"] = (time.perf_counter() - s) * 1000

        # 2) seven bulk batches, parents first
        s = time.perf_counter()
        # -- candidates (20)
        cur.executemany(
            """INSERT INTO candidates (candidate_id,full_name,email,role,dept,offer_status,
               offer_signed_at,bg_status,bg_completed_at,visa_status,visa_expiry,
               start_date,source,phone,notes,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(r["candidate_id"], r["full_name"], r["email"], r["role"], r["dept"],
              r["offer_status"], _nil(r["offer_signed_at"]), r["bg_status"],
              _nil(r["bg_completed_at"]), r["visa_status"], _nil(r["visa_expiry"]),
              _nil(r["start_date"]), r["source"], _nil(r.get("phone")),
              r.get("notes", ""), SEEDED_AT)
             for r in tables["candidates"]])
        # -- shifts (8)
        cur.executemany(
            "INSERT INTO shifts (shift_id,name,start_time,end_time,timezone) VALUES (?,?,?,?,?)",
            [(r["shift_id"], r["name"], r["start_time"], r["end_time"], r["timezone"])
             for r in tables["shifts"]])
        # -- employees (20): two-pass for self-FKs (manager_id, rehire_of)
        cur.executemany(
            """INSERT INTO employees (employee_id,candidate_id,full_name,work_email,phone,
               dept,role,employment_type,status,join_date,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            [(r["employee_id"], _nil(r["candidate_id"]), r["full_name"], r["work_email"],
              _nil(r.get("phone")), r["dept"], r["role"], r["employment_type"],
              r["status"], r["join_date"], SEEDED_AT)
             for r in tables["employees"]])
        for r in tables["employees"]:
            if _nil(r.get("manager_id")) or _nil(r.get("rehire_of")):
                cur.execute(
                    "UPDATE employees SET manager_id=?, rehire_of=? WHERE employee_id=?",
                    (_nil(r.get("manager_id")), _nil(r.get("rehire_of")), r["employee_id"]))
        # -- shift_members (junction from shifts.csv member_ids)
        members = [(r["shift_id"], m.strip()) for r in tables["shifts"]
                   for m in (r.get("member_ids") or "").split(";") if m.strip()]
        cur.executemany("INSERT INTO shift_members (shift_id,employee_id) VALUES (?,?)", members)
        # -- equipment (20): canonical hold = single id in equipment.hold_for_candidate;
        # full conflict list -> equipment_holds ledger. LT-1005 staged conflict is
        # seeded deterministically here (canonical CAND-002 + ledger CAND-002/CAND-005).
        hold_lists: dict[str, list[str]] = {}
        equip_rows = []
        for r in tables["equipment"]:
            holds = [h.strip() for h in (r.get("hold_for_candidate") or "").replace(",", ";").split(";")
                     if h.strip()]
            if len(holds) > 1:
                raise SystemExit(
                    f"seed_failed: {r['asset_tag']} hold_for_candidate must be a single "
                    f"canonical id (got {holds!r}); conflict pair lives in equipment_holds")
            hold_lists[r["asset_tag"]] = holds
        # Staged LT-1005 double-hold: CSV carries the single canonical hold
        # (CAND-002); the conflicting second hold (CAND-005) is staged here so
        # equipment.hold_for_candidate stays single while equipment_holds has the pair.
        if hold_lists.get("LT-1005") == ["CAND-002"]:
            hold_lists["LT-1005"] = ["CAND-002", "CAND-005"]
        for r in tables["equipment"]:
            holds = hold_lists[r["asset_tag"]]
            equip_rows.append((r["asset_tag"], r["serial"], r["category"], r["model"],
                               r["status"], _nil(r.get("assigned_to")),
                               holds[0] if holds else None, r["location"],
                               r["po_number"], r["warranty_expiry"], SEEDED_AT))
        cur.executemany(
            """INSERT INTO equipment (asset_tag,serial,category,model,status,assigned_to,
               hold_for_candidate,location,po_number,warranty_expiry,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""", equip_rows)
        hold_rows = []
        n = 0
        for tag in sorted(hold_lists):
            for cand in hold_lists[tag]:
                n += 1
                hold_rows.append((f"HOLD-{n:03d}", tag, cand, "EMP-003", SEEDED_AT, None))
        cur.executemany(
            """INSERT INTO equipment_holds (hold_id,asset_tag,candidate_id,placed_by,placed_at,released_at)
               VALUES (?,?,?,?,?,?)""", hold_rows)
        # -- tickets (20): created/due recomputed from seed NOW.
        # due_at = created_at + priority SLA; the BREACHED_IDS trio lands
        # 1-6h in the past, open/in_progress land in the future, resolved
        # keep resolved_at (never breached). All other columns come from CSV
        # unchanged, so trap rows (T-5001 P1, T-5002 P2, T-5019 stealth) keep
        # their IDs/priority/status/shift.
        prio_of = {r["ticket_id"]: r["priority"] for r in tables["tickets"]}
        ticket_rows = []
        for r in tables["tickets"]:
            tid = r["ticket_id"]
            ago = TICKET_CREATED_AGO_H.get(tid)
            if ago is None:
                raise SystemExit(f"seed_failed: no created-ago offset for {tid}")
            sla = SLA_HOURS[r["priority"]]
            created = NOW - timedelta(hours=ago)
            due = created + timedelta(hours=sla)
            status = (r["status"] or "").strip().lower()
            if tid in BREACHED_IDS:
                assert due < NOW, f"{tid} offset must breach (due={due} now={NOW})"
                resolved = None
            elif status == "resolved":
                resolved = _iso(due - timedelta(hours=RESOLVED_LEAD_H))
            else:
                assert due > NOW, f"{tid} offset must be future-due (due={due} now={NOW})"
                resolved = None
            ticket_rows.append((tid, r["title"], _nil(r.get("requester_id")),
               _nil(r.get("requester_candidate")), _nil(r.get("assignee_id")),
               r["priority"], r["category"], r["status"], _iso(created),
               _iso(due), resolved, r["shift_id"], r["channel"]))
        cur.executemany(
            """INSERT INTO tickets (ticket_id,title,requester_id,requester_candidate,assignee_id,
               priority,category,status,created_at,due_at,resolved_at,shift_id,channel)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ticket_rows)
        # -- subscriptions (6): renewal_date anchored +N days from seed NOW
        # (SUB-01 +2d auto-renew trap stays armed on every run date).
        sub_rows = []
        for r in tables["subscriptions"]:
            renew_in = SUB_RENEW_IN_DAYS.get(r["sub_id"])
            if renew_in is None:
                raise SystemExit(f"seed_failed: no renew offset for {r['sub_id']}")
            sub_rows.append((r["sub_id"], r["tool"], int(r["seats"]), int(r["seat_cost_inr"]),
              (NOW + timedelta(days=renew_in)).date().isoformat(),
              int(r["auto_renew"]), _nil(r.get("cancelled_at")),
              _nil(r.get("owner_id")), SEEDED_AT))
        cur.executemany(
            """INSERT INTO subscriptions (sub_id,tool,seats,seat_cost_inr,renewal_date,
               auto_renew,cancelled_at,owner_id,created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            sub_rows)
        # -- api_keys (5): rotation/expiry shifted by (NOW - OLD_SEEDED_AT) so
        # KEY-01 stays the stalest prod key (295d, expired) on any run date.
        cur.executemany(
            """INSERT INTO api_keys (key_id,label,key_prefix,key_hash,created_at,
               last_rotated_at,expires_at,scope,is_prod)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            [(r["key_id"], r["label"], r["key_prefix"], r["key_hash"],
              _shift_iso(r["created_at"], delta),
              _shift_iso(r["last_rotated_at"], delta),
              _shift_iso(r["expires_at"], delta), r["scope"], int(r["is_prod"]))
             for r in tables["api_keys"]])
        for r in tables["api_keys"]:
            if _nil(r.get("replaces_key_id")) or _nil(r.get("revoked_at")):
                cur.execute(
                    "UPDATE api_keys SET replaces_key_id=?, revoked_at=? WHERE key_id=?",
                    (_nil(r.get("replaces_key_id")), _nil(r.get("revoked_at")), r["key_id"]))
        # -- audit_log: 2 exemplar rows (infra, excluded from 79-count)
        cur.executemany(
            """INSERT INTO audit_log (occurred_at,actor_id,action,entity,entity_id,reason,metadata)
               VALUES (?,?,?,?,?,?,?)""",
            [(SEEDED_AT, "EMP-002", "bg.override", "candidate", "CAND-009",
              "Family business affidavit received — HR override pending Day-1 re-check",
              '{"bg_status":"fail","overridden_by":"EMP-002"}'),
             (SEEDED_AT, "EMP-003", "equip.hold_conflict", "equipment", "LT-1005",
              "Double-hold staged: CAND-002 + CAND-005 — second assign must 409",
              '{"asset_tag":"LT-1005","holds":["CAND-002","CAND-005"]}'),
             ])
        # idempotency_ledger stays empty at seed.
        timings["insert"] = (time.perf_counter() - s) * 1000

        # 3) in-txn validation (same checks as CI): fail -> ROLLBACK
        s = time.perf_counter()
        snapshot = {tname: [dict(r) for r in cur.execute(f"SELECT * FROM {tname}")]
                    for tname in EXPECTED_ORDER}
        snapshot["equipment_holds"] = [dict(r) for r in cur.execute("SELECT * FROM equipment_holds")]
        snapshot["shift_members"] = [dict(r) for r in cur.execute("SELECT * FROM shift_members")]
        failures = validate.check_all(snapshot)
        timings["validate"] = (time.perf_counter() - s) * 1000
        if failures:
            con.rollback()
            raise SystemExit(f"seed_failed, rolled back: {failures}")
        con.commit()
        timings["total"] = (time.perf_counter() - t0) * 1000

        # 4) snapshot (outside TX: VACUUM INTO needs no open write TX; target must not exist)
        if make_snapshot:
            s = time.perf_counter()
            if snapshot_path.exists():
                snapshot_path.unlink()  # VACUUM INTO refuses an existing non-empty file
            cur.execute(f"VACUUM INTO '{snapshot_path}'")
            timings["snapshot"] = (time.perf_counter() - s) * 1000
    finally:
        con.close()

    counts = {k: len(v) for k, v in validate.load_sqlite(db_path).items() if k in EXPECTED_ORDER}
    sla_ok = timings["total"] < 5000
    print(f"seeded {SEED_VERSION} anchored {SEEDED_AT} (relative offsets; breach=3 stable) counts={counts}")
    print(f"timings_ms={ {k: round(v) for k, v in timings.items()} } "
          f"SLA_5000ms={'PASS' if sla_ok else 'FAIL'}")
    print("warnings=['CAND-003 visa risk', '3 SLA-breached tickets staged', "
          "'1 double-hold conflict staged (LT-1005)', 'KEY-01 stale 295d blocks provision', "
          "'SUB-01 renews seed+2d (auto-renew ON)']")
    return {"seed_version": SEED_VERSION, "counts": counts, "timings_ms": timings}


def reset_from_snapshot(db_path: Path, snapshot_path: Path) -> dict:
    """Fast reset: file copy of the post-seed snapshot (<1.5s target).

    Safe because: no connection is open during the copy, and afterwards we
    reopen + re-apply WAL (VACUUM INTO outputs rollback-journal mode).
    """
    t0 = time.perf_counter()
    if not snapshot_path.exists():
        raise SystemExit(f"no snapshot at {snapshot_path}; run seed.py first")
    shutil.copyfile(snapshot_path, db_path)
    con = connect(db_path)  # re-applies journal_mode=WAL on the restored copy
    counts = {k: len(v) for k, v in validate.load_sqlite(db_path).items() if k in EXPECTED_ORDER}
    con.close()
    ms = (time.perf_counter() - t0) * 1000
    print(f"reset to {SEED_VERSION} counts={counts} duration_ms={ms:.0f}")
    return {"reset_to_version": SEED_VERSION, "counts": counts, "duration_ms": ms}


def main() -> int:
    ap = argparse.ArgumentParser(description="v14 demo seed (SQLite, single TX)")
    ap.add_argument("--db", type=Path, default=HERE / "demo.db")
    ap.add_argument("--csv", type=Path, default=HERE)
    ap.add_argument("--snapshot", type=Path, default=HERE / "seed-snapshot.db")
    ap.add_argument("--reset", action="store_true", help="restore snapshot via file copy")
    ap.add_argument("--no-snapshot", action="store_true", help="skip VACUUM INTO step")
    a = ap.parse_args()
    if a.reset:
        reset_from_snapshot(a.db, a.snapshot)
    else:
        load(a.db, a.csv, a.snapshot, make_snapshot=not a.no_snapshot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
