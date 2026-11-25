# 07 — External Freshness Cross-Check (Pinned Stack)

**Date (UTC):** 2026-11-24
**Checked-by:** Explorer subagent
**Method:** `execute search()` tool discovery → no searxng/firecrawl servers found; only `context7/query-docs`, `gh_grep`, `opencode/*` available → fell back to `default.websearch` (8 queries) + `default.webfetch` (PyPI JSON ×2, npm registry JSON, FastAPI release notes, FastMCP changelog). 13 lookups total.

## Version table (pin vs latest, 2026-11-24)

| Package | Pinned | Latest verified | Source | Drift? |
|---|---|---|---|---|
| `fastapi` (PyPI) | 0.165.0 | **0.165.0** (2026-11-18) | `https://pypi.org/pypi/fastapi/json` → `info.version: 0.165.0`, `release_url: .../0.165.0/` | ✅ **None — pin is latest** |
| `fastmcp` (PyPI) | 4.2.4 | **4.2.5** (2026-11-23) | `https://pypi.org/pypi/fastmcp/json` → `info.version: 4.2.5`; `gofastmcp.com/docs/changelog` + GitHub releases | ⚠️ **1 patch behind** |
| `@2ndbrainlabs-ai/synapse-cli` (npm) | 0.1.9 | **0.1.9** (`dist-tags.latest: 0.1.9`, 2026-11-09) | `https://registry.npmjs.org/@2ndbrainlabs-ai%2Fsynapse-cli` → `time.0.1.9: 2026-11-09` | ✅ **None — pin is latest** |
| Ollama model `qwen3:4b` | qwen3:4b | **Available** in Ollama library (`ollama.com/library/qwen3:4b`, registry `qwen3:4b`) | websearch + `ollama.com/library/qwen3` | ✅ **Exists; no rename** |

Requires-Python / runtime floors (from registry metadata):
- `fastapi 0.165.0` → `requires_python >=3.11` (classifiers list 3.11–3.15).
- `fastmcp 4.2.5` → `requires_python >=3.11` (3.11–3.15 supported; 3.10 capped at 4.1.8).
- `synapse-cli 0.1.9` → `engines.node >=20` (was `>=18` through 0.1.8). **Runbook must state Node 20+.**

## fastapi 0.165.0 — no action

- Pin equals latest; no upgrade available.
- Release-notes reviewed back to 0.162.x: recent breaking changes were in **0.162.6, 0.162.0, 0.160.0, 0.155.0, 0.151.0–0.145.0, 0.143.0** (per `fastapi.tiangolo.com/release-notes/` TOC). None post-date 0.165.0, so nothing since the pin.
- `requires_dist`: `starlette>=1.6.0`, `pydantic>=2.9.0`. Plan's `pip install fastapi==0.165.0` remains valid. No flag changes (library, not CLI).

## fastmcp 4.2.4 → 4.2.5 — patch drift (review before bumping)

**Should we bump?** Optional. 4.2.4 is 3 days old (2026-11-20); 4.2.5 (2026-11-23, "Smoke Signals") is mostly additive + security hardening. Staying pinned is safe; bumping gets OAuth/OpenAPI fixes but opts into a new default listener.

**What changes in 4.2.5 (from `gofastmcp.com/docs/changelog`, `v4.2.4...v4.2.5`):**
1. **`subscriptions/listen` ON by default** on 2026-07-28 connections. Servers now advertise `listChanged` + `resources.subscribe`; clients hold one open stream/connection. Limits: 1024 open listen streams per process; extra get an error. Multi-worker/replica: `notify_*` only reaches listeners on the same process.
   - **Plan impact:** serverless / capped-worker / per-connection-billed hosts should opt out: `FASTMCP_ENABLE_SUBSCRIPTIONS_LISTEN=false` (env, before `import fastmcp`) or `fastmcp.settings.enable_subscriptions_listen = False`. Opted-out server behaves exactly like 4.2.4 (`listChanged=false`, `subscriptions/listen → -32601`, `notify_*` no-op). Handshake-era (≤2025-11-25) unaffected.
2. **New opt-ins:** `UsageMiddleware` (OTel `mcp.server.operation.duration` histogram for `tools/call`, `prompts/get`); experimental Events extension `fastmcp.experimental.events` (`events list|watch`) — API may break any time, do not pin runbook on it.
3. **Security hardening (may break strict setups):**
   - CIMD clients: must set `valid_scopes` or they get no scopes (previously could widen scopes).
   - Redirect-URI validation: exact patterns now match query strings and reject fragments; root exact pattern (e.g. `https://app.example/`) matches only that path — append `/*` for subtree.
   - Refresh-token rotation: presenting a token >60s after rotation ends the whole grant (suspected theft); revoking a refresh token now also ends that grant's access tokens. Multi-process clients sharing one stored refresh token must share the rotated value.
   - `OAuthProxy`/`OIDCProxy`: new `client_registration_ttl_seconds` (default off); `AzureProvider` multi-tenant (`organizations/consumers/common`) no longer checks issuer unless `token_issuer` set; proxy backends now see only the real client's roots/sampling/elicitation support.
4. **OpenAPI:** transport headers (`mcp-protocol-version` etc.) no longer forwarded to wrapped API; new `forward_client_headers` on `FastMCP.from_openapi / from_fastapi / OpenAPIProvider` (`False` = none, or list of names). Cookie param values now percent-encoded — backends parsing `;`/space/non-ASCII cookies must decode.
5. **Fixes worth having:** OAuth proxy concurrent code/refresh redemption race (GHSA-78c8-3jhx-5mg7, actually in 4.2.4), revoked access token staying revoked after refresh, tool-transform isolation, schema/`$ref` fixes.

**No** constructor/kwarg, decorator, `ctx.*`, or repo-location breaks in 4.2.4→4.2.5 (those were v2→v3/v4 migrations). `pip install fastmcp==4.2.4` still resolves.

## synapse-cli 0.1.9 — pin is latest, but runbook flags changed since 0.1.9-era docs

Registry (`registry.npmjs.org`) confirms `latest = 0.1.9` (published 2026-11-09T12:18:45Z). History: 0.1.5 (2026-09-03) → 0.1.6/0.1.7/0.1.8 (2026-11-01/02) → 0.1.9. **Do not use `0.1.4-re-2` / `0.1.5` install strings if they appear in plan.md — update to `npm install -g @2ndbrainlabs-ai/synapse-cli` (resolves to 0.1.9).**

Flag / behavior drifts that **invalidate old runbook commands** (from current README / `synapse-cli-ts` docs):
- **Node `>=20` required** (`npmjs` page + registry `engines`). Old `Node 18+` text is stale. `synapse --version` check stays valid.
- **v1 engine removed; v2 only.** `synapse build` without `--engine`. `--engine v2` still accepted; `--engine v1` exits non-zero with "v1 engine removed".
- **Removed v1 flags now fatal:** `-o/--output`, `--no-validate`, `--no-docs`, `-g/--generate` exit non-zero on v2 builds (previously ignored). Remove them from any copied commands; v2 names its own output (`<tool_name>_server.py`, or `synapse_auto_server.py` for `--local --auto` on Python).
- **Current valid build flags:** `synapse build [--auto|--custom] [-q/--query] [--smart-names] [--local] [--resume] [--discover] [--all-endpoints|--endpoints "…"] [--server-name] [--new]`. Non-terminal/CI must pass `--all-endpoints` or `--endpoints`; otherwise the build stops with "Endpoint Selection Required".
- `synapse analyze`, `synapse init`, `synapse info`, `synapse config*`, `synapse model*`, `synapse update` unchanged. `--local` provider matrix now includes `ollama` (`http://localhost:11434/v1`, no key, JSON-mode fallback since Ollama documents `tool_choice` as unsupported — small models may fail with `returned no emit_tool_plan call`; use a stronger model).

## Ollama `qwen3:4b` — available

- `ollama.com/library/qwen3:4b` + registry page resolve (Qwen3 family: 0.6b/1.7b/4b/8b/14b/30b/32b/235b; tools + thinking variants, ~256K context per roundups).
- `ollama pull qwen3:4b` / `ollama run qwen3:4b` valid. No rename to `qwen3.5`/`qwen3.6` needed, though newer Qwen3.5/3.6/3.8 families exist — pin stays reproducible.
- Note for `--local ollama` path: Synapse sends `response_format: json_object` + inlined schema instead of forced tool call; codegen quality depends on model holding strict schema (see above).

## Drift flags vs plan.md commands

| # | Check | Verdict |
|---|---|---|
| 1 | `pip install fastapi==0.165.0` | ✅ Keep — is latest |
| 2 | `pip install fastmcp==4.2.4` | ✅ Keep (reproducible); ⚠️ optional bump to 4.2.5 — if bumping, add listen-stream opt-out note for serverless/capped hosts and review OAuth/redirect-URI + `forward_client_headers` + cookie-decode points |
| 3 | `npm install -g @2ndbrainlabs-ai/synapse-cli` (expect 0.1.9) | ✅ Keep; ✏️ ensure no `--engine v1`, `-o`, `--no-validate`, `--no-docs`, `-g` flags remain; ensure Node 20+ prerequisite; use `--all-endpoints`/`--endpoints` in CI |
| 4 | `ollama pull/run qwen3:4b` | ✅ Keep — model exists |

**Bottom line:** No pinned version is stale except a 1-day-old `fastmcp` patch (safe to defer). The only plan.md invalidators are stale `synapse` v1 flags and the Node 18→20 floor.
