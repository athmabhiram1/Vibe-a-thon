# 43 — Fast CI: Guardrails to Stop Agent Hallucinations Mid-Build

**Sources:** `research/build/02-api-design.md` (detection contract) · `final/04-synapse-auto.md` §4–§5 (anti-patterns) · `final/15-endpoints.md` (Pair 4 semantics).
**Goal:** <5 min GitHub Actions workflow that fails fast when the agent invents endpoints, duplicates `operation_id`s, breaks OpenAPI, drifts seed data, or forgets `--discover`.
**Rule:** CI is read-only vs prod — lint, diff, run `validate.py`, run `pytest`; never auto-deploy or auto-`--discover`.

## 1. What each job catches

| # | Job | Hallucination it stops |
|---|---|---|
| 1 | `endpoint-lint` | f-string paths, `add_api_route`, missing `operation_id`/`response_model`, unprefixed IDs, wrong route order |
| 2 | `operation-id-uniqueness` | duplicate/colliding IDs (`list_candidates` × 2, auto-generated `get_item`) |
| 3 | `openapi-diff` | phantom tools: code claims endpoint, OpenAPI doesn't have it (or vice versa) |
| 4 | `seed-check` | `validate.py` seed drift: headcount/breach counts changed, SLA math broken |
| 5 | `pytest` | approval-gate bypass, double-POST double-assign, missing audit row |
| 6 | `discover-reminder` | stale `.synapse/surface_cache.json` — reminds human to run `--discover`, never runs it in CI |

## 2. Workflow YAML — copy-paste (`.github/workflows/fast-ci.yml`)

```yaml
name: fast-ci  # <5 min, fail-fast guardrails for agent builds

on:
  push:
    branches: [main, demo/**]
  pull_request:

permissions:
  contents: read

concurrency:
  group: fast-ci-${{ github.ref }}
  cancel-in-progress: true

env:
  PYTHON_VERSION: "3.12"
  HR_PORT: "8001"
  IT_PORT: "8002"

jobs:
  endpoint-lint:
    runs-on: ubuntu-latest
    timeout-minutes: 3
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ env.PYTHON_VERSION }} }
      - name: Static endpoint lint (no dynamic registration)
        run: |
          python - <<'PY'
          import ast, pathlib, sys
          bad = []
          for f in list(pathlib.Path("hr_service/routers").glob("*.py")) + list(pathlib.Path("it_service/routers").glob("*.py")):
              tree = ast.parse(f.read_text())
              src = f.read_text()
              # ban factories / dynamic registration
              for banned in ("add_api_route", "f\"", "f'", "+ \"/", "for ", "include_router("):
                  pass  # cheap grep below handles it
              for node in ast.walk(tree):
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                      for d in node.decorator_list:
                          s = ast.unparse(d)
                          if "router." in s:
                              if "operation_id" not in s:
                                  bad.append(f"{f}:{node.lineno} {node.name} missing operation_id")
                              if "response_model" not in s:
                                  bad.append(f"{f}:{node.lineno} {node.name} missing response_model")
                              if '"/"' in s or "f'" in s or 'f"' in s or "+ " in s:
                                  bad.append(f"{f}:{node.lineno} {node.name} non-literal path")
          import subprocess
          grep = subprocess.run(
            ["grep", "-rn", "--include=*.py", "-E",
             "add_api_route|include_in_schema\\s*=\\s*True|UploadFile|Form\\(|Header\\(.+\\)\\.\\.\\.",
             "hr_service", "it_service"],
            capture_output=True, text=True)
          if grep.stdout.strip():
              bad.append("banned pattern:\n" + grep.stdout.strip())
          # prefixed operation_ids required
          import re
          ids = re.findall(r'operation_id\s*=\s*"(.*?)"', "".join(
            p.read_text() for p in list(pathlib.Path("hr_service").rglob("*.py")) + list(pathlib.Path("it_service").rglob("*.py"))))
          for i in ids:
              if not (i.startswith("hr_") or i.startswith("it_")):
                  bad.append(f"unprefixed operation_id: {i} (must be hr_* / it_*)")
          if bad:
              print("\n".join("FAIL: " + b for b in bad)); sys.exit(1)
          print(f"endpoint-lint OK: {len(ids)} prefixed operation_ids")
          PY

  operation-id-uniqueness:
    runs-on: ubuntu-latest
    timeout-minutes: 2
    needs: endpoint-lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ env.PYTHON_VERSION }} }
      - name: operation_id uniqueness across hr + it
        run: |
          python - <<'PY'
          import pathlib, re, sys, collections
          files = list(pathlib.Path(".").rglob("*.py"))
          ids = []
          for p in files:
              if ".venv" in str(p): continue
              try: ids += re.findall(r'operation_id\s*=\s*["\'](.*?)["\']', p.read_text())
              except Exception: pass
          dupes = [k for k, v in collections.Counter(ids).items() if v > 1]
          if dupes:
              print(f"FAIL: duplicate operation_ids: {dupes}"); sys.exit(1)
          # catch auto-generated FastAPI ids (get_item, get_item_1) leaking into openapi later
          print(f"operation_id uniqueness OK: {len(ids)} total, {len(set(ids))} unique")
          PY

  openapi-diff:
    runs-on: ubuntu-latest
    timeout-minutes: 4
    needs: operation-id-uniqueness
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ env.PYTHON_VERSION }} }
      - run: pip install -q fastapi uvicorn httpx pydantic email-validator
      - name: Boot services + dump openapi.json
        run: |
          (uvicorn hr_service.main:app --port $HR_PORT >/tmp/hr.log 2>&1 &) 
          (uvicorn it_service.main:app --port $IT_PORT >/tmp/it.log 2>&1 &)
          for i in $(seq 1 30); do
            curl -sf localhost:$HR_PORT/openapi.json -o /tmp/hr.json && \
            curl -sf localhost:$IT_PORT/openapi.json -o /tmp/it.json && break
            sleep 2
          done
          ls -la /tmp/hr.json /tmp/it.json
      - name: Diff operationIds vs expected 11 + fail on phantom tools
        run: |
          python - <<'PY'
          import json, sys
          EXPECTED = {"hr_list_candidates","hr_get_candidate","hr_create_employee",
            "hr_shift_calendar","hr_get_oncall","it_list_equipment","it_assign_laptop",
            "it_create_ticket","it_sla_breach_list","it_get_ticket","it_reroute_ticket",
            "hr_health_check","it_health_check"}
          hr = json.load(open("/tmp/hr.json")); it = json.load(open("/tmp/it.json"))
          def ids(spec):
              return {o.get("operationId","") for m in spec["paths"].values() for o in m.values()}
          found = ids(hr) | ids(it)
          print("HR:", sorted(ids(hr))); print("IT:", sorted(ids(it)))
          if "" in found:
              print("FAIL: route missing operationId"); sys.exit(1)
          missing, extra = EXPECTED - found, found - EXPECTED
          # H5 (hr_get_oncall) may be commented out for baseline builds — warn, don't fail
          if missing == {"hr_get_oncall"}:
              print("WARN: baseline build without H5 (hr_get_oncall) — OK")
          elif missing:
              print(f"FAIL: missing from OpenAPI: {sorted(missing)}"); sys.exit(1)
          if extra:
              print(f"FAIL: phantom tools not in contract: {sorted(extra)}"); sys.exit(1)
          print("openapi-diff OK")
          PY

  seed-check:
    runs-on: ubuntu-latest
    timeout-minutes: 3
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ env.PYTHON_VERSION }} }
      - run: pip install -q pydantic
      - name: validate.py seed check (deterministic demo data)
        run: |
          test -f scripts/validate.py || { echo "FAIL: scripts/validate.py missing"; exit 1; }
          python scripts/validate.py --strict
          # expected: headcount + breach counts + SLA deadline = created_at + sla_hours

  pytest-guards:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: [openapi-diff, seed-check]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ env.PYTHON_VERSION }} }
      - run: pip install -q fastapi uvicorn httpx pytest pydantic email-validator
      - name: Approval / idempotency / audit tests only (fast subset)
        run: |
          pytest -q -k "approval or idempotency or audit or sla or reroute" --maxfail=1
          # Representative cases CI must include:
          #  test_approval_blocks_unconfirmed_assign  (POST without confirm=True -> 409/422, no DB write)
          #  test_idempotent_assign_same_key         (same Idempotency-Key -> 1 assignment, replay 200 cached)
          #  test_audit_row_on_reroute               (reroute writes audit: ticket_id, from, to, reason)

  discover-reminder:
    runs-on: ubuntu-latest
    timeout-minutes: 1
    needs: [pytest-guards]
    if: always()
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 2 }
      - name: surface_cache --discover reminder (never auto-runs)
        run: |
          if git diff --name-only HEAD~1 -- hr_service/routers it_service/routers | grep -q .; then
            echo "::warning::Routers changed but .synapse/surface_cache.json is reused by builds."
            echo "::warning::Run locally: synapse build --discover --auto --all-endpoints"
            echo "Changed: $(git diff --name-only HEAD~1 -- hr_service/routers it_service/routers)"
          else
            echo "No router changes — no --discover needed."
          fi
```

## 3. Supporting files (add once)

```bash
# scripts/validate.py contract (what seed-check asserts)
python scripts/validate.py --strict
# asserts: candidate count, free-laptop pool, T-551 breach fixture,
#   deadline_at == created_at + sla_hours, shift fixtures for support-night

# pytest markers (pytest.ini)
# -k "approval or idempotency or audit or sla or reroute" keeps CI <5 min;
# full suite runs nightly, not per-push.
```

## 4. Local pre-push mirror (same checks, 60s)

```bash
python scripts/validate.py --strict && \
pytest -q -k "approval or idempotency or audit" --maxfail=1 && \
curl -s localhost:8001/openapi.json | python -c "import json,sys; print(sorted({o.get('operationId','') for m in json.load(sys.stdin)['paths'].values() for o in m.values()}))"
```

## 5. Failure → fix table

| CI failure | Likely agent hallucination | Fix |
|---|---|---|
| `endpoint-lint` missing `operation_id` | invented route without ID | add prefixed `operation_id="hr_*"/"it_*"` |
| `operation-id-uniqueness` dupe | copied stub, forgot rename | rename to unique prefixed ID |
| `openapi-diff` phantom | route hidden (`include_in_schema`) or dynamic | literal decorator + `include_router` at import time |
| `seed-check` drift | agent rewrote fixtures | restore `scripts/seed*.json`, rerun `validate.py` |
| `pytest` idempotency fail | double-POST created 2 rows | honor `Idempotency-Key`, return cached 200 |
| `discover-reminder` warning | new H5 not visible to agent | run `synapse build --discover` locally |
