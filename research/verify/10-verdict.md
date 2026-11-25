# 10 — All-Rounder Verdict: Is This Stack the Best for Solo Track 3 Win?

**Date:** 2026-11-22 | **Question:** FastAPI + FastMCP 4.1.7 + Postgres/SQLite + SQLAlchemy + Render + Ollama pins + Docker + pytest/eval + Cursor — best combo for solo Track 3 (HR+IT onboard copilot) win, or is there a better combo?
**Sources:** `research/build/01-49` + `research/final/01-20` (esp. 08,12,16,17,20) + `research/01-04` + websearch 22 Nov 2026 (FastMCP 4.2.4, Render pricing/free docs, LocalAgentBench + Ollama tool-gating papers).
**Short answer:** Stack direction is right; 7/9 layers KEEP as-is. 2 layers need SWITCH before D1 — Ollama pins (demo-killer) and FastMCP pin (11 days stale + security fix). No framework swap beats this combo for Synapse + solo + 15-day budget.

## 1. Layer Scores (KEEP/SWITCH)

| # | Layer (current) | Verdict | One-line why + exact pin change if SWITCH |
|---|---|---|---|
| 1 | FastAPI (template `backend/` + explicit `operation_id`, `fastapi==0.165.0`) | **KEEP** | Only Synapse-safe scaffold: literal `operation_id` on every op, no dynamic routers; `fastapi-users`/`add_pagination` correctly rejected in build/06. |
| 2 | FastMCP `4.1.7` | **SWITCH** | Stale 12 days; latest `4.2.4` (21 Nov 2026) fixes OAuth-proxy race GHSA-78c8-3jhx-5mg7 + mounted-tool listing break — both bite Track 3 federation. → `fastmcp==4.2.4` (keep `mcp==2.3.0`, `httpx>=0.28`, `uvicorn>=0.30`); drop any `fastapi-mcp==0.4.0` use. |
| 3 | Postgres (cloud) + SQLite (local fallback) | **KEEP** | Correct split: Postgres on Render for live URL, SQLite in compose for airplane-mode P2. Caveat: Render Free Postgres expires 30 days, ephemeral FS loses local SQLite on redeploy — back up via `pg_dump` + volume tar (build/11 §5). |
| 4 | SQLAlchemy (`2.0.44` + SQLModel `0.0.27` + `asyncpg`, Alembic `1.17.1`) | **KEEP** | Current, Synapse-clean (`FilterDepends` only, no magic); manual `skip/limit` beats `fastapi-pagination` for detector stability. |
| 5 | Render (Starter $7 live URL + local compose mirror) | **KEEP** | Verified 25 Oct 2026: Free sleeps 15 min → ~60s wake (demo-killer); Starter 0.5 CPU/512 MB $7 never sleeps. Solo default Render + compose mirror is cheapest predictable URL; add Railway only if worker/Redis needed. |
| 6 | Ollama pins (`gemma3:4b` chat + `qwen2.5-coder:7b` codegen + `llama3.2:3b` fallback, `num_ctx 8192`) | **SWITCH — P0** | Both defaults fail MCP tool-calling: `gemma3:4b` = no native tool support (HTTP 400 "does not support tools", 0% bench); `qwen2.5-coder:7b` = 26% agent score, emits text JSON not `tool_calls`. → Primary `qwen3:4b` (97.7 top-8GB agent score) + fallback `llama3.2:3b` (native `tool_calls`, 52%) + codegen `qwen2.5:7b` (66%, real tools) or `qwen3-coder:30B` if VRAM allows. Keep `num_ctx 8192`, `OLLAMA_NO_CLOUD=1`, `OLLAMA_KEEP_ALIVE=30m`. |
| 7 | Docker (`python:3.12-slim`, `postgres:16-alpine`, `redis:7-alpine`, `ollama:0.6.8`, compose 8001/8002) | **KEEP (align pins)** | Reproducible + hot-spare path is solo-optimal. One fix: `services/api*/requirements.txt` still says `fastapi==0.115.*` — bump to `fastapi==0.165.0` to match build/06 or Synapse surface drifts between local/cloud. |
| 8 | pytest/eval (`pytest8 + httpx ASGI + respx + pytest-benchmark + cov≥80%` + golden-JSON every commit / `deepeval` nightly) | **KEEP** | Correct anti-hallucination ladder: deterministic golden asserts gate merges, LLM-judge never gates commits; `eval/run.py → scorecard.csv` (≥95%/≥80%) is exactly what judges ask for. |
| 9 | Cursor (`.cursor/mcp.json` + Inspector CLI + Claude Desktop) | **KEEP** | Synapse lists Cursor as first-class host; `MCP_REV` bump + Inspector `tools/list` as ground truth correctly solves stale-cache failure mode. |

No better combo found: Hono/Express loses Python-Custom parity (Custom reads Python only); Next.js full-stack adds JS-scan blind spot; Railway/HF add cost/complexity without killing cold-start better than $7 Render; `fastapi-mcp` is 15-month-stale and crashes on `mcp` 2.x.

## 2. Top-3 Switch Candidates by Expected Value

1. **Ollama pins → `qwen3:4b` / `llama3.2:3b`** (EV highest — saves demo). Evidence: LocalAgentBench Oct 2026 (Q4_K_M, Ollama, RTX 3090): `qwen3:4b` 97.7 / `qwen2.5:7b` 66.1 / `llama3.2:3b` 52.1 / `qwen2.5-coder:7b` 26.0 / `gemma3:4b` n/a (no native tools); arxiv 2609.26693 + betterclaw Sep 2026 confirm Ollama gates `tools=` per-model — `gemma3` rejected 400, `qwen-coder` text-only. Cost: 1 evening (`pull + create -8k + warm + 20-trial emit_tool_plan`); tripwire T5 re-tuned to new primary.
2. **FastMCP `4.1.7` → `4.2.4`** (EV high — saves federation + security Q&A). Evidence: PyPI/deps.dev 21 Nov 2026 `4.2.4` latest, 60 releases/12 mo, fixes proxy-token double-redeem + transform-hides-all-tools bug. Cost: `uv pip install -U fastmcp==4.2.4`, re-run `mount(namespace=...)` + `AuditMiddleware` smoke (build/08 §4-5).
3. **Docker reqs `fastapi==0.115.*` → `==0.165.0`** (EV medium — prevents local/cloud OpenAPI drift that breaks `--discover` T2 tripwire). Cost: 2-line edit + rebuild; verify `operationId` 10/10 both ports.

## 3. Go / No-Go for plan.md As-Is

**Conditional GO — with 2 pre-D1 patches (≤2h total), else NO-GO.**

- Patch A (30 min): bump `fastmcp==4.1.7` → `==4.2.4` everywhere (master plan §file-map, §G-gates, build/08 §6).
- Patch B (90 min): swap Ollama table (build/47 + master plan D9/Modelfile/file-map) to `qwen3:4b-8k` primary, `llama3.2:3b-8k` fallback, `qwen2.5:7b-8k` codegen; re-run T5 (20 trials, success ≥60%) before D6 agent loop.
- Patch C (5 min): align Docker `requirements.txt` to `fastapi==0.165.0`.

Without Patch B the live Q1-Q3 chain risks 0%-tool silent failure on stage — the single biggest solo-track-3 loss mode. With A+B+C, plan.md (15-day gates G1-G6 + tripwires T1-T8 + D8 pivot + P0-P4 fallback) is the best solo bet: Synapse-front-and-center, governed live-data story, reproducible evidence folder, and T2 hedge intact.

*Next: apply 3 patches → execute D1 P0 gate (`synapse info`, `--local` matrix, team cap, `--discover` timing).*
