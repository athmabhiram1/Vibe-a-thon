# 50 — Index (MOC of All 50 Build Docs)

**Date:** 2026-11-22 | **Status:** 16 present (01-05, 08-12, 15, 18-20, 49-50) · 34 planned [PLANNED] with 1-line briefs so nothing is lost.
**How to use:** start at 49-master-plan, then follow dependency order (§3). Present docs are authoritative; [PLANNED] titles are reserved — do not reuse numbers.

## A. Present docs (read these)

| # | File | What it gives you |
|---|---|---|
| 01 | 01-architecture.md | Topology (2 FastAPI :8001/:8002 + Synapse hr-api/it-api + safety + P0-P4), frozen ports, compose, env table |
| 02 | 02-api-design.md | 11 detection-safe endpoints (`hr_*/it_*`), Pydantic models, router stubs, `--discover` runbook |
| 03 | 03-db-schema.md | Postgres-first/SQLite DDL, 79-row counts, FK order, partial uniques, trap traceability, validation bundle |
| 04 | 04-auth.md | JWT verifier + `read/write/admin:all`, per-tool middleware, `${ENV}` redaction, DEMO_MODE guards, 8-case matrix |
| 05 | 05-deploy.md | Render/Railway/HF/local, cold-start mitigation, `up.sh`, hotspot drill, verify matrix |
| 08 | 08-lib-mcp.md | FastMCP 4.1.7 primary vs SDK fallback vs fastapi_mcp reject; curated tools, AuditMiddleware, mount namespaces, pins |
| 09 | 09-lib-models.md | Pydantic v2 + SQLAlchemy 2.0 + Alembic + asyncpg/psycopg/aiosqlite; models, schemas, idempotency, WAL |
| 10a | 10-lib-models.md | Local-model pick `qwen2.5-coder:7b` + Modelfile 8192 + VRAM table + `ollama ps` checks |
| 10b | 11-lib-docker.md | 2×API + Postgres + Redis + Ollama compose, Dockerfiles, hot-spare clone |
| 11 | 12-lib-testing.md | pytest + httpx ASGI + respx + benchmark + coverage ≥80; golden JSON + deepeval; `eval/run.py` + scorecard |
| 12 | 15-lib-packet.md | `submission/` packet: README/ARCH/BENCH/LIMITS/PITCH/captions/deck/benchmark + night-before checklist |
| 13 | 18-step-seed.md | `/demo/seed|reset|status` controller+service, timings (<5s SLA), curl + DemoBar |
| 14 | 19-step-synapse.md | CLI 0.1.9 runbook: init → hr-api → it-api --new → info → verify; 5 error fixes; no `list-tools` |
| 15 | 20-step-clients.md | Claude Desktop (restart) + Cursor (hot-reload + MCP_REV) + Inspector CLI; live-discover choreography |
| 49 | 49-master-plan.md | 15-day plan, dependency graph, file map, 8 tripwires, 6 gates (this sprint's driver) |
| 50 | 50-index.md | This MOC |

Numbers 06-07 reserved for lib-auth-details + lib-seed-helpers; 13-14 for lib-video + lib-deck; 16-17 for packet-benchmarks + packet-limits; 21-48 for step-guides (see §B).

## B. Planned docs 21-48 (reserved titles + 1-line briefs)

| # | Reserved title | Brief ([SYNTH] from final/ + present builds) |
|---|---|---|
| 21 | step-agent-loop | Agent `model→tool→exec→result→response` <10s; Q1-Q3 prompts; TTFT log |
| 22 | step-evals-harness | 30-50 cases taxonomy; `eval/run.py` usage; ≥95%/≥80% gates |
| 23 | step-redteam-matrix | H2 10 injection cases × 2 arch; denial receipts; transcripts |
| 24 | step-fallback-p0-video | 60s timestamped video spec; 3 canned JSON; USB staging |
| 25 | step-fallback-p1-cached | `--mode=live\|cached\|local`; narration line; flag impl |
| 26 | step-fallback-p2-local | `synapse_auto_server.py` + FastMCP 5-8 tools + `ollama ps` + TELEMETRY=0 |
| 27 | step-fallback-p3-hotspot | Hotspot SSID, spare laptop clone, offline drill <90s |
| 28 | step-rehearsal-script | 10 dry-run log sheet; 3 Q&A (centrality/privacy/safety); stage cues |
| 29 | packet-readme | README template filled (badges, 2 links, 5-cmd run) |
| 30 | packet-architecture | Mermaid T3 diagram + PNG fallback + 5-line flow + 2-line fallback |
| 31 | packet-benchmarks | Cold-start, p50/p95, TTFT, VRAM table + `benchmark/run.js` repro |
| 32 | packet-limits | ₹0 budget table, quota screenshot, guards, mid-demo quota line |
| 33 | packet-pitch-video | 75s script + shot list + OBS/CapCut settings + captions workflow |
| 34 | packet-deck | 8-slide outline → Canva/Slides; 24pt+, QR, PDF backup |
| 35 | ops-quota-log | `evidence/quota-log.md` format; every hosted build logged |
| 36 | ops-env-secrets | `.env.example` hygiene; `${ENV}` check in CI; no real tokens |
| 37 | ops-prewarm-drill | `scripts/up.sh cloud/local`; T-60min ritual; cold-window choreography |
| 38 | ops-pivot-runbook | T3→T2 <1wk checklist; freeze branch; retitle; 3× eval rerun |
| 39 | ref-operation-ids | Canonical 11 IDs table; collision rule; never-rename policy |
| 40 | ref-join-keys | `assignee_email↔email`, `created_at↔shift_calendar`, breach formula |
| 41 | ref-demo-questions | Q1-Q3 verbatim + expected tool chains + fallback answers |
| 42 | ref-error-fixes | Union of build/19 + cache-bust + 403/401 + hold_conflict 409 |
| 43 | ref-glossary | hr-api/it-api, `--discover`, H5, P0-P4, Cite-Before-Act, idempotency |
| 44 | track2-hedge-mvp | T2 `safety_check_server.py` + evals + THREAT-MODEL.md + abuse video |
| 45 | track1-emergency | <48h: 1 server + canned discovery only |
| 46 | appendix-wk1-proof | `/docs` screenshots, federation-proof.png, `docs/WK1-DEMO.md` |
| 47 | appendix-scorecard | Final `scorecard.csv` + 3 transcripts + variance note |
| 48 | appendix-submission | Portal checklist: video, write-up, server IDs, comparison table, clips |

## C. Dependency order (read/build sequence)

```
01 arch → 02 api + 03 db → 18 seed → 05 deploy/11 docker → 04 auth/08 mcp/09 models/10 models
→ 19 synapse → 20 clients → 21 agent → 22-23 evals → 24-27 fallback → 12 testing(gates)
→ 15 packet + 29-34 packet/* → 28 rehearsal → 35-38 ops → 39-43 refs → 44-45 hedges → 46-48 appendix
Driver: 49-master-plan. Map: §A→§B→§C.
```

## D. Coverage note

Build docs 06-07/13-14/16-17 were never written; their content lives in final/ (06≈final/13, 07≈final/14, 13≈final/12-demo-risk, 14≈final/16-judge-score, 16≈final/11-privacy, 17≈final/17-effort) and is folded into 49 §§0-6. No silent drift: where 17-effort WK1 ports (8008/8009/8000) conflict with frozen 8001/8002, 01-architecture §2 wins (federation-spike superseded).
