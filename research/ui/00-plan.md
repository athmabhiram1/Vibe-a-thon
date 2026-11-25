# UI → Backend Plan (00) — Onboard Copilot web console

Authoritative backend contract (do NOT re-derive): HR FastAPI `:8001` → `/hr/candidates`, `/hr/candidates/{id}`, `POST /hr/employees`, `/hr/shifts`, `/hr/oncall` (live-later). IT FastAPI `:8002` → `/it/equipment`, `POST /it/equipment/assign`, `POST /it/tickets`, `/it/tickets/{id}`, `POST /it/tickets/{id}/reroute`, `/it/tickets/breaches` (**must be registered before `/{id}`**). Demo `POST /hr/demo/*` + `/it/demo/*`. Browser never calls `:8001/:8002` directly — everything goes through Next `/api/*` proxies.

## 1. Page → backend mapping

| Page (file) | Data it needs | API route (Next) | Backend target |
|---|---|---|---|
| `/` (`src/app/page.tsx` + `src/components/site/*.tsx`) | static marketing; hero feed mirrors breaches statically | none (static) | none — optional live: `it_sla_breach_list()` |
| `/console` (`src/app/console/page.tsx:50-58`) | breach list; candidate queue | `GET /api/breaches`, `GET /api/candidates` | `GET /it/tickets/breaches` (I6); `GET /hr/candidates` (H1) |
| `/console/review/[id]` (`[id]/page.tsx` + `review-client.tsx:165-170`) | one candidate + citations (candidate row, ticket row, on-call row); approve; replay; injection sim | `GET /api/candidates` (filter client-side today) → **should be** `GET /api/hr/candidates/[id]`; `POST /api/approve`; `POST /api/inject` | `GET /hr/candidates/{id}` + `GET /it/tickets/{id}` + `GET /hr/oncall?team=` (citations); approve fans out to `POST /hr/employees` (H2), `POST /it/equipment/assign` (I2, Idempotency-Key), `POST /it/tickets/{id}/reroute` (I5) |
| `/audit` (`src/app/audit/page.tsx:39-43`) | hash-chained tail + session receipts | `GET /api/audit` | ledger tail (safety-check/MCP ledger or `seed/demo.db` audit table); returns `{entries, chainVerified}` |
| `AppShell` (`src/components/app/app-shell.tsx:29`) | backend health dot | `GET /api/demo` (**MISSING**) | `GET /hr/demo/status` or `/it/demo/status` (live-later) |

`layout.tsx` / `template.tsx`: no backend (fonts, metadata, page transition only).

## 2. What each `/api` route should proxy (target state)

- `src/app/api/route.ts` — **replace**: hello-world stub (`:1-5`) → service index `{hr, it, demo, audit}` or delete. Owner rewrites, no other editor touches.
- `src/app/api/candidates/route.ts` — `GET` → `{HR}/hr/candidates` (passthrough query); on offline/`NEXT_PUBLIC_DEMO_MODE=static`, return `CANDIDATES` from `lib/data.ts` with `source:"snapshot"`. Keep response shape `{candidates}`.
- `src/app/api/breaches/route.ts` — `GET` → `{IT}/it/tickets/breaches`; attach `sla` via `slaState()`; snapshot fallback `BREACH_TICKETS`. Keep `{breaches}`.
- `src/app/api/audit/route.ts` — `GET` → ledger tail; verify `prevHash→hash` server-side, return `{entries, chainVerified}`. Snapshot fallback `AUDIT_TAIL`.
- `src/app/api/approve/route.ts` — orchestrator, already live-shaped: `POST {action, body, ticket_id?}` → `create_employee→POST {HR}/hr/employees`, `assign_laptop→POST {IT}/it/equipment/assign` (forwards/generates `Idempotency-Key`, `:85-87`), `reroute→POST {IT}/it/tickets/{id}/reroute`; 409 → `hold_conflict`/`duplicate` (`:10-24`). **Fix**: reads `HR_BASE`/`IT_BASE` (`:3-4`) but `.env` defines `HR_BASE_URL`/`IT_BASE_URL` → rename to match `.env`.
- `src/app/api/inject/route.ts` — `POST` → static denial `R-0093-D` today (`:11-17`); live: append `DENY` to ledger then return receipt. Fine as-is for demo.
- **NEW** `src/app/api/hr/candidates/[id]/route.ts`, `.../employees/route.ts`, `.../shifts/route.ts`, `.../oncall/route.ts` — thin GET/POST passthroughs to H1–H5 (oncall: map backend 404 → `{present:false}` per `onboard-api.ts:370-385`).
- **NEW** `src/app/api/it/equipment/route.ts`, `.../equipment/assign/route.ts`, `.../tickets/route.ts`, `.../tickets/breaches/route.ts`, `.../tickets/[id]/route.ts`, `.../tickets/[id]/reroute/route.ts` — thin passthroughs to I1–I6. **Order trap**: `breaches` file-route must exist independent of `[id]` (Next file routing already guarantees no shadowing, unlike FastAPI def order — still, keep both and test `/breaches` ≠ 404).
- **NEW** `src/app/api/demo/status/route.ts` (+ `seed`, `reset`) and `GET /api/demo` health — backs `AppShell` status dot and `demo_seed/demo_reset/demo_status` in `onboard-api.ts:479-499`.

## 3. Placeholders / stubs found (`file:line`)

1. `src/app/api/route.ts:3-5` — hello-world `GET` stub; replace with service index.
2. `src/lib/store.ts:22` — `const RECEIPT = "R-0092"` dead const (server receipt `data.receiptId` is used, `:41`); delete.
3. `src/lib/store.ts:36-40` — `approve()` POSTs `{candidateId}` to `/api/approve`, but that route requires `{action, body, ticket_id?}` (`api/approve/route.ts:64-72`) → **contract break**: approve always 400s today; align one side (§5 #1).
4. `src/app/api/approve/route.ts:3-4` — env names `HR_BASE`/`IT_BASE` don't match `.env` `HR_BASE_URL`/`IT_BASE_URL` → always falls back to `127.0.0.1`; rename.
5. `src/components/app/app-shell.tsx:29` — `fetch("/api/demo")` → route doesn't exist → status dot permanently `offline`; fixed by NEW demo health route.
6. `src/components/app/app-shell.tsx:17` — `API_DOCS_HREF = "http://localhost:8001/docs"` hardcoded; move to env.
7. `src/components/review/review-client.tsx:190-194` — offline fallback to canned `getCandidate(id)` snapshot with `backendUnreachable` banner; keep intentionally (venue-Wi-Fi story) but label `source:"snapshot"` in UI.
8. `src/app/audit/page.tsx:230-232` — hardcoded `R-0092` stamp; render `sessionApprovals[0].receiptId` instead.
9. `.env:1` — `DATABASE_URL=file:/home/z/my-project/db/custom.db` (foreign path); point at workspace `seed/demo.db` or drop if ledger lives in backend.
10. `.env:6-7` — `NEXT_PUBLIC_HR_URL=` / `NEXT_PUBLIC_IT_URL=` empty (same-origin proxy mode — correct, keep; document).
11. `src/lib/data.ts:1-7` — header comment admits static dataset pending backend integration; keep as snapshot, add `source` field per payload.
12. `src/lib/onboard-api.ts` (whole file) + `src/lib/db.ts` (whole file) — **dead code**: zero importers (grep). Either wire in (§5) or delete; do not leave both client + `db.ts`-Prisma paths half-alive.

## 4. Missing pieces (build list)

- [ ] NEW `/api/hr/*` (4 routes) and `/api/it/*` (6 routes) proxies; test `breaches`-before-`[id]` explicitly.
- [ ] NEW `/api/demo/*` (`status` GET, `seed`/`reset` POST) + `GET /api/demo` health.
- [ ] Approve contract alignment: store sends staged `{action, body}` fan-out (recommended) vs approve route accepts `{candidateId}`.
- [ ] Review page fetches `GET /api/hr/candidates/[id]` (+ ticket + oncall for citations) instead of full-list filter (`review-client.tsx:165-170`).
- [ ] Audit tail served from real ledger with server-side chain verification; `chainVerified` drives the badge (`audit/page.tsx:69-73`), not a constant.
- [ ] Denial path records `DENY` to ledger when live (inject route).
- [ ] Env hygiene: rename `HR_BASE/IT_BASE` → `HR_BASE_URL/IT_BASE_URL`; fix `DATABASE_URL`; document empty `NEXT_PUBLIC_*` = proxy mode.
- [ ] Decide Prisma: `lib/db.ts` + `prisma/` either backs the audit ledger or is deleted (no half-wiring).
- [ ] Decide `onboard-api.ts`: adopt as the single browser client (recommended — already typed for H1–H5/I1–I6 + timeouts + 404/409 mapping) and refactor `console/page.tsx`, `review-client.tsx`, `audit/page.tsx` onto it; or delete it.
- [ ] Landing (`site/*`) stays static — only optional change: hero feed via `it_sla_breach_list()`.

## 5. File-ownership map — 19 parallel editors (disjoint files)

| # | Owner | Files (exclusive) | Task |
|---|---|---|---|
| E01 | api-candidates | `src/app/api/candidates/route.ts` | proxy HR list + snapshot fallback |
| E02 | api-breaches | `src/app/api/breaches/route.ts` | proxy IT breaches + `sla` attach |
| E03 | api-audit | `src/app/api/audit/route.ts` | ledger tail + chain verify |
| E04 | api-approve | `src/app/api/approve/route.ts` | env rename + contract decision + 409 mapping |
| E05 | api-inject | `src/app/api/inject/route.ts` | denial + live ledger append |
| E06 | api-hr-new | `src/app/api/hr/**` (all NEW) | H1–H5 thin proxies |
| E07 | api-it-new | `src/app/api/it/**` (all NEW) | I1–I6 thin proxies, breaches-vs-[id] test |
| E08 | api-demo-new | `src/app/api/demo/**` (all NEW, incl. `GET /api/demo`) | health/status/seed/reset → demo routers |
| E09 | api-index | `src/app/api/route.ts` | service index, remove hello-world |
| E10 | page-console | `src/app/console/page.tsx` | adopt client, loading/error/empty states |
| E11 | page-review-shell | `src/app/console/review/[id]/page.tsx` | server fetch + metadata (keep thin) |
| E12 | review-client | `src/components/review/review-client.tsx` | adopt client, approve fan-out, replay, snapshot label |
| E13 | page-audit | `src/app/audit/page.tsx` | live tail, verify badge, real receipt id |
| E14 | app-shell | `src/components/app/app-shell.tsx` | health via demo status, docs href env |
| E15 | lib-data | `src/lib/data.ts` | snapshot source labels, type-align to Pydantic shapes |
| E16 | lib-store | `src/lib/store.ts` | align payloads, drop dead `RECEIPT`, keep persist key |
| E17 | lib-client | `src/lib/onboard-api.ts` | single browser client; exported contract for E10/E12/E13 |
| E18 | lib-db | `src/lib/db.ts` + `prisma/*` | ledger-or-delete decision |
| E19 | site-static | `src/components/site/*` (10 files) + `src/lib/team.ts`, `src/app/page.tsx`, `layout.tsx`, `template.tsx` | static only; no backend calls; hero-live optional |

Rules: no editor touches another's files; shared contracts (`onboard-api.ts` shapes, approve POST body, fallback `{source:"snapshot"}` envelope) are agreed from §2 before coding; E06/E07/E08 create NEW paths only so they never collide with E01–E05.
