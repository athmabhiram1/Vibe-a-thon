# Quota proof — `synapse info` (screenshot-grade, text-backed)

> Captured live: **2026-11-25 17:35 UTC** (`synapse --version` 0.1.9, read-only, no build run).
> All numbers below are copied **verbatim** from that live `synapse info` output.
> Full transcript: [`quota-proof.txt`](./quota-proof.txt) · terminal render: [`quota-proof.png`](./quota-proof.png)
> (PNG rendered headless via Playwright + Chromium 1255 `executable_path` override — no display used.)

## Account quota (live)

| Metric | Used / Cap | Remaining | Notes |
|---|---|---|---|
| MCP servers | **2 / 10** | 8 remaining | `hr-api`, `it-api` (IDs truncated: `6269969f`, `5fe96a56` — as previously recorded in `submission/LIMITS.md`; live `info` shows counts only) |
| Lines indexed | **775 / 100.0K** | 99.2K remaining | verbatim `775 / 100.0K  (99.2K remaining)` |
| Spend | ₹0 / $0 | free tier | rebuilds reuse `surface_cache.json`; no re-index cost |

## Verbatim source (for judges)

```text
  Synapse Info
  ────────────────────────

  Project

  Status          Initialized
  Version         1.0.0
  Created         2026-11-24 13:57
  API key         (not set) (project)
  Analyzed        Not yet (run synapse analyze)

  Account Quota

  MCP servers     2 / 10 used  (8 remaining)
  Lines indexed   775 / 100.0K  (99.2K remaining)
```

- Matches `evidence/quota-log.md` last AFTER row (`2/10 · 775/100.0K · 99.2K left`) and `submission/LIMITS.md`.
- Freeze tripwire T8 intact: 80% of server slots and >99% of line budget remaining — hosted builds stay unfrozen.
- Key redaction: live output already shows `API key (not set) (project)`; nothing secret was captured.
