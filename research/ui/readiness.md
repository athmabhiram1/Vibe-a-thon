# Submission-Readiness Sweep — workspace-25f2ad75-4340-469c-8a6d-0acc097f4f32

Date: 2026-11-25 (UTC) · Mode: READ-ONLY (no workspace files edited)
Scope: `src/**/*.md`, `public/**/*.md`, `*.md`, `package.json`, README, `submission/` packet, secret scan in `src/`

## 1. Placeholder scan

Scoped searches (case-insensitive) for `lorem | TODO | FIXME | XXX | Coming soon | example.com | your-key-here | 12345` (+ `placeholder` where noted):

| Scope | Pattern | Result |
|---|---|---|
| `src/**/*.md` | all placeholders | **0 matches — CLEAN** |
| `public/**/*.md` (no `.md` files in `public/`) | all placeholders | **0 matches — CLEAN (vacuous; only `favicon.svg`, `logo.svg`, `robots.txt` present)** |
| `src/` all files: `lorem\|Coming soon\|your-key-here\|example.com` | subset | **0 matches — CLEAN** |
| `public/` all files: same subset | subset | **0 matches — CLEAN** |
| Whole workspace: `lorem\|TODO\|FIXME\|XXX\|Coming soon\|example.com\|your-key-here\|12345` | full | 2 matches, both benign (see table below) |

### Placeholder hit table (file:line + owner lane)

| # | File:line | Hit | Verdict | Fix / owner lane |
|---|---|---|---|---|
| 1 | `bun.lock:1087` | `...fastq-1.20.1.tgz...` (matches `12345`-adjacent numeric pattern only via hash fragment) | **False positive — lockfile dependency hash, NOT a placeholder. Leave alone.** | No action. Lane: — |
| 2 | `scripts/oc/verify_static.js:51` | `for (const p of ["TODO", "XXX", "【", "placeholder", "lorem"]) {` — the repo's own static-check denylist | **Intentional guardrail, NOT a placeholder. Leave alone.** | No action. Lane: — |

No `lorem`, `Coming soon`, `example.com`, `your-key-here`, `TODO`/`FIXME` placeholders found in `src/`, `public/`, or any `*.md`. No cleanup edits needed; workspace untouched.

## 2. package.json name/version + rename proposal (NOT applied)

- Current: `name: "nextjs_tailwind_shadcn_ts"`, `version: "0.2.1"`, `private: true`
- Scripts: `dev: next dev -p 3000`, `build: next build + standalone copy`, `start: bun .next/standalone/server.js`, `lint`, `db:push/generate/migrate/reset` (prisma)
- Proposal (per request, **do NOT rename — propose only**): rename to **`onboard-copilot-track3`**
  - Why: current name is the generic scaffold default; proposed name matches submission track identity.
  - Lane: **Track lead / release owner** — rename `package.json:name`, verify `bun.lock` name field (if present), CI/badge references, and any docs mentioning the old name. Do not rename in this sweep.

## 3. README presence / accuracy

| Check | Result |
|---|---|
| Root `README.md` | **MISSING** — only `*.md` in workspace is `download/README.md` (1 line: "Here are all the generated files."). No root README. |
| 3-command quickstart | **ABSENT** (no README to contain it). Reconstruct from `package.json` + `Caddyfile`: `bun install` → `bun run dev` (port 3000) → `bun run build && bun run start`. DB steps (`db:push`/`db:generate`) undocumented. |
| Backend ports documented? | **NO** — ports only discoverable in code: frontend `3000` (`package.json:dev`, `Caddyfile:16` reverse-proxy `localhost:3000`), HR backend default `8001` (`src/lib/onboard-api.ts:15`, `src/app/api/approve/route.ts:3`), IT backend default `8002` (`onboard-api.ts:21`, `approve/route.ts:4`), API docs link `http://localhost:8001/docs` (`src/components/app/app-shell.tsx:17`), demo hint `demo · localhost:3000` (`src/components/site/team.tsx:84`). Env overrides `NEXT_PUBLIC_HR_URL` / `NEXT_PUBLIC_IT_URL` / `HR_BASE` / `IT_BASE` are also undocumented. |

Gap: **add root `README.md`** with 3-command quickstart, ports/env table (3000 / 8001 / 8002), and backend startup instructions. Lane: **Docs / DX owner**.

## 4. submission/ packet → frontend links

| Check | Result |
|---|---|
| `submission/**/*` glob | **No files found — packet does not exist in workspace.** |
| Case-insensitive variants (`submission*`, `packet*`, `SUBMISSION*`, `docs/`) | **No files found.** |
| Links to frontend | **N/A — nothing to verify.** |

Gap: **create `submission/` packet** (or point to its canonical location) with links to frontend entry (`/` on `:3000`), API docs (`http://localhost:8001/docs`), and demo path referenced in `team.tsx:84`. Lane: **Submission / track owner**.

## 5. Secret scan in `src/`

| Pattern | Result |
|---|---|
| `sk-`, `ghp-`, `Bearer <token>`, `xox[bap]-`, `AKIA`, `secret[_-]?key` (broad) | Only hit was `mask-*` CSS in `src/app/globals.css:196-201` (`mask-image`, `mask-size`, `mask-repeat`) — **false positive on substring `sk-`/`mask-`. No secrets.** |
| Strict: `sk-(proj\|live\|test)`, `ghp_…`, `gho_`, `github_pat_`, `xox[bap]-`, `AKIA…`, `AIza…`, `Bearer <token>` | **0 matches — CLEAN** |

Additional hygiene: `.env` exists at workspace root (contents not read); `.gitignore:34` correctly ignores `.env*`. `Caddyfile` exposes only `localhost:3000` proxy + `XTransformPort` query — no credentials. Recommend pre-submit `git log --all -p | grep` + GitHub secret-scanning passkey check before publishing. Lane: **Security / release owner (verify only)**.

## 6. Packet gaps / pre-submit checklist

1. [ ] Add root `README.md` (3-cmd quickstart, ports 3000/8001/8002, env vars, DB commands) — Docs/DX lane
2. [ ] Create `submission/` packet with frontend + API-docs links — Submission lane
3. [ ] Rename `package.json` → `onboard-copilot-track3` (proposal only, not done) — Track lead lane
4. [ ] Confirm `.env` never committed (`git status --ignored`); rotate any exposed keys — Security lane
5. [ ] Decide on hardcoded `localhost` URLs (`onboard-api.ts:15,21`, `approve/route.ts:3-4`, `app-shell.tsx:17`, `team.tsx:84`) for non-local demos — Backend/frontend lane

*Report written to `research/ui/readiness.md`. Workspace files were not modified.*
