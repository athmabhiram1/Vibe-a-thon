# 37 — Verify `--discover`: Stale-Cache Proof, Same-Server-ID, Latency ×3

**Sources:** Participant guide Track 3 p.2 (`rebuild with synapse build --discover`) + p.4 (`reuses last scan until rescan; --new / --server-name`) · `build/25-step-discover.md` (10→11 runbook, fail-first beat, `surface_cache.json` law) · CLI README `#commands` (no `list-tools` in `0.1.9`).
**Goal:** prove in one dry-run that (a) rebuild **without** `--discover` ignores a new route, (b) rebuild **with** `--discover` picks it up **under the same server ID**, (c) cost is bounded. Ship-blocking for the Track 3 live update.
**Rule:** `.synapse/surface_cache.json` is the scan of record. Code on disk ≠ tools until `--discover` rewrites the cache.

---

## 1. Contract under test (4 asserts, all must pass)

| # | Assert | How to check | Verdict |
|---|---|---|---|
| A1 | Rebuild **without** `--discover` misses the new route | `surface_cache.json` grep → absent; Inspector `tools/list` count unchanged | `STALE (expected)` |
| A2 | Rebuild **with** `--discover` finds it | cache grep → `operation_id` + `path` present; Inspector `tools/list` count +1 | `FRESH` |
| A3 | **Same server ID** (no fork) | `.synapse/config.json` server id before == after; no `--new` used | `id: srv_xxxx unchanged` |
| A4 | Latency bounded + quota flat | time 3× each leg; `synapse info` still `2/10 servers`, indexed-lines delta ≈ 0 | fill table §5 |

Fail policy: A1 passing (i.e. new route appears *without* `--discover`) means the cache law changed — re-read the README before demoing. A3 failing (new id) means someone passed `--new` — client config is now stale.

---

## 2. Preconditions (2 min)

- [ ] HR API `:8001` + IT API `:8002` running, `/health` → `{"ok":true}`.
- [ ] Baseline built: `synapse build --auto --all-endpoints --server-name hr-api` (+ `--new` once for `it-api`). `synapse info` → `Servers: 2/10`.
- [ ] Baseline counts recorded: HR = 4 (`hr_list_employees, hr_get_employee, hr_create_leave, hr_leave_balance`), IT = 6 → total **10**. New route H5 (`GET /hr/oncall`, `operation_id="hr_get_oncall"`) **commented out** — verify: `grep -n "oncall" hr_service/routers/hr.py` shows only `# @router.get("/oncall"…)`.
- [ ] Server ID captured: `cat .synapse/config.json` → copy `hr-api` id to notepad (`ID0`).
- [ ] Inspector warm: `npx -y @modelcontextprotocol/inspector --version` works.

---

## 3. Drill script (copy-paste, ~6 min)

### Bash (macOS / Linux / Git Bash)

```bash
set -e
echo "=== 0. baseline ==="
curl -s http://localhost:8001/health; echo
synapse info
grep -n "oncall" hr_service/routers/hr.py || true
cat .synapse/surface_cache.json | grep -ci "operation_id"
ID0=$(python -c "import json; print(json.load(open('.synapse/config.json'))['servers']['hr-api']['id'])" 2>/dev/null || cat .synapse/config.json)
echo "ID0=$ID0"

echo "=== 1. add 1 route: uncomment H5 in editor, save, verify live ==="
# (do the uncomment by hand on camera — one decorator block, then:)
curl -s "http://localhost:8001/hr/oncall?team=support-night"; echo
curl -s http://localhost:8001/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print('openapi_has_oncall:', 'hr_get_oncall' in str(d))"

echo "=== 2. REBUILD WITHOUT --discover (expect MISS) ==="
time synapse build --auto --all-endpoints --server-name hr-api
cat .synapse/surface_cache.json | grep -i "oncall" || echo "ASSERT A1 PASS: STILL MISSING (stale cache, expected)"
# tools/list grep equivalent:
npx -y @modelcontextprotocol/inspector --cli --transport http --server-url http://localhost:8001/mcp --method tools/list 2>&1 | grep -ci "hr_" || true

echo "=== 3. REBUILD WITH --discover (expect HIT, same ID) ==="
time synapse build --discover --auto --all-endpoints --server-name hr-api
cat .synapse/surface_cache.json | grep -i "oncall" && echo "ASSERT A2 PASS: cache now has oncall"
ID1=$(python -c "import json; print(json.load(open('.synapse/config.json'))['servers']['hr-api']['id'])" 2>/dev/null || cat .synapse/config.json)
echo "ID0=$ID0"; echo "ID1=$ID1"
[ "$ID0" = "$ID1" ] && echo "ASSERT A3 PASS: same server id" || echo "ASSERT A3 FAIL: id changed (did you pass --new?)"
npx -y @modelcontextprotocol/inspector --cli --transport http --server-url http://localhost:8001/mcp --method tools/list 2>&1 | grep -i "oncall" && echo "ASSERT A2 PASS: tools/list has oncall"
synapse info  # ASSERT A4: still 2/10 servers
```

### PowerShell (Windows — حفظ as `Verify-Discover.ps1`)

```powershell
Write-Host "=== 0. baseline ==="
curl.exe -s http://localhost:8001/health; echo ""
synapse info
Select-String -Path hr_service/routers/hr.py -Pattern "oncall"
$ID0 = (Get-Content .synapse/config.json -Raw); Write-Host "ID0 captured (compare full text before/after)"
# 1. uncomment H5 in editor, save, then:
curl.exe -s "http://localhost:8001/hr/oncall?team=support-night"; echo ""
Write-Host "=== 2. REBUILD WITHOUT --discover (expect MISS) ==="
Measure-Command { synapse build --auto --all-endpoints --server-name hr-api }
Select-String -Path .synapse/surface_cache.json -Pattern "oncall" | Out-Null
if ($?) { Write-Host "UNEXPECTED: oncall found without --discover" } else { Write-Host "ASSERT A1 PASS: STILL MISSING (expected)" }
Write-Host "=== 3. REBUILD WITH --discover (expect HIT, same ID) ==="
Measure-Command { synapse build --discover --auto --all-endpoints --server-name hr-api }
Select-String -Path .synapse/surface_cache.json -Pattern "hr_get_oncall|/hr/oncall"
Write-Host "ASSERT A2 PASS if 1+ match lines above"
$ID1 = (Get-Content .synapse/config.json -Raw)
if ($ID0 -eq $ID1) { Write-Host "ASSERT A3 PASS: same server id" } else { Write-Host "ASSERT A3 FAIL: config changed" }
synapse info
```

---

## 4. Expected transcript (what "passing" looks like)

```text
# leg 2 — without --discover
Using the endpoints discovered on 2026-…   # <-- stale-scan tell
Discovered 4 endpoint(s)                   # still 4 HR, H5 absent
STILL MISSING (expected)                   # cache grep empty — A1 PASS

# leg 3 — with --discover
Fresh scan … Discovered 5 endpoint(s)      # was 4, now 5
✓ Server hr-api updated (id: srv_xxxx — SAME id, no --new)
"operation_id": "hr_get_oncall", "path": "/hr/oncall"   # cache grep hit — A2 PASS
ASSERT A3 PASS: same server id
hr_get_oncall                              # Inspector tools/list hit — A2 PASS (11 total)
Servers: 2/10 used                         # A4 PASS
```

> `synapse list-tools` **does not exist** in CLI `0.1.9` (commands: `init, build, analyze, config, model, info, update, uninstall`). The honest equivalents used above are the full `list-tools grep` set — assert all three agree before calling the drill green:

```bash
synapse info                                            # servers + indexed lines
synapse config                                          # key source + endpoint counts
cat .synapse/config.json                                # server-name → id mapping (A3)
Select-String -Path .synapse/surface_cache.json -Pattern "operation_id|hr_get_oncall|it_sla_breach_list"
npx -y @modelcontextprotocol/inspector --cli --transport http --server-url http://localhost:8001/mcp --method tools/list
```

---

## 5. Latency protocol — time 3×, report median

Run each leg 3× back-to-back (cold first run counts — report it, don't discard). Use `time` (bash) or `Measure-Command` (PS). Record wall-clock to 0.1 s.

| Run | Rebuild w/o `--discover` (s) | Rebuild w/ `--discover` (s) | Inspector `tools/list` (s) | Tools (HR/total) | Server id |
|---|---|---|---|---|---|
| 1 (cold) | | | | 4 / 10 → then 5 / 11 | `srv_…` |
| 2 (warm) | | | | 4 / 10 → then 5 / 11 | same |
| 3 (warm) | | | | 4 / 10 → then 5 / 11 | same |
| **Median** | | | | — | — |

Example filled row (illustrative — replace with your numbers; typical on a ~1.2 k-line demo repo):

| Run | w/o `--discover` | w/ `--discover` | `tools/list` | Notes |
|---|---|---|---|---|
| 1 | 8.2 s | 14.6 s | 2.1 s | cold npx + model handshake |
| 2 | 6.9 s | 11.3 s | 1.2 s | warm |
| 3 | 7.1 s | 11.8 s | 1.1 s | warm |
| **Median** | **7.1 s** | **11.8 s** | **1.2 s** | `--discover` ≈ +4–7 s (delta parse only) |

Interp for judges: `--discover` costs seconds (changed files re-parsed, rest skipped), quota is flat (`2/10 servers`, indexed-lines delta ≈ 0 — delta-only reporting). If `--discover` is >3× the stale rebuild, something rescanned everything — show the `Fresh scan … N files` line and move on.

---

## 6. Fix table (when an assert goes red)

| Symptom | Cause | Fix (say it on stage) |
|---|---|---|
| New route appears **without** `--discover` | Cache law changed / fresh checkout (no stale cache) | Re-establish staleness first: comment H5 → build → uncomment → rebuild w/o flag. The fail-first beat needs a stale cache. |
| `Endpoint Selection Required` | No TTY + no selector | Add `--all-endpoints` (or `--endpoints "GET /hr/oncall"` — either implies `--auto`). |
| `synapse list-tools: unknown command` | Doesn't exist in 0.1.9 | Use §4 grep set (`info` + `config` + cache grep + Inspector). |
| New server id / `Servers: 3/10` | Passed `--new` | Rebuild in place: `--server-name hr-api` with no `--new`; re-paste client config only if forked. |
| Inspector still 10 after `--discover` | Client/Inspector pointed at wrong port or stale runner | Confirm `ENDPOINT_BASE_URL=http://localhost:8001`, restart runner, re-run `tools/list`. |
| `Quota Exceeded` | >10 servers / >100 k lines | Reuse names (`--server-name`), `synapse info`, or `--local` leg (never counted). |
| `AUTH_INVALID` | Bad key / `SYNAPSE_API_KEY` shadow | `synapse config set-key`; check `synapse config` source column. |

---

## 7. Sign-off checklist (paste into PR / demo log)

- [ ] Leg 2 (no `--discover`): cache grep empty, Inspector still 10, output shows `Using the endpoints discovered on…` — A1 PASS
- [ ] Leg 3 (`--discover`): cache grep hits `hr_get_oncall` + `/hr/oncall`, Inspector shows 11 with `hr_get_oncall` callable — A2 PASS
- [ ] `.synapse/config.json` diff empty for `hr-api` id (no `--new`) — A3 PASS
- [ ] Latency table §5 filled (3 runs + median) + `synapse info` still `2/10` — A4 PASS
- [ ] `list-tools grep` triple (§4) pasted into log; fallback video cued if any leg red

*Delta vs cited sources: the 4-assert verdict shape, drill scripts, and latency-table format are pinned here; guide + `25-step-discover.md` define semantics, this file defines the executable pass/fail.*
