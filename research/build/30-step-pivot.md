# Track 2 Pivot Plan — 30 Steps (<1 Week)

**Goal:** If Track 1 (federated t3-attempt) goes ungreen, pivot to safety-tool narrative in <1 week without losing evals, demos, or judging credit.
**Trigger conditions (any one fires pivot):** federation ungreen | gRPC blocked | `emit_tool_plan` fail | TTFT >20s.
**Non-goals:** No new infra, no new vendor, no re-recording full demo unless needed.

## Phase 0 — Freeze & Decide (Day 1, ~3h)

1. **Freeze `t3-attempt` branch** — `git tag track1-freeze-$(date +%F) && git push origin --tags`; create `pivot/track2-safety` from freeze point.
2. **Record trigger + timestamp** in `research/build/30-step-pivot.md` log table (which condition, evidence link, decider).
3. **Lock scope doc** — add `PIVOT: ACTIVE` banner to README top; link this file.
4. **Notify judges framing** — one-line pivot note: "From federated planner → local safety auditor using same eval harness."
5. **Snapshot evals** — copy last green `evals/*.json` to `evals/track1-snapshot/`.

## Phase 1 — Retitle to Safety Tool (Day 1–2)

6. **Retitle README** — `Federated Tool Planner` → `Tool-Call Safety Auditor`; rewrite lines 1–20: problem = unsafe tool calls, solution = local audit + deny/allow.
7. **Rewrite demo script intro** (30s) — "We froze federation; this audits the same tool plans locally."
8. **Update `02-api-design.md` header** — mark federated endpoints `DEFERRED`, promote `sunset_vendor` / `adjudicate_claim` fallback specs to `REQUIRED`.
9. **Write `THREAT-MODEL.md`** (new file) — assets, trust boundaries, attacker capabilities, 5 abuse cases: prompt injection via vendor memo, over-claim adjudication, PII leak in tool args, replayed plan, rogue vendor endpoint.
10. **Map mitigations** — for each threat: control (schema pin, allowlist, redaction, nonce/TTL, deny-by-default) + test ID.
11. **Keep `emit_tool_plan`** — reframe as untrusted input producer; auditor is system-under-test, not the planner.

## Phase 2 — Evals Rerun 3× (Day 2–4)

12. **Pin eval harness** — freeze `evals/run.py` + seed list; document commit hash in README.
13. **Rerun baseline 3×** — `for i in 1 2 3; do python evals/run.py --seed $i --out evals/pivot-run-$i.json; done`.
14. **Compute variance** — pass rate, TTFT p50/p95, deny-precision/recall; fail pivot if flaky >10pp spread (investigate, don't hide).
15. **Add safety-specific assertions** — injection blocked, PII redacted, over-claim denied, replay rejected, unknown-vendor denied.
16. **TTFT guard** — assert local auditor p95 TTFT <20s; if >20s, cut model size / cache policy first, note in log.
17. **Publish eval table** in README — 3-run mean ± std, link raw JSON.

## Phase 3 — Fallback Specs (Day 3–4)

18. **Spec `sunset_vendor` fallback** — inputs (`vendor_id`, `reason`), preconditions (no in-flight claims), effects (deny-list + audit log), error codes (`VENDOR_NOT_FOUND`, `CLAIMS_PENDING`).
19. **Spec `adjudicate_claim` fallback** — local-only rules engine, deterministic fixtures, no gRPC dependency; define allow/deny/escalate schema.
20. **Contract tests** — 5 happy + 5 adversarial cases per fallback; must pass offline (`--no-network`).
21. **gRPC stub** — if gRPC blocked, ship `grpc_stub.py` returning `UNAVAILABLE` → auto-fallback to local adjudication; log fallback count.
22. **Remove federation claims** from slides/README — replace architecture diagram with local-audit diagram.

## Phase 4 — Abuse-Demo Video (Day 4–5)

23. **Script 90s abuse demo** — (a) benign claim allowed, (b) injected memo blocked, (c) over-claim denied; show logs + redaction live.
24. **Record single-take video** — screen + voiceover, <2min, upload unlisted, link in README + submission.
25. **Capture 3 screenshots** — allow / deny / audit-log for judges who won't watch video.
26. **Update threat-model traceability** — each demo timestamp → THREAT-MODEL.md test ID.

## Phase 5 — Ship & Sunset (Day 5–7)

27. **Final README pass** — title, 3-bullet pivot note, eval table, video link, fallback spec links, freeze tag.
28. **Sunset checklist** — archive `t3-attempt` CI, close federation TODOs as `WONTFIX-pivot`, keep branch readable for judges.
29. **Dry-run judging** — 5-min walkthrough: threat → demo → evals → fallbacks; fix any TTFT or setup snag.
30. **Go/no-go gate** — ship Track 2 if: 3× evals green, video live, both fallbacks specced + tested, TTFT p95 <20s. Else cut abuse case #5 and ship.

## Appendix — Trigger Log

| Date | Condition | Evidence | Decider | Action |
|------|-----------|----------|---------|--------|
| _TBD_ | federation ungreen / gRPC blocked / emit_tool_plan fail / TTFT>20s | link | _name_ | froze `t3-attempt`, cut `pivot/track2-safety` |

## Appendix — File Map

- `README.md` — retitled safety tool + eval table + video
- `THREAT-MODEL.md` — new, 5 abuse cases + mitigations
- `research/build/02-api-design.md` — `sunset_vendor` / `adjudicate_claim` fallback specs REQUIRED
- `evals/pivot-run-{1,2,3}.json` — 3× rerun evidence
- `docs/abuse-demo.md` — script + video link + screenshots
