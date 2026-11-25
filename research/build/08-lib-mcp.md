# 08 — MCP Library Choice: FastMCP vs fastapi_mcp vs MCP Python SDK

> Scope: curated `@mcp.tool` vs auto-mount, auth middleware, `AuditMiddleware`, `mount`/namespace for Track 3 reuse. Primary + fallback with version pins.

## 1. Verdict

**Primary: FastMCP (`fastmcp`). Fallback: MCP Python SDK (`mcp`) directly.**
Avoid `fastapi_mcp` for anything you ship; use it at most as a throwaway bootstrap, or replace it with `FastMCP.from_fastapi()`.

| | FastMCP ✅ primary | MCP Python SDK (fallback) | fastapi_mcp ❌ not recommended |
|---|---|---|---|
| Package / version (Nov 2026) | `fastmcp==4.1.7` (26 Oct 2026; 4.1.4 checked 28 Oct) — depends on `mcp` v2 | `mcp==2.3.0` (2 Oct 2026); v1 line at `1.30.0` | `fastapi-mcp==0.4.0` (28 Jul 2025 — ~15 months stale, 90 open issues / 68 open PRs) |
| Maintainer / license | Prefect (jlowin), Apache-2.0, weekly releases | MCP project (`modelcontextprotocol`), MIT, Tier-1 official SDK | Tadata Inc., MIT, alpha on PyPI |
| Python | 3.10+ (prefer 3.11+) | 3.11+ (README; 3.10 works per guides) | 3.10+ |
| Spec | 2026-07-28 + legacy clients; optional `fastmcp-tasks` | 2026-07-28 + legacy; Tasks **not** implemented, OTel on by default | 2025-11-25 (stuck on `mcp` 1.x) |

## 2. Curated `@mcp.tool` vs auto-mount

**Our build wants curated tools — that decides it.**

- **FastMCP (curated-first, auto for bootstrap).** Hand-write `@mcp.tool` (no parens in v4); `from_fastapi(app)` / `from_openapi(spec, client)` use `OpenAPIProvider` under the hood. Official docs warn explicitly: *"LLMs achieve significantly better performance with well-designed and curated MCP servers than with auto-converted OpenAPI servers… use the FastAPI integration for bootstrapping and prototyping, not for mirroring your API."* Pattern: bootstrap with `from_fastapi`, then rebuild the tools you keep as curated `@mcp.tool`.
- **MCP Python SDK (curated-only).** `from mcp.server import MCPServer` + `@mcp.tool()`. No converter, no proxying/composition documented. Fewest moving parts; you own everything.
- **fastapi_mcp (auto-only).** `mcp = FastApiMCP(app); mcp.mount_http()` exposes **every** route as a tool via ASGI transport, preserving schemas/Swagger docs. Fast for demos, wrong for curated surface: no allow-list per-tool story, every endpoint change re-shapes the LLM tool surface.

```python
# FastMCP curated (primary pattern)
from fastmcp import FastMCP
mcp = FastMCP("Track1")
@mcp.tool
def create_ticket(title: str, severity: str = "p3") -> dict:
    """Create a ticket. Curated description beats auto-generated schema."""
    ...
```

## 3. Auth middleware

| | FastMCP | SDK | fastapi_mcp |
|---|---|---|---|
| Model | Single `auth=` provider: `JWTVerifier`, `RemoteAuthProvider`, `OAuthProxy` (bridges providers lacking DCR), `GitHub/Google/Azure/Auth0/Keycloak/WorkOS` providers, `MultiAuth`; plus `AuthMiddleware(require_scopes(...))` and custom `Middleware.on_call_tool` | Raw plumbing: `token_verifier=` + `auth_server_provider=` + `AuthSettings`; `ServerMiddleware` wraps raw JSON-RPC (one hook, untyped) | Reuses FastAPI `Depends`: `AuthConfig(dependencies=[Depends(verify_auth)])`, token passthrough via `mcp-remote --header`, OAuth flow per spec 2025-03-26 |
| Fit for us | ✅ Best: JWT/JWKS at edge (`auth=JWTVerifier(...)`) + scope middleware + custom user-inject middleware | ✅ OK if you want zero framework: implement verifier yourself | ⚠️ Only good if FastAPI already owns auth; no provider layer |

```python
# FastMCP auth (production shape)
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
verifier = JWTVerifier(jwks_uri="https://auth.example.com/.well-known/jwks.json",
    issuer="https://auth.example.com", audience="mcp-track1")
mcp = FastMCP(name="Track1", auth=verifier)
```

Custom per-request auth/context injection uses `Middleware.on_call_tool` + `get_http_request()` / `ctx.set_state("user_id", ...)` (see gelembjuk/Roman pattern). Note mount caveat below.

## 4. AuditMiddleware

- **FastMCP: first-class recipe.** Subclass `fastmcp.server.middleware.Middleware`, override `on_call_tool`, emit one redacted record per call (tool, call_id, schema_hash, redacted args, status `completed/empty/error/failed`, duration_ms). Built-ins compose by order: `ErrorHandlingMiddleware` → `RateLimitingMiddleware(token-bucket)` → `LoggingMiddleware` → custom `AuditMiddleware`. Use OTel export when the goal is spans; use `AuditMiddleware` for a self-contained redacted audit trail.
- **SDK:** hand-roll around `ServerMiddleware` (raw messages, no `ToolResult`-aware hook, no built-in rate-limit/audit).
- **fastapi_mcp:** no middleware/audit layer; rely on FastAPI middleware + access logs.

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext
class AuditMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        try:
            result = await call_next(context)
        except Exception:
            self.emit({"tool": context.message.name, "status": "failed"}); raise
        self.emit({"tool": context.message.name,
                   "status": "error" if result.is_error else "completed"})
        return result
    def emit(self, r: dict): print(r)  # swap: structured logger/queue/store
mcp.add_middleware(AuditMiddleware())
```

## 5. Mount / namespace for Track 3 reuse

**Only FastMCP does this.** `parent.mount(child, namespace="...")` is live composition (not snapshot): child's lifespan runs, child's middleware runs for its tools, parent middleware runs for **all**.

```python
from fastmcp import FastMCP
t3 = FastMCP("Track3")
t3.mount(track1_mcp, namespace="track1")  # track1_create_ticket
t3.mount(track2_mcp, namespace="track2")
# optional rename: mount(srv, namespace="t1", tool_names={"create_ticket": "open_ticket"})
```

Caveats (v3→v4): `mount(prefix=)` → `mount(namespace=)`; `import_server()` is gone (it skipped lifespan/middleware — `mount` is the replacement, not an equivalent); `FastMCP.as_proxy` → `create_proxy`. State does **not** cross mounts by default — share via common `session_state_store` or `serializable=False` request-scoped values. Serve alongside FastAPI via `mcp_app = mcp.http_app(path="/mcp"); app = FastAPI(lifespan=mcp_app.lifespan); app.mount("/analytics", mcp_app)`.

SDK has no composition; fastapi_mcp mounts **into** FastAPI (`mount_http()`/`mount_sse()`), not MCP-into-MCP namespaces.

## 6. Pins (copy/paste)

```toml
# Primary
requires-python = ">=3.11"
dependencies = ["fastmcp==4.1.7", "mcp==2.3.0", "httpx>=0.28", "uvicorn>=0.30"]
# Fallback (no framework): dependencies = ["mcp==2.3.0"]
# Throwaway bootstrap ONLY: ["fastapi-mcp==0.4.0", "mcp==1.30.0", "fastapi>=0.115"]
#   - fastapi_mcp declares mcp>=1.12 unbounded; fresh installs pull mcp 2.x and crash
#     (TypeError: Server.__init__() takes 2 positional arguments but 3 were given).
#     Pin mcp==1.30.0 if you touch it. mount() is deprecated → mount_http()/mount_sse().
```

## 7. Sources

- Context7 `prefecthq/fastmcp` + `gofastmcp`: middleware hierarchy, `mount(server, namespace, tool_names)`, `AuditMiddleware` recipe, `JWTVerifier`/`RemoteAuthProvider`/`OAuthProxy`, `from_fastapi`/`OpenAPIProvider` curation warning, `http_app` lifespan mounting, v3→v4 breaking renames.
- AgenticWire (Jul 2026, re-verified Oct 2026): fastapi_mcp 0.4.0 stale 432d, `mcp<2` pin required; FastMCP 4.0.10→4.1.x active.
- eSEOspace Oct 2026 / TrustedMCP Nov 2026 / Promptise Oct 2026: `fastmcp` 4.1.x on `mcp` 2.3.0, `MCPServer` rename, spec 2026-07-28, auth/rate-limit matrix.
