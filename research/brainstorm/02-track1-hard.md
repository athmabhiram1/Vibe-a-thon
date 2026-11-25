# Track 1 HARD Brainstorm — Differentiated Python Builds (Synapse Auto Constraints)

**Constraints:** Python codebase only. Deployed API required (FastAPI/Flask/Frappe served over HTTP, Docker-compose). No `.js/.jsx` custom frontend — server-rendered templates / Jinja / HTMX or pure REST + OpenAPI docs only. User has lots of time, wants differentiated / defensible.

**Sources researched:** OpenG2P FastAPI-common architecture, DIGIT Urban Stack + Workflow v2, ERPNext/Frappe Docker, pyx12 / pydifact / x12-python / EdiFabric / Bots-EDI, FastAPI BackgroundTasks + `fastapi run` production deploy via Context7.

## Score Table (1-5, 5=best)

| Domain | Novelty | Demo power | Synapse-fit (Python+API, no JS) | Portfolio value | Total /20 |
|---|---|---|---|---|---|
| **A. Municipal File Workflow (e-File + DIGIT Workflow-v2 clone)** | 5 | 5 | 5 | 5 | **20** |
| **B. On-Prem ERP Core (Frappe/ERPNext-pattern, FastAPI re-impl)** | 4 | 4 | 4 | 5 | **17** |
| **C. EDI Supply-Chain Gateway (X12 850/856/810 + 997)** | 5 | 4 | 5 | 4 | **18** |

Winner for differentiation: **A > C > B**. B is most credible for jobs but least novel (everyone clones ERP). A+C combo is killer: municipal procurement that speaks EDI.

---

## A. Municipal File Workflow — e-File / DIGIT Workflow-v2 in FastAPI

**What:** Multi-tenant, role-based file-noting system: citizen application → clerk verification → field inspection → approver sanction → payment/issue. Mirrors DIGIT `egov-workflow-v2` BusinessService + ProcessInstance model, but re-implemented in Python (DIGIT itself is Java/Spring — porting to Python *is* the differentiation).

**Public sample codebases (reference, do not fork Java directly):**
- DIGIT Core (workflow, MDMS, inbox): https://github.com/egovernments/DIGIT-Core
- DIGIT Urban archived monorepo (property-tax, trade-license, OBPS patterns): https://github.com/egovernments/URBAN
- UPYOG (successor stack, workflow+grievance+property): https://github.com/upyog/UPYOG
- DIGIT Workflow API spec (`/egov-wf/process/_transition`, `/businessservice/_search`): https://docs.digit.org/platform/platform/api-specifications/workflow
- Python pattern to copy: OpenG2P `openg2p-fastapi-common` (Initializer, BaseController/BaseService, JWS auth): https://docs.openg2p.org/platform/architecture/openg2p-fastapi-common
- Python FastAPI reference for demo polish: https://github.com/lailarallc/edi-preflight (FastAPI+Jinja+HTMX, no JS build, Fly.io deploy — allowed pattern)

**Seed data plan (all checked in as CSV/JSON + `seed.py`):**
- `tenants.json`: 3 ULBs — `pb.amritsar`, `pb.jalandhar`, `demo.simcity` (tenantId-prefixed IDs like DIGIT).
- `business_services.json`: 2 workflows — `PT.ASSESSMENT` (CREATE→VERIFY→FIELD_INSPECT→APPROVE→PAY, with SENDBACKTOCITIZEN loop) and `TL.NEW` (trade-license equivalent). Copy DIGIT BusinessService shape: states {isStart, isTerminate}, actions {role, nextState}, SLA mins.
- `users.csv`: 12 users — CITIZEN x3, TL_CEMP clerk x2, FIELD_INSPECTOR x2, APPROVER x2, ADMIN, AUDITOR (uuid, role, tenant).
- `applications_seed.json`: 40 property/trade files across all states (some SLA-breached → red inbox), each with documents list, comments, assignee history.
- `mdms_sla.json`: SLA buckets (green >1/3 remaining, yellow, red overdue) per DIGIT inbox spec.

**3 agent tasks (each must end in state-change + append-only audit row):**
1. `clerk-triage-agent`: polls `GET /inbox?role=TL_CEMP&tenant=pb.amritsar`, picks CITIZENACTIONREQUIRED or PENDING_VERIFY files, validates mandatory docs (self-attested deed, photo), then `POST /process/_transition {businessId, action: FORWARD|SENDBACKTOCITIZEN}` → writes `audit_log {file_id, actor, from_state, to_state, action, hash_chain}`. State-change + audit required to pass.
2. `inspector-agent`: claims FIELD_INSPECT queue, uploads inspection note (lat/long + outcome PASS/FAIL), transitions to APPROVE or REJECT. Must handle concurrent claim (optimistic locking via `version` column, 409 on conflict) + audit.
3. `sla-escalation-agent` (BackgroundTasks / cron): scans overdue `processInstances`, auto-escalates assignee to supervisor, emits `POST /notifications` (logged, not emailed), writes audit `ESCALATE`. Demonstrates FastAPI `BackgroundTasks` (Context7 pattern) + `fastapi run` production deploy.

**Quota impact (10 servers / 100k lines):**
- Servers: 1 (single FastAPI + Postgres + Redis compose; `fastapi run` or uvicorn). Optionally 2nd for demo deploy.
- Lines: ~4,500–6,500 Python (models, workflow engine, inbox, seed, audit hash-chain). Well under quota; leaves room for A+C combo.

---

## B. On-Prem ERP Core — ERPNext-pattern, FastAPI Re-implementation

**What:** Air-gapped-friendly ERP slice: Chart of Accounts + Item/Vendor + Purchase Order → Goods Receipt → Purchase Invoice → Payment, with role approvals and immutable ledger. Do NOT fork ERPNext directly (GPLv3 + heavy JS frontend violates no-JS rule); instead re-implement the *pattern* in FastAPI + Postgres, citing ERPNext as spec.

**Public sample codebases:**
- ERPNext (spec reference, Python/Frappe): https://github.com/frappe/erpnext (41k★, GPL-3.0)
- Frappe Docker (official compose: backend/frontend/websocket/queues/scheduler + MariaDB/Redis, 11 containers): https://github.com/frappe/frappe_docker
- Frappe Docker setup examples (noproxy / external DB / HTTPS): `frappe_docker/docs/02-setup/06-setup-examples.md`
- Alternative if Frappe allowed: `bench` + `apps.json` custom-app build; but recommended Synapse path is FastAPI clone to avoid Node/JS asset build.

**Seed data plan:**
- `coa.csv`: ~60-account chart (assets/liabilities/income/expense, GST-ready).
- `items.csv`: 80 SKUs across 5 categories with UOM, HSN, reorder level.
- `vendors.csv`: 12 vendors (GSTIN, payment terms, lead time).
- `opening_stock.json` + `purchase_orders_seed.json`: 25 POs in DRAFT/SUBMITTED/APPROVED/RECEIVED/INVOICED states, 3 with price variance >5% (approval-gate test), 2 overdue.
- `fx_and_tax.json`: GST slabs 5/12/18/28, TDS flags.

**3 agent tasks (state-change + audit):**
1. `po-creator-agent`: from low-stock report (`qty < reorder`), drafts `POST /purchase-orders` (DRAFT), attaches vendor quote, transitions to SUBMITTED → writes `stock_ledger + audit_log` (double-entry preview, no posting yet).
2. `approver-agent`: inbox `GET /approvals?role=PURCHASE_MANAGER`, enforces tolerance (reject if variance >5% or budget exceeded → SENDBACK), else APPROVE → posts encumbrance to GL (state-change in `gl_entries`), audit with idempotency key.
3. `receiver-biller-agent`: on ASN/GRN (`POST /goods-receipts`), matches PO qty ± tolerance, transitions PO→RECEIVED, auto-creates `POST /purchase-invoices` from GRN, posts AP + inventory GL, writes audit. Mismatch → HOLD + discrepancy audit.

**Quota impact:**
- Servers: 1–2 (FastAPI + Postgres + Redis; avoid full 11-container Frappe stack to save quota). If true Frappe: 1 server but ~4GB RAM + 5GB image — heavy.
- Lines: ~6,000–9,000 Python (ledger, inventory, approval engine). Fits; but boring unless paired with EDI ingest (see C).

---

## C. EDI Supply-Chain Gateway — X12 850/856/810 ↔ JSON + 997

**What:** Supplier-facing EDI translator: ingest raw X12 over SFTP/API upload → validate → convert to JSON order → drive ERP states → generate 997/999 ack + outbound 855/856. Pure Python, no JS. Highest technical moat; almost no bootcamp builds do EDI.

**Public sample codebases:**
- pyx12 (mature validator, X12N maps, `X12ContextReader.iter_segments('2300')`, 997/999 gen): https://github.com/azoner/pyx12 + docs https://pyx12.readthedocs.io/en/stable/ + examples https://pyx12.readthedocs.io/en/stable/examples.html (`st_iterator.py`, `834_x12_json.py`, `node_iterator.py`)
- pydifact (UN/EDIFACT ORDERS/INVOIC/DESADV): https://github.com/nerdocs/pydifact
- x12-python (supply-chain 850/855/856/860/810 schemas): https://github.com/copyleftdev/x12-python
- EdiFabric Python bindings (`pip install edifabric-x12`, 850/856/810→JSON, demo key `bd96a836feca45cb91c86ee65d281f52`): https://github.com/EdiFabric/edifabric-python-bindings
- Bots-EDI (full translator reference — Django+Python, grammars+mappings+routing): https://bots-edi.org/ (frozen 3.2 + NG 4.0 Python3.10/Django5)
- FastAPI demo pattern (stateless parse+validate+PDF export, HTMX): https://github.com/lailarallc/edi-preflight

**Seed data plan (all as `.x12` + `.json` golden files):**
- `samples/850/`: 15 POs — 5 retailers (Walmart, Amazon, UNFI, KeHE, Costco flavours: different N1 loops, date qualifiers, UOMs), 2 with deliberate errors (bad SSCC, missing BEG).
- `samples/856/`: 10 ASNs with HL hierarchy (shipment→order→pack→item), 2 with broken HL counts.
- `samples/810/`: 10 invoices matching 850s (3 with qty/price mismatch → dispute).
- `partners.json`: ISA IDs, GS qualifiers, delimiters, per-partner required vs optional segments (retailer implementation guides).
- `golden/`: expected JSON + expected 997 ack per sample (locks parser behaviour, 300+ test pattern like edi-preflight).

**3 agent tasks (state-change + audit):**
1. `inbound-850-agent`: `POST /edi/inbound` (raw X12 upload) → tokenize → `X12ContextReader` validate against map → extract BEG/N1/PO1 → create `purchase_order` (DRAFT→SUBMITTED) + `POST /edi/ack/997` → store raw + parsed + ack + audit `EDI_RECEIVED`. Invalid → QUARANTINE + error audit, no state leak.
2. `asn-matcher-agent`: ingest 856 → rebuild HL tree → 3-way match (PO vs ASN vs GRN) → on full match transition order→RECEIVED + post inventory; on short/over-ship → PARTIAL + discrepancy audit with chargeback-$ attribution (retailer rule table).
3. `invoice-reconciler-agent`: ingest 810 → match to PO/ASN (price/qty tolerance) → auto-approve→PAYABLE or dispute→HOLD + generate outbound 855 (PO ack) / 997; every decision writes `edi_audit {isa13, gs06, st_control, verdict, actor=agent}`. Nightly `BackgroundTasks` replays quarantined files after partner-map update.

**Quota impact:**
- Servers: 1 (FastAPI + Postgres; SFTP poller as BackgroundTasks/cron, no AS2 server needed for demo). 
- Lines: ~5,000–7,500 Python (tokenizer thin-wrap over pyx12/pydifact + matcher + ack gen + retailer rules). Under quota; combines well with A or B.

---

## Recommendation

Build **A first** (municipal workflow = strongest demo story: citizen→clerk→inspector→approver with SLA inbox + hash-chained audit; non-obvious, civic-impact, easy to narrate). Add **C as stretch** (EDI inbound that auto-creates municipal procurement POs — nobody else has this). Use **B only as ledger backend** if time remains; don't lead with generic ERP.

**Suggested repo layout (all Python, deployed API):**
```
/app (FastAPI: workflow/, erp/, edi/, audit/, auth/)
/seed (tenants, business_services, users, x12 samples, coa/items/vendors)
/tests (golden-file locks for workflow transitions + EDI 850/856/810)
/compose.yaml (api + postgres + redis, `fastapi run` prod)
```
