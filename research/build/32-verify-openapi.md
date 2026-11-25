# 32 — Verify openapi.json Contract (operationId → Picker → /docs → Types)

**Scope:** pre-`synapse build` gate. Proves every FastAPI route survives to `openapi.json`, renders in Swagger `/docs`, carries a typed `response_model`, uses scalar-only params (Synapse tree-sitter picker-safe), and appears in the Synapse picker cache.
**When to run:** after any route add/edit, before `synapse build --auto --all-endpoints`, and in CI before demo freeze.
**Applies to:** `hr_api.py` (:8001) + `it_api.py` (:8002). FastAPI ≥ 0.100, Pydantic v2.

---

## 0. Contract rules (fail = do not build)

| # | Rule | Why |
|---|---|---|
| R1 | Every route has unique literal `operation_id` (`hr_*` / `it_*`) | Synapse picker keys on it; duplicates/collision = dropped tool |
| R2 | Every `operation_id` in `/openapi.json` appears in Synapse picker cache | Gap = dynamic route, `include_in_schema=False`, un-included router |
| R3 | `GET /docs` returns 200 and lists every path | Catches `include_in_schema=False`, auth-guarded docs, broken schema gen |
| R4 | Every route declares `response_model=<Pydantic>` (no `None` / bare `dict`) | Untyped returns generate `additionalProperties: true` → vague tools, judge-visible slop |
| R5 | All params are scalar (`str/int/float/bool/UUID/datetime/Enum`) + `Query/Path`; bodies are single Pydantic model | `dict/Any/nested-JSON-string` params break Auto tool arg extraction |

---

## 1. Fast import check (no server needed) — `python -c`

Catches syntax errors, missing `response_model`, non-scalar signatures before booting uvicorn.

```bash
# HR API
python -c "import hr_api; app=hr_api.app; print(len(app.routes), 'routes OK:', app.title)"

# IT API
python -c "import it_api; app=it_api.app; print(len(app.routes), 'routes OK:', app.title)"

# Strict: assert every route has operation_id + response_model (fails fast)
python -c "
from hr_api import app as a1
from it_api import app as a2
for app,label in [(a1,'hr'),(a2,'it')]:
    for r in app.routes:
        if not getattr(r,'methods',None): continue
        assert getattr(r,'operation_id',None), f'{label}: {r.path} missing operation_id'
        assert getattr(r,'response_model',None) is not None, f'{label}: {r.path} [{r.operation_id}] missing response_model'
print('R1+R4 PASS: all routes have operation_id + response_model')
"
```

**Expected:**

```
8 routes OK: HR API
9 routes OK: IT API
R1+R4 PASS: all routes have operation_id + response_model
```

**Fixes:** `AssertionError: missing operation_id` → add `operation_id="hr_list_employees"` literal to decorator. `missing response_model` → add `response_model=EmployeeOut` (define in `models.py`, never inline `dict`).

---

## 2. Boot + curl openapi.json + /docs

```bash
# terminal 1+2
uvicorn hr_api:app --port 8001 &
uvicorn it_api:app --port 8002 &

# R2/R3: raw spec + docs render
curl -s http://localhost:8001/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print('HR ops:', sorted(o.get('operationId','?') for p in d['paths'].values() for o in p.values()))"
curl -s http://localhost:8002/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print('IT ops:', sorted(o.get('operationId','?') for p in d['paths'].values() for o in p.values()))"

curl -s -o NUL -w "HR /docs -> %{http_code}\n" http://localhost:8001/docs
curl -s -o NUL -w "IT /docs -> %{http_code}\n" http://localhost:8002/docs
```

PowerShell equivalents:

```powershell
curl.exe -s http://localhost:8001/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print(sorted(o.get('operationId','?') for p in d['paths'].values() for o in p.values()))"
Invoke-WebRequest http://localhost:8001/docs -UseBasicParsing | Select-Object StatusCode
```

**Expected:** both `/docs` → `200`; op lists show `hr_*` (5) and `it_*` (6), all unique, no `?`.

**Fixes:** missing path → route has `include_in_schema=False` or router never `app.include_router()`'d. `/docs` 404/500 → schema gen crashed on `Any`/recursive model — pin concrete Pydantic types.

---

## 3. Scalar-params + typed-response audit (one script)

```bash
python verify_openapi.py --base http://localhost:8001 --prefix hr_ --expect 5
python verify_openapi.py --base http://localhost:8002 --prefix it_ --expect 6
```

`verify_openapi.py` (save at repo root, stdlib + `requests` only):

```python
"""openapi.json contract gate: R1-R5. Exit 0 = build-safe. Exit 1 = fix first."""
import argparse, json, sys, urllib.request

SCALARS = {"string", "integer", "number", "boolean"}

def get(base, path):
    with urllib.request.urlopen(base + path, timeout=10) as r:
        return r.status, r.read()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--expect", type=int, required=True)
    a = ap.parse_args()
    fails = []

    # R3: /docs renders
    status, _ = get(a.base, "/docs")
    print(f"[R3] GET /docs -> {status}")
    if status != 200:
        fails.append("R3 /docs not 200")

    # fetch spec
    _, raw = get(a.base, "/openapi.json")
    spec = json.loads(raw)
    ops = {o.get("operationId"): (path, o)
           for path, item in spec.get("paths", {}).items() for o in item.values()}
    print(f"[R1] {len(ops)} operationIds: {sorted(ops)}")

    # R1: count + prefix + uniqueness
    if len(ops) != a.expect:
        fails.append(f"R1 expected {a.expect} ops, found {len(ops)}")
    for op in ops:
        if not op or not op.startswith(a.prefix):
            fails.append(f"R1 bad/missing operationId: {op!r} (want prefix {a.prefix!r})")

    # R4+R5 per operation
    for op, (path, o) in sorted(ops.items()):
        # R4: typed 200 response (object/array with $ref or typed items, not free-form)
        resp = (o.get("responses", {}).get("200", {})
                .get("content", {}).get("application/json", {}).get("schema", {}))
        if not resp or (resp.get("type") not in ("object", "array") and "$ref" not in resp):
            fails.append(f"R4 {op} ({path}): 200 response untyped -> add response_model=")
        # R5: params scalar-only
        for p in o.get("parameters", []):
            t = ((p.get("schema") or {}).get("type"))
            fmt = ((p.get("schema") or {}).get("format"))
            if t not in SCALARS and "$ref" not in (p.get("schema") or {}):
                # allow uuid/date-time strings + enums
                if not (t == "string" or (p.get("schema") or {}).get("enum")):
                    fails.append(f"R5 {op}: param {p.get('name')} type={t} not scalar")
        # R5: body must be single $ref'd model, not free dict
        body = (o.get("requestBody", {}).get("content", {})
                .get("application/json", {}).get("schema", {}))
        if body and "$ref" not in body and body.get("type") == "object" \
                and not body.get("properties"):
            fails.append(f"R5 {op}: body is free-form object -> use one BaseModel")

    if fails:
        print("FAIL:"); [print(" -", f) for f in fails]
        sys.exit(1)
    print(f"PASS R1+R3+R4+R5 on {a.base} ({len(ops)} ops)")

if __name__ == "__main__":
    main()
```

**Expected:**

```
[R3] GET /docs -> 200
[R1] 5 operationIds: ['hr_create_employee', 'hr_get_employee', ...]
PASS R1+R3+R4+R5 on http://localhost:8001 (5 ops)
```

---

## 4. Picker diff — every operationId in Synapse cache (R2)

Run **after** a scan (`synapse build --auto ...` or `synapse analyze`). Compares live spec vs `.synapse/surface_cache.json`.

```bash
python picker_diff.py --base http://localhost:8001 --cache .synapse/surface_cache.json
```

`picker_diff.py`:

```python
"""Diff openapi.json operationIds vs Synapse picker cache. Exit 1 on any gap."""
import argparse, json, urllib.request

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--cache", default=".synapse/surface_cache.json")
    a = ap.parse_args()
    with urllib.request.urlopen(a.base + "/openapi.json", timeout=10) as r:
        spec = json.loads(r.read())
    spec_ops = {o.get("operationId")
                for item in spec["paths"].values() for o in item.values()}
    cache_raw = open(a.cache, encoding="utf-8").read()
    cached = {op for op in spec_ops if op and op in cache_raw}
    missing = sorted(spec_ops - cached)
    print(f"spec={len(spec_ops)} cached={len(cached)} missing={missing or 'none'}")
    if missing:
        print("R2 FAIL: picker dropped:", missing)
        print("Likely: dynamic path (f-string), include_in_schema=False, "
              "router not included, or stale cache -> rerun with --discover.")
        raise SystemExit(1)
    print("R2 PASS: every operationId is pickable")

if __name__ == "__main__":
    main()
```

PowerShell one-liner (no script file, quick triage):

```powershell
$spec = (curl.exe -s http://localhost:8001/openapi.json | ConvertFrom-Json).paths.PSObject.Properties.Value.operationId
$cache = Get-Content .synapse/surface_cache.json -Raw
$spec | ForEach-Object { if ($cache -notmatch $_) { Write-Host "MISSING: $_" } }
```

**Expected:** `missing=none` / no `MISSING:` lines. Any gap → fix route shape, then `synapse build --discover --auto --all-endpoints --server-name hr-api` and re-diff.

---

## 5. Anti-pattern checklist (picker killers)

- ❌ `@app.get("/employees/{x}")` with `x: dict` / `Any` → ✅ `x: UUID` / `str`
- ❌ `def f(payload: str)` holding JSON text → ✅ `def f(payload: TicketCreate)` (one BaseModel)
- ❌ `operation_id=f"hr_{name}"` (dynamic) → ✅ literal `operation_id="hr_list_employees"`
- ❌ `include_in_schema=False` on real routes → ✅ remove (use only for `/healthz` internals)
- ❌ router defined but `app.include_router(router)` forgotten → ✅ include + re-curl spec
- ❌ `response_model=None` / `-> dict` → ✅ `response_model=EmployeeOut | list[EmployeeOut]`

---

## 6. CI / pre-build gate (copy-paste)

```bash
python -c "import hr_api, it_api; print('imports OK')"
uvicorn hr_api:app --port 8001 & uvicorn it_api:app --port 8002 &
sleep 3
python verify_openapi.py --base http://localhost:8001 --prefix hr_ --expect 5
python verify_openapi.py --base http://localhost:8002 --prefix it_ --expect 6
synapse build --auto --all-endpoints --server-name hr-api
synapse build --auto --all-endpoints --server-name it-api --new
python picker_diff.py --base http://localhost:8001
python picker_diff.py --base http://localhost:8002 --cache .synapse/surface_cache.json
```

Green on all six lines = safe to build. Red anywhere = fix code, never `--force` past it.

## Sources

- Synapse picker semantics + `surface_cache.json` + `--discover` rebuild: `research/build/19-step-synapse.md` §§4–7; CLI README https://github.com/2ndbrainlabs-ai/synapse-cli-ts
- FastAPI `operation_id` / `response_model` / `include_in_schema` contract: `research/final/04-synapse-auto.md`; FastAPI docs https://fastapi.tiangolo.com/tutorial/path-params/ + https://fastapi.tiangolo.com/tutorial/extra-models/
