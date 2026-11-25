# 19 — Hypothesis Registry (max 5, falsifiable)

**Date:** 2026-11-22 | **Tracks:** 1–4 | **Status:** registry, pre-build verification queue
**Rule:** max 5 active hypotheses. Each must state a falsification criterion — a specific observation that kills it.

| ID | Hypothesis (short) | Priority | Verification method | Expected outcome | File |
|----|--------------------|----------|---------------------|------------------|------|
| H1 | Onboarding Day-1 blockers span HR+IT join | P0 — must verify before Track 1 scope lock | 5-user concierge test + IT/HR ticket-log sample (n≥20) | ≥3/5 users blocked on join-dependent step (payroll ID, laptop, SSO) not on form UX | [19-H1](19-H1-onboarding-blockers.md) |
| H2 | Approval-gated composite beats many-tools on safety | P0 — decides Track 2 architecture | Adversarial red-team matrix (10 injection cases × 2 architectures) | Composite (planner + approval gate + scoped executor) blocks ≥9/10; many-tools baseline blocks ≤6/10 | [19-H2](19-H2-approval-gated-composite.md) |
| H3 | Live `--discover` moment decides Track 3 demo win | P1 — decides demo script | A/B dry-run judging (n≥6 judges, with vs without live discover) | Live-discover version scores ≥1.5 pts higher (10-pt wow/clarity) and wins ≥5/6 pairwise picks | [19-H3](19-H3-discover-moment.md) |
| H4 | Python FastAPI explicit `operation_id` guarantees detection | P0 — build-breaker for Track 3 agent interop | Scanner probe against 3 FastAPI variants (auto IDs vs explicit `operation_id` vs duplicate IDs) | Explicit-`operation_id` variant = 100% tool detection; auto-ID variant misses ≥1 tool or mangles name | [19-H4](19-H4-operation-id-detection.md) |
| H5 | Consumer-framed onboarding beats infra framing | P1 — decides pitch + landing copy | 2-arm message test (consumer outcome vs infra/platform framing, n≥30) | Consumer arm: ≥20% higher comprehension + ≥15% higher signup intent (Likert + CTA click) | [19-H5](19-H5-consumer-framing.md) |

## Retirement rule
- Any hypothesis falsified by its criterion is marked FALSIFIED within 24h, removed from active count, and replaced only via new `19-Hn` file.
- Unfalsified after verification → PROMOTED to assumption with evidence link.

## Verification queue (order)
1. H1 (blocks Track 1 problem selection) → 2. H4 (blocks Track 3 build) → 3. H2 (blocks Track 2 build) → 4. H3 (blocks demo rehearsal) → 5. H5 (blocks pitch polish).

## Full records
- H1: `19-H1-onboarding-blockers.md`
- H2: `19-H2-approval-gated-composite.md`
- H3: `19-H3-discover-moment.md`
- H4: `19-H4-operation-id-detection.md`
- H5: `19-H5-consumer-framing.md`
