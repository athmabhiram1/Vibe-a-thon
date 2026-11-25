# Step 22 — Idempotency Ledger: Postgres + Python (409 vs Replay Matrix)

> Goal: exactly-once *effect* for non-idempotent tools (`transfer`, `book`, `charge`) across retries, crashes, and double-clicks. One ledger table + one rule: **commit result and ledger state in the same transaction.**

## 1. Schema (Postgres)

```sql
CREATE TYPE idem_state AS ENUM ('IN_PROGRESS', 'SUCCEEDED', 'FAILED');

CREATE TABLE idempotency_ledger (
  actor_id     TEXT NOT NULL,          -- tenant / user / api-key scope
  operation    TEXT NOT NULL,          -- 'transfer.v1', 'booking.create.v2'
  idem_key     TEXT NOT NULL,          -- client-supplied Idempotency-Key (uuid v4)
  request_hash CHAR(64) NOT NULL,      -- sha256(canonical_json(args))
  state        idem_state NOT NULL DEFAULT 'IN_PROGRESS',
  lease_token  UUID NOT NULL DEFAULT gen_random_uuid(),
  response_code INT,                   -- cached HTTP/status to replay
  response_body JSONB,                 -- cached success payload to replay
  error_code   TEXT,                   -- cached machine-readable error
  error_msg    TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at   TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '24 hours',
  PRIMARY KEY (actor_id, operation, idem_key)
);
CREATE INDEX ON idempotency_ledger (expires_at) WHERE state <> 'IN_PROGRESS';
CREATE INDEX ON idempotency_ledger (state, updated_at) WHERE state = 'IN_PROGRESS';
```

Why this PK: `(actor_id, operation, key)` scopes keys per caller + tool version. Never use bare global `key` — cross-tenant replay is a vulnerability. `request_hash` enables **semantic replay** (§5). `lease_token` enables crash-safe fencing (§3).

TTL: `DELETE` or partition-drop rows where `expires_at < now()`. Keep `SUCCEEDED` 24h–7d (replay window), `FAILED` shorter, `IN_PROGRESS` reaped by lease timeout (e.g. 2 min).

## 2. Claim with ON CONFLICT (atomic gate)

```sql
-- Attempt 1: try to become owner. Returns the row whether we won or lost.
INSERT INTO idempotency_ledger (actor_id, operation, idem_key, request_hash)
VALUES ($1, $2, $3, $4)
ON CONFLICT (actor_id, operation, idem_key) DO NOTHING
RETURNING lease_token;
-- If a row is returned → we own IN_PROGRESS, execute.
-- If zero rows → someone owned it first → go to §4 matrix.
```

Reclaim a stale lease (previous worker crashed while IN_PROGRESS):

```sql
UPDATE idempotency_ledger
SET lease_token = gen_random_uuid(), request_hash = $4, updated_at = now()
WHERE actor_id=$1 AND operation=$2 AND idem_key=$3
  AND state = 'IN_PROGRESS'
  AND updated_at < now() - INTERVAL '2 minutes'
RETURNING lease_token;
-- If returned → we stole the expired lease, execute. Else → treat as conflict/replay.
```

## 3. Commit-together rule (the only correctness rule)

> **Never commit the business effect without flipping the ledger row in the SAME DB transaction. Never flip the ledger without the effect.**

```sql
BEGIN;
-- 1) business write (same txn, same connection)
INSERT INTO transfers (id, from_acct, to_acct, amount) VALUES (...);
-- 2) ledger flip (same txn)
UPDATE idempotency_ledger
SET state='SUCCEEDED', response_code=200,
    response_body='{"transfer_id":"..."}', updated_at=now()
WHERE actor_id=$1 AND operation=$2 AND idem_key=$3 AND lease_token=$4;
COMMIT;
-- Failure path: same shape with state='FAILED', error_code/error_msg set.
```

If `COMMIT` fails / process crashes before it: row stays `IN_PROGRESS` with our dead `lease_token` → next retry reclaims via §2 timeout. If crash happens *after* `COMMIT`: retry hits `SUCCEEDED` → pure replay, no second transfer. Any design that writes the result to Redis/email/another DB in a separate commit breaks this guarantee.

## 4. 409 CONFLICT vs Replay Matrix (server behavior)

Let `stored` = existing row, `incoming_hash = sha256(args)`.

| Stored state | Hash match? | Action | HTTP |
|---|---|---|---|
| none (insert won) | — | Execute (§3) | `200/201` on success |
| `IN_PROGRESS`, lease live | — | Another worker is running it | `409 CONFLICT` + `Retry-After: 1`, body `{"status":"in_progress"}` |
| `IN_PROGRESS`, lease expired | match or not | Steal lease (§2), execute | `200/201` (new execution) |
| `SUCCEEDED` | match | **Replay** stored `response_code/body`, do NOT re-execute | same `200` as first time |
| `SUCCEEDED` | mismatch | Same key, different args = client bug | `422 UNPROCESSABLE` (`idempotency_key_reused`) — never `409` |
| `FAILED` | match | Safe ops: retry execution; non-retryable business errors: replay error | `200` on recovery or replayed `4xx` |
| `FAILED` | mismatch | Same as SUCCEEDED/mismatch | `422` |

Status-code discipline: `409` = "in flight, back off" (retryable). `422` = "key reused with different payload" (do NOT retry, mint a new key). `200 + replayed:true` = semantic replay. Conflating 409/422 causes infinite retry loops or silent wrong transfers.

Headers: require `Idempotency-Key: <uuid>` + `Idempotency-Operation: transfer.v1`. Response always echoes `Idempotency-Key` and `Idempotent-Replayed: true/false`.

## 5. Semantic replay (same intent, different bytes)

Byte-hash is too strict (`{"amt":10}` vs `{"amt":10.0}`). Normalize before hashing:

1. Canonicalize: strip volatile fields (`request_id`, `timestamp`, `trace_id`), sort keys, round decimals to minor units (cents), lowercase emails.
2. `request_hash = sha256(canonical_json)`.
3. Optional second tier: `semantic_hash` over intent tuple, e.g. `(from, to, cents, currency, date)` — catches key-format drift across SDK versions.

If `incoming_hash != stored.request_hash` but `semantic_hash` matches → still `422`, but include `hint: "same intent, new key required"` to guide the client.

## 6. Python reference (psycopg3, sync)

```python
import hashlib, json, uuid
from enum import Enum
import psycopg

class IdemOutcome(Enum):
    EXECUTE = "execute"       # caller must run business logic, then finalize()
    REPLAY = "replay"         # return cached response now
    CONFLICT = "conflict"     # return 409 Retry-After
    KEY_REUSE = "key_reuse"   # return 422

def canonical_hash(args: dict, volatile=("request_id","timestamp","trace_id")) -> str:
    clean = {k: v for k, v in args.items() if k not in volatile}
    blob = json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()

LEASE_TIMEOUT_SQL = "INTERVAL '2 minutes'"

def claim(conn, actor_id: str, operation: str, key: str, args: dict):
    """Returns (outcome, payload, lease_token). Single round-trip gate."""
    h = canonical_hash(args)
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO idempotency_ledger (actor_id, operation, idem_key, request_hash)
               VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING lease_token""",
            (actor_id, operation, key, h))
        row = cur.fetchone()
        if row:  # we own it
            conn.commit()
            return (IdemOutcome.EXECUTE, None, row[0])
        # Lost race: inspect stored row
        cur.execute(
            """SELECT state, request_hash, response_code, response_body,
                      error_code, error_msg, lease_token, updated_at
               FROM idempotency_ledger WHERE actor_id=%s AND operation=%s AND idem_key=%s""",
            (actor_id, operation, key))
        state, stored_hash, code, body, ecode, emsg, lease, updated = cur.fetchone()
        if state == "IN_PROGRESS":
            cur.execute("SELECT now() - updated_at > " + LEASE_TIMEOUT_SQL + " FROM idempotency_ledger WHERE actor_id=%s AND operation=%s AND idem_key=%s",
                        (actor_id, operation, key))
            expired = cur.fetchone()[0]
            if expired:
                cur.execute(
                    """UPDATE idempotency_ledger SET lease_token=gen_random_uuid(),
                       request_hash=%s, updated_at=now()
                       WHERE actor_id=%s AND operation=%s AND idem_key=%s
                       AND state='IN_PROGRESS' RETURNING lease_token""",
                    (h, actor_id, operation, key))
                r = cur.fetchone()
                conn.commit()
                if r: return (IdemOutcome.EXECUTE, None, r[0])
            conn.commit()
            return (IdemOutcome.CONFLICT, {"status": "in_progress"}, None)
        if stored_hash != h:
            conn.commit()
            return (IdemOutcome.KEY_REUSE,
                    {"error": "idempotency_key_reused", "hint": "mint a new key for new args"}, None)
        conn.commit()
        if state == "SUCCEEDED":
            return (IdemOutcome.REPLAY, {"code": code, "body": body}, None)
        # FAILED + same hash: let caller retry execution (or replay ecode if non-retryable)
        return (IdemOutcome.REPLAY if ecode in ("insufficient_funds", "validation") else IdemOutcome.EXECUTE,
                {"error": ecode, "message": emsg}, lease)

def finalize(conn, actor_id, operation, key, lease, ok: bool, code: int, body: dict | None = None,
             ecode: str | None = None, emsg: str | None = None):
    """MUST be called inside the same transaction as the business write."""
    with conn.cursor() as cur:
        cur.execute("BEGIN") if conn.autocommit else None
        # ... caller executes business SQL on `cur` here (same txn) ...
        cur.execute(
            """UPDATE idempotency_ledger SET state=%s, response_code=%s, response_body=%s,
               error_code=%s, error_msg=%s, updated_at=now()
               WHERE actor_id=%s AND operation=%s AND idem_key=%s AND lease_token=%s""",
            ('SUCCEEDED' if ok else 'FAILED', code,
             json.dumps(body) if body else None, ecode, emsg,
             actor_id, operation, key, lease))
        if cur.rowcount != 1:
            raise RuntimeError("lease lost; business txn must ROLLBACK")
        conn.commit()

# FastAPI sketch
# @app.post("/transfer")
# def transfer(req: Request, Idempotency_Key: str = Header(...)):
#     outcome, payload, lease = claim(conn, actor, "transfer.v1", Idempotency_Key, req.json())
#     if outcome == IdemOutcome.REPLAY: return JSONResponse(payload["body"], status_code=payload["code"],
#                                                          headers={"Idempotent-Replayed": "true"})
#     if outcome == IdemOutcome.CONFLICT: return JSONResponse(payload, status_code=409,
#                                                             headers={"Retry-After": "1"})
#     if outcome == IdemOutcome.KEY_REUSE: return JSONResponse(payload, status_code=422)
#     try:
#         with psycopg.connect(DSN) as c2:  # same-txn finalize pattern
#             with c2.cursor() as cur:
#                 cur.execute("INSERT INTO transfers ...")
#                 finalize(c2, actor, "transfer.v1", Idempotency_Key, lease, True, 200, {"id": tid})
#     except Exception as e:
#         mark FAILED via finalize(..., ok=False, ...); raise
```

Client rule: generate `uuid4` per user intent (button-click), retry on network error/`5xx`/`409` with same key, mint a new key for new args. Never reuse one key across different transfers.

## 7. Demo + checklist

Demo (5 min): `POST /transfer` (key A) → `200 idempotent-replayed:false`; retry same key+args → `200 replayed:true`, one row in `transfers`; same key+different amount → `422`; parallel double-click (key A, no wait) → one `200`, one `409`; kill -9 mid-transfer → next retry reclaims lease, single effect.
Checklist: PK is 3-col · `ON CONFLICT DO NOTHING` + lease steal · commit-together enforced (rowcount check) · 409/422/replay matrix tested · canonical hash strips volatile fields · expiry janitor cron · load test: 100-way same-key burst → exactly 1 effect.
