"""Synapse Custom safety tool: guarded onboarding composite (stage-then-activate).

Single @mcp.tool `onboard` (explicit name=) composing 8 private helpers:

    _verify_offer -> _bg_gate -> _rbac -> _stage
        -> _hold -> _schedule -> _preview -> _activate

Safety contract (plan.md S5 + research/final/05 + 13 + brainstorm/04):
  - CITE preview+hash -> CHECK scope/hash/approval -> ACT -> RECORD audit line.
  - Stage (confirm=False) returns a WRITE PREVIEW + preview_hash; no writes happen.
  - Activate requires confirm=True AND the exact preview_hash.
  - Idempotency: (actor, operation, key) PK in sqlite; same key+hash replays the
    cached result, same key+different hash -> 409 CONFLICT, never re-executes.
  - `${ENV:VAR}` secret refs are redacted at every sink; hashes run over the
    redacted canonical form.
  - audit.jsonl hash chain: sha256(prev_hash || canonical_json(line_without_hash)),
    genesis prev = "0"*64, seq dense from 1.

FastMCP 4.2.4 API. Stdlib + fastmcp only. No mount/namespace needed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

from fastmcp import FastMCP

mcp = FastMCP(name="OnboardingSafetyServer")

# --------------------------------------------------------------------------
# Constants / paths (overridable via env for tests)
# --------------------------------------------------------------------------

LEDGER_PATH = os.environ.get("SAFETY_LEDGER_PATH", "safety_ledger.db")
AUDIT_PATH = os.environ.get("SAFETY_AUDIT_PATH", "audit.jsonl")
PREVIEW_TTL_S = 10 * 60  # approvals/previews valid 10 min
SCHEMA_VERSION = 1
OPERATION = "onboard.execute"

# Role -> scopes (deny-closed: unknown tool/op or missing scope => deny).
SCOPES: dict[str, str] = {
    "onboard.execute": "onboarding:write",
    "onboard.preview": "onboarding:read",
}
# Demo actor scopes. Wired to real JWT claims in production (see 13-safety-audit
# S2); here the actor's scopes travel in ACTOR_SCOPES env (comma-separated).
DEFAULT_ACTOR = os.environ.get("SAFETY_ACTOR", "user:demo-agent")

# Secret hygiene: client args may carry ${ENV:VAR} refs. Redact at every sink.
ENV_REF_RE = re.compile(r"\$\{ENV:[A-Za-z_][A-Za-z0-9_]*\}")
SECRET_VALUE_RE = re.compile(r"(ghp_|xoxb-|sk-|AKIA)[\w-]+")

TERMINATED_EMPLOYEES = {"EMP-007"}  # rehire trap
RETIRED_LAPTOPS = {"LT-1012"}  # retired trap
HELD_LAPTOPS = {"LT-1005"}  # double-hold conflict trap

CLASS_C_COOLDOWN_S = 30.0  # same-approver re-confirmation cooldown (13 S3/S7)


def _hr_base() -> str:
    """Real HR service base URL (env-overridable; read at call time for tests)."""
    return (os.environ.get("HR_BASE_URL", "http://localhost:8001") or "").rstrip("/")


def _it_base() -> str:
    """Real IT service base URL (env-overridable; read at call time for tests)."""
    return (os.environ.get("IT_BASE_URL", "http://localhost:8002") or "").rstrip("/")


# Prompt-injection shapes the eval also blocks (eval/run.py INJECTION_RE core):
# override/skip-checks/SQL-escape/fake-approval/attacker shapes. Any hit in the
# tool args or prompt blob => deny-closed, never executes.
INJECTION_RE = re.compile(
    r"ignore\s+previous|system\s*:|skip[_\s-]?"
    r"(bg|visa|checks|policy|approval)|demo_mode|drop\s+table|"
    r"or\s+['\"]?1['\"]?\s*=\s*['\"]?1|;\s*--|approve\s+apv_0+|attacker@",
    re.I,
)


def _injection_hit(*texts: str) -> bool:
    blob = " ".join(t for t in texts if t)
    return bool(blob) and INJECTION_RE.search(blob) is not None


def _classify_risk(stored_plan: dict) -> tuple[str, str]:
    """Class B (single approval) vs Class C (double approval) per 13 S3.

    Class C (destructive / elevated-risk onboarding) when any holds:
      - background check not a clean pass (pending/waived/... needs 2nd eyes)
      - weekend start (orientation cover risk)
    Everything else is routine Class B. Returns (class, reason).
    """
    bg = str(stored_plan.get("bg_status", "") or "").lower()
    orient = stored_plan.get("orientation") or {}
    weekend = bool(orient.get("weekend_start", False)) if isinstance(orient, dict) else False
    if bg and bg != "pass":
        return "C", f"elevated_risk:bg_{bg}"
    if weekend:
        return "C", "elevated_risk:weekend_start"
    return "B", "routine"


def _http_get_json(url: str, timeout_s: float = 10.0) -> tuple[int | None, dict]:
    """GET JSON over stdlib urllib. Returns (status, body). status None = unreachable."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return resp.status, {"raw": raw}
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", "replace")
        except Exception:
            raw = ""
        try:
            return exc.code, json.loads(raw) if raw else {"detail": raw}
        except json.JSONDecodeError:
            return exc.code, {"detail": raw}
    except Exception as exc:  # connection refused / timeout / DNS
        return None, {"detail": f"upstream_unavailable: {exc}"}


def _http_post_json(url: str, payload: dict, timeout_s: float = 10.0) -> tuple[int | None, dict]:
    """POST JSON over stdlib urllib. Returns (status, body). status None = unreachable."""
    data = json.dumps(payload).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return resp.status, {"raw": raw}
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", "replace")
        except Exception:
            raw = ""
        try:
            return exc.code, json.loads(raw) if raw else {"detail": raw}
        except json.JSONDecodeError:
            return exc.code, {"detail": raw}
    except Exception as exc:  # connection refused / timeout / DNS
        return None, {"detail": f"upstream_unavailable: {exc}"}


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical(obj: object) -> str:
    """Canonical JSON: sorted keys, no whitespace, unicode preserved."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact(text: str) -> str:
    """Redact ${ENV:VAR} refs and secret-shaped values at every sink."""
    text = ENV_REF_RE.sub("[REDACTED]", text)
    text = SECRET_VALUE_RE.sub("[REDACTED]", text)
    return text


def _redacted_canonical(args: dict) -> str:
    return redact(_canonical(args))


def _preview_hash_for(plan: dict) -> str:
    # Hash over the REDACTED canonical form so hashes stay stable w/o leaking.
    return _sha256_hex(_redacted_canonical(plan))


def _actor_scopes() -> list[str]:
    raw = os.environ.get("SAFETY_ACTOR_SCOPES", "onboarding:read,onboarding:write")
    return [s.strip() for s in raw.split(",") if s.strip()]


# --------------------------------------------------------------------------
# sqlite ledger (idempotency + staged previews). PK = concurrency control.
# --------------------------------------------------------------------------

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(LEDGER_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS onboarding_idempotency (
             actor_id     TEXT NOT NULL,
             operation    TEXT NOT NULL,
             key          TEXT NOT NULL,
             request_hash TEXT NOT NULL,
             state        TEXT NOT NULL CHECK (state IN ('IN_PROGRESS','SUCCEEDED','FAILED')),
             lease_token  TEXT NOT NULL,
             resource_id  TEXT,
             response_code INTEGER,
             response_body TEXT,
             created_at   TEXT NOT NULL,
             expires_at   TEXT NOT NULL,
             PRIMARY KEY (actor_id, operation, key)
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS staged_previews (
             preview_id   TEXT PRIMARY KEY,
             preview_hash TEXT NOT NULL,
             actor_id     TEXT NOT NULL,
             plan_redacted TEXT NOT NULL,
             created_at   REAL NOT NULL
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS class_c_first_approval (
             preview_hash TEXT PRIMARY KEY,
             approver     TEXT NOT NULL,
             created_at   REAL NOT NULL
           )"""
    )
    conn.commit()
    return conn


def _ledger_lookup(actor: str, operation: str, key: str) -> dict | None:
    conn = _db()
    try:
        row = conn.execute(
            "SELECT request_hash, state, resource_id, response_code, response_body"
            " FROM onboarding_idempotency WHERE actor_id=? AND operation=? AND key=?",
            (actor, operation, key),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "request_hash": row[0],
        "state": row[1],
        "resource_id": row[2],
        "response_code": row[3],
        "response_body": json.loads(row[4]) if row[4] else None,
    }


def _ledger_insert_in_progress(actor: str, operation: str, key: str, req_hash: str) -> tuple[bool, str]:
    """INSERT ... ON CONFLICT DO NOTHING. Returns (won, lease_token)."""
    import uuid

    lease = str(uuid.uuid4())
    now = _utc_now_iso()
    exp = datetime.now(timezone.utc).timestamp() + 24 * 3600
    exp_iso = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")
    conn = _db()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO onboarding_idempotency"
            " (actor_id, operation, key, request_hash, state, lease_token,"
            "  response_code, created_at, expires_at)"
            " VALUES (?,?,?,?, 'IN_PROGRESS', ?, NULL, ?, ?)",
            (actor, operation, key, req_hash, lease, now, exp_iso),
        )
        conn.commit()
        return (cur.rowcount == 1), lease
    finally:
        conn.close()


def _ledger_mark(actor: str, operation: str, key: str, lease: str, state: str,
                 resource_id: str, code: int, body: dict) -> bool:
    """Fencing write: only the lease owner may flip IN_PROGRESS -> terminal."""
    conn = _db()
    try:
        cur = conn.execute(
            "UPDATE onboarding_idempotency SET state=?, resource_id=?,"
            " response_code=?, response_body=?"
            " WHERE actor_id=? AND operation=? AND key=?"
            " AND state='IN_PROGRESS' AND lease_token=?",
            (state, resource_id, code, redact(_canonical(body)),
             actor, operation, key, lease),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


def _ledger_release(actor: str, operation: str, key: str, lease: str) -> None:
    """Rollback a fencing claim (upstream unreachable before any write happened).

    Deletes the IN_PROGRESS row owned by this lease so a retry with the same
    key can proceed instead of wedging on IDEMPOTENCY_IN_PROGRESS.
    """
    conn = _db()
    try:
        conn.execute(
            "DELETE FROM onboarding_idempotency"
            " WHERE actor_id=? AND operation=? AND key=?"
            " AND state='IN_PROGRESS' AND lease_token=?",
            (actor, operation, key, lease),
        )
        conn.commit()
    finally:
        conn.close()


def _c_first_approval(preview_hash: str) -> dict | None:
    """Return the recorded first Class-C approval for this preview, if any."""
    conn = _db()
    try:
        row = conn.execute(
            "SELECT approver, created_at FROM class_c_first_approval"
            " WHERE preview_hash=?",
            (preview_hash,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"approver": row[0], "created_at": float(row[1])}


def _c_record_first_approval(preview_hash: str, approver: str) -> None:
    conn = _db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO class_c_first_approval"
            " (preview_hash, approver, created_at) VALUES (?,?,?)",
            (preview_hash, approver, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def _c_clear_approval(preview_hash: str) -> None:
    conn = _db()
    try:
        conn.execute(
            "DELETE FROM class_c_first_approval WHERE preview_hash=?",
            (preview_hash,),
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# audit.jsonl hash chain
# --------------------------------------------------------------------------

def _audit_append(entry: dict) -> dict:
    """Append one audit line; returns the line (with seq/prev_hash/hash)."""
    prev_hash = "0" * 64
    seq = 1
    if os.path.exists(AUDIT_PATH):
        with open(AUDIT_PATH, "r", encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        if lines:
            last = json.loads(lines[-1])
            prev_hash = last["hash"]
            seq = int(last["seq"]) + 1
    entry = {k: v for k, v in entry.items() if k != "hash"}
    entry["v"] = SCHEMA_VERSION
    entry["seq"] = seq
    entry["prev_hash"] = prev_hash
    entry["hash"] = _sha256_hex(prev_hash + _canonical({k: entry[k] for k in sorted(entry)}))
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(redact(_canonical(entry)) + "\n")
    return entry


def _audit(actor: str, tool: str, operation: str, args_hash: str, preview_id: str,
           preview_hash: str, decision: str, rule: str, reason: str,
           idem_key: str, idem_state: str, latency_ms: int) -> dict:
    return _audit_append({
        "ts": _utc_now_iso(),
        "actor": redact(actor),
        "server": "onboarding-safety",
        "tool": tool,
        "operation": operation,
        "args_hash": args_hash,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "decision": decision,
        "rule": rule,
        "reason": reason,
        "idempotency_key": idem_key,
        "idempotency_state": idem_state,
        "latency_ms": latency_ms,
    })


def verify_audit_chain(path: str = AUDIT_PATH) -> dict:
    """Verify seq continuity + prev_hash link + recomputed hash. Reports firstBadSeq."""
    if not os.path.exists(path):
        return {"ok": True, "count": 0, "head_hash": None, "firstBadSeq": None}
    prev = "0" * 64
    expected_seq = 1
    head = None
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    for idx, ln in enumerate(lines, start=1):
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            return {"ok": False, "count": len(lines), "head_hash": head,
                    "firstBadSeq": idx}
        if int(obj.get("seq", -1)) != expected_seq or obj.get("prev_hash") != prev:
            return {"ok": False, "count": len(lines), "head_hash": head,
                    "firstBadSeq": expected_seq}
        body = {k: v for k, v in obj.items() if k != "hash"}
        recomputed = _sha256_hex(obj["prev_hash"] + _canonical({k: body[k] for k in sorted(body)}))
        if recomputed != obj.get("hash"):
            return {"ok": False, "count": len(lines), "head_hash": head,
                    "firstBadSeq": expected_seq}
        prev = obj["hash"]
        head = prev
        expected_seq += 1
    return {"ok": True, "count": len(lines), "head_hash": head, "firstBadSeq": None}


# --------------------------------------------------------------------------
# 8 private helpers (composite pipeline, in order)
# --------------------------------------------------------------------------

def _verify_offer(candidate_id: str, email: str, dept: str, start_date: str) -> tuple[bool, str, dict]:
    """Helper 1: validate the offer facts. Deny-closed on missing/bad fields."""
    if not candidate_id or not email or not dept or not start_date:
        return False, "missing_offer_fields", {}
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "invalid_email", {}
    facts = {
        "candidate_id": candidate_id,
        "email": email,
        "dept": dept,
        "start_date": start_date,
    }
    return True, "offer_ok", facts


def _bg_gate(candidate_id: str, bg_status: str) -> tuple[bool, str, str]:
    """Helper 2: background-check gate. fail => deny; pending => warn (preview only)."""
    s = (bg_status or "").strip().lower()
    if s == "pass":
        return True, "bg_pass", "allow"
    if s == "pending":
        return True, "bg_pending_warn", "warn"
    return False, "bg_fail_blocked", "deny"


def _rbac(actor: str, operation: str) -> tuple[bool, str]:
    """Helper 3: deny-closed scope check. Unknown op or missing scope => deny."""
    needed = SCOPES.get(operation)
    if needed is None:
        return False, "ambiguous_scope"
    if needed not in _actor_scopes():
        return False, "insufficient_scope"
    return True, "scope_ok"


def _stage(actor: str, plan: dict) -> tuple[str, str]:
    """Helper 4: persist the redacted plan; mint preview_id + preview_hash."""
    import uuid

    ph = _preview_hash_for(plan)
    pid = "prv_" + uuid.uuid4().hex[:8]
    conn = _db()
    try:
        conn.execute(
            "INSERT INTO staged_previews (preview_id, preview_hash, actor_id,"
            " plan_redacted, created_at) VALUES (?,?,?,?,?)",
            (pid, ph, actor, redact(_canonical(plan)), time.time()),
        )
        conn.commit()
    finally:
        conn.close()
    return pid, ph


def _hold(plan: dict) -> tuple[bool, str]:
    """Helper 5: equipment-hold conflict check (LT-1005 double-hold, LT-1012 retired)."""
    laptop = str(plan.get("laptop_id") or "")
    if laptop in RETIRED_LAPTOPS:
        return False, f"laptop_retired:{laptop}"
    if laptop in HELD_LAPTOPS:
        return False, f"laptop_hold_conflict:{laptop}"
    return True, "hold_ok"


def _schedule(start_date: str, dept: str) -> tuple[bool, str, dict]:
    """Helper 6: orientation scheduling (flags weekend starts; never denies)."""
    import datetime as _dt

    weekend = False
    try:
        dow = _dt.date.fromisoformat(start_date).weekday()
        weekend = dow >= 5
    except ValueError:
        return False, "invalid_start_date", {}
    slot = {"orientation_day": "Monday-09:00" if weekend else "Day1-09:00",
            "weekend_start": weekend, "dept": dept}
    return True, "schedule_ok", slot


def _preview(preview_id: str, tool_name: str, preview_hash: str,
             key: str, effect: str) -> str:
    """Helper 7: exact Class-B approval prompt (13-safety-audit S4)."""
    short = preview_hash[:8]
    return (
        f"⚠️ WRITE PREVIEW {preview_id} ({tool_name})\n"
        f"Args hash: {short} | Idempotency-Key: {key}\n"
        f"Effect: {redact(effect)}\n"
        f"Reply APPROVE {preview_id} to execute, or REJECT {preview_id} with a reason.\n"
        f"Expires in 10 min. Same key + different args → 409 conflict, never executes."
    )


def _preview_destructive(preview_id: str, tool_name: str, preview_hash: str,
                         key: str, effect: str) -> str:
    """Helper 7b: exact Class-C double-approval prompt (13-safety-audit S4)."""
    short = preview_hash[:8]
    return (
        f"🛑 DESTRUCTIVE PREVIEW {preview_id} ({tool_name}) — ELEVATED RISK\n"
        f"Args hash: {short} | Idempotency-Key: {key}\n"
        f"Effect: {redact(effect)}\n"
        f"Reply APPROVE {preview_id} FIRST, then a second approver (or you after 30s)"
        f" replies APPROVE {preview_id} AGAIN.\n"
        f"Both approvals cite the same preview_hash; any arg change voids all approvals."
    )


def _activate(actor: str, operation: str, key: str, req_hash: str,
              resource_id: str, result: dict) -> dict:
    """Helper 8: idempotent commit. Same key+hash replays; key reuse+hash drift => 409."""
    existing = _ledger_lookup(actor, operation, key)
    if existing is not None:
        if existing["state"] == "SUCCEEDED" and existing["request_hash"] == req_hash:
            return {"status": "already_applied", "result": existing["response_body"]}
        if existing["state"] == "FAILED" and existing["request_hash"] == req_hash:
            return {"status": "already_applied", "result": existing["response_body"]}
        if existing["state"] == "IN_PROGRESS" and existing["request_hash"] == req_hash:
            return {"status": "error", "reason": "IDEMPOTENCY_IN_PROGRESS",
                    "detail": "Wait and retry with the same key."}
        return {"status": "error", "reason": "IDEMPOTENCY_CONFLICT",
                "detail": (f"CONFLICT: Idempotency-Key {key} already used with different args "
                           f"(expected {existing['request_hash'][:8]}, got {req_hash[:8]}). "
                           f"Generate a new key for a new action.")}
    won, lease = _ledger_insert_in_progress(actor, operation, key, req_hash)
    if not won:  # lost a race: re-read and replay/conflict
        return _activate(actor, operation, key, req_hash, resource_id, result)
    ok = _ledger_mark(actor, operation, key, lease, "SUCCEEDED", resource_id, 200, result)
    if not ok:
        return {"status": "error", "reason": "lease_lost",
                "detail": "Fencing check failed; do not retry blindly."}
    return {"status": "applied", "result": result}


# --------------------------------------------------------------------------
# The single guarded composite tool
# --------------------------------------------------------------------------

@mcp.tool(
    name="onboard",
    description=("Guarded onboarding composite: verify offer, background-check gate, "
                "RBAC scope, stage preview, equipment hold, orientation schedule, "
                "then activate. Stage with confirm=False; activate with confirm=True "
                "AND the exact preview_hash plus an idempotency_key."),
    tags={"onboarding", "safety"},
    meta={"version": "1.0", "readOnlyHint": False},
)
def onboard(
    candidate_id: str,
    email: str,
    dept: str,
    start_date: str,
    laptop_id: str = "",
    bg_status: str = "pending",
    confirm: bool = False,
    preview_hash: str = "",
    idempotency_key: str = "",
    actor: str = "",
    approver: str = "",
    ticket_id: str = "",
) -> dict:
    """Guarded onboard: stage-then-activate with confirm + preview_hash + idempotency.

    Activate calls the REAL HR/IT services over HTTP (HR_BASE_URL/IT_BASE_URL)
    inside the ledger fencing boundary and stores the REAL returned IDs.
    Class B (routine) needs one approval; Class C (BG not pass or weekend
    start) needs two approvals citing the same preview_hash: a distinct second
    approver, or the same approver after a 30s cooldown.
    """
    t0 = time.time()
    who = redact(actor or DEFAULT_ACTOR)

    def ms() -> int:
        return int((time.time() - t0) * 1000)

    # ---- 0. injection gate (deny-closed, both paths) ----------------------
    if _injection_hit(candidate_id, email, dept, laptop_id, bg_status,
                       idempotency_key, approver, ticket_id, preview_hash):
        _audit(who, "onboard", OPERATION, _sha256_hex(redact(candidate_id)),
               "", preview_hash if confirm else "", "deny",
               "policy:B-single-approval", "injection_blocked",
               redact(idempotency_key), "NONE", ms())
        return {"status": "denied",
                "reason": "DENIED: injection_blocked. Override/skip-checks shapes never execute."}

    # ---- 1. _verify_offer -------------------------------------------------
    ok, reason, facts = _verify_offer(candidate_id, email, dept, start_date)
    if not ok:
        _audit(who, "onboard", OPERATION, _sha256_hex(redact(candidate_id)),
               "", "", "deny", "policy:B-single-approval", reason,
               redact(idempotency_key), "NONE", ms())
        return {"status": "denied", "reason": f"DENIED: {reason}."}

    # ---- 2. _bg_gate -------------------------------------------------------
    bg_ok, bg_reason, bg_level = _bg_gate(candidate_id, bg_status)
    if not bg_ok:
        _audit(who, "onboard", OPERATION, _sha256_hex(redact(candidate_id)),
               "", "", "deny", "policy:B-single-approval", bg_reason,
               redact(idempotency_key), "NONE", ms())
        return {"status": "denied", "reason": f"DENIED {bg_reason}."}

    # ---- 3. _rbac ----------------------------------------------------------
    scope_ok, scope_reason = _rbac(who, OPERATION if confirm else "onboard.preview")
    if not scope_ok:
        _audit(who, "onboard", OPERATION, _sha256_hex(redact(candidate_id)),
               "", "", "deny", "scope/*", scope_reason,
               redact(idempotency_key), "NONE", ms())
        return {"status": "denied", "reason": f"DENIED: {scope_reason}."}

    plan = {**facts, "laptop_id": laptop_id, "bg_status": bg_status.lower()}

    # ---- STAGE path (confirm=False): read-only preview, no writes ---------
    if not confirm:
        hold_ok, hold_reason = _hold(plan)
        sched_ok, sched_reason, slot = _schedule(start_date, dept)
        if not sched_ok:
            _audit(who, "onboard", OPERATION, _sha256_hex(_redacted_canonical(plan)),
                   "", "", "deny", "policy:B-single-approval", sched_reason,
                   redact(idempotency_key), "NONE", ms())
            return {"status": "denied", "reason": f"DENIED: {sched_reason}."}
        full_plan = {**plan, "orientation": slot,
                     "hold": hold_reason if hold_ok else "CONFLICT:" + hold_reason,
                     "bg": bg_reason}
        pid, ph = _stage(who, full_plan)
        risk_class, risk_reason = _classify_risk(full_plan)
        rule = ("policy:C-double-approval" if risk_class == "C"
                else "policy:B-single-approval")
        key = redact(idempotency_key) or "idem-pending"
        effect = (f"Create {email} in {dept} starting {start_date}"
                  + (f" + assign {laptop_id}" if laptop_id else "")
                  + ("" if hold_ok else f" [HOLD {hold_reason} — resolve before approval]")
                  + (" [BG PENDING — verify before approval]" if bg_level == "warn" else "")
                  + (f" [CLASS C {risk_reason} — double approval required]"
                     if risk_class == "C" else ""))
        prompt = (_preview_destructive(pid, "onboard", ph, key, effect)
                  if risk_class == "C"
                  else _preview(pid, "onboard", ph, key, effect))
        _audit(who, "onboard", OPERATION, _sha256_hex(_redacted_canonical(full_plan)),
               pid, ph, "require_approval", rule,
               f"staged:{bg_reason}/{hold_reason}/{risk_reason}", key, "STAGED", ms())
        out: dict = {"status": "preview", "preview_id": pid, "preview_hash": ph,
                     "prompt": prompt, "plan": json.loads(redact(_canonical(full_plan))),
                     "warnings": ([bg_reason] if bg_level == "warn" else [])
                                 + ([] if hold_ok else [hold_reason]),
                     "risk_class": risk_class,
                     "note": ("Re-call onboard with confirm=True, this preview_hash,"
                              " an idempotency_key"
                              + (" and approver + a second approval" if risk_class == "C" else "")
                              + " to activate.")}
        return out

    # ---- ACTIVATE path (confirm=True): CHECK then ACT then RECORD ---------
    if not preview_hash:
        _audit(who, "onboard", OPERATION, _sha256_hex(_redacted_canonical(plan)),
               "", "", "deny", "policy:B-single-approval", "no_preview",
               redact(idempotency_key), "NONE", ms())
        return {"status": "denied",
                "reason": "DENIED: no_preview. Stage first with confirm=False."}
    if not idempotency_key:
        _audit(who, "onboard", OPERATION, _sha256_hex(_redacted_canonical(plan)),
               "", preview_hash, "deny", "policy:B-single-approval",
               "missing_idempotency_key", "", "NONE", ms())
        return {"status": "denied",
                "reason": "DENIED: missing_idempotency_key (428). Writes need a key."}

    # Replay-first (13 S7): a stored SUCCEEDED result is RETURNED on exact
    # replay (same key + same hash + same actor), even after the staged row
    # was consumed. Any re-execution restarts the full approval flow.
    prior = _ledger_lookup(who, OPERATION, idempotency_key)
    if prior is not None:
        if prior["request_hash"] == preview_hash and prior["state"] in ("SUCCEEDED", "FAILED"):
            _audit(who, "onboard", OPERATION, _sha256_hex(_redacted_canonical(plan)),
                   "", preview_hash, "allow", "policy:B-single-approval",
                   "replay:cached", redact(idempotency_key), prior["state"], ms())
            return {"status": "already_applied", "preview_hash": preview_hash,
                    "result": prior["response_body"],
                    "note": "Replay with same key+hash returned the cached result; no re-execution."}
        if prior["request_hash"] != preview_hash:
            _audit(who, "onboard", OPERATION, _sha256_hex(_redacted_canonical(plan)),
                   "", preview_hash, "deny", "policy:B-single-approval",
                   "IDEMPOTENCY_CONFLICT", redact(idempotency_key), "CONFLICT", ms())
            return {"status": "error", "reason": "IDEMPOTENCY_CONFLICT",
                    "detail": (f"CONFLICT: Idempotency-Key {redact(idempotency_key)} already used "
                               f"with different args (expected {prior['request_hash'][:8]}, "
                               f"got {preview_hash[:8]}). Generate a new key for a new action.")}
        _audit(who, "onboard", OPERATION, _sha256_hex(_redacted_canonical(plan)),
               "", preview_hash, "deny", "policy:B-single-approval",
               "IDEMPOTENCY_IN_PROGRESS", redact(idempotency_key), "IN_PROGRESS", ms())
        return {"status": "error", "reason": "IDEMPOTENCY_IN_PROGRESS",
                "detail": "Wait and retry with the same key."}

    conn = _db()
    try:
        # Exact lookup: hash is unique per stage; bind to actor.
        row = conn.execute(
            "SELECT preview_id, plan_redacted, created_at FROM staged_previews"
            " WHERE preview_hash=? AND actor_id=? ORDER BY created_at DESC LIMIT 1",
            (preview_hash, who),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        _audit(who, "onboard", OPERATION, _sha256_hex(_redacted_canonical(plan)),
               "", preview_hash, "deny", "policy:B-single-approval", "no_preview",
               redact(idempotency_key), "NONE", ms())
        return {"status": "denied",
                "reason": "DENIED: no_preview. Unknown or expired preview_hash; re-run preview."}
    pid, plan_json, created_at = row
    if time.time() - float(created_at) > PREVIEW_TTL_S:
        _audit(who, "onboard", OPERATION, _sha256_hex(_redacted_canonical(plan)),
               pid, preview_hash, "deny", "policy:B-single-approval",
               "approval_expired", redact(idempotency_key), "NONE", ms())
        return {"status": "denied",
                "reason": f"DENIED {pid}: approval_expired. Ask for a fresh preview."}

    stored_plan = json.loads(plan_json)
    # Re-derive gates server-side at commit (HashGate ordering): hold must pass now.
    hold_ok, hold_reason = _hold(stored_plan)
    if not hold_ok:
        _audit(who, "onboard", OPERATION, _sha256_hex(plan_json),
               pid, preview_hash, "deny", "policy:B-single-approval",
               f"precondition_failed:{hold_reason}",
               redact(idempotency_key), "NONE", ms())
        return {"status": "denied",
                "reason": f"DENIED {pid}: precondition_failed:{hold_reason}."}

    # ---- Class B vs C gate (13 S3/S7) ------------------------------------
    risk_class, risk_reason = _classify_risk(stored_plan)
    rule = ("policy:C-double-approval" if risk_class == "C"
            else "policy:B-single-approval")
    if risk_class == "C":
        me = redact(approver or who)
        if not (approver or who):
            _audit(who, "onboard", OPERATION, _sha256_hex(plan_json),
                   pid, preview_hash, "deny", rule, "missing_approver",
                   redact(idempotency_key), "NONE", ms())
            return {"status": "denied",
                    "reason": (f"DENIED {pid}: missing_approver. Class C ({risk_reason})"
                               " needs two approvals citing this preview_hash.")}
        first = _c_first_approval(preview_hash)
        if first is None:
            _c_record_first_approval(preview_hash, me)
            _audit(who, "onboard", OPERATION, _sha256_hex(plan_json),
                   pid, preview_hash, "require_approval", rule,
                   f"first_approval:{me}", redact(idempotency_key), "STAGED", ms())
            return {"status": "need_second_approval", "preview_hash": preview_hash,
                    "reason": (f"Class C ({risk_reason}): first approval by {me} recorded. "
                               "A distinct approver — or the same approver after 30s — "
                               f"must re-call with approver set and preview_hash {preview_hash[:8]}.")}
        same = (first["approver"] == me)
        waited = time.time() - float(first["created_at"])
        if same and waited < CLASS_C_COOLDOWN_S:
            _audit(who, "onboard", OPERATION, _sha256_hex(plan_json),
                   pid, preview_hash, "deny", rule,
                   f"cooldown:{int(CLASS_C_COOLDOWN_S - waited)}s_left",
                   redact(idempotency_key), "STAGED", ms())
            return {"status": "need_second_approval", "preview_hash": preview_hash,
                    "reason": (f"Class C cooldown: same approver {me} must wait "
                               f"{int(CLASS_C_COOLDOWN_S - waited)}s more, or use a "
                               "distinct second approver."),
                    "retry_after_s": int(CLASS_C_COOLDOWN_S - waited)}
        # Distinct approver, or same approver past cooldown -> proceed to ACT.

    # ---- Ledger fencing claim FIRST: the real writes happen inside this ----
    # ---- boundary; success AND real 404/409 denials both commit here. -----
    won, lease = _ledger_insert_in_progress(who, OPERATION, idempotency_key, preview_hash)
    if not won:  # lost a race: re-read and replay/conflict (never double-execute)
        raced = _ledger_lookup(who, OPERATION, idempotency_key)
        if raced is not None and raced["request_hash"] == preview_hash \
                and raced["state"] in ("SUCCEEDED", "FAILED"):
            return {"status": "already_applied", "preview_hash": preview_hash,
                    "result": raced["response_body"],
                    "note": "Replay with same key+hash returned the cached result; no re-execution."}
        return {"status": "error", "reason": "IDEMPOTENCY_CONFLICT",
                "detail": "Lost the fencing race; retry with the same key."}

    def _fail(state_code: int, deny_reason: str, body_extra: dict) -> dict:
        body = {"preview_id": pid, "preview_hash": preview_hash,
                "reason": deny_reason, **body_extra}
        _ledger_mark(who, OPERATION, idempotency_key, lease, "FAILED",
                     body_extra.get("employee_id", ""), state_code, body)
        _audit(who, "onboard", OPERATION, _sha256_hex(plan_json),
               pid, preview_hash, "deny", rule, deny_reason,
               redact(idempotency_key), "FAILED", ms())
        return {"status": "denied",
                "reason": f"DENIED {pid}: {deny_reason}.",
                "receipt": body}

    def _unreachable(detail: str) -> dict:
        # No write happened yet: release the claim so a retry can proceed.
        _ledger_release(who, OPERATION, idempotency_key, lease)
        _audit(who, "onboard", OPERATION, _sha256_hex(plan_json),
               pid, preview_hash, "deny", rule, "service_unavailable",
               redact(idempotency_key), "NONE", ms())
        return {"status": "error", "reason": "service_unavailable",
                "detail": (f"{redact(detail)} Is HR ({_hr_base()}) + IT ({_it_base()}) up?")}

    hr, it = _hr_base(), _it_base()

    # ---- ACT 1: resolve the candidate over HTTP (real name + 404 surfacing)
    st, cand = _http_get_json(f"{hr}/hr/candidates/{candidate_id}")
    if st is None:
        return _unreachable(str(cand.get("detail", "hr unreachable")))
    if st == 404 or not isinstance(cand, dict) or not cand.get("candidate_id"):
        return _fail(404, f"candidate_not_found:{candidate_id}",
                     {"hr_status": st, "hr_body": cand})
    if st >= 400:
        return _fail(st, f"hr_candidate_lookup_failed:{st}", {"hr_body": cand})
    cand_name = str(cand.get("name") or "").strip()
    if not cand_name:
        return _fail(st, "candidate_name_missing", {"hr_body": cand})

    # ---- ACT 2: POST /hr/employees (real EMP-NNN id comes back from HR) ---
    st, emp = _http_post_json(f"{hr}/hr/employees", {
        "name": cand_name,
        "email": email,
        "team": dept,
        "start_date": start_date,
        "role": "engineer",
    })
    if st is None:
        return _unreachable(str(emp.get("detail", "hr unreachable")))
    if st >= 400 or not isinstance(emp, dict) or not emp.get("employee_id"):
        detail = emp.get("detail", emp) if isinstance(emp, dict) else emp
        return _fail(st, f"hr_create_employee:{st}:{redact(str(detail))}",
                     {"hr_status": st, "hr_body": emp})
    real_emp_id = str(emp["employee_id"])

    assignment: dict = {}
    if laptop_id:
        # ---- ACT 3: POST /it/equipment/assign (real 404/409s surface) ----
        st, asn = _http_post_json(f"{it}/it/equipment/assign", {
            "serial": laptop_id, "employee_id": real_emp_id,
        })
        if st is None:
            # HR row already exists: record the partial as FAILED (denial receipt
            # carrying the real employee id) so the judge can cross-check HR.
            return _fail(503, f"it_unreachable_after_hr_create:{real_emp_id}",
                         {"employee_id": real_emp_id, "employee": emp,
                          "it_body": asn})
        if st >= 400 or not isinstance(asn, dict):
            detail = asn.get("detail", asn) if isinstance(asn, dict) else asn
            return _fail(st, f"it_assign:{st}:{redact(str(detail))}",
                         {"employee_id": real_emp_id, "employee": emp,
                          "it_status": st, "it_body": asn})
        assignment = asn

    reroute: dict = {}
    if ticket_id:
        # ---- ACT 4 (optional): POST /it/tickets/{id}/reroute to the hire --
        st, rrt = _http_post_json(f"{it}/it/tickets/{ticket_id}/reroute", {
            "to_email": email, "reason": f"onboarding-reroute-to-{real_emp_id}",
        })
        if st is None:
            return _fail(503, f"it_unreachable_after_hr_create:{real_emp_id}",
                         {"employee_id": real_emp_id, "employee": emp,
                          "assignment": assignment, "it_body": rrt})
        if st >= 400 or not isinstance(rrt, dict):
            detail = rrt.get("detail", rrt) if isinstance(rrt, dict) else rrt
            return _fail(st, f"it_reroute:{st}:{redact(str(detail))}",
                         {"employee_id": real_emp_id, "employee": emp,
                          "assignment": assignment,
                          "it_status": st, "it_body": rrt})
        reroute = rrt

    receipt = {"employee_id": real_emp_id, "email": redact(email),
               "name": redact(cand_name), "dept": dept, "start_date": start_date,
               "laptop_id": laptop_id, "assignment": assignment,
               "reroute": reroute, "preview_id": pid,
               "preview_hash": preview_hash,
               "risk_class": risk_class}
    ok = _ledger_mark(who, OPERATION, idempotency_key, lease, "SUCCEEDED",
                      real_emp_id, 200, receipt)
    if not ok:
        return {"status": "error", "reason": "lease_lost",
                "detail": "Fencing check failed; do not retry blindly."}
    conn = _db()
    try:
        conn.execute("DELETE FROM staged_previews WHERE preview_hash=? AND actor_id=?",
                     (preview_hash, who))
        conn.execute("DELETE FROM class_c_first_approval WHERE preview_hash=?",
                     (preview_hash,))
        conn.commit()
    finally:
        conn.close()
    _audit(who, "onboard", OPERATION, _sha256_hex(plan_json),
           pid, preview_hash, "allow", rule,
           f"approval:{pid}:hr:{real_emp_id}", redact(idempotency_key), "SUCCEEDED", ms())
    return {"status": "applied", "preview_hash": preview_hash,
            "result": json.loads(redact(_canonical(receipt))),
            "receipt": f"ACTIVE {real_emp_id} for {redact(email)}."}


if __name__ == "__main__":
    mcp.run()
