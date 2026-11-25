# Integration Critic — Console / Review / Audit vs Plan + ARCHITECTURE

**Workspace:** `workspace-25f2ad75-4340-469c-8a6d-0acc097f4f32` (read 2026-11-25; files were being edited mid-read — two review variants observed, see D1).
**Sources:** `src/app/console/page.tsx`, `src/app/console/review/[id]/page.tsx` (653-line self-contained version), `src/components/review/review-client.tsx` (633-line zustand variant), `src/app/audit/page.tsx`, `src/app/api/{approve,breaches,candidates,audit,inject,demo}/route.ts`, `src/lib/{data,store,onboard-api}.ts`, `src/components/app/app-shell.tsx`, `next.config.ts`, `tailwind.config.ts`, `src/app/globals.css`, repo `plan.md` §§2–3,6, `submission/ARCHITECTURE.md` §§tool-inventory/data-flow, `research/frontend/05-review-checklist.md` (C1–C5/R1–R4/A1–A4/P1–P4).

**One-line verdict:** the three pages look demo-complete on projector, but the UI talks to **static mocks + three narrow proxies**, not to the plan's H1–H5/I1–I6/L1 surface — the two live-moment actions (seed/reset, approve) both 400 against their own proxies, the typed client points at proxies that don't exist, and the "verified / online / receipt" banners are hardcoded.

---

## Ranked top-8 defects (by judging impact)

### D1 — Approve path 400s against its own proxy; UI promises 3 write-backs, proxy does 1 (WIRES LIE, demo-killer)
- **Where:** `src/app/console/review/[id]/page.tsx:164-171` sends `{action:"create_employee", candidateId}` · `src/app/api/approve/route.ts:74-80` requires `{action, body:{…}}` → `400 Missing body` · `src/lib/store.ts:36-40` (other review variant `src/components/review/review-client.tsx:548`) sends `{candidateId}` with no `action` → `400 Missing action` · route only implements single-shot `create_employee|assign_laptop|reroute`, never the 3-step staged plan (`it.equipment.assign` + `it.ticket.claim` + `hr.rbac.grant` from `src/lib/data.ts:172-194`).
- **Impact:** judge clicks "Approve & activate" on CAND-002 → red "Approval refused (400)" on the projector. Replay shows the same error. The receipt/cached-replay story (plan §5, 60s beat 32–48s) cannot happen against a live backend.
- **Fix cost:** S (1–2h) — make one contract: `{action, body, ticket_id}` + `Idempotency-Key` header; review page fans out the 3 staged calls (or adds one `activate` proxy that does); surface the proxy's `hold_conflict|duplicate` hint (route.ts:10-24) in the Alert instead of `detail ?? error`.

### D2 — Seed / Reset buttons 400 always (contract mismatch)
- **Where:** `src/app/console/page.tsx:219-223` posts `JSON.stringify({action})` · `src/app/api/demo/route.ts:46-56` requires `{target:"seed"|"reset"}` → `400 Missing target` every click; toast shows "Seed failed · POST /api/demo returned 400".
- **Impact:** judge/operator cannot re-arm the Monday batch on stage; empty-queue state (`page.tsx:509-526`) tells them to "Seed the Monday batch" with a button that fails. Recovery story (P1→P3) dies.
- **Fix cost:** XS (10 min) — send `{target: action, system:"both"}`; pass through the proxy's `guarded (403 ALLOW_DEMO_SEED)` branch (demo/route.ts:104-109) as "seed guard on — rerun with confirm" instead of generic failure.

### D3 — `onboard-api.ts` typed client targets routes that don't exist (dead wiring, CORS story false)
- **Where:** `src/lib/onboard-api.ts:28-30,324-463` fetches `/api/hr/*`, `/api/it/*` (`hr_list_candidates`, `hr_get_oncall`, `it_sla_breach_list`, …) · only `/api/{approve,demo,breaches,candidates,audit,inject}` exist (glob `src/app/api/**/*`); no `src/app/api/hr/**` or `it/**` handlers. Nothing imports `onboard-api.ts` (console/review use `/api/candidates|breaches|demo?oncall=1` + static `data.ts`).
- **Impact:** ARCHITECTURE "two systems → two MCP servers → one copilot" reads as live, but the UI never touches HR :8001 / IT :8002 shapes (`candidate_id` vs `id`, `ticket_id` vs `id`, `Oncall` vs `OncallState`). Any judge question ("show me the real breach list") exposes mocks. CORS claim ("same-origin proxies stay intact", `next.config.ts:6`) is true for the used paths but the documented client bypasses it.
- **Fix cost:** M (2–4h) — either implement `/api/hr/[...path]` + `/api/it/[...path]` passthroughs with `HR_BASE`/`IT_BASE`, timeout, `Idempotency-Key` forward, and switch pages to the client; or delete `onboard-api.ts` and relabel the UI "seeded preview (mock)" so it stops claiming `hr_service · GET /hr/candidates` (`console/page.tsx:494-496`).

### D4 — Audit page silently substitutes static chain on fetch failure; "chain verified · 0 breaks" is hardcoded
- **Where:** `src/app/audit/page.tsx:38-42` `.catch(() => setEntries(AUDIT_TAIL))` with no error state · `page.tsx:69-73` badge always "chain verified" · `src/app/api/audit/route.ts:4-11` returns static `AUDIT_TAIL` + `chainVerified:true` (no hash check) · `src/lib/data.ts:268-325` seq 91→96 fixed.
- **Impact:** checklist R1 violation in the exact artifact the safety story depends on (plan §5 ledger). Dead backend projects a healthy hash chain; judge can't distinguish live record from canned JSON. Session receipts (`store.ts` persist) can disagree with the static tail with no reconciliation.
- **Fix cost:** S (1h) — keep static fallback but banner it ("showing canned tail — /api/audit unreachable, status X"); compute `prevHash→hash` linkage client-side and flip badge to "UNVERIFIED" on break; show `entries[].seq` range dynamically instead of hardcoded "seq 91 → 96".

### D5 — Backend-status dot reports "online" when both backends are down
- **Where:** `src/components/app/app-shell.tsx:28-32` sets `online` on `res.ok` · `src/app/api/demo/route.ts:184-195` returns HTTP 200 with `{ok:false}` when one backend is reachable, and 200-with-`ok:false` masks single-backend outages; only double-total-failure yields 502.
- **Impact:** header dot glows green while HR or IT is dead; judge trusts the "staged from live services" framing until an action 502s. 30s poll (`app-shell.tsx:37`) with no manual retry.
- **Fix cost:** XS (20 min) — treat as online only if `data.ok===true`; else `offline` with tooltip naming the failing upstream (`upstream.hr_status/it_status` already returned); add click-to-recheck.

### D6 — H5/L1 live-discover moment has no UI; review hardcodes the on-call citation
- **Where:** console on-call panel (`console/page.tsx:638-705`) correctly handles `available:false` from `/api/demo?oncall=1` (`demo/route.ts:134-136`), but nothing references **L1** `GET /it/oncall-coverage` / `it_oncall_coverage` (plan §2, ARCHITECTURE tool table) · review citations (`[id]/page.tsx:491-512`, `data.ts:210-219`) hardcode `HR-ONCALL-H5 · Ravi K.` hash `2ab8f0c3d4` · no "H5 not yet discovered" disabled state (checklist C5), no refresh-tools/discover affordance (A3).
- **Impact:** the 60s live beat ("add L1 on stage → discover → re-route", plan §6) is unprojectable — there is no panel that changes when `--discover` runs. A baseline without H5 looks identical to post-discover.
- **Fix cost:** S (1–2h) — add on-call-coverage card (owner vs needs_reroute per breaching ticket) fed by a new `/api/coverage` proxy; when `available:false`, show "H5 not yet discovered — run synapse build --discover" and disable reroute-claim with that explanation.

### D7 — Theme/token split: v3 config reads hex vars through `hsl()`, custom tokens only exist in v4 `@theme`
- **Where:** `tailwind.config.ts:13-52` maps colors as `hsl(var(--background))` etc. · `globals.css:61-96` defines `--background:#f2ede2` (hex, not channels) → `hsl(#f2ede2)` invalid wherever the v3 pipeline resolves it · `bg-caution/10 text-caution bg-espresso bg-paper-deep text-espresso-foreground` (console/review/audit throughout) exist only in `@theme inline` (`globals.css:41-44`), absent from the v3 `extend` · no `ThemeProvider`/`next-themes` despite a full `.dark` block; `reactStrictMode:false` (`next.config.ts:11`) hides double-effect fetch bugs.
- **Impact:** build-pipeline-dependent color breakage (works under v4 light, silently wrong/missing under v3 or dark): severity chips, STAGED watermark (`watermark-band`), espresso receipt bands — the highest-contrast judging elements. No dark toggle means `.dark` palette is dead weight on projector.
- **Fix cost:** S (1h) — pick one pipeline: v4 `@theme` (delete v3 `extend` color block or convert to `rgb(var(--x)/<alpha-value>)` channel vars) or pin v3 with channel vars; add explicit fallback text colors on `bg-primary/10`-style translucents; either wire `next-themes` or delete `.dark` to stop implying a mode that can't trigger.

### D8 — Projector legibility + judge-trust nits that compound in 60s (counts, receipts, tiny mono)
- **Where:** `console/page.tsx:316-318` `StatChip approvedCount/2` hardcodes `/2` with 3 candidates; `316` `ticketsTotal:11` (`data.ts:78`) vs 3 rendered breaches; review receipt `R-0092` (`store.ts:22`) and audit `R-0092` pin (`audit/page.tsx:230-232`) regardless of candidate; `BUILD_OUTPUT` (`data.ts:327-336`) claims `HR 12 · IT 18` vs ARCHITECTURE-verified `HR 9 + IT 11 = 20`; body/JSON at `font-mono text-[10-11.5px]` (`console:328,364,446`, review `receipt` dl, audit `page:175-177`) violates checklist P2 (≥16px body / ≥14px JSON); `API docs → http://localhost:8001/docs` (`app-shell.tsx:17`) dead on any non-localhost projection; `persist` (`store.ts:74`) makes "ACTIVE" survive refresh/new candidate, so a second judge sees the first judge's approval.
- **Impact:** each alone is cosmetic; together the projector shows numbers that don't add up, a receipt that doesn't match the candidate, and JSON the back row can't read — exactly what P1–P4 + "one verdict banner" were meant to prevent.
- **Fix cost:** XS–S (≤1h total) — derive counts (`breaches.length`, `candidates.length`, session receipt per candidate), render `BUILD_OUTPUT` from `/api/demo` status or relabel "last verified output", bump result/receipt/banner type to ≥14px mono, make API-docs href relative/env-driven, scope `persist` to sessionStorage or add visible "Reset demo clears local approvals" (button already exists in shell — link the two).

---

## What was skimmed vs not re-verified
- Skimmed, not executed: `db.ts`, `team.ts`, `hooks/use-toast.ts`, `site/*` landing, `Caddyfile`, backend `hr_service/it_service` (not in this workspace snapshot — proxy targets `HR_BASE`/`IT_BASE` default `127.0.0.1:8001/8002`).
- Note: the file at `console/review/[id]/page.tsx` changed between reads (16-line `ReviewClient` wrapper → 653-line self-contained page); both variants are cited in D1. If both exist on different branches, delete one — two approve contracts is itself a judging hazard.
- Not a defect (confirmed good): breach/candidate/on-call loading + error + empty states with retry (`console/page.tsx:95-135,370-379,499-526,655-680`); review load-error + retry (`[id]/page.tsx:229-257`); seed/reset + approve buttons disable in-flight (`console:289-299`, `[id]:160,608`); `next.config.ts:6` same-origin proxy comment; demo proxy timeout + 403-guard surfacing (`demo/route.ts:9-25,104-109`); approve 409 hold/duplicate mapping exists server-side (`approve/route.ts:10-24`) — it just never reaches the UI.

## Suggested fix order (judging ROI)
1. D1 approve contract → 2. D2 seed/target → 3. D5 status-dot honesty → 4. D4 audit fallback banner → 5. D8 counts/receipt/type → 6. D6 L1 coverage card → 7. D3 client-or-mock decision → 8. D7 theme pipeline pick.
