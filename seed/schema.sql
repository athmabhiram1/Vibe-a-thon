-- seed/schema.sql — v14 demo DDL (SQLite-only golden path, no ORM)
-- 11 tables · FK dependency order · partial uniques WHERE deleted_at IS NULL
-- WAL pragmas + snapshot/reset recipe: see seed/README.md
-- All timestamps TEXT ISO-8601 · booleans INTEGER 0/1 · seeded_at fixed 2026-11-23T00:00:00Z
-- Env: python sqlite3 3.38.4 (VACUUM INTO needs >= 3.27, partial index native)

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;

-- ============ 1. candidates (20) ============
CREATE TABLE IF NOT EXISTS candidates (
  candidate_id      TEXT PRIMARY KEY,                    -- CAND-001...CAND-020
  full_name         TEXT NOT NULL,
  email             TEXT NOT NULL,                       -- firstname.lastnameNN@example.com, no real PII
  role              TEXT NOT NULL,                       -- SDE-1 | SDE-2 | Designer | PM | IT-Support | HR-Exec
  dept              TEXT NOT NULL,                       -- Engineering | Design | Product | IT | HR
  offer_status      TEXT NOT NULL,                       -- signed | pending | declined | expired
  offer_signed_at   TEXT,                                -- required iff signed (ISO DATE)
  bg_status         TEXT NOT NULL,                       -- pass | pending | fail | waived_intern | not_started
  bg_completed_at   TEXT,                                -- required iff pass/fail
  visa_status       TEXT NOT NULL,                       -- citizen | h1b_valid | h1b_expiring_30d | opt_expiring_15d | requires_sponsorship
  visa_expiry       TEXT,                                -- required unless citizen
  start_date        TEXT,                                -- NULL for declined/expired; 4 weekend starts staged
  source            TEXT NOT NULL DEFAULT 'portal',      -- referral | campus | portal
  phone             TEXT,                                -- used by rehire match (CAND-006 <-> EMP-007)
  notes             TEXT NOT NULL DEFAULT '',           -- demo cue: BLOCKED-BG | VISA-RISK | WEEKEND-START
  created_at        TEXT NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  deleted_at        TEXT DEFAULT NULL,                   -- soft delete; partial uniques ignore deleted rows

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
    (offer_status IN ('declined','expired') AND start_date IS NULL)
    OR (offer_status IN ('signed','pending'))
  )
);
-- Partial unique: live dupes blocked, deleted history allowed to re-apply.
CREATE UNIQUE INDEX IF NOT EXISTS ux_candidates_email_active
  ON candidates (lower(email)) WHERE deleted_at IS NULL;

-- ============ 2. shifts (8) — no FK deps, seed before tickets ============
CREATE TABLE IF NOT EXISTS shifts (
  shift_id    TEXT PRIMARY KEY,                          -- SH-01...SH-08
  name        TEXT NOT NULL,                             -- BLR-Morning | BLR-Evening | Night-OnCall ...
  start_time  TEXT NOT NULL,                             -- HH:MM 24h
  end_time    TEXT NOT NULL,                             -- overnight allowed (22:00 -> 06:00)
  timezone    TEXT NOT NULL DEFAULT 'Asia/Kolkata',
  deleted_at  TEXT DEFAULT NULL,
  CONSTRAINT ck_shift_tz CHECK (timezone IN ('Asia/Kolkata','UTC'))
);

-- ============ 3. employees (20; live convert of CAND-002 creates EMP-021) ============
CREATE TABLE IF NOT EXISTS employees (
  employee_id     TEXT PRIMARY KEY,                      -- EMP-001...EMP-020
  candidate_id    TEXT REFERENCES candidates(candidate_id) ON DELETE SET NULL,
  full_name       TEXT NOT NULL,
  work_email      TEXT NOT NULL,                         -- firstname.lastname@demo.example.com
  phone           TEXT,                                  -- rehire match key (EMP-007 <-> CAND-006)
  dept            TEXT NOT NULL,
  role            TEXT NOT NULL,
  employment_type TEXT NOT NULL DEFAULT 'full_time',    -- full_time | intern | contractor
  status          TEXT NOT NULL DEFAULT 'active',        -- active | on_notice | terminated
  join_date       TEXT NOT NULL,
  manager_id      TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  rehire_of       TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  created_at      TEXT NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  deleted_at      TEXT DEFAULT NULL,

  CONSTRAINT ck_emp_type   CHECK (employment_type IN ('full_time','intern','contractor')),
  CONSTRAINT ck_emp_status CHECK (status IN ('active','on_notice','terminated')),
  CONSTRAINT ck_emp_no_self_manage CHECK (manager_id IS NULL OR manager_id <> employee_id),
  CONSTRAINT ck_emp_no_self_rehire CHECK (rehire_of IS NULL OR rehire_of <> employee_id),
  CONSTRAINT ck_emp_rehire_chain   CHECK (
    rehire_of IS NULL OR status <> 'terminated'
  )
);
-- THE critical partial unique: terminated history coexists, live dupes blocked.
-- Rehire modal (reactivate EMP-007 vs override + reason -> audit_log) enforced at app layer.
CREATE UNIQUE INDEX IF NOT EXISTS ux_employees_work_email_active
  ON employees (lower(work_email)) WHERE deleted_at IS NULL AND status IN ('active','on_notice');
CREATE INDEX IF NOT EXISTS ix_employees_candidate ON employees (candidate_id) WHERE candidate_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_employees_manager   ON employees (manager_id)   WHERE manager_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_employees_status    ON employees (status);

-- ============ 4. shift_members (junction, ~10 rows; excluded from 79-count) ============
CREATE TABLE IF NOT EXISTS shift_members (
  shift_id    TEXT NOT NULL REFERENCES shifts(shift_id) ON DELETE CASCADE,
  employee_id TEXT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
  PRIMARY KEY (shift_id, employee_id)
);

-- ============ 5. equipment (20) ============
CREATE TABLE IF NOT EXISTS equipment (
  asset_tag           TEXT PRIMARY KEY,                  -- LT-1001... | MN-2001... | BDG-3001...
  serial              TEXT NOT NULL,                     -- 2 near-dupes differ by 1 char (collision guard)
  category            TEXT NOT NULL,                     -- laptop | monitor | badge
  model               TEXT NOT NULL,                     -- MacBook Pro 14 | ThinkPad T14 | Dell U2723QE
  status              TEXT NOT NULL DEFAULT 'available', -- available | assigned | on_hold | repair | retired
  assigned_to         TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  hold_for_candidate  TEXT REFERENCES candidates(candidate_id) ON DELETE SET NULL,
  location            TEXT NOT NULL DEFAULT 'HYD-Store', -- BLR-Desk-... | HYD-Store
  po_number           TEXT NOT NULL,
  warranty_expiry     TEXT NOT NULL,
  created_at          TEXT NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  deleted_at          TEXT DEFAULT NULL,

  CONSTRAINT ck_eq_cat    CHECK (category IN ('laptop','monitor','badge')),
  CONSTRAINT ck_eq_status  CHECK (status IN ('available','assigned','on_hold','repair','retired')),
  CONSTRAINT ck_eq_assigned_iff CHECK (
    (status = 'assigned' AND assigned_to IS NOT NULL AND hold_for_candidate IS NULL)
    OR (status = 'on_hold' AND hold_for_candidate IS NOT NULL AND assigned_to IS NULL)
    OR (status IN ('available','repair','retired') AND assigned_to IS NULL)
  ),
  CONSTRAINT ck_eq_hold_needs_cand CHECK (
    (hold_for_candidate IS NULL) OR (status = 'on_hold')
  )
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_equipment_serial
  ON equipment (serial) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_equipment_status   ON equipment (status);
CREATE INDEX IF NOT EXISTS ix_equipment_assignee ON equipment (assigned_to) WHERE assigned_to IS NOT NULL;

-- ============ 6. equipment_holds (hold-race ledger; LT-1005 double-hold lives here) ============
CREATE TABLE IF NOT EXISTS equipment_holds (
  hold_id       TEXT PRIMARY KEY,                        -- HOLD-001...
  asset_tag     TEXT NOT NULL REFERENCES equipment(asset_tag) ON DELETE CASCADE,
  candidate_id  TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  placed_by     TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  placed_at     TEXT NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  released_at   TEXT,
  CONSTRAINT ck_hold_release CHECK (released_at IS NULL OR released_at >= placed_at)
);
-- Only one UNRELEASED hold per (asset, candidate); same asset held for 2 candidates = conflict demo.
CREATE UNIQUE INDEX IF NOT EXISTS ux_holds_open_per_pair
  ON equipment_holds (asset_tag, candidate_id) WHERE released_at IS NULL;

-- ============ 7. tickets (20) ============
CREATE TABLE IF NOT EXISTS tickets (
  ticket_id     TEXT PRIMARY KEY,                        -- T-5001...T-5020
  title         TEXT NOT NULL,
  requester_id  TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  requester_candidate TEXT REFERENCES candidates(candidate_id) ON DELETE SET NULL,
  assignee_id   TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  priority      TEXT NOT NULL,                           -- P1 | P2 | P3 | P4
  category      TEXT NOT NULL,                           -- laptop_setup | access | vpn | payroll | badge | other
  status        TEXT NOT NULL DEFAULT 'open',            -- open | in_progress | resolved | breached
  created_at    TEXT NOT NULL,                           -- anchored to seeded_at minus offsets (deterministic SLA)
  due_at        TEXT NOT NULL,                           -- slaDue(created_at, priority): P1=4h P2=8h P3=24h P4=48h
  resolved_at   TEXT,
  shift_id      TEXT NOT NULL REFERENCES shifts(shift_id) ON DELETE RESTRICT,
  channel       TEXT NOT NULL DEFAULT 'portal',          -- portal | email | slack
  deleted_at    TEXT DEFAULT NULL,

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
  )
);
CREATE INDEX IF NOT EXISTS ix_tickets_status    ON tickets (status);
CREATE INDEX IF NOT EXISTS ix_tickets_priority  ON tickets (priority);
CREATE INDEX IF NOT EXISTS ix_tickets_assignee  ON tickets (assignee_id) WHERE assignee_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_tickets_shift     ON tickets (shift_id);
CREATE INDEX IF NOT EXISTS ix_tickets_due       ON tickets (due_at) WHERE status <> 'resolved';

-- ============ 8. subscriptions (6) — auto-renew trap ============
CREATE TABLE IF NOT EXISTS subscriptions (
  sub_id          TEXT PRIMARY KEY,                      -- SUB-01...SUB-06
  tool            TEXT NOT NULL,                         -- Figma | Slack | ...
  seats           INTEGER NOT NULL,
  seat_cost_inr   INTEGER NOT NULL,                      -- minor units (Rs.1,499 -> 149900 paise); avoids float
  renewal_date    TEXT NOT NULL,                         -- SUB-01 = 2026-11-25 (< seeded_at+7d -> warning fires)
  auto_renew      INTEGER NOT NULL DEFAULT 1,            -- 0/1; SQLite bool
  cancelled_at    TEXT,
  owner_id        TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  created_at      TEXT NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  deleted_at      TEXT DEFAULT NULL,

  CONSTRAINT ck_sub_bool   CHECK (auto_renew IN (0,1)),
  CONSTRAINT ck_sub_seats  CHECK (seats > 0),
  CONSTRAINT ck_sub_cost   CHECK (seat_cost_inr > 0),
  CONSTRAINT ck_sub_cancel CHECK (cancelled_at IS NULL OR auto_renew = 0)
);
CREATE INDEX IF NOT EXISTS ix_subs_renewal ON subscriptions (renewal_date) WHERE auto_renew = 1;

-- ============ 9. api_keys (5) — rotation edge ============
CREATE TABLE IF NOT EXISTS api_keys (
  key_id          TEXT PRIMARY KEY,                      -- KEY-01...KEY-05
  label           TEXT NOT NULL,                         -- prod-deploy-key | prod-read ...
  key_prefix      TEXT NOT NULL,                         -- first chars only; never store raw secret
  key_hash        TEXT NOT NULL,                         -- sha256 of full key (stub hashes in seed)
  created_at      TEXT NOT NULL,
  last_rotated_at TEXT NOT NULL,
  expires_at      TEXT NOT NULL,
  scope           TEXT NOT NULL,                         -- deploy | read | admin
  is_prod         INTEGER NOT NULL DEFAULT 0,            -- 0/1; SQLite bool
  replaces_key_id TEXT REFERENCES api_keys(key_id) ON DELETE SET NULL,  -- rotation chain (grace window)
  revoked_at      TEXT,
  deleted_at      TEXT DEFAULT NULL,

  CONSTRAINT ck_key_bool    CHECK (is_prod IN (0,1)),
  CONSTRAINT ck_key_scope   CHECK (scope IN ('deploy','read','admin')),
  CONSTRAINT ck_key_rotated CHECK (last_rotated_at >= created_at),
  CONSTRAINT ck_key_revoke  CHECK (revoked_at IS NULL OR revoked_at >= last_rotated_at)
);
-- Seed: KEY-01 prod-deploy last_rotated 2026-02-01 (~295d, expired — hard-blocks provision);
-- KEY-02 prod-read rotated 7d ago (healthy control). Banner: >90d amber, >180d red.
CREATE UNIQUE INDEX IF NOT EXISTS ux_api_keys_prefix
  ON api_keys (key_prefix) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_api_keys_prod ON api_keys (is_prod, last_rotated_at) WHERE revoked_at IS NULL;

-- ============ 10. audit_log (append-only; 2 exemplar rows at seed) ============
CREATE TABLE IF NOT EXISTS audit_log (
  audit_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  occurred_at TEXT NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  actor_id    TEXT REFERENCES employees(employee_id) ON DELETE SET NULL,
  action      TEXT NOT NULL,                             -- candidate.convert | bg.override | key.rotate | ...
  entity      TEXT NOT NULL,                             -- candidate | employee | equipment | ticket | subscription | api_key
  entity_id   TEXT NOT NULL,                             -- CAND-009 | LT-1005 | KEY-01 ...
  reason      TEXT,                                      -- REQUIRED for bg.override + rehire-create-new (app-enforced)
  metadata    TEXT NOT NULL DEFAULT '{}',                -- JSON string
  CONSTRAINT ck_audit_action CHECK (action <> '')
);
CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_log (entity, entity_id);
CREATE INDEX IF NOT EXISTS ix_audit_actor  ON audit_log (occurred_at DESC, actor_id);

-- ============ 11. idempotency_ledger (empty at seed) ============
CREATE TABLE IF NOT EXISTS idempotency_ledger (
  idempotency_key TEXT PRIMARY KEY,
  endpoint        TEXT NOT NULL,                         -- POST /demo/seed | POST /keys/rotate ...
  request_hash    TEXT NOT NULL,                         -- sha256(canonical body); mismatched reuse -> 422
  status_code     INTEGER NOT NULL,
  response_body   TEXT NOT NULL,                         -- JSON string
  created_at      TEXT NOT NULL DEFAULT '2026-11-23T00:00:00Z',
  expires_at      TEXT NOT NULL,                         -- created_at + 24h (sweep job deletes expired)
  CONSTRAINT ck_idem_status CHECK (status_code BETWEEN 200 AND 599)
);
CREATE INDEX IF NOT EXISTS ix_idem_expiry ON idempotency_ledger (expires_at);
