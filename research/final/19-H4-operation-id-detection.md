# H4 — Python FastAPI Explicit `operation_id` Guarantees Detection

**Claim:** For Track 3 agent interop, only explicit `operation_id` on every Python FastAPI route guarantees 100% stable tool detection/naming by OpenAPI scanners; auto-generated IDs miss or mangle tools.

**Null (H0):** Scanner detection is equivalent with or without explicit `operation_id`; auto-ID variant detects 100% of routes with stable usable names.

**Falsification criterion (specific observation that kills H4):** Probe 3 FastAPI variants with the same 5 routes (GET/POST, path params, duplicated names) — (A) no explicit IDs, (B) explicit unique `operation_id` on all routes, (C) duplicate `operation_id`s. If variant A also yields 5/5 detected with clean stable names (no `get_api_foo_get`-style mangling, no drops), H4 is FALSIFIED.

**Alternative (if falsified):** Skip `operation_id` enforcement; rely on default FastAPI OpenAPI + client-side name cleanup.

**Priority:** P0 — build-breaker. If true, every Track 3 demo API must lint for explicit IDs or the discover moment silently drops tools.

**Verification method:**
1. Spin 3 minimal FastAPI apps (5 routes each) on localhost; dump `/openapi.json`.
2. Run scanner/discover parser; record detected-tool count, names, duplicates/collisions.
3. Pass bar: B = 5/5 clean names; predict A = ≤4/5 or mangled names; C = collision warning.

**Expected outcome:** B = 5/5 stable (`createTicket`, `getTicket`…); A = 4/5 or names like `read_item_items__item_id__get`; C = dedup suffixes. Action on confirm: add `operation_id` lint rule + starter template with explicit IDs for all Track 3 targets.
```python
# required pattern
@app.get("/tickets/{tid}", operation_id="getTicket")
def get_ticket(tid: str): ...
```
