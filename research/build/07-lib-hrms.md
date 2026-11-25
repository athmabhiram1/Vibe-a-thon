# 07 — Premade HR Backends: Reuse vs Mock (Frappe HRMS · ERPNext HR · Odoo Employees)

**Date:** 2026-11-22 · **Question:** can we `docker compose up` a real HRMS for the hackathon, or should we mock FastAPI facades that mirror their schemas?

**TL;DR recommendation: MOCK — build thin Python/FastAPI facades (`hrms_facade/`) that mirror Frappe HRMS doctypes + Odoo `hr.employee` fields, seeded with 12–20 fake employees. Do NOT run Frappe/ERPNext/Odoo Docker during the live build/demo. Keep one optional `compose.realdeps.yml` (disabled by default) for a post-hackathon swap-in.**

---

## 1. Candidates at a glance

| | Frappe HRMS (v15/v16) | ERPNext HR module | Odoo Employees (17/18/19/20) |
|---|---|---|---|
| What it is | Standalone HRMS app on Frappe Framework (split from ERPNext at v14). Full HR: Employee, Leave, Attendance, Shift/Roster, Payroll, Expense, Appraisal, Onboarding | Same HR code as Frappe HRMS, bundled as module inside full ERPNext (Accounts, Stock, Selling, Manufacturing + HR) | `hr` / `hr.employee` (+ `hr_holidays`/`hr_attendance`/`hr_expense` addons). Since v18 employee contract fields split into `hr.version` (accessed via `_inherits` on `hr.employee`) |
| Language | Python (Frappe Framework) + JS | Python (same Frappe stack + ERPNext app) | Python (Odoo ORM) + JS (OWL) |
| License | AGPL-3.0 | AGPL-3.0 | LGPL-3.0 (Community) / Enterprise (paid) for full HR extras |
| API style | REST: `/api/resource/Employee`, `/api/resource/Leave Application`, whitelisted methods e.g. `hrms.api.roster.get_events`; token/api-key auth | Identical to Frappe HRMS (same `/api/resource/...` surface, plus ERP endpoints) | XML-RPC (`/xmlrpc/2/object` + `execute_kw`) and JSON-RPC/JSON-2 (`POST /json/2/<model>/<method>`, bearer API key). `search_read`/`create`/`write` on `hr.employee` |
| Best fit if… | You want the richest OSS HR schema without full ERP | You need HR + accounting/inventory in one DB | You want the lightest container and simplest external API |

---

## 2. Compose weight (what `docker compose up` actually starts)

### 2.1 Frappe HRMS / ERPNext — heavy (7–11 services)

Base `frappe_docker` compose + app image:

```
configurator (init, exits) · backend (Werkzeug) · frontend (nginx) · websocket (socketio.js)
queue-short · queue-long (RQ workers) · scheduler · redis-cache · redis-queue (+ redis-socketio in older files)
db (mariadb:10.8 — requires special command params for Frappe) OR postgres variant
+ site bootstrap (bench new-site + bench get-app hrms / erpnext + install-app)
```

- Dev quickstart is deceptively simple (`git clone hrms; cd hrms/docker; docker-compose up` → `http://localhost:8000`, `Administrator/admin`), but first boot builds site, installs apps, runs patches — 10–30 min on a laptop, multi-GB images (`frappe/erpnext:v16.x` ≈ 2 GB+ compressed).
- Production single-server example requires **2 vCPU / 4 GB RAM / 50 GB SSD minimum**, Docker Engine v23+, and public DNS + ports 80/443 for TLS. Dev docs explicitly say *"allocate at least 4 GB RAM to Docker."*
- ERPNext adds weight over plain HRMS (bigger image, more doctypes/patches, longer `bench migrate`). Never run both stacks — HRMS alone already implies Frappe + MariaDB + 3× Redis.

### 2.2 Odoo Employees — light (2 services)

```yaml
services:
  web:  image: odoo:18  (depends_on db, ports 8069)
  db:   image: postgres:16  (PG16 required for Odoo 20; PG13+ for v19)
volumes: odoo-data, pg-data
```

- Official guidance: **minimum 2 GB RAM / 2 vCPU; production 4 GB / 4 vCPU**. Single `odoo:18` image (~1 GB), boots in ~1–2 min, module install via `-i hr,hr_holidays,hr_attendance` or UI Apps page.
- Compose weight winner by far. Only Postgres + Odoo. No Redis/worker/scheduler/socketio fleet.

| Metric | Frappe HRMS | ERPNext (+HR) | Odoo Employees |
|---|---|---|---|
| Containers | 9–11 | 9–11 (larger image) | **2** |
| Image pull | ~3–5 GB total | ~4–6 GB total | ~1.2 GB total |
| Idle RAM | ~2.5–4 GB (needs 4 GB Docker allocation) | ~3–4.5 GB | ~0.8–1.5 GB (fine on 2 GB) |
| Cold start to login | 10–30 min first build; 2–5 min warm | 15–40 min first build | 1–3 min |
| Disk (volumes) | db-data + sites + logs + redis-* | same, larger sites vol | pg-data + odoo-data only |

---

## 3. Schema coverage (what you'd mirror in the mock)

### Frappe HRMS doctypes (mirror these Pydantic models)
- `Employee` (id/name, company, dept, designation, holiday_list, leave_approver)
- `Leave Type` / `Leave Allocation` / `Leave Application` (status Draft→Applied→Approved; `validate()` enforces balance, overlap, max-days, block-dates, no-self-approval, salary-processed-days)
- `Attendance` + `Shift Type` / `Shift Assignment`; roster API `get_events(month_start, month_end, employee_filters, shift_filters)` merges holidays+leaves+shifts per employee
- `Salary Structure` / `Salary Slip` / `Payroll Entry`; `Expense Claim`; `Appraisal`; `Holiday List`
- REST shape: `GET /api/resource/Employee?fields=["name","employee_name","department"]` → `{data:[...]}`. Writes need `Authorization: token key:secret`.

### Odoo models (same mock covers both)
- `hr.employee` (name, work_email, department_id, job_id, work_location, manager/parent_id, timezone) + via `hr.version`: contract-type fields, attendance-based flags (`_get_whitelist_fields_from_template`)
- `hr.leave` (domain `[["state","=","validate"]]`), `hr.attendance`, `hr.expense`, `hr.contract`/`hr.version`
- RPC shape: `execute_kw(db, uid, pw, 'hr.employee', 'search_read', [[[...]]], {'fields': [...], 'limit': 20})` or `POST /json/2/hr.employee/search_read {"domain":[],"fields":["name","department_id"]}` with `Authorization: bearer <apikey>`.

Mock needs only 4 resources to satisfy both: **Employee, Leave, Attendance, Expense/Payroll stub**. Field names: use Frappe-style snake_case (`employee_name`, `from_date`, `to_date`, `leave_type`, `status`) and add `odoo_id` / `external_ref` passthrough so a later adapter can map `hr.employee.name ↔ Employee.employee_name` without renaming.

---

## 4. Seed effort

| | Frappe HRMS | ERPNext HR | Odoo Employees | Mock FastAPI facade |
|---|---|---|---|---|
| Prereq chain | Company → Holiday List → Leave Policy/Period → Leave Allocation → Employee → Salary Structure | Same + Chart of Accounts + Stock/UOM setup tax | Create DB → install `hr*` addons → Departments → Jobs → Employees (CSV import possible) | `seed.py` inserts 15 rows into SQLite |
| Time (experienced) | 1–3 hrs clicking + patch fixes | 2–4 hrs | 30–60 min | **10 min** |
| Failure modes | MariaDB collation/params, Redis version, bench patch breaks, version-14 vs v15 branch mismatch (use `--branch version-14/15` consistently) | Same + ERPNext↔HRMS version pin drift | Addon version mismatch (18.0 vs master), `fields_get` noise, access-rights (`AccessError` on `res.partner`-style relations) | None — deterministic |
| Demo risk | Site won't finish building on event Wi-Fi; `Administrator/admin` reset; background workers silent | Same, worse | Lowest real-backend risk, but still needs Postgres volume + admin password | **Zero infra risk; runs on `uvicorn :8001`** |

---

## 5. Synapse Python-only constraint (decisive)

From `research/03-synapse-technical.md`:

1. **Generated files are Python (FastMCP) only.** Hosted Auto produces no file (account-side config + `npx synapse-mcp` runner that HTTP-forwards to your live API). `--local` Auto writes `synapse_auto_server.py` **for Python projects only**; TS/Java/Go/Rust repos get names but no file.
2. **Detection is static decorator/regex scanning** (`needles.ts`, `python.ts::decoratorToRoute`): `@app.get`, `@router.*`, Flask `add_url_rule`, Django `path()/re_path()`, aiohttp adds. **Frappe `@frappe.whitelist()` methods and Odoo `models.Model` methods are NOT in the needle set** — a raw Frappe/Odoo repo will likely yield zero or garbage endpoints under `--local`.
3. **Auto tools are dumb HTTP forwards** to `ENDPOINT_BASE_URL`. They only work if the API is *deployed/reachable at demo time* with env secrets filled. A Frappe/Odoo container that isn't up = dead demo.
4. Offline/`--local` Custom mode needs importable Python functions (`from <module> import <qualname>`, AST-audited, no inline helpers). Frappe/Odoo business logic is framework-coupled (needs `frappe.db`, `self.env`) and won't import cleanly into a generated `<tool>_server.py`.

**Consequence:** even though Frappe and Odoo are "Python," they are *opaque* to Synapse's extractor. A small hand-written **FastAPI facade is the only option Synapse reliably detects** (`@app.get("/employees")`, `@router.post("/leaves")`) and therefore the only option that yields a one-shot `synapse build --local` file + hosted runner config during the hackathon.

---

## 6. Recommendation: mock now, adapt later

**Do this:**
1. Create `services/hrms-facade/` — FastAPI (`@app.get/post` only, so Synapse needles hit), Pydantic models mirroring §3, SQLite/in-memory store, `seed.py` (15 employees, 30 leaves, 40 attendance rows), `Dockerfile` (~50 MB) + `compose.yml` entry (1 service, 128 MB RAM).
2. Endpoints (keep ≤8 so Synapse Auto stays clean): `GET /employees`, `GET /employees/{id}`, `POST /leaves` (validates overlap/balance like Frappe `validate()`), `GET /leaves?employee=`, `POST /attendance/check-in|check-out`, `GET /roster?month=`, `POST /expenses`.
3. Add `adapters/frappe.py` + `adapters/odoo.py` stubs (unimplemented `FrappeHRMSAdapter` / `OdooHRAdapter` with identical method names) to tell judges "swap реал backend post-hackathon without changing MCP tools."
4. Keep `compose.realdeps.yml` (Frappe HRMS *or* Odoo, never both; default profile `never`) documents the real path but is **not started** in the demo.
5. `synapse build --auto --all-endpoints --discover` targets **only** the facade URL (`ENDPOINT_BASE_URL=http://localhost:8001`).

**Run real Docker only if:** (a) a judging criterion explicitly rewards "real HRMS integration," AND (b) you have a pre-built, pre-seeded image + a machine with ≥8 GB free RAM + wired internet. If so, pick **Odoo** (2 containers, fastest seed). Never attempt a first-time Frappe/ERPNext build on event Wi-Fi.

---

## 7. Sources
- Context7 `/frappe/hrms` (README docker setup, `hrms/api/roster.py get_events`, `leave_application.py validate()`), `/frappe/frappe_docker` (single-server 2vCPU/4GB/50GB req, 4 GB Docker allocation, core services list), `/odoo/documentation` + `/websites/odoo*` (2 GB min / 4 GB recommended, PG13/16 reqs, XML-RPC + `/json/2/<model>/<method>` bearer API, `hr.version` split).
- Web: `hub.docker.com/r/arnadeem/erpnext-hrms`, `discuss.frappe.io/t/container-basics/99306`, `forums.unraid.net` (4 GB/10 GB ERPNext), `oec.sh/odoo-17-docker`, `cicdoo.com/guides/odoo-docker-compose-production`, Odoo 18 External API docs (`/xmlrpc/2/*`, `/json/2/*`).
- Internal: `research/03-synapse-technical.md` §§2–3 (Python-only files, needle list, HTTP-forward + `ENDPOINT_BASE_URL` requirement).
