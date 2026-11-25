# 04 — Track 2 Safety & Governance Patterns
*Judged on errors, edge cases, safety + confirmation before data change*

> Sources: MCP 1st-Birthday **Cite-Before-Act** proxy; **MCP.STORE / Keycloak JWT + CEL** (`agentgateway` `AgentgatewayPolicy`); **DataHub Blackbox evidence gate** (`confirm_root_cause`, `ACCEPTANCE.md`, `ARCHITECTURE.md`); **Solo.io agentgateway MCP governance** (registration catalog, signature verification, audit); Context7 `modelcontextprotocol/modelcontextprotocol` Python SDK auth tutorial (2026-07-28).

---

## 1. The Golden Rule for Track 2

> **Investigation can be autonomous. Mutation must not be.**
> Blackbox phrasing to steal: `READ → PROVE → ACT → VERIFY → WRITE`

Judges will try to break you with:
1. Destructive tool call with no confirm (“delete all rows where…”)
2. Ambiguous scope (“clean up the db”)
3. Secret in prompt / log (“here’s my `GITHUB_PAT=ghp_...`”)
4. Double-submit / retry after timeout (non-idempotent write executes twice)
5. Hallucinated citation (“trust me, lineage says X”)

Win by making all 5 **structurally impossible**, not “the LLM is careful”.

---

## 2. Confirmation-Step UX: dry-run → preview → approve → execute → audit

### Pattern A — Cite-Before-Act proxy (recommended for demo)

Architecture from `MCP-1st-Birthday/cite-before-act-mcp`:

```
Client → Cite-Before-Act Proxy → Middleware → Detection → Explain → Approval → Upstream Server
                                              (if mutating) ↓
                                              Multi-Method Approval (Dialog + Slack + File)
                                              ↓ Execute or Reject
```

4 engines to copy:
- **Detection** (`detection.py`): allowlist + blocklist + naming convention (`create_*`, `update_*`, `delete_*`, `merge_*`, `push_*`, `*write*`) + metadata/description scan. Default-deny: unknown = mutating.
- **Explain** (`explain.py`): LLM-readable preview, not just echo of args.
- **Approval** (`approval.py`): timeout (default 300s), explicit approve/reject, audit log.
- **Middleware** (`middleware.py`): intercepts `tools/call`, routes read-only through, gates mutating.

Detection table to implement on Day 1:

| Class | Examples | Policy |
|---|---|---|
| Read-only (auto-allow) | `get_*`, `list_*`, `search_*`, `describe_*`, `select`, `profile` | Execute immediately, log |
| Mutating (require approval) | `create_*`, `update_*`, `delete_*`, `insert`, `merge_*`, `push_*`, `write_*`, `star_*` | Dry-run → preview → approve |
| Destructive (require approval + typed confirm) | `delete_repository`, `drop_table`, `truncate`, `*delete*` bulk | Preview + type resource name + approve |
| Unknown | anything not classified | Treat as mutating (fail-closed) |

### Pattern B — In-agent confirm loop (no proxy, easiest for hackathon)

Every write tool **must** expose `dry_run: bool = True` and return a preview object:

```python
@mcp.tool()
def update_row(table: str, row_id: int, patch: dict, dry_run: bool = True,
               idempotency_key: str = "") -> dict:
    """Preview first, mutate only on explicit approval."""
    preview = build_preview(table, row_id, patch)  # before/after diff + blast radius
    if dry_run:
        return {"status": "preview", "preview": preview,
                "requires_approval": True, "idempotency_key": idempotency_key or new_key()}
    # only here: check approval token + evidence gate, then execute
```

UX flow (exact order judges expect):

1. **Dry-run**: agent calls tool with `dry_run=true` → returns human-readable diff.
2. **Preview**: agent renders preview to user, never executes silently.
3. **Approve**: user says yes / clicks Approve / types resource name.
4. **Execute**: agent re-calls with `dry_run=false` + same `idempotency_key` + `approval_token`.
5. **Audit**: append-only log entry (who, what, when, diff, evidence IDs, result).

### Copy-paste demo script lines — “agent asks approval”

Use these verbatim in your demo so the judge hears the gate:

```
Agent: "I found 3 rows in `raw_orders` where amount is 100× contract (evidence #E7, #E12 below).
        Proposed fix: UPDATE raw_orders SET amount = amount/100 WHERE provider='cloudpay_v2' AND ingested_at >= '2026-08-01' (3 rows, preview below).
        This is a WRITE. Reply APPROVE 3-rows-cloudpay OR edit the scope. I will not execute until you confirm."

User: "APPROVE 3-rows-cloudpay"

Agent: "Approval recorded (token apr_9f3…, key idem_7c2…). Executing now — dry_run=false… Done: 3 rows updated in 412ms. Verifying: re-ran invariant suite 32/32 green, KPI 93.3× → 0.93×. Audit entry #A41 written."
```

Rejection line:

```
Agent: "Rejected — no approval token found for `delete_repository`. Returning error to client, nothing was executed. To proceed, run dry-run first and reply APPROVE <key>."
```

Bad-input line (shows edge-case handling):

```
Agent: "I can't do 'clean up the db' — scope is ambiguous. I found 2 candidate scopes: (1) 3 anomalous rows, (2) full table truncate (12,400 rows, DESTRUCTIVE, blocked by policy). Pick 1 or restate. Default: no action."
```

---

## 3. Read-only vs Write Scopes (OAuth + CEL)

### MCP Python SDK auth (Context7 — `/modelcontextprotocol/modelcontextprotocol`)

Minimum viable secure server (copy from official tutorial):

```python
from mcp.server import MCPServer
from mcp.server.auth.settings import AuthSettings

mcp = MCPServer(
    "Track2Demo",
    token_verifier=JWTTokenVerifier(),  # validates JWT via JWKS, checks iss/aud/exp
    auth=AuthSettings.model_validate({
        "issuer_url": ISSUER,                      # e.g. Keycloak realm URL
        "resource_server_url": MCP_SERVER_URL,     # MUST equal token aud
        "required_scopes": ["mcp:tools"],          # or ["read:all"] vs ["write:all"]
        "validate_token_resource": True,
    }),
)
```

Rules:
- Short-lived access tokens + rotating refresh tokens (public clients).
- `aud` must be **your** MCP server URL (`resource` param RFC 8707). Reject if mismatch → prevents token replay across servers.
- Missing scope → `403 + WWW-Authenticate: insufficient_scope`, not silent allow.
- Discovery endpoints need no token: `POST /mcp` (401 challenge) + `/.well-known/oauth-protected-resource/mcp`.

Split scopes Day 1:

```
read:all   → get_*, list_*, search_*, profile, lineage, assertions
write:all  → create_*, update_*, patch, writeback
admin:all  → delete_*, drop_*, truncate, grant (require second human + typed confirm)
```

### Gateway-level CEL (Solo.io agentgateway / MCP.STORE pattern)

Don't re-implement authz in every tool — enforce at proxy with CEL, mirroring `AgentgatewayPolicy`:

```yaml
# Solo.io agentgateway standalone example (adapted)
mcpAuthorization:
  rules:
    - 'mcp.tool.target == "public-tools"'                                    # anyone authed
    - 'mcp.tool.target == "admin-tools" && has(jwt.sub) && "admin" in jwt.roles'
    - 'mcp.tool.name == "add_issue_comment" && jwt.sub == "alice"'
    - 'mcp.tool.name == "echo" && has(jwt.sub)'                               # echo for all authed
```

CEL variables available: `mcp.tool.name`, `mcp.tool.target`, `mcp.tool.arguments` (post-request), `mcp.methodName` (`tools/list` vs `tools/call`), `jwt.sub`, `jwt.roles`, `jwt.<claim>`.

Keycloak mapping (MCP 2025-03-26 supported today; 2025-06-18+ needs `--features=cimd,resource-indicators`):
- Start Keycloak: `kc.sh start --features=cimd,resource-indicators`
- Each MCP server = separate Keycloak client (never share one app registration across servers — else `aud` check is meaningless).
- Store per-tool permission as client roles; mint signed “wristband” JWT (`x-authorized-tools` header) for identity-based tool filtering on `tools/list` — users only *see* tools they can call (least privilege + no confusion).

Solo.io hardening checklist:
- Strict auth by default (reject unauthenticated unless explicitly permissive).
- Per-request policy evaluation (no stale sessions).
- Registration catalog: fingerprint + version + sign every tool description; gateway verifies signature on `tools/list` → blocks tool poisoning / rug-pulls / shadowing / name collisions.
- Sanitize tool descriptions (strip directives, length-limit) + centralized audit log (who called what with what args).

---

## 4. `${ENV}` Secret Handling

From Cite-Before-Act two-tier config (do this exactly):

| Layer | Lives in | Contains | Committed? |
|---|---|---|---|
| `.env` (global defaults) | project root, `python-dotenv` loaded via absolute path | `GITHUB_PAT`, `SLACK_BOT_TOKEN`, `KEYCLOAK_ISSUER`, `APPROVAL_TIMEOUT_SECONDS`, detection defaults | **NEVER** (`.gitignore` + `.env.example` only) |
| MCP client config | Claude Desktop / inspector JSON | `UPSTREAM_COMMAND`, per-server `DETECTION_ALLOWLIST/BLOCKLIST`, `${input:...}` refs | Yes, but secrets as refs only |

Rules:
```json
{
  "env": {
    "UPSTREAM_HEADER_Authorization": "Bearer ${input:github_mcp_pat}",
    "DETECTION_ENABLE_CONVENTION": "true"
  }
}
```
- `load_dotenv()` must NOT override real env vars → per-server config wins, `.env` is fallback.
- No secret in logs / previews / audit UI — redact with `SECRET_RE = re.compile(r'(ghp_|xoxb-|sk-)[\w-]+')`.
- DuckDB lesson from Blackbox: a naive `SELECT`-only check still exposes local files (`read_csv`, `pragma_*`). Enforce at connection layer: disable file access, pin read-only mode, block `COPY ... TO/FROM`, `ATTACH`, `LOAD`.
- Demo safety: `--read-only` flag on upstream server for rehearsals; `--lockdown-mode` to limit to non-public content.

---

## 5. Idempotency (anti-double-execute)

Judges *will* retry / double-click Approve. Every mutating tool:

```python
def execute_write(*, idempotency_key: str, approval_token: str, ...):
    if seen(idempotency_key):
        return {"status": "duplicate", "original_result": fetch(idempotency_key)}  # no re-execute
    verify(approval_token, scope=idempotency_key)  # token bound to exact preview hash
    with transaction():
        result = mutate(...)
        store(idempotency_key, result, preview_hash)
    return result
```

- Key = `uuid4` generated at dry-run, echoed in preview, reused on execute.
- Approval token bound to `hash(preview)` — if args changed post-approval, token invalid → force new dry-run.
- Store keys durably (sqlite table `idempotency(key PK, preview_hash, result_json, ts)`), TTL 24h.
- Return `duplicate:true` on replay, never re-mutate. Show this in demo: click Approve twice → second returns cached result.

---

## 6. Evidence-Gate Checklist (Blackbox pattern)

Steal Blackbox's `confirm_root_cause` gate verbatim. Three object kinds (mirror in `types.ts` + backend):

- **Fact** (`EvidenceItem`): only deterministic tool code creates it. Fields: `id`, `kind` (metadata/profile/baseline_comparison/sql/lineage/test/patch/writeback), `source` (datahub/warehouse/pipeline/git), raw output. **Never free-typed by LLM.**
- **Hypothesis**: LLM via `record_hypothesis`, must target a DataHub URN / asset+field. Confirm/eliminate requires citing valid `evidence_ids` — tool rejects otherwise.
- **Action** (patch/writeback): gated by state (`no repair without confirmed root cause`), verified by re-execution.

`confirm_root_cause` rejects unless citations include ALL:
- [ ] ≥1 **DataHub lineage or metadata** evidence (proves topology, not file-reading)
- [ ] ≥1 **quantitative** evidence (profile diff, SQL count, baseline comparison)
- [ ] Evidence **references the exact asset + field blamed** (anti-hallucination: citing wrong URN = reject)
- [ ] `NO_INCIDENT` is itself gated (healthy-fixture control must not invent incident)
- [ ] Repair scoped to allowlist (`pipeline/transforms/*.sql`); revert on failed verification; git branch `blackbox/fix-*`; remote PR only after `VERIFIED`; DataHub marked resolved only after KPI check passes

Acceptance harness to demo (Blackbox `ACCEPTANCE.md` — 22 gates, commit results):
`positive_incident` (finds `raw.raw_orders.amount`, 32/32 green, KPI 93.3×→0.93×) + `control_no_incident` + `bad_repair_rejected` (blanket `/100` patch must FAIL historical-immutability invariants) + `datahub_ablation` (`BLACKBOX_DISABLE_DATAHUB=true` → still diagnoses on 5-transform fixture but loses topology map, contract proof, citations, writeback — report honestly).

---

## 7. Minimal Track-2 Safety Scaffold (copy-paste)

```
server/
  main.py            # MCPServer + AuthSettings + TokenVerifier
  tools_read.py      # read:all — no gate
  tools_write.py     # write:all — dry_run + idempotency_key + approval_token + evidence gate
  detection.py       # is_mutating(name, meta) — fail-closed
  explain.py         # preview_diff(before, after, blast_radius)
  approval.py        # request/approve/reject + timeout + audit append
  evidence.py        # EvidenceItem, record_hypothesis, confirm_root_cause
  audit.jsonl        # append-only: ts, sub, tool, args_hash, preview_hash, evidence_ids, decision
.env.example         # keys only, no values
evals/
  positive_incident.json / control_no_incident.json / bad_repair_rejected.json
```

Audit entry schema: `{ts, actor_jwt_sub, tool, args_hash, preview, evidence_ids[], approval_token, idempotency_key, result, verify_suite}`.

---

## 8. Sources
- Cite-Before-Act: `MCP-1st-Birthday/cite-before-act-mcp` (HuggingFace Space + `bisonbet/Cite-Before-Act-MCP` GitHub) — middleware, detection, approval, `.env` two-tier config, GitHub example.
- Keycloak as MCP authz server: `keycloak.org/securing-apps/mcp-authz-server` + Red Hat `Securing Applications Guide Ch.12`; MCP spec versions 2025-03-26 (Supported) → 2026-07-28 (Experimental, needs CIMD + resource-indicators).
- CEL/JWT tool access: `agentgateway.dev/docs/.../mcp/tool-access`, `/mcp/mcp-access`, `/mcp/auth/setup`; Solo `docs.solo.io/agentgateway/.../security/mcp-authz`.
- Blackbox: `alejandro-publius/blackbox-datahub` (`docs/ARCHITECTURE.md`, `ACCEPTANCE.md`, `DEMO_SCRIPT.md`, `evals/README.md`) + DataHub blog “Meet the 2026 Winners”.
- Solo.io governance: `solo.io/products/agentgateway`, `solo.io/blog/prevent-mcp-tool-poisoning-with-registration-workflow`, `solo.io/blog/agentgateway-mcp-authentication-multi-provider-ai`.
- Context7: `tools.context7 query-docs /modelcontextprotocol/modelcontextprotocol` — Python `JWTTokenVerifier + MCPServer(AuthSettings)` pattern.
