# Quota log — every `synapse info` before/after hosted build

> Append before AND after each hosted build. `--local` builds are never counted — still log them as LOCAL. Freeze hosted if remaining <40% (T8).

## Template

```text
## YYYY-MM-DD HH:MM UTC — <reason e.g. hr-api baseline / it-api --new / discover live-add>
BEFORE: synapse info → servers TODO/10, indexed lines TODO/100k, remaining TODO%
CMD: synapse build <flags> --server-name <name>
AFTER: synapse info → servers TODO/10, indexed lines TODO/100k, remaining TODO%
BUILD: server_id=TODO, tools=TODO (expect 13 baseline / 14 after discover: 11/12 functional-only; 6 /demo/* excluded via --endpoints allowlist), surface_cache=TODO
PROOF: submission/assets/quota-proof/TODO.png
```

## Log

| Date (UTC) | Reason | Before (servers / lines / %) | Command | After (servers / lines / %) | Tools | Proof |
|---|---|---|---|---|---|---|
| 2026-11-24 09:36 | `hr-api baseline` | 0/10 · 0/100.0K · 100% | `synapse build --auto --endpoints "<13-tool allowlist: 11 functional paths + hr_health_check,it_health_check>" --server-name hr-api` | 1/10 · 775/100.0K · 99.2K left | 13/13 | CLI transcript in `research/verify-final/12-synapse-run.md` |
| 2026-11-24 09:37 | `it-api --new` | 1/10 · 775/100.0K · 99.2K left | `synapse build --auto --endpoints "<same 13-tool allowlist>" --server-name it-api --new` | 2/10 · 775/100.0K · 99.2K left | 13/13 | CLI transcript in `research/verify-final/12-synapse-run.md` |
| 2026-11-24 09:39 | `live discover R1 (L1)` | 2/10 · 775/100.0K · 99.2K left | move `live_moment.py` out → `synapse build --auto --endpoints "<13-tool allowlist>" --server-name hr-api` (13, 2.36s) → restore → `synapse build --discover --auto --endpoints "<14-tool allowlist: +GET /oncall-coverage>" --server-name hr-api` | 2/10 · 775/100.0K · 99.2K left | 13→14 | CLI transcript in `research/verify-final/12-synapse-run.md` |
| 2026-11-24 09:40 | `live discover R2 (L1)` | 2/10 · 775/100.0K · 99.2K left | same choreography as R1: baseline 13 (4.75s) → discover 14 (4.72s), same server ID | 2/10 · 775/100.0K · 99.2K left | 13→14 | CLI transcript in `research/verify-final/12-synapse-run.md` |
| 2026-11-24 09:41 | `live discover R3 (L1)` | 2/10 · 775/100.0K · 99.2K left | same choreography as R1: baseline 13 (4.83s) → discover 14 (4.82s), same server ID | 2/10 · 775/100.0K · 99.2K left | 13→14 | CLI transcript in `research/verify-final/12-synapse-run.md` |
| 2026-11-25 14:48 | `28-discover rehearsal check (NO BUILD — hr-api already 14, H5 live)` | 2/10 · 775/100.0K · 99.2K left | no `synapse build` executed (guard "ONLY if baseline is 13" false); read-only `synapse info` + Inspector `tools/list` only | 2/10 · 775/100.0K · 99.2K left | 14 (unchanged) | `research/verify-final/28-discover.md` |

## Quota rules (free tier)

- 10 MCP servers + 100,000 indexed lines/account. Unchanged rebuild costs nothing (`surface_cache.json` reused until `--discover`). `synapse info` is the source of truth; `LIMITS.md` numbers must match this log.
