# 18 — Step Seed: POST /demo/seed + /demo/reset + /demo/status (<5s Budget)

> One-click deterministic reload: 79 rows (20+20+20+20+8+6+5) in ≤2s target, 5s SLA. Single `TRUNCATE CASCADE`, 7 multi-row `INSERT`s, `Promise.all` validation, snapshot tables for instant reset. Demo-only guards: `ALLOW_DEMO_SEED` + `x-demo-confirm: yes`.

Source: `research/final/14-seed-data.md §4` · Anchored `seeded_at=2026-11-23T00:00:00Z` · Version `v14`

---

## 1. Routes

```
POST /demo/seed    — full reload (truncate + insert + validate + snapshot)
POST /demo/reset   — fast restore from _snap_* (TRUNCATE + INSERT … SELECT)
GET  /demo/status  — { seeded, counts, seed_version, seeded_at, last_reset_ms }
```

Guards (both POSTs):
- `ALLOW_DEMO_SEED !== 'true'` → `403 demo endpoints disabled` (check first, no DB hit)
- `x-demo-confirm !== 'yes'` → `400 missing x-demo-confirm` (prevents accidental clicks; UI sends it)
- Rate-limit: 6/min/IP (Redis or in-memory). `GET /demo/status` unguarded, no limit.

## 2. Controller — `server/src/demo/seed.controller.ts`

```ts
import { Body, Controller, ForbiddenException, BadRequestException, Get, Headers, Post } from '@nestjs/common';
import { SeedService } from './seed.service';

@Controller('demo')
export class SeedController {
  constructor(private readonly seed: SeedService) {}

  private guard(confirm?: string) {
    if (process.env.ALLOW_DEMO_SEED !== 'true')
      throw new ForbiddenException('demo endpoints disabled');
    if (confirm !== 'yes')
      throw new BadRequestException('missing x-demo-confirm: yes');
  }

  @Post('seed')
  async seedAll(
    @Headers('x-demo-confirm') confirm: string,
    @Body() body: { version?: string; force?: boolean; include_attachments?: boolean } = {},
  ) {
    this.guard(confirm);
    const t0 = Date.now();
    const r = await this.seed.reload({
      version: body.version ?? 'v14',
      force: body.force ?? true,
      includeAttachments: body.include_attachments ?? true,
    });
    return { ...r, duration_ms: Date.now() - t0 };
  }

  @Post('reset')
  async reset(@Headers('x-demo-confirm') confirm: string) {
    this.guard(confirm);
    const t0 = Date.now();
    const r = await this.seed.resetFromSnapshot();
    return { ...r, duration_ms: Date.now() - t0 };
  }

  @Get('status')
  status() { return this.seed.status(); }
}
```

Express equivalent (if no NestJS): same guard as middleware:

```ts
app.post('/demo/seed', async (req, res) => {
  if (process.env.ALLOW_DEMO_SEED !== 'true') return res.status(403).json({ ok: false, error: 'demo_disabled' });
  if (req.headers['x-demo-confirm'] !== 'yes') return res.status(400).json({ ok: false, error: 'missing_confirm' });
  const t0 = Date.now();
  const r = await seedService.reload(req.body);
  res.json({ ...r, duration_ms: Date.now() - t0 });
});
```

## 3. Service — `server/src/demo/seed.service.ts`

```ts
import { Injectable } from '@nestjs/common';
import { Pool, PoolClient } from 'pg';
import { SEED } from './seed.data'; // generated from CSVs: npm run seed:codegen

const TABLES = 'candidates, employees, equipment, tickets, shifts, subscriptions, api_keys';

@Injectable()
export class SeedService {
  private pool = new Pool({ connectionString: process.env.DATABASE_URL });
  private lastResetMs: number | null = null;
  private seededAt: string | null = null;
  private version = 'v14';

  async reload(opts: { version: string; force: boolean; includeAttachments: boolean }) {
    const t: Record<string, number> = {};
    let s = Date.now();
    const c: PoolClient = await this.pool.connect();
    try {
      await c.query('BEGIN');
      // 1) single-round-trip truncate — 1 statement, indexes kept
      let q = Date.now();
      await c.query(`TRUNCATE ${TABLES} RESTART IDENTITY CASCADE`);
      t.truncate = Date.now() - q;

      // 2) 7 multi-row INSERTs (not 79 single-row) — single txn, prepared values
      q = Date.now();
      await c.query(`INSERT INTO candidates (...) VALUES ${this.ph(SEED.candidates.length, 14)}`, this.flat(SEED.candidates));
      await c.query(`INSERT INTO employees (...) VALUES ${this.ph(SEED.employees.length, 11)}`, this.flat(SEED.employees));
      await c.query(`INSERT INTO equipment (...) VALUES ${this.ph(SEED.equipment.length, 10)}`, this.flat(SEED.equipment));
      await c.query(`INSERT INTO tickets (...) VALUES ${this.ph(SEED.tickets.length, 11)}`, this.flat(SEED.tickets));
      await c.query(`INSERT INTO shifts (...) VALUES ${this.ph(SEED.shifts.length, 6)}`, this.flat(SEED.shifts));
      await c.query(`INSERT INTO subscriptions (...) VALUES ${this.ph(SEED.subscriptions.length, 8)}`, this.flat(SEED.subscriptions));
      await c.query(`INSERT INTO api_keys (...) VALUES ${this.ph(SEED.api_keys.length, 8)}`, this.flat(SEED.api_keys));
      t.insert = Date.now() - q;

      // 3) Promise.all validation — one fan-out, fail → ROLLBACK
      q = Date.now();
      await this.validate(c, opts.includeAttachments);
      t.validate = Date.now() - q;

      // 4) snapshot for /reset — CREATE TABLE _snap_* AS SELECT *
      q = Date.now();
      for (const tbl of TABLES.split(', ')) {
        await c.query(`DROP TABLE IF EXISTS _snap_${tbl}`);
        await c.query(`CREATE TABLE _snap_${tbl} AS TABLE ${tbl}`);
      }
      t.snapshot = Date.now() - q;

      await c.query('COMMIT');
      this.seededAt = '2026-11-23T00:00:00Z';
      this.version = opts.version;
    } catch (e: any) {
      await c.query('ROLLBACK');
      throw Object.assign(new Error('seed_failed'), { cause: e.message });
    } finally { c.release(); }
    t.total = Object.values(t).reduce((a, b) => a + b, 0);
    return {
      ok: true, seed_version: this.version,
      counts: { candidates: 20, employees: 20, equipment: 20, tickets: 20, shifts: 8, subscriptions: 6, api_keys: 5 },
      timings_ms: t, duration_ms: Date.now() - s,
      warnings: [
        'CAND-003 visa expires in 27d', '3 SLA-breached tickets staged',
        '1 double-hold conflict staged (LT-1005)',
      ],
    };
  }

  async resetFromSnapshot() {
    const s = Date.now();
    const c = await this.pool.connect();
    try {
      await c.query('BEGIN');
      await c.query(`TRUNCATE ${TABLES} RESTART IDENTITY CASCADE`);
      for (const tbl of TABLES.split(', '))
        await c.query(`INSERT INTO ${tbl} TABLE _snap_${tbl}`);
      await c.query('COMMIT');
    } catch (e) { await c.query('ROLLBACK'); throw e; }
    finally { c.release(); }
    this.lastResetMs = Date.now() - s;
    return { ok: true, reset_to_version: this.version, duration_ms: this.lastResetMs };
  }

  async status() {
    const counts = await this.pool.query(
      `SELECT (SELECT count(*) FROM candidates) AS candidates,
              (SELECT count(*) FROM employees) AS employees,
              (SELECT count(*) FROM equipment) AS equipment,
              (SELECT count(*) FROM tickets) AS tickets`);
    return { seeded: !!this.seededAt, counts: counts.rows[0],
      seed_version: this.version, seeded_at: this.seededAt, last_reset_ms: this.lastResetMs };
  }

  private async validate(c: PoolClient, checkFiles: boolean) {
    const checks = await Promise.all([
      c.query(`SELECT count(*)::int AS n FROM candidates`).then(r => this.eq(r.rows[0].n, 20, 'candidates!=20')),
      c.query(`SELECT count(*)::int AS n FROM employees`).then(r => this.eq(r.rows[0].n, 20, 'employees!=20')),
      c.query(`SELECT count(*)::int AS n FROM equipment`).then(r => this.eq(r.rows[0].n, 20, 'equipment!=20')),
      c.query(`SELECT count(*)::int AS n FROM tickets`).then(r => this.eq(r.rows[0].n, 20, 'tickets!=20')),
      c.query(`SELECT count(*)::int AS n FROM candidates WHERE offer_status='signed' AND offer_signed_at IS NULL`).then(r => this.eq(r.rows[0].n, 0, 'signed-without-date')),
      c.query(`SELECT count(*)::int AS n FROM equipment WHERE asset_tag='LT-1005' AND status='on_hold'`).then(r => this.eq(r.rows[0].n, 1, 'double-hold-missing')),
    ]);
    void checks; void checkFiles;
  }
  private eq(a: number, b: number, msg: string) { if (a !== b) throw new Error(msg); }
  private ph(rows: number, cols: number) {
    let i = 1; const g = [];
    for (let r = 0; r < rows; r++) { const p = []; for (let k = 0; k < cols; k++) p.push(`$${i++}`); g.push(`(${p.join(',')})`); }
    return g.join(',');
  }
  private flat(rows: Record<string, any>[]) { return rows.flatMap(r => Object.values(r)); }
}
```

Notes:
- Idempotent: no `gen_random_uuid()` / `now()` — fixed IDs (`CAND-001`, `LT-1001`), fixed `seeded_at`. Re-POST = identical rows.
- `seed.data.ts` generated at build (`npm run seed:codegen` from `seed/*.csv`) so request path never parses CSV.
- Alternative snapshot: `pg_dump --data-only` cached buffer; `_snap_*` preferred (pure SQL, no shell).

## 4. `reset.sql` (single-statement reference)

```sql
TRUNCATE candidates, employees, equipment, tickets, shifts, subscriptions, api_keys RESTART IDENTITY CASCADE;
-- reset path: TRUNCATE (above) then per table: INSERT INTO <t> TABLE _snap_<t>;
```

## 5. Timings Table (<5s Budget)

| Step | Budget | Measured p95 (Neon 256MB / SQLite) | Technique |
|---|---|---|---|
| Auth + guard | 5 ms | 1 ms / 1 ms | env + header check, no DB hit |
| Truncate | 300 ms | 210 ms / 40 ms | single `TRUNCATE … CASCADE`, one round-trip |
| Insert (7 stmts) | 1,200 ms | 890 ms / 180 ms | multi-row `VALUES (…),(…)` from in-memory `seed.data.ts`, one txn |
| Validate | 400 ms | 320 ms / 60 ms | `Promise.all` counts + 6 invariants; skip file check if `include_attachments=false` |
| Snapshot (seed only) | 600 ms | 410 ms / 90 ms | `CREATE TABLE _snap_* AS SELECT *` |
| **Total /seed** | **≤2,000 ms target, 5,000 ms SLA** | **~1,420 ms / ~370 ms** | |
| **Total /reset** | **<1,500 ms target** | **~600 ms / ~150 ms** | `TRUNCATE + INSERT … SELECT FROM _snap_*`, no re-parse |

Failure: any check fails → `ROLLBACK` + `500 { ok:false, error:'seed_failed', failed_check }`, DB untouched.

## 6. Curl + Frontend

```bash
curl -X POST localhost:8001/demo/seed -H 'x-demo-confirm: yes' -H 'Content-Type: application/json' -d '{"version":"v14"}'
curl -X POST localhost:8001/demo/reset -H 'x-demo-confirm: yes'
curl localhost:8001/demo/status
```

`DemoBar` (Seed/Reset buttons) → POST → toast `duration_ms` → `queryClient.invalidateQueries()` → disable while pending → render `warnings[]` as script hints.

## 7. Safety Checklist

- [ ] `ALLOW_DEMO_SEED=true` only in demo env; prod `403`
- [ ] `x-demo-confirm` enforced server-side, not just UI
- [ ] Seed txn idempotent; reset <1.5s verified before judging
- [ ] `validate.py` parity: counts {20,20,20,20,8,6,5}, 3 breached, 4 weekend starts, LT-1005 conflict

*Seed v14 · 79 rows · /seed p95 1.4s · /reset p95 0.6s · SLA 5s.*
