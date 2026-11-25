# 04 — Synapse Auto Detection Guarantees (HR + IT FastAPIs)

Tech grounding for Track 1 / Track 3: how to write FastAPI routes so
`synapse build --auto` **always detects them**, and what silently drops
endpoints. Applies equally to an HR service and an IT/ticketing service.

## 1. How Synapse Auto detection works (v2 engine)

1. **Scan (local, tree-sitter).** `synapse build` detects project language
   (marker file `requirements.txt` / `pyproject.toml`, else most-common
   extension) and extracts HTTP routes **on your machine** with tree-sitter.
2. **Pick.** Auto exposes the routes you select as MCP tools that call your
   deployed API.
3. **Generate.** Hosted: endpoint config saved to your Synapse account, served
   by `@2ndbrainlabs-ai/synapse-mcp` runner via `npx` (no file written).
   `--local` on Python: writes `synapse_auto_server.py` passthrough server
   without calling a model (unless `--smart-names`).

Key consequence: **detection is static, not runtime.** If tree-sitter cannot
see a literal `@app.get("/literal-path")`, the endpoint does not exist as far
as Synapse is concerned — even if it works at runtime via `app.openapi()`.

Sources: [Synapse CLI README — Build modes / How build works](https://github.com/2ndbrainlabs-ai/synapse-cli-ts),
[Getting started docs](https://synapse.2ndbrainlabs.ai/docs),
[API reference](https://synapse.2ndbrainlabs.ai/docs/api).

## 2. CLI surface you must know

```bash
synapse init                        # one-time per project (not needed for --local)
synapse build                       # interactive: asks Auto or Custom
synapse build --auto --all-endpoints
synapse build --auto --endpoints "GET /employees,POST /employees"
synapse build --auto --endpoints "/employees,get_employee_by_id"
synapse build --discover            # rescan after code changes
synapse build --auto --server-name hr-api        # pick which server to update
synapse build --auto --server-name it-api --new  # second server in one repo
synapse build --auto --smart-names  # better tool names from handler source + README
synapse info                        # quota: 10 servers, 100k indexed lines
```

- No terminal + no `--all-endpoints`/`--endpoints` → `Endpoint Selection Required` error.
- Rebuilds update the **same server id** (`.synapse/config.json`); client config keeps working.
- `--smart-names` (Auto only) sends each selected handler's source (≤3000 chars)
  + README (≤6000 chars) to the backend/your model. Plain Auto sends only
  name, method, path, header names (`${ENV}` placeholders), example payload.

## 3. The `surface_cache.json` trap (Track 3 live-update demo)

First build saves to `.synapse/surface_cache.json`:

```
Using the endpoints discovered on Oct 30, 2026, 1:05 PM (12 endpoint(s)).
Run synapse build --discover to rescan.
```

- **Later builds reuse the cache.** Code changes are invisible until `--discover`.
- `--discover` only re-parses files whose contents changed — cheap, always run it after adding a route.
- Auto cache stores **endpoints only**; a Custom build after Auto always rescans.
- Empty result is never reused (rescans automatically).
- Missing/unreadable/foreign cache → full scan. **Deleting the file is always safe.**
- `--resume` wins over `--discover` (finishes paused scan first).

Demo script for "add endpoint live":

```bash
# terminal 1: APIs running
uvicorn hr_api:app --port 8001
uvicorn it_api:app --port 8002
# terminal 2: add route, then
synapse build --discover --auto --all-endpoints --server-name hr-api
# agent uses new tool immediately, no client-config change
```

## 4. Route patterns that GUARANTEE detection

Rule of thumb: **literal decorator + literal path + module-level `app`/`router`
+ `include_router` + unique `operation_id` + Pydantic body.**

```python
# hr_api.py — copy-paste scaffold (IT service mirrors it)
from fastapi import FastAPI, APIRouter, Depends, Header
from pydantic import BaseModel

app = FastAPI(title="HR API")

class EmployeeCreate(BaseModel):
    name: str
    email: str
    department: str | None = None

class EmployeeOut(EmployeeCreate):
    id: int

router = APIRouter(prefix="/employees", tags=["employees"])

@router.get("/", operation_id="list_employees", summary="List employees")
def list_employees() -> list[EmployeeOut]:
    """List all employees. Used by agent to find people by department."""
    ...

@router.get("/{employee_id}", operation_id="get_employee_by_id")
def get_employee_by_id(employee_id: int) -> EmployeeOut:
    """Fetch one employee by numeric id."""
    ...

@router.post("/", operation_id="create_employee", response_model=EmployeeOut)
def create_employee(payload: EmployeeCreate) -> EmployeeOut:
    """Onboard a new employee."""
    ...

# Health / root routes: put FIRST or at least explicitly; declare before
# any catch-all so static scan order matches runtime resolution.
@app.get("/health", operation_id="health_check")
def health_check() -> dict:
    """Liveness probe."""
    return {"ok": True}

app.include_router(router)
```

Checklist (all verified against FastAPI docs):

1. **Explicit decorators.** `@app.get(...)`, `@app.post(...)`,
   `@router.get(...)` with a **string-literal path**. Tree-sitter matches the
   literal; f-strings / concatenation / variables are invisible.
2. **Unique `operation_id`.** `operation_id="list_employees"` becomes the MCP
   tool name (`--endpoints` also accepts it). Auto-generated ids
   (`list_employees_employees__get`) collide across two services; set them
   explicitly and prefix per service (`hr_list_employees`, `it_list_tickets`).
   Ref: [Path-operation advanced config](https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/).
3. **Pydantic `BaseModel` body + `response_model`.** Gives Synapse a typed
   schema to marshal into tool args instead of an opaque `dict`.
4. **`APIRouter` + `app.include_router(router)`.** Routers are detected;
   keep `prefix="/employees"` literal and call `include_router` at module
   scope in the file Synapse scans.
5. **Docstring + `summary`.** `description` falls back to the docstring; it
   becomes the tool description the agent reads. Write one line per route.
   Ref: [APIRouter decorator params](https://fastapi.tiangolo.com/reference/apirouter/).
6. **Query/path params as typed function args** (`employee_id: int`,
   `department: str | None = None`). These map cleanly to tool arguments.
7. **One app per service, distinct ports/names.** HR on `:8001` /
   `--server-name hr-api`, IT on `:8002` / `--server-name it-api`. Prevents
   `operation_id` collisions and quota confusion.

## 5. Anti-patterns — detected at runtime, MISSED by Synapse

| # | Anti-pattern | Why it breaks detection / tool quality | Fix |
|---|--------------|----------------------------------------|-----|
| 1 | **Dynamic route registration** — `for r in routes: app.add_api_route(r.path, ...)` / `app.route()` factory / decorator loops | No literal decorator for tree-sitter to match; endpoint missing from picker and from `--all-endpoints` | Unroll to explicit `@app.get("/fixed-path")` per route |
| 2 | **`include_in_schema=False`** on route or router | Excluded from OpenAPI (`/docs`); Synapse follows the same surface and skips it. Ref: [include_in_schema](https://fastapi.tiangolo.com/reference/fastapi/) | Remove flag; gate visibility with auth (`Depends`), not schema exclusion |
| 3 | **Required `Header(...)` / API-key params** e.g. `x_api_key: str = Header(...)` | Hosted Auto only sends header *names* with `${ENV}` placeholders; a required secret header makes every tool call fail until the runner env is wired | Make headers optional with default, or inject via `Depends(get_api_key)` documented in README; keep real tokens in env |
| 4 | **`File(...)` / `UploadFile` / `Form(...)`** params (e.g. resume upload, avatar) | Multipart bodies don't marshal to JSON tool args; `--local` passthrough and hosted runner both mishandle them | Expose a JSON twin (`POST /resumes/metadata`) for the agent; keep the multipart route for humans, exclude it from `--endpoints` |
| 5 | **Catch-all / conflicting order** — `@app.get("/{anything}")` before specific routes | Static scan lists both; runtime shadows the specific one, agent calls the wrong tool | Declare specific routes first, catch-all last (or delete it) |
| 6 | **No `operation_id` across two services** | Both services generate `get_item`-style ids; `--endpoints get_item` becomes ambiguous, smart-names collide | Prefix every id: `hr_*`, `it_*` |
| 7 | **Routers never included** — `router = APIRouter(...)` without `app.include_router(router)` in scanned tree | Dead surface: detected but 404 at runtime; rebuild churns | `include_router` at import time in `app.py`; avoid conditional includes |
| 8 | **Plain `.js/.jsx` shims or TS-only wrappers** | Synapse does not scan `.js/.jsx` at all | Keep the FastAPI Python service as the scanned root |
| 9 | **Auth via closure / custom callable returning 401 outside `Depends`** | Signature looks arg-less; generated tool omits credentials and always 401s | Use standard `Depends(oauth2_scheme)` / `Depends(get_current_user)` so headers/params are visible |
| 10 | **Stale cache demos** — adding a route then rebuilding without `--discover` | New endpoint silently absent; looks like a detection bug | Always `synapse build --discover` after edits (Track 3 requirement) |

## 6. Minimal HR + IT pair (Track 3 ready)

```
track3/
  hr_api.py      # FastAPI app "HR API",  :8001, operation_ids hr_*
  it_api.py      # FastAPI app "IT API",  :8002, operation_ids it_*
  requirements.txt  # fastapi, uvicorn, pydantic
```

```bash
cd track3 && synapse init
synapse build --auto --all-endpoints --server-name hr-api
synapse build --auto --all-endpoints --server-name it-api --new
# cross-system questions: "who owns laptop X and are they on leave?"
# live update: add GET /leave-balances, then:
synapse build --discover --auto --all-endpoints --server-name hr-api
```

Verify before building:

```bash
python -c "import hr_api, it_api; print(len(hr_api.app.routes), len(it_api.app.routes))"
curl -s localhost:8001/openapi.json | python -c "import json,sys; print(sorted(set(o.get('operationId','') for o in __import__('itertools').chain(*[m.values() for m in json.load(sys.stdin)['paths'].values()]))))"
```

Every `operationId` printed here should appear in the Synapse endpoint picker;
any gap means one of the anti-patterns above.

## Doc URLs

- FastAPI — custom `operation_id`: https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/
- FastAPI — `APIRouter` decorator params (`tags`, `summary`, `description`, `operation_id`, `include_in_schema`): https://fastapi.tiangolo.com/reference/apirouter/
- FastAPI — `include_in_schema`: https://fastapi.tiangolo.com/reference/fastapi/
- FastAPI — Header param models: https://fastapi.tiangolo.com/tutorial/header-param-models/
- FastAPI — Form models + file uploads: https://fastapi.tiangolo.com/tutorial/request-form-models/
- Synapse CLI (flags, cache, rebuild, `--server-name`, `--discover`, `--resume`): https://github.com/2ndbrainlabs-ai/synapse-cli-ts
- Synapse getting started: https://synapse.2ndbrainlabs.ai/docs
- Synapse API reference: https://synapse.2ndbrainlabs.ai/docs/api
- Synapse examples: https://github.com/2ndbrainlabs-ai/synapse-examples
- MCP standard: https://modelcontextprotocol.io
