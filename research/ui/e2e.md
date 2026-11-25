# E2E Verification — Next.js proxies (:3000) → HR (:8001) / IT (:8002)

Date: 2026-11-25 (UTC) · Runner: e2e lane · Base: `workspace-25f2ad75-4340-469c-8a6d-0acc097f4f32`

## Environment (as found)

- **Next dev on :3000 was DOWN on arrival** (curl `000`, nothing listening on 3000/8001/8002).
  Started with `bun run dev` in background (1st try, up within ~1 min). No reboot of backends was performed.
- **Backends :8001 (HR) + :8002 (IT) are DOWN, not RUNNING.** Direct probes
  `GET 127.0.0.1:8001/hr/demo/status` and `GET 127.0.0.1:8002/it/demo/status`
  both return empty / connection-refused. `netstat` shows no listeners on 8001/8002.
  Per lane rules no backend was started or reseeded.
- Consequence: every live-proxy route honestly reports `upstream_unreachable` (502);
  seed-fallback routes serve demo data labeled `demo-simulated`. This is the
  designed degraded behavior, not a route bug.
- **No test employee was created** (POST /api/approve → 502, backend unreachable,
  so no EMP-02x row exists to note — there is nothing to clean up).
- Side effect note: one malformed POST /api/inject (PowerShell quoting mangled the
  first attempt's body) recorded a default POLICY denial at audit seq 97, plus the
  valid skip-checks denial at seq 98. Both are in-memory ring only (reset on dev
  server restart); no backend or DB write occurred (`backendWrite: false`).

## Route table

| # | Request | Status | Key fields | Verdict |
|---|---|---|---|---|
| 1 | `GET /api/candidates` | **502** | `error: hr_backend_unreachable`, hint → check :8001 + HR_BASE_URL | **FAIL (backend-down)** — route surfaces 502 honestly; no seed fallback by design |
| 2 | `GET /api/candidates?id=CAND-002` | **502** | same `hr_backend_unreachable` envelope | **FAIL (backend-down)** — same reason; `?id=` single-fetch path unreachable without HR |
| 3 | `GET /api/breaches` | **200** | `mode: demo-simulated`, `backendReachable: false`, `breaches[3]`: T-5001 (P1, over 151m), T-5002 (P2, over 32m), T-5003 (P2, over 49m) | **PASS** — 3 rows as expected via seed fallback |
| 4 | `GET /api/demo` (status) | **502** | `ok: false`, `hr.error: upstream_unreachable`, `it.error: upstream_unreachable`, `upstream: {hr_status: null, it_status: null}` | **FAIL (backend-down)** — aggregate correctly reports both backends unreachable |
| 5 | `GET /api/demo?oncall=1` | **502** | `available: false`, `error: upstream_unreachable`, `detail: Cannot reach backend at http://127.0.0.1:8001/hr/oncall` | **PARTIAL** — `available: false` as expected pre-discover, but status is 502 not 200 (route returns 200+hint only on backend 404; fetch-failure maps to 502). Honest, spec expectation needs the 404-vs-unreachable distinction |
| 6 | `POST /api/approve` `{"action":"create_employee","body":{CAND-002, E2E Probe, e2e-probe@example.com, payments-core}}` | **502** | `error: upstream_unreachable`, `detail: Cannot reach backend at http://127.0.0.1:8001/hr/employees` | **FAIL (backend-down)** — no employee created, no EMP-02x row; retry when HR is up |
| 7 | `GET /api/audit` | **200** | `mode: demo-simulated`, `chainVerified: true`, `backendReachable: false`, seed seq 91–96 + ring appends (seq 97 POLICY, seq 98 DENY) | **PASS** — hash-chained ring served, inject appends observed live |
| 8 | `POST /api/inject` `{"scenario":"skip-checks"}` | **200** | `mode: demo-simulated`, `backendWrite: false`, `verdict: DENY`, `policy: policy.skip-checks-denied`, `receiptId: R-0094-D`, `auditSeq: 98` | **PASS** — DENY as expected, no tool executed |

## Evidence (raw bodies, trimmed)

- `1`: `{"error":"hr_backend_unreachable","hint":"Could not reach HR service. Check that it is running on :8001 and HR_BASE_URL is set correctly."}` HTTP:502
- `2`: same envelope as 1. HTTP:502
- `3`: `{"service":"it_service","route":"GET /it/tickets/breaches","mode":"demo-simulated","backendReachable":false,"note":"IT backend unreachable at http://localhost:8002/it/tickets/breaches; serving the 3-row seed breach list.","breaches":[{T-5001…sla:{breached:true,overMinutes:151,pct:140}},{T-5002…overMinutes:32,pct:107},{T-5003…overMinutes:49,pct:110}}]}` HTTP:200
- `4`: `{"ok":false,"duration_ms":9,"hr":{"error":"upstream_unreachable",…},"it":{"error":"upstream_unreachable",…},"upstream":{"hr_status":null,"it_status":null}}` HTTP:502
- `5`: `{"available":false,"error":"upstream_unreachable","detail":"Cannot reach backend at http://127.0.0.1:8001/hr/oncall: fetch failed"}` HTTP:502
- `6`: `{"error":"upstream_unreachable","detail":"Cannot reach backend at http://127.0.0.1:8001/hr/employees: fetch failed"}` HTTP:502
- `7`: `{"service":"audit","route":"GET /audit/tail","mode":"demo-simulated","chainVerified":true,…,"entries":[seq 91…96 seed + 97 + 98]}` HTTP:200
- `8`: `{"mode":"demo-simulated","backendWrite":false,"scenario":"skip-checks","verdict":"DENY","policy":"policy.skip-checks-denied","receiptId":"R-0094-D",…,"auditSeq":98,"auditHash":"547e8dc95f"}` HTTP:200

## Summary

- **Next-blocked? NO** — dev server started 1st try, all 8 routes reachable. No fallback to backend-direct testing needed.
- **Pass: 3/8** (breaches, audit, inject-skip-checks). **Backend-blocked: 4/8** (candidates ×2, demo status, approve create_employee) — all return honest 502s. **Partial: 1/8** (demo oncall: `available:false` ✓, status 502 vs expected 200).
- To reach green: start HR (:8001) + IT (:8002) backends, then re-run rows 1, 2, 4, 5, 6. Expected deltas: candidates list + CAND-002 single fetch, demo `ok:true`, oncall 200-or-live-data, approve returning EMP-02x (record that row in this file on retry).
