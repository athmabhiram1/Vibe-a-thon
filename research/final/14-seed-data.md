# 14 — Seed Data Design for HR + IT Demo

> Goal: one-click demo dataset that exercises every risky path (offer-signed, BG pending/pass, visa risk, weekend start, equipment holds, SLA breach, on-shift mapping) and resets in <5s. Deterministic IDs, no PII, safe to show on projector.

---

## 1. File Layouts

### 1a. Repo layout (proposed)

```
seed/
  schema.sql                  # DDL for demo (postgres/sqlite-compatible)
  candidates.csv              # 20 rows
  employees.csv               # 20 rows (12 linked to candidates, 8 pre-existing)
  equipment.csv               # 20 rows (laptops, badges, monitors)
  tickets.csv                 # 20 rows (IT helpdesk)
  shifts.csv                  # 8 rows (on-shift roster for ticket mapping)
  subscriptions.csv           # 6 rows (SaaS seats — for auto-renew trap)
  api_keys.csv                # 5 rows (for rotation edge case)
  attachments/
    offer_Aarav_Mehta_signed.pdf      # stub PDF (1 page, fake signature)
    bg_report_Priya_Nair_PASS.pdf     # stub
    visa_Chen_Wei_H1B_receipt.pdf     # stub
  README.md                   # how to load manually: `psql < schema.sql` + `\copy`
  validate.py                 # row-count + FK + invariant checks (run in CI + /demo/seed)
```

### 1b. Runtime layout (server)

```
server/
  src/demo/
    seed.controller.ts        # POST /demo/seed, POST /demo/reset
    seed.service.ts           # truncate+insert in dependency order, timed
    seed.data.ts              # in-code JSON mirror of CSVs (single source for <5s path)
    reset.sql                 # TRUNCATE ... CASCADE (one statement)
```

> Rule: CSVs are the **human-editable source of truth**. `seed.data.ts` is generated from CSVs at build time (`npm run seed:codegen`) so `/demo/seed` never parses CSV at request time — that's how reset stays <5s.

---

## 2. CSV / JSON Schemas

### 2.1 `candidates.csv` — 20 rows

```csv
candidate_id,full_name,email,role,dept,offer_status,offer_signed_at,bg_status,bg_completed_at,visa_status,visa_expiry,start_date,source,notes
```

| Column | Type | Values / constraints |
|---|---|---|
| `candidate_id` | `TEXT PK` e.g. `CAND-001` | deterministic, zero-padded |
| `full_name` | TEXT | fictional Indian + intl mix, no real PII |
| `email` | TEXT UNIQUE | `firstname.lastnameNN@example.com` |
| `role` | TEXT | SDE-1, SDE-2, Designer, PM, IT-Support, HR-Exec |
| `dept` | TEXT | Engineering, Design, Product, IT, HR |
| `offer_status` | ENUM | `signed` (14) \| `pending` (3) \| `declined` (2) \| `expired` (1) |
| `offer_signed_at` | DATE nullable | required if `signed` |
| `bg_status` | ENUM | `pass` (8) \| `pending` (7) \| `fail` (1) \| `waived_intern` (1) \| `not_started` (3) |
| `bg_completed_at` | DATE nullable | required if `pass`/`fail` |
| `visa_status` | ENUM | `citizen` (13) \| `h1b_valid` (2) \| `h1b_expiring_30d` (2) \| `opt_expiring_15d` (1) \| `requires_sponsorship` (2) |
| `visa_expiry` | DATE nullable | required unless `citizen` |
| `start_date` | DATE | spread incl. **4 weekend starts (Sat/Sun)** |
| `source` | TEXT | referral, campus, portal |
| `notes` | TEXT | demo cue, e.g. `BLOCKED-BG`, `VISA-RISK`, `WEEKEND-START` |

JSON equivalent:

```json
{
  "candidate_id": "CAND-003",
  "full_name": "Chen Wei",
  "email": "chen.wei03@example.com",
  "role": "SDE-2", "dept": "Engineering",
  "offer_status": "signed", "offer_signed_at": "2026-11-10",
  "bg_status": "pass", "bg_completed_at": "2026-11-15",
  "visa_status": "h1b_expiring_30d", "visa_expiry": "2026-12-20",
  "start_date": "2026-11-30",
  "source": "referral", "notes": "VISA-RISK: H-1B expires in 27d"
}
```

**Validation invariants (enforced in `validate.py` + DB CHECK):**
- `offer_status='signed' → offer_signed_at NOT NULL`
- `bg_status IN ('pass','fail') → bg_completed_at NOT NULL`
- `visa_status != 'citizen' → visa_expiry NOT NULL`
- `start_date >= offer_signed_at` (if signed)

### 2.2 `employees.csv` — 20 rows

```csv
employee_id,candidate_id,full_name,work_email,dept,role,employment_type,status,join_date,manager_id,rehire_of
```

| Column | Type | Notes |
|---|---|---|
| `employee_id` | `TEXT PK` `EMP-001…EMP-020` | |
| `candidate_id` | `TEXT FK nullable` | 12 linked (hired), 8 `NULL` (pre-existing staff: 2 managers, 2 IT agents, 1 HR, 3 tenured) |
| `work_email` | TEXT UNIQUE | `firstname.lastname@demo.example.com` |
| `employment_type` | ENUM | `full_time` (16) \| `intern` (2) \| `contractor` (2) |
| `status` | ENUM | `active` (18) \| `on_notice` (1) \| `terminated` (1 — for rehire test) |
| `join_date` | DATE | |
| `manager_id` | FK → employees | every row except CEO-stub `EMP-001` has one |
| `rehire_of` | FK nullable → employees | `NULL` except rehire edge row (see §5.1) |

### 2.3 `equipment.csv` — 20 rows (inventory with serials + holds)

```csv
asset_tag,serial,category,model,status,assigned_to,hold_for_candidate,location,po_number,warranty_expiry
```

| Column | Type | Values |
|---|---|---|
| `asset_tag` | PK `LT-1001…`, `MN-2001…`, `BDG-3001…` | |
| `serial` | TEXT UNIQUE | realistic: `SN-MBP14-X7K2-…`; **2 intentional near-duplicates** differ by 1 char to test serial-collision guard |
| `category` | ENUM | `laptop` (12) \| `monitor` (4) \| `badge` (4) |
| `model` | TEXT | MacBook Pro 14, ThinkPad T14, Dell U2723QE |
| `status` | ENUM | `available` (6) \| `assigned` (8) \| `on_hold` (4) \| `repair` (1) \| `retired` (1) |
| `assigned_to` | FK nullable | set iff `assigned` |
| `hold_for_candidate` | FK nullable → candidates | set iff `on_hold`; **one double-hold conflict** (same laptop held for 2 candidates — tests hold race) |
| `location` | TEXT | `BLR-Desk-…`, `HYD-Store` |
| `po_number` | TEXT | `PO-2026-…` |
| `warranty_expiry` | DATE | 1 expired (trap: assign retired/expired asset) |

### 2.4 `tickets.csv` — 20 rows (SLA breached + on-shift mapping)

```csv
ticket_id,title,requester_id,assignee_id,priority,category,status,created_at,due_at,resolved_at,shift_id,channel
```

| Column | Type | Values |
|---|---|---|
| `ticket_id` | PK `T-5001…T-5020` | |
| `priority` | ENUM | `P1` (3) \| `P2` (6) \| `P3` (7) \| `P4` (4) |
| `category` | ENUM | `laptop_setup` (6) \| `access` (5) \| `vpn` (3) \| `payroll` (2) \| `badge` (2) \| `other` (2) |
| `status` | ENUM | `open` (7) \| `in_progress` (5) \| `resolved` (6) \| `breached` (2 — computed, stored for demo determinism) |
| `created_at` / `due_at` | TIMESTAMPTZ | SLA: P1=4h, P2=8h, P3=24h, P4=48h; **3 rows have `now > due_at AND status != resolved` = breached** |
| `resolved_at` | nullable | |
| `shift_id` | FK → shifts | every ticket maps to exactly one shift (tests on-shift routing) |
| `channel` | ENUM | `portal` \| `email` \| `slack` |

**SLA rule (seed + live share one function `slaDue(createdAt, priority)`):** seed pre-computes `due_at`; UI badge reads same function so demo never flakes.

### 2.5 `shifts.csv` — 8 rows

```csv
shift_id,name,start_time,end_time,timezone,member_ids
```

```csv
SH-01,BLR-Morning,09:00,17:00,Asia/Kolkata,"EMP-014;EMP-015"
SH-02,BLR-Evening,14:00,22:00,Asia/Kolkata,"EMP-014;EMP-016"
SH-03,Night-OnCall,22:00,06:00,Asia/Kolkata,"EMP-016"
...
```

Ticket→shift mapping is by `created_at` falling in shift window (pre-computed in seed; verified by `validate.py`).

### 2.6 `subscriptions.csv` — 6 rows (auto-renew trap)

```csv
sub_id,tool,seats,seat_cost_inr,renewal_date,auto_renew,cancelled_at,owner_id
```

- `SUB-01 Figma 25 seats ₹1,499/seat auto_renew=true renewal 2026-11-25` (trap: cancelling 1 seat doesn't stop renewal)
- `SUB-02 Slack … auto_renew=true`, `SUB-03 … auto_renew=false` (control), etc.

### 2.7 `api_keys.csv` — 5 rows (rotation edge)

```csv
key_id,label,prefix,created_at,last_rotated_at,expires_at,scope,is_prod
```

- `KEY-01 prod-deploy-key last_rotated 2026-02-01 (295d ago, EXPIRED-trap)`; `KEY-02 prod-read … rotated 7d ago (healthy control)`.

---

## 3. 20-Row Sample Plan (each row earns its place)

### Candidates (CAND-001…020)

| ID | Name (fictional) | Offer | BG | Visa | Start | Demo purpose |
|---|---|---|---|---|---|---|
| CAND-001 | Aarav Mehta | signed | **pending** | citizen | Mon 2026-11-30 | ⛔ Day-1 flow BLOCKED — BG pending gate |
| CAND-002 | Priya Nair | signed | **pass** | citizen | Mon 2026-11-30 | ✅ Happy path — convert to employee live |
| CAND-003 | Chen Wei | signed | pass | **h1b_expiring_30d** | Mon 2026-11-30 | ⚠️ VISA-RISK banner (expires 2026-12-20) |
| CAND-004 | Sara Thomas | signed | pending | citizen | **Sat 2026-12-05** | 📅 WEEKEND-START warning (IT shift?) |
| CAND-005 | Rohan Gupta | signed | pass | citizen | **Sun 2026-12-06** | 📅 Weekend + laptop on_hold → assign |
| CAND-006 | Ananya Iyer | signed | **pending** | **requires_sponsorship** | Mon 2026-12-07 | Double-risk: BG + visa |
| CAND-007 | Vikram Rao | signed | pass | citizen | Mon 2026-12-07 | Control: clean hire #2 |
| CAND-008 | Fatima Khan | signed | pass | **opt_expiring_15d** | Tue 2026-12-08 | VISA-RISK critical (15d) |
| CAND-009 | James D'Souza | signed | **fail** | citizen | Mon 2026-12-07 | ⛔ BG-fail blocks conversion, HR override logged |
| CAND-010 | Kavya Reddy | **pending** | not_started | citizen | Mon 2026-12-14 | Offer not signed — convert button disabled |
| CAND-011 | Arjun Singh | signed | pass | citizen | **Sat 2026-12-12** | Weekend start + badge hold |
| CAND-012 | Meera Pillai | signed | **pending** | citizen | Mon 2026-12-14 | BG pending, equipment already on hold (hold-waste demo) |
| CAND-013 | Daniel Kim | signed | pass | **h1b_valid** | Mon 2026-12-14 | Visa OK control |
| CAND-014 | Ishita Bose | **declined** | not_started | citizen | — | Declined — excluded from Day-1 list |
| CAND-015 | Rahul Verma | signed | **waived_intern** | citizen | Mon 2026-12-07 | Intern fast-track (BG waived) |
| CAND-016 | Sofia Almeida | signed | pass | **requires_sponsorship** | Mon 2026-12-14 | Sponsorship letter task auto-created |
| CAND-017 | Karan Malhotra | **expired** | not_started | citizen | — | Expired offer — resend flow |
| CAND-018 | Divya Menon | **pending** | not_started | citizen | Mon 2026-12-21 | Pending-nudge email demo |
| CAND-019 | Omar Farouk | **declined** | not_started | citizen | — | Attrition stat (offer-accept rate) |
| CAND-020 | Neha Sharma | signed | pass | citizen | **Sun 2026-12-13** | 4th weekend start; SLA-breach ticket linked (T-5007) |

Counts: signed 14 / pending 3 (010, 018 + 1) — adjust 010/018/…; pass 8, pending 7 incl. 001/004/006/012, fail 1, waived 1, not_started 3. Weekend starts: 004, 005, 011, 020 ✅.

### Employees (EMP-001…020)

- `EMP-001` CEO stub (manager of all managers), `EMP-002` HR-Lead, `EMP-003` IT-Lead, `EMP-014/015/016` IT agents on shifts.
- `EMP-007` = **terminated 2026-06-30** (for rehire test with CAND-006 same email root).
- 12 hired-from-candidate rows created only *after* conversion in live demo; seed ships 8 pre-existing + `EMP-007` terminated + 11 active = 20 after judge clicks "Convert" on CAND-002 (seed pre-links CAND-002→EMP-021? No — keep deterministic: seed includes EMP-008…EMP-019 as already-converted earlier cohort, CAND-002 converts to EMP-020 live).

Simplest deterministic rule for judges: **seed loads 20 employees; converting CAND-002 creates EMP-021.** No ID collision.

### Equipment (20)

| Asset | Status | Linked to | Demo cue |
|---|---|---|---|
| LT-1001…1004 | on_hold | CAND-002, 005, 011, 012 | Assign live on Day-1 |
| LT-1005 | on_hold | CAND-002 **+ CAND-005** (double-hold) | ⚠️ Hold-conflict modal |
| LT-1006…1010 + MN/BDG | assigned/available | — | Normal pool |
| LT-1011 | repair | — | Excluded from picker, greyed |
| LT-1012 | retired, warranty expired | — | ⛔ Trap: must be unselectable |
| SN collision | LT-1008 `SN-MBP14-X7K2-991A` vs LT-1009 `SN-MBP14-X7K2-991B` | — | Unique-constraint test |

### Tickets (T-5001…5020)

| Ticket | Pri | Status | SLA | Demo cue |
|---|---|---|---|---|
| T-5001 | P1 | **breached** (open, due 6h ago) | 4h | 🔴 SLA banner + escalate button |
| T-5002 | P2 | **breached** | 8h | 🔴 auto-assign to on-shift agent |
| T-5003 | P1 | in_progress | due in 1h | 🟡 Due-soon |
| T-5004…5006 | P2/P3 | open | due tomorrow | On-shift mapping (SH-01 vs SH-02) |
| T-5007 | P3 | open, requester CAND-020 | due in 24h | Linked to weekend-starter |
| T-5008…5020 | mixed | resolved (6) / open / in_progress | met | Resolution-time stats |

---

## 4. API Spec — `POST /demo/seed` + `POST /demo/reset` (<5s)

### 4.1 Endpoints

```
POST /demo/seed    — idempotent full reload (truncate + insert + validate). Demo setup.
POST /demo/reset   — fast reset to post-seed snapshot (TRUNCATE + COPY FROM snapshot OR single-transaction restore). Judge-facing "Reset demo" button.
GET  /demo/status  — { seeded: bool, counts: {...}, seed_version, seeded_at, last_reset_ms }
```

Both POSTs are **demo-only**: `if (process.env.ALLOW_DEMO_SEED !== 'true') return 403`. Rate-limit 6/min/IP. Require header `x-demo-confirm: yes` (prevents accidental clicks) — UI sends it automatically.

### 4.2 Request / Response

```http
POST /demo/seed HTTP/1.1
x-demo-confirm: yes
Content-Type: application/json

{ "version": "v14", "include_attachments": true }
```

```json
// 200 OK
{
  "ok": true,
  "seed_version": "v14",
  "counts": { "candidates": 20, "employees": 20, "equipment": 20, "tickets": 20, "shifts": 8, "subscriptions": 6, "api_keys": 5 },
  "timings_ms": { "truncate": 210, "insert": 890, "validate": 320, "total": 1420 },
  "warnings": ["CAND-003 visa expires in 27d", "3 SLA-breached tickets staged", "1 double-hold conflict staged (LT-1005)"],
  "duration_ms": 1420
}

// 409 — already seeded and dirty (only if ?force=false and rows changed)
// { "ok": false, "error": "seed_dirty", "hint": "POST /demo/reset or /demo/seed with force:true" }
```

`POST /demo/reset` — same shape, `total` must be **<5000ms p95** (target <1500ms). Returns `duration_ms` + `reset_to_version`.

### 4.3 <5s Budget (how it's met)

| Step | Budget | Technique |
|---|---|---|
| Auth + guard | 5ms | env check first, no DB hit |
| Truncate | 300ms | **Single `TRUNCATE cands, emps, equip, tickets, shifts, subs, keys RESTART IDENTITY CASCADE`** — one round-trip; indexes kept |
| Insert | 1200ms | **Multi-row `INSERT … VALUES (…),(…)` (7 statements total, not 79)** from in-memory `seed.data.ts`; `UNLOGGED` staging or single transaction; prepared statements reused |
| Validate | 400ms | Row counts + 6 invariant queries in **one `Promise.all`**; attachments existence check skipped when `include_attachments=false` |
| Snapshot (reset path only) | — | After first `/seed`, `CREATE TABLE _snap_* AS SELECT *` — `/reset` = `TRUNCATE + INSERT INTO … SELECT FROM _snap_*` (no re-parse). Alternative: `pg_dump --data-only` cached buffer |
| Total | **≤2000ms target, 5000ms SLA** | p95 measured on free-tier Postgres (Neon/Supabase 256MB); SQLite <500ms |

**Failure semantics:** whole reload in **one transaction** — any invariant failure → `ROLLBACK` + `500 { ok:false, error:'seed_failed', failed_check:'…' }`, DB left untouched. Seed is **idempotent**: re-POST yields identical IDs/counts (no `gen_random_uuid()`, no `now()` — fixed `seeded_at = '2026-11-23T00:00:00Z'`, ticket `created_at` anchored relative to that).

**Frontend wiring:** `DemoBar` (`Seed` / `Reset` buttons) → `POST` → toast with `duration_ms` → `queryClient.invalidateQueries()` → boarding checklist re-renders. Disable buttons while pending; show `warnings[]` as demo script hints.

```ts
// seed.controller.ts (NestJS-style sketch)
@Post('seed') async seed(@Headers('x-demo-confirm') c: string, @Body() b: {version?: string; force?: boolean}) {
  if (process.env.ALLOW_DEMO_SEED !== 'true') throw new ForbiddenException('demo endpoints disabled');
  if (c !== 'yes') throw new BadRequestException('missing x-demo-confirm: yes');
  const t0 = Date.now();
  const r = await this.seedService.reload(b?.version ?? 'v14');
  return { ...r, duration_ms: Date.now() - t0 };
}
```

---

## 5. Edge Cases (must demo, must not corrupt)

### 5.1 Rehire duplicate (terminated → re-applies)

- **Setup:** `EMP-007 Rahul Verma (terminated 2026-06-30)` shares phone/email-root with `CAND-006` (same person, new application).
- **Rule:** converting CAND-006 must **not** create a second active `work_email`. Service checks `LOWER(work_email)` + `phone` against `status != 'terminated'` history → modal: *"Rehire detected — Rahul Verma (EMP-007, terminated). [Rehire → reactivate EMP-007] [Create new profile (requires HR override + reason)]"*.
- **Seed test:** `validate.py::test_rehire_flag` asserts the match query returns exactly 1 row. Unique **partial index**: `UNIQUE(work_email) WHERE status='active'` (allows history, blocks live dupes).

### 5.2 Auto-renew trap (cancelling seats ≠ cancelling renewal)

- **Setup:** `SUB-01 Figma auto_renew=true renewal 2026-11-25`.
- **Trap:** judge removes 1 seat → UI must still show *"Renews 2026-11-25 · auto-renew ON — turn off to avoid ₹37,475 charge"*. Cancelling seats only lowers next-cycle count; only `POST /subs/:id/auto-renew {off, reason}` stops billing.
- **Guard:** `cancelSeat` requires `acknowledge_renewal: true` checkbox if `renewal_date < now+7d`. Seed asserts `SUB-01.renewal_date - seeded_at < 7d` so the warning always fires in demo.

### 5.3 Prod API key not rotated (stale credential)

- **Setup:** `KEY-01 prod-deploy-key last_rotated 2026-02-01` (≈295d, `expires_at` passed); `KEY-02` healthy (7d).
- **Rule:** any deploy/offboard action while `KEY-01` is default → hard block: *"Prod key stale (>90d). Rotate before Day-1 provisioning."* + one-click `POST /keys/rotate` (old key → 24h grace, then revoked; audit-logged).
- **Seed test:** `test_stale_key_blocks_provision` calls `canProvision()` with seed data → expects `false` with reason `stale_prod_key`, and `true` after simulated rotation. Banner threshold: `>90d amber, >180d red`.

### 5.4 Three more traps in seed (bonus)

1. **Weekend-start with no IT cover:** CAND-004 starts Sat; `validate.py` warns if no `SH-*` covers Sat → judge sees *"No IT shift Sat — move start or assign on-call"*.
2. **BG-fail override audit:** converting CAND-009 requires typed reason → written to `audit_log(actor, action, reason)`; seed test asserts `audit_log` insert.
3. **Double-hold race:** LT-1005 held for two candidates → second `assign` gets `409 hold_conflict`; seed pre-stages it so judges hit the modal without setup.

---

## 6. Validation Checklist (`validate.py` — run in `/demo/seed` + CI)

```
[ ] counts == {20,20,20,20,8,6,5}
[ ] all FKs resolve; no orphan hold_for_candidate / assignee_id / shift_id
[ ] invariants §2.1 hold (signed→date, visa→expiry, start≥signed)
[ ] exactly 3 breached tickets by slaDue(); each has shift_id
[ ] 4 weekend starts present; visa-risk ≥3; bg-pending ≥5
[ ] serials unique; double-hold LT-1005 present; retired LT-1012 not assignable
[ ] rehire match == 1 row; stale prod key == KEY-01; SUB-01 renews within 7d
```

---

*Seed version: `v14` · anchored `seeded_at=2026-11-23T00:00:00Z` · total demo rows 79 · reload p95 1.4s / SLA 5s.*
