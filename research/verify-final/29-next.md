# 29 — Next.js proxy layer verification (:3000 → :8001/:8002)

Date: 2026-11-25 UTC · Workspace: `workspace-25f2ad75-4340-469c-8a6d-0acc097f4f32` · No files edited.

## Server state
- Dev server :3000 already UP (PID 25484 LISTENING, `/` → 200, 91 KB HTML). Zero restarts needed — no "3 tries" path triggered. NOT blocked.
- Backends untouched: :8001 `/health` → 200, :8002 `/health` → 200. (Bare `/` on both → 404, expected — no root route.)

## Status codes (curl.exe, live server)
| Route | Code | Body evidence |
|---|---|---|
| `/` | 200 | full landing HTML |
| `/console` | 200 | console page |
| `/audit` | 200 | audit page |
| `/console/review/CAND-001` | 200 | review sub-page |
| `/api/candidates` | 200 | real rows (CAND-001 Aarav Mehta…) |
| `/api/breaches` | 200 | real tickets (T-5001…) |
| `/api/demo` | 200 | `{ok:true, hr+it seeded v14, 20/20/20/20…}` |
| `/api/demo?oncall=1` | 200 | live oncall (Kiran Desai, EMP-014) |
| `/api/audit` | 200 | `demo-simulated`, chainVerified:true, ~105-entry ring |

## Proxy wiring (read-only check of `src/app/api/*/route.ts`)
- `demo/route.ts`: GET aggregates `${HR_BASE}/hr/demo/status` + `${IT_BASE}/it/demo/status`; `?oncall=1` proxies `:8001/hr/oncall`; POST seed/reset forwards with `x-demo-confirm: yes`; unreachable upstream → honest 502. Direct backend probes confirm upstreams live (`/hr/demo/status` 200, `/it/demo/status` 200, `/hr/oncall` 200).
- `audit/route.ts`: probes `:8001/:8002/audit` (+ demo/status); neither backend exposes `/audit`, so it serves the in-memory demo ring and says so (`backendReachable:false` + note). Honest labeling, chainVerified:true — acceptable for recording, not a failure.

## Fallback coverage (not needed, but confirmed)
- `C:\Users\athma\OneDrive\Desktop\my projects\VIBE_CODE\frontend.html` exists; direct-backend curl works. Backends-direct fallback covers the demo if Next ever goes down.

## Verdict
**Next-OK.** All 8 required routes 200 with real/proxied payloads. No trivial fixes needed — nothing edited.
