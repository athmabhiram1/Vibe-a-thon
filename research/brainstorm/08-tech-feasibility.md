# 08 — Technical Feasibility: Python FastAPI + Synapse + MCP Client

Date: 2026-11-22 | Stack: FastAPI + `fastapi-mcp`/`FastMCP` (Synapse-style auto-server) + MCP client + Ollama local

## 1. TL;DR — What Always Works

- Use explicit `@app.get/post/put/delete(path, operation_id="...", description="...")` + Pydantic models + scalar query/path params. Both `fastapi-mcp` and `FastMCP.from_fastapi()` read the **OpenAPI schema**, not the decorator source — if it shows cleanly in `/openapi.json` + Swagger, it becomes a tool.
- Minimal scaffold = `FastAPI(title, description)` + 1 GET + 1 POST + `FastApiMCP(app); mcp.mount_http()` **or** `FastMCP.from_fastapi(app=app); mcp.run()`. Pick **one** adapter, pin versions.
- `--local` (Ollama `qwen2.5-coder:7b`, 4.7 GB, 32K ctx) = free/offline, good for scaffolds + single-function fixes. Hosted frontier model = needed for multi-file refactors, long-context (>32K), reliable tool-calling.
- Biggest risks: (a) `fastapi-mcp` stale (last push Nov 2025, slow Streamable-HTTP uptake), (b) auto-converted REST → MCP gives bloated/poor tool UX (both vendors warn), (c) Ollama default ctx is only **4K on <24 GiB VRAM** — must raise to 16–64K, (d) Node 20 + Python 3.10+ + `uv` mismatch breaks Claude Desktop stdio launch.

## 2. Route Patterns That Guarantee Detection

Both adapters derive tools from `app.openapi()`. Rules distilled from docs + GitHub examples:

### 2.1 DO (detected 100%)
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Demo API", description="Brainstorm demo", version="0.1.0")

class Item(BaseModel):
    name: str
    description: str | None = None

@app.get("/items/", operation_id="list_items", description="List all items")
async def list_items() -> list[Item]:
    return []

@app.post("/items/", operation_id="create_item", description="Create an item")
async def create_item(item: Item) -> Item:
    return item

@app.get("/users/{user_id}", operation_id="get_user_info", description="Get user by ID")
async def read_user(user_id: int):
    return {"user_id": user_id}
```
Why this works:
- `operation_id="snake_case"` → becomes MCP **tool name**. Without it FastAPI auto-generates `read_user_users__user_id__get` (cryptic, LLM-unfriendly). Source: `tadata-org/fastapi_mcp` README + `fastapi_mcp/server.py`.
- Docstring or `description=` → becomes tool description (preserved verbatim in Swagger → MCP).
- Pydantic `BaseModel` body + scalar `int/str/bool` path/query params → clean JSON Schema. `response_model=` optional but improves filtering.
- `APIRouter` + `app.include_router(router)` also detected **if included before** `FastApiMCP(app)` / `from_fastapi(app=app)` construction. Order matters: build all routes first, then wrap, then `mount_http()`.

### 2.2 AVOID (silently dropped or mangled)
| Pattern | Outcome |
|---|---|
| No `operation_id`, long nested paths | Auto-ID, usable but ugly; rename |
| `UploadFile` / `File()` / `Form()` bodies | No JSON channel in MCP (SEP-2631 draft); route stays HTTP-only |
| Required `Header()` / `Cookie()` params | Not mapped to GraphQL/tool args; make optional, pass via `headers=["authorization"]` or `passthrough_headers` |
| Query-model mixed with plain params (`model: MyQuery = Query()` + `q: str`) | FastAPI itself can't serve cleanly; fold into one model |
| `include_in_schema=False` routes | Invisible to OpenAPI → invisible to MCP |
| Routes added **after** `FastApiMCP(app)` | Missing until `mcp.setup_server()` re-called (fastapi-mcp) |
| Duplicate `operation_id` | Collision; second tool shadows first |

Refs:
- https://github.com/tadata-org/fastapi_mcp (README: Tool Naming, `mount_http`)
- https://gofastmcp.com/docs/integrations/fastapi (from_fastapi + mount)
- https://fastapi.tiangolo.com/reference/fastapi/ (`@app.get/post` params)

## 3. Minimal FastAPI Scaffold (Copy-Paste, Always Works)

### Option A — `fastapi-mcp` (mount inside existing app; best when you already have FastAPI)
```python
# main.py
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel

app = FastAPI(title="Brainstorm API", description="Demo", version="0.1.0")

class Echo(BaseModel):
    text: str

@app.get("/ping", operation_id="ping", description="Health check")
async def ping():
    return {"ok": True}

@app.post("/echo", operation_id="echo_text", description="Echo text back")
async def echo(body: Echo) -> Echo:
    return body

mcp = FastApiMCP(
    app,
    name="Brainstorm MCP",
    description="Demo MCP over FastAPI",
    # include_operations=["ping","echo_text"],  # allowlist when ready
    # exclude_operations=[...], exclude_tags=[...], describe_all_responses=False
)
mcp.mount_http()  # -> /mcp (Streamable HTTP). Old: mcp.mount(mount_path="/sse")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# run: python main.py  -> REST at :8000/docs, MCP at :8000/mcp
```
Pin: `pip install "fastapi-mcp>=0.4.0" "mcp==1.30.0"` (v0.4.0 adds Streamable HTTP; `mount()` deprecated → `mount_http()`/`mount_sse()`).

### Option B — `FastMCP` (curated companion server; best for new/AI-native surface)
```python
# server.py
from fastmcp import FastMCP

mcp = FastMCP(name="Brainstorm Tools")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@mcp.resource("resource://config")
def get_config() -> dict:
    """App config."""
    return {"version": "1.0"}

if __name__ == "__main__":
    mcp.run()  # stdio by default; use run(transport="http") for HTTP
```
Convert existing app in one line:
```python
from fastmcp import FastMCP
mcp = FastMCP.from_fastapi(app=app)
mcp.run()
```
Mount into FastAPI:
```python
mcp_app = mcp.http_app()
app.mount("/analytics", mcp_app)  # -> /analytics/mcp
```
Refs: https://github.com/prefecthq/fastmcp/blob/main/docs/tutorials/create-mcp-server.mdx, https://gofastmcp.com/docs/integrations/fastapi

### `synapse_auto_server.py` shape (project-local, no public package found)
`gh_grep "synapse_auto_server.py"` = 0 hits → treat as **our own convention file**, not a library. Recommended shape:
```python
# synapse_auto_server.py — single entrypoint, either adapter behind a flag
import argparse
from main import app  # all routes defined + included first

def build(adapter: str):
    if adapter == "fastapi-mcp":
        from fastapi_mcp import FastApiMCP
        mcp = FastApiMCP(app, name="Synapse Auto", base_url="http://localhost:8000")
        mcp.mount_http()
        return app
    else:  # fastmcp
        from fastmcp import FastMCP
        return FastMCP.from_fastapi(app=app)

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--adapter", default="fastapi-mcp")
    p.add_argument("--local", action="store_true", help="offline hint: no cloud calls")
    args = p.parse_args()
    # --local does NOT change server code; it tells the client/agent to use Ollama only
```
Document the flag in README so `--local` is a **client policy**, not a server branch.

## 4. fastapi_mcp vs FastMCP vs "Synapse" — Decision Table

| Criterion | `fastapi-mcp` (tadata-org, MIT, ★12k, stale ~Nov 2025) | `FastMCP` (Prefect, Apache-2.0, ★28k, active, ~1M dl/day) |
|---|---|---|
| Mental model | **Adapter**: `FastApiMCP(app)` + `mount_http()` keeps same ASGI app, reuses FastAPI DI/auth | **Framework**: `@mcp.tool` curated, or `from_fastapi(app)` converter (separate server) |
| Tool naming | `operation_id` auto-derived | You name functions explicitly |
| Auth | Reuses FastAPI `Depends()`; OAuth 2.1 since v0.3.1, no provider layer | `OAuthProxy` + GitHub/Google/Azure providers, CIMD, PKCE (v2.12+/v3.0) |
| Transport | `mount_http()` (Streamable HTTP, v0.4.0+), legacy SSE | stdio + SSE + Streamable HTTP; `http_app()` mount |
| Best for | Existing FastAPI monolith → expose same routes to agents fast | New service, curated few-tools UX, production auth |
| Warning | Both vendors: auto-converted OpenAPI servers underperform curated tools for complex APIs |

Rule: prototype with either; **ship curated `FastMCP` tools** for >10 routes or agent-facing prod. See:
- https://www.agenticwire.news/article/fastmcp-vs-fastapi-mcp
- https://agentindex.app/en/compare/prefecthq-fastmcp-vs-tadata-org-fastapi-mcp
- https://gofastmcp.com/docs/integrations/openapi (TIP box on curation)

## 5. MCP Client Config (Claude Desktop / Cursor) — Copy-Paste

Stdio (local script, `uv`-pinned — avoids PATH issues):
```json
{
  "mcpServers": {
    "brainstorm": {
      "command": "uv",
      "args": ["run", "--with", "fastmcp", "fastmcp", "run", "C:/path/to/server.py"],
      "env": { "API_KEY": "value-if-needed" }
    }
  }
}
```
Plain python variant:
```json
{ "mcpServers": { "dice-roller": { "command": "python", "args": ["path/to/server.py"] } } }
```
Notes: Claude Desktop runs isolated (no shell env) → must pass `env` explicitly; use absolute `uv` path on macOS (`brew install uv`); restart app, look for 🔨 hammer icon. `fastmcp install mcp-json server.py [--copy]` generates this JSON. Cursor accepts same `mcpServers` shape (`.cursor/mcp.json` or settings).

Refs: https://gofastmcp.com/integrations/claude-desktop, https://gofastmcp.com/cli/install-mcp

## 6. `--local` vs Hosted Decision Tree

```
Need offline / zero-cost / private repo?
├─ YES → --local (Ollama)
│   ├─ VRAM ≥16 GB? → qwen2.5-coder:7b (4.7 GB, 32K) chat + qwen2.5-coder:1.5b (1 GB) autocomplete
│   ├─ VRAM ≥24-32 GB? → qwen3-coder:30b (19 GB, 256K max) for agents + 1.5b tab-complete
│   └─ MUST set num_ctx ≥16-64K via Modelfile (default 4K on <24 GiB VRAM!) + verify `ollama ps`
└─ NO (hosted allowed) → frontier cloud model
    ├─ Multi-file refactor / >32K repo slice / flaky tool-calling? → hosted (GPT-4o-class, Claude)
    └─ Simple scaffold already proven locally? → stay local, save quota
Hybrid (recommended): local 7b drafts scaffolds → hosted reviews/merges hard parts.
```

Ollama hard limits (checked Oct–Nov 2026):
- `qwen2.5-coder`: 0.5b(398 MB)/1.5b/3b/7b(4.7 GB)/14b(9 GB)/32b(20 GB), all **32K ctx**, Apache-2.0, 128K only on full-precision HF weights (YaRN). Good single-function edits, weak multi-file agents.
- `qwen3-coder:30b` (19 GB, 256K max, tool-calling listed) needs ~32 GB machine; `gpt-oss:20b` ~14 GB/128K fits tight-16 GB.
- Throughput killer: CPU offload (PROCESSOR ≠ 100% GPU) → 10× slower; KV-cache for 32-64K ctx adds GBs on top of weights.
- Set ctx: `Modelfile: FROM qwen2.5-coder:7b` + `PARAMETER num_ctx 8192` → `ollama create my-7b-8k -f Modelfile`, or `OLLAMA_CONTEXT_LENGTH=64000 ollama serve` / `/set parameter num_ctx 64000`.
- Cloud tags (`*:cloud`) + `OLLAMA_NO_CLOUD=1` guard: local = no exfil; cloud = billed + sent.

Refs: https://ollama.com/library/qwen2.5-coder, https://docs.ollama.com/context-length, https://github.com/ollama/ollama/blob/main/docs/faq.mdx

## 7. Quota / Offline Risks

1. **Stale adapter**: `fastapi-mcp` idle 12 mo → pin + test `mount_http()` on Streamable HTTP; fallback to `FastMCP.from_fastapi`.
2. **Tool-bloat**: 1-tool-per-route → agent confusion; mitigate with `include_operations/include_tags` allowlist, then curate to ≤10 high-value tools.
3. **Context overflow**: default 4K truncates repo + tool defs → silent bad patches; always set + verify `ollama ps` CONTEXT.
4. **Hosted quota**: long-context agent loops burn tokens fast; use local for loops, hosted for final pass; set `num_predict`/max-tokens caps.
5. **Offline breakage**: hosted model, `uv --with` fetch, or `*:cloud` tag fails offline → pre-pull models, vendor `uv.lock`, set `OLLAMA_NO_CLOUD=1` in drills.
6. **Auth leak**: `.well-known/mcp/server-card.json` + CORS `*` exposes catalog; require token + narrow CORS in prod.

## 8. Node 20 + Python Env Checklist

```bash
node --version   # want v20.x LTS
python --version # want 3.10+ (3.11/3.12 ideal; fastapi-gql-mcp requires >=3.10)
uv --version     # installer/runner for both adapters; brew install uv (macOS) so GUI apps see it
ollama --version && ollama list && ollama ps  # models pre-pulled, ctx verified
pip install "fastapi>=0.110" "uvicorn[standard]" "pydantic>=2" "httpx"
# pick ONE primary, keep other for fallback:
pip install "fastmcp>=4.1"            # active, recommended
pip install "fastapi-mcp>=0.4.0"      # if wrapping existing app
# verify
python -c "import fastapi, fastmcp; print('ok')"
uvicorn main:app --reload  # :8000/docs must render before MCP wrap
npx mcp-remote --help      # optional smoke-test client for /mcp Streamable HTTP
```
Windows notes (this repo): use absolute paths in `claude_desktop_config.json`, quote spaces; prefer `uv` over `python` command to dodge venv/PATH isolation; keep `server.py` + `Modelfile` in repo root.

## 9. Doc URLs (primary)

- FastAPI decorators: https://fastapi.tiangolo.com/reference/fastapi/ · https://fastapi.tiangolo.com/reference/apirouter/
- FastMCP server/tools: https://github.com/prefecthq/fastmcp/blob/main/docs/tutorials/create-mcp-server.mdx · https://gofastmcp.com/docs/integrations/fastapi
- fastapi-mcp usage: https://github.com/tadata-org/fastapi_mcp · https://github.com/new-gen-ai/fastapi_mcp · https://the docs.io/fastapi_mcp/quick_start (thedocs.io mirror)
- Comparisons: https://www.agenticwire.news/article/fastmcp-vs-fastapi-mcp · https://agentindex.app/en/compare/prefecthq-fastmcp-vs-tadata-org-fastapi-mcp · https://www.pyblog.in/programming/python/connect-fastapi-to-mcp-two-integration-patterns
- MCP clients: https://gofastmcp.com/integrations/claude-desktop · https://gofastmcp.com/cli/install-mcp
- Ollama ctx/limits: https://docs.ollama.com/context-length · https://ollama.com/library/qwen2.5-coder · https://github.com/ollama/ollama/blob/main/docs/faq.mdx
