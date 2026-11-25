# 48 — Fast-Fix Playbook: Mid-Build Stucks

> 60-second triage for the 12 most common build stalls. Pattern: **Symptom → Cause → 1-Line Fix → Verify.**

## Quick Index

| # | Stuck | Fix in 5 words |
|---|-------|----------------|
| 1 | Not Initialized | Init config before calling |
| 2 | Quota Exceeded | Check usage, switch key |
| 3 | AUTH_INVALID | Re-export valid API key |
| 4 | Endpoint Selection Required | Set explicit model endpoint |
| 5 | no emit_tool_plan | Force plan before tools |
| 6 | SERVER_ERROR | Retry + pin stable version |
| 7 | surface_cache stale | Clear cache, re-fetch |
| 8 | operation_id collision | Uniquify operationId |
| 9 | .js invisible | Fix glob / include pattern |
| 10 | Weak model | Upgrade to strong model |
| 11 | npx runner fetch fail | Pin version, clear npx cache |
| 12 | Claude restart vs Cursor refresh | Know which to reboot |

---

### 1. Not Initialized
- **Symptom:** `Error: client not initialized` / `null config` on first call, everything else looks correct.
- **Cause:** SDK/client used before `init()` / env load completes; async init race.
- **Fix:** Call and await `init()` (load env + config) before any client call.
- **Verify:** `node -e "await init(); console.log(client.isReady())" # expect true`

### 2. Quota Exceeded
- **Symptom:** `429 / quota_exceeded / rate_limit_exceeded`, builds halt mid-run.
- **Cause:** Token/RPM/TPM budget hit on current key or tier.
- **Fix:** Check usage dashboard, then rotate key or lower `max_tokens` / concurrency.
- **Verify:** `curl -s https://api.provider.com/v1/usage -H "Authorization: Bearer $KEY" | head -c 500`

### 3. AUTH_INVALID
- **Symptom:** `401 AUTH_INVALID / invalid_api_key / incorrect key prefix`.
- **Cause:** Expired, revoked, mistyped, or wrong-project key; `OPENAI_API_KEY` not exported in this shell.
- **Fix:** Re-copy key from dashboard and `export` it fresh in current terminal.
- **Verify:** `echo ${#API_KEY} && curl -s -o /dev/null -w "%{http_code}" https://api.provider.com/v1/models -H "Authorization: Bearer $API_KEY" # expect 200`

### 4. Endpoint Selection Required
- **Symptom:** `400 endpoint_selection_required / model_not_deployed / specify deployment`.
- **Cause:** Gateway (Azure / proxy / multi-model router) doesn't know which deployment to route to.
- **Fix:** Set explicit `model` / `deployment` / `endpoint` param in the request config.
- **Verify:** `grep -rn "model.*deployment\|endpoint" config/ | head -5 # expect explicit value, not empty`

### 5. no emit_tool_plan
- **Symptom:** Agent fires tools with no plan, loops or calls tools out of order.
- **Cause:** Planner step skipped; system prompt doesn't force `emit_tool_plan` before tool use.
- **Fix:** Require plan-first: force `emit_tool_plan` call before any tool invocation.
- **Verify:** `grep -rn "emit_tool_plan" logs/ | head -3 # expect plan entry before first tool_call`

### 6. SERVER_ERROR
- **Symptom:** `500 / 502 / 503 SERVER_ERROR`, intermittent, retry sometimes works.
- **Cause:** Provider-side overload or pinned preview/beta model version flapping.
- **Fix:** Exponential-backoff retry (3x) and pin to a stable model version.
- **Verify:** `for i in 1 2 3; do curl -s -o /dev/null -w "%{http_code}\n" https://api.provider.com/v1/health; sleep 2; done # expect 200s`

### 7. surface_cache Stale
- **Symptom:** Old schema / stale completions served after you changed prompt or spec.
- **Cause:** Cached surface (prompt cache / disk cache / CDN) not invalidated on change.
- **Fix:** Bust it: clear cache dir and re-fetch with `cache: false` once.
- **Verify:** `rm -rf .cache/surface_cache && npm run build -- --no-cache && echo FRESH`

### 8. operation_id Collision
- **Symptom:** `operation_id collision / duplicate operationId` on OpenAPI build or codegen overwrite.
- **Cause:** Two routes share the same `operationId`; codegen emits one function over the other.
- **Fix:** Rename to unique `{verb}{Resource}` operationIds across the spec.
- **Verify:** `grep -rhoP "operationId:\s*\K.*" api/ | sort | uniq -d # expect no output`

### 9. .js Invisible
- **Symptom:** `.js` files exist on disk but bundler/linter acts like they're missing.
- **Cause:** `glob` / `tsconfig.include` / `.gitignore` excludes `*.js` (e.g. `allowJs: false`).
- **Fix:** Add `*.js` to include: set `allowJs: true` or fix glob to `**/*.{ts,js}`.
- **Verify:** `npx tsc --showConfig | grep -A5 include && ls src/**/*.js # expect files listed`

### 10. Weak Model
- **Symptom:** Loops, hallucinates APIs, ignores tool schema on complex tasks.
- **Cause:** Small/fast model assigned to a reasoning-heavy step.
- **Fix:** Upgrade that step to a strong model (e.g. Sonnet/Opus-class) and keep weak model for boilerplate.
- **Verify:** `grep -rn "model" agents/*.yaml | head -10 # expect strong model on planner/coder`

### 11. npx Runner Fetch Fail
- **Symptom:** `npx: fetch failed / ENOTFOUND / ETIMEDOUT` when scaffolding or running a tool.
- **Cause:** Stale npx cache, unpinned `latest` tag, or offline registry/proxy.
- **Fix:** Clear npx cache and pin version: `npx --yes pkg@x.y.z`.
- **Verify:** `npx --yes clear-npx-cache && npm ping && npx --yes cowsay@1.6.0 hi # expect OK + hi`

### 12. Claude Restart vs Cursor Refresh
- **Symptom:** Stale MCP tools / hung agent after config change; unsure what to reboot.
- **Cause:** Config change needs full process restart (Claude) vs UI-only reload (Cursor).
- **Fix:** MCP/config/key change → full Claude restart; prompt/file-only change → Cursor window reload.
- **Verify:** `Cursor: Cmd+Shift+P → "Reload Window"; Claude Desktop: Quit → reopen → Tools list shows new MCP`
