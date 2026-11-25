# Track 1 — Make a Legacy App Agent-Ready (Synapse Auto) — Brainstorm

> Context: Vibe-a-thon Track 1. Synapse CLI v0.1.9 generates Python MCP servers from code. `Auto` = static HTTP route detection (it greps for explicit `@app.get/post/put/delete`, Flask `@route`, Django `path()` — no dynamic routers, no `add_url_rule` loops, no auth-gated magic). Requires a **deployed API** (Render / Railway / HF Space / Render free tier) so judges can call the MCP server live.
> Anti-slop rule: NO generic inventory-reorder, library-book CRUD, clinic-appointment CRUD, support-ticket chatbot.

## Prior-art check (default.websearch, Nov 2026)
- Devfolio "Push to Prod" (Genspark x Claude, Apr 2026): winners = ConnectCrew (AI CRM relationship graph), Vendor Wrangler (vendor handling), Unscatter — all generic CRM/vendor wrappers. **Lesson: CRM/procurement-chatbot = slop zone now.**
- Solo.io 2026 MCP & AI Agents Hackathon: winners = Frugalia (FinOps waste detector), MIMIC-IV clinical query federation, MCP governance scorer. **Lesson: single-query read-only MCP + "ask my DB" demos already won; judges now expect multi-step state-changing tasks with evidence gates.**
- SORINT legacy-modernization hackathon case study (Sep 2026): winning playbook = ingest unmapped legacy codebase → reverse-engineer business logic → rebuild with IaC + compliance. **Lesson: frame Track 1 as "reverse + expose + orchestrate", not "chat over rows".**
- Fiberplane Vibe Summer 2025: winners = Screenshift (16-tool MCP), Executive Assistant nightly summaries via n8n+MCP. **Lesson: 10-16 tool servers with orchestration beat 3-tool CRUD wrappers.**
- Implication for Synapse Auto: pick legacies with **real workflow state machines** (approvals, recalls, inspections, allocations) where the agent must call 3-5 tools in order with conditional logic. Pure `GET /products` legacies lose.

## Synapse Auto constraints (from CLI v0.1.9 behavior)
1. Static detection only — every exposed endpoint must be a literal decorator in a `*.py` file: `@app.get("/api/v1/...")`. No factory loops.
2. Needs deployed API — legacy itself can be heavy (Java/PHP) IF we ship a thin **FastAPI proxy** (`proxy/main.py`) with explicit routes that forwards with `httpx` + caches JWT. Auto scans the proxy, not the legacy.
3. Python-native legacies (Frappe/ERPNext, Django, Flask) are lowest risk: Auto scans them directly.
4. Auth: bake demo creds into env vars on the deployed proxy; expose `POST /demo/seed` + `POST /demo/reset` so judges get deterministic state.

## Context7 note
- Code Mode `search()` discovered `tools.context7["resolve-library-id"]` + `tools.context7["query-docs"]`. Recommended lookups during build: `/tiangolo/fastapi` (explicit route patterns, JWT via `OAuth2PasswordBearer`), `/pallets/flask` (static `@app.route` patterns), `/django/django` (`urlpatterns` explicit `path()`). Use these to keep proxy code Auto-compatible. Do not use dynamic `APIRouter` includes across files for the judged surface.

---

### Idea 1 — Eden Shelter-Match Operator
- **Legacy system + repo:** Sahana Eden — humanitarian disaster-management (Python / Web2py, GPL) — https://github.com/sahana/eden — live demo: https://demo.sahanafoundation.org (or self-host `docker run` image `sahana/eden`)
- **Agent tasks (each 3-5 tool calls):**
  1. `intake-surge`: `POST /shelter/search` (capacity, lat/lon) → `POST /request/match` (unmet shelter requests within 20km) → `POST /allocation/propose` (bin-pack families to beds respecting medical flags) → human approves.
  2. `relief-convoy`: `GET /warehouse/stock` (blankets, water) → `POST /shipment/plan` (multi-warehouse split respecting expiry) → `POST /shipment/commit`.
  3. `duplicate-victim-dedupe`: `GET /person/search?name=` fuzzy → `POST /person/merge` (keeps earliest registration, moves aid entitlements) → `GET /audit/log`.
- **Endpoints to expose + why:** `GET /shelter/search`, `POST /allocation/propose`, `GET /warehouse/stock`, `POST /shipment/plan`, `POST /shipment/commit`, `GET /person/search`, `POST /person/merge`, `POST /demo/seed|reset`. Why: allocation + shipment are transactional multi-step with constraints (capacity, expiry, distance) — impossible as single CRUD; perfect MCP tool chain.
- **Why not slop:** disaster-triage with geospatial + constraint solving; no Devfolio winner touches shelter logistics; demo uses real Sahana data model (dvr_case, req_req, inv_inv_item).
- **Demo risk: 2/5** — Eden demo instance is public; proxy is simple read + propose/commit split. Risk is Web2py session auth → mitigate with service-account + proxy-side token cache.

### Idea 2 — EDMS Compliance Vault Auditor
- **Legacy system + repo:** Mayan EDMS — document management (Python / Django, Apache-2.0) — https://github.com/mayan-edms/mayan-edms — docker: `mayanedms/mayanedms`; REST API docs built-in `/api/v4/`
- **Agent tasks:**
  1. `retention-sweep`: `GET /documents/expired?policy=7y` → `GET /documents/{id}/versions` → `POST /documents/{id}/quarantine` (legal hold check first) → `POST /audit/report`.
  2. `pii-redaction-pass`: `GET /documents/unscanned` → `POST /ocr/scan` → `POST /redaction/apply` (SSN/IBAN regex hits) → `POST /documents/{id}/reindex`.
  3. `chain-of-custody-proof`: `GET /documents/{id}/events` → `POST /custody/export` (signed hash chain PDF) for auditor.
- **Endpoints to expose + why:** `GET /documents/expired`, `GET /documents/{id}/versions`, `POST /documents/{id}/quarantine`, `POST /ocr/scan`, `POST /redaction/apply`, `GET /documents/{id}/events`, `POST /custody/export`, `POST /demo/seed`. Why: Django-native routes → Auto scans directly; versioning + ACL + workflow states give agent real branching (hold vs. destroy).
- **Why not slop:** compliance-audit with hash-chain evidence, not "upload/download files"; maps to SORINT evidence-gate pattern judges already rewarded.
- **Demo risk: 1/5** — pure Python/Django, Docker one-liner, seeded PDFs included. Lowest risk pick.

### Idea 3 — Gradebook Rescue Planner (Moodle)
- **Legacy system + repo:** Moodle LMS (PHP, GPL-3.0) — https://github.com/moodle/moodle — REST: `core_grades_*` + `mod_quiz_*` web services; sandbox: https://sandbox.moodledemo.net (reset hourly)
- **Architecture for Auto:** thin FastAPI proxy `proxy/moodle_proxy.py` with explicit `@app.get("/api/v1/course/{id}/at-risk")` etc. forwarding to Moodle tokens via `httpx`. Auto scans proxy.
- **Agent tasks:**
  1. `at-risk-triage`: `GET /course/{id}/at-risk?threshold=60` (gradebook join) → `GET /student/{id}/activity` (last login, missing quizzes) → `POST /intervention/plan` (nudge vs. office-hour vs. retake path).
  2. `quiz-gap-fill`: `GET /quiz/{id}/item-analysis` (worst 3 questions) → `POST /quiz/remediation-pack` (generates practice set linked to outcomes) → `POST /calendar/schedule`.
  3. `plagiarism-hold`: `GET /assignment/flagged` → `POST /assignment/hold-grade` → `POST /message/send` (advisor notice with evidence links).
- **Endpoints to expose + why:** `GET /course/{id}/at-risk`, `GET /student/{id}/activity`, `POST /intervention/plan`, `GET /quiz/{id}/item-analysis`, `POST /quiz/remediation-pack`, `POST /assignment/hold-grade`. Why: joins across gradebook + logstore + quiz stats force multi-call reasoning; intervention plan is a write with policy guardrails.
- **Why not slop:** pedagogy-aware orchestration (outcome mapping, item analysis), not "list courses / enroll student" CRUD that every LMS demo does.
- **Demo risk: 3/5** — Moodle sandbox resets hourly and tokens are fiddly; mitigate by snapshotting gradebook JSON into proxy cache + `POST /demo/seed` replay so live demo survives reset.

### Idea 4 — Ledger Forensics & Repair (Firefly III)
- **Legacy system + repo:** Firefly III — personal/small-biz finance (PHP / Laravel, AGPL) — https://github.com/firefly-iii/firefly-iii — first-class REST API `/api/v1/` + demo at https://demo.firefly-iii.org; docker `fireflyiii/core:latest`
- **Architecture for Auto:** FastAPI proxy with explicit routes (`/api/v1/ff/transactions/search`, `/api/v1/ff/reconcile/propose`) adding idempotency keys Firefly lacks.
- **Agent tasks:**
  1. `duplicate-hunt`: `GET /transactions/search?window=30d` → `POST /reconcile/duplicates` (amount+date+payee fuzzy clusters) → `POST /transactions/merge` (keeps attachments).
  2. `budget-bleed-fix`: `GET /budgets/{id}/spent` → `GET /recurring/overshoot` → `POST /budget/repair-plan` (move envelope vs. cut rule) → `POST /rules/apply`.
  3. `orphan-loan-match`: `GET /accounts/unreconciled` → `POST /transfer/propose` (match debits to loan credits) → `POST /transfer/commit`.
- **Endpoints to expose + why:** `GET /transactions/search`, `POST /reconcile/duplicates`, `POST /transactions/merge`, `GET /budgets/{id}/spent`, `POST /budget/repair-plan`, `POST /transfer/propose|commit`. Why: double-entry invariants + fuzzy matching require agent to gather evidence before any write; merge/commit split gives safe live demo.
- **Why not slop:** forensic accounting with invariant checks (sum-to-zero, attachment preservation), not "create expense" CRUD; FinOps winners (Frugalia) were K8s-cost, not ledger-repair.
- **Demo risk: 2/5** — Firefly demo API is stable and seedable via data importer; only risk is Laravel token expiry → proxy refresh handles it.

### Idea 5 — Fleet Compliance Dispatcher (Traccar)
- **Legacy system + repo:** Traccar — GPS tracking (Java, Apache-2.0) — https://github.com/traccar/traccar — REST `/api/devices|positions|geofences|events`; demo: https://demo.traccar.org (user `demo`) ; docker `traccar/traccar:latest`
- **Architecture for Auto:** FastAPI proxy (`/api/v1/fleet/...`) because legacy is Java; proxy adds geofence-violation state machine Traccar lacks.
- **Agent tasks:**
  1. `geofence-court`: `GET /fleet/violations?since=24h` → `GET /device/{id}/track` (positions polyline) → `POST /incident/open` (with map snapshot + driver) → `POST /notify/dispatch`.
  2. `maintenance-grounding`: `GET /fleet/odometer` → `POST /maintenance/due` (interval rules) → `POST /device/{id}/ground` (block dispatch until service).
  3. `ghost-trip-audit`: `GET /device/{id}/trips?gap=2h` (ignition-off-but-moving) → `POST /audit/flag` → `POST /geofence/suggest` (auto-tighten polygon).
- **Endpoints to expose + why:** `GET /fleet/violations`, `GET /device/{id}/track`, `POST /incident/open`, `GET /fleet/odometer`, `POST /maintenance/due`, `POST /device/{id}/ground`, `POST /geofence/suggest`. Why: spatiotemporal reasoning (polylines, gaps, odometer math) forces real agent planning; grounding is a safety-critical write judges remember.
- **Why not slop:** fleet-compliance with map evidence, not vehicle-list CRUD; zero overlap with Devfolio commerce/CRM winners.
- **Demo risk: 3/5** — Traccar demo server is public but rate-limited and GPS replay needs scripting; mitigate with recorded GPX replay in `POST /demo/seed` so demo runs offline.

### Idea 6 — Subcontract QC Loop (ERPNext, non-generic slice)
- **Legacy system + repo:** ERPNext (Python / Frappe, GPL-3.0) — https://github.com/frappe/erpnext — REST `/api/resource/*` + demo: https://demo.erpnext.com; docker `frappe/erpnext:v15`
- **Deliberately NOT inventory-reorder.** Slice is manufacturing subcontract + quality-inspection rejection chain — the part of ERPNext no hackathon touches.
- **Agent tasks:**
  1. `challan-reconcile`: `GET /subcontract/overdue-challans` (material sent vs. finished received) → `GET /stock-ledger/{item}` → `POST /challan/close-or-escalate` (short-close with scrap accounting).
  2. `qc-rejection-disposition`: `GET /quality-inspections/failed` → `GET /bom/{item}/operations` → `POST /disposition/propose` (rework vs. scrap vs. return-to-vendor with cost impact) → `POST /stock-entry/commit`.
  3. `capacity-reroute`: `GET /work-orders/delayed` → `GET /workstations/load` → `POST /work-order/reroute` (split qty across stations).
- **Endpoints to expose + why:** `GET /subcontract/overdue-challans`, `GET /quality-inspections/failed`, `POST /disposition/propose`, `POST /stock-entry/commit`, `GET /workstations/load`, `POST /work-order/reroute`, `POST /demo/seed`. Why: Frappe-native Python routes → Auto scans directly; BOM explosion + inspection + stock-entry commit is a 4-call transaction with cost math.
- **Why not slop:** explicitly bans the slop slice (reorder-level report) and picks the expert slice (subcontract challan + QC disposition) that requires domain knowledge; judges cited manufacturing depth in past enterprise tracks.
- **Demo risk: 4/5** — ERPNext Docker is heavy (~4GB, slow seed) and v15 demo creds rotate; highest risk. Mitigate: pre-seed lightweight site, record fallback JSON, or swap to Idea 2 as primary. Only pick if team has Docker RAM + time.

## Recommendation
- **Primary: Idea 2 (Mayan EDMS)** — Python-native, risk 1/5, strongest evidence-gate story, 8 explicit routes fit Auto perfectly.
- **Backup: Idea 4 (Firefly III)** — stable demo API, memorable money-repair narrative, risk 2/5.
- **Showpiece if ambitious: Idea 1 (Sahana Eden)** — humanitarian impact + geospatial wow, risk 2/5.
- Avoid Idea 6 unless the team can pre-build the ERPNext image before the event day.

## Build checklist for whichever is chosen
1. `proxy/main.py` (or native app) with 7-9 literal `@app.get/post` decorators, no loops.
2. `POST /demo/seed` + `POST /demo/reset` with <5s runtime.
3. Deployed URL in README + `synapse.json` pointing at deployed base URL.
4. 3 scripted agent transcripts (one per task) showing 3-5 sequential tool calls with a conditional branch.
5. 90-sec demo: seed → task 1 live → audit export proof.
