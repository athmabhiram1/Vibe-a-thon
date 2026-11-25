# 02 — frontend.html Build Spec (Single-File Demo UI, Track 3)

**Date:** 2026-11-22 | **Target:** `frontend.html` — single self-contained file, no build step, CDN allowed
**Backends:** HR `http://localhost:8001` + IT `http://localhost:8002` | **Stack:** vanilla JS + `fetch` only, no framework, no secrets in code
**Sources:** `plan.md` §2–§6 + `research/final/15-endpoints.md` (authoritative for paths/operationIds)

> operation_id note (conflict resolved): `plan.md` §2 uses prefixed aliases (`hr_list_candidates`, `hr_get_oncall`, …) as *MCP tool-name shorthand*. `15-endpoints.md` §2–§3 gives the *code-authoritative* `operation_id` values actually on the decorators (`list_candidates`, `get_oncall`, …). **Frontend calls HTTP paths, not operationIds** — so paths below are identical in both docs. Builder MUST use the `15-endpoints.md` IDs in FastAPI code; either alias set is acceptable in UI labels. Table below lists both.

---

## 1. Goals + non-goals

**Goals (what this file must do on stage):**
1. Drive the full Track 3 loop without touching curl/Inspector: exception queue → staged preview with citations → `APPROVE <hash>` → flip + receipt → audit row.
2. Make the `--discover` moment visible: `GET /hr/oncall` absent → added live → re-polled → Q3 reroute chain unblocked. Same server ID, no client re-config (show in Discovery Status pane).
3. Stay readable on projector at 10 ft: ≥18pt base font, high contrast, 3 panes visible at 1920×1080 *and* 1366×768 without horizontal scroll.

**Non-goals:** no auth/login UI, no pagination component, no chart lib required (plain counts/bars via CSS), no persistence (all state in-memory + server), no secrets/env in code (bases are `http://localhost` literals with editable inputs, default 8001/8002).

---

## 2. Global layout (3-pane visible)

```
+==================================================================================+
| HEADER  [Track 3 badge]  Onboard Copilot — HR×IT   HR:8001 [●] IT:8002 [●]  Seed  |
|         Reset | Status | clock | font-size toggle (18/22/26pt)                   |
+==========================+===============================+=======================+
| LEFT (queue)             | CENTER (work)                 | RIGHT (proof)         |
| 1. Exception Queue       | 3. Candidate Detail         | 5. Audit Log pane     |
| 2. Breach Board          | 4. Staged Preview + Approve | 6. Discovery Status   |
|                          |    + Receipt                |                       |
+--------------------------+-----------------------------+-----------------------+
| FOOTER: last fetch ms | tool count 13/14 | seed hash | error toast region              |
+==================================================================================+
```

- CSS grid: `grid-template-columns: 340px 1fr 380px;` collapse to 1 column under 900px (stack order: queue → detail → preview → audit → breach → discovery).
- Base: `html { font-size: 18pt; }` minimum; toggle buttons set `18/22/26pt` on `<html>`. Contrast: black `#0A0A0A` on white, or white on `#0A0A0A` dark mode; accent yellow `#FFD400` for WRITE preview border; red `#D00000` for breach; green `#007A33` for receipt. No gray-on-gray text (contrast ≥7:1).
- No build: single `<style>` + single `<script>` at end of body. CDN allowed but OPTIONAL (e.g., no Tailwind needed; if used, must degrade gracefully offline).

### 2.1 Header wireframe

```
+----------------------------------------------------------------------------------+
| 🏷️ TRACK 3 · COPILOT ACROSS TWO SYSTEMS   Onboard Copilot                        |
| HR [● LIVE :8001] [input HR base____]  IT [● LIVE :8002] [input IT base____]      |
| [🌱 Seed] [♻️ Reset] [📡 Status]   Tools: 13/14   [A- 18pt] [A 22pt] [A+ 26pt]   |
+----------------------------------------------------------------------------------+
```

- Track 3 badge: fixed left, high-contrast pill (`TRACK 3`), never hidden on resize.
- Health dots: polled via `GET /demo/status` (or `GET /hr/candidates?limit=1` + `GET /it/tickets/breaches` fallback if `/demo/status` absent). Green = 2xx <1s, amber = slow, red = down + tooltip with fetch error.
- Base-URL inputs: editable text fields defaulting to `http://localhost:8001` / `:8002`; all fetch calls read from them (enables ngrok mirror without code change).

### 2.2 LEFT — Exception Queue + Breach Board

```
+------------------------------+
| ⚠️ EXCEPTION QUEUE (n) [↻]   |
| +--------------------------+ |
| | CAND-002 Priya · SIGNED  | |  <- selected
| | visa-risk · starts Mon   | |
| +--------------------------+ |
| | CAND-007 … BG pending    | |
| +--------------------------+ |
| empty: "✅ Queue clear —    | |
|  all candidates converted" | |
+------------------------------+
| 🔥 BREACH BOARD [↻]          |
| T-5001 P1 support-night OPEN |
|  breached 26h · a@x.com     |
| T-5002 P2 …                  |
| empty: "No breaches 🎉"      |
+------------------------------+
```

- Exception Queue = candidates needing decision (status `interview|offer`, or visa-risk/BG-pending/weekend-start flags). Click row → loads Candidate Detail + Staged Preview. Keyboard: ↑/↓ to move.
- Breach Board = result of `GET /it/tickets/breaches`. Each card: ticket_id, priority, team, assignee_email, hours-breached, [Forensics] button → `GET /it/tickets/{id}` + `GET /hr/shifts` join line ("assignee off-shift · on-call backup: …").

### 2.3 CENTER — Candidate Detail + Staged Preview + Approve + Receipt

```
+=================================================+
| 👤 CANDIDATE DETAIL  CAND-002                   |
| Priya · priya@… · platform · SIGNED · BG: pass  |
| visa-risk ⚠️ · starts Mon (weekend? no)         |
| [hire → POST /hr/employees] citations: H1 H2    |
+-------------------------------------------------+
| ⚠️ WRITE PREVIEW <a3f9c1>  (yellow border)      |
| Will call: POST /hr/employees {name,email,…}    |
| + POST /it/equipment/assign {LT-1007→EMP-021}   |
| hash: sha256(redacted) a3f9…c1  [Copy]          |
| citations: hr_list_candidates · shift_calendar  |
+-------------------------------------------------+
| [✅ APPROVE a3f9c1] [✖ Reject]  need hash match |
| Receipt: ACTIVE EMP-021 · LT-1007 · 12:01:33    |
|  audit seq #14 · hash-chained ✅                |
+=================================================+
```

- Staged Preview is client-side staging (Cite-Before-Act UX from `plan.md` §5): shows exact JSON bodies that *would* be POSTed, plus short hash (first 6 of sha256 of canonical redacted body). APPROVE button disabled until hash displayed; on click sends real POSTs in order (employee → assign → optional reroutes) and renders Receipt.
- Reject path: logs a DENIED audit line locally + (optional) no server call; must still show in Audit pane.

### 2.4 RIGHT — Audit Log pane + Discovery Status

```
+----------------------------------+
| 🧾 AUDIT LOG (seq ↑) [Verify] [⤓]|
| #14 ALLOW create_employee EMP-021|
|  hash a3f9… ✓ prev-linked        |
| #13 DENY skip-checks (inject) 🛑 |
| empty: "No actions yet —         |
|  approve to write first row"     |
+----------------------------------+
| 📡 DISCOVERY STATUS              |
| tools: 13/14  it_oncall_coverage: ❌  |
| [Check on-call] [Re-poll]        |
| post-discover: ✅ get_oncall     |
|  on-call now: Lee (night)        |
| [Reroute breaches → on-call]     |
+----------------------------------+
```

- Audit Log: in-memory `audit[]` (seq from 1, `sha256(prev‖canonical)` chain per `plan.md` §5). [Verify] recomputes chain, reports `firstBadSeq or OK`. [⤓] downloads `audit.jsonl`. Both ALLOW and DENY rows recorded.
- Discovery Status: tracks the live moment. [Check on-call] calls `GET /hr/oncall`; before uncomment+H5 it 404s → show `❌ NOT YET — run synapse build --discover` hint. After, shows on-call person + enables [Reroute breaches → on-call] (chains breach list → oncall → reroute per ticket).

---

## 3. Exact API table (paths authoritative per 15-endpoints.md)

Bases: `HR = http://localhost:8001`, `IT = http://localhost:8002`. All `fetch` with `Content-Type: application/json`, no auth headers, no secrets.

| # | UI trigger | Method + Path | operation_id (code / plan-alias) | Query / Body | Success → UI |
|---|---|---|---|---|---|
| H1 | Queue load, Refresh | `GET {HR}/hr/candidates` | `list_candidates` / `hr_list_candidates` | `?team=&limit=20` | render Exception Queue cards |
| H2 | Select candidate | `GET {HR}/hr/candidates/{id}` | `get_candidate` / `hr_get_candidate` | path `CAND-002` | render Candidate Detail |
| H4 | Forensics / Q1 line | `GET {HR}/shifts` | `shift_calendar` / `hr_shift_calendar` | `?team=support-night&date=YYYY-MM-DD` (date = `ticket.created_at` date) | "on-shift?" join line |
| H5 ⭐ | [Check on-call], Q3 | `GET {HR}/oncall` | `get_oncall` / `hr_get_oncall` | `?team=support-night&at=<ISO now>` (both optional; default works) | Discovery Status flip ❌→✅; enables reroute |
| H3 | APPROVE (step 1) | `POST {HR}/hr/employees` | `create_employee` / `hr_create_employee` | `{name,email,team,start_date,role}` ← from candidate | Receipt `EMP-0xx` + audit ALLOW |
| I1 | Preview (laptop pick) | `GET {IT}/it/equipment` | `list_equipment` / `it_list_equipment` | `?status=free&limit=50` | pick first free (avoid `LT-1005` conflict, `LT-1012` retired — show trap warning if returned) |
| I2 | APPROVE (step 2) | `POST {IT}/it/equipment/assign` | `assign_laptop` / `it_assign_laptop` | `{serial, employee_id}` | Receipt `serial→employee` + audit ALLOW |
| I6 | Breach Board load | `GET {IT}/tickets/breaches` | `sla_breach_list` / `it_sla_breach_list` | `?team=&since=` optional | render Breach Board (expect 3 seeded) |
| I4 | [Forensics] | `GET {IT}/it/tickets/{id}` | `get_ticket` / `it_get_ticket` | path `T-5001` | forensics line + shift join |
| I5 | [Reroute …] per ticket | `POST {IT}/it/tickets/{id}/reroute` | `reroute_ticket` / `it_reroute_ticket` | `{to_email:<oncall.email>, reason:"sla-breach-reroute-to-oncall"}` | ticket card → `assignee=on-call` + audit ALLOW per ticket |
| D1 | [🌱 Seed] | `POST {HR or IT}/demo/seed` | — (demo-only) | header `x-demo-confirm: yes`, empty body; try HR first, fall back IT | toast `seeded 79 rows` + auto-refresh all panes |
| D2 | [♻️ Reset] | `POST {HR or IT}/demo/reset` | — | same confirm header | toast `reset` + clear receipt/audit(local) + refresh |
| D3 | [📡 Status], health dots | `GET {HR or IT}/demo/status` | — | — | header dots + footer `seeded_at`; fallback to H1+I6 probe if 404 |

> Route-order trap (builders beware, from 15-endpoints.md §3): server MUST declare `GET /it/tickets/breaches` BEFORE `GET /it/tickets/{id}` or breach calls 404. Frontend cannot fix this — surface the error verbatim in toast if seen.
> `POST /it/tickets` (`create_ticket`) exists but is NOT required for this UI (seeded tickets suffice); omit to keep tool count story clean.

**Vanilla fetch pattern (copy-paste):**
```js
const HR = () => document.getElementById('hrBase').value.replace(/\/$/,'');
const IT = () => document.getElementById('itBase').value.replace(/\/$/,'');
async function api(base, path, opts={}) {
  const t0 = performance.now();
  const res = await fetch(base + path, {headers:{'Content-Type':'application/json', ...(opts.headers||{})}, ...opts});
  const ms = Math.round(performance.now()-t0);
  footer(`… ${path} → ${res.status} · ${ms}ms`);
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}: ${await res.text().catch(()=> '')}`);
  return res.status === 204 ? null : res.json();
}
// examples:
api(HR(), '/hr/candidates?limit=20')
api(HR(), '/hr/oncall?team=support-night')
api(HR(), '/hr/employees', {method:'POST', body: JSON.stringify({name, email, team, start_date, role})})
api(IT(), '/it/tickets/breaches')
api(IT(), '/it/tickets/T-5001/reroute', {method:'POST', body: JSON.stringify({to_email: oncall.email, reason:'sla-breach-reroute-to-oncall'})})
api(HR(), '/demo/seed', {method:'POST', headers:{'x-demo-confirm':'yes'}})
```

---

## 4. Seed / Reset behavior

- Buttons in header: `[🌱 Seed]` → `POST /demo/seed`, `[♻️ Reset]` → `POST /demo/reset`, guarded by `ALLOW_DEMO_SEED=true + x-demo-confirm: yes + 6/min/IP` server-side (`plan.md` §3). Frontend always sends the confirm header; on `429/403` show toast "seed blocked (guard) — wait / check ALLOW_DEMO_SEED=true".
- After either: re-fetch H1 + I6 + I1, clear staged hash + receipt, keep audit log but append `SEED`/`RESET` marker row (local, clearly labeled non-server).
- Seed trap surfacing (from `plan.md` §3): if `LT-1005` appears in free pool show `⚠️ LT-1005 double-hold conflict — skip`; if `LT-1012` show `retired trap`. Candidate `CAND-002 → EMP-021` expected on first convert (display in receipt).

---

## 5. Error / empty / loading states (every pane needs all three)

| Situation | UI (projector-legible, no silent fail) |
|---|---|
| Backend down (fetch throws) | header dot red + pane-level banner `🔴 HR :8001 unreachable — is uvicorn up? (see toast)` + [Retry]; toast shows verbatim error first 200 chars |
| 404 on `/hr/oncall` (pre-discover) | Discovery pane amber: `get_oncall not yet exposed — uncomment H5 + synapse build --discover`; [Check on-call] stays enabled for re-poll |
| 404 on `/it/tickets/breaches` | Breach pane: `route shadowed — server must declare /breaches BEFORE /{id} (15-endpoints.md §3)` |
| Empty candidates / breaches | `✅ Queue clear` / `🎉 No breaches` (never blank pane) |
| Loading | per-pane skeleton line `⏳ loading …` + footer ms; never global spinner blocking other panes |
| Approve double-click | disable button after first click; duplicate returns cached receipt (`CONFLICT: key reused` style per `plan.md` §5) |
| Prompt-inject demo (optional) | input box in Staged Preview: typing "skip checks" → local `🛑 DENIED <reason>` audit row, no POST sent (mirrors eval guard story) |

---

## 6. Projector readability + a11y

- `font-size ≥18pt` base with `18/22/26pt` toggle; line-height ≥1.4; buttons ≥48px tall; focus outlines always visible.
- High contrast only; status never color-alone (always icon + text: `✅/⚠️/🔴/❌`).
- 3 panes visible at 1366px wide; no horizontal scroll; footer status line always in viewport or sticky.

---

## 7. Build constraints (hard)

1. ONE file `frontend.html`, no build step, `file://` + `http://` both work (no modules — plain `<script>`, no `import`).
2. Vanilla JS + `fetch` only; CDN links allowed but page must fully function offline/CDN-blocked (no Tailwind/JS-framework dependency for core loop).
3. No secrets/keys/tokens in code; only localhost base URLs + `x-demo-confirm` guard header.
4. All 8 required calls present: H1, H4, H3, I1, I2, I6, I5, H5-post-discover + D1/D2 buttons. Missing any one = fail.
5. Every POST goes through Staged Preview + hash + APPROVE click (Cite-Before-Act); no auto-POST on select/load.

---

## 8. Acceptance checklist (judge-run, <60s)

- [ ] Double-click `frontend.html` (or any static server) — no console errors, 3 panes + Track 3 badge visible, base font ≥18pt.
- [ ] With HR :8001 + IT :8002 running seeded: Queue shows CAND-002, Breach Board shows 3 (T-5001 P1 etc.), free laptop pool loads.
- [ ] Click CAND-002 → detail + staged preview with hash + citations appear; APPROVE disabled until hash rendered.
- [ ] APPROVE → `POST /hr/employees` → EMP-021 receipt + `POST /it/equipment/assign` → assignment receipt + 2 audit ALLOW rows, hash-chained; [Verify] reports OK.
- [ ] `GET /hr/shifts?team=&date=` forensics line renders ("off-shift" join) for a breached ticket.
- [ ] Pre-discover: [Check on-call] shows NOT-YET state; post `synapse build --discover`: re-poll shows on-call person, [Reroute breaches → on-call] chains I6→H5→I5×n with per-ticket audit rows.
- [ ] Seed/Reset buttons POST with confirm header, toast + refresh; 403/429 guard error shown verbatim, not swallowed.
- [ ] Kill HR backend → red dot + pane banner + retry; empty DB → `Queue clear` / `No breaches`, never blank.
- [ ] View-source: no `import`, no API key/secret string, only `localhost:8001/8002` + `x-demo-confirm`.
- [ ] 1366×768 screenshot: header + all 3 panes legible, no horizontal scroll.

---

## 9. Suggested file skeleton (builder follows, keeps single-file)

```html
<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Onboard Copilot — Track 3</title>
<style>/* grid 340px 1fr 380px; 18pt base; yellow preview border; red/green states */</style>
</head><body>
<header>…badge + bases + seed/reset/status + font toggle…</header>
<main>
  <section id="left"><div id="queue"></div><div id="breaches"></div></section>
  <section id="center"><div id="detail"></div><div id="preview"></div><div id="receipt"></div></section>
  <section id="right"><div id="audit"></div><div id="discovery"></div></section>
</main>
<footer id="statusbar"></footer>
<div id="toasts" aria-live="polite"></div>
<script>/* api() helper + per-pane loaders + stage/approve/audit-chain + seed/reset + oncall/reroute */</script>
</body></html>
```

*Next step: implement `frontend.html` from this spec, then screenshot-verify against §8 at 1920 and 1366 widths.*
