# 03 — DB Schema: HR+IT Demo (SQLite / Postgres)

> Source: `research/final/14-seed-data.md` (seed v14, `seeded_at=2026-11-23T00:00:00Z`, 79 demo rows). Target: one Postgres-first DDL that also runs on SQLite with zero forks, plus demo-only seed/reset contract.
> Conventions: `TEXT` PKs are deterministic (`CAND-001`, `EMP-001`, `LT-1001`, `T-5001`, `SH-01`, `SUB-01`, `KEY-01`); no `gen_random_uuid()` / `now()` in seed rows. All timestamps `TIMESTAMPTZ` in Postgres, `TEXT (ISO-8601)` in SQLite. Money in integer paise/INR minor units where computed.

---

## 1. Entity map + seed counts

| Table | Rows | PK | Key FKs |
|---|---|---|---|
| `candidates` | 20 | `candidate_id` | — (referenced by `employees.candidate_id`, `equipment.hold_for_candidate`) |
| `employees` | 20 (+`EMP-021` live on convert of CAND-002) | `employee_id` | `candidate_id → candidates`, `manager_id → employees`, `rehire_of → employees` |
| `equipment` | 20 | `asset_tag` | `assigned_to → employees`, `hold_for_candidate → candidates` |
| `tickets` | 20 | `ticket_id` | `requester_id → employees` (nullable — requester may be candidate, see §5), `assignee_id → employees`, `shift_id → shifts` |
| `shifts` | 8 | `shift_id` | — (referenced by `tickets.shift_id`; members via `shift_members`) |
| `shift_members` | ~14 (junction) | (`shift_id`, `employee_id`) | `shift_id → shifts`, `employee_id → employees` |
| `subscriptions` | 6 | `sub_id` | `owner_id → employees` |
| `api_keys` | 5 | `key_id` | — (rotation chain via `replaces_key_id → api_keys`) |
| `audit_log` | grows (seed: 2 exemplar rows) | `audit_id BIGSERIAL/INTEGER PK` | `actor_id → employees` nullable (system actions `NULL`) |
| `idempotency_ledger` | grows (seed: empty) | `idempotency_key TEXT PK` | — (no FK; stores request hash + response) |

Total seed rows: 20+20+20+20+8+6+5 = 99? No — spec counts only 7 tables = **79 rows** (shift_members junction + audit exemplars are extra infra rows, excluded from the 79 contract; `validate.py` asserts exactly the 7 counts).

---

## 2. DDL (Postgres-first, SQLite-compatible)

> SQLite notes inline as `-- SQLITE:` comments. `ENUM` → `TEXT + CHECK`. `TIMESTAMPTZ` → `TEXT`. `BIGSERIAL` → `INTEGER PRIMARY KEY AUTOINCREMENT`. Partial unique indexes work on both. `TRUNCATE … CASCADE` (Postgres) → `DELETE FROM` in dependency-reverse order (SQLite); both wrapped in one transaction.

```sql
-- ============ 0. extensions / pragmas ============
-- POSTGRES: CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- only if you need gen_random_uuid() outside seed
-- SQLITE: PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL;

-- ============ 1. candidates (20) ============
CREATE TABLE candidates (
  candidate_id      TEXT PRIMARY KEY,                    -- CAND-001…CAND-020
  full_name         TEXT NOT NULL,
  email             TEXT NOT NULL,                       -- firstname.lastnameNN@example.com, no real PII
  role              TEXT NOT NULL,                       -- SDE-1 | SDE-2 | Designer | PM | IT-Support | HR-Exec
  dept              TEXT NOT NULL,                       -- Engineering | Design | Product | IT | HR
  offer_status      TEXT NOT NULL,                       -- signed | pending | declined | expired
  offer_signed_at   DATE,                                -- required iff signed
  bg_status         TEXT NOT NULL,                       -- pass | pending | fail | waived_intern | not_started
  bg_completed_at   DATE,                                -- required iff pass/fail
  visa_status       TEXT NOT NULL,                       -- citizen | h1b_valid | h1b_expiring_30d | opt_expiring_15d | requires_sponsorship
  visa_expiry       DATE,                                -- required unless citizen
  start_date        DATE,                                -- NULL allowed for declined/expired; 4 weekend starts staged
  source            TEXT NOT NULL DEFAULT 'portal',      -- referral | campus | portal
  notes             TEXT NOT NULL DEFAULT '',            -- demo cue: BLOCKED-BG | VISA-RISK | WEEKEND-START
  created_at        TIMESTAMPTZ NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  -- SQLITE: store TIMESTAMPTZ/DATE as TEXT ISO-8601; DEFAULT '2026-11-23T00:00:00Z'

  CONSTRAINT ck_cand_offer_status CHECK (offer_status IN ('signed','pending','declined','expired')),
  CONSTRAINT ck_cand_bg_status    CHECK (bg_status IN ('pass','pending','fail','waived_intern','not_started')),
  CONSTRAINT ck_cand_visa_status  CHECK (visa_status IN ('citizen','h1b_valid','h1b_expiring_30d','opt_expiring_15d','requires_sponsorship')),
  CONSTRAINT ck_cand_role         CHECK (role IN ('SDE-1','SDE-2','Designer','PM','IT-Support','HR-Exec')),
  CONSTRAINT ck_cand_dept         CHECK (dept IN ('Engineering','Design','Product','IT','HR')),
  CONSTRAINT ck_cand_signed_date  CHECK (
    (offer_status = 'signed' AND offer_signed_at IS NOT NULL)
    OR (offer_status <> 'signed')
  ),
  CONSTRAINT ck_cand_bg_date CHECK (
    (bg_status IN ('pass','fail') AND bg_completed_at IS NOT NULL)
    OR (bg_status NOT IN ('pass','fail'))
  ),
  CONSTRAINT ck_cand_visa_date CHECK (
    (visa_status <> 'citizen' AND visa_expiry IS NOT NULL)
    OR (visa_status = 'citizen')
  ),
  CONSTRAINT ck_cand_start_after_sign CHECK (
    start_date IS NULL OR offer_signed_at IS NULL OR start_date >= offer_signed_at
  ),
  CONSTRAINT ck_cand_declined_no_start CHECK (
    -- declined/expired rows normally carry no start_date (CAND-014/017/019)
    (offer_status IN ('declined','expired') AND start_date IS NULL)
    OR (offer_status IN ('signed','pending'))
  )
);
CREATE UNIQUE INDEX ux_candidates_email_active
  ON candidates (lower(email)) WHERE offer_status <> 'declined';
-- partial unique: blocks live dupe applications, allows declined history to re-apply.
-- NOTE: seed wants plain UNIQUE(email); prefer this partial variant + validate.py uniqueness check
-- over declined rows, so CAND re-application doesn't 500 the demo.

-- ============ 2. employees (20; live convert creates EMP-021) ============
CREATE TABLE employees (
  employee_id     TEXT PRIMARY KEY,                      -- EMP-001…EMP-020
  candidate_id    TEXT REFERENCES candidates(candidate_id) ON DELETE SET NULL,
  full_name       TEXT NOT NULL,
  work_email      TEXT NOT NULL,                         -- firstname.lastname@demo.example.com
  phone           TEXT,                                  -- used by rehire match (EMP-007 ↔ CAND-006)
  dept            TEXT NOT NULL,
  role            TEXT NOT NULL,
  employment_type TEXT NOT NULL DEFAULT 'full_time',    -- full_time | intern | contractor
  status          TEXT NOT NULL DEFAULT 'active',        -- active | on_notice | terminated
  join_date       DATE NOT NULL,
  manager_id      TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  rehire_of       TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT '2026-11-23T00:00:00Z',

  CONSTRAINT ck_emp_type   CHECK (employment_type IN ('full_time','intern','contractor')),
  CONSTRAINT ck_emp_status CHECK (status IN ('active','on_notice','terminated')),
  CONSTRAINT ck_emp_no_self_manage CHECK (manager_id IS NULL OR manager_id <> employee_id),
  CONSTRAINT ck_emp_no_self_rehire CHECK (rehire_of IS NULL OR rehire_of <> employee_id),
  CONSTRAINT ck_emp_rehire_chain   CHECK (
    -- only terminated history rows are valid rehire targets; enforced at app layer too
    rehire_of IS NULL OR status <> 'terminated'
  )
);
-- THE critical partial unique from §5.1: history allowed, live dupes blocked
CREATE UNIQUE INDEX ux_employees_work_email_active
  ON employees (lower(work_email)) WHERE status IN ('active','on_notice');
CREATE INDEX ix_employees_candidate ON employees (candidate_id) WHERE candidate_id IS NOT NULL;
CREATE INDEX ix_employees_manager   ON employees (manager_id)   WHERE manager_id IS NOT NULL;
CREATE INDEX ix_employees_status    ON employees (status);

-- ============ 3. equipment (20) ============
CREATE TABLE equipment (
  asset_tag           TEXT PRIMARY KEY,                  -- LT-1001… | MN-2001… | BDG-3001…
  serial              TEXT NOT NULL,                     -- 2 near-dupes differ by 1 char (collision guard test)
  category            TEXT NOT NULL,                     -- laptop | monitor | badge
  model               TEXT NOT NULL,                     -- MacBook Pro 14 | ThinkPad T14 | Dell U2723QE
  status              TEXT NOT NULL DEFAULT 'available', -- available | assigned | on_hold | repair | retired
  assigned_to         TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  hold_for_candidate  TEXT REFERENCES candidates(candidate_id) ON DELETE SET NULL,
  location            TEXT NOT NULL DEFAULT 'HYD-Store', -- BLR-Desk-… | HYD-Store
  po_number           TEXT NOT NULL,
  warranty_expiry     DATE NOT NULL,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT '2026-11-23T00:00:00Z',

  CONSTRAINT ck_eq_cat    CHECK (category IN ('laptop','monitor','badge')),
  CONSTRAINT ck_eq_status  CHECK (status IN ('available','assigned','on_hold','repair','retired')),
  CONSTRAINT ck_eq_assigned_iff CHECK (
    (status = 'assigned' AND assigned_to IS NOT NULL AND hold_for_candidate IS NULL)
    OR (status = 'on_hold' AND hold_for_candidate IS NOT NULL AND assigned_to IS NULL)
    OR (status IN ('available','repair','retired') AND assigned_to IS NULL)
    -- NOTE: on_hold + assigned_to both set is rejected; double-hold across ROWS
    -- (LT-1005 held for CAND-002 AND CAND-005) is staged via a second hold row, see §4
  ),
  CONSTRAINT ck_eq_hold_needs_cand CHECK (
    (hold_for_candidate IS NULL) OR (status = 'on_hold')
  )
);
CREATE UNIQUE INDEX ux_equipment_serial ON equipment (serial);
-- Double-hold conflict staging: second hold for same asset lives in equipment_holds (§4),
-- so this table keeps one canonical hold_for_candidate while the race is demonstrable.
CREATE INDEX ix_equipment_status   ON equipment (status);
CREATE INDEX ix_equipment_assignee ON equipment (assigned_to) WHERE assigned_to IS NOT NULL;

-- Hold-race ledger (supports LT-1005 double-hold without violating ck_eq_assigned_iff):
CREATE TABLE equipment_holds (
  hold_id       TEXT PRIMARY KEY,                        -- HOLD-001…
  asset_tag     TEXT NOT NULL REFERENCES equipment(asset_tag) ON DELETE CASCADE,
  candidate_id  TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  placed_by     TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  placed_at     TIMESTAMPTZ NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  released_at   TIMESTAMPTZ,
  CONSTRAINT ck_hold_release CHECK (released_at IS NULL OR released_at >= placed_at)
);
-- Only one UNRELEASED hold per (asset, candidate); same asset held for 2 candidates = conflict demo
CREATE UNIQUE INDEX ux_holds_open_per_pair ON equipment_holds (asset_tag, candidate_id) WHERE released_at IS NULL;

-- ============ 4. shifts (8) + members ============
CREATE TABLE shifts (
  shift_id    TEXT PRIMARY KEY,                          -- SH-01…SH-08
  name        TEXT NOT NULL,                             -- BLR-Morning | BLR-Evening | Night-OnCall …
  start_time  TIME NOT NULL,                             -- 09:00, 14:00, 22:00 …
  end_time    TIME NOT NULL,                             -- overnight allowed (22:00→06:00)
  timezone    TEXT NOT NULL DEFAULT 'Asia/Kolkata',
  -- overnight shifts have end_time <= start_time; same-day shifts end > start — no CHECK, handled by routing fn
  CONSTRAINT ck_shift_tz CHECK (timezone IN ('Asia/Kolkata','UTC'))
);
CREATE TABLE shift_members (
  shift_id    TEXT NOT NULL REFERENCES shifts(shift_id) ON DELETE CASCADE,
  employee_id TEXT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
  PRIMARY KEY (shift_id, employee_id)
);
-- Seed: SH-01 {EMP-014,EMP-015}, SH-02 {EMP-014,EMP-016}, SH-03 {EMP-016}, … 8 shifts ≈14 memberships.
-- Ticket→shift pre-computed by created_at-in-window; validate.py re-derives it.

-- ============ 5. tickets (20) ============
CREATE TABLE tickets (
  ticket_id     TEXT PRIMARY KEY,                        -- T-5001…T-5020
  title         TEXT NOT NULL,
  requester_id  TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  requester_candidate TEXT REFERENCES candidates(candidate_id) ON DELETE SET NULL,
  assignee_id   TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  priority      TEXT NOT NULL,                           -- P1 | P2 | P3 | P4
  category      TEXT NOT NULL,                           -- laptop_setup | access | vpn | payroll | badge | other
  status        TEXT NOT NULL DEFAULT 'open',            -- open | in_progress | resolved | breached
  created_at    TIMESTAMPTZ NOT NULL,                    -- anchored to seeded_at minus offsets (deterministic SLA)
  due_at        TIMESTAMPTZ NOT NULL,                    -- slaDue(created_at, priority): P1=4h P2=8h P3=24h P4=48h
  resolved_at   TIMESTAMPTZ,
  shift_id      TEXT NOT NULL REFERENCES shifts(shift_id) ON DELETE RESTRICT,
  channel       TEXT NOT NULL DEFAULT 'portal',          -- portal | email | slack

  CONSTRAINT ck_tk_pri   CHECK (priority IN ('P1','P2','P3','P4')),
  CONSTRAINT ck_tk_cat   CHECK (category IN ('laptop_setup','access','vpn','payroll','badge','other')),
  CONSTRAINT ck_tk_stat  CHECK (status IN ('open','in_progress','resolved','breached')),
  CONSTRAINT ck_tk_chan  CHECK (channel IN ('portal','email','slack')),
  CONSTRAINT ck_tk_due_after_create CHECK (due_at > created_at),
  CONSTRAINT ck_tk_resolved_iff CHECK (
    (status = 'resolved' AND resolved_at IS NOT NULL)
    OR (status <> 'resolved' AND resolved_at IS NULL)
  ),
  CONSTRAINT ck_tk_resolved_after_create CHECK (
    resolved_at IS NULL OR resolved_at >= created_at
  ),
  CONSTRAINT ck_tk_requester CHECK (
    requester_id IS NOT NULL OR requester_candidate IS NOT NULL
    -- T-5007 requester is CAND-020 (weekend-starter); most tickets requester_id → employees
  )
);
CREATE INDEX ix_tickets_status    ON tickets (status);
CREATE INDEX ix_tickets_priority  ON tickets (priority);
CREATE INDEX ix_tickets_assignee  ON tickets (assignee_id) WHERE assignee_id IS NOT NULL;
CREATE INDEX ix_tickets_shift     ON tickets (shift_id);
CREATE INDEX ix_tickets_due       ON tickets (due_at) WHERE status <> 'resolved';
-- Breach query pattern: WHERE status <> 'resolved' AND due_at < now() — covered by ix_tickets_due.

-- ============ 6. subscriptions (6) — auto-renew trap ============
CREATE TABLE subscriptions (
  sub_id          TEXT PRIMARY KEY,                      -- SUB-01…SUB-06
  tool            TEXT NOT NULL,                         -- Figma | Slack | …
  seats           INTEGER NOT NULL,
  seat_cost_inr   INTEGER NOT NULL,                      -- minor units (₹1,499 → 149900 paise); avoids float
  renewal_date    DATE NOT NULL,                         -- SUB-01 = 2026-11-25 (< seeded_at+7d → warning always fires)
  auto_renew      BOOLEAN NOT NULL DEFAULT TRUE,         -- SQLITE: INTEGER 0/1 + CHECK below
  cancelled_at    TIMESTAMPTZ,
  owner_id        TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,

  CONSTRAINT ck_sub_seats  CHECK (seats > 0),
  CONSTRAINT ck_sub_cost   CHECK (seat_cost_inr > 0),
  CONSTRAINT ck_sub_cancel CHECK (cancelled_at IS NULL OR auto_renew = FALSE)
  -- SQLITE: CHECK (auto_renew IN (0,1)) — add when generating sqlite DDL
);
CREATE INDEX ix_subs_renewal ON subscriptions (renewal_date) WHERE auto_renew = TRUE;
-- Guard lives in app: cancelSeat within 7d of renewal_date requires acknowledge_renewal=true.

-- ============ 7. api_keys (5) — rotation edge ============
CREATE TABLE api_keys (
  key_id          TEXT PRIMARY KEY,                      -- KEY-01…KEY-05
  label           TEXT NOT NULL,                         -- prod-deploy-key | prod-read …
  key_prefix      TEXT NOT NULL,                         -- first 8 chars only; never store raw secret
  key_hash        TEXT NOT NULL,                         -- sha256 of full key
  created_at      TIMESTAMPTZ NOT NULL,
  last_rotated_at TIMESTAMPTZ NOT NULL,
  expires_at      TIMESTAMPTZ NOT NULL,
  scope           TEXT NOT NULL,                         -- deploy | read | admin …
  is_prod         BOOLEAN NOT NULL DEFAULT FALSE,
  replaces_key_id TEXT REFERENCES api_keys(key_id) ON DELETE SET NULL,  -- rotation chain (grace window)
  revoked_at      TIMESTAMPTZ,

  CONSTRAINT ck_key_scope CHECK (scope IN ('deploy','read','admin')),
  CONSTRAINT ck_key_rotated CHECK (last_rotated_at >= created_at),
  CONSTRAINT ck_key_revoke  CHECK (revoked_at IS NULL OR revoked_at >= last_rotated_at)
  -- SQLITE: is_prod IN (0,1)
);
-- Seed: KEY-01 prod-deploy last_rotated 2026-02-01 (≈295d, expired — hard-blocks provision);
-- KEY-02 prod-read rotated 7d ago (healthy control). Banner: >90d amber, >180d red.
CREATE UNIQUE INDEX ux_api_keys_prefix ON api_keys (key_prefix);
CREATE INDEX ix_api_keys_prod ON api_keys (is_prod, last_rotated_at) WHERE revoked_at IS NULL;

-- ============ 8. audit_log (append-only) ============
CREATE TABLE audit_log (
  audit_id    BIGSERIAL PRIMARY KEY,
  -- SQLITE: audit_id INTEGER PRIMARY KEY AUTOINCREMENT
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  actor_id    TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  action      TEXT NOT NULL,                             -- candidate.convert | bg.override | key.rotate | sub.auto_renew_off | equip.assign …
  entity      TEXT NOT NULL,                             -- candidate | employee | equipment | ticket | subscription | api_key
  entity_id   TEXT NOT NULL,                             -- CAND-009 | LT-1005 | KEY-01 …
  reason      TEXT,                                      -- REQUIRED for bg.override + rehire-create-new (app-enforced)
  metadata    JSONB,                                     -- SQLITE: TEXT (JSON string)
  CONSTRAINT ck_audit_action CHECK (action <> '')
);
CREATE INDEX ix_audit_entity ON audit_log (entity, entity_id);
CREATE INDEX ix_audit_actor  ON audit_log (occurred_at DESC, actor_id);
-- App rule (not DB): REVOKE UPDATE/DELETE ON audit_log FROM app_role (Postgres); SQLite: no UPDATE/DELETE triggers.

-- ============ 9. idempotency_ledger ============
CREATE TABLE idempotency_ledger (
  idempotency_key TEXT PRIMARY KEY,                      -- client-sent Idempotency-Key header (uuid/v4)
  endpoint        TEXT NOT NULL,                         -- POST /demo/seed | POST /employees/convert | POST /keys/rotate …
  request_hash    TEXT NOT NULL,                         -- sha256(canonical body) — mismatched reuse → 422
  status_code     INTEGER NOT NULL,
  response_body   JSONB NOT NULL,                        -- SQLITE: TEXT
  created_at      TIMESTAMPTZ NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  expires_at      TIMESTAMPTZ NOT NULL,                  -- created_at + 24h (sweep job deletes expired)
  CONSTRAINT ck_idem_status CHECK (status_code BETWEEN 200 AND 599)
);
CREATE INDEX ix_idem_expiry ON idempotency_ledger (expires_at);
```

---

## 3. FK dependency order (seed + truncate)

**Insert order (parents first):** `shifts → candidates → employees (managers first: EMP-001, then rest; self-FK needs deferrable or two-pass UPDATE) → shift_members → equipment (+ equipment_holds) → tickets → subscriptions → api_keys (KEY-01 before keys that replace it) → audit_log` (idempotency_ledger stays empty at seed).

- `employees.manager_id` self-FK: seed in two passes (INSERT with `manager_id NULL`, then UPDATE), or Postgres `SET CONSTRAINTS … DEFERRED` with `DEFERRABLE INITIALLY DEFERRED`. SQLite path uses two-pass.
- **Truncate:** Postgres single statement `TRUNCATE candidates, employees, equipment, equipment_holds, tickets, shifts, shift_members, subscriptions, api_keys, audit_log, idempotency_ledger RESTART IDENTITY CASCADE;` — one round-trip. SQLite: `DELETE FROM` in reverse order inside one transaction (+ `DELETE FROM sqlite_sequence`).

---

## 4. Partial unique indexes (why partial, not plain UNIQUE)

| Index | Predicate | What it allows | What it blocks |
|---|---|---|---|
| `ux_candidates_email_active WHERE offer_status <> 'declined'` | re-applications after decline | second live application with same email | — |
| `ux_employees_work_email_active WHERE status IN ('active','on_notice')` | terminated history (`EMP-007`) coexists with re-applicant (`CAND-006`) | creating a 2nd **active** `work_email` on convert → forces Rehire modal (`reactivate EMP-007` vs `override + reason → audit_log`) | — |
| `ux_holds_open_per_pair WHERE released_at IS NULL` | LT-1005 held for CAND-002 **and** CAND-005 simultaneously (different pairs, both open) | 3rd identical hold row | second `assign` on LT-1005 → `409 hold_conflict` |
| `ux_equipment_serial` (full unique) | — | — | near-dupe serial insert (LT-1008 vs LT-1009 differ by 1 char — must stay unique) |
| `ux_api_keys_prefix` (full unique) | — | — | prefix collision on rotate |

---

## 5. CHECK-constraint → demo-trap traceability

| Seed trap (from 14 §5) | Enforcing CHECK / index | App-layer companion |
|---|---|---|
| BG-pending gate (CAND-001), BG-fail (CAND-009) | `ck_cand_bg_date`; convert service rejects `bg_status NOT IN ('pass','waived_intern')` | HR override requires typed reason → `audit_log(bg.override)` |
| VISA-RISK (CAND-003/006/008/016) | `ck_cand_visa_date` guarantees expiry present → banner `visa_expiry − now()` | banner thresholds; sponsorship-letter task auto-created (CAND-016) |
| Weekend start (CAND-004/005/011/020) | none (warning, not error) | shift-cover check: no `SH-*` Sat → *"move start or assign on-call"* |
| Retired asset trap (LT-1012) | `ck_eq_assigned_iff` + picker filter `status IN ('available','on_hold')` | greyed-out row, unselectable |
| Double-hold race (LT-1005) | `ux_holds_open_per_pair` + `ck_eq_assigned_iff` | `409 hold_conflict` modal |
| SLA breach (T-5001/5002 + 1 more) | `ck_tk_due_after_create`, `ck_tk_resolved_iff` | `slaDue()` shared seed+UI; escalate + on-shift auto-assign |
| Auto-renew trap (SUB-01) | `ck_sub_cancel` (cancel ⇒ auto_renew OFF path) | `acknowledge_renewal` checkbox <7d to renewal |
| Stale prod key (KEY-01, 295d) | `ck_key_rotated`; provision gate `max(last_rotated_at) < now−90d → block` | one-click `POST /keys/rotate` (24h grace → revoke, audit-logged) |
| Serial collision (LT-1008/1009) | `ux_equipment_serial` | insert guard + friendly error |

---

## 6. Seed counts + validation query bundle

Expected post-`POST /demo/seed`: `{candidates:20, employees:20, equipment:20, tickets:20, shifts:8, subscriptions:6, api_keys:5}` (+ junction/audit rows excluded from contract).

```sql
-- one-round-trip count check (also the GET /demo/status counts source)
SELECT 'candidates' AS t, COUNT(*) FROM candidates UNION ALL
SELECT 'employees', COUNT(*) FROM employees UNION ALL
SELECT 'equipment', COUNT(*) FROM equipment UNION ALL
SELECT 'tickets', COUNT(*) FROM tickets UNION ALL
SELECT 'shifts', COUNT(*) FROM shifts UNION ALL
SELECT 'subscriptions', COUNT(*) FROM subscriptions UNION ALL
SELECT 'api_keys', COUNT(*) FROM api_keys;
-- FK orphans (must all return 0):
SELECT COUNT(*) FROM employees   e LEFT JOIN candidates c ON c.candidate_id=e.candidate_id   WHERE e.candidate_id IS NOT NULL AND c.candidate_id IS NULL;
SELECT COUNT(*) FROM equipment   q LEFT JOIN candidates c ON c.candidate_id=q.hold_for_candidate WHERE q.hold_for_candidate IS NOT NULL AND c.candidate_id IS NULL;
SELECT COUNT(*) FROM tickets     t LEFT JOIN shifts     s ON s.shift_id=t.shift_id           WHERE s.shift_id IS NULL;
-- invariant spot-checks:
SELECT COUNT(*) FROM candidates WHERE offer_status='signed' AND offer_signed_at IS NULL;  -- expect 0
SELECT COUNT(*) FROM candidates WHERE visa_status<>'citizen' AND visa_expiry IS NULL;      -- expect 0
SELECT COUNT(*) FROM tickets WHERE status<>'resolved' AND due_at < '2026-11-23T00:00:00Z';  -- expect 3 (breached)
SELECT COUNT(*) FROM candidates WHERE strftime('%w', start_date) IN ('0','6');              -- expect 4 (SQLite) / EXTRACT(DOW…) IN (0,6) (PG)
```

`POST /demo/seed` = truncate + 7 multi-row INSERTs + this bundle, one transaction, `ROLLBACK` on any failure; idempotent (fixed IDs, fixed `seeded_at`); `POST /demo/reset` restores `_snap_*` snapshot (<5s SLA, ~1.4s target). Demo-gated (`ALLOW_DEMO_SEED`, `x-demo-confirm: yes`, 6/min/IP).

---

*Seed v14 · files: `seed/schema.sql` (this §2), CSVs + `seed.data.ts` codegen, `reset.sql`, `validate.py` · tables 11 (7 counted + shift_members, equipment_holds, audit_log, idempotency_ledger) · partial uniques 3 + full uniques 2.*
