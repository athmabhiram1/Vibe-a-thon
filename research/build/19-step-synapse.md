# 19 — Step-by-Step Synapse Commands (HR-API then IT, Exact Order)

**CLI:** `@2ndbrainlabs-ai/synapse-cli` `0.1.9` (2026-11-09) · **Node ≥ 20** · **Repo:** `2ndbrainlabs-ai/synapse-cli-ts`
**Sources:** [CLI README](https://github.com/2ndbrainlabs-ai/synapse-cli-ts) (authoritative — docs site is stale v1), [Getting started](https://synapse.2ndbrainlabs.ai/docs), prior notes `03-synapse-technical.md`, `final/04-synapse-auto.md`.
**Scope:** exact copy-paste runbook — install → version → init → build hr-api → build it-api (`--new`) → `info` quota → verify tools. With expected outputs + 3 error fixes.

---

## 0. Pre-reqs

```bash
node --version   # must be v20+. If v18: nvm install 20 && nvm use 20
```

FastAPI services exist and use literal decorators + unique `operation_id` (see `final/04-synapse-auto.md`). Example layout:

```
track3/
  hr_api.py          # FastAPI(title="HR API"), :8001, operation_id hr_*
  it_api.py          # FastAPI(title="IT API"), :8002, operation_id it_*
  requirements.txt   # fastapi, uvicorn, pydantic
```

---

## Step 1 — Install CLI globally

```bash
npm i -g @2ndbrainlabs-ai/synapse-cli
```

**Expected:**

```
added 1 package in ~5s
```

**Fixes:**
- `EACCES permission denied` (Windows/macOS): re-run terminal as Admin, or `npm config set prefix ~/.npm-global` + add to PATH. Do not use `sudo npm` habitually.
- `EBADENGINE Unsupported engine`: upgrade Node to 20+ (see Step 0).
- Stale version: `synapse update` or `npm i -g @2ndbrainlabs-ai/synapse-cli@latest`.

---

## Step 2 — Verify version

```bash
synapse --version
```

**Expected:**

```
0.1.9
```

If it prints `0.1.x < 0.1.9`, run `synapse update`. If `command not found`, reopen terminal (PATH refresh) and check `npm root -g`.

---

## Step 3 — One-time init (per project)

```bash
cd track3
synapse init
```

**What happens:** prompts `Paste your Synapse API key:` (get it at `https://synapse.2ndbrainlabs.ai` console → API keys). Validates against backend, writes `.synapse/config.json`.

**Expected:**

```
✓ Synapse initialized
  Server: hr-api (default: folder name)
  Config: .synapse/config.json
```

Run `synapse init --force` to re-init. `synapse init` is **not** needed for `--local` builds.

---

## Step 4 — Build server #1: HR-API (all endpoints)

```bash
synapse build --auto --all-endpoints --server-name hr-api
```

**What happens:**
1. Scan (local tree-sitter) → endpoint picker skipped because `--all-endpoints` given.
2. Hosted generate → endpoint config saved to Synapse account.
3. Prints MCP client snippet with `SYNAPSE_SERVER_ID`.

**Expected:**

```
Discovered 5 endpoint(s)
✓ Server hr-api updated (id: srv_xxxx)
# paste into claude_desktop_config.json:
{"command":"npx","args":["-y","@2ndbrainlabs-ai/synapse-mcp"],
 "env":{"SYNAPSE_API_KEY":"…","SYNAPSE_SERVER_ID":"srv_xxxx",
         "SYNAPSE_API_URL":"https://api.synapse.2ndbrainlabs.ai",
         "ENDPOINT_BASE_URL":"http://localhost:8001"}}
```

Set `ENDPOINT_BASE_URL=http://localhost:8001` (HR) in the client env, otherwise every hosted Auto tool call 404s — Synapse proxies, it does not host your API.

---

## Step 5 — Build server #2: IT (new server in same repo)

```bash
synapse build --auto --all-endpoints --server-name it-api --new
```

**Why `--new`:** without it, rebuilds update the *same* server id recorded in `.synapse/config.json`. `--new` forks a second server; later builds update the newest one. `--server-name <name>` picks by name (default: folder name).

**Expected:**

```
Discovered 6 endpoint(s)
✓ Server it-api created (id: srv_yyyy) — update SYNAPSE_SERVER_ID
```

Wire second client entry with `ENDPOINT_BASE_URL=http://localhost:8002`. Verify both APIs running:

```bash
uvicorn hr_api:app --port 8001
uvicorn it_api:app --port 8002
```

**Live-update variant (demo moment):** after adding a route, always rescan — builds reuse `.synapse/surface_cache.json`:

```bash
synapse build --discover --auto --all-endpoints --server-name hr-api
# expected: "Using the endpoints discovered on …" replaced by fresh scan; new tool appears, same server id
```

Optional better names: append `--smart-names` (sends handler source ≤3000 chars + README ≤6000 chars to model).

---

## Step 6 — Quota / project check

```bash
synapse info
```

**Expected:**

```
Project: track3
Servers: 2/10 used
Indexed lines: ~1,200/100,000 used
```

Free tier = **10 MCP servers, 100,000 indexed lines**. Rebuilds of unchanged repos cost ~nothing (delta-only). `--local` builds never count. `synapse analyze` also reports indexed lines (Python-only).

---

## Step 7 — Verify tools ("list-tools grep")

> ⚠️ `synapse list-tools` **does not exist** in CLI 0.1.9. README `#commands` lists only: `init, build, analyze, config, model, info, update, uninstall`. There is no `list-tools` / `list-endpoints` subcommand.

Use these equivalents instead:

```bash
synapse info                  # servers + indexed lines
synapse config                # key source (redacted), project, endpoints, local provider
cat .synapse/config.json      # server id + server-name mapping
cat .synapse/surface_cache.json | grep -i "operation\|path\|method"
```

**Expected `config`:**

```
API key: sk_…abcd (env SYNAPSE_API_KEY)
Project: track3
Endpoints: 11 (hr-api: 5, it-api: 6)
```

**Grep check (PowerShell):**

```powershell
Select-String -Path .synapse/surface_cache.json -Pattern "operation_id|list_employees|list_tickets"
```

Every `operationId` in `localhost:8001/openapi.json` should appear here; any gap = dynamic-route / `include_in_schema=False` / missing `include_router` anti-pattern (see `04-synapse-auto.md` §5).

---

## Error-fix table (the 3 requested + 2 bonus)

| Message | Cause | Fix |
|---|---|---|
| `Endpoint Selection Required` | No TTY (CI/pipe) + neither `--all-endpoints` nor `--endpoints` passed; CLI refuses to expose nothing | Add `--all-endpoints`, or `synapse build --auto --endpoints "GET /employees,POST /employees"` (also accepts `/path` or `operation_id`). Either flag implies `--auto`. |
| `Your Synapse API key is invalid or expired [AUTH_INVALID]` | Bad/revoked key, or `SYNAPSE_API_KEY` override shadowing saved key | `synapse config set-key` (masked prompt, keeps out of history) or set `SYNAPSE_API_KEY`. Check source with `synapse config`. Rotate: console → new key → `set-key` → `config keys` → `config revoke <old-id>`. |
| `Quota Exceeded` | >10 servers or >100k indexed lines | `synapse info` to confirm. Rebuild existing (`--server-name hr-api`, no `--new`) instead of forking; delete unused server in console; or switch demo leg to `synapse build --local` (no quota, Python-only file `synapse_auto_server.py`). |
| `Not Initialized` on `build` | `synapse init` never run in this folder | `synapse init` (or one-shot `synapse build --local --llm-api-key …` for local-only). |
| `v1 engine removed` / `Option removed` | Copied stale flags (`--query` is Custom-only `-q`, `--output/--no-validate/--no-docs/--engine v1`, `synapse status`) from docs site | Drop v1 flags; use `synapse build [--auto\|--custom] [-q <query>] [--smart-names] [--local] [--resume] [--discover]`. `--engine v2` still accepted. |

General: `synapse build` exits non-zero on any unfinished build (bad key, backend down, scan paused by `--max-time`/Ctrl-C → resume with `--resume`; quote `Session:` id in issues). Add `--dev` to hit `localhost:50051` backend.

---

## Full copy-paste block

```bash
npm i -g @2ndbrainlabs-ai/synapse-cli
synapse --version
cd track3
synapse init
synapse build --auto --all-endpoints --server-name hr-api
synapse build --auto --all-endpoints --server-name it-api --new
synapse info
synapse config
```

## Doc URLs

- CLI README (flags, cache, rebuild, quota, troubleshooting): https://github.com/2ndbrainlabs-ai/synapse-cli-ts
- Getting started: https://synapse.2ndbrainlabs.ai/docs
- API reference: https://synapse.2ndbrainlabs.ai/docs/api
- Examples: https://github.com/2ndbrainlabs-ai/synapse-examples
