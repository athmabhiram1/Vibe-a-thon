# 13 — Auth Library: Keycloak + CEL vs Simple JWT + FastMCP Scopes

> Verdict up front: **ship simple JWT + FastMCP `JWTVerifier` + `require_scopes` + `AuthMiddleware`.** Skip live Keycloak unless a judge explicitly asks "where is the IdP?" — then show it as a 1-slide upgrade path. You keep the "cannot bypass security" wow (Solo.io MCP.STORE pattern) at ~1% of the weight.

## 0. TL;DR comparison

| | A: Keycloak + CEL/JS policies | B (recommended): Simple JWT + FastMCP scopes |
|---|---|---|
| Image / RAM | `quay.io/keycloak/keycloak` ~500–700 MB compressed; **base RSS ~1250 MB** (realm cache + 10k sessions), K8s defaults **request 1700 Mi / limit 2 Gi**; heap = 70% of limit + ~300 MB non-heap | **0 MB extra** — `PyJWT` + `fastmcp` you already ship; verifier is ~20 lines; keys in env |
| Cold start | **20–40 s** `start-dev --import-realm`, 60 s+ optimized `start --optimized` + DB check; needs Postgres for prod (H2 dev only) | **<100 ms** — static `JWKS.json` or HS256 secret; no container |
| Realm setup | 30–60 min first time: realm JSON + client + roles + mappers + `--import-realm` mount + admin bootstrap + token test | **5 min**: 1 Python script mints 3 tokens (see §3) |
| Wristband filtering | Realm role `wristband_vip` → client-scope mapper → `realm_access.roles` → Keycloak Policy Enforcer / CEL `allow if "vip" in auth.claims` | JWT claim `wristband: vip\|staff\|general` or scope `vip:read` → `require_scopes()` + `on_list_tools` hide |
| Demo failure modes | Port 8080 clash, Java OOM on 8 GB laptop, realm import silently skipped if file mis-mounted, token expiry mid-demo, Wi-Fi → JWKS fetch fail | Expired `exp` (set 8 h), clock skew (allow 60 s leeway), wrong `aud` (1-line fix) |
| Judge optics | High enterprise gravitas ("real IdP") — MCP.STORE runner-up won on this | High velocity + honest scoping — GSA rubric rewards "real agent-facing action, not thin wrapper" + Cite-Before-Act gate |
| When to use | Track 3 / enterprise buyer in room, "multi-tenant hospital" story, judge asks about SSO/OIDC | **Default for all tracks.** Upgrade to Keycloak post-demo without changing tool code (same `require_scopes` strings) |

Sources: Keycloak memory/perf — `docs/guides/high-availability/partials/concepts/perf_recommendations.adoc` ("1250 MB base"), `changes-24_0_0.adoc` ("requests 1700MiB / limits 2GiB", "heap 70% + ~300 MB non-heap"), `docs/guides/server/containers.adoc` (`--import-realm` mount to `/opt/keycloak/data/import`); FastMCP — `/prefecthq/fastmcp` `fastmcp-server-middleware-authorization.mdx` (`AuthMiddleware`, `on_list_tools` filter, `on_call_tool` gate, "skips all checks for STDIO"), `docs/servers/authorization.mdx` (`require_scopes`), `docs/deployment/sandboxed-agents.mdx` (per-tool `require_scopes("write:summary")` + global `JWTVerifier`), `docs/servers/auth/token-verification.mdx` (env-var config).

## 1. Why Keycloak hurts in a 24–48 h hackathon

1. **Weight.** Even `start-dev` wants >1 GB free. On a hackathon laptop already running Docker (Postgres + Redis + Ollama per `11-lib-docker.md` ≈ 5 GB with an 8B model), Keycloak tips you into swap. Judges see a spinner, not security.
2. **Realm setup is a second demo.** Create realm `vibe` → client `mcp-client` (confidential, service-accounts on) → roles `wristband_vip/staff/general` → client-scope mapper (add roles to `aud`/`scope` claim) → export `realm-export.json` → mount + `start-dev --import-realm` → create `admin/change_me` → test `curl .../realms/vibe/protocol/openid-connect/token`. One typo = "invalid_client" on stage. Budget 30–60 min + a re-export.
3. **CEL/policy layer is extra.** Keycloak Authorization Services uses JS/Drools/CEL-ish policies per resource. Synapse-generated tools are dumb HTTP forwards (`research/03-synapse-technical.md` §2.2) — they don't call the policy enforcer unless you hand-wire it. You pay the complexity without the enforcement.
4. **Offline risk.** Hosted JWKS fetch + token endpoint = Wi-Fi dependency. Venue Wi-Fi + OIDC discovery = classic demo death.

Keep Keycloak as a **diagram box + realm JSON in repo** (`infra/keycloak/realm-export.json`), not a running container.

## 2. Recommended: simple JWT + FastMCP scopes (copy-paste)

Architecture: tiny local issuer (your Python script) → RS256 or HS256 JWT with `wristband` claim + `scope` → `JWTVerifier` globally → `require_scopes()` per tool → `AuthMiddleware` hides what you can't call.

### 2.1 Mint demo tokens (5 min, no server)

```python
# infra/auth/mint.py — run once, paste tokens into .env / Inspector header
import time, jwt  # pip install PyJWT

SECRET = "demo-only-32char-secret-change-me"  # HS256; prod: RS256 + JWKS.json
def mint(sub: str, wristband: str, scopes: list[str]) -> str:
    now = int(time.time())
    return jwt.encode({
        "iss": "http://localhost:8001", "aud": "vibe-mcp",
        "sub": sub, "wristband": wristband, "scope": " ".join(scopes),
        "iat": now, "exp": now + 8*3600,
    }, SECRET, algorithm="HS256")

if __name__ == "__main__":
    print("VIP  :", mint("judge-01", "vip", ["tools:read", "tools:write", "vip:read"]))
    print("STAFF:", mint("staff-01", "staff", ["tools:read", "tools:write"]))
    print("GEN  :", mint("guest-01", "general", ["tools:read"]))
```

Wristband model: `general` = read-only preview, `staff` = read + activate, `vip` = + restricted tool (e.g. `discharge_patient`, `approve_refund`). One claim, three tokens, instant role-play on stage.

### 2.2 Verify + per-tool scopes (the server file)

```python
# server.py — works with Synapse-generated or hand-written FastMCP
import os
from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes
from fastmcp.server.auth.providers.jwt import JWTVerifier

# HS256 demo: point JWKS at local static file or use env; prod: real JWKS URI
auth = JWTVerifier(
    jwks_uri=os.getenv("JWT_JWKS_URI", "http://localhost:8001/.well-known/jwks.json"),
    issuer="http://localhost:8001",
    audience="vibe-mcp",
    # required_scopes=["tools:read"],  # global floor; leave None, gate per-tool instead
)

mcp = FastMCP(name="VibeServer", auth=auth)

@mcp.tool(auth=require_scopes("tools:read"))
def onboard_preview(name: str, dept: str) -> dict:
    """STAGE (read-only): any wristband can preview."""
    return {"plan": {"name": name, "dept": dept}, "note": "confirm to activate"}

@mcp.tool(auth=require_scopes("tools:write"))
def onboard_activate(preview_hash: str, confirm: bool, idempotency_key: str) -> dict:
    """ACTIVATE (write): needs staff/vip. confirm=True + hash required."""
    if not confirm:
        return {"status": "aborted"}
    return {"status": "applied", "preview_hash": preview_hash}

@mcp.tool(auth=require_scopes("vip:read"))
def vip_discharge(patient_id: str) -> dict:
    """VIP-only: hidden from general/staff in tools/list."""
    return {"patient": patient_id, "bed": "freed"}
```

Per-tool `auth=` is AND-logic (all listed scopes must be present). Global `JWTVerifier` handles signature/`iss`/`aud`/`exp`; per-tool handles *what this wristband may do*. Source: `docs/servers/authorization.mdx`, `docs/deployment/sandboxed-agents.mdx`.

### 2.3 Hide tools you can't call (wristband filtering judges can SEE)

```python
from fastmcp.server.middleware.authorization import AuthMiddleware

def wristband_is_vip(auth_claims: dict) -> bool:
    # adapt to your verifier's claims shape: scope string or wristband field
    return "vip:read" in auth_claims.get("scope", "") or auth_claims.get("wristband") == "vip"

# Global gate: filters tools/list AND blocks call_tool
mcp.add_middleware(AuthMiddleware(auth=wristband_is_vip))
# For per-tool granularity, prefer @mcp.tool(auth=require_scopes(...)) above;
# use AuthMiddleware for cross-cutting rules (e.g. deny-all when token expired).
```

Demo beat: `tools/list` with GEN token shows 2 tools; same call with VIP token shows 3. That visible filtering is the "cannot bypass" moment MCP.STORE won with — no Keycloak needed. `on_list_tools` filters the list response; `on_call_tool` gates execution (same file: `fastmcp-server-middleware-authorization.mdx`). Note: STDIO transport skips OAuth checks — demo over HTTP/SSE so judges see enforcement.

Env hygiene (matches Synapse `${VAR}` pattern, `research/03-synapse-technical.md` §2.3):

```bash
# .env.example — commit this, never commit .env
JWT_JWKS_URI=http://localhost:8001/.well-known/jwks.json
JWT_ISSUER=http://localhost:8001
JWT_AUDIENCE=vibe-mcp
GEN_TOKEN=eyJ...
STAFF_TOKEN=eyJ...
VIP_TOKEN=eyJ...
```

## 3. If a judge asks "is this real auth?" — 30-sec upgrade answer

> "Demo runs on short-lived HS256 JWTs with the same `iss/aud/scope` contract as Keycloak. Swapping to Keycloak is a 3-line change: point `jwks_uri` at `http://keycloak:8080/realms/vibe/protocol/openid-connect/certs`, keep every `require_scopes()` string identical, realm JSON is already in `infra/keycloak/realm-export.json`. We skipped the 2 GB container so the agent — not the IdP boot — owns the demo time."

Realm stub to include (don't boot it live):

```bash
# infra/keycloak/realm-export.json — export once from a local Keycloak, commit, show as artefact
docker run --rm -p 8080:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=change_me quay.io/keycloak/keycloak:26.3.2 start-dev
# then: create realm `vibe`, client `mcp-client`, roles wristband_vip/staff/general,
# client-scope `wristband` mapper → realm-export.json → commit to infra/keycloak/
docker run --rm -v $PWD/infra/keycloak:/opt/keycloak/data/import \
  quay.io/keycloak/keycloak:26.3.2 start-dev --import-realm  # offline proof it imports
```

## 4. Live demo choreography (4 min)

| Time | Action | Narration |
|---|---|---|
| 0:00–0:45 | `tools/list` with GEN token → 2 tools | "General wristband sees preview only." |
| 0:45–1:30 | Call `onboard_activate` with GEN → `403 / scope missing` | "Agent cannot bypass — enforcement is server-side." |
| 1:30–2:30 | Swap to VIP header → `tools/list` → 3 tools, call `vip_discharge` → success | "Same agent, VIP wristband, new capability — no rebuild." |
| 2:30–3:30 | `confirm=False` → abort; replay same `idempotency_key` → `already_applied` | Cite-Before-Act gate (Best Overall pattern) + idempotency |
| 3:30–4:00 | Show upgrade slide (realm JSON + 3-line diff) | "Keycloak-ready, Keycloak-optional." |

Inspector verify (no UI magic):

```bash
# list as general vs vip — diff proves filtering
mcp-inspector --cli --transport http --server-url http://localhost:8000/mcp \
  --method tools/list --header "Authorization: Bearer $GEN_TOKEN"
mcp-inspector --cli --transport http --server-url http://localhost:8000/mcp \
  --method tools/list --header "Authorization: Bearer $VIP_TOKEN"
```

## 5. Pre-demo checklist

- [ ] Tokens minted with 8 h `exp`, `aud=vibe-mcp` matches verifier
- [ ] HTTP transport (not STDIO) so `AuthMiddleware` enforces
- [ ] `.env.example` committed, real tokens only in local `.env`
- [ ] `confirm=False` / bad hash / replay-key paths rehearsed
- [ ] `infra/keycloak/realm-export.json` in repo as upgrade artefact (container NOT running)
- [ ] Fallback: `demo-fallback.mp4` shows GEN→403→VIP→200 if Wi-Fi dies

## Sources

- FastMCP AuthMiddleware / scopes: `/prefecthq/fastmcp` `fastmcp-server-middleware-authorization.mdx`, `docs/servers/authorization.mdx`, `docs/deployment/sandboxed-agents.mdx`, `docs/servers/auth/token-verification.mdx` (via Context7, 2026-11-22)
- Keycloak weight/startup: `/keycloak/keycloak` `perf_recommendations.adoc`, `changes-24_0_0.adoc`, `containers.adoc` (via Context7, 2026-11-22)
- Judge patterns: MCP.STORE Keycloak JWT + CEL "cannot bypass" — https://www.solo.io/blog/celebrating-the-winners-of-the-2026-hackathon-for-mcp-ai-agents ; Cite-Before-Act — https://gradio.app/mcp-birthday-winners ; GSA "not a thin wrapper" rubric — https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon
- Local: `research/03-synapse-technical.md` §2.3–2.4, `research/final/05-fastmcp-custom.md` §b–c, `research/build/11-lib-docker.md` (stack weight context)
