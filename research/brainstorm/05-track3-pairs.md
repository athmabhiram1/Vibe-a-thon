# Track 3 Pairs — Copilot Across Two Systems (Scored Brainstorm)

> Goal: each pair = two FastAPI MCP servers (System A + System B), 2+ cross-system
> questions answerable only by joining both, plus one **live `--discover` moment**
> where a brand-new endpoint is added mid-demo and picked up without restart.
> FastAPI pattern (Context7 `/websites/fastapi_tiangolo`): new `@app.get()` with
> `Annotated[FilterParams, Query()]` + `response_model=...` appears in OpenAPI/discover instantly.

Scoring rubric (1–5 each): **Join clarity** (obvious shared key) · **Question wow**
(audience gasp factor) · **Discover moment** (how crisp the live endpoint addition is) ·
**Setup ease** (docker/sample availability). **Total /20.**

---

## Pair 1 — Citizen Portal + Officer Dashboard ⭐ RECOMMENDED

- **System A (citizen-portal):** citizen request intake (FastAPI mock; real-world refs:
  `tpt-solutions/tpt-gov-nz` — `apps/portal-citizen` Next.js + `gov-dept-*` services;
  `alphagov/govuk` platform; GitHub `collections/government` civic app templates).
- **System B (officer-dashboard):** back-office caseworker triage queue (refs: `tpt-gov-nz`
  `apps/portal-staff` read-only caseworker views; OPA `.rego` consent policies as access-control model).
- **Join key:** `request_id` / `citizen_id` (portal creates → dashboard triages; status enum shared).
- **Cross Q1:** "Citizen C-1042 filed a pothole report — what is its officer-side status, assigned team, and SLA clock?"
- **Cross Q2:** "List all citizen requests still marked 'submitted' in the portal but already 'resolved' in the dashboard — i.e., status drift / un-notified citizens."
- **Live `--discover` endpoint:** `GET /requests/{id}/sla-countdown` (computes hours-left from `filed_at + sla_hours - now`, Pydantic `SLACountdown` response_model). Added live to officer-dashboard; copilot re-discovers and answers "which 3 requests breach SLA in the next 24h?"
- **Score:** Join 5 · Wow 5 · Discover 5 · Setup 5 = **19/20**. Cheapest to mock, most relatable narrative.

## Pair 2 — FHIR Clinic + Insurance OpenIMIS

- **System A (fhir-clinic):** clinical encounters (real: `hapifhir/hapi-fhir-jpaserver-starter`
  `docker compose up -d` → `http://localhost:8080/fhir`; image `hapiproject/hapi:latest`; Postgres-backed).
- **System B (insurance-openimis):** payer claims/policies (real: `openimis/openimis-dist_dkr`
  all-inclusive docker package; `openimis.org` docs; CHT interoperability guide `docs.communityhealthtoolkit.org/building/interoperability/openimis/`).
- **Join key:** `patient_id ↔ insuree_number` (mapping table `patient_to_insuree`); secondary join `encounter_date ↔ claim_date`.
- **Cross Q1:** "Patient P-77 had 3 FHIR Encounters this month — which ones have no matching OpenIMIS claim (unbilled care)?"
- **Cross Q2:** "Claim CL-9001 was rejected for 'unknown diagnosis' — what ICD code does the FHIR Condition actually carry, and who is right?"
- **Live `--discover` endpoint:** `GET /coverage-check?patient_id=&procedure_code=` on insurance side (returns `covered: bool, copay, policy_active`). Added live mid-demo; copilot re-discovers then pre-checks next week's appointments for denials.
- **Score:** Join 4 · Wow 5 · Discover 4 · Setup 3 = **16/20**. Highest realism; heaviest setup (HAPI JVM + OpenIMIS stack) → use slim FastAPI facades mirroring their schemas for the demo.

## Pair 3 — Orders + EDIFACT Reconciliation

- **System A (orders-modern):** REST/JSON purchase orders (real: `frappe/erpnext` docker —
  `frappe_docker` compose + `bench new-site --install-app erpnext`; MariaDB/Redis/workers).
- **System B (edi-legacy):** EDIFACT ORDERS/DESADV/INVOIC mailbox (real refs: `EdiFabric/EDIFACT.NET`
  examples `EdiFabric.Examples.EDIFACT.DESADV/ORDERS`; `Effektor/EDIFACT` EXAMPLES.md; `johnmonarch/EDIForge` starter packs `edifact-orders-basic.json`, `edifact-desadv-basic.json`).
- **Join key:** `PO_number ↔ UNH/BGM reference` (`BGM+220+PO-12345`); line-item join `SKU ↔ LIN/C212`.
- **Cross Q1:** "PO-12345 in ERPNext says 100 units ordered — what quantity does the supplier's DESADV say shipped, and what is the shortfall?"
- **Cross Q2:** "Which POs have an INVOIC in the EDI mailbox but no goods-receipt in orders (invoiced-before-delivery exceptions)?"
- **Live `--discover` endpoint:** `GET /reconciliation/{po_number}` on a reconciliation facade (joins both, returns `ordered vs shipped vs invoiced` variance object). Added live; copilot re-discovers and runs it across all open POs.
- **Score:** Join 5 · Wow 4 · Discover 5 · Setup 4 = **18/20**. Best "old meets new" story; EDI parsing (pydifact) is the visual hook.

## Pair 4 — HR + Ticketing with SLA Twist

- **System A (hr-directory):** employees, teams, shifts, on-call roster (mock FastAPI; real schema refs: ERPNext HR module).
- **System B (ticketing-sla):** tickets with SLA/OLA deadlines (real: `Zammad` — Rails+PG+ES, AGPL, multi-channel intake, 4–8GB RAM floor; `GLPI` — PHP+MariaDB, ITIL SLAs/OLAs + CMDB; `osTicket`/`FreeScout` lighter alternatives).
- **Join key:** `assignee_email ↔ employee_id`; twist join `ticket.created_at ↔ shift_calendar` (was assignee on-shift?).
- **Cross Q1:** "Ticket T-551 breached SLA — was the assignee even on shift, and who was the on-call backup who should have been paged?"
- **Cross Q2:** "Which team has the worst breach rate normalized by ticket volume, and does it correlate with understaffed night shifts?"
- **Live `--discover` endpoint:** `GET /oncall?at={iso_timestamp}` on HR side (returns current on-call person per team). Added live; copilot re-discovers then re-routes all currently-breaching tickets to whoever is on call *right now*.
- **Score:** Join 4 · Wow 5 · Discover 5 · Setup 5 = **19/20**. SLA-breach blame game always lands; trivially mockable with Zammad/GLPI concepts.

## Pair 5 — Telecom Alarms + Dispatch

- **System A (net-alarms):** network events/alarms (real: `OpenNMS Horizon` — `opennms/horizon` + `opennms/minion` docker images, `opennms-forge/docker-remote-poller` compose samples; alternative: lightweight SNMP-trap mock facade).
- **System B (field-dispatch):** technician tickets, truck rolls, skills/location (mock FastAPI; real-world pattern: GLPI assets + tickets as dispatch board).
- **Join key:** `site_id / node_label` (alarm node ↔ dispatch work-site); geo join `alarm.lat/lon ↔ tech coverage zone`.
- **Cross Q1:** "Alarm A-9001 (fiber cut, site LAGOS-12) — is there already a dispatch ticket for that site, which tech, and ETA?"
- **Cross Q2:** "Which critical alarms in the last hour have zero corresponding dispatch (unacknowledged network risk)?"
- **Live `--discover` endpoint:** `GET /nearest-tech?site_id=` on dispatch side (haversine over tech GPS + skill filter, returns ranked techs). Added live; copilot re-discovers and auto-proposes assignments for all unassigned critical alarms.
- **Score:** Join 5 · Wow 4 · Discover 4 · Setup 3 = **16/20**. Great map visual if you add one; OpenNMS full stack is heavy → facade recommended.

## Pair 6 (Bonus) — Permits + Inspection Scheduler

- **System A (permit-office):** building/event permit applications.
- **System B (inspection-cal):** inspector calendars, zones, checklists.
- **Join key:** `permit_id`; geo join `permit.address ↔ inspector.zone`.
- **Cross Q1:** "Permit P-300 is 'approved pending inspection' — is an inspection actually scheduled, when, and by whom?"
- **Cross Q2:** "Which approved permits have no inspection within 14 days (backlog risk by zone)?"
- **Live `--discover` endpoint:** `GET /inspector-availability?zone=&date=` (returns free slots). Added live; copilot re-discovers and books the earliest slot for every backlogged permit.
- **Score:** Join 4 · Wow 3 · Discover 4 · Setup 5 = **16/20**. Easiest backup pair; government-adjacent variant of Pair 1.

---

## Ranking & recommendation

1. **Pair 1 (19) + Pair 4 (19)** — pick one as the flagship; both mock in minutes, join keys obvious, discover moments crisp.
2. **Pair 3 (18)** — best enterprise-legacy flavor; keep as second demo.
3. **Pairs 2/5/6 (16)** — strong but heavier (2, 5) or lower wow (6); use as stretch goals.
4. Suggested Track 3 script shape: Q1 (simple lookup join) → Q2 (exception/anti-join) → live endpoint add → `--discover` → Q3 answered *only* by the new endpoint.
