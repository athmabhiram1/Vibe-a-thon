# 06 — Synapse Edge: Synapse CLI vs fastapi_mcp vs FastMCP.from_fastapi vs Hand-written MCP SDK

> Context: our HR+IT build = Track 3 (copilot across two systems). Two Synapse Auto servers
> (HR service + IT ticketing service), one agent answering questions that need both,
> plus the live-update demo (`synapse build --discover` after adding an endpoint).
> Pins: Synapse CLI `0.1.9`, hosted runner `@2ndbrainlabs-ai/synapse-mcp 0.0.4`.
> Facts below about Synapse behavior come from the official hackathon participant guide
> (2nd Brain Labs × Geek Room Vibe-a-thon, Oct 2026); competitor facts from official docs.

## 1. One-table differentiation

| Dimension | Synapse CLI (Auto) | `fastapi_mcp` (`FastApiMCP`) | `FastMCP.from_fastapi` / `from_openapi` | Hand-written MCP SDK (`mcp` python-sdk) |
|---|---|---|---|---|
| **Detection: how it finds your API** | **Static analysis (tree-sitter)** of source: finds HTTP routes in Python, TS/TSX, Java, C#, Go, Rust without running the app. No OpenAPI needed. Plain JS (`.js/.jsx`) is NOT scanned. | **Runtime OpenAPI**: reads your live FastAPI app's `openapi.json` in-process (`FastApiMCP(app)`). App must import and run. | **Runtime OpenAPI**: `from_fastapi(app)` wraps the same OpenAPI spec via an `OpenAPIProvider`; `from_openapi(spec, client)` needs a spec dict + `httpx` client pointed at a live base URL. | **None**: you hand-write every `@mcp.tool()` with type hints; SDK generates schemas from signatures. |
| **What you write** | One CLI command: `synapse build --auto --all-endpoints`. No code edits, no imports into the app. | ~3 lines of code added to your app (`FastApiMCP(app)` + `mount()`), plus redeploy. | ~5–10 lines of glue code: build client, load spec, `FastMCP.from_fastapi(app)` / `from_openapi(...)`, `mcp.run()` or `http_app()` + mount. | A whole `server.py`: define each tool function, prompts, resources, transports by hand. |
| **Output: what runs the tools** | **Hosted runner**: no file written; client config runs `@2ndbrainlabs-ai/synapse-mcp` via npx with your `SYNAPSE_SERVER_ID` (tools proxy to your deployed API). **`--local` output**: `synapse_auto_server.py` in project root (Python projects only). | **Mount**: MCP endpoint mounted *inside* your FastAPI app (`mcp.mount()` / `mount(mcp)`), same process/port. | **Mount or standalone**: `mcp.http_app(path='/mcp')` mounted into FastAPI (must pass `lifespan`), or `mcp.run()` standalone proxying to the API over HTTP. | **Standalone file**: your `server.py` run via `uv run mcp dev` / stdio / streamable-HTTP; you own hosting. |
| **Cross-language** | 6 scanned languages; **generated server is always Python**. | Python/FastAPI only. | Python only (any OpenAPI spec as input for `from_openapi`). | Any SDK language, but all manual. |
| **Custom composition** | Custom mode (Python only): composes many functions into **one smart tool** from `--query` text → `<tool_name>_server.py`. `--smart-names` renames Auto tools from handlers+README. | No composition; 1 endpoint ≈ 1 tool (route maps can exclude/rename only). | Route maps + `route_map_fn` + `mcp_component_fn` can curate/rename, but you code the mapping. | Full control: design any tool shape, confirmations, error paths — at full manual cost. |
| **Quota / cost** | Free tier: **10 MCP servers + 100,000 indexed lines/account** (`synapse info` to check). Rebuilding unchanged repo costs nothing. `--local` builds never count against quota (uses your own model key). | No quota; cost = your hosting + (for `from_openapi` proxying) per-call latency to your API. | Same as fastapi_mcp: no quota, you host. | Same: you host, no quota. |
| **Secrets handling** | Headers emitted as `${ENV}` placeholders; tokens stay in env vars. Hosted Auto sends only endpoint names/routes/docstrings; `--smart-names`/Custom also send function details/source. `--local` keeps code on-machine. | You wire auth headers into the mounted app yourself. | You construct the `httpx.AsyncClient` (bearer headers, timeouts) yourself. | You implement auth per tool yourself. |

## 2. The `--discover` live moment (unique to Synapse)

The Track 3 judging rubric explicitly demands it: *"add a new endpoint, rebuild with
`synapse build --discover`, and show the agent using it straight away."* The sequence:

```bash
# agent already answers HR+IT questions through two hosted servers
# ... add GET /leave-balance to the HR service ...
synapse build --discover   # rescan; only changed files are parsed again
# same SYNAPSE_SERVER_ID, client config untouched — ask the new question immediately
```

Why this is the demo beat: later builds **update the same MCP server**, so the pasted client
JSON keeps working — no restart-the-app, no re-mount, no redeploy. `--discover` reuses the last
scan and re-parses only changed files, so the rescan is visibly fast on stage.

## 3. What competitors can't demo live

1. **No code-touch, no running app.** `fastapi_mcp` and `from_fastapi` both require the FastAPI
   app object at runtime (import it, mount, serve it). Synapse only needs the *source tree* —
   static detection works on a legacy app you are forbidden to modify (Track 1: "no changes to
   the original app's code"), even on a repo whose dependencies no longer install.
2. **No OpenAPI prerequisite.** Competitors die without a correct `openapi.json`
   (missing decorators, non-FastAPI framework, or a second language like Java/C# = no spec at
   all). Synapse's tree-sitter scan finds routes in 6 languages with zero annotations.
3. **Same-ID rebuild.** Competitor flow for "we added an endpoint" = edit glue code, restart the
   server, sometimes re-paste client config. Synapse keeps the server ID; the agent picks up the
   new tool with zero client-side changes.
4. **One smart tool from many functions.** Custom mode (`synapse build --custom --query "…"`)
   composes a whole workflow (create account + assign equipment + schedule orientation) into one
   agent-facing tool. The OpenAPI converters can only expose what the REST surface already has —
   one endpoint, one tool — and hand-writing that composition is the multi-hour baseline we
   compare against in Track 2.
5. **Hosted runner = nothing to host.** The demo laptop never runs a Python server for hosted
   Auto builds; npx pulls the runner and proxies to the already-deployed API. Every competitor
   column requires you to run, expose, and keep alive a server process on demo Wi-Fi.

## 4. When to admit the competitor wins (honest demo Q&A)

- App is already FastAPI + you live in Python + you want the MCP colocated with the API:
  `fastapi_mcp`'s `mount()` is simpler and quota-free.
- You need programmatic control of route→tool mapping (`RouteMap`, `route_map_fn`,
  `mcp_component_fn`, curated `x-mcp-tool` subsets): `FastMCP.from_openapi` is the scalpel.
- Maximum control / exotic transports / custom prompts & resources: hand-written SDK
  (`@mcp.tool()` + `mcp.run(transport='streamable-http')`); also the only path with zero
  dependency on any generator's output quality.
- Sensitive code you won't send anywhere and a non-Python repo: note the local-mode limit —
  local Auto on TS/Java/C#/Go/Rust names tools but writes no file; hosted build is required.

## 5. Pins & doc URLs

- Synapse CLI `0.1.9`: `https://www.npmjs.com/package/@2ndbrainlabs-ai/synapse-cli`
  (`npm install -g @2ndbrainlabs-ai/synapse-cli`, `synapse --version`)
- Hosted runner `@2ndbrainlabs-ai/synapse-mcp 0.0.4`: invoked via npx with `SYNAPSE_SERVER_ID`
  (config snippet printed by `synapse build`; never hand-write it)
- Synapse docs: getting-started + API reference + CLI README + examples + console
  (see participant guide References page; CLI source: `2ndbrainlabs-ai` GitHub org)
- `fastapi_mcp`: PyPI `https://pypi.org/project/fastapi-mcp/` ·
  GitHub `https://github.com/tadata-org/fastapi_mcp` (`FastApiMCP(app)` + `mcp.mount()`)
- FastMCP FastAPI integration: `https://gofastmcp.com/docs/integrations/fastapi`
  (`FastMCP.from_fastapi(app=app)`; mount via `mcp.http_app(path='/mcp')` + lifespan)
- FastMCP OpenAPI integration: `https://gofastmcp.com/docs/integrations/openapi`
  (`FastMCP.from_openapi(openapi_spec=spec, client=client)`; `RouteMap`/`MCPType`/route_map_fn curation)
- MCP Python SDK: `https://py.sdk.modelcontextprotocol.io/`
  (hand-written: `from mcp.server.fastmcp import FastMCP`, `@mcp.tool()`, `mcp.run()`; v2 renames to `MCPServer`)
- Model Context Protocol spec: `https://modelcontextprotocol.io/`
- FastMCP vs fastapi-mcp comparison: `https://www.agenticwire.news/article/fastmcp-vs-fastapi-mcp`
