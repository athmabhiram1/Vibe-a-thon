# 06 — Frontend Verification: `frontend.html`

**Date:** 2026-11-24 | **Reviewer:** Explorer (subagent) | **File reviewed:** `frontend.html` at repo root
**Verdict:** ☐ SHIP · ☐ FIX-FIRST · ☐ REJECT · ☒ **NOT BUILT** (file absent — nothing to score)

## 1. Existence check

- `frontend.html` in `C:\Users\athma\OneDrive\Desktop\my projects\VIBE_CODE` (root): **ABSENT** (directory listing, 28 entries — no match).
- Recursive search `**/frontend*.html` across repo: **no files found**. No candidate file elsewhere to score.
- `research/verify-final/` directory did not exist; created by writing this file.

## 2. Rubric scoring (per `research/frontend/05-review-checklist.md` §6)

Not scorable — file does not exist. All 10 checks recorded as unscored:

| # | Check | Score |
|---|---|---|
| 1 | Exact paths + ports + operationIds (C1–C3) | — /2 (NOT BUILT) |
| 2 | Breach-before-id + H5-absent handling (C4–C5) | — /2 |
| 3 | Error states + timeout (R1–R2) | — /2 |
| 4 | Double-submit + idempotency-key (R3) | — /2 |
| 5 | Seed/reset guards + no secrets (R4–R5) | — /2 |
| 6 | Projector legibility: contrast + font (P1–P2) | — /2 |
| 7 | 3-pane fit + verdict banner (P3–P4) | — /2 |
| 8 | Write safety: approve gate (A1–A2) | — /2 |
| 9 | Discover honesty + CORS honesty (A3–A4) | — /2 |
| 10 | A11y minimum (X1–X3) | — /2 |
| | **TOTAL** | **— /20 (NOT BUILT; no SHIP/FIX-FIRST/REJECT applies)** |

No patch list is possible (nothing to patch). What follows is the full build brief so the builder knows exactly what remains.

## 3. What remains: 8 required API calls (per `research/frontend/02-frontend-spec.md` §§3, 7.4)

Bases: HR = `http://localhost:8001`, IT = `http://localhost:8002`. Vanilla JS + `fetch` only, `Content-Type: application/json`, no auth/secrets. Editable base-URL inputs defaulting to the above. Spec §7.4: missing any one = fail. (Note: `POST /it/tickets` / `create_ticket` is explicitly NOT required — seeded tickets suffice; omit to keep the tool-count story clean.)

| # | UI trigger | Method + Path | operationId (code / plan-alias) | Query / Body |
|---|---|---|---|---|
| H1 | Queue load, Refresh | `GET {HR}/hr/candidates` | `list_candidates` / `hr_list_candidates` | `?team=&limit=20` → Exception Queue cards |
| H4 | Forensics / Q1 line | `GET {HR}/hr/shifts` | `shift_calendar` / `hr_shift_calendar` | `?team=support-night&date=YYYY-MM-DD` (date = ticket `created_at` date) → "on-shift?" join line |
| H3 | APPROVE step 1 | `POST {HR}/hr/employees` | `create_employee` / `hr_create_employee` | `{name,email,team,start_date,role}` from candidate → receipt `EMP-0xx` + audit ALLOW |
| I1 | Preview (laptop pick) | `GET {IT}/it/equipment` | `list_equipment` / `it_list_equipment` | `?status=free&limit=50` → pick first free; warn on `LT-1005` (double-hold) / `LT-1012` (retired) traps |
| I2 | APPROVE step 2 | `POST {IT}/it/equipment/assign` | `assign_laptop` / `it_assign_laptop` | `{serial, employee_id}` → assignment receipt + audit ALLOW |
| I6 | Breach Board load | `GET {IT}/it/tickets/breaches` | `sla_breach_list` / `it_sla_breach_list` | `?team=&since=` optional → expect 3 seeded |
| I5 | [Reroute …] per ticket | `POST {IT}/it/tickets/{id}/reroute` | `reroute_ticket` / `it_reroute_ticket` | `{to_email:<oncall.email>, reason:"sla-breach-reroute-to-oncall"}` → per-ticket audit ALLOW |
| H5 ⭐ | [Check on-call], Q3 (post-discover) | `GET {HR}/hr/oncall` | `get_oncall` / `hr_get_oncall` | `?team=support-night&at=<ISO now>` (both optional) → Discovery flip ❌→✅, enables reroute |
| D1 | [🌱 Seed] | `POST {HR or IT}/demo/seed` | — (demo-only) | header `x-demo-confirm: yes`, empty body; try HR first, fall back IT → toast + refresh |
| D2 | [♻️ Reset] | `POST {HR or IT}/demo/reset` | — | same confirm header → toast + clear receipt/audit(local) + refresh |
| D3 | [📡 Status], health dots | `GET {HR or IT}/demo/status` | — | header dots + footer `seeded_at`; fallback to H1+I6 probe if 404 |

Plus for completeness the builder will also need (referenced in spec table, used by Forensics/Q-flows):
- H2 `GET {HR}/hr/candidates/{id}` (`get_candidate`) → Candidate Detail.
- I4 `GET {IT}/it/tickets/{id}` (`get_ticket`) → forensics line + shift join.

Critical traps for builder: (a) call `GET /it/tickets/breaches` as a literal string, never by interpolating `get_ticket`; server must declare `/breaches` BEFORE `/{id}` — surface verbatim error in toast if shadowed. (b) H5 404 pre-discover is EXPECTED — amber `not yet exposed` state, re-poll enabled. (c) Every POST goes through Staged Preview + hash + APPROVE click (Cite-Before-Act); no auto-POST on select/load. (d) `x-demo-confirm: yes` header on seed/reset; show 403/429 guard errors verbatim.

## 4. Acceptance checklist (per `02-frontend-spec.md` §8 — judge-run, <60s)

Builder must satisfy ALL of these before re-submitting for review:

- [ ] Double-click `frontend.html` (or any static server) — no console errors, 3 panes + Track 3 badge visible, base font ≥18pt (spec: `html { font-size: 18pt; }` + 18/22/26pt toggle).
- [ ] With HR :8001 + IT :8002 running seeded: Queue shows CAND-002, Breach Board shows 3 (T-5001 P1 etc.), free laptop pool loads.
- [ ] Click CAND-002 → detail + staged preview with hash + citations appear; APPROVE disabled until hash rendered.
- [ ] APPROVE → `POST /hr/employees` → EMP-021 receipt + `POST /it/equipment/assign` → assignment receipt + 2 audit ALLOW rows, hash-chained; [Verify] reports OK.
- [ ] `GET /hr/shifts?team=&date=` forensics line renders ("off-shift" join) for a breached ticket.
- [ ] Pre-discover: [Check on-call] shows NOT-YET state; post `synapse build --discover`: re-poll shows on-call person, [Reroute breaches → on-call] chains I6→H5→I5×n with per-ticket audit rows.
- [ ] Seed/Reset buttons POST with confirm header, toast + refresh; 403/429 guard error shown verbatim, not swallowed.
- [ ] Kill HR backend → red dot + pane banner + retry; empty DB → `Queue clear` / `No breaches`, never blank.
- [ ] View-source: no `import`, no API key/secret string, only `localhost:8001/8002` + `x-demo-confirm`.
- [ ] 1366×768 screenshot: header + all 3 panes legible, no horizontal scroll.

## 5. Review routing

- Current status: **NOT BUILT** — do not apply the 10-check rubric or SHIP/FIX-FIRST/REJECT yet.
- Next step: implement `frontend.html` at repo root from `research/frontend/02-frontend-spec.md` (§9 skeleton), then screenshot-verify against §8 at 1920 and 1366 widths.
- Re-check after build: ☐ (score against `research/frontend/05-review-checklist.md` 10-check rubric; Ship ≥ 18/20 with zero 0s).
- Spec sources: `research/frontend/02-frontend-spec.md` (build), `research/frontend/05-review-checklist.md` (review), `research/final/15-endpoints.md` (authoritative paths/operationIds: HR `http://localhost:8001` + `/hr`, IT `http://localhost:8002` + `/it`, 11 operationIds, H5 live-discover, I6-before-I4 order).
