# 20 — Public-URL Gap Verification (ngrok share mirror)

**Date (UTC):** 2026-11-24 | **Runner:** subagent (public-URL gap) | **Scope:** hosted Synapse MCP tools forward to `ENDPOINT_BASE_URL=localhost` — dies for any off-machine judge
**Verdict:** ☒ **BLOCKED** — ngrok binary present, credentials absent. No tunnel started, no rebuild, no remote-curl proof. Nothing below is invented.

## 1. Problem statement

Hosted Synapse Auto tools are dumb HTTP forwards: the `npx @2ndbrainlabs-ai/synapse-mcp` runner calls `ENDPOINT_BASE_URL` live at tool-call time (see `research/03-synapse-technical.md:56`, `research/build/19-step-synapse.md:105`). Both client entries currently point at `http://localhost:8001` / `:8002` (`.env:1-6`, `research/build/19-step-synapse.md:100-102`). A judge on another machine resolves `localhost` to *their own* machine → every tool call fails. Fix = public tunnel URLs + runner/client env repointed (+ rebuild per task, same server IDs) + remote-curl proof.

## 2. What was actually checked (executed, not assumed)

| Check | Result |
|---|---|
| `ngrok version` | ✅ `3.39.11-msix-stable` at `C:\Users\athma\AppData\Local\Microsoft\WindowsApps\ngrok.exe` — **binary present** |
| `$env:NGROK_AUTHTOKEN` | ❌ **empty/absent** (length 0) |
| `.env` NGROK lines | ❌ **none** — only `HR/IT/ENDPOINT_BASE_URL` localhost lines (`.env:1-6`) |
| `config/ngrok.yml` | ❌ **does not exist** (`Test-Path` False). Repo has root `ngrok.yml` only, with unresolved `$NGROK_AUTHTOKEN` / `$NGROK_DOMAIN_HR` / `$NGROK_DOMAIN_IT` placeholders |
| Agent config `%LOCALAPPDATA%\ngrok\ngrok.yml` | ❌ **missing** (`GetFileAttributesEx … cannot find the path`) |
| `$env:NGROK_DOMAIN*` | ❌ all empty — no reserved dev domain wired anywhere |
| `ngrok http 8001 --log stdout` (live attempt) | ❌ **`ERR_NGROK_4018` — "authentication failed: This ngrok session is not authenticated"**, session closed. Tunneling is impossible without an authtoken |
| Local APIs (primary path) | ✅ `http://localhost:8001/health` → 200, `http://localhost:8002/health` → 200 — localhost demo unaffected; **only the public mirror is blocked** |
| Synapse state (for the rebuild step) | CLI `0.1.9` present; `.synapse/config.json` holds `hr-api 6269969f-…` + `it-api 5fe96a56-…`; quota `2/10 servers, 775/100.0K` (`evidence/quota-log.md:20-24`). Rebuilds are quota-free (surface-cache reuse) but were **not run — no public URLs exist to rebuild against** |

## 3. Not done (blocked, deliberately)

- [ ] `ngrok http 8001` + `ngrok http 8002` (or `ngrok start --config ngrok.yml hr it`) — needs authtoken
- [ ] Rebuilds with public base URLs (same IDs) — needs tunnel URLs first
- [ ] Remote curl from off-machine / phone hotspot — needs tunnels up
- [ ] `evidence/quota-log.md` append — nothing to log yet (no `synapse info` before/after run)

## 4. Exact user runbook (do in order)

**Step 0 — services already up?** If not: boot APIs (`./scripts/up.sh local` on Git Bash, or `uvicorn hr_service.main:app --port 8001` + `uvicorn it_service.main:app --port 8002`), confirm `curl http://localhost:8001/health` and `:8002/health` → 200.

**Step 1 — install (already done on this laptop, skip unless new machine):** `ngrok version` → expect `3.39.11`. Otherwise install from `https://ngrok.com/download` (or `winget install ngrok`).

**Step 2 — authtoken (one time):**
1. Sign up: `https://dashboard.ngrok.com/signup` → copy authtoken: `https://dashboard.ngrok.com/get-started/your-authtoken`
2. Save it (pick ONE — never paste the token into chat/files):
   - `ngrok config add-authtoken` (interactive, writes `%LOCALAPPDATA%\ngrok\ngrok.yml`), **or**
   - `$env:NGROK_AUTHTOKEN="<paste>"` (session-only; add to `.env` — already gitignored — for persistence)
3. (Optional, stable URLs) Reserve **1 free dev domain**: `https://dashboard.ngrok.com/domains` → set `$env:NGROK_DOMAIN` (single-domain) or `$env:NGROK_DOMAIN_HR` + `$env:NGROK_DOMAIN_IT` (two domains).

**Step 3 — open tunnels (keep these terminals running):**
- Single free domain: `ngrok http 8001 --domain="$NGROK_DOMAIN"` (hr mirror; it stays localhost), or scripted: `NGROK_DOMAIN=<domain> ./scripts/share.sh single`
- Two domains: `ngrok start --config ngrok.yml hr it` (needs `NGROK_AUTHTOKEN`, `NGROK_DOMAIN_HR`, `NGROK_DOMAIN_IT` exported first), or `NGROK_DOMAIN_HR=… NGROK_DOMAIN_IT=… ./scripts/share.sh both`
- No reserved domain: `ngrok http 8001` and (second terminal) `ngrok http 8002` — use the random `https://*.ngrok-free.app` URLs ngrok prints. **Copy both `https://…` URLs.**

**Step 4 — rebuild both Synapse servers against public base URLs (same IDs — NEVER `--new` again or you fork server #3 and burn quota):**
```powershell
$env:SYNAPSE_API_KEY = (Select-String '^SYNAPSE_API_KEY=(.+)' .env).Matches[0].Groups[1].Value  # session only, never echo
synapse info   # BEFORE → evidence/quota-log.md
$env:ENDPOINT_BASE_URL = "https://<HR-NGROK-URL>"
synapse build --auto --endpoints "GET /candidates,GET /candidates/{candidate_id},POST /employees,GET /shifts,GET /oncall,GET /equipment,POST /equipment/assign,POST /tickets,GET /tickets/breaches,GET /tickets/{ticket_id},POST /tickets/{ticket_id}/reroute,hr_health_check,it_health_check" --server-name hr-api
$env:ENDPOINT_BASE_URL = "https://<IT-NGROK-URL>"
synapse build --auto --endpoints "GET /candidates,GET /candidates/{candidate_id},POST /employees,GET /shifts,GET /oncall,GET /equipment,POST /equipment/assign,POST /tickets,GET /tickets/breaches,GET /tickets/{ticket_id},POST /tickets/{ticket_id}/reroute,hr_health_check,it_health_check" --server-name it-api
synapse info   # AFTER → evidence/quota-log.md (expect servers still 2/10, lines still 775/100K)
```
Expect `same server id` on both builds; assert 13 tools each via Inspector `tools/list` (see `research/verify-final/12-synapse-run.md:§3`). Allowlist is the 13-tool baseline from `12-synapse-run.md:29` (11 functional paths + 2 health checks; `GET /oncall-coverage` only after the live `--discover` moment).

**Step 5 — repoint clients** (runner reads `ENDPOINT_BASE_URL` at call time — skip this and tools still hit localhost): set `ENDPOINT_BASE_URL=https://<HR-NGROK-URL>` on the `hr-api` entry and `https://<IT-NGROK-URL>` on `it-api` in `.cursor/mcp.json` + `claude_desktop_config.json` (+ bump `MCP_REV` if you want hot-reload), then restart the MCP clients.

**Step 6 — re-verify (proof required):** from an OFF-machine network (phone hotspot / second machine):
```bash
curl -s -o /dev/null -w "HR [%{http_code} %{time_total}s]\n" "https://<HR-NGROK-URL>/health"
curl -s -o /dev/null -w "IT [%{http_code} %{time_total}s]\n" "https://<IT-NGROK-URL>/health"
curl -s "https://<HR-NGROK-URL>/hr/candidates?limit=1" | head -c 300; echo
```
Then one live `tools/list` + one `hr_list_candidates` call through the hosted runner with the public env, and paste all outputs into `evidence/quota-log.md` + flip this file to PASS.

## 5. Quota / cost note

No quota consumed by this check (zero builds run; `synapse info` not even re-polled — last known `2/10 · 775/100.0K` per `evidence/quota-log.md:24`). Expected cost of the unblock: **0 new servers, 0 new lines** (rebuilds reuse `surface_cache.json`; `--discover` also added 0 lines in `12-synapse-run.md:17`). ngrok free tier suffices (1 dev domain + full client; second tunnel needs a second domain or a random URL).

## 6. Re-check routing

Status **BLOCKED** until Steps 2–6 produce: (a) two public `https://…` URLs serving `/health` 200 off-machine, (b) two same-ID rebuilds logged in `evidence/quota-log.md`, (c) one remote tool call transcript. If ngrok drops at the venue, fall back to localhost with zero pause (kill-network drill <90s, `scripts/share.sh` header) — localhost path is verified healthy (§2).
