# 34 — Verify Approval Hash Binding (pytest Matrix + preview_hash Recompute)

**Sources:** `research/final/13-safety-audit.md` §§1,4,5,7 (guarded_call, UX strings, idempotency ledger, double-approve) · `research/brainstorm/04-track2-safety.md` §5 (token bound to `hash(preview)`, replay returns cached) · `research/build/04-auth.md` §§3–4 (hash over redacted form, scope-deny short-circuit).
**Goal:** prove approval is a receipt for one exact diff — not a session token. Any arg drift, hash mismatch, expiry, or missing confirm denies; exact replay returns cached without re-execution.
**Rule:** `preview_hash = sha256_hex(canonical_json(tool, redacted_args, schema_version))`; approval bound to `(actor, client_id, preview_id, preview_hash)`; TTL ≤10 min; ≤20 pending/user.

## 1. Binding contract under test

```python
import hashlib, json

def canonical_json(tool: str, args: dict, schema_version: int = 1) -> bytes:
    return json.dumps(
        {"tool": tool, "args": args, "v": schema_version},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")

def preview_hash(tool: str, redacted_args: dict, schema_version: int = 1) -> str:
    return hashlib.sha256(canonical_json(tool, redacted_args, schema_version)).hexdigest()

def valid_approval(approval, preview, ctx, now) -> tuple[bool, str]:
    if approval is None or preview is None:
        return False, "approval_invalid"
    if approval.get("confirm") is False:
        return False, "approval_invalid"          # explicit REJECT aborts
    if approval["preview_id"] != preview["preview_id"]:
        return False, "approval_invalid"
    if approval["preview_hash"] != preview["preview_hash"]:
        return False, "preview_hash_mismatch"
    if approval["actor"] != ctx["actor"] or approval["client_id"] != ctx["client_id"]:
        return False, "approval_invalid"          # not transferable across actor/client
    if approval["expires_at"] <= now:
        return False, "approval_expired"
    recomputed = preview_hash(preview["tool"], preview["redacted_args"])
    if recomputed != preview["preview_hash"]:
        return False, "preview_hash_mismatch"     # stored preview itself tampered
    live = preview_hash(ctx["tool"], ctx["redacted_args"])
    if live != preview["preview_hash"]:
        return False, "preview_hash_mismatch"     # args changed post-approval → void
    return True, "approval:ok"
```

Notes (from 13 §§5–6): hash the **redacted** canonical form (`${ENV:NAME}` by name, never value); validate-then-hash; `idempotency_key` (which action) and `preview_hash` (what bytes) are checked independently — key conflict + hash drift → `409 IDEMPOTENCY_CONFLICT`, never execute.

## 2. Verification matrix (ship-blocking, 5 cases)

| # | Case | Setup | Expect |
|---|---|---|---|
| 1 | `confirm=False` aborts | dry-run → preview `prv_A`; approver sends `REJECT prv_A` (`confirm=False`) then execute `dry_run=false` same key+args | deny `approval_invalid`; no mutation; one audit line `decision=deny reason=approval_invalid` |
| 2 | Wrong hash denies | preview `prv_B` hash `hB`; execute cites `approval_id` bound to different `preview_hash hX` | deny `preview_hash_mismatch`; never invokes tool; audit `decision=deny` |
| 3 | Changed args voids approval | approve `prv_C` (`{email:"ada@x", team:"platform"}`); execute same key but `team:"support-night"` | recomputed live hash ≠ approved hash → deny `preview_hash_mismatch` + `409 IDEMPOTENCY_CONFLICT` on key reuse; force fresh dry-run |
| 4 | Expired TTL denies | approval `expires_at = now - 1s` (TTL 10 min exceeded) or `sleep`/freeze past expiry; execute same key+args | deny `approval_expired`; audit `decision=deny`; cached result NOT served on expired replay — full re-approval required |
| 5 | Double-approve returns cached | approve `prv_E`, execute → `SUCCEEDED` stored `(key, hash, result)`; execute again same `(actor, key, hash)` unexpired | second call returns stored result, `duplicate:true`, **no re-execution** (mutate counter still 1); audit second line `decision=allow reason=replay-cached` |

All five must also assert: scope check ran **before** approval lookup (viewer → `insufficient_scope` even with valid approval), and no sink (preview/log/audit/error) contains a resolved `${ENV:*}` value.

## 3. pytest matrix (copy-paste, stdlib + pytest + freezegun-style clock)

```python
import hashlib, json, time, uuid
import pytest

TTL_S = 600  # 10 min per 13 §7

def canonical_json(tool, args, v=1):
    return json.dumps({"tool": tool, "args": args, "v": v},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def phash(tool, args):
    return hashlib.sha256(canonical_json(tool, args)).hexdigest()

class Denied(Exception):
    def __init__(self, reason): super().__init__(reason); self.reason = reason

class Gate:
    """Minimal in-memory guarded_call per 13 §1 + idempotency ledger per 13 §5."""
    def __init__(self):
        self.previews, self.approvals, self.ledger = {}, {}, {}
        self.mutations = 0
    def dry_run(self, tool, args):
        pid = "prv_" + uuid.uuid4().hex[:6]
        h = phash(tool, args)
        self.previews[pid] = {"preview_id": pid, "tool": tool,
                              "redacted_args": dict(args), "preview_hash": h}
        return pid, h
    def approve(self, preview_id, actor="user:ada", client="web", confirm=True, ttl=TTL_S, now=None):
        now = now if now is not None else time.time()
        pv = self.previews[preview_id]
        aid = "apr_" + uuid.uuid4().hex[:6]
        self.approvals[aid] = {"approval_id": aid, "preview_id": preview_id,
                               "preview_hash": pv["preview_hash"], "actor": actor,
                               "client_id": client, "confirm": confirm, "expires_at": now + ttl}
        return aid
    def execute(self, tool, args, preview_id, approval_id, key, actor="user:ada", client="web", now=None):
        now = now if now is not None else time.time()
        pv = self.previews.get(preview_id)
        if pv is None: raise Denied("no_preview")
        live = phash(tool, args)
        if live != pv["preview_hash"]: raise Denied("preview_hash_mismatch")
        ap = self.approvals.get(approval_id)
        ok, reason = self._valid(ap, pv, tool, args, actor, client, now)
        if not ok: raise Denied(reason)
        slot = self.ledger.get((actor, tool, key))
        if slot and slot["hash"] != live: raise Denied("idempotency_conflict")
        if slot and slot["state"] == "SUCCEEDED":  # exact replay → cached
            return {"status": "duplicate", "result": slot["result"], "cached": True}
        self.mutations += 1
        result = {"ok": True, "tool": tool, "n": self.mutations}
        self.ledger[(actor, tool, key)] = {"hash": live, "state": "SUCCEEDED", "result": result}
        return {"status": "executed", "result": result, "cached": False}
    @staticmethod
    def _valid(ap, pv, tool, args, actor, client, now):
        if ap is None or ap.get("confirm") is False: return False, "approval_invalid"
        if ap["preview_id"] != pv["preview_id"]: return False, "approval_invalid"
        if ap["preview_hash"] != pv["preview_hash"]: return False, "preview_hash_mismatch"
        if ap["actor"] != actor or ap["client_id"] != client: return False, "approval_invalid"
        if ap["expires_at"] <= now: return False, "approval_expired"
        if phash(pv["tool"], pv["redacted_args"]) != pv["preview_hash"]: return False, "preview_hash_mismatch"
        return True, "approval:ok"

ARGS = {"email": "ada@example.com", "team": "platform"}

def test_1_confirm_false_aborts():
    g = Gate(); pid, _ = g.dry_run("provision_user", ARGS)
    aid = g.approve(pid, confirm=False)  # REJECT prv_xxx
    with pytest.raises(Denied) as e:
        g.execute("provision_user", ARGS, pid, aid, key="k1")
    assert e.value.reason == "approval_invalid" and g.mutations == 0

def test_2_wrong_hash_denies():
    g = Gate(); pid, _ = g.dry_run("provision_user", ARGS)
    aid = g.approve(pid)
    g.approvals[aid]["preview_hash"] = "0" * 64  # attacker-swapped / stale approval
    with pytest.raises(Denied) as e:
        g.execute("provision_user", ARGS, pid, aid, key="k2")
    assert e.value.reason == "preview_hash_mismatch" and g.mutations == 0

def test_3_changed_args_voids_approval():
    g = Gate(); pid, _ = g.dry_run("provision_user", ARGS)
    aid = g.approve(pid)
    drifted = {"email": "ada@example.com", "team": "support-night"}
    with pytest.raises(Denied) as e:
        g.execute("provision_user", drifted, pid, aid, key="k3")
    assert e.value.reason == "preview_hash_mismatch" and g.mutations == 0

def test_4_expired_ttl_denies():
    g = Gate(); pid, _ = g.dry_run("provision_user", ARGS)
    t0 = time.time()
    aid = g.approve(pid, ttl=TTL_S, now=t0)
    with pytest.raises(Denied) as e:
        g.execute("provision_user", ARGS, pid, aid, key="k4", now=t0 + TTL_S + 1)
    assert e.value.reason == "approval_expired" and g.mutations == 0

def test_5_double_approve_returns_cached():
    g = Gate(); pid, _ = g.dry_run("provision_user", ARGS)
    aid = g.approve(pid)
    first = g.execute("provision_user", ARGS, pid, aid, key="k5")
    second = g.execute("provision_user", ARGS, pid, aid, key="k5")  # double-click Approve
    assert first["cached"] is False and second["cached"] is True
    assert second["result"] == first["result"] and g.mutations == 1

def test_preview_hash_recompute_check():
    """Stored preview tamper-evidence: recompute must equal minted hash."""
    g = Gate(); pid, h = g.dry_run("provision_user", ARGS)
    pv = g.previews[pid]
    assert phash(pv["tool"], pv["redacted_args"]) == h == pv["preview_hash"]
    pv["redacted_args"]["team"] = "support-night"  # tamper
    assert phash(pv["tool"], pv["redacted_args"]) != pv["preview_hash"]
```

Run: `pytest research/build/tests/test_34_verify_approval.py -v` — expect `6 passed`. Failure policy: any case executing a mutation or returning non-cached second execute = ship-blocker; re-run full matrix after any change to `canonical_json`, redaction, TTL, or ledger PK.

## 4. Demo proof lines (say while running pytest)

```text
Agent: "Preview prv_7f3a hash 9f2c… — reply APPROVE prv_7f3a. Any arg change voids it."
User: "APPROVE prv_7f3a" (then edits team →) Agent: "DENIED prv_7f3a: preview_hash_mismatch. Fresh preview needed."
User: (double-clicks Approve →) Agent: "Duplicate — returning cached result, no re-execution."
```

*Delta vs cited sources: TTL=600s, 20-pending cap, `duplicate:true` replay shape, and the 6-test pytest file are pinned here; 13/04 define semantics, this file defines the executable verdict.*
