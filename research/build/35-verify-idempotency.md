# 35 — Verify Idempotency: Replay, Conflict, Lease-Reclaim, Fencing & Commit-Together Rollback

**Goal:** prove the idempotency layer is correct under retries, concurrent duplicates, crashed holders, and partial-commit failures.
**Scope:** one `idempotency_keys` table + five replay tests every implementation must pass.
**Applies to:** any mutating endpoint that accepts `Idempotency-Key` + request-hash (`X-Request-Hash` or server-computed body hash).

---

## 1. Contract under test

| # | Scenario | Input | Expected |
|---|---|---|---|
| 1 | Exact replay (same key + same hash, completed) | `POST /it/tickets` twice, same key+hash | 2nd returns **stored** status + body, no side effect re-executed |
| 2 | Key reuse with different payload | same key, different hash | **409 CONFLICT** `{"code":"IDEMPOTENCY_KEY_REUSED"}` |
| 3 | Concurrent duplicate while IN_PROGRESS | B arrives while A holds lease | **409 + `Retry-After`** (wait/poll), never double-execute |
| 4 | Expired lease reclaim with fencing | A crashes, lease expires, B reclaims with higher fencing token; stale A commit rejected | only B's result stored |
| 5 | Commit-together rollback | business row + idempotency record committed in one txn; on failure both roll back, key reusable | retry after 5xx re-executes cleanly |

**Header contract:**

```http
POST /it/tickets HTTP/1.1
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
X-Request-Hash: sha256-hex-of-canonical-body   # or server computes it
Content-Type: application/json
```

Responses:

- `201` — first execution completed.
- `200` + `Idempotent-Replayed: true` — exact replay, stored body returned.
- `409 {"code":"IDEMPOTENCY_KEY_REUSED"}` — same key, different hash.
- `409 {"code":"IDEMPOTENCY_IN_PROGRESS","retry_after":2}` — lease live, another owner working.
- `422 {"code":"STALE_FENCING_TOKEN"}` — stale holder's commit rejected after reclaim (server-internal; client sees retry → gets B's result).

---

## 2. Minimal schema (Postgres)

```sql
-- 35-verify-idempotency.sql
CREATE TABLE IF NOT EXISTS idempotency_keys (
  idem_key        TEXT PRIMARY KEY,
  request_hash    TEXT        NOT NULL,          -- sha256 of canonical body
  status          TEXT        NOT NULL DEFAULT 'IN_PROGRESS'
                  CHECK (status IN ('IN_PROGRESS','COMPLETED','FAILED')),
  response_status INT,                            -- HTTP status of stored result
  response_body   JSONB,                          -- stored result body
  fencing_token   BIGINT      NOT NULL DEFAULT 1, -- monotonic per key, bumped on reclaim
  lease_owner     TEXT        NOT NULL,            -- uuid of holder
  lease_expires_at TIMESTAMPTZ NOT NULL,           -- now() + lease_ttl (e.g. 30s)
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_idem_lease ON idempotency_keys (status, lease_expires_at);
```

**Tuning:** `lease_ttl = 30s` for user-facing POSTs, `2–5s` for high-contention internal calls. `request_hash = hex(sha256(canonical_json(body)))` — keys sorted, whitespace stripped, floats normalized. Never hash headers.

---

## 3. Claim / complete / reclaim SQL (single-statement atomicity)

### 3a. Claim (INSERT-else-inspect) — one round trip

```sql
-- Attempt claim. Returns the row that decides the path.
-- Bind: :key, :hash, :owner (gen_random_uuid()), :ttl (interval '30 seconds')
INSERT INTO idempotency_keys
  (idem_key, request_hash, status, fencing_token, lease_owner, lease_expires_at)
VALUES (:key, :hash, 'IN_PROGRESS', 1, :owner, now() + :ttl)
ON CONFLICT (idem_key) DO NOTHING
RETURNING idem_key, request_hash, status, fencing_token, lease_owner, lease_expires_at;
-- If a row is returned → we are the owner (fencing_token = 1). Execute business logic,
-- then COMMIT-TOGETHER (§3c).
-- If zero rows → key exists: run §3b inspect.
```

### 3b. Inspect existing key (replay / conflict / wait / reclaim)

```sql
-- Bind: :key, :hash, :owner, :ttl
SELECT idem_key, request_hash, status, response_status, response_body,
       fencing_token, lease_owner, lease_expires_at
FROM idempotency_keys WHERE idem_key = :key;
```

Decision table in app code (after SELECT):

```python
if row.request_hash != incoming_hash:
    return 409, {"code": "IDEMPOTENCY_KEY_REUSED"}          # Test 2 — never compare after reclaim
if row.status == "COMPLETED":
    return row.response_status, row.response_body, {"Idempotent-Replayed": "true"}  # Test 1
if row.status == "IN_PROGRESS" and row.lease_expires_at > now():
    return 409, {"code": "IDEMPOTENCY_IN_PROGRESS", "retry_after": 2}  # Test 3 — do NOT execute
# else: lease expired → reclaim (§3d). Test 4.
```

### 3c. Commit-together (business row + COMPLETED in ONE transaction) — Test 5

```sql
-- Bind: :key, :owner, :fence (token from claim/reclaim),
--       :http (201), :resp (jsonb), plus business bind vars.
BEGIN;
  -- Fencing guard: only the current lease holder may complete.
  UPDATE idempotency_keys
     SET status = 'COMPLETED',
         response_status = :http,
         response_body   = :resp,
         updated_at      = now()
   WHERE idem_key = :key
     AND lease_owner   = :owner
     AND fencing_token = :fence
     AND status = 'IN_PROGRESS';
  -- If rowcount = 0 → stale owner (reclaimed). ROLLBACK, then re-inspect (§3b)
  -- and return whoever won. This is the fencing enforcement.

  INSERT INTO tickets (ticket_id, title, team, assignee_email)  -- business write
  VALUES (:tid, :title, :team, :email);
  -- Any error here → ROLLBACK rolls back BOTH rows (Test 5). Key stays
  -- IN_PROGRESS-with-expired-lease or is marked FAILED (see note), so a
  -- retry with same key+hash can re-execute instead of wedging on COMPLETED.
COMMIT;
```

> **FAILED vs expired-IN_PROGRESS:** two valid designs. (a) On business error, `ROLLBACK` everything and leave the key `IN_PROGRESS`; the lease expires and a retry reclaims it. (b) Catch the error and in a *new* txn mark `status='FAILED'` so the next same-key+hash retry may re-execute (delete-or-reclaim FAILED), while different-hash still 409s. The pytest below asserts design (a)-compatible behavior: after a crash/rollback the same key+hash is **re-executable**, never stuck returning a 5xx as "stored".

### 3d. Expired-lease reclaim with fencing bump

```sql
-- Bind: :key, :hash, :owner (new uuid), :ttl
-- Only reclaims if lease expired AND hash matches AND still IN_PROGRESS.
UPDATE idempotency_keys
   SET fencing_token   = fencing_token + 1,
       lease_owner     = :owner,
       lease_expires_at = now() + :ttl,
       updated_at      = now()
 WHERE idem_key = :key
   AND request_hash = :hash
   AND status = 'IN_PROGRESS'
   AND lease_expires_at <= now()
RETURNING fencing_token;
-- rowcount = 1 → we own it at the NEW token. Execute, then commit-together with
--   :fence = returned token and :owner = our uuid.
-- rowcount = 0 → someone else reclaimed first (or it COMPLETED). Re-inspect (§3b).
```

**Why fencing matters:** without the `fencing_token = :fence AND lease_owner = :owner` guard in §3c, a crashed-but-not-dead worker A can wake up after B reclaimed and overwrite B's COMPLETED result (last-writer-wins corruption). With fencing, A's `UPDATE … WHERE fencing_token = old` matches 0 rows → A rolls back → client retry reads B's stored result.

Sequence diagram:

```
A claims (fence=1, lease T+30s) ── executes ──╮ crash before commit
                                              │ lease expires
B reclaim (fence=2, new owner) ── executes ── commits COMPLETED(fence=2)
A wakes, tries commit(fence=1) ── 0 rows ── ROLLBACK → 409/refresh → returns B's body ✓
```

---

## 4. pytest suite (psycopg3 + httpx, copy-paste)

Assumes helpers `post_ticket(key, body, hash=None)` and direct DB access via `db` fixture.
Set short TTLs via env (`IDEM_TTL_SECONDS=2` in test) so lease tests don't sleep 30s.

```python
# tests/test_idempotency_35.py
import hashlib, json, time, uuid
import pytest, httpx

BASE = "http://localhost:8002"
TTL = 2  # seconds; test server reads IDEM_TTL_SECONDS

def h(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def post_ticket(key, body, hash_override=None):
    return httpx.post(f"{BASE}/it/tickets", json=body, headers={
        "Idempotency-Key": key,
        "X-Request-Hash": hash_override or h(body),
    }, timeout=10)

def new_key(): return str(uuid.uuid4())

TICKET_A = {"title": "db down", "assignee_email": "oncall@x.io", "team": "support-night", "sla_hours": 4}
TICKET_B = {"title": "totally different", "assignee_email": "other@x.io", "team": "support-night", "sla_hours": 4}

# 1 — Same key+hash returns stored, executes once.
def test_1_exact_replay_returns_stored(db):
    key = new_key()
    r1 = post_ticket(key, TICKET_A); assert r1.status_code == 201
    t1 = r1.json()["ticket_id"]
    r2 = post_ticket(key, TICKET_A)
    assert r2.status_code in (200, 201)
    assert r2.headers.get("Idempotent-Replayed") == "true"
    assert r2.json()["ticket_id"] == t1
    assert db.count_tickets_with_title("db down") == 1  # no double side effect

# 2 — Same key, different hash → 409, original intact.
def test_2_hash_mismatch_409(db):
    key = new_key()
    r1 = post_ticket(key, TICKET_A); assert r1.status_code == 201
    r2 = post_ticket(key, TICKET_B)  # same key, different body+hash
    assert r2.status_code == 409
    assert r2.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    r3 = post_ticket(key, TICKET_A)  # original still replays
    assert r3.json()["ticket_id"] == r1.json()["ticket_id"]

# 3 — IN_PROGRESS with live lease → 409 wait, single execution.
def test_3_in_progress_returns_409_wait(db):
    from tests.helpers import hold_lease  # opens claim, sleeps TTL+1, never commits
    key = new_key()
    with hold_lease(key, h(TICKET_A), seconds=TTL + 2):
        r = post_ticket(key, TICKET_A)
        assert r.status_code == 409
        assert r.json()["code"] == "IDEMPOTENCY_IN_PROGRESS"
        assert "retry_after" in r.json() or "Retry-After" in r.headers
    # after holder finishes, replay returns stored (poll like a client would)
    deadline = time.time() + 15
    while time.time() < deadline:
        r = post_ticket(key, TICKET_A)
        if r.headers.get("Idempotent-Replayed") == "true": break
        time.sleep(0.5)
    assert r.headers.get("Idempotent-Replayed") == "true"

# 4 — Expired lease reclaim with fencing: stale commit rejected.
def test_4_expired_lease_reclaim_fencing(db):
    key, body = new_key(), dict(TICKET_A)
    owner_a = db.claim(key, h(body), ttl_seconds=1)   # fence=1
    time.sleep(1.5)                                    # let lease expire
    owner_b, fence_b = db.reclaim(key, h(body), ttl_seconds=30)
    assert fence_b == owner_a.fencing_token + 1
    # stale A tries to commit with old token → must affect 0 rows
    assert db.try_complete(key, owner_a.lease_owner, owner_a.fencing_token,
                           201, {"ticket_id": "T-STALE"}) == 0
    # B commits with new token → wins
    assert db.try_complete(key, owner_b, fence_b, 201, {"ticket_id": "T-WIN"}) == 1
    r = post_ticket(key, body)
    assert r.json()["ticket_id"] == "T-WIN"            # client sees winner, not stale

# 5 — Commit-together rollback: business + idempotency atomic.
def test_5_commit_together_rollback(db):
    key = new_key()
    with db.sabotage_next_ticket_insert():             # force business INSERT to fail once
        r = httpx.post(f"{BASE}/it/tickets", json=TICKET_A,
                       headers={"Idempotency-Key": key, "X-Request-Hash": h(TICKET_A)},
                       timeout=10)
        assert r.status_code >= 500
    row = db.get_idem(key)
    assert row is None or row["status"] in ("IN_PROGRESS", "FAILED")  # never COMPLETED-with-500
    assert db.count_tickets_with_title("db down") == 0                # business row rolled back
    time.sleep(TTL + 1)  # let any IN_PROGRESS lease lapse (design-a) / or FAILED reusable (design-b)
    r2 = post_ticket(key, TICKET_A)
    assert r2.status_code == 201
    assert db.count_tickets_with_title("db down") == 1
```

**Test helpers** (`tests/helpers.py` — implement once per stack):

```python
# hold_lease: INSERTs IN_PROGRESS directly (simulates a slow worker holding the lease).
# db.claim / db.reclaim / db.try_complete: thin wrappers around §3a/§3d/§3c SQL.
# db.sabotage_next_ticket_insert: toggle (e.g. fault-injection flag or
#   CREATE RULE / trigger raising for one statement) then auto-reset.
```

**Run:**

```bash
IDEM_TTL_SECONDS=2 pytest tests/test_idempotency_35.py -v
# expect: 5 passed. Flakes in test_3/4 almost always mean clock skew
# (lease compared in app vs DB) — compare lease_expires_at <= now() in SQL only.
```

---

## 5. Reviewer checklist (fail the build if any is missing)

- [ ] Hash compared **before** status: different-hash always 409 even if COMPLETED.
- [ ] Live-lease IN_PROGRESS never executes; returns 409 + retry hint.
- [ ] Reclaim requires **expired lease + matching hash + IN_PROGRESS** in a single `UPDATE…WHERE`.
- [ ] Complete carries `WHERE lease_owner AND fencing_token`; stale commit → 0 rows → rollback.
- [ ] Business write + `COMPLETED` in **one transaction**; failure leaves key re-executable (never stores a 5xx as success).
- [ ] Canonical-hash function covered by a unit test (key order / whitespace must not change the hash).
- [ ] Load check: 50 concurrent same-key+hash POSTs → exactly 1 business row, 49 replays (k6/`hey` script in CI).
