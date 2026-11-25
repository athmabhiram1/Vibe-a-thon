# LIMITS — Quota-proof (cost = ₹0)

## Free-tier budget (cost = ₹0)

| Service | Tier | Cap used | We use | Proof |
|---|---|---|---|---|
| Synapse hosted | Free: 10 MCP servers, 100k indexed lines/account | 2/10 servers, 775/100K lines (`synapse info` 2026-11-24; see `../evidence/quota-log.md`) | 2 servers (hr-api, it-api) | `../evidence/quota-log.md` + `assets/quota-proof/synapse-info.txt` (text capture 2026-11-24, key redacted) |
| Hosting (judged runs) | localhost + ngrok free (no paid cloud) | localhost measured (boot 1.3s/svc, BENCHMARKS.md); ngrok tunnels [UNMEASURED — paste `ngrok` session count at freeze] | 2×uvicorn :8001/:8002 | `assets/quota-proof/ngrok.png` (user-owned freeze-day shot; pending) |
| Cloud backup | Fly 2s-wake / Render Free | 0 hrs used (nothing deployed during build; backup only) | Backup only; Render $7 rejected | `assets/quota-proof/` ([screenshot pending — only if backup is deployed]) |
| AI (judged) | Hosted frontier default | [UNMEASURED — paste request count + daily quota from provider dashboard at freeze] | Cached; TTFT tripwire T4 | dashboard screenshot (user-owned freeze-day shot; pending) |
| AI (local) | Ollama qwen3:4b-8k + qwen2.5-coder:7b-8k | `qwen2.5-coder:7b` pulled 4.7 GB (`ollama list` 2026-11-24); nothing resident at capture (`ollama ps` empty); earlier `qwen3:8b` 6.7 GB CPU | P2 only | `assets/quota-proof/ollama-ps.txt` + `ollama-ps.png` (text-capture rendering) |
| DB/Auth | SQLite WAL file (no server) | `seed/demo.db` 200KB shared by both services (`HR_DB_PATH` default), counts 20/20/20/20/8/6/5 | 20/20/20/20/8/6/5 | `seed/validate.py` output |

Billing target: ₹0 — screenshots in `assets/quota-proof/` must show ₹0 / $0.

## Guards

- Cache (TTL [UNMEASURED — no `CACHE_TTL` constant found in code; confirm debounce/cache window and paste seconds here]) + debounce + server-side rate limit (demo seed 6/min/IP; `x-demo-confirm: yes` + `ALLOW_DEMO_SEED=true`) + fallback to cached-JSON when quota hit.
- No keys in client; `.env.example` documents every var (`HR_BASE_URL`, `IT_BASE_URL`, `ENDPOINT_BASE_URL`, `DATABASE_URL`, `SYNAPSE_SERVER_ID`, `MCP_REV`, `OLLAMA_HOST`, `ALLOW_DEMO_SEED`).
- Headers sent as `${ENV:VAR}` placeholders; secrets redacted at every sink; hash over redacted form.
- Rebuilds reuse `surface_cache.json` until `--discover`; unchanged rebuild costs nothing; `--local` builds never counted.
- Eval budget: live path ≤500ms; mock ~11ms.

## Quota tripwire

- T8 quota <40% → freeze hosted builds, switch to `--local` + cached-JSON. Log every `synapse info` before/after hosted build in `../evidence/quota-log.md`.

## If quota hits mid-demo → offline GIF + cached response path (see video 0:55)

P0 `demo/golden.mp4` (<3min, USB copy) + P3 cached receipts. Script line: *"same code path, local replica."*
