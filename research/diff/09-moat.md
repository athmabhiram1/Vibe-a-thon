# 09 — Cost/Effort Moat: Why This Wins on Economics, Not Just Demo

**Date:** 2026-11-22 · **Type:** diff/ROI memo (judge-facing numbers)
**Inputs:** `research/final/02-hr-onboarding.md` (S1–S20 pricing + penalty + turnover anchors) · `research/final/11-backup-compare.md` (10–14h primary build, drop tripwires) · `research/final/17-effort-plan.md` (solo stack: 2 FastAPIs + SQLite, `--local` fallback, ≤3 servers) · fresh web verification 2026-11-22 (BambooHR / Workday / I-9 / failed-hire / ServiceNow HRSD).
**Claim:** our moat is **build-hours + run-cost + zero-rip-and-replace + offline survivability**. Incumbents charge per-seat rent; we ship a working layer in a weekend that runs for pennies.

---

## 1. Our cost structure (auditable, judge-reproducible)

| Cost line | Our number | How it's achieved | Evidence / where to prove it |
|---|---|---|---|
| **Primary build** | **10–14 h solo, LOW risk** | 1 FastAPI app (files/stages/audit) + seed script (200 apps) + 6–8 tools → 1 composite `advance_file` + approval gate. No GIS, no X12 grammar. | 11-backup-compare §2 scorecard + §5 solo-build plan (T+0–12h). Backup-1 14–18h / Backup-2 12–16h — primary is cheapest AND highest-scoring (24/25). |
| **Stack** | **2 FastAPIs + SQLite + Docker** | HR/onboarding API + dispatch/provisioning API (or single app split in two), SQLite file DB, `docker compose up` = whole system. No managed DB, no SaaS dependency. | 17-effort-plan §§1–3 (FastAPI scaffold 0.5–2 days; compose: fastapi + 2 servers + ollama). |
| **Run cost / onboard** | **<$0.01 target (local); ~$0.02–0.10 hosted fallback** | Local path: Ollama `gemma3:4b` / `llama3.2:3b` on laptop = $0 marginal (electricity only). Hosted path: one onboarding = ~3–6 tool calls × ~1–2k tokens ≈ 10k tokens ≈ $0.01–0.03 on cheap frontier (e.g. $1–3/MTok in/out). SQLite writes = free. No per-seat meter. | 17-effort-plan §2.3 (model sizes: 3–4B ≈ 2GB, laptop-runnable; 7–8B needs 16GB RAM) + §3 D4 Ollama registry. OnboardIQ-style target: sub-cent local inference is the comparable claim — ours is stronger because it's *measured TTFT/accuracy table* (17 §8 DoD), not a marketing line. |
| **HRIS rip-and-replace** | **$0 — none required** | We layer ON TOP: read from existing HRIS/ATS via `ENDPOINT_BASE_URL`, write readiness-record + audit rows back. Scoped tokens, redacted secrets, Cite-Before-Act approval. Customer keeps Workday/BambooHR/Greenhouse. | 11 §4 demo contract (deployed API behind `ENDPOINT_BASE_URL`, scoped tokens, approval gate, visible audit row). 02 §4 buying logic: fund compliance + readiness evidence, not a new system of record. |
| **Offline / venue survival** | **`--local` fallback, $0 extra** | `synapse build --local --discover` → `synapse_auto_server.py` pinned; P0–P4 fallback (video + canned JSON + local-only Docker + hotspot). Kill-network drill = rehearsed line: "switching to local replica, same code path." | 17 §§6–7 (P0–P4, kill-network/wrong-model/quota drills, feature freeze D12). 11 §D-tripwires (backup recording mandatory). |
| **Quota footprint** | **≤3 servers, ≤10 tools** | 2 homeservers/APIs + 1 FastAPI; allowlist `include_operations` to ≤8 tools; `quota-proof.md` (servers=2, lines indexed, MAU screenshot). Competition rule treated as hard cap. | 17 §§2.2, 3 D13 (`quota-proof.md`); 11 D2 tripwire (>10 tools → allowlist + re-`--discover`). |

**Judge sentence:** *"Weekend to build, pennies to run, nothing to rip out, and it demos with the Wi-Fi off."*

---

## 2. Incumbent pricing (verified 2026-11-22)

| Incumbent | Price anchor (verified) | Fine print judges should feel | Source / rating |
|---|---|---|---|
| **BambooHR** | **$10 / $17 / $25 PEPM** (Core/Pro/Elite, >25 emps; flat $250/$425/$650 under 25). Older guides cite ~$6–12 PEPM — directional, now stale-low. | At 500 emps Core = **~$5,000/mo = $60k/yr** before add-ons (payroll, ATS). Onboarding module doesn't fix IT/RBAC handoff (the 10-gap failure surface). | 2026 published pricing (bamboohr.com/pricing; Compono/Pin/Buttoned guides). 02-S19 (L3, older $6–12 est. — cite as "was $6–12, now $10–25"). |
| **Workday HCM** | **Core $25–45 PEPM; full suite $80–120 PEPM.** $50+/PEPM fair for realistic bundle. 1,000 emps core-only ≈ $300–540k/yr; full suite ≈ $1M+/yr. + 6-figure implementation. | Custom quote only; $50–150/worker/yr list per module × modules; escalator + discount-expiry trap; preboarding/RBAC via HRIS→Entra/Okta still needs integration work. | 2026 buyer benchmarks (Vendr/Procr/ERP Research via PeopleOpsClub; Redress Compliance; OutSail $34–42 PEPM at scale). 02-S19 L3 + S10 L5. |
| **ServiceNow HRSD** | **$4–9 PEPM negotiated (Standard vs Pro gap 30–50%) + Now Assist ~+30% + 8% annual uplift default.** Implementation **$60–250k** (basic $60–120k; comprehensive $150–250k); first release 6–12 wks *with accelerators*. | Quote-based, per-employee-in-scope (hire 2,000 → pay 2,000 more at true-up even if they never open the portal). Backend needs specialist developers; heavy customization → upgrade breakage. G2: "challenging setup, training on each aspect." | Redress Compliance HRSD guides (2026, n=29 negotiations, median 18% saving when scope contested); Spacetechnologies impl guide; V-Soft 6–12 wk; G2 HRSD reviews. |
| **Greenhouse / Sapling onboarding** | **~$6–12k/yr entry** (onboarding-only lane). | Covers ATS-side preboarding, not Day-1 IT readiness proof or 30-day RBAC review. | 02-S19 L3. |

**Slide-ready contrast row:**

| | BambooHR (500 emps) | Workday (1,000 emps) | ServiceNow HRSD | **Ours** |
|---|---|---|---|---|
| Annual license | ~$60–150k | ~$300k–1.2M | PEPM × headcount + AI add-on + uplift | **$0 (OSS + local model)** |
| Implementation | weeks + services | 6–12 mo + consultants | $60–250k + 6–12 wks | **10–14 h solo** |
| Marginal onboard | bundled in seat | bundled in seat | bundled in seat | **<$0.01** |
| Rip-and-replace? | you move INTO it | you move INTO it | platform commitment | **no — layers on top** |
| Offline demo? | no | no | no | **yes (`--local`)** |

---

## 3. Pain-side anchors (why anyone pays at all)

| Pain | Number | Source / rating |
|---|---|---|
| Failed hire | **$25k (manager) – $50k (C-level)**; SHRM fully-loaded up to **$240k**; 50–200% of salary by level | Enboarder 2025 (n=1,000 HR leaders) via 02-S6 (L4); SHRM via DevlinPeck/Apollo (L4). |
| Cost-per-hire (re-hire cost) | **~$4,700 avg**; 39-day median vacancy ≈ $19.5k lost output at $500/day planning rate | SHRM Human Capital Benchmarking via 02-S20 (L4); Pin cost-per-hire 2026. |
| Early attrition | **35% back out after accepting** (Gartner); 60.8% say 90-day turnover UP YoY; 20.5% lose up to half of hires in 90 days; +82% retention with structured onboarding | 02-S8/S6/S4 (L4). |
| I-9 paperwork fines | **$288–$2,861 per form** (2026 inflation-adjusted); substantive typically **~$2,500/form**; knowing-hire up to **$28,619/worker**. Example: 1,000 forms × 65% error ≈ **$1.8M exposure**. | USCIS I-9 Central + DHS 2026 schedule via Sheppard/Morgan Lewis/CDFlabor/I-9 Intelligence (L5); 02-S9. ICE Mar-2026: expanded substantive-error list = more "technical" errors now fined as substantive. |
| IT not-ready Day-1 | Day-1 IT **>30 min = pre-start failed**; ~101 apps/company (Okta 2025); 11 steps / 6 owners / 10 gaps failure surface | CheckFlow (02-S13 L3); Okta via Uplift (02-S15); VeroTX/Uplift (02-S18). |
| Automation skepticism (our wedge) | Only **30%** say AI in onboarding helpful; **52%** say too admin-focused; 31% lacked human interaction; **12%** say employer does great onboarding | 02-S18/S7/S3 (L3–L4). → Sell orchestration + readiness evidence + human gates, NOT chatbot. |

---

## 4. ROI slide — numbers judges FEEL (60-second script)

> **Title: "One prevented re-hire pays for 2.5 million onboards."**
>
> | If… | Math | Source |
> |---|---|---|
> | You onboard 500/yr on BambooHR Core | $60k/yr ÷ 500 = **$120/onboard** in seat-rent alone | §2 |
> | You run ours locally | **<$0.01/onboard** → **12,000× cheaper** per onboard | §1 |
> | You prevent ONE $25k failed hire | $25,000 ÷ $0.01 = **2.5M onboards funded** | Enboarder/SHRM §3 |
> | You catch I-9 errors in 100 forms | 100 × $2,500 = **$250k exposure killed** by checklist gating | DHS 2026 §3 |
> | You cut offer→cleared-start 9→2 days (retailer case) | **-22% recruiting cost, acceptance 67%→84%** | Veremark case, 02-S17 (vendor case — say "directional") |
> | You build it | **One weekend (10–14 h), no rip-and-replace, demos offline** | 11 §2/§5 |
>
> **Closer (say it):** *"BambooHR charges you $120 a head to store the problem. Workday charges $600+ to customize around it. ServiceNow charges $250k to configure it. We prevent the $25,000 re-hire for a penny — and the I-9 fine that costs more than our entire build."*

**Honesty guardrails (ITKAN 5/5 bar — say what doesn't work):**
- Vendor-case lifts (acceptance/dropout) are **directional L3**, not guarantees — label them.
- BambooHR $6–12 is the *old* estimate; current published floor is **$10** — don't underquote the incumbent (stronger to overquote them accurately).
- Workday $50+ is bundle-realistic, core-only can be $25–45 — say "core $30s, realistic bundle $50+, full suite $80–120."
- Our <$0.01 is **local-inference marginal** (power + laptop amortized, not $0 absolute) — hosted fallback $0.02–0.10; both still 3–4 orders below seat-rent.

---

## 5. Moat in one paragraph (README / packet reuse)

> Incumbent onboarding economics are **seat-rent + services**: $10–25 PEPM (BambooHR) to $50+/PEPM bundles (Workday) plus $60–250k ServiceNow-style implementations — all before the $25–50k failed hire or the $2,861-per-form I-9 fine they don't prevent. Our build inverts it: **10–14 h solo** on 2 FastAPIs + SQLite, **<$0.01/onboard** local marginal cost, **zero HRIS migration** (layers over existing systems via scoped-token adapters), **offline-capable** (`--local` + canned fallback), inside a **≤3-server / ≤10-tool quota**. The moat isn't a feature — it's that the economics make every incumbent quote look like the problem statement.

---

## Sources (all verified 2026-11-22 unless noted)

- BambooHR pricing: bamboohr.com/pricing ($25 Elite PEPM); Compono/Pin/Buttoned/LilachBullock guides ($10/$17/$25; flat $250/$425/$650 ≤25).
- Workday: PeopleOpsClub/Vendr benchmarks (core $25–45 / full $80–120 PEPM); Redress Compliance 2026; OutSail ($34–42 at scale); ElearningIndustry avg.
- ServiceNow HRSD: Redress Compliance HRSD-for-enterprise + licensing guide 2026 ($4–9 PEPM, 30–50% tier gap, +30% Assist, 8% uplift, 29-negotiation file); Spacetechnologies impl ($60–250k); V-Soft (6–12 wks); G2 HRSD reviews; PeopleManagingPeople review.
- I-9: USCIS I-9 Central Penalties; DHS 2026 schedule via Sheppard / Morgan Lewis (Apr-2026) / CDF Labor / I-9 Intelligence / MarvelHR ($288–$2,861; knowing-hire to $28,619; substantive ~$2,500).
- Failed hire / CPH: Enboarder 2025 via DevlinPeck ($25–50k); SHRM benchmarking (~$4,700 CPH); SHRM fully-loaded to $240k; Gartner via Veremark (35% back-out); Brandon Hall (+82% retention).
- Internal: 02-hr-onboarding.md §§3–5; 11-backup-compare.md §§2,4,5; 17-effort-plan.md §§1–3,8.
