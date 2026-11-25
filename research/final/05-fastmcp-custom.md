# FastMCP Custom Composition + Safety: Stage-Then-Activate, Confirm + preview_hash, Idempotency

**Purpose:** Tech grounding for Track 2 ("One smart tool from many small functions") onboarding — how Synapse Custom's single-`@mcp.tool` output maps onto canonical FastMCP, and the safety wrapper every write-path demo needs.
**Date:** 2026-11-22. All links verified at research time. Claims without a URL are marked **[Inference]**.

> Method note (Cite-Before-Act): every factual claim below carries a source URL, per the MCP 1st Birthday Best-Overall pattern (Cite-Before-Act MCP — "require explicit approval before state-mutating operations": https://gradio.app/mcp-birthday-winners, live Space: https://huggingface.co/spaces/MCP-1st-Birthday/cite-before-act-mcp). Nothing is invented; interpretation is labeled **[Inference]**.

---

## TL;DR for team

- **Synapse Custom output = one FastMCP `@mcp.tool` Python file** (`<tool_name>_server.py`, `FastMCP("<name>")` + `mcp.run()`), whose body may only call functions in the extracted manifest (see `research/03-synapse-technical.md` §2.4). Style it exactly like canonical FastMCP below so judges recognise it.
- **Never expose a raw mutating tool.** Wrap every write in the onboarding safety triple: **(1) stage-then-activate** (preview first, activate second), **(2) confirm + preview_hash** (human confirms the exact hash they previewed), **(3) idempotency key** (safe retry, no double-apply).
- **MCP spec backs you:** "there SHOULD always be a human in the loop with the ability to deny tool invocations… Present confirmation prompts" — https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx (via Context7).
- **Auth story:** standard MCP OAuth is interactive user-consent; only headless daemons/CI use client-credentials without a user — https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/extensions/auth/oauth-client-credentials.mdx. For the hackathon: scope tools by role + `${VAR}` secrets, don't claim full OAuth unless you built it.

---

## (a) FastMCP `@mcp.tool` composition — the canonical pattern

Source docs: https://gofastmcp.com/docs/servers/tools (Tools), https://github.com/PrefectHQ/fastmcp (repo, ~28.7k stars), Context7 library ID `/prefecthq/fastmcp`.

**1. One function = one tool (schema is inferred).** FastMCP "automatically uses the function name as the tool name, parses the docstring for the tool description and per-parameter descriptions, generates an input schema from the function's parameters and type annotations" (Context7 `query-docs` on `/prefecthq/fastmcp`, source `docs/servers/tools.mdx`):

```python
from fastmcp import FastMCP

mcp = FastMCP(name="OnboardingServer")

@mcp.tool
def onboard_employee(name: str, dept: str, laptop: bool = True) -> dict:
    """Onboard a new employee: create account, assign equipment, schedule orientation."""
    account = create_account(name, dept)          # only manifest-listed callees
    equip = assign_equipment(account["id"], laptop)
    invite = schedule_orientation(account["id"])
    return {"account": account, "equipment": equip, "orientation": invite}

if __name__ == "__main__":
    mcp.run()
```

**2. Override name/description/tags/meta when composing.** Decorator args (`name=`, `description=`, `tags={...}`, `meta={...}`) override the inferred schema — use them so the "one smart tool" reads as designed, not accidental (same source):

```python
@mcp.tool(
    name="process_refund",
    description="Check order, check policy, issue refund. Read-only checks run first; refund needs confirm.",
    tags={"orders", "refunds"},
    meta={"version": "1.0"},
)
def process_refund_impl(order_id: str, reason: str, idempotency_key: str) -> dict:
    """Internal description ignored; decorator description is exposed."""
    ...
```

**3. Mounting/namespacing (Track 3 reuse).** `main.mount(server, namespace="hr")` prefixes tools (`hr_get_data`) and avoids collisions; mounting after-the-fact still works ("Dynamic Composition") — https://gofastmcp.com/docs/servers/composition and Context7 `docs/servers/transforms/namespace.mdx`.
**[Inference]** For Track 2 you don't need mounting — one composed file is the deliverable. Keep mounting in your pocket for Track 3 (two Synapse servers → one orchestrator).

**4. Error + middleware hooks.** Wrap `call_next()` in try/except and re-raise; use `ErrorHandlingMiddleware(transform_errors=False)` to log while preserving protocol errors; gate all tools with `AuthMiddleware(auth)` checks (`on_call_tool`, `on_list_tools`) — Context7 `docs/servers/middleware.mdx`, `fastmcp-server-middleware-authorization.mdx`.

---

## (b) Safety triple for every mutating tool: stage → confirm → activate + idempotency

Why: GSA 2026 rubric rejects "a thin wrapper around a single REST call" and demands "each tool represents a real agent-facing action" (https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon); Cite-Before-Act won Best Overall for exactly this middleware (https://gradio.app/mcp-birthday-winners).

### Pattern (copy-paste for `onboard_employee` / `process_refund`)

```python
import hashlib, json
from fastmcp import FastMCP

mcp = FastMCP(name="OnboardingServer")
_STAGED: dict[str, dict] = {}  # demo only; use DB/Redis in production

def _preview_hash(plan: dict) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()[:16]

@mcp.tool
def onboard_preview(name: str, dept: str, laptop: bool = True) -> dict:
    """STAGE (read-only): preview what onboarding WOULD do. No writes."""
    plan = {"create_account": {"name": name, "dept": dept},
            "assign_equipment": {"laptop": laptop},
            "schedule_orientation": {"dept": dept}}
    ph = _preview_hash(plan)
    _STAGED[ph] = plan
    return {"preview_hash": ph, "plan": plan, "note": "Call onboard_activate only after human confirms this hash."}

@mcp.tool
def onboard_activate(preview_hash: str, confirm: bool, idempotency_key: str) -> dict:
    """ACTIVATE (write): requires confirm=True AND the exact preview_hash. Idempotent."""
    if not confirm:
        return {"status": "aborted", "reason": "confirm=False; human did not approve."}
    plan = _STAGED.get(preview_hash)
    if plan is None:
        return {"status": "error", "reason": "unknown/expired preview_hash; re-run preview."}
    # idempotency: same key → return prior result, never double-apply
    existing = lookup_by_idempotency_key(idempotency_key)  # your ledger check
    if existing is not None:
        return {"status": "already_applied", "result": existing}
    result = apply_plan(plan)  # the only place writes happen
    store_idempotency_key(idempotency_key, preview_hash, result)
    _STAGED.pop(preview_hash, None)
    return {"status": "applied", "preview_hash": preview_hash, "result": result}
```

Rules:
1. **stage-then-activate:** preview tool is `readOnlyHint=True`; activate is `readOnlyHint=False` (annotation pattern per https://gofastmcp.com/docs/servers/tools and CircleCI FastMCP example). Demo shows both calls; agent must never call activate first.
2. **confirm + preview_hash:** the human (or MCP client's confirmation prompt, per the spec's "SHOULD… present confirmation prompts") approves the *hash*, not a vague "yes". Mismatch/expired hash → refuse. This is the Cite-Before-Act gate in miniature.
3. **idempotency:** `idempotency_key` (client-generated UUID) is a required param; ledger lookup before any write; retries return `already_applied`. **[Inference]** Synapse won't generate this for you — hand-add it after `synapse build --custom` and call it out in the "one vs many" comparison (Track 2 deliverable).

---

## (c) Auth / scopes — what to claim honestly

- **MCP standard auth = interactive OAuth consent** ("browser opens, user logs in, grants permission"); client-credentials (no user) only for "background services, CI/CD, server-to-server, daemons" — https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/extensions/auth/oauth-client-credentials.mdx. **If a human should authorize, use the user-driven flow** (same source).
- **Spec consent rule:** human-in-the-loop SHOULD be able to deny any tool call; apps SHOULD show which tools are exposed + indicators + confirmation prompts — https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx.
- **FastMCP enforcement:** `AuthMiddleware(auth)` global checks + per-component checks; `on_list_tools` filtering so unauthorized tools are hidden, `on_call_tool` gating execution (Context7 `fastmcp-server-middleware-authorization.mdx`).
- **Hackathon-honest posture [Inference]:** Synapse emits `${VAR}` env placeholders + `.env.example` merge (see `research/03-synapse-technical.md` §2.3); that is *secret hygiene*, not OAuth. Claim: "scoped tokens at source, least-privilege endpoint selection, confirm-gate on writes" — not "full OAuth2 scopes" unless you wired a provider (Keycloak/JWT pattern like MCP.STORE runner-up: https://www.solo.io/blog/celebrating-the-winners-of-the-2026-hackathon-for-mcp-ai-agents).

---

## (d) How Synapse Custom maps onto this (don't fight the generator)

| Synapse Custom reality (verified in `research/03-synapse-technical.md`) | What you do after `synapse build --custom` |
|---|---|
| One `@mcp.tool`, body calls only manifest functions (`auditBody` rejects inline `def` helpers/unknown callees) | Keep composition inside manifest functions; add safety as *separate* preview/activate tools in the same file or a thin wrapper file |
| Params are model-chosen (`ToolPlan`: `tool_name, description, param_names/types, body_source, imports, env_vars, is_async`) | Rename via decorator `name=`/`description=`; add `idempotency_key`, `confirm`, `preview_hash` params by hand |
| Renderer auto-adds `from <module> import <qualname>` + merges `.env.example` | Keep `${VAR}` placeholders; never paste real tokens; show `.env.example` in demo |
| Rebuilds reuse `.synapse/surface_cache.json` until `--discover` | Always `synapse build --discover` after code changes before recording |
| Small local models fail with `returned no emit_tool_plan call` | Use hosted or a strong `--local` model (see `guide.txt` p.5–6 provider table) |

---

## (e) Track 2 demo checklist (judges: "tool design, errors/edge cases, safety")

Per `guide.txt` p.2 (Track 2 judged on tool design, error/edge handling, safety + "confirmation step before any action that changes data"):

- [ ] `synapse build --custom -q "<workflow>"` output file committed (`<tool>_server.py`).
- [ ] Preview/activate split visible in client (Claude Desktop/Cursor snippet from Synapse, restart client).
- [ ] `confirm=False` → abort; wrong `preview_hash` → error; same `idempotency_key` twice → `already_applied` (show all three live).
- [ ] One-vs-many comparison: same job with N small tools vs 1 composed tool (fewer steps, fewer mis-calls, gated writes) — required Track 2 artefact.
- [ ] No JS-only codebases (Custom reads Python only; generated servers are always Python — `guide.txt` p.4).

---

## Sources (all accessed 2026-11-22)

**Context7 (via `execute` search):**
- `/prefecthq/fastmcp` — `@mcp.tool` decorator (name/description/tags/meta inference), `docs/servers/tools.mdx`, `docs/tutorials/create-mcp-server.mdx`
- `/prefecthq/fastmcp` — namespace/mount composition, `docs/servers/transforms/namespace.mdx`
- `/prefecthq/fastmcp` — middleware: try/except `call_next`, `ErrorHandlingMiddleware`, `AuthMiddleware` (`docs/servers/middleware.mdx`, `fastmcp-server-middleware-authorization.mdx`)
- `/modelcontextprotocol/modelcontextprotocol` — Tools spec human-in-the-loop SHOULD + confirmation prompts (`docs/specification/2026-07-28/server/tools.mdx`); OAuth client-credentials vs user-consent (`docs/extensions/auth/oauth-client-credentials.mdx`); elicitation URL-mode diagram (`docs/specification/2026-07-28/client/elicitation.mdx`)

**Web (Cite-Before-Act + FastMCP grounding):**
- https://gradio.app/mcp-birthday-winners (Cite-Before-Act Best Overall; Legacy Modernizer; Vehicle Diagnostics)
- https://huggingface.co/spaces/MCP-1st-Birthday/cite-before-act-mcp (approval-before-mutation middleware)
- https://gofastmcp.com/docs/servers/tools (return values, duplicate-tool policy, annotations `readOnlyHint/openWorldHint`)
- https://gofastmcp.com/docs/servers/composition (mount, dynamic composition, conflict resolution)
- https://github.com/PrefectHQ/fastmcp (framework repo)
- https://www.solo.io/blog/celebrating-the-winners-of-the-2026-hackathon-for-mcp-ai-agents (MCP.STORE Keycloak/JWT "cannot bypass"; K8s governance)
- https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon ("not a thin wrapper" rubric)
- Local: `research/03-synapse-technical.md` (§2.3–2.4 Custom mechanics), `guide.txt` pp.1–8 (tracks, modes, `--local` providers, error table)
