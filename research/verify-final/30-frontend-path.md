# 30 — Frontend click-path audit (frontend.html, read-only + curl)

Date (UTC): 2026-11-25 · Backends probed live via `curl.exe` (:8001 HR, :8002 IT both up, `/health` → 200 ×2).
Method: mapped every `fetch` call site in `frontend.html` (via `api(base,path,…)`), then curled the
same path to confirm data exists. `frontend.html` was NOT edited.

## Backend ground truth (curl, live)

| Probe | Result |
|---|---|
| `GET :8001/health`, `GET :8002/health` | 200 `{"ok":true}` ×2 — both up |
| `GET :8001/demo/status` (bare) | **404 `Not Found`** |
| `GET :8002/demo/status` (bare) | **404 `Not Found`** |
| `GET :8001/hr/demo/status` / `GET :8002/it/demo/status` | 200 seeded=true, 20/20/20/20 rows, v14 — correct paths carry the `/hr`, `/it` prefix |
| `POST :8001/demo/seed` (bare, frontend's exact path) | **404** — dead |
| `POST :8001/hr/demo/seed` (correct path, with confirm header) | 403 `demo endpoints disabled` (ALLOW_DEMO_SEED=false in this env) |
| `GET :8001/hr/candidates?limit=2` | 200 — CAND-001, CAND-002 (Priya Nair) |
| `GET :8001/hr/candidates/CAND-002` | 200 — Priya Nair signed |
| `GET :8001/hr/oncall?team=support-night` | 200 — EMP-014 Kiran Desai |
| `GET :8001/hr/shifts?team=IT&date=2026-11-24` | 200 — 10 rows (join works with real team+date) |
| `GET :8002/it/equipment?status=free&limit=50` | 200 — 7 rows, all `status:"available"` (server maps/ignores `free`→`available`) |
| `GET :8002/it/tickets/breaches` (literal) | 200 — 12 breached tickets |
| `GET :8002/it/tickets/T-5001` | 200 — breached ticket |
| OpenAPI `:8002` paths | `/it/equipment`, `/it/equipment/assign`, `/it/tickets`, `/it/tickets/breaches`, `/it/tickets/{ticket_id}`, `/it/tickets/{ticket_id}/reroute`, `/it/demo/*`, `/it/oncall-coverage` |
| OpenAPI `:8001` paths | `/hr/candidates`, `/hr/candidates/{candidate_id}`, `/hr/employees`, `/hr/shifts`, `/hr/oncall`, `/hr/demo/*` — no bare `/demo/*` anywhere |

## Button → fetch → endpoint table (PASS/FAIL)

| # | Button / control (id) | Fetch call site | Endpoint hit | Curl verdict | Result |
|---|---|---|---|---|---|
| 1 | ↻ queue reload (`queueReload`), team filter change (`teamFilter`) | `loadQueue()` L421 `GET HR()+"/hr/candidates?"+qs(team,limit:20)` | `GET :8001/hr/candidates` (H1) | 200, 2+ rows | **PASS** |
| 2 | Queue card click / ↑↓/Enter (`queueList`) | `loadDetail(id)` L479 `GET /hr/candidates/{id}` | `GET :8001/hr/candidates/CAND-002` (H2) | 200 | **PASS** |
| 3 | Auto stage-write (no button; runs after H2) | `stageWrite()` L509 `GET /it/equipment?status=free…` → fallback `?limit=50` → `GET ?limit=50` full pool | `GET :8002/it/equipment` (I1) | 200, 7 free/available | **PASS** (fallback chain sound; `free`→`available` absorbed by `pickLaptop` accepting both) |
| 4 | ✅ APPROVE (`approveBtn`) step 1 | `approve()` L558 `POST /hr/employees` + Idempotency-Key | `POST :8001/hr/employees` (H3) | path in OpenAPI; not POSTed by audit (write op — left unexecuted) | **PASS (path correct, not live-fired)** |
| 5 | ✅ APPROVE step 2 | `approve()` L563 `POST /it/equipment/assign {serial,employee_id}` + Idempotency-Key | `POST :8002/it/equipment/assign` (I2) | path in OpenAPI; not live-fired | **PASS (path correct, not live-fired)** |
| 6 | ✖ Reject (`rejectBtn`) | none — local `addAudit(DENY)` only, no POST | — (by design, verdict L591) | n/a | **PASS (local-only, correct)** |
| 7 | Copy hash (`copyHashBtn`) | none — clipboard write | — | n/a | **PASS (local-only)** |
| 8 | ↻ breach reload (`breachReload`) | `loadBreaches()` L600 literal `GET IT()+"/it/tickets/breaches"` — never interpolated (route-order NOTE L14-18) | `GET :8002/it/tickets/breaches` (I6) | 200, 12 rows | **PASS** |
| 9 | Forensics btn (per breach card) | `forensics()` L639 `GET /it/tickets/{id}` (I4) + L643 `GET /hr/shifts?team,date` (H4) | I4 + H4 | I4 200; H4 200 with real team/date (empty `[]` only when team/date has no rows — handled) | **PASS** (H4 failure shows amber warn, L644 — no crash) |
| 10 | Check on-call (`oncallBtn`) / Re-poll (`repolBtn`) | `checkOncall()` L664 `GET /hr/oncall?team=support-night` | `GET :8001/hr/oncall` (H5) | 200 Kiran Desai | **PASS — H5 live** |
| 11 | H5-absent path (same buttons, 404 branch) | L674 `if 404 → amber pre-discover` ("uncomment H5 + synapse build --discover, then Re-poll; Q3 parked") | — | code-reviewed: no fetch on wrong path, reroute zone cleared, no silent fail | **PASS (mishandling: none — correct amber handling)** |
| 12 | Stage reroute plan → APPROVE reroute ×N (dynamic btns in `rerouteZone`) | `renderRerouteStage()` L710 `POST /it/tickets/{id}/reroute {to_email,reason}` + Idempotency-Key per ticket | `POST :8002/it/tickets/{id}/reroute` (I5) | path in OpenAPI; not live-fired (would mutate) | **PASS (path correct, not live-fired)** |
| 13 | 🌱 Seed (`seedBtn`, two-click arm) | `demoPost("seed")` L737 `POST {HR,IT}()+"/demo/seed"` (bare, **no `/hr`|`/it` prefix**) | `POST :8001/demo/seed` → 404; fallback `:8002/demo/seed` → 404 | **404 confirmed by curl** (correct path would be `/hr/demo/seed`, currently 403-disabled anyway) | **FAIL — DEAD BUTTON (wrong path)** |
| 14 | ♻️ Reset (`resetBtn`, two-click arm) | `demoPost("reset")` L737 `POST {HR,IT}()+"/demo/reset"` (bare) | same prefix bug | same 404 class (correct path `/hr/demo/reset`) | **FAIL — DEAD BUTTON (wrong path)** |
| 15 | 📡 Status (`statusBtn`) | `statusCheck()` L754 bare `GET /demo/status` on HR, fallback IT — both 404 — then `health()` | bare path 404 (curl-confirmed); `health()` fallback probes H1 + I6 | dots still update; toast shows error but UI recovers | **PARTIAL PASS — wrong path, degraded not dead** (fix: `GET /hr/demo/status` with IT fallback) |
| 16 | Refresh tools (`toolRefresh`) | `refreshAll()` → `health()+loadQueue()+loadBreaches()` | H1 + I6 + demo/status-then-fallback | 200s | **PASS** |
| 17 | Verify (`verifyBtn`) | none — local sha256 chain recompute | — | n/a | **PASS (local-only)** |
| 18 | ⤓ download audit (`dlBtn`) | none — Blob JSONL download | — | n/a | **PASS (local-only)** |
| 19 | Font A-/A/A+ (`data-font` 18/22/26) | none — sets `documentElement.style.fontSize` | — | n/a | **PASS (local-only)** |
| 20 | Esc disarm | none — local | — | n/a | **PASS** |
| — | Registry entry `it_create_ticket` (I3 `POST /it/tickets`) | **no call site** — listed in TOOLS L311 but never fetched, no button wires it | path exists in OpenAPI | n/a | **FLAG — inert registry row, never `markSeen`; not a broken button, but Tools counter can never reach 14/14 via UI** |

## Dead / wrong-path summary

1. **DEAD: Seed + Reset (FAIL).** `demoPost()` builds `"/demo/"+kind` against both bases, but servers only
   serve `/hr/demo/*` and `/it/demo/*`. Both attempts 404 (curl-confirmed), so the buttons always end in
   the "blocked/failed on both bases" toast + `SYS …-FAILED` audit row. Fix (backend-owner edit, not made here):
   `path = (base===HR()?"/hr":"/it")+"/demo/"+kind`, or try prefixed paths in the loop.
   Note: even fixed, this env returns 403 `demo endpoints disabled`, which the existing toast already explains.
2. **WRONG PATH, DEGRADED: Status + health dots (PARTIAL).** `health()` L396 `GET /demo/status` and
   `statusCheck()` bare `/demo/status` both 404; recovery works (`health()` falls back to H1 probe,
   `statusCheck()` falls back to IT base then `health()`), so dots/queue/breaches still go green — but every
   load pays a failed fetch + error toast. Fix: `GET /hr/demo/status` first, `GET /it/demo/status` fallback.
3. **404 messaging correct:** breach-board 404 branch (L609) names the route-shadow cause with the
   `15-endpoints.md §3` pointer; on-call 404 branch (L674) gives the amber pre-discover state with the
   `--discover` + Re-poll recovery. Neither hides the error.
4. **No other dead buttons.** All read/write flows H1–H4, H5, I1, I2, I4–I6 use prefixed paths present in
   live OpenAPI; writes carry `Idempotency-Key`; double-submit guard + receipt cache verified in code.

## Projector basics (code inspection)

- **Base size:** `html{font-size:18pt}` (24px) + A-/A/A+ switcher (18/22/26pt) — good.
- **Minimums:** `.btn min-height:48px`, `.btn.small 44px` — touch/projector friendly.
- **Contrast (dark room):** bg `#0A0A0A`/panel `#141414` + ink `#FFF`, muted `#E8E8E8`, accent `#FFD400` on black,
  green `#3DDC84` on `#00331a`, red `#FF6B6B` on `#3d0000` — all pass by inspection; `:focus-visible` 3px outline.
- **Tiny-text flags (minor):** `table.tools` + `.kbd-hint` at `.68rem` (~12pt @18pt base), `.base-row label` `.7rem`,
  `pre.json`/cards `.72rem` (~13pt). Smallest strings are hints/tool-ids, never the decision (APPROVE/hash/receipt
  render ≥ `.78rem` + 48px targets). At 18pt default the back row may strain on the tool table — mitigate with the
  built-in A+ 26pt button; consider raising `table.tools` to `.72rem` if the projector is weak.
- **Failure visibility:** every `catch` writes a `.verdict.err` + toast + footer `last fetch` line — no silent fails.

## Repro (read-only, Windows)

```powershell
curl.exe -s --max-time 8 http://localhost:8001/health
curl.exe -s --max-time 8 "http://localhost:8001/hr/candidates?limit=2"
curl.exe -s --max-time 8 "http://localhost:8001/hr/oncall?team=support-night"
curl.exe -s --max-time 8 http://localhost:8002/it/tickets/breaches
curl.exe -s --max-time 8 http://localhost:8001/demo/status            # 404 (frontend's path — the bug)
curl.exe -s --max-time 8 http://localhost:8001/hr/demo/status         # 200 (correct path)
curl.exe -s --max-time 8 -o NUL -w "%{http_code}`n" -X POST http://localhost:8001/demo/seed -H "x-demo-confirm: yes" -H "Content-Type: application/json" -d "{}"  # 404
```
