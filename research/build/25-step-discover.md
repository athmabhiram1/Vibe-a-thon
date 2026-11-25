# 25 — Live `--discover` Runbook: Baseline 10 Tools → Uncomment `GET /hr/oncall` → Rescan → Reroute (Q3)

**CLI:** `@2ndbrainlabs-ai/synapse-cli` `0.1.9` · **Node ≥ 20** · **Repo:** `2ndbrainlabs-ai/synapse-cli-ts`
**Sources:** `03-synapse-technical.md` §2–3, `build/17-step-it.md` §7, `build/19-step-synapse.md` §§4–7, `build/20-step-clients.md` §§2–4, `final/04-synapse-auto.md`.
**Scope:** exact live-demo choreography — prove 10-tool baseline, add H5 live on camera, fail first on stale cache, `build --discover` to 11 tools, refresh both clients, run Q3 SLA-breach → on-call → reroute. Total ~10 min + 2 min buffer.
**Rule #1 of this demo:** builds reuse `.synapse/surface_cache.json` silently. Code changed since last scan is **ignored until `--discover`**. Exploit that on stage.

---

## 0. Pre-demo state (do this 30 min before doors)

- [ ] HR API (`:8001`) + IT API (`:8002`) both running, `/health` → `{"ok":true}`.
- [ ] HR router has `GET /hr/oncall` (`operation_id="hr_get_oncall"`, H5) present in file but **commented out** — verify with grep:
  ```bash
  grep -n "oncall" hr_service/routers/hr.py
  # expect: # @router.get("/oncall", operation_id="hr_get_oncall") — commented
  ```
- [ ] Baseline already built: `synapse build --auto --all-endpoints --server-name hr-api` + `--new` for `it-api`. `synapse info` → `Servers: 2/10`.
- [ ] Baseline tool count = **10**: H1–H4 (employees, get_employee, create_leave, leave_balance) + I1–I6 (list_equipment, assign_laptop, create_ticket, sla_breach_list, get_ticket, reroute_ticket). H5 absent by design.
- [ ] Cursor `.cursor/mcp.json` committed with `"MCP_REV": "1"`; Claude Desktop `claude_desktop_config.json` has both Synapse runner entries with correct `SYNAPSE_SERVER_ID` + `ENDPOINT_BASE_URL` (8001 / 8002).
- [ ] Inspector CLI warm: `npx -y @modelcontextprotocol/inspector --version` works offline (cache warm).
- [ ] Fallback video `demo-fallback.mp4` (<3 min) on desktop + USB; phone hotspot ready.
- [ ] Second terminal open, `surface_cache.json` path ready to `cat`/grep on projector.

Expected baseline fingerprint (memorize):

| Server | Tools | operation_ids |
|---|---|---|
| hr-api | 4 | `hr_list_employees, hr_get_employee, hr_create_leave, hr_leave_balance` |
| it-api | 6 | `it_list_equipment, it_assign_laptop, it_create_ticket, it_sla_breach_list, it_get_ticket, it_reroute_ticket` |

---

## Phase A — Baseline proof (Steps 1–6, ~2 min)

### Step 1 — Show both APIs alive (15s)
```bash
curl.exe -s http://localhost:8001/health; echo
curl.exe -s http://localhost:8002/health; echo
```
Narration: *"Two services, two ports, both green."* Expected: `{"ok":true}` × 2.

### Step 2 — Show 10-tool baseline in Cursor (20s)
Cursor chat → `tools/list` or Tools & Integrations panel. Point: 4 HR + 6 IT = 10. Narration: *"Baseline — ten tools. No on-call."*

### Step 3 — Inspector CLI independent verify (20s)
```bash
npx -y @modelcontextprotocol/inspector --cli --transport http --server-url http://localhost:8001/mcp --method tools/list 2>&1 | head -c 500
# ad-hoc stdio alt (no config file):
npx -y @modelcontextprotocol/inspector --cli node build/index.js --method tools/list
```
Narration: *"Trust but verify — ask the protocol directly."* Expect 10 names; `oncall` absent.

### Step 4 — Prove H5 is commented out (15s)
```bash
grep -n "oncall" hr_service/routers/hr.py
cat .synapse/surface_cache.json | grep -i "oncall" || echo "H5 NOT in cache (expected)"
```
Narration: *"The on-call route exists — but it's commented out, and it's not in the cache."*

### Step 5 — Show `synapse info` quota headroom (15s)
```bash
synapse info
```
Expected: `Servers: 2/10 used`, `Indexed lines: ~1,200/100,000`. Narration: *"Headroom for the live fork — no quota drama."*

### Step 6 — State the stale-cache law (15s, slide or say it)
> *"Synapse reuses `.synapse/surface_cache.json` on every build. New code is invisible until `--discover`. Watch me prove it by failing first."*

---

## Phase B — Uncomment live + FAIL FIRST (Steps 7–12, ~2.5 min)

### Step 7 — Uncomment `GET /hr/oncall` on camera (30s)
In editor, uncomment (exact shape — literal decorator, unique `operation_id`, `response_model`):
```python
# H5 — was commented, now live
@router.get("/oncall", operation_id="hr_get_oncall",
            description="Current on-call owner for a team. Q3 reroute target.",
            response_model=OnCall)
def get_oncall(team: Annotated[str, Query()] = "support-night") -> OnCall:
    ...
```
Save file. Restart/reload HR: `uvicorn hr_api:app --port 8001 --reload` (already `--reload` → auto). Verify:
```bash
curl.exe -s http://localhost:8001/hr/oncall?team=support-night
curl.exe -s http://localhost:8001/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print('hr_get_oncall' in str(d))"
```
Expected: JSON `{"email":"oncall@demo.example.com",...}` + `True`. Narration: *"Route is live in FastAPI — but Synapse doesn't know yet."*

### Step 8 — FAIL-FIRST beat: rebuild WITHOUT `--discover` (30s) ⭐
```bash
synapse build --auto --all-endpoints --server-name hr-api
```
**Expected failure (this is the point):** output says `Using the endpoints discovered on <old-date>` / `Discovered 4 endpoint(s)` — still 4 HR tools, H5 missing, same server id. Narration: *"I added a route and rebuilt — and nothing happened. That's the stale-cache trap. The build reused yesterday's scan."* Let the audience feel it. Point at the `Using the endpoints…` line on projector.

### Step 9 — Confirm the miss via cache grep (20s)
```bash
cat .synapse/surface_cache.json | grep -i "oncall" || echo "STILL MISSING — cache is stale (expected)"
Select-String -Path .synapse/surface_cache.json -Pattern "operation_id|list_employees|oncall"
```
Narration: *"Cache grep: no on-call. The file on disk changed; the cache didn't."*

### Step 10 — Show client still at 10 (Cursor refresh does nothing) (20s)
Cursor → refresh icon → `tools/list` → still 13 tools. Narration: *"Client refresh can't fix this — the server side never learned the route."*

### Step 11 — Say the fix out loud (10s)
> *"One flag: `--discover`. Force a rescan."*

### Step 12 — Timing checkpoint glance (10s)
You should be at ~4:30 elapsed. If behind, skip Step 10's second grep; keep the fail beat, cut the lecture.

---

## Phase C — `--discover` rescan → 11 tools (Steps 13–17, ~2 min)

### Step 13 — Live rescan (30s) ⭐
```bash
synapse build --discover --auto --all-endpoints --server-name hr-api
```
Expected:
```
Fresh scan … Discovered 5 endpoint(s)   # was 4
✓ Server hr-api updated (id: srv_xxxx — SAME id, no --new)
```
Narration: *"Fresh scan — five HR endpoints. Same server id, new tool."* (`--smart-names` optional: append it for nicer labels; costs one model call.)

### Step 14 — Cache grep now hits (15s)
```bash
cat .synapse/surface_cache.json | grep -i "oncall"
# expect: "operation_id": "hr_get_oncall" / "path": "/hr/oncall"
```
Narration: *"Cache now knows on-call."*

### Step 15 — `list-tools` grep equivalent (20s)
> ⚠️ `synapse list-tools` **does not exist** in CLI 0.1.9 (README `#commands`: only `init, build, analyze, config, model, info, update, uninstall`). Use:
```bash
synapse info                  # servers + indexed lines
synapse config                # key source, project, endpoint counts
cat .synapse/config.json      # server id + name mapping (confirms no fork)
```
Expected `config`: `Endpoints: 11 (hr-api: 5, it-api: 6)`. PowerShell grep:
```powershell
Select-String -Path .synapse/surface_cache.json -Pattern "operation_id|hr_get_oncall|it_sla_breach_list"
```
Narration: *"No list-tools subcommand — this grep is the honest equivalent."*

### Step 16 — Inspector CLI re-verify: 11 (20s)
```bash
npx -y @modelcontextprotocol/inspector --cli --transport http --server-url http://localhost:8001/mcp --method tools/list
```
Expected: `hr_get_oncall` present. Narration: *"Eleven tools at the protocol layer — before touching any client."*

### Step 17 — Quota sanity (10s)
```bash
synapse info
```
Expected: still `2/10 servers`; indexed-lines delta ~nothing (delta-only reporting). Narration: *"Rescans are cheap — delta-only."*

---

## Phase D — Client refresh contrast (Steps 18–21, ~2 min)

### Step 18 — Cursor hot-reload: `MCP_REV` bump (30s)
In `.cursor/mcp.json`, bump `"MCP_REV": "1"` → `"2"`, save → refresh icon (or toggle server off → on) → `tools/list`.
```json
{ "mcpServers": { "hr-api": { "env": { "MCP_REV": "2", "ENDPOINT_BASE_URL": "http://localhost:8001" } } } }
```
Expected: 14th tool appears, **no app restart**. Narration: *"Env bump changes the hash — full reload, no restart."* If stale: HTTP variant bump `?v=1` → `?v=2`; nuclear: `Developer: Reload Window`.

### Step 19 — Claude Desktop contrast: full restart (30s, talk over it)
Edit `%APPDATA%\Claude\claude_desktop_config.json` (absolute paths, validate JSON — one trailing comma = zero servers) → fully **Quit** (tray → Quit, not window X) → relaunch → confirm tools menu. Narration: *"Same change in Claude Desktop costs a full restart. Cursor: hot-reload. Claude: quit-relaunch. Plan your demo client accordingly."* (If short on time: show as slide, don't relaunch live.)

### Step 20 — Call H5 live in chat (20s)
Cursor/Claude chat: *"Who is on-call for support-night?"* → agent calls `hr_get_oncall(team="support-night")` → returns `oncall@demo.example.com`. Narration: *"Live discovery, callable in chat."*

### Step 21 — Stuck-drill (say, don't do — 10s)
*"If refresh does nothing: MCP_REV bump → toggle off/on → Reload Window → full restart. Stdio servers share one background process across windows — only a full restart guarantees a flush."*

---

## Phase E — Q3 reroute demo (Steps 22–25, ~2.5 min)

### Step 22 — Q3 breach triage: `it_sla_breach_list` (30s)
Chat: *"List breached tickets for support-night."* → `it_sla_breach_list(team="support-night")` → 3 rows incl. **T-551** (`breached:true`). Or curl fallback:
```bash
curl.exe -s "http://localhost:8002/it/tickets/breaches?team=support-night"
```
Narration: *"Start every Q1/Q2/Q3 answer here — the pre-computed breach anti-join."*

### Step 23 — Resolve the reroute target via H5 (30s)
Chat: *"Who owns support-night on-call?"* → `hr_get_oncall` → `oncall@demo.example.com`. Narration: *"The tool we just discovered live is now the Q3 answer's missing link."* Confirm-before-call: state serial/email aloud per agent-guardrail pattern.

### Step 24 — Reroute T-551 (30s) ⭐
Chat: *"Reroute T-551 to the on-call owner."* → `it_reroute_ticket(ticket_id="T-551", to_email="oncall@demo.example.com")`. Verify:
```bash
curl.exe -s http://localhost:8002/it/tickets/T-551 | python -c "import json,sys; print(json.load(sys.stdin)['assignee_email'])"
# expect: oncall@demo.example.com
```
Narration: *"Breach → on-call → reroute. Cross-service, two servers, closed loop."*

### Step 25 — Close + reset hooks (20s)
```bash
curl.exe -s -X POST http://localhost:8002/it/demo/seed
curl.exe -s -X POST http://localhost:8001/hr/demo/seed
```
Narration: *"Seed hooks restore the deterministic dataset in <1s — room is reset for Q&A."* End slide: baseline 10 → live 11 → Q3 closed. Q&A / fallback video if anything went red.

---

## Appendix A — Master timing (10 min + buffer)

| Clock | Phase | Beat |
|---|---|---|
| 0:00–2:00 | A (Steps 1–6) | Baseline 10, H5 commented, cache law stated |
| 2:00–4:30 | B (Steps 7–12) | Baseline allowlist build (13) → **fail-first** rebuild w/o `--discover` (still 13) |
| 4:30–6:30 | C (Steps 13–17) | `build --discover` → 11, cache + Inspector verify |
| 6:30–8:30 | D (Steps 18–21) | Cursor hot-reload vs Claude restart, live H5 call |
| 8:30–10:00 | E (Steps 22–25) | Q3: breaches → on-call → reroute T-551 → reseed |
| 10:00–12:00 | Buffer | Q&A / `demo-fallback.mp4` if red |

## Appendix B — Fail-first + error-fix table

| Symptom | Cause | On-stage fix (say it) |
|---|---|---|
| Rebuild shows `Using the endpoints discovered on …`, still 13 tools | Stale `surface_cache.json`; forgot `--discover` | *"That's the trap — rescan:"* `synapse build --discover --auto --endpoints "<expanded allowlist>" --server-name hr-api` |
| `Endpoint Selection Required` | No TTY + neither `--all-endpoints` nor `--endpoints` | Add `--all-endpoints` (or `--endpoints "GET /hr/oncall"`; either implies `--auto`) |
| `synapse list-tools: unknown command` | Doesn't exist in 0.1.9 | Use `synapse info` + `synapse config` + `surface_cache.json` grep (Step 15) |
| Cursor refresh shows stale 10 | Tool-list cache; same server hash | Bump `MCP_REV` 1→2 (HTTP: `?v=1`→`?v=2`), toggle off/on, `Reload Window` |
| Claude shows zero servers after edit | Trailing comma / relative path in JSON | Validate JSON, absolute paths only, full Quit → relaunch |
| `Quota Exceeded` | >10 servers / >100k lines | Rebuild in place (`--server-name hr-api`, no `--new`); `synapse info`; or `--local` leg (no quota) |
| `AUTH_INVALID` | Bad key / `SYNAPSE_API_KEY` shadowing | `synapse config set-key`, check `synapse config` source |
| Reroute 404 / `ticket not found` | Seeded store was mutated mid-demo | `POST /it/demo/seed` + `POST /hr/demo/seed`, retry Steps 22–24 |
| Route-shadow: `/breaches` returns single-ticket shape | `breaches` declared after `{ticket_id}` | Reorder: `GET /tickets/breaches` BEFORE `GET /tickets/{ticket_id}` (see `17-step-it.md` §4) |

## Appendix C — Copy-paste block (tape to laptop)

```bash
# baseline
curl.exe -s http://localhost:8001/health
curl.exe -s http://localhost:8002/health
synapse info
grep -n "oncall" hr_service/routers/hr.py
# uncomment H5 in editor, save, then:
curl.exe -s "http://localhost:8001/hr/oncall?team=support-night"
# FAIL FIRST (no --discover — stays at 10):
synapse build --auto --all-endpoints --server-name hr-api
cat .synapse/surface_cache.json | grep -i "oncall" || echo "STILL MISSING (expected)"
# THE FIX:
synapse build --discover --auto --all-endpoints --server-name hr-api
cat .synapse/surface_cache.json | grep -i "oncall"
synapse info; synapse config
# Q3 verify
curl.exe -s "http://localhost:8002/it/tickets/breaches?team=support-night"
curl.exe -s http://localhost:8002/it/tickets/T-551
curl.exe -s -X POST http://localhost:8001/hr/demo/seed
curl.exe -s -X POST http://localhost:8002/it/demo/seed
```

## Doc URLs

- CLI README (flags, cache, rebuild, quota, troubleshooting): https://github.com/2ndbrainlabs-ai/synapse-cli-ts
- Getting started: https://synapse.2ndbrainlabs.ai/docs (stale v1 — README wins)
- Examples: https://github.com/2ndbrainlabs-ai/synapse-examples
