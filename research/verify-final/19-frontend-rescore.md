# 19 — Frontend Re-score (independent, vs 05-review-checklist.md rubric)

**Date:** 2026-11-24 · **Reviewer:** independent rescore agent (did NOT trust builder self-score)
**File reviewed:** `frontend.html` (799 lines, single-file vanilla JS, no build step)
**Spec source of truth:** `research/final/15-endpoints.md` (HR `http://localhost:8001` + `/hr`; IT `http://localhost:8002` + `/it`)
**Live probing:** SERVERS UP — probed with `curl.exe` (see §Live probe results). **Nothing marked UNPROBED.**

---

## Live probe results (this rescore actually hit the backends)

| Probe | Result |
|---|---|
| `GET :8001/hr/candidates?limit=1` | **200** — 1 row (`CAND-001`) |
| `GET :8001/demo/status` / `:8002/demo/status` | **404 `{"detail":"Not Found"}` both** — frontend's H1+I6 fallback path is the real health path, correctly implemented |
| `GET :8002/it/tickets/breaches` | **200** — 3 rows (T-5001, T-5019, T-5002, all `breached:true`) |
| `GET :8001/hr/oncall?team=support-night` | **200** — `{"team":"support-night","employee_id":"EMP-014","name":"Kiran Desai",...}` (H5 live on disk) |
| `GET :8002/it/equipment?limit=2` | **200** — 2 rows (LT-1001/LT-1002 `on_hold`) |
| `OPTIONS :8002/it/tickets/breaches` (CORS preflight) | **200** with `access-control-allow-origin: *` — matches frontend's failure-hint claim |

---

## Check-by-check evidence (10 rows)

| # | Check | Evidence in file | Score |
|---|---|---|---|
| 1 | Exact paths + ports + operationIds (C1–C3) | Ports exact: HR default `http://localhost:8001`, IT `http://localhost:8002`, editable (L147–151). Paths exact for 10/11: `/hr/candidates`, `/hr/candidates/{id}`, `POST /hr/employees`, `/hr/shifts?team&date`, `/hr/oncall?team`, `/it/equipment?status&limit`, `POST /it/equipment/assign`, `/it/tickets/breaches` (literal, L600), `/it/tickets/{id}`, `POST …/reroute`. **Gaps:** (a) `POST /it/tickets` (I3/`create_ticket`) is listed in TOOLS but **never called** anywhere in the file; (b) breach call sends **no `team`/`since` params**; (c) on-call call sends `team` only, omits `at`; (d) operationIds use `hr_`/`it_` prefixes (`hr_list_candidates`, `it_sla_breach_list`…) vs spec's unprefixed (`list_candidates`, `sla_breach_list`) — consistent 1:1 namespacing, but not literally exact. No wrong ports, no invented endpoints. | **1** |
| 2 | Breach-before-id + H5-absent (C4–C5) | C4: literal `"/it/tickets/breaches"` (L410, L600) with header comment (L14–18) + 404-shadow diagnosis banner (L609–610). Never interpolated. C5: 404 on H5 → amber pre-discover state ("run `synapse build --discover`, then Re-poll. Q3 stays parked", L676–678), no crash; post-H5 green path enables reroute (L667–671). Live probe confirms H5 200 today so green path is exercised. **Staleness note (advisory, not docked twice):** current 15-endpoints.md moved the live moment to L1 `GET /it/oncall-coverage`, with H5 on-disk baseline — file's H5-uncomment narrative is outdated (see patch P4). | **2** |
| 3 | Error states + timeout (R1–R2) | Every pane has loading → success → error: queue (L418/L425/L430), breach (L597/L607/L611 + Retry btn), detail, preview, discovery, forensics. `!res.ok` checked, status+body excerpt shown (L345–346), JSON-parse failures caught (L349). All fetches via `api()` with `AbortSignal.timeout(10000)` (L335) and timeout-specific message naming uvicorn 8001/8002 (L339–342). | **2** |
| 4 | Double-submit + idempotency-key (R3) | `state.approving` guard + button disable + "APPROVING…" label (L551–555); `receiptCache[id]` returns cached receipt, never re-POSTs (L474–476, L554). `Idempotency-Key: uuid()` on employees (L559), assign (L564), every reroute (L711), seed/reset (L738). Reroute loop disables both buttons while running (L706). | **2** |
| 5 | Seed/reset guards + no secrets (R4–R5) | Two-click arm with 6 s auto-expiry (L726–730); reset label "Click again — wipes demo tickets" (L776); Esc disarms (L790–794). No API keys/tokens/passwords/`Authorization:` anywhere (only `Content-Type`, `Idempotency-Key`, `x-demo-confirm: yes`). All query params via `qs()`/URLSearchParams (L272) and `encodeURIComponent` on ids (L479, L639, L710). | **2** |
| 6 | Contrast + fonts (P1–P2) | Dark theme: `#FFF` on `#0A0A0A`/`#141414`; status colors on dark-tinted grounds (green `#3DDC84` on `#00331a`, red `#FF6B6B` on `#3d0000`, amber on `#3a2a00`) — no gray-on-gray, no red-on-green. Root `18pt` (=24 px); smallest text `.kbd-hint`/tool table `.68rem` ≈ 16 px ≥ 14 px floor; buttons ≈ 19 px; `pre.json` ≈ 17 px with wrapping. | **2** |
| 7 | 3-pane fit + verdict banner (P3–P4) | Grid `340px minmax(0,1fr) 380px` with `min-width:0`, wrapping `pre`/`cards`/`tables` (`word-break:break-word`), collapse <900 px (L136–138) — fits 1280×720 without page h-scroll by construction (not pixel-rendered — see limitation). One-line verdict banners per question: breach (`T-xxx BREACHED · assignee off-shift · on-call: …`, L648), queue, detail, preview, discovery — judges never parse raw JSON. | **2** |
| 8 | Approve gates (A1–A2) | No chat box at all; the only free-text input (inject probe) **refuses** and logs DENY with no POST (L520–525). Every write staged first: employee+assign preview with hash (L534–539) + disabled-until-staged APPROVE (L471/L541); reroute requires "Stage reroute plan" → hash → APPROVE ×N (L695–704). Reject logs DENY, no POST (L588–592). | **2** |
| 9 | Discover honesty + CORS (A3–A4) | CORS honest: no `no-cors`, `TypeError: Failed to fetch` surfaced with real fix ("Is uvicorn on 8001/8002 running (CORS allow_origins=[\"*\"])?", L342) — **live-verified** (preflight returns `ACAO: *`). **Docked:** TOOLS is a `static const` of 14 with `seen`-markers filled as calls succeed — honest progress tracking, but not a live-fetched tool list; "Refresh" only re-probes health/queue/breaches and can never reveal a genuinely new tool (e.g. L1 `it_oncall_coverage`). Static-list-with-refresh = rubric's 1. | **1** |
| 10 | A11y minimum (X1–X3) | Every input has `<label for>` (bases, team filter, start/role/inject); icon-only ↻/⤓ have `aria-label`. `:focus-visible` 3 px outline preserved, no `outline:none` (L36). APPROVE is a native button (Tab + Enter/Space); Esc disarms seed/reset. All verdicts use `role="status"` + `aria-live="polite"` (7+ regions + footer + toasts). | **2** |
| | **TOTAL** || **18/20** |

---

## Verdict: ☑ SHIP (18/20, zero 0s)

No reject-level defect. Both deductions are fix-first-in-spirit but already within the SHIP band per rubric (≥18, no 0s). Ship the demo; apply patches P1–P4 opportunistically (none blocks the arena).

## Patch list (non-blocking, ordered by value)

- **P1 (row 1):** Exercise or drop I3 — add a "file ticket" path that `POST /it/tickets`, or annotate TOOLS `it_create_ticket` as "registered, not used by this demo flow" so judges don't hunt a dead button.
- **P2 (row 1):** Send breach filters — `api(IT(),"/it/tickets/breaches?"+qs({team,since}))` wired to the team filter, so Q2's "worst breach rate by team" is actually server-filtered.
- **P3 (row 1):** Document the `hr_`/`it_` operationId prefix mapping in the header comment (one line: "UI prefixes spec IDs with service namespace; mapping is 1:1"), and pass `at` on the on-call query.
- **P4 (row 9 / spec drift):** Update the discovery narrative to match current 15-endpoints.md: H5 is on-disk baseline; the live `--discover` moment is L1 `GET /it/oncall-coverage`. Add an L1 probe + "needs_reroute" affordance, or a comment acknowledging the handoff, so the file doesn't contradict the runbook mid-demo.
- **P5 (verification limitation, acknowledged):** 3-pane fit judged by construction (grid + wrapping rules), not a pixel render at 1280×720. If a projector check is wanted, screenshot the file in Chromium at 1280×720/100% and confirm zero page-level h-scroll.

**Re-check after patch:** ☐ (only if P1–P4 applied — re-score rows 1 and 9)
