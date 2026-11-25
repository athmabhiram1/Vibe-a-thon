# 10 — FINAL VERDICT: GO-WITH-FIXES (the critic's read)

**Date:** 2026-11-24 · **Synthesizer role:** final verdict, no cheerleading.
**Sources read:** `research/verify/01–09` (all 9 present) + `research/verify/10-verdict.md` (prior, now SUPERSEDED — see §5) + `plan.md` (master, 2026-11-24) + `research/build/49-master-plan.md` (D1–D15) + `research/final/16-judge-score.md` (23/25 FUND) + `research/final/18-contradictions.md` (6 rows).
**Gaps noted:** `research/verify-final/01–09` do NOT exist — this file creates that directory; `verify/01–09` used as proxy (identical lane content). `reconcile/RECONCILE.md` does not exist — `final/18-contradictions.md` used instead. `research/build/50-index.md` not read (MOC only, non-deciding).

## 1. Verdict: GO-WITH-FIXES (not clean GO, not NO-GO)

**GO-WITH-FIXES.** `plan.md` as written is the best solo Track-3 bet available — it has already absorbed 7 of 9 verify-lane switches (SQLite-only, no-Alembic, localhost+ngrok, single-process, downscoped pytest, Inspector-only live, FastMCP-curated-11). Ship it after the 3 fixes in §2 (total ≤2h). Without Fix #1 (model T5 pre-flight) this is a **NO-GO**: the single biggest loss mode is silent 0%-tool failure on stage, and the two model sources in this repo currently contradict each other (§5).

What the judges will actually score, in order: (1) live state-change + receipt behind an approval gate (Write lens, 5/5 — strongest), (2) `synapse build --discover` doing visible work mid-demo (Syn lens, 5/5), (3) attack→refusal→scorecard beat (safety evidence, measured 39/40 guarded vs ~9/40 baseline), (4) audit row. Everything else — Docker elegance, coverage %, cloud URL — is stage dressing. The fix list below is ordered by damage to those four beats.

## 2. Fix list — ordered by judging impact (owner + minutes)

| # | Fix | Why it decides judging | Owner | Minutes |
|---|---|---|---|---|
| F1 | **Resolve model-pin contradiction BEFORE D6: 20-trial `emit_tool_plan` shootout `qwen3:4b` vs `qwen2.5-coder:7b` @ `num_ctx 8192`, keep winner as P2, loser deleted from Modelfile.** `verify/06` (rigorous: VRAM math + 50-prompt harness) keeps `qwen2.5-coder:7b` (80–90%) and kills `llama3.2:3b`; old `verify/10` + `plan.md:43` name `qwen3:4b` primary (97.7 LocalAgentBench). Both agree on `gemma3:4b` = dead (no native tools, HTTP 400) and hosted-frontier-default + cached-JSON P3. Do not carry two "primaries" into D6. T5 gate decides: winner ≥60%, loser out. | solo builder | 90 |
| F2 | **Bump `fastmcp==4.1.7` → `==4.2.4` everywhere** (`requirements.txt`, master-plan file-map, build/08 §6). 4.1.7 is 12+ days stale; 4.2.4 fixes OAuth-proxy double-redeem (GHSA) + mounted-tool listing break — both bite the HR+IT federation story judges will probe. `fastapi-mcp==0.4.0` stays rejected (stale ~16 mo, weak naming, token bloat). Re-run `mount(namespace=…)` + count==11 smoke. | solo builder | 15 |
| F3 | **Align Docker `requirements.txt` `fastapi==0.115.*` → `==0.165.0`** to match build/06 + `verify/01`. Local/cloud OpenAPI drift breaks the T2 tripwire (tools ≠ 10/11) and the `--discover` live beat. | solo builder | 5 |
| F4 | **Enforce single-process golden path in README step 1; move compose to `compose.opt.yml`.** `verify/07` proves compose-cold (image + model pull) blows the 90s T1 tripwire by 5–30 min. Judge rerun card must be exactly: `clone → pip install -r requirements.txt → run.bat / uvicorn …` (3 cmds, <60s). Compose stays as opt-in backup only. | solo builder | 30 |
| F5 | **Add M05 severity note to `eval/` README** (WARN-with-citation-flag ≈ BLOCK-intent; 39/40 = rubric-severity debate, not bypass). `verify/08` flags this as the one predictable judge nitpick on the 96.8% scorecard. | solo builder | 10 |
| F6 | **Freeze ports once: hr 8001 / it 8002 / ollama 11434** (per `plan.md:65`); grep and kill any surviving `:8000`/`:8008` references from build-era docs before D2. Stale-port curl is the cheapest stage failure available. | solo builder | 10 |

Total: ~160 min. D12 freeze rule stands: after D12, fixes stop except narration + cache-bust.

## 3. Top-3 switch candidates (lanes DID find better pieces — all already in plan.md, listed for the record)

1. **Postgres-first → SQLite-only (WAL) golden** (`verify/03`). Dual-dialect tax + `pg_isready` cold boot + 250–400 MB image + venue-Wi-Fi death vs file-copy `VACUUM INTO` reset in ms, offline-proof. Postgres/Neon demoted to opt-in backup. Highest EV switch in the repo.
2. **Render $7 primary → localhost + ngrok primary** (`verify/05`). $7 pays to hide the 15-min-sleep risk instead of removing it; free-PG 30-day expiry is a demo-week time bomb; venue Wi-Fi kills every cloud URL equally. Fly 2s-wake or Render Free stays as backup only.
3. **SQLAlchemy + Alembic → raw `aiosqlite` + Pydantic v2 `response_model` + `schema.sql`** (`verify/04`). Zero migration need at 79 rows; Alembic `env.py` is the #1 LLM-hallucination surface; raw schema ports 1:1 to Drizzle/D1 while ORM models are throwaway. Pydantic itself is KEPT (contract + OpenAPI + codegen).

Honorable mention (no switch needed): FastAPI KEEP (`verify/01` — best static detection + 1-line `operation_id` control), stdlib-eval KEEP + pytest-downscope (`verify/08` — the 40-case CSV is the safety-points artifact), Inspector-Web-UI-only live (`verify/09` — Cursor/Desktop require full restarts that read as broken on stage).

## 4. D-tripwire status (plan.md §7 — all 8, ARMED pre-D1; none firing yet, two red-on-contact)

| Tripwire | Threshold (plan.md) | Status today | Critic's note |
|---|---|---|---|
| T1 cold start | `compose up` cold >90s | 🟡 ARMED — **will go RED if anyone demos compose-cold** | F4 (single-process golden) is the mitigation; drill nightly on hot-spot |
| T2 tool count | tools ≠ 10/11 | 🟡 ARMED | F3 (pin align) + literal `operation_id` on every route; CI asserts count == 11 |
| T3 discover | median >90s or <3/5 → T3→T2 in 48h | 🟡 ARMED — highest structural risk | D8 pivot gate is real; T2 Custom MVP already exists so pivot costs <1 wk |
| T4 TTFT | >20s | 🟡 ARMED | Hosted default covers it; CPU-only 7B reads (~144 s/2K tokens) must never be the live path |
| T5 `emit_tool_plan` | <60% → cached-JSON | 🔴 **RED-ON-CONTACT — the open contradiction** | F1 shootout is mandatory before D6; loser pin deleted, no sentimentality |
| T6 video | >90s / inaudible | 🟡 ARMED | Pre-record P0 by D11 regardless; USB copy staged |
| T7 scorecard | block <90% or FP >15% | 🟢 GREEN (measured 39/40, 0% FP) | F5 note covers M05; freeze `eval/` except guard fixes |
| T8 quota | <40% → freeze hosted | 🟡 ARMED | Log every `synapse info` to `evidence/quota-log.md` from D1; never debug against hosted quota |

No pivot past T+20h (master-plan rule). D-tripwires freeze at D12.

## 5. Why the prior `verify/10-verdict.md` is SUPERSEDED (do not follow it)

The 2026-11-22 `verify/10` scored 7/9 KEEP and recommended KEEP Postgres, KEEP SQLAlchemy, KEEP Render $7, KEEP Cursor-live. All four were overturned by the deeper kill-lanes (`verify/03, 04, 05, 09`) with measured evidence (cold-start timings, image weights, restart-tax citations, hallucination ranking) — and `plan.md` (2026-11-24) correctly adopted the lane versions. Follow `plan.md` + §2 above, not the old file. The only point where the old file is still sharper is the `qwen3:4b` LocalAgentBench citation — which is exactly what F1 re-tests rather than assumes.

## 6. Single next command (D1 P0 gate — unblocks everything downstream)

```bash
synapse info 2>&1 | tee evidence/quota-log.md
```

If hosted quota <8 servers free or gRPC unreachable on venue-like NAT, trigger T8/T3 early and pivot T3→T2 within 48h per master-plan §0. Do not write application code until this line is logged. Immediately after: `ollama pull qwen3:4b && ollama pull qwen2.5-coder:7b` (night-before pull for F1).
