# 24 — Custom Composite `onboard_employee_guarded` (Track 2, 8 Fused Helpers)

**CLI:** `@2ndbrainlabs-ai/synapse-cli` `0.1.9` · **Node ≥ 20** · **Mode:** Custom (Python only) · **Track:** 2 (reused in Track 3)
**Sources:** Participant guide p.2 / p.4 (Custom = compose Python functions into one tool; add confirmation before mutating actions), prior notes `19-step-synapse.md`, `final/04-synapse-auto.md`.
**Scope:** exact runbook — source layout with 8 helpers → `synapse build --custom -q workflow` → decorator name/description override → hand-add `confirm + preview_hash + idempotency_key` → mount namespace for Track 3 reuse. With full file template + 1-vs-8 comparison table.

> Custom reads **Python only**. Plain `.js/.jsx` is never scanned. Generated output is always a Python file `<tool_name>_server.py` in project root (hosted or `--local`). Auto flags like `--smart-names`, `--all-endpoints` do **not** apply to Custom — use `-q/--query` instead.

---

## 0. Pre-reqs

```bash
node --version   # v20+
synapse --version  # 0.1.9; else synapse update
cd track2-onboard  # run INSIDE the python project
synapse init       # once per project (skipped only for --local)
python --version   # 3.10+ for generated server
pip install mcp fastmcp pydantic  # as needed by generated server
```

Expected layout:

```
track2-onboard/
  hr_onboard/
    __init__.py
    accounts.py      # create_user_account, grant_system_access
    assets.py        # assign_equipment
    schedule.py      # schedule_orientation
    payroll.py       # create_payroll_record
    notify.py        # send_welcome_pack, log_audit_event
    org.py           # assign_manager
  requirements.txt
```

---

## 1. The 8 fused helpers (what Synapse fuses)

Keep each helper small, typed, single-purpose, with docstring — Custom sends function source to the model, and good docstrings become good tool descriptions. All sync or all async (don't mix).

```python
# hr_onboard/accounts.py
def create_user_account(email: str, full_name: str, dept: str) -> dict:
    """Create HR identity. Returns {"user_id": ...}."""
def grant_system_access(user_id: str, systems: list[str]) -> dict:
    """Grant SSO/systems access. Returns {"granted": [...]}."""

# hr_onboard/assets.py
def assign_equipment(user_id: str, role: str) -> dict:
    """Reserve laptop/badge from inventory. Returns {"asset_tag": ...}."""

# hr_onboard/schedule.py
def schedule_orientation(user_id: str, start_date: str) -> dict:
    """Book orientation slot. Returns {"session_id": ..., "when": ...}."""

# hr_onboard/payroll.py
def create_payroll_record(user_id: str, salary_band: str, start_date: str) -> dict:
    """Create payroll stub. Returns {"payroll_id": ...}."""

# hr_onboard/org.py
def assign_manager(user_id: str, dept: str) -> dict:
    """Resolve + assign default manager for dept. Returns {"manager_id": ...}."""

# hr_onboard/notify.py
def send_welcome_pack(email: str, full_name: str) -> dict:
    """Send welcome email. Returns {"sent": True}."""
def log_audit_event(actor: str, action: str, ref_id: str) -> dict:
    """Append immutable audit log. Returns {"audit_id": ...}."""
```

| # | Helper | Mutating? | Fused into guarded flow at |
|---|---|---|---|
| 1 | `create_user_account` | yes | Step A — identity first (all else keys off `user_id`) |
| 2 | `assign_manager` | no (lookup+link) | Step B — needed before access/equipment defaults |
| 3 | `grant_system_access` | yes | Step C — batched `systems` list |
| 4 | `assign_equipment` | yes | Step D — reserves asset |
| 5 | `schedule_orientation` | yes | Step E — books calendar |
| 6 | `create_payroll_record` | yes (sensitive) | Step F — gated behind `confirm=True` |
| 7 | `send_welcome_pack` | yes (side-effect) | Step G — only after commit |
| 8 | `log_audit_event` | append-only | Step H — always, even on partial failure |

> If any helper does HTTP, keep `httpx` calls with `${ENV}` headers, not hardcoded tokens.

---

## 2. Build command (query variant, no menu)

```bash
synapse build --custom -q "Onboard a new employee: create user account, assign manager, grant system access, assign equipment, schedule orientation, create payroll record, send welcome pack, log audit event. Single guarded tool named onboard_employee_guarded with confirm gate before any mutating step"
```

Long-form equivalent (CI-safe, same thing):

```bash
synapse build --custom --query "Onboard a new employee: create user account, assign manager, grant system access, assign equipment, schedule orientation, create payroll record, send welcome pack, log audit event. Single guarded tool named onboard_employee_guarded with confirm gate before any mutating step"
```

**What happens:**
1. Local scan (tree-sitter, Python only) → function picker filtered by query (no `--all-endpoints` in Custom).
2. Hosted generate → writes `onboard_employee_guarded_server.py` in project root.
3. Prints MCP client snippet pointing at that file (not an `npx synapse-mcp` runner — that's Auto-hosted only).

**Expected:**

```
Discovered 8 function(s)
✓ Custom tool onboard_employee_guarded written to onboard_employee_guarded_server.py
# paste snippet into MCP client config (points at file, see §5)
```

**Fixes:**

| Message | Fix |
|---|---|
| `Endpoint Selection Required` / empty pick | Query too narrow — broaden `-q` text to name all 8 verbs; or re-run with explicit function list if CLI prompts |
| `returned no emit_tool_plan call` (`--local` only) | Local model too small — switch: `synapse model set anthropic` + `export ANTHROPIC_API_KEY=…`, or use hosted build |
| `Not Initialized` | `synapse init` first (not needed for `--local`) |
| No `.py` found / 0 functions | You are in wrong folder or project is JS/TS — Custom reads Python only |

`--local` variant (no quota, needs strong model):

```bash
export ANTHROPIC_API_KEY=sk-ant-…
synapse build --custom -q "Onboard a new employee: ..." --local
```

---

## 3. Decorator name/description override (do by hand)

Generated file ships with a best-guess decorator. **Override it** so the agent reliably picks the guarded tool and never calls helpers directly (helpers are fused inside — they are not separate MCP tools after Custom build).

Find (generated):

```python
@mcp.tool(name="onboard_employee", description="Onboard employee workflow")
```

Replace with:

```python
@mcp.tool(
    name="onboard_employee_guarded",
    description=(
        "Guarded HR onboarding workflow (8 steps fused): create account, "
        "assign manager, grant access, assign equipment, schedule orientation, "
        "create payroll, send welcome pack, audit-log. "
        "Requires confirm=True plus preview_hash match to execute mutating steps; "
        "call with confirm=False first to get a preview. Idempotent via idempotency_key."
    ),
)
```

Rules:
- `name` must be snake_case, unique across **all** MCP servers the agent sees (see §5 namespacing).
- `description` must state (a) what it does, (b) the confirm/preview contract, (c) idempotency — this is what the model reads when choosing tools.
- Keep the Python function name in sync: `def onboard_employee_guarded(...)`.

---

## 4. Hand-add `confirm + preview_hash + idempotency_key` (required for judging)

> Track 2 is judged on **safety: confirmation step before any action that changes data** (guide p.2). The generator does not reliably emit this — add it by hand every time. Pattern: two-phase `preview → confirm`.

### 4a. Signature to enforce

```python
def onboard_employee_guarded(
    email: str,
    full_name: str,
    dept: str,
    role: str,
    start_date: str,
    salary_band: str,
    systems: list[str] | None = None,
    # --- guards (hand-added) ---
    confirm: bool = False,
    preview_hash: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
```

- `confirm=False` → **dry-run only**: validate inputs, compute plan + `preview_hash`, return preview, mutate nothing.
- `confirm=True` → must also pass `preview_hash` from the preview; mismatch → refuse.
- `idempotency_key` → client-generated UUID per employee (`email + start_date` hash is fine); server keeps `seen_keys: dict` → returns cached result on retry instead of double-creating.

### 4b. Minimal guard block (paste inside tool, before any helper call)

```python
import hashlib, json

_seen: dict[str, dict] = {}  # module-level; swap for redis in prod

def _hash(plan: dict) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()[:16]

# inside onboard_employee_guarded, after building `plan` dict:
plan = {"email": email, "full_name": full_name, "dept": dept, "role": role,
        "start_date": start_date, "salary_band": salary_band,
        "systems": systems or ["hr-portal", "sso"]}
digest = _hash(plan)

if idempotency_key and idempotency_key in _seen:
    return {"status": "duplicate", "result": _seen[idempotency_key], "idempotency_key": idempotency_key}

if not confirm:
    return {"status": "preview", "preview_hash": digest, "plan": plan,
            "next": "re-call with confirm=True, preview_hash=<hash>, idempotency_key=<uuid>"}

if preview_hash != digest:
    return {"status": "refused", "reason": "preview_hash mismatch; re-preview with confirm=False",
            "expected_hash": digest}
# ... proceed with 8 helper calls, wrap in try/except with compensation ...
```

### 4c. Fused execution skeleton (compensate on partial failure)

```python
# ... after guard block ...
result: dict = {"user_id": None}
try:
    u = create_user_account(email, full_name, dept); result["user_id"] = u["user_id"]
    result["manager"] = assign_manager(u["user_id"], dept)
    result["access"] = grant_system_access(u["user_id"], plan["systems"])
    result["equipment"] = assign_equipment(u["user_id"], role)
    result["orientation"] = schedule_orientation(u["user_id"], start_date)
    result["payroll"] = create_payroll_record(u["user_id"], salary_band, start_date)
    result["welcome"] = send_welcome_pack(email, full_name)
    result["audit"] = log_audit_event("agent:onboard", "employee_onboarded", u["user_id"])
except Exception as e:
    result["status"] = "partial_failure"
    result["error"] = str(e)
    try: log_audit_event("agent:onboard", f"onboard_failed: {e}", result.get("user_id") or email)
    except Exception: pass
    if idempotency_key: _seen[idempotency_key] = result
    return result

result["status"] = "committed"
if idempotency_key: _seen[idempotency_key] = result
return {"status": "committed", "preview_hash": digest, "result": result}
```

Never let `send_welcome_pack` run before commit; never skip `log_audit_event` on failure.

---

## 5. File template — `onboard_employee_guarded_server.py` (copy-paste)

```python
"""Synapse Custom tool: onboard_employee_guarded. Hand-guarded (confirm + hash + idempotency)."""
import hashlib, json
from mcp.server.fastmcp import FastMCP

from hr_onboard.accounts import create_user_account, grant_system_access
from hr_onboard.assets import assign_equipment
from hr_onboard.schedule import schedule_orientation
from hr_onboard.payroll import create_payroll_record
from hr_onboard.org import assign_manager
from hr_onboard.notify import send_welcome_pack, log_audit_event

mcp = FastMCP("hr-onboard-guarded")
_seen: dict[str, dict] = {}

def _hash(plan: dict) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()[:16]

@mcp.tool(
    name="onboard_employee_guarded",
    description=(
        "Guarded HR onboarding workflow (8 steps fused): create account, "
        "assign manager, grant access, assign equipment, schedule orientation, "
        "create payroll, send welcome pack, audit-log. "
        "Requires confirm=True plus preview_hash match to execute mutating steps; "
        "call with confirm=False first to get a preview. Idempotent via idempotency_key."
    ),
)
def onboard_employee_guarded(
    email: str, full_name: str, dept: str, role: str,
    start_date: str, salary_band: str,
    systems: list[str] | None = None,
    confirm: bool = False,
    preview_hash: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    plan = {"email": email, "full_name": full_name, "dept": dept, "role": role,
            "start_date": start_date, "salary_band": salary_band,
            "systems": systems or ["hr-portal", "sso"]}
    digest = _hash(plan)
    if idempotency_key and idempotency_key in _seen:
        return {"status": "duplicate", "result": _seen[idempotency_key],
                "idempotency_key": idempotency_key}
    if not confirm:
        return {"status": "preview", "preview_hash": digest, "plan": plan,
                "next": "re-call with confirm=True, preview_hash=<hash>, idempotency_key=<uuid>"}
    if preview_hash != digest:
        return {"status": "refused",
                "reason": "preview_hash mismatch; re-preview with confirm=False",
                "expected_hash": digest}
    result: dict = {}
    try:
        u = create_user_account(email, full_name, dept); result["user_id"] = u["user_id"]
        result["manager"] = assign_manager(u["user_id"], dept)
        result["access"] = grant_system_access(u["user_id"], plan["systems"])
        result["equipment"] = assign_equipment(u["user_id"], role)
        result["orientation"] = schedule_orientation(u["user_id"], start_date)
        result["payroll"] = create_payroll_record(u["user_id"], salary_band, start_date)
        result["welcome"] = send_welcome_pack(email, full_name)
        result["audit"] = log_audit_event("agent:onboard", "employee_onboarded", u["user_id"])
    except Exception as e:
        result["status"] = "partial_failure"; result["error"] = str(e)
        try: log_audit_event("agent:onboard", f"onboard_failed: {e}", result.get("user_id") or email)
        except Exception: pass
        if idempotency_key: _seen[idempotency_key] = result
        return result
    result["status"] = "committed"
    if idempotency_key: _seen[idempotency_key] = result
    return {"status": "committed", "preview_hash": digest, "result": result}

if __name__ == "__main__":
    mcp.run()
```

Run it: `python onboard_employee_guarded_server.py` (must import cleanly before wiring to client).

---

## 6. Mount namespace for Track 3 reuse (two servers, no collisions)

Track 3 mounts **two** MCP servers (HR + IT). Give the guarded tool its own client entry and a distinct namespace so `onboard_*` never collides with Auto-generated `hr_*` / `it_*` tools.

Claude Desktop (`claude_desktop_config.json`) / Cursor (Settings → MCP) — **use the snippet Synapse prints**, shaped like:

```json
{
  "mcpServers": {
    "hr-auto": {
      "command": "npx",
      "args": ["-y", "@2ndbrainlabs-ai/synapse-mcp"],
      "env": {
        "SYNAPSE_API_KEY": "${SYNAPSE_API_KEY}",
        "SYNAPSE_SERVER_ID": "srv_hr_xxxx",
        "SYNAPSE_API_URL": "https://api.synapse.2ndbrainlabs.ai",
        "ENDPOINT_BASE_URL": "http://localhost:8001"
      }
    },
    "hr-onboard-guarded": {
      "command": "python",
      "args": ["/abs/path/track2-onboard/onboard_employee_guarded_server.py"],
      "env": {}
    },
    "it-auto": {
      "command": "npx",
      "args": ["-y", "@2ndbrainlabs-ai/synapse-mcp"],
      "env": {
        "SYNAPSE_API_KEY": "${SYNAPSE_API_KEY}",
        "SYNAPSE_SERVER_ID": "srv_it_yyyy",
        "ENDPOINT_BASE_URL": "http://localhost:8002"
      }
    }
  }
}
```

Rules:
- Custom file servers use `command: python + absolute file path`; hosted Auto servers use `npx synapse-mcp + SERVER_ID`. Don't swap them.
- Namespace = server key (`hr-onboard-guarded`) + tool name (`onboard_employee_guarded`); keep both prefixed `hr_` / `onboard_` so Track 3 questions ("onboard Alice and open her IT ticket") route to the right server.
- After adding any helper, rescan **only** the Custom project: `synapse build --custom -q "..." --discover`, then re-apply §3–§4 hand-edits (generator overwrites the file).
- Restart the MCP client after every rebuild; verify with a preview call (should return `status: preview`, zero mutations).

---

## 7. Appendix A — 1-vs-8 comparison table (submit with Track 2)

Demo the same job ("onboard Priya, SDE-1, start 2026-12-01") twice: once with only the 8 raw helpers exposed, once with `onboard_employee_guarded`.

| Dimension | 8 separate tools | 1 guarded composite (`onboard_employee_guarded`) |
|---|---|---|
| Agent calls to finish | 8–12 (one per helper + retries + ordering fixes) | 2 (preview `confirm=False` + commit `confirm=True`) |
| Ordering bugs | Common (payroll before account, welcome before commit) | Impossible — order baked into server code |
| Partial failure | Orphan state (account created, payroll missing; agent must compensate) | Single `partial_failure` envelope + audit log + safe retry via `idempotency_key` |
| Confirmation / safety | Each mutating tool needs its own gate; easy to skip one | One gate at top (`confirm + preview_hash`); mutations unreachable without it |
| Double-execution on retry | Creates 2 accounts / 2 payroll rows | `duplicate` short-circuit on `idempotency_key` |
| Tokens / latency | ~8× tool-call round trips + planner chatter | ~1 plan + 1 commit; helpers run in-process |
| Descriptions to maintain | 8 names/descriptions must all be excellent | 1 name/description to get right (§3) |
| Error demo for judges | Agent stalls mid-flow, asks user what to roll back | Show: preview → tampered `preview_hash` → `refused` → correct commit → replay same `idempotency_key` → `duplicate` |
| When 8 wins | Debugging a single step, or reusing one helper elsewhere | — |
| When 1 wins | — | Every end-to-end onboarding; the submitted path |

Suggested demo script: (1) preview call, (2) commit call, (3) replay with same `idempotency_key` → `duplicate`, (4) tampered hash → `refused`, (5) kill `payroll` stub mid-run → `partial_failure + audit`. Record all five for the Track 2 error-handling score.

---

## 8. Verify checklist

```bash
python -c "import onboard_employee_guarded_server; print('import ok')"
synapse info     # Servers: n/10, indexed lines (Custom counts; --local never counts)
synapse config   # key source, project, endpoints
```

- [ ] `confirm=False` returns `preview` and creates nothing (check DB/inventory unchanged)
- [ ] `confirm=True + preview_hash` returns `committed` with all 8 result keys
- [ ] Same `idempotency_key` twice → second is `duplicate`
- [ ] Wrong `preview_hash` → `refused`
- [ ] Tool name is exactly `onboard_employee_guarded` in client tool list (no `onboard_employee` leftover)
- [ ] Track 3 client shows all three servers (`hr-auto`, `hr-onboard-guarded`, `it-auto`) after restart

## Doc URLs

- CLI README (flags, cache, rebuild, quota): https://github.com/2ndbrainlabs-ai/synapse-cli-ts
- Getting started: https://synapse.2ndbrainlabs.ai/docs
- API reference: https://synapse.2ndbrainlabs.ai/docs/api
- Examples: https://github.com/2ndbrainlabs-ai/synapse-examples
