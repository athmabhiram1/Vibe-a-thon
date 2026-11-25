# BENCHMARKS

## Setup

Device: `AMD Ryzen 7 250 w/ Radeon 780M, 15.3 GiB RAM` | Network: `[VENUE-UNMEASURED — run a speedtest on freeze day and paste Mbps here]` | Date: `2026-11-24` | Commit: `e41db76df1f62f186265bc3a9713809854bfd637` | Ports: hr 8001, it 8002, ollama 11434

> Freeze (D12) status: every number below was measured 2026-11-24 on this bench unless marked `[VENUE-UNMEASURED — <exact command to fill>]`. Repro: `eval/run.py` + curl loop below (`submission/benchmark/run.js` does not exist — use the PowerShell one-liner in §Repro). CI gate: guarded block ≥90%, FP ≤15% (measured acc 97.5% / block 96.8% / 0% FP @ 11.0ms MOCK).

| Metric | Trial 1 | Trial 2 | Trial 3 | Median | Notes |
|---|---|---|---|---|---|
| Cold start (single-process: 2×uvicorn + SQLite) | 1.3s | 1.3s | 1.3s | 1.3s | Fresh `uvicorn` → `/docs` 200. T1=hr :8011, T2=it :8012, T3=both in parallel (:8013/:8014, both up in 1.3s). `run.bat` adds 5s settle → ~6–7s wall. Target <15s: PASS; T1 tripwire >90s |
| Cold start (compose.opt.yml backup) | N/A | N/A | N/A | N/A | No Docker on bench machine; compose file is opt-in backup profile only. Fill: `docker compose -f compose.opt.yml --profile opt up --build -d` then time to `/docs` 200 |
| p50 API latency (`GET /it/tickets/breaches`) | 9.6ms | 12.4ms | 10.6ms | 10.6ms | 20× `curl.exe` per trial, localhost. Raw T3 (ms): 11.3 10.6 9.5 11.6 10.8 10.5 11.2 9.8 11.0 10.7 10.4 10.1 10.0 11.4 9.9 10.0 12.1 9.5 10.7 10.5 |
| p95 API latency (`GET /it/tickets/breaches`) | 10.5ms | 15.5ms | 11.6ms | 11.6ms | Same 3×20 trials as p50. (Python `urllib` on this box routes via OS proxy ≈2s/req — use `curl.exe`, direct, ~10ms) |
| Seed (`POST /hr|/it/demo/seed`) | 84.6ms | 34.1ms | 30.7ms | 34.1ms | Measured 2026-11-24 via `POST :8021/hr/demo/seed` (`ALLOW_DEMO_SEED=true`, `x-demo-confirm: yes`); response `duration_ms`, counts 20/20/20/20/8/6/5 each trial. T1 first-seed-after-boot, T2–T3 warm. Old note (pre-measure): running servers returned `403 "demo endpoints disabled"` when `ALLOW_DEMO_SEED` unset |
| Reset (`POST /hr|/it/demo/reset`) | 18.7ms | 14.4ms | 13.5ms | 14.4ms | Measured 2026-11-24 via `POST :8021/hr/demo/reset` (same gate/headers as seed); response `duration_ms`, counts 20/20/20/20/8/6/5 each trial, snapshot restore (not full reseed). Adjacent read (kept): `GET /hr/demo/status` 200 in 7.2ms, `/it/demo/status` 200 in 6.9ms, counts 20/20/20/20/8/6/5, `seed_version v14` |
| TTFT (agent first token, hosted frontier) | [VENUE-UNMEASURED] | [VENUE-UNMEASURED] | [VENUE-UNMEASURED] | [VENUE-UNMEASURED] | Fill: run the judged agent path once per trial, record time-to-first-token. T4 tripwire >20s → cached-JSON |
| TTFT (local, `qwen3:8b` substitute) | 0.32s | 0.22s | 0.23s | 0.24s | 5 trials via `POST /api/generate` stream (`think:false`, `num_ctx 8192`, prompt `Reply with exactly: READY`): 0.32 / 0.22 / 0.23 / 0.25 / 0.24s, median 0.24s. T1 cold, T2–T5 warm. NOTE: `qwen3:4b` from `Modelfile.local-8k` is NOT pulled on this box — closest installed model used. Trivial prompt, NOT the agent path. Fill exact-model: `ollama pull qwen3:4b` then re-run |
| AI call latency cached / fresh | [VENUE-UNMEASURED] / [VENUE-UNMEASURED] | — | — | [VENUE-UNMEASURED] / [VENUE-UNMEASURED] | Fill: instrument the agent's model-call wrapper to log wall time on cache-hit vs cache-miss, run 5 demos, paste medians. Proves quota guard works |
| `synapse build --discover` median (5 runs) | [VENUE-UNMEASURED] ×5 | — | — | [VENUE-UNMEASURED] | `synapse` CLI present on bench but hosted builds spend quota — freeze-gated, do NOT run here. Fill at venue: `synapse build --discover --auto --endpoints "<expanded 12 functional + health allowlist>" --server-name hr-api` ×5, paste each + median. T3 tripwire >90s / <3/5 → T3→T2 in 48h |
| Safety eval (guarded vs baseline) | — | — | — | 97.5% acc / 96.8% block / 0% FP @ MOCK p50 11.0ms p95 11.0ms | `python eval/run.py` 2026-11-24: 40 cases (31 BLOCK + 9 ALLOW), guarded acc 97.5% (39/40 strict; M05 WARN-as-designed), baseline 29.0% block / 11.1% FP (weak-by-design single-signal comparator). Latency is MOCK (wall-clock + 11.0ms simulated), NOT measured |
| VRAM (Ollama) | — | — | — | `qwen3:8b` resident 6.7 GB, 100% CPU | `ollama ps` 2026-11-24. Target pair `qwen3:4b + qwen2.5-coder:7b` NOT pulled → `[VENUE-UNMEASURED — ollama pull qwen3:4b && ollama pull qwen2.5-coder:7b && ollama ps]`; swap if OOM → hosted-only |
| Lighthouse Perf / A11y | [VENUE-UNMEASURED] / [VENUE-UNMEASURED] | — | — | [VENUE-UNMEASURED] / [VENUE-UNMEASURED] | `lighthouse` not installed on bench. Fill: `npx -y lighthouse <live-url> --view` (needs public URL + Chrome) |
| Bundle / payload size (`/breaches` JSON) | 3.3KB | — | — | 3.3KB | Measured `curl.exe` download: 3312 bytes, 3 items [T-5001,T-5002,T-5019], HTTP 200. Keep <50KB seeded |

## Repro

```powershell
# p50/p95 breaches latency (20x, direct — do NOT use python urllib on this box: OS proxy inflates to ~2s/req)
$ts = @(); for ($i=1; $i -le 20; $i++) { $w = curl.exe -s http://localhost:8002/it/tickets/breaches -o NUL -w "%{time_total}"; $ts += [double]$w }
python eval/run.py                 # 40 cases, guarded vs baseline, prints scorecard.csv + MOCK p50/p95
python seed/validate.py            # counts 20/20/20/20/8/6/5 + 0 orphans + 3 breached + 4 weekend + LT-1005
curl.exe -s http://localhost:8002/it/tickets/breaches -o NUL -w "bytes:%{size_download} time:%{time_total}s\n"
```

## Targets (tripwires)

- T1 cold start >90s · T2 tools ≠13/14 (≠11/12 functional-only) · T4 TTFT >20s · T5 emit_tool_plan <60% → cached-JSON · T7 scorecard red (block <90% or FP >15%)
