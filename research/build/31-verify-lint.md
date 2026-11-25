# 31 — Verify Lint: Stop Endpoint Hallucinations

> Gate that fails CI when the API surface drifts from what MCP / OpenAPI clients can see. Run after `20-step-clients` and before deploy.

## 0. Why this exists

LLM-generated FastAPI code hallucinates endpoints in 6 repeatable ways:

| Hallucination | Symptom |
|---|---|
| Dynamic route loops (`for p in paths: app.get(p)`) | Routes invisible to static analysis, missing from OpenAPI |
| Duplicate / missing `operation_id` | MCP tool names collide, clients overwrite each other |
| Router added after MCP wrap | Endpoints live but not exposed as tools |
| `include_in_schema=False` on real endpoints | Works in curl, missing from OpenAPI/MCP |
| Required `Header` / `File` / `Form` params | Breaks JSON-only MCP transport |
| Catch-all mounted first | Swallows every route below it |

This lint makes all six a hard CI failure.

## 1. The lint script

Save as `scripts/lint_endpoints.py`. Zero third-party deps — stdlib `ast` only, so it runs in any CI image.

```python
"""Fail if FastAPI surface is un-scannable by MCP/OpenAPI clients."""
import ast
import re
import sys
from pathlib import Path

APP_FILES = [Path("app/main.py"), Path("app/app.py"), Path("src/main.py")]
ROUTER_GLOB = "app/**/*.py"
OP_ID_RE = re.compile(r"^(hr|it)_[a-z0-9_]+$")
FAILURES: list[str] = []

def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"FAIL: {msg}")

def find_app_file() -> Path | None:
    for p in APP_FILES:
        if p.exists():
            return p
    # fallback: first file containing FastAPI(
    for p in Path(".").rglob("*.py"):
        if "test" in p.parts or ".venv" in p.parts:
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "FastAPI":
                return p
    return None

def check_literal_decorators(tree: ast.AST, fname: str) -> None:
    """Rule 1: only literal @app.get('/path') / @app.post(...) — no loops, no variables."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While, ast.ListComp, ast.DictComp)):
            src = ast.dump(node)[:200]
            if any(k in src for k in ("route", "add_api_route", "get", "post", "put", "delete", "path")):
                fail(f"{fname}:{node.lineno} dynamic route registration inside loop/comprehension — use literal decorators")
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in ("get", "post", "put", "patch", "delete", "add_api_route"):
                recv = getattr(func.value, "id", "") or getattr(func.value, "attr", "")
                if recv in ("app", "router"):
                    if node.args:
                        first = node.args[0]
                        if not (isinstance(first, ast.Constant) and isinstance(first.value, str) and first.value.startswith("/")):
                            fail(f"{fname}:{node.lineno} non-literal route path — must be a string literal starting with '/'")

def check_operation_ids(tree: ast.AST, fname: str, seen: dict[str, str]) -> None:
    """Rule 2: unique operation_id matching hr_*/it_*."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                op_id = None
                for kw in dec.keywords:
                    if kw.arg == "operation_id":
                        if isinstance(kw.value, ast.Constant):
                            op_id = kw.value.value
                        else:
                            fail(f"{fname}:{node.lineno} {node.name} operation_id must be a string literal")
                if op_id is not None:
                    loc = f"{fname}:{node.lineno} {node.name}"
                    if not OP_ID_RE.match(str(op_id)):
                        fail(f"{loc} operation_id='{op_id}' must match ^(hr|it)_[a-z0-9_]+$")
                    if op_id in seen:
                        fail(f"{loc} duplicate operation_id='{op_id}' (first seen at {seen[op_id]})")
                    else:
                        seen[op_id] = loc

def check_schema_and_params(tree: ast.AST, fname: str) -> None:
    """Rules 3-4: no include_in_schema=False, no required Header/File/Form."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    for kw in dec.keywords:
                        if kw.arg == "include_in_schema" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                            fail(f"{fname}:{node.lineno} {node.name} has include_in_schema=False — hidden from OpenAPI/MCP")
            for arg in node.args.args + node.args.kwonlyargs:
                ann = ast.unparse(arg.annotation) if arg.annotation else ""
                has_default = True  # kwonly without default = required
                # positional check
                idx = node.args.args.index(arg) if arg in node.args.args else -1
                if idx >= 0:
                    n_defaults = len(node.args.defaults)
                    n_args = len(node.args.args)
                    has_default = (idx >= n_args - n_defaults)
                else:
                    has_default = arg.arg in [a.arg for a in node.args.kwonlyargs][
                        : len(node.args.kw_defaults)] and \
                        node.args.kw_defaults[[a.arg for a in node.args.kwonlyargs].index(arg.arg)] is not None
                for banned in ("Header", "File", "Form"):
                    if banned in ann and not has_default:
                        fail(f"{fname}:{node.lineno} {node.name} required {banned}(...) param '{arg.arg}' breaks JSON-only MCP transport — give a default or move to Body")

def check_router_before_mcp(app_path: Path) -> int:
    """Rule 5: all include_router() calls must precede MCP/Tool wrap."""
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    last_include = -1
    first_wrap = 10**9
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", "") or getattr(node.func, "id", "")
            if name == "include_router":
                last_include = max(last_include, node.lineno)
            if name in ("mount", "Mount", "Tool", "create_mcp_server", "MCPServer", "serve"):
                first_wrap = min(first_wrap, getattr(node, "lineno", first_wrap))
    # heuristic: any assignment from FastMCP / mcp / tools import counts as wrap
    src_lines = app_path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(src_lines, 1):
        if re.search(r"(FastMCP|mcp.*=|MCP.*app|serve\(app)", line):
            first_wrap = min(first_wrap, i)
    if last_include > 0 and first_wrap < 10**9 and last_include > first_wrap:
        fail(f"{app_path}:{last_include} include_router() after MCP wrap (line {first_wrap}) — routers must be included BEFORE wrap")
        return 1
    return 0

def check_catchall_last(app_path: Path) -> None:
    """Rule 6: catch-all / full-path route must be registered last."""
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    route_lines: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") in ("get", "post", "put", "patch", "delete", "route", "add_api_route"):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                route_lines.append((node.lineno, node.args[0].value))
    route_lines.sort()
    for i, (ln, path) in enumerate(route_lines):
        is_catchall = "{path" in path or "{full" in path or path in ("/{rest:path}", "/{full_path:path}")
        if is_catchall and i != len(route_lines) - 1:
            fail(f"{app_path}:{ln} catch-all '{path}' is not last — it swallows routes below it")

def main() -> int:
    seen: dict[str, str] = {}
    py_files = list(Path(".").glob("app/*.py")) + list(Path(".").glob("src/*.py"))
    if not py_files:
        py_files = [p for p in Path(".").rglob("*.py") if ".venv" not in p.parts][:50]
    for f in py_files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except Exception as e:
            fail(f"{f} unparseable: {e}")
            continue
        check_literal_decorators(tree, str(f))
        check_operation_ids(tree, str(f), seen)
        check_schema_and_params(tree, str(f))
    app_file = find_app_file()
    if app_file is None:
        fail("no FastAPI() app file found (checked app/main.py, src/main.py)")
    else:
        print(f"app file: {app_file}")
        check_router_before_mcp(app_file)
        check_catchall_last(app_file)
    print(f"\n{len(FAILURES)} failure(s).")
    return 1 if FAILURES else 0

if __name__ == "__main__":
    sys.exit(main())
```

Run locally:

```bash
python scripts/lint_endpoints.py
```

Expected clean output:

```text
app file: app/main.py

0 failure(s).
```

## 2. CI gate

`.github/workflows/endpoint-lint.yml` — runs on every PR, blocks merge on failure. No extra setup (stdlib only).

```yaml
name: endpoint-lint
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Endpoint lint (no hallucinations)
        run: python scripts/lint_endpoints.py
```

Branch-protection checklist: Settings → Branches → Require status checks → tick `endpoint-lint`.

Optional pre-commit hook (`.pre-commit-config.yaml`):

```yaml
repos:
  - repo: local
    hooks:
      - id: endpoint-lint
        name: endpoint lint
        entry: python scripts/lint_endpoints.py
        language: system
        pass_filenames: false
```

## 3. Fix table

| CI error | Root cause | Fix (copy-paste shape) |
|---|---|---|
| `dynamic route registration inside loop` | `for p in paths: app.get(p)(fn)` | Unroll to literals: `@app.get("/hr_status", operation_id="hr_status")` — one decorator per route |
| `non-literal route path` | `app.get(PREFIX + "/x")` or variable | Inline the literal: `@app.get("/v1/hr_status", ...)`; keep prefix in the string |
| `operation_id must match ^(hr\|it)_` | Missing or `camelCase` id | `@app.get("/hr_status", operation_id="hr_status")` / `operation_id="it_ticket_create"` |
| `duplicate operation_id='hr_x'` | Copy-pasted handler | Rename second: `hr_x_retry`, `hr_x_admin`; keep prefix per domain (`hr_` = HR agent, `it_` = IT agent) |
| `include_in_schema=False` | Debug/internal route hidden | Delete the kwarg, or if truly internal move to a separate `internal_router` never mounted on the public app |
| `required Header(...) param` | `token: str = Header(...)` | `token: str \| None = Header(None)` + enforce inside, or move auth to dependency in `04-auth.md` |
| `required File/Form param` | `f: UploadFile = File(...)` | MCP is JSON-only: accept `filename: str, content_b64: str` in Body, decode server-side |
| `include_router() after MCP wrap` | `mcp = FastMCP(app)` then `app.include_router(r)` | Reorder `app/main.py`: `include_router` × N → `FastMCP(app)` / `serve(app)` last |
| `catch-all … is not last` | `/{rest:path}` above real routes | Move catch-all registration to the bottom of `main.py`, after all `include_router` calls |

## 4. Minimal compliant example

```python
from fastapi import FastAPI
from routers import hr, it
from fastmcp import FastMCP

app = FastAPI(title="VIBE_CODE")
app.include_router(hr.router)   # before wrap
app.include_router(it.router)   # before wrap

@app.get("/hr_status", operation_id="hr_status")
def hr_status() -> dict:
    return {"ok": True}

@app.get("/{full_path:path}", operation_id="it_fallback_404")  # LAST
def fallback(full_path: str) -> dict:
    return {"error": "not found", "path": full_path}

mcp = FastMCP.from_fastapi(app)  # wrap is always last
```

## 5. Verification checklist (paste into PR)

- [ ] `python scripts/lint_endpoints.py` → 0 failures
- [ ] Every route has literal path + `operation_id` (`hr_*` / `it_*`, unique)
- [ ] No `include_in_schema=False` on public routes
- [ ] No required `Header` / `File` / `Form` params
- [ ] `include_router` × N all above MCP wrap; catch-all is last decorator
