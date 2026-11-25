# UI Greenpass — workspace-25f2ad75-4340-469c-8a6d-0acc097f4f32

Date: 2026-11-25 (UTC) · Mode: READ-ONLY (no workspace files edited; dev server started via `npx next dev -p 3000` only because the `bun run dev` script pipes through `tee`, which is missing on Windows)
Workspace: `workspace-25f2ad75-4340-469c-8a6d-0acc097f4f32` · Report: `research/ui/greenpass.md`

## Verdict: CONDITIONAL GO — demo-able now, 4 code FIXes + 3 doc/packet FIXes before submit

Nothing blocks a live venue demo (all pages/APIs 200, backends reachable). No FIX below breaks runtime today, but the FIX list must be cleared (or explicitly waived) before submission.

## 1. `npx tsc --noEmit` — 10 errors at time of run (see `tsc-out.txt` in workspace root)

| # | Error | Status at end of pass | Owner |
|---|---|---|---|
| 1–2 | `examples/websocket/*`: missing `socket.io` / `socket.io-client` types | OPEN, low priority — examples dir, not app runtime. Either `bun add -D socket.io socket.io-client` or exclude from tsconfig | Examples owner |
| 3–5 | `src/app/api/demo/route.ts:108,110,111`: `Cannot find name 'guarded'` | LIKELY FIXED after tsc run — file now declares `guardedStatus`/`guardedBody` and returns `guarded: guardedBody`; re-run tsc to confirm | E08 api-demo-new |
| 6 | `src/app/console/page.tsx:8`: `CalendarAlert` not exported from lucide-react | FIXED after tsc run — string no longer present in file (import now uses `CalendarDays`/`CircleAlert`); re-run tsc to confirm | E10 page-console |
| 7–9 | `review-client.tsx:256-257`: `data.candidate` not on `CandidatesPayload` | OPEN but runtime-safe (code falls back to `data.candidates.find(...)`). Fix type or use optional chaining | E12 review-client |
| 10 | `src/lib/db.ts:1`: `PrismaClient` not exported from `@prisma/client` | OPEN — `prisma generate` never run (or client not installed for current schema). Decide ledger-or-delete per 00-plan §4 | E18 lib-db |

Re-run `npx tsc --noEmit` after E08/E10 edits land; expect only examples + db + review-client items to remain.

## 2. Placeholder scan — CLEAN

`lorem|TODO|FIXME|Coming soon|example.com` over `src/`: **0 matches**. Only hits are legitimate `<input placeholder="…">` attributes in `examples/websocket/frontend.tsx` and type-name noise inside `node_modules`. Matches `readiness.md` §1 (2 benign hits, both false positives). No action.

## 3. Routes (dev server on :3000; backends :8001/:8002 NOT rebooted, probed only)

| Route | Status | Body check |
|---|---|---|
| `/` | 200 | full landing HTML, no error markers |
| `/console` | 200 | 42 KB HTML, no `Error:|error-boundary|Something went wrong|Application error` markers (best-effort curl check) |
| `/audit` | 200 (one transient 500 mid-pass from a stale Turbopack compile of `store.ts`, self-resolved — file on disk was already correct) | renders |
| `/api/candidates` | 200 | 20 candidates JSON |
| `/api/breaches` | 200 | 12 tickets JSON, all `breached:true` |
| `/api/demo` | 200 | `{ok:true, hr:{…}, it:{…}, upstream:{hr_status:200, it_status:200}}` |
| `/api/audit` | 200 | `{chainVerified:true, entries:[seq 91–98, hash-chained]}` |
| `:8001/hr/candidates`, `:8002/it/tickets/breaches` | 200 / 200 | backends UP (roots 404 and `/docs` unreachable = docs disabled, not outage) |

## 4. Prior-flag reconciliation (`research/ui/00-plan.md` §3 + `readiness.md` §6)

- `critic.md`, `e2e.md`, `build-health.md`: **do not exist** under `research/ui/` (only `00-plan.md` + `readiness.md` present; repo-wide glob confirms). Nothing to reconcile there.
- FIXED since flagged: `store.ts` approve contract (now sends `{action,…}` via `postApprove`, regex typo fixed) — E16; `GET /api/demo` health route exists — E08; audit page renders live `receiptId`s, no hardcoded `R-0092` stamp — E13; `CalendarAlert` import gone — E10.
- STILL OPEN: `approve`/`demo` routes read `HR_BASE`/`IT_BASE` but `.env` defines `HR_BASE_URL`/`IT_BASE_URL` (falls back to `127.0.0.1` — works locally, breaks any non-local demo) — **E04**; `DATABASE_URL=file:/home/z/my-project/db/custom.db` foreign path — **E18**; `api/route.ts` still hello-world stub — **E09**; hardcoded `http://localhost:8001/docs` in `app-shell.tsx:17` — **E14**; `review-client` `data.candidate` typing — **E12**; `lib/db.ts` vs Prisma undecided — **E18**.
- STILL OPEN (docs/packet): no root `README.md` (3-command quickstart, ports/env table) — **Docs/DX lane**; no `submission/` packet — **Submission lane**; `package.json` rename to `onboard-copilot-track3` proposal unapplied — **Track lead lane**.

## 5. FIX list (ordered)

1. E04: rename `HR_BASE`/`IT_BASE` → `HR_BASE_URL`/`IT_BASE_URL` in `approve` + `demo` routes (non-local demo breaks otherwise).
2. E12: fix `CandidatesPayload` typing in `review-client.tsx:256-257`.
3. E18: run `prisma generate` (or delete `lib/db.ts` + `prisma/`); fix `DATABASE_URL` to workspace `seed/demo.db`.
4. E08: re-run tsc to confirm `guarded` errors gone.
5. E09/E14: replace api index stub; move docs HREF to env.
6. Docs/DX + Submission + Track-lead lanes: README, `submission/` packet, rename proposal.
7. Waive or fix `examples/websocket` socket.io types.
