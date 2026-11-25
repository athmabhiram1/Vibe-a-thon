# 04 — Auth & Scopes for Demo (JWT + Scope Middleware + Demo Guards)

> Companion build spec to `research/final/13-safety-audit.md` (the authoritative safety design).
> This file narrows that design to **what the demo implements**: a minimal JWT resource
> server, a three-tier scope split, per-tool middleware, `${ENV}` secret handling with
> redaction, and demo-mode guards. Anything destructive / production (double approval,
> Postgres idempotency ledger, hash-chained audit) is referenced, not re-implemented.

## 1. Goal and non-goals

**Demo proves:** unauthenticated → 401, wrong scope → 403 with actionable challenge,
right scope → executes; secrets never leak into logs/previews; `DEMO_MODE=true`
makes all writes safe to click.

**Non-goals (deferred to 13):** JWKS rotation/caching policy, double-approval flow,
Postgres idempotency table, hash-chained `audit.jsonl` verification, multi-tenant
isolation. Demo keeps in-memory equivalents behind the same interfaces so production
can swap stores without changing the proxy.

## 2. JWT verifier + AuthSettings (MCP Python SDK ≥ 2.2)

Authoritative pattern per 13 §2: `TokenVerifier` + `AuthSettings` travel together;
`stdio` transport skips verification (process boundary is the trust boundary).

```python
import asyncio, os
import httpx, jwt
from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings

ISSUER = os.environ["DEMO_ISSUER"]  # e.g. https://auth.demo.local
METADATA_URL = f"{ISSUER}/.well-known/oauth-authorization-server"
MCP_SERVER_URL = os.environ.get("DEMO_MCP_URL", "http://localhost:3000/mcp")

class DemoJWTVerifier(TokenVerifier):
    def __init__(self):
        md = httpx.get(METADATA_URL, timeout=5).raise_for_status().json()
        assert md["issuer"] == ISSUER, f"Unexpected issuer: {md['issuer']}"
        self._jwks = jwt.PyJWKClient(md["jwks_uri"], timeout=5)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            key = await asyncio.to_thread(
                self._jwks.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token, key, algorithms=["RS256"],  # fixed allowlist: no alg-confusion
                issuer=ISSUER, audience=MCP_SERVER_URL,
                leeway=30, options={"require": ["exp"]},
            )
        except jwt.PyJWKClientConnectionError:
            raise  # JWKS outage != invalid token -> fail closed (503), don't map to 401
        except jwt.PyJWTError:
            return None  # SDK -> 401 + RFC9728 discovery challenge
        scope = claims.get("scope", "")
        scopes = scope.split() if isinstance(scope, str) else list(scope or [])
        return AccessToken(
            token=token,
            client_id=claims.get("client_id") or claims.get("azp") or "",
            scopes=scopes,
            expires_at=int(claims["exp"]),
            resource=MCP_SERVER_URL,
            subject=claims.get("sub"), claims=claims,
        )

mcp = MCPServer(
    "OnboardingDemo",
    token_verifier=DemoJWTVerifier(),
    auth=AuthSettings.model_validate({
        "issuer_url": ISSUER,  # plain str: AnyHttpUrl appends "/" and breaks exact match
        "resource_server_url": MCP_SERVER_URL,  # == aud + PRM `resource`
        "required_scopes": ["read:all"],  # server-wide floor: every call is at least a read
        "validate_token_resource": True,  # reject aud/resource mismatch (default-off pre-3.0)
    }),
)
```

Rules (from 13 §2): exact `issuer_url` string; `resource_server_url` must equal the public
client-facing URL; `required_scopes` missing → SDK 403 (no `scope` param — clients re-read
`scopes_supported`); always set `validate_token_resource=True`; never take identity from
tool args — `get_access_token().subject/client_id` is the actor.

**Demo shortcut (allowed):** if `DEMO_JWKS_STATIC` is set, `DemoJWTVerifier` may verify
against a checked-in test JWKS + `DEMO_ISSUER=https://demo.local` instead of fetching
metadata, so the demo runs offline. Gate strictly on `DEMO_MODE=true`; refuse in prod.

## 3. Scope split: `read:all` / `write:all` / `admin:all`

Three hierarchical tiers; higher implies lower (`admin:all ⊃ write:all ⊃ read:all`).
The SDK enforces only the server floor — hierarchy and per-tool mapping live in our
middleware (§4).

| Scope | Grants | Example tools |
|---|---|---|
| `read:all` | all reads + previews (`preview=true`, rollback-only) | `search_users`, `list_courses`, `get_user`, `preview_provision`, `preview_assign` |
| `write:all` | + single-approval mutating writes (13 Class B) | `provision_user`, `assign_license`, `assign_course`, `activate_account` |
| `admin:all` | + destructive / irreversible (13 Class C) | `deprovision_user`, `revoke_license`, `reset_credentials`, bulk `provision_*` (n>10) |

Token examples: a viewer JWT carries `scope: "read:all"`; an operator carries
`"read:all write:all"`; the demo admin carries all three. Never issue wildcard `*`;
unknown scope strings are ignored (deny-closed, cf. 13 §7).

## 4. Per-tool scope middleware

```python
from mcp.server.auth.middleware.auth_context import get_access_token

TOOL_SCOPES: dict[str, str] = {  # exhaustive: missing entry == deny (13 §7)
    # reads
    "search_users": "read:all", "list_courses": "read:all",
    "get_user": "read:all", "preview_provision": "read:all",
    "preview_assign": "read:all",
    # mutating
    "provision_user": "write:all", "assign_license": "write:all",
    "assign_course": "write:all", "activate_account": "write:all",
    # destructive
    "deprovision_user": "admin:all", "revoke_license": "admin:all",
    "reset_credentials": "admin:all",
}

_RANK = {"read:all": 1, "write:all": 2, "admin:all": 3}

def require_scope(tool_name: str) -> AccessToken:
    tok = get_access_token()
    needed = TOOL_SCOPES.get(tool_name)
    if needed is None:
        raise ScopeDenied("ambiguous_scope", tool_name, needed="?")
    have = max((_RANK.get(s, 0) for s in (tok.scopes if tok else [])), default=0)
    if tok is None or have < _RANK[needed]:
        raise ScopeDenied("insufficient_scope", tool_name, needed=needed)
    if tok.claims.get("tenant") and tok.claims["tenant"] != current_tenant():
        raise ScopeDenied("ambiguous_scope", tool_name, needed=needed)  # cross-tenant
    return tok

class ScopeDenied(Exception):
    def __init__(self, reason, tool, needed):
        super().__init__(reason)
        self.reason, self.tool, self.needed = reason, tool, needed
    # HTTP mapping: 403 + WWW-Authenticate: Bearer scope="<needed>"
    #   error="insufficient_scope" | "ambiguous_scope", never echo the token.
```

Middleware order per call: **auth (SDK) → demo-guard (§6) → scope check (above) →
Cite-Before-Act proxy (13 §1) → invoke**. Scope denial short-circuits before any
preview/approval lookup and appends one audit line (`decision=deny`,
`reason=insufficient_scope|ambiguous_scope`) per 13 §8.

## 5. `${ENV}` secret handling + redaction

Per 13 §6, demo implements the same contract with a 30-line helper:

1. **Reference, don't inline.** Clients pass `"api_key": "${ENV:PROV_API_KEY}"`.
   Plaintext secrets in args are rejected (`reason=secret_leak_blocked`).
2. **Resolve server-side at invoke time only** — after scope + approval pass, just
   before the downstream call; resolved values live in a short-lived local, never
   stored.
3. **Hash the redacted form.** `preview_hash = sha256(canonical_json(redacted_args))`
   so hashes are stable without leaking values.
4. **Redact every sink:** previews, approvals, logs, idempotency records, error
   strings, audit `args_hash` inputs. Regex: `\$\{ENV:[A-Za-z_][A-Za-z0-9_]*\}` plus
   any resolved value → `[REDACTED]`.

```python
import re
ENV_REF = re.compile(r"^\$\{ENV:([A-Za-z_][A-Za-z0-9_]*)\}$")

def resolve_env_refs(args: dict) -> tuple[dict, list[str]]:
    resolved, names = {}, []
    for k, v in args.items():
        m = ENV_REF.match(str(v)) if isinstance(v, str) else None
        if m:
            name = m.group(1)
            val = os.environ.get(name)
            if val is None:
                raise SecretError(f"missing env: {name}")  # name only, no value
            resolved[k], names.append(val)
        else:
            resolved[k] = v
            if isinstance(v, str) and looks_secret(v):
                raise SecretError("plaintext secret rejected; use ${ENV:NAME}")
    return resolved, names  # caller scrubs `names` in finally: overwrite + del
```

## 6. Demo-mode guards

`DEMO_MODE=true` (default in the demo build) makes every write click-safe:

| Guard | Behavior |
|---|---|
| `DEMO_MODE=true` required for static-JWKS + canned tokens | server refuses to start demo shortcuts when `false`/unset |
| Write sandbox | Class B/C tools run against seeded fakes; outbound HTTP disabled except allowlisted `DEMO_EGRESS_ALLOW` (default: none) |
| Banner + tool annotations | every write preview prints `DEMO — no real accounts touched`; destructive tools additionally require typing the preview id (re-confirmation standing in for 2nd approval) |
| Canned tokens | three printed JWTs (viewer/operator/admin) with 30-min expiry, audience locked to `DEMO_MCP_URL`; `validate_token_resource` still on |
| Kill switch | `DEMO_READONLY=true` downgrades all writes to `preview=true` regardless of scope |
| No persistence | audit goes to stdout `audit.jsonl` lines (same schema as 13 §8, `v:0-demo`); secrets never printed |

Startup self-check (fail closed): assert demo JWKS ≠ prod issuer, assert egress
allowlist empty by default, assert `DEMO_READONLY` parsing is strict (`"true"` only).

## 7. Minimal test matrix (ship-blocking)

| # | Case | Expect |
|---|---|---|
| 1 | no token → `search_users` | 401 + RFC9728 challenge |
| 2 | viewer (`read:all`) → `provision_user` | 403 `insufficient_scope`, `scope="write:all"` |
| 3 | operator → `revoke_license` | 403 `scope="admin:all"` |
| 4 | admin → `provision_user` w/ approval | allow + audit line |
| 5 | unknown tool / unmapped scope | deny `ambiguous_scope` |
| 6 | `${ENV:KEY}` arg | preview/log shows `${ENV:KEY}`, never value |
| 7 | plaintext secret in args | deny `secret_leak_blocked` |
| 8 | `DEMO_READONLY=true` + operator write | served as preview, no commit |

*Sources: `research/final/13-safety-audit.md` §§1–8 (JWT verifier, scope middleware,
`${ENV}` redaction, audit schema); MCP Python SDK authorization docs; demo deltas
(scope hierarchy, static-JWKS offline mode, `DEMO_READONLY` sandbox) are new to this file.*
