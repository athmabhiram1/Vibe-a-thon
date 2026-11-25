# 13 — Safety & Audit Design for Onboarding Writes (provision, assign, activate)

> Scope: all **mutating onboarding tools** — `provision_user`, `assign_license` / `assign_course`,
> `activate_account`, plus destructive variants (`deprovision`, `revoke`, `reset_credentials`).
> Reads (search/list/preview/get) are auto-allowed. Writes require Cite-Before-Act + approval +
> idempotency + append-only audit. Secrets (`${ENV:…}`) are never persisted.

---

## 1. Cite-Before-Act proxy (the gatekeeper)

No mutating tool is called directly by the agent. Every call passes through a **safety proxy**
(middleware / wrapper) that enforces this order:

```
1. CITE   — proxy resolves which policy rule + which preview authorizes this call
2. CHECK  — scope match, preview_hash match, approval validity, idempotency state
3. ACT    — only then invoke the underlying tool / API
4. RECORD — append one audit.jsonl line (success AND denial)
```

**Cite means:** the proxy must be able to point at (a) the exact preview object
(`preview_id` + `preview_hash`) the user approved, and (b) the policy row in §3 that
authorized it. If either reference is missing, stale, or ambiguous → **deny** (see §7).

Reference pattern (adapted from StartDebugging safe-file-write + HashGate ordering:
policy-check → server-side re-derivation → hash-compare → validate):

```python
async def guarded_call(tool_name, args, ctx):
    decision = classify(tool_name, args)          # §3 table
    if decision == "auto_allow":
        return await invoke(tool_name, args)
    preview = previews.get(ctx.preview_id)        # must exist, unexpired, bound to caller
    if preview is None:
        return deny("no_preview", ctx)
    canonical = canonical_json(tool_name, args)   # sorted keys, no whitespace
    if sha256_hex(canonical) != preview.preview_hash:
        return deny("preview_hash_mismatch", ctx) # args changed after preview
    approval = approvals.get(ctx.approval_id)     # must cite preview_id + hash
    if not valid_approval(approval, preview, ctx):
        return deny("approval_invalid", ctx)
    return await invoke_with_idempotency(tool_name, args, ctx)
```

Key properties borrowed from surveyed designs:

- **State is a receipt for one specific diff**, not a session token. The `preview_hash`
  is minted at preview time from canonical args; any arg change invalidates it.
- **Optimistic concurrency:** preview also captures `base_hash` (e.g. user-record version /
  ETag). Re-check at commit; abort on `412 precondition_failed` if the world moved.
- **Replay is harmless:** second commit with same `(idempotency_key, preview_hash)` returns
  the stored result, never re-executes (see §5).

---

## 2. MCP Python SDK — AuthSettings + JWT (authoritative pattern)

Use the official MCP Python SDK resource-server pattern (MCP spec 2026-07-28, SDK ≥ 2.2).
Sources: `py.sdk.modelcontextprotocol.io/run/authorization`, `modelcontextprotocol.io`
authorization tutorial, SDK `src/mcp/server/auth/*`.

```python
import asyncio
import httpx2, jwt
from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.middleware.auth_context import get_access_token

ISSUER = "https://auth.example.com"              # exact issuer from discovery metadata
METADATA_URL = "https://auth.example.com/.well-known/oauth-authorization-server"
MCP_SERVER_URL = "http://localhost:3000/mcp"     # public URL = audience + resource

class JWTTokenVerifier(TokenVerifier):
    def __init__(self):
        md = httpx2.get(METADATA_URL, timeout=5).raise_for_status().json()
        assert md["issuer"] == ISSUER, f"Unexpected issuer: {md['issuer']}"
        self.jwks = jwt.PyJWKClient(md["jwks_uri"], timeout=5)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            key = await asyncio.to_thread(self.jwks.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token, key, algorithms=["RS256"],   # fixed allowlist stops alg-confusion
                issuer=ISSUER, audience=MCP_SERVER_URL,
                leeway=30, options={"require": ["exp"]},
            )
        except jwt.PyJWKClientConnectionError:
            raise            # JWKS outage ≠ invalid token; fail closed / 503
        except jwt.PyJWTError:
            return None      # SDK turns None → 401 + RFC9728 discovery challenge
        scope = claims.get("scope")
        return AccessToken(
            token=token,
            client_id=claims.get("client_id") or claims.get("azp") or "",
            scopes=scope.split() if isinstance(scope, str) else [],
            expires_at=int(claims["exp"]),
            resource=MCP_SERVER_URL,                # jwt.decode already checked aud
            subject=claims.get("sub"), claims=claims,
        )

mcp = MCPServer(
    "Onboarding",
    token_verifier=JWTTokenVerifier(),
    auth=AuthSettings.model_validate({
        "issuer_url": ISSUER,                       # string keeps no trailing slash
        "resource_server_url": MCP_SERVER_URL,
        "required_scopes": ["onboarding:write"],    # server-wide floor
        "validate_token_resource": True,            # reject aud/resource mismatch
    }),
)

@mcp.tool()
def provision_user(email: str) -> str:
    tok = get_access_token()   # identity comes from token, never from tool args
    if tok is None: return "anonymous"
    return f"{tok.client_id} scopes={tok.scopes}"
```

Rules:

| Setting | Meaning | Gotcha |
|---|---|---|
| `issuer_url` | → `authorization_servers` in PRM discovery doc | Pass a plain string; `AnyHttpUrl()` appends `/` and breaks exact issuer match |
| `resource_server_url` | Public MCP URL; `aud` + PRM `resource` | Must equal what clients connect to |
| `required_scopes` | Floor every request must carry | Missing scope → `403` (SDK 403 carries no `scope` param; clients re-read `scopes_supported`) |
| `validate_token_resource=True` | Refuse `AccessToken.resource != resource_server_url` | Default-off pre-3.0 (with deprecation warning); **always set it** |
| `token_verifier` + `auth` | Must travel together | One without the other → `ValueError` at construction |
| Transport | Auth lives in HTTP headers | `stdio` / in-memory `Client(mcp)` **skip** verification; process boundary is the trust boundary there |

**Per-tool scopes** (SDK checks only the server floor): add a thin middleware mapping
`provision_user → onboarding:write`, `assign_license → licensing:write`,
`activate_account → onboarding:write`, reads → `onboarding:read`, returning
`403 insufficient_scope` with an actionable `scope="…"` challenge (per community
`ToolScopeMiddleware` pattern).

---

## 3. Detection table — read auto-allow vs mutating vs destructive

Classification is by **(tool, args)** — e.g. `activate_account(dry_run=true)` is a preview,
not a write.

| Class | Tools / examples | Proxy behavior | Approval | Audit |
|---|---|---|---|---|
| **A — Read (auto-allow)** | `search_users`, `list_courses`, `get_user`, `preview_provision`, `preview_assign` (`preview=true`, rollback-only, never commits) | Execute immediately; still log at `observe` level | None | `decision=allow` |
| **B — Mutating (preview + single approval)** | `provision_user`, `assign_license`, `assign_course`, `activate_account` | Require fresh preview + `preview_hash` match + one human approval + `Idempotency-Key` | **1 approval** (`APPROVE <preview_id>`) | `require_approval → allow/deny` full record |
| **C — Destructive / irreversible (preview + double approval)** | `deprovision_user`, `revoke_license`, `reset_credentials`, bulk `provision_*` (n>10), any scope-escalating write | Same as B **plus**: second distinct approver OR same-approver re-confirmation after 30 s cool-down; no bulk-destructive without ticket ref | **2 approvals** | Full record + `risk=destructive` + ticket ref |
| **Ambiguous / unclassified** | Unknown tool, missing scope map entry, arg-dependent risk undecidable | **Deny-closed**: treat as Class C minimum, actually **reject** until a rule is added | N/A — rejected | `decision=deny reason=ambiguous_scope` |

Enforcement notes:

- `?preview=true` runs the **same code path** with commit disabled + `conn.rollback()` on
  release, so previews surface defaults/triggers/constraint errors (not estimates).
- Destructive tools also require `If-Match: <base_hash>` (resource version at preview time).
- Reads with side effects (e.g. `get_user` that sends an email) are Class B — classify by
  **effect**, not by verb.

---

## 4. UX lines — exact approval prompts (confirm these strings in implementation)

The agent MUST print these verbatim (fill `<…>` slots) before any Class B/C execution:

**B — single approval prompt:**

```text
⚠️ WRITE PREVIEW <preview_id> (<tool_name>)
Args hash: <preview_hash8> | Idempotency-Key: <key>
Effect: <one-line human-readable effect, e.g. "Create ada@example.com + assign Pro license ($12/seat)">
Reply APPROVE <preview_id> to execute, or REJECT <preview_id> with a reason.
Expires in 10 min. Same key + different args → 409 conflict, never executes.
```

**C — destructive / double approval prompt:**

```text
🛑 DESTRUCTIVE PREVIEW <preview_id> (<tool_name>) — IRREVERSIBLE
Args hash: <preview_hash8> | Idempotency-Key: <key> | Ticket: <ticket_ref>
Effect: <effect> | Blast radius: <n users / seats / $>
Reply APPROVE <preview_id> FIRST, then a second approver (or you after 30s) replies APPROVE <preview_id> AGAIN.
Both approvals cite the same preview_hash; any arg change voids all approvals.
```

**Denials / conflicts (printed + audited):**

```text
DENIED <preview_id>: <no_preview | preview_hash_mismatch | approval_invalid |
  approval_expired | ambiguous_scope | insufficient_scope | precondition_failed>.
Ask for a fresh preview; do not retry with the same approval.
```

```text
CONFLICT: Idempotency-Key <key> already used with different args
(expected <hashA8>, got <hashB8>). Generate a new key for a new action.
```

---

## 5. `idempotency_key` + `preview_hash` binding

Two identifiers, two jobs (per Stripe-style / FastAPI-Postgres literature):

- `idempotency_key` — **which** user action (client-generated UUIDv4 per intent:
  `run_id + step_id`; mandatory for agent principals; `428`/`422` if absent on writes).
- `preview_hash` (`request_hash`) — **what** exact bytes were approved
  (`sha256(canonical_json(tool, args, schema_version))`; canonical = sorted keys,
  `separators=(",",":")`, `ensure_ascii=False`; validate-then-hash, never hash raw bytes).

Server table (Postgres; PK is the concurrency control):

```sql
CREATE TABLE onboarding_idempotency (
  actor_id      uuid NOT NULL,          -- from JWT sub, never from args
  operation     text NOT NULL,          -- stable command name: provision.create, license.assign…
  key           text NOT NULL,          -- client Idempotency-Key
  request_hash  char(64) NOT NULL,      -- preview_hash of canonical args
  state         text NOT NULL CHECK (state IN ('IN_PROGRESS','SUCCEEDED','FAILED')),
  lease_token   uuid NOT NULL,          -- fencing token for expiry reclaim
  resource_id   text,
  response_code smallint,
  response_body jsonb,                  -- allowlisted snapshot only, no secrets
  created_at    timestamptz DEFAULT now(),
  expires_at    timestamptz NOT NULL,   -- e.g. now()+24h
  PRIMARY KEY (actor_id, operation, key)
);
```

State machine (all paths audited):

| Existing | Hash | Meaning | Response |
|---|---|---|---|
| none | — | new command; `INSERT … ON CONFLICT DO NOTHING` wins → execute | execute in TX with business row + audit line |
| `SUCCEEDED` | same | safe replay | return stored result, **no re-execution** |
| `FAILED` | same | definitive rejection already recorded | return same error |
| `IN_PROGRESS` | same | original still owns it | `409 IDEMPOTENCY_IN_PROGRESS` — wait + retry same key |
| any | **different** | key reused for different args | `409 IDEMPOTENCY_CONFLICT` — never execute |
| expired `IN_PROGRESS` | same | possibly abandoned | reclaim only with new `lease_token`; old owner's commit must fail fencing check |

Commit rule: **business mutation + idempotency `SUCCEEDED` row + audit line commit in one
transaction.** If the TX rolls back, none exists. Semantic-replay corollary (Xu et al.):
key state by **action** (`actor + operation + key + request_hash`), not by token — a fresh
approval token for an already-`COMMITTED` action returns the first result instead of
re-executing. Warn (don't silently proceed) when two keys differ only by turn/step but
carry identical params inside a short window.

---

## 6. `${ENV}` redaction

- Client args may reference secrets as `${ENV:VAR_NAME}`. The proxy resolves them
  **server-side at invoke time** and **never** writes the plaintext into previews,
  approvals, logs, idempotency `response_body`, or error strings.
- Redaction function applied to every sink: replace `\$\{ENV:[A-Za-z_][A-Za-z0-9_]*\}`
  and any resolved value matching a known-secret shape with `[REDACTED]`.
- `preview_hash` is computed over the **redacted canonical form** (reference by name,
  not value), so hashes stay stable without leaking secrets.
- Violation (secret-shaped value reaching a sink) → `deny` + `reason=secret_leak_blocked`
  + security audit line.

---

## 7. Ambiguous-scope rejection + double-approve cached result

**Ambiguous scope → reject (deny-closed):**

```python
SCOPES = {"provision_user": "onboarding:write", "assign_license": "licensing:write",
          "activate_account": "onboarding:write", ...}   # exhaustive
needed = SCOPES.get(tool_name)
if needed is None or needed not in token.scopes:
    return deny("ambiguous_scope" if needed is None else "insufficient_scope")
```

Unknown tool, missing map entry, wildcard scope request, or cross-tenant args
(`actor.tenant != args.tenant`) → `deny` + audited `ambiguous_scope`. Adding the rule
requires a code change + review, never a runtime exception.

**Double-approve for cached results:** a cached/stored `SUCCEEDED` result may be
**returned** on exact replay (same key + same hash + same actor + unexpired), but any
**re-execution** (new key, hash drift, expiry, base-hash change) restarts the full
Class B/C approval flow. Approvals are single-action, ≤10 min TTL, bound to
`(actor, client_id, preview_id, preview_hash)`; at most 20 pending per user
(oldest evicted). The second approval for Class C must cite the **same**
`preview_id + preview_hash` and arrive from a distinct approver (or same approver
after cool-down); a changed hash voids both.

---

## 8. Append-only `audit.jsonl` schema (tamper-evident hash chain)

One JSON object per line, UTF-8, `\n`-terminated, `0600` perms. Every proxy decision
(`allow`, `deny`, `require_approval`, `usage`) appends exactly one line — including denials.
Hash: `hash = sha256_hex(prev_hash_bytes ‖ canonical_json(line_without_hash))`;
genesis `prev_hash = "0"×64`; `seq` dense from 1; verification stops at first break and
reports `firstBadSeq`. (Chain proves integrity, not authorship or completeness — anchor
head hash externally for truncation detection.)

```jsonc
{
  "v": 1,                                   // schema version
  "seq": 42,                                // dense position, starts at 1
  "ts": "2026-11-22T10:14:08.123456Z",      // RFC3339 UTC, completion time
  "session": "sess_abc", "actor": "user:ada", "client_id": "onboarder-web",
  "tenant": "acme",
  "server": "onboarding-mcp", "tool": "provision_user",
  "operation": "provision.create",
  "args_hash": "sha256:<hex64>",            // NEVER raw args
  "preview_id": "prv_7f3a", "preview_hash": "<hex64>",
  "approval_id": "apr_9c1e", "approver": "ada@example.com",
  "decision": "allow | deny | require_approval | observe",
  "rule": "policy:B-single-approval | policy:C-double-approval | scope/* | budget/*",
  "reason": "approval:apr_9c1e | preview_hash_mismatch | ambiguous_scope | …",
  "idempotency_key": "550e8400-…", "idempotency_state": "SUCCEEDED | CONFLICT | …",
  "latency_ms": 18, "cost_usd": 0.0,
  "prev_hash": "<hex64>", "hash": "<hex64>"
}
```

Minimal writer contract: compute `args_hash`/`preview_hash` over redacted canonical JSON;
fill `prev_hash` from prior line's `hash`; write atomically (append + fsync); never
rewrite. Verifier: check `seq` continuity → `prev_hash` link → recomputed `hash`, in that
order. Report `head_hash + count` alongside verdict so truncation is detectable by an
external anchor.

---

## 9. Provision / assign / activate wiring checklist

1. SDK `JWTTokenVerifier + AuthSettings(required_scopes=["onboarding:write"],
   validate_token_resource=True)`; per-tool scope middleware.
2. Every write tool gets `preview=true` (rollback-only) + canonical `preview_hash` +
   mandatory `Idempotency-Key` + `If-Match: base_hash` for destructive.
3. Proxy enforces Cite-Before-Act (§1) → classification (§3) → exact UX strings (§4).
4. Secrets only as `${ENV:VAR}`, redacted at every sink (§6).
5. Ambiguous scope = deny; Class C = double approval citing same hash (§7).
6. One `audit.jsonl` line per decision, hash-chained (§8); anchor head externally.

*Sources: MCP Python SDK authorization docs (`py.sdk.modelcontextprotocol.io/run/authorization`,
`modelcontextprotocol.io` RS256 tutorial, `mcp/server/auth/*`); Belgavi.AI agent-ready
contracts (preview-hash binding, mandatory idempotency keys); StartDebugging preview-confirm-apply
(state-as-receipt, base-hash concurrency); DEV/vanhpoker semantic-replay + Nabh Patodi
Postgres idempotency ledger (`ON CONFLICT`, fencing, commit-together rule); MAQPNA /
speccheck / usertrust / DCTL append-only hash-chained JSONL audit-log specs.*
