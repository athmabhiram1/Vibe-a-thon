# 05 — Review Checklist for Generated frontend.html

**Purpose:** Score the returned `frontend.html` in one pass before the live demo. Fail fast: any **Reject** item blocks ship. Fix-first items must be patched same-day.
**Source of truth:** `research/final/15-endpoints.md` (HR `http://localhost:8001` + `/hr`, IT `http://localhost:8002` + `/it`; 11 operationIds; H5 live-discover; I6-before-I4 route order).

---

## 1. Correctness (spec fidelity — check against 15-endpoints.md)

- [ ] **C1 — Exact base URLs + ports.** HR calls go to `http://localhost:8001`, IT to `http://localhost:8002`. No swapped ports, no single-port proxy assumption, no relative `/api/...` paths unless the file documents the proxy mapping explicitly.
- [ ] **C2 — Exact API paths (11).** HR: `GET /hr/candidates`, `GET /hr/candidates/{id}`, `POST /hr/employees`, `GET /hr/shifts?team=&date=`, `GET /hr/oncall?team=&at=`. IT: `GET /it/equipment?status=&limit=`, `POST /it/equipment/assign`, `POST /it/tickets`, `GET /it/tickets/breaches?team=&since=`, `GET /it/tickets/{ticket_id}`, `POST /it/tickets/{ticket_id}/reroute`. Any typo (`/hrs/`, `/ticket/`, `/breach`) = Reject.
- [ ] **C3 — operationIds referenced correctly (if shown).** `list_candidates`, `get_candidate`, `create_employee`, `shift_calendar`, `get_oncall`, `list_equipment`, `assign_laptop`, `create_ticket`, `get_ticket`, `reroute_ticket`, `sla_breach_list`. No invented names (`getBreaches`, `list_tickets`).
- [ ] **C4 — Breach-before-id route assumption handled.** Code calls `GET /it/tickets/breaches` as a literal string and never builds it by interpolating `get_ticket("/it/tickets/" + "breaches")`. Comment or code acknowledges `/tickets/breaches` must be declared before `/tickets/{ticket_id}` server-side (per §3 stub NOTE) and the frontend does not depend on route-registration order.
- [ ] **C5 — H5 absent-at-baseline handled.** On load (10-tool baseline, H5 not yet added) the UI does NOT hard-crash: On-Call panel shows explicit empty/disabled state ("H5 not yet discovered — run `synapse build --discover`"), Q3 button disabled or explains dependency. After H5 appears, Q3 enables without page rewrite. A frontend that assumes H5 always exists = Fix-first.

## 2. Robustness

- [ ] **R1 — Fetch error states everywhere.** Every panel (Seed, Q1, Q2, Q3, Tools, Writes) renders loading → success → error states. Errors show status code + body excerpt, never a blank pane or silent console-only log. `!res.ok` is checked; JSON parse failures are caught.
- [ ] **R2 — Timeout + abort.** All `fetch` calls pass `AbortSignal.timeout(...)` (or `AbortController`, ≥8s) and display "timed out — is uvicorn on 8001/8002 running?" rather than hanging the demo spinner forever.
- [ ] **R3 — Double-submit guard + idempotency-key send.** All POST buttons (`create_employee`, `assign_laptop`, `create_ticket`, `reroute_ticket`) disable while in-flight; reroute/seed sends `Idempotency-Key: <uuid>` header. No double-click = double-ticket bug.
- [ ] **R4 — Seed/reset guards.** Seed and Reset buttons require a typed confirmation or two-click arm ("click again to confirm") and Reset warns it wipes demo tickets. No one-click nuke next to Q1.
- [ ] **R5 — No hardcoded secrets / no credential leakage.** No API keys, tokens, passwords, or `Authorization:` literals in the file. Query params (`team`, `date`, `at`, `since`) are URL-encoded via `URLSearchParams` or `encodeURIComponent`, not string-concatenated raw.

## 3. Readability on Projector (arena legibility)

- [ ] **P1 — Contrast.** Dark-on-light or light-on-dark body text ≥ 4.5:1; no gray-on-gray (`#999` on `#eee`), no red-on-green status. JSON keys and values distinguishable at 3m distance.
- [ ] **P2 — Font size.** Base body ≥ 16px, JSON/log output ≥ 14px, headings ≥ 20px. No 11–12px "tiny terminal text" anywhere including `<pre>` blocks.
- [ ] **P3 — 3-pane fit at 1280×720, 100% zoom, no horizontal scroll.** Left (controls) / middle (results) / right (trace or tools) visible simultaneously. Tables wrap or scroll vertically within their pane; page-level horizontal scrollbar = Fix-first.
- [ ] **P4 — Status visible from back row.** Each question (Q1/Q2/Q3) has a one-line verdict banner ("T-551 BREACHED · assignee off-shift · on-call: …") — judges never have to parse raw JSON to know the answer.

## 4. Anti-patterns (instant flags)

- [ ] **A1 — No chat-only tab with no write button.** If there is a chat/prompt box, there is a visible Approve/Run-write button beside it. A free-text box that claims to "reroute" but has no confirmation gate = Reject (violates Track 2 safety pattern from 15-endpoints.md §2–3).
- [ ] **A2 — No dashboard without approve.** Every write path (`create_employee`, `assign_laptop`, `reroute_ticket`) shows a preview (who → what) + explicit Approve step. One-click auto-reroute-all with no confirm = Reject.
- [ ] **A3 — No hardcoded tool list that hides --discover.** Tool list is fetched/rendered dynamically (10 → 11 after discover) or has a "Refresh tools / re-run --discover" button. A static `const TOOLS = [...10 items]` with no refresh path conceals the arena moment = Fix-first.
- [ ] **A4 — No CORS / connectivity magical thinking.** File does not assume `no-cors`, does not swallow `TypeError: Failed to fetch` as success. Failure hint names the real fix (start uvicorn on 8001/8002, enable CORS `allow_origins=["*"]` for demo) rather than "check internet".

## 5. Accessibility Basics (minimum bar)

- [ ] **X1 — Labels.** Every input/select has an associated `<label for=...>`; icon-only buttons have `aria-label`.
- [ ] **X2 — Focus visible + keyboard approve.** Focus outline preserved (no `outline: none` without replacement); Approve/confirm reachable and activatable by Tab + Enter/Space; Esc closes any confirm dialog.
- [ ] **X3 — Live region for results.** Result/error banners use `role="status"` / `aria-live="polite"` so screen-reader and keyboard-only judges get the verdict without hunting the JSON pane.

---

## 6. Scored Rubric (10 checks — circle one per row)

Score each 2 = pass, 1 = fix-first (patch today), 0 = reject (blocks demo). **Ship ≥ 18/20 with zero 0s. Fix-first = 14–17 or any single 1 without 0s. Reject = ≤ 13 or any 0.**

| # | Check (maps to above) | 2 (ship) | 1 (fix-first) | 0 (reject) | Score |
|---|---|---|---|---|---|
| 1 | Exact paths + ports + operationIds (C1–C3) | All 11 exact | 1–2 typos, fixable in minutes | Wrong ports / invented endpoints | /2 |
| 2 | Breach-before-id + H5-absent handling (C4–C5) | Both handled w/ explicit states | One missing, easy patch | Q3 crashes at baseline | /2 |
| 3 | Error states + timeout (R1–R2) | All panes + timeout msg | 1 pane missing state | Silent fails / infinite spinner | /2 |
| 4 | Double-submit + idempotency-key (R3) | Disabled btns + header sent | Guard but no header | Double-POST possible | /2 |
| 5 | Seed/reset guards + no secrets (R4–R5) | Confirm arm + clean | Minor gap | One-click wipe / leaked key | /2 |
| 6 | Projector legibility: contrast + font (P1–P2) | ≥16px/≥14px, passes contrast | 1–2 small spots | Unreadable at 3m | /2 |
| 7 | 3-pane fit + verdict banner (P3–P4) | Fits 1280px + banners | Scrolls slightly / banner thin | H-scroll / must read raw JSON | /2 |
| 8 | Write safety: approve gate (A1–A2) | Every write previews + approves | 1 write path unguarded | Auto-write / chat-only reroute | /2 |
| 9 | Discover honesty + CORS honesty (A3–A4) | Dynamic tools + real fetch hints | Static list but refresh btn | Hides H5 moment / `no-cors` hack | /2 |
| 10 | A11y minimum (X1–X3) | Labels + focus + live region | 1 gap | Unkeyboardable approve | /2 |
| | **TOTAL** | | | | **/20** |

**Verdict:** ☐ SHIP (≥18, no 0s) · ☐ FIX-FIRST (14–17, list patches): ___ · ☐ REJECT (≤13 or any 0, reason): ___

**Reviewer / date:** ___ · **File reviewed:** `frontend.html` (sha/size): ___ · **Re-check after patch:** ☐
