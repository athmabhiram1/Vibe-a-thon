# Omnilearn Phase 1 — Academic Angle: MCP Tool Design + Agent Reliability for Track 3 Onboarding Copilot (HR + IT Desk via Synapse Auto)

**Track:** 3 — Onboarding Copilot (HR + IT service desk, tool-composed via Synapse Auto)
**Question:** How should MCP tool surface be designed (sprawl vs. composition) and how should multi-step agent reliability + confirmation gates be engineered for an HR/IT onboarding copilot?
**Method:** Systematic web review — 10 pre-registered queries (Boolean, `site:`, quotes, 2 contradiction-seeking). No URLs invented; all URLs verbatim from search/fetch results.
**Date:** 2026-11-22 (UTC)
**Evidence levels:** L1 = peer-reviewed / arXiv pre-print with empirical evaluation; L2 = official protocol spec or vendor engineering from protocol owner / cloud provider guidance; L3 = enterprise deployment report, benchmark study, or structured benchmark analysis; L4 = practitioner engineering blog with measurements or detailed design rationale; L5 = community discussion / secondary explainer.

---

## 1. Search strategy table (query verbatim + N retrieved → screened → kept)

| # | Query (verbatim) | Type | Retrieved | Screened (title/abstract) | Kept (cited) |
|---|------------------|------|-----------|---------------------------|--------------|
| Q1 | `MCP "tool sprawl" composition Model Context Protocol design` | Boolean + quotes (sprawl vs composition) | 10 | 10 | 4 |
| Q2 | `MCP server tool design best practices composition granularity` | Boolean (composition/granularity) | 10 | 10 | 4 |
| Q3 | `site:anthropic.com MCP tool design composition` | `site:` | 10 | 10 | 3 |
| Q4 | `"Model Context Protocol" tool composition design patterns` | quotes | 10 | 10 | 3 |
| Q5 | `AI agent multi-step reliability failure rates benchmark tool use` | Boolean (reliability) | 10 | 10 | 4 |
| Q6 | `site:arxiv.org LLM agent multi-step reliability tool use benchmark` | `site:` (arxiv) | 10 | 10 | 3 |
| Q7 | `"confirmation gate" OR "human-in-the-loop" AI agent reliability approval tool calls` | Boolean OR + quotes (confirmation gates) | 10 | 10 | 3 |
| Q8 | `MCP agent failures limitations negative results tool selection accuracy drops` | **Contradiction-seeking #1** (failures/negative results) | 10 | 10 | 4 |
| Q9 | `AI agents "failure modes" tool use "negative results" multi-step tasks fail` | **Contradiction-seeking #2** (failure modes/negative results) | 10 | 10 | 2 |
| Q10 | `"human in the loop" approval gates agent tool use best practices confirmation prompt` | quotes (approval gates) | 10 | 10 | 3 |
| **Total** | 10 queries (meets ≥8; includes Boolean, 2× `site:`, 4× quotes, 2× contradiction-seeking) | — | **~100** | **~100** | **~20 unique sources** |

**Screening rule:** keep iff (a) directly addresses MCP tool granularity/composition, multi-step tool-use reliability measurement, or approval/confirmation design; (b) URL traceable to search/fetch output; (c) prefer primary (spec, vendor eng, paper) over aggregator. Exclude marketing pages without design content.

---

## 2. Source table (rated L1–L5)

### A. MCP tool sprawl vs. composition (core design question)

| ID | Source (URL verbatim from retrieval) | Claim / evidence relevant to Track 3 | Level |
|----|--------------------------------------|--------------------------------------|-------|
| S1 | https://www.anthropic.com/engineering/writing-tools-for-agents | Build few thoughtful workflow tools, not endpoint wrappers: `schedule_event` not `list_users`+`list_events`+`create_event`; `search_contacts` not `list_contacts`; consolidate multi-call chains under the hood; namespace (`asana_search` vs `jira_search`); optimize token efficiency (pagination/filtering/truncation, response_format concise/detailed). Evaluation-driven iteration with held-out tasks. | **L2** — protocol owner engineering guidance |
| S2 | https://docs.aws.amazon.com/prescriptive-guidance/latest/mcp-strategies/mcp-tool-strategy-scope.html | Granular (tool-per-API) vs. coarse-grained (workflow) scoping. Rules: map tools to complete user interactions; bundle if workflow needs ≥3 calls; ≤8 parameters per tool (bundle priority over param count); separate read vs. write; sensible defaults; prefer deterministic execution. Too few tools → hallucination; too many → confusion. | **L2** — cloud provider prescriptive guidance |
| S3 | https://docs.aws.amazon.com/prescriptive-guidance/latest/mcp-strategies/introduction.html | Synthesis: structured wrappers ~3× more accurate on DB tasks than direct API access (cites "Middleware for LLMs" paper); scoping + clear schemas + workflow scoping + filtering reduces context/latency. Maps to Well-Architected (security, reliability, cost). | **L2** |
| S4 | https://modelcontextprotocol.io/specification/2026-07-28/server/tools | Normative: tools are model-controlled; human-in-loop SHOULD always exist with deny ability; clients SHOULD show tools, visual indicators, confirmation prompts; servers MUST validate inputs, access control, rate-limit; annotations untrusted. Supports readOnlyHint/destructive annotations, input/outputSchema, paginated tools/list. | **L2** — official spec |
| S5 | https://www.anthropic.com/engineering/advanced-tool-use (also http://anthropic.com/engineering/advanced-tool-use) | Tool Search Tool: 58 tools ≈55K tokens pre-conversation; 50+ MCP tools ≈72K tokens; deferred loading (`defer_loading:true`) → ~500-token search tool + 3–5 tools on demand (~3K), ~85% token saving, 95% context preserved. Opus 4 49%→74%, Opus 4.5 79.5%→88.1% on MCP evals. Most common failures: wrong tool selection + incorrect params on similar names. Use when >10 tools or >10K tokens of definitions. | **L2** |
| S6 | https://anthropic.com/engineering/code-execution-with-mcp | Two cost drivers: (1) tool definitions overload context (thousands of tools → 100K+ tokens), (2) intermediate results consume context. Fix: programmatic tool calling / code mode — model writes code that calls MCP tools, only final result returns. Requires sandboxing/monitoring. | **L2** |
| S7 | https://modelcontextprotocol.io/docs/develop/clients/client-best-practices | Client patterns for 100s–1000s tools: progressive discovery (catalog → inspect → execute via `search_tools` meta-tool) + programmatic tool calling. Threshold suggestion: switch when definitions occupy ~1–5% of context window. | **L2** |
| S8 | https://engineering.block.xyz/blog/blocks-playbook-for-designing-mcp-servers | 60+ MCP servers at Block: top-down from workflows, not bottom-up from endpoints; combine internal API calls into one high-level tool; token budget (Claude 3.7 200K limit; performance drops on long context); tactics for large outputs inside tool. | **L3** — enterprise deployment report |
| S9 | https://docs.workato.com/mcp/mcp-server-tool-design | Composable-school counterpoint: simple (one action), composable (Unix-like chaining, consistent naming e.g. `email_address`), predictable (standard errors). Start 3–5 core tools; limit 5–8 per server; don't combine unrelated domains. Test selection accuracy + multi-tool composability. | **L3** — platform guidance (compositional, not workflow-bundled) |
| S10 | https://aws.amazon.com/blogs/machine-learning/mcp-tool-design-practical-approaches-and-tradeoffs | Practical tradeoffs: improve descriptions (reduces confusion, increases bloat); schema constraints (enums, defaults, rename to domain language, drop rare fields); ≤8 params; lazy loading (skills loaded only when relevant, no guarantee). Compares approaches on bloat vs. confusion axes. | **L2/L3** — vendor engineering w/ experiments (rate L2) |
| S11 | http://arcade.dev/blog/mcp-gateway-pattern | Gateway pattern: centralize auth/policy/tooling; tool definitions for 50+ tools = tens of thousands of tokens; gateway (policy + curation + stable contracts) + client-side deferred discovery compose. Registry + tool search alone ≠ governance. | **L4** |
| S12 | https://spyn3.com/resources/too-many-mcp-tools-context-bloat | Measure surface: `tools/list` count, schema size, overlap; flag `search`/`fetch`/`list` collisions and generic `query` params; group by source, reveal on demand, single endpoint. Direct failure mode: every definition enters selection surface. | **L4** |
| S13 | http://formation.dev/blog/mcp-system-design-tool-boundaries | Heuristic: ~12 well-scoped tools beat 40 overlapping ones; test selection errors + task success. Controls that compose: filter (host), split (per-server), scope (per-tool). Discovery ≠ permission; consequential tools need independent checks + host confirmation policy. | **L4** |
| S14 | https://www.itential.com/resource/blog/designing-mcp-servers-for-infrastructure | Outcome-first, aggressive curation, bounded context, deterministic guardrails. Failure of endpoint-mirroring: ambiguous selection, context bloat, higher failure rates. | **L4** |

### B. Agent multi-step reliability + confirmation gates

| ID | Source (URL verbatim) | Claim / evidence | Level |
|----|-----------------------|------------------|-------|
| S15 | https://arxiv.org/html/2610.32555 (also https://arxiv.org/html/2610.32555v1) | **MCP-Injector** (L1 key negative result): 57,240 threads / 1,774 repos calibrate fault profile (permanent-heavy: 91.3% permanent); 1,350-cell factorial (2 backbones × 3 stacks × 3 conditions): faults → task-completion 8.08→3.23 (−60%, Δ −4.85, 95% CI [−5.22,−4.48]); partial degradation most common (56%); scale does NOT buy fault tolerance (120B vs 20B resilience-ratio p=0.96; OPP completion 91.1% vs 95.6%); framework error handling matters more than scale. Treat as stress profile (GitHub reporting bias). | **L1** — pre-print w/ full-factorial experiment |
| S16 | https://arxiv.org/html/2611.07689 | Calling correct tool alone = 84.7% pass; mixing with confusion tools → 32.3% even though required tool still present. Quantifies sprawl penalty. | **L1** |
| S17 | https://arxiv.org/html/2602.00933v1 | MCP-Atlas: incorrect tool selection most common Tool Usage failure; agents fail to try alternatives after failed search despite relevant options present. | **L1** |
| S18 | https://arxiv.org/html/2602.16666v3 | Towards a Science of AI Agent Reliability: GAIA-style multi-step + tool-use evaluation; task-completion vs. grounded evaluation distinction. | **L1** |
| S19 | https://arxiv.org/html/2601.06112v1 | ReliabilityBench: fault tolerance under timeouts/rate-limits/schema drift — closest prior work; differs by lacking calibrated (mode×persistence) profile and middleware approach. Cited by S15. | **L1** |
| S20 | https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk | Tools are primary actions in context window — design for context efficiency; MCP handles auth/API plumbing (Slack, GitHub, Drive, Asana) so focus on agent behavior, not integration code. | **L2** |
| S21 | https://promptessor.com/blog/human-in-the-loop-ai-agents | HITL patterns: approval gates, escalation, pause/resume, reviewer context, audit trails for agents. | **L4** |
| S22 | https://github.com/openai/openai-agents-python/blob/main/docs/human_in_the_loop.md | Reference implementation: pause execution until person approves/rejects sensitive tool calls; tools declare need for approval. | **L3** — framework docs |
| S23 | https://docs.n8n.io/build/integrate-ai/ai-examples/human-in-the-loop-for-tools | Workflow HITL: pause before tool runs, approve via Slack/chat; approve → execute with model-specified inputs. Direct template for HR/IT desk. | **L3** |
| S24 | https://www.reddit.com/r/AI_Agents/comments/1xne5bj/how_are_you_doing_human_approval_for_agent_tool/ | Practitioner comparison of 4 frameworks' approval UX — useful for Synapse Auto client design but anecdotal. | **L5** |

**Deliberately excluded (screened out):** generic ops pages without MCP/agent content (e.g., AWS llms.txt index redirect), tangentially related agent-washing / single-model benchmark posts, YouTube-only claims without transcript data.

---

## 3. Consensus

1. **Workflow-bundled beats endpoint-mirrored — with a composability caveat.** S1, S2, S3, S8, S10, S14 agree: one tool per user story (`onboard_employee`, `schedule_event`, `track_latest_order`), orchestrating 3+ API calls server-side, cuts round trips, context, latency, and selection error. S9/S11 dissent in degree, not direction: keep tools simple/composable with stable contracts and let the *gateway/server* compose; don't make mega-tools ambiguous. Synthesis for Synapse Auto: **coarse at the agent boundary, composable inside the server** — agent sees `hr.create_offer`, `it.provision_accounts`, `onboarding.run_day_one_checklist`; server internally chains HRIS/IdP/ticketing calls with deterministic code.
2. **Tool count is a budget: ~5–12 visible tools, ≤8 params each.** Convergent numbers: Workato 5–8/server starting 3–5 (S9); Formation ~12 beats 40 (S13); AWS ≤8 params, bundle-priority (S2); Anthropic defer beyond ~10 tools / ~10K tokens (S5). Every definition costs tokens on every turn and widens mis-selection (S5, S6, S12, S16).
3. **Sprawl penalty is measured, not hypothetical.** 84.7%→32.3% with confusion tools present (S16); Opus 49%→74% / 79.5%→88.1% with deferred search (S5); 60% score drop under realistic MCP faults with partial (not catastrophic) degradation dominant (S15). Incorrect-tool-selection is the modal failure (S17).
4. **Discovery + execution must be separated.** Progressive disclosure / deferred loading / gateway curation are complementary layers (S5, S7, S11): gateway curates eligibility; client loads only task-relevant definitions; code mode keeps intermediates out of context (S6). For onboarding copilot: HR server, IT server, and knowledge server behind one Synapse Auto gateway; per-role filtering so HR generalist never sees `it.revoke_access` unless in scope (S13's filter/split/scope triad).
5. **Confirmation gates are normative, not optional.** MCP spec: human-in-loop SHOULD always exist with deny; confirm sensitive ops; treat annotations as untrusted (S4). Framework consensus: tools declare approval need; runtime pauses, surfaces proposed action + args, awaits approve/reject; audit log (S21–S23). Spec's `readOnlyHint`/destructive annotations inform UX but never authorize (S1, S4).
6. **Reliability must be measured as system property under faults.** Capability benchmarks mask brittleness (S15); need repeated runs (pass^k, variance, trajectory metrics: path correctness, harmful-call rate, step efficiency), fault injection (MCP-Injector OP0 vs OPP), and grounded-fulfillment scoring (tool appropriateness ≥2) to catch ungrounded bypass answers that inflate scores (S15 §6.1). Larger models do not auto-fix ops brittleness (S15 §6.3).

---

## 4. Gaps, contradictions, and what remains open

- **Composition vs. composability tension unresolved.** No study directly compares Workflow-bundled (S1/S2) vs. Unix-composable (S9) on the *same* HR/IT task suite measuring selection accuracy, recovery rate, and auditability. Risk: over-bundled `onboard_employee(do_everything=True)` becomes ambiguous/untestable; over-granular `create_user`+`assign_license`+`open_ticket` reintroduces chaining failures. **Track 3 decision:** start coarse (S9's "start coarse, break apart on eval signal"), instrument per S1's eval loop.
- **Thresholds are heuristics, not laws.** 8 params, 10 tools, 10K tokens, 12-vs-40 — all vendor/expert rules of thumb (S2, S5, S9, S13), varying by model (namespacing prefix/suffix effects vary by LLM, S1). Must calibrate on Synapse Auto + chosen backbone with golden onboarding tasks.
- **Fault profile is a stress test, not a base rate.** S15's 91.3% permanent-heavy mix inherits GitHub reporting bias; transient/intermittent regimes under-powered (9/1905 events). HR/IT desk needs its own incident mix (IdP rate limits, HRIS schema drift, ticket-queue hangs) — mine Synapse Auto logs, don't reuse open-source weights blindly.
- **HITL UX tax unquantified.** No kept source measures approval fatigue, latency cost of gates, or over-reliance after many approvals — critical for high-volume onboarding weeks. S21–S24 describe mechanisms, not dose-response. Plan A/B: risk-tiered gates (auto-approve read-only + low-risk; bound + step-up for offer letters, compensation, access grants, deletions).
- **Multi-server, long-horizon gap.** S15 uses 25 single-server tasks, excludes multi-agent and HITL workflows (stated limitation). Onboarding is inherently multi-server (HRIS + IdP + MDM + ticketing + docs) and multi-day — exactly the untested regime. ReliabilityBench (S19) and MCP-Atlas (S17) partially cover but not HR/IT.
- **Negative results to keep visible:** (a) retrieval-only fixes cap early for tool-selection failures (community synthesis, screened but not kept as primary — see Q8 results); (b) bigger backbone ≠ more resilient (S15 p=0.96); (c) dirty/irrelevant context can *reduce* accuracy (Q8 "MCP Tool Trap" / context-rot claim) — all argue against "add more tools + bigger model" as strategy.

---

## 5. Implications for Track 3 Onboarding Copilot (HR + IT via Synapse Auto)

**Tool surface (proposed v0):**
- `hr.search_policy(query)` — retrieval only, concise by default, `fields`/`limit` args (S1 response_format, S13 grep/sort/head mapping).
- `hr.create_offer(candidate_id, …)` — write, **confirmation gate + separation of duties** (S4, S21).
- `it.provision_accounts(employee_id, bundles)` — bundled workflow (IdP + M365/Slack + MDM), idempotent, dry_run default true; returns checklist + handles.
- `it.order_equipment(employee_id, catalog_item)` — bundled with eligibility check inside.
- `onboarding.run_day_one_checklist(employee_id)` — top-level composed tool for the canonical user story (S2 "think in user stories").
- Gateway: Synapse Auto exposes only role-scoped subsets; defer rest (S5, S7, S11). Consistent `domain.entity.verb` naming; no `search` collisions (prefix by service, S1).

**Reliability + gates:**
- Risk tiers: Tier 0 read-only auto; Tier 1 low-risk writes (ticket notes) single approver; Tier 2 high-stakes (offers, comp, access grants, wipes) bound confirmation showing diff + affected systems + reversible window, with audit log (S4, S21–S23).
- Never trust `readOnlyHint` for authz; enforce server-side with scoped credentials (S4, S11).
- Eval: golden onboarding tasks (happy + edge + adversarial: ambiguous names, duplicate employee IDs, IdP 429, HRIS schema change), repeated runs, trajectory metrics (path correctness, harmful-call rate, step efficiency), OP0 vs fault-injected comparison via MCP-Injector-style middleware, grounded-fulfillment scoring (S15, S1 cookbook).
- Token/composability hygiene: `outputSchema` + cursor pagination + summary-first (S4, S9); code mode for multi-doc assembly (offer packet) to avoid intermediate bloat (S6).

---

## 6. Limitations of this review

- Web-only, no independent re-analysis; arXiv pre-prints (S15–S19) not yet peer-reviewed — rated L1 for empirical rigor but provisional.
- Counts are retrieval-log estimates from result pages, not database exports.
- HR/IT-specific MCP studies absent — generalization from engineering-assistant, DB, and telecom benchmarks assumed; flag for Phase 1 primary evaluation.

## 7. References (only URLs returned by search/fetch — no invented URLs)

- https://www.anthropic.com/engineering/writing-tools-for-agents
- https://docs.aws.amazon.com/prescriptive-guidance/latest/mcp-strategies/mcp-tool-strategy-scope.html
- https://docs.aws.amazon.com/prescriptive-guidance/latest/mcp-strategies/introduction.html
- https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- https://www.anthropic.com/engineering/advanced-tool-use
- https://anthropic.com/engineering/code-execution-with-mcp
- https://modelcontextprotocol.io/docs/develop/clients/client-best-practices
- https://engineering.block.xyz/blog/blocks-playbook-for-designing-mcp-servers
- https://docs.workato.com/mcp/mcp-server-tool-design
- https://aws.amazon.com/blogs/machine-learning/mcp-tool-design-practical-approaches-and-tradeoffs
- http://arcade.dev/blog/mcp-gateway-pattern
- https://spyn3.com/resources/too-many-mcp-tools-context-bloat
- http://formation.dev/blog/mcp-system-design-tool-boundaries
- https://www.itential.com/resource/blog/designing-mcp-servers-for-infrastructure
- https://arxiv.org/html/2610.32555
- https://arxiv.org/html/2611.07689
- https://arxiv.org/html/2602.00933v1
- https://arxiv.org/html/2602.16666v3
- https://arxiv.org/html/2601.06112v1
- https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
- https://promptessor.com/blog/human-in-the-loop-ai-agents
- https://github.com/openai/openai-agents-python/blob/main/docs/human_in_the_loop.md
- https://docs.n8n.io/build/integrate-ai/ai-examples/human-in-the-loop-for-tools
- https://www.reddit.com/r/AI_Agents/comments/1xne5bj/how_are_you_doing_human_approval_for_agent_tool/
