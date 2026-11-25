# 02 — MCP Adapter: Kill FastMCP 4.1.7?

**Question:** For our 11-tool HR+IT surface, should FastMCP 4.1.7 remain the primary pick vs (a) `fastapi_mcp`, (b) official MCP Python SDK hand-written, (c) generic FastAPI→MCP gateway?

**Verdict: FAIL TO KILL — keep FastMCP as primary. Reject `fastapi_mcp` as primary (stale). Use official SDK only as transport underneath; do NOT auto-generate all routes — hand-curate 11 tools.**

## 1. Options compared

| # | Option | What it is |
|---|--------|------------|
| A | **FastMCP 4.x** (`PrefectHQ/fastmcp`) | High-level MCP framework. `@mcp.tool`, `FastMCP.from_fastapi` / `from_openapi`, `mount`, `AuthMiddleware`, `http_app()` |
| B | **`fastapi_mcp`** (`tadata-org/fastapi_mcp`) | Zero-config wrapper: `FastApiMCP(app)` → converts FastAPI `operation_id`s to MCP tools, `mount_http()` |
| C | **Official MCP Python SDK hand-written** (`modelcontextprotocol/python-sdk`, `mcp` on PyPI) | Low-level `Server` / `MCPServer` + `streamable_http_app()` Starlette app mounted in FastAPI; every `list_tools`/`call_tool` hand-coded |
| D | **Generic FastAPI→MCP gateway** (auto `from_fastapi`/`from_openapi` with no curation) | Pattern, not a package: expose every route as a tool |

## 2. Tool-naming control (11 stable names matter)

- **FastMCP: full control.** `@mcp.tool(name=...)` explicit override; `FastMCP.from_fastapi(..., mcp_names={...})` rename map; `ToolTransform({old: ToolTransformConfig(name="short")})`; server-level `include_tags`/`exclude_tags`, `on_duplicate_tools="error"`; duplicate detection (`on_duplicate_tools` error/warn/replace). Docs: `@tool Decorator Arguments — name: Sets the explicit tool name exposed via MCP` (gofastmcp.com/docs/servers/tools).
- **`fastapi_mcp`: weak, derived.** "Tool Naming. FastAPI-MCP uses the `operation_id` from your FastAPI routes as the MCP tool names" (pypi.org/project/fastapi-mcp/0.3.0). Auto-generated IDs contain hyphens / start with numbers → "Tool naming rules cause issues" (augmentcode.com/mcp/fastapi-mcp). Renaming means renaming your REST API — unacceptable for HR+IT stability.
- **SDK hand-written: total control, total boilerplate.** You set every name in `on_list_tools`/`on_call_tool` handlers, but you also hand-write schemas, validation, serialization. No `mcp_names` / transform helpers.
- **Gateway (auto): worst.** Plain-English benchmark on identical 8-function set: FastMCP 937 tokens vs SDK 1,129 vs fastapi_mcp 1,724 tokens schemas; "fastapi-mcp sends 34% fewer bytes … and costs 84% more tokens" (python.plainenglish.io). Auto-exposure bloats context for 11 tools.

**Winner: A (FastMCP curated) ≈ C (manual) > B/D.**

## 3. Curated allowlist (must expose exactly 11, hide admin/internal)

- **FastMCP:** `include_tags`/`exclude_tags` on constructor; `route_maps=[RouteMap(tags={"admin"}, mcp_type=MCPType.EXCLUDE), RouteMap(methods=["DELETE"], mcp_type=MCPType.EXCLUDE), RouteMap(mcp_type=MCPType.EXCLUDE)]` catch-all; `route_map_fn` + `mcp_component_fn` for `x-mcp-tool` flag pattern; `tags_example.py` shows `from_fastapi(route_maps=[...])` (gh_grep: `PrefectHQ/fastmcp/examples/tags_example.py:50`, `langflow-ai/openrag/src/mcp_http/server.py:245`). Known footgun tracked: "route_maps ignored – every FastAPI route exposed" Issue #548 — mitigation is explicit `EXCLUDE` catch-all + test `list_tools()` count == 11.
- **`fastapi_mcp`:** `include_operations=[...]` / `exclude_operations=[...]`, `include_tags`/`exclude_tags` — but "You cannot use both include_operations and exclude_operations at the same time" (mcpservers.org/servers/.../fastapi-mcp). Coarse; no per-tool description rewrite / annotation control.
- **SDK hand-written:** allowlist is inherent (only register 11). Best guarantee, highest maintenance cost.
- **Recommendation for 11 tools:** do NOT use `from_fastapi` auto-mount as the contract. Write 11 explicit `@mcp.tool(name="hr_...")` wrappers calling service functions. Use `from_fastapi` only for prototyping.

## 4. Auth middleware

- **FastMCP:** first-class. `AuthMiddleware(auth=require_scopes("api"))`, per-tool `auth=require_scopes(...)` / `require_roles(...)` / custom `AuthCheck(ctx)`, `get_access_token()` inside tools; enterprise providers (GitHub, Google, Azure, Auth0, WorkOS); parent middleware runs for mounted children (context7 `/prefecthq/fastmcp` → `docs/servers/middleware.mdx`). Correct layer for HR PII gating.
- **`fastapi_mcp`:** markets "with Auth!" but inherits FastAPI deps opaquely; no per-tool scope model documented to same depth; stale (see §6) so auth bugs won't be patched.
- **SDK:** DIY Starlette middleware + manual token checks per handler (StackOverflow pattern uses global `auth_token` + `require_auth()` inside each tool — error-prone).
- **Gateway:** no opinion; you bolt it on.

**Winner: A.**

## 5. Mount namespaces (hr_* vs it_* collision avoidance)

- **FastMCP:** `main.mount(weather, namespace="weather")` → `weather_get_data`; `mount(server, namespace, tool_names={orig: custom})`; `Namespace("api")` transform; `on_duplicate_*` policies; dynamic composition (child tools added later visible). Verified via context7 `/prefecthq/fastmcp`: `mount` APIDOC + `docs/servers/transforms/namespace.mdx`. `prefix=` → `namespace=` rename in v4 (must use `namespace=`).
- **SDK:** `api.mount("/math", fm_math.streamable_http_app())` works but lifespan composition requires `AsyncExitStack` + `session_manager.run()` merging; open issues #713 (multi streamable-http lifespan), #1367 (mount on FastAPI broken), #951 (redirect/404 on mounted path). Avoid for HR+IT.
- **`fastapi_mcp`:** `mcp.mount_http()` — single namespace, no transform chain.

**Winner: A.**

## 6. Maintenance / stars / downloads (as of Nov 2026)

| Signal | FastMCP (A) | fastapi_mcp (B) | Official SDK `mcp` (C) |
|--------|-------------|-----------------|------------------------|
| Repo | `PrefectHQ/fastmcp`, commit 9h ago Nov 21 2026 (v4.2.4 "Burn After Reading") | `tadata-org/fastapi_mcp`, **last commit Aug 10 2025, last release v0.4.0 Jul 28 2025** | `modelcontextprotocol/python-sdk`, active (asgi.md updated Sep 5 2026, v2.3.0) |
| Stars | **~28.7k** (gofastmcp.com) | **~12k** (star-history #4559) | high (official; exact count varies by mirror) |
| Downloads | `fastmcp` **~53.7M/mo, ~13.5M/wk, ~2.5M/day** (pypistats); latest 4.2.4 Nov 21 2026 | negligible vs above; no release in **~480 days** → stale per AgenticWire "432 days since Jul 28 2025" | `mcp` **~235M/mo, ~79M/wk** (pypistats, v2.3.0) — transitively pulled by many frameworks |
| Streamable HTTP | `mcp.run(transport="http")`, `mcp.http_app(path="/mcp")` combinable with FastAPI routes; `create_streamable_http_app(..., stateless_http, json_response)` | **v0.4.0 added Streamable HTTP** (Jul 28 2025 changelog) — then stalled; SSE legacy path deprecated upstream | `mcp.streamable_http_app()` / `server.streamable_http_app()` Starlette app; `Mount`/`Host` documented in `docs/run/asgi.md` |

**Kill assessment:** the "fastapi_mcp stale Nov 2025?" claim is **confirmed and understated** — stale since Jul–Aug 2025. Do not make it the primary. FastMCP 4.1.7 specifically: superseded by 4.2.x within days; pin `fastmcp>=4.1,<5` (or `==4.2.*` after verifying `mount(namespace=)`, `ToolTransform`, `AuthMiddleware` imports) rather than `==4.1.7`.

## 7. Streamable HTTP + FastAPI coexistence

- Preferred (FastMCP docs `/integrations/fastapi`): `mcp = FastMCP.from_fastapi(app)` for discovery, then `mcp_app = mcp.http_app(path="/mcp")` + `FastAPI(routes=[*mcp_app.routes, *app.routes], lifespan=mcp_app.lifespan)`. Both REST (`/products`) and MCP (`/mcp`) on one port.
- SDK-only: `Mount("/", streamable_http_app())` + manual lifespan wiring — documented but fragile (see issues above).
- `fastapi_mcp`: `FastApiMCP(app); mcp.mount_http()` — simplest, but you inherit staleness + naming weakness.

## 8. Decision

- **Primary: FastMCP 4.x (not pinned to 4.1.7), hand-curated 11 `@mcp.tool`s** with explicit `name=`, `hr_`/`it_` namespaces via `mount(namespace=)` or name prefixes, `AuthMiddleware(require_scopes(...))`, `on_duplicate_tools="error"`, `http_app(path="/mcp")` mounted in existing FastAPI. Add a CI test asserting `len(await client.list_tools()) == 11` and exact name set (guards against Issue-#548-style over-exposure).
- **Rejected as primary:** `fastapi_mcp` (stale ~16 months, weak naming, coarse allowlist, token-bloat). Acceptable only as throwaway prototype.
- **Rejected as primary:** pure SDK hand-roll (max control, but rewrites what FastMCP already gives: schema gen, validation, auth, mounts, Streamable HTTP). Revisit only if FastMCP churn (v2→v3→v4 renames: `FastMCP→MCPServer` in SDK v2, `prefix→namespace`, `import_server→mount`) becomes a burden.
- **Rejected:** uncurated gateway (expose-everything). Violates least-privilege for HR data.

## Sources

- websearch: gofastmcp docs (tools, authorization, composition, namespace, fastapi/openapi integrations, upgrading v2→v4), PyPI `fastmcp` 4.2.4 / pypistats (53.7M/mo), PyPI `mcp` 2.3.0 / pypistats (235M/mo), `tadata-org/fastapi_mcp` (last commit Aug 10 2025, v0.4.0 Jul 28 2025), fastapi-mcp.tadata.com customization, `modelcontextprotocol/python-sdk` docs/run/asgi.md + issues #713/#951/#1367, plainenglish token benchmark, AgenticWire maintenance note, PrefectHQ/fastmcp (28.7k stars, Nov 21 2026 commits).
- context7 (`/prefecthq/fastmcp`, 8349 snippets): `mount(server, namespace, tool_names)`, `Namespace` transform, `AuthMiddleware` parent/child semantics.
- gh_grep `FastMCP.from_fastapi` (Python): `PrefectHQ/fastmcp/examples/tags_example.py:50`, `OpenBB-finance/OpenBB/.../test_skills.py`, `langflow-ai/openrag/src/mcp_http/server.py:245` — confirms `route_maps` + `RouteMap` curated pattern in the wild.
