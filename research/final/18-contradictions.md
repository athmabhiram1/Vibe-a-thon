# 18 — Contradictions Map: Where Sources Disagree on Onboarding / MCP Approach

**Date:** 2026-11-22 · **Scope:** onboarding + MCP-tool design disagreements relevant to Vibe-a-thon with 2nd Brain Labs.
**Method:** claims below are drawn from `research/01-2nd-brain-labs.md`, `02-geek-room.md`, `03-synapse-technical.md`, `04-slop-vs-differentiated.md`, `brainstorm/02-track1-hard.md`, `brainstorm/03-track2-composite.md`, `brainstorm/09-judge-fit.md`. Status scale: **Unresolved / Leaning-A / Leaning-B / Resolved**.

---

## Row 1 — Consumer polish wins overall vs Infra/governance wins enterprise (and overall)

| | Claim |
|---|---|
| **A — Consumer / single-flow transactional wins** | Geek Room Vibe-a-thon 2.0 winner pattern was single-flow transactional (ShopperMan: paste-link → analysis → action — `brainstorm/09-judge-fit.md §3`); MCP Birthday **Best Consumer: Portfolio Intelligence Platform** (multi-agent portfolio analysis with visible trace); LlamaIndex RAG-a-thon winner **Timeline of You** won by generating a concrete O-1 visa-packet artefact; YC Browser-Use winner **Browser Brawl** won on live-site evals. Common thread: 60-second wow, artefact on screen. Sources: `04-slop-vs-differentiated.md §(c)(1)(4)`; `09-judge-fit.md §3`. |
| **B — Infra / safety / governance wins (even Best Overall)** | MCP Birthday **Best Overall: Cite-Before-Act MCP** (approval gate before state-mutating tools) + **Best Enterprise: MCEPTION** (MCP server that deploys other MCP servers); Solo.io 2026 winner: **K8s-native MCP governance** (security-posture scoring via Gemini/Ollama) + runner-up **MCP.STORE** ("agents *cannot bypass* Keycloak JWT + CEL"); DataHub Grand Prize: **Blackbox** (lineage-grounded incident response with machine-enforced evidence gate, opens PR). Sources: `04 §(c)(1)(2)(3)`; GSA rubric `04 §(b)(8)`. |
| **Root of disagreement** | Track split + judge composition. Consumer-track judges reward wow/artefact; enterprise-track (and 2BL-sponsored) judges reward "cannot do the wrong thing" (policy-before-rails, audit, idempotency). PitchScoop counter-example is instructive: won with 32+ tools but judges still flagged tool-sprawl fatigue (`03-track2-composite.md` header). |
| **Status** | **Leaning-B for this event; Unresolved globally.** |
| **Current balance** | For a 2BL-judged event (thesis = "integration tax," "governance at the source" — `01 §2`), lead with B (governed write-back + audit) wrapped in A's 60-second wow (paste ID → preview → approve → receipt visible). For a Geek Room general event, invert the wrapper. |

## Row 2 — Local Ollama is sufficient vs Hosted backend is required

| | Claim |
|---|---|
| **A — Local is enough (private, no quota, offline)** | README `#choosing-a-provider`: `--local` supports 9 providers incl. **Ollama (no key)**, Bedrock/Vertex/custom OpenAI-compatible; **no quota, no signup**; "Mostly yes" offline if code + inference stay on-machine (telemetry off via `SYNAPSE_TELEMETRY=0`). Source: `03 §2.5` table + `03 §2.1` (`synapse model set … ollama`). |
| **B — Hosted is required for a gradable demo** | (i) **Local Auto on non-Python yields names but no file** (TS/Java/C#/Go/Rust get `--smart-names` only); hosted Auto gives account-side config + `npx synapse-mcp` runner instead (`03 §2.5`). (ii) Weak/small local models fail codegen with `returned no emit_tool_plan call` — "fix is a stronger model" (`03 §2.6`). (iii) Either way, Auto tools are HTTP forwards — you still need a **deployed API + `ENDPOINT_BASE_URL`** (`03 §2.2`, `src/backend/server-renderer.ts`). |
| **Root** | Language × mode matrix + model-strength threshold. Local/Custom/Python + strong model works; Local/Auto/non-Python does not produce a runnable server by design. |
| **Status** | **Leaning-B.** |
| **Current balance** | Default to **hosted** for the graded path (especially any non-Python codebase). Use `--local` only for Python Custom with a strong model (qwen3-coder:30b-class or hosted API model), and pre-test `emit_tool_plan` success. Always budget gRPC + quota + runner-fetch risk on event Wi-Fi (`03 §4` checklist). |

## Row 3 — Many tools (expose everything) vs Few curated tools (one composite)

| | Claim |
|---|---|
| **A — Expose every route (coverage = capability)** | Synapse Auto default: one tool per discovered HTTP route; headless `--all-endpoints` / `--endpoints "GET /x,…"`; rebuilds update same server ID (`03 §2.1`). Implicit vendor pitch: nothing migrated, everything reachable. Source: npm README `#how-build-works`, `#reusing-discovered-endpoints` (via `03 §2.1–2.2`). |
| **B — Few curated, goal-shaped tools win; mirroring endpoints is penalised** | GSA 2026 rubric: "each tool [must be] a **real agent-facing action, not a thin wrapper around a single REST call**… rather than mirroring underlying API endpoints" (`04 §(b)(8)`). Winners that fused beat winners that sprayed: OrbitCast, PRISM ("decisions to approve, not paragraphs"), WebMCP RBAC-gated tools (`03-track2-composite.md` header). `brainstorm/03` template: **1 `@mcp.tool` fusing 5–8 private helpers** with Detect → Validate → Dry-run preview → Confirm → Execute → Receipt; demo angle "we deleted 7 tools." |
| **Root** | Generator default (mirror the API) vs judge rubric (design around user goals + enforce ordering: policy-before-rails, match-then-post atomic). Many-tools lets the agent pay-before-fraud-check or revoke-SSO-but-leave-API-key (`03-track2-composite.md §5–6`). |
| **Status** | **Leaning-B (strong).** |
| **Current balance** | Use Auto for **discovery breadth**, Custom for the **graded write path**. Ship one composite (`adjudicate_claim`, `reconcile_shipment`, `sunset_vendor`, `refund_with_policy_gate`) with `confirm + preview_hash`, idempotency, and a 1-vs-6 call-count table showing the agent *cannot* skip the policy step. |

## Row 4 — Onboarding / employee-lifecycle agent is cliché vs Guardrailed onboarding is novel

| | Claim |
|---|---|
| **A — Onboarding/HR agent is slop** | Saturated archetypes judges have "seen a gazillion times": resume matcher/ATS scorer (3 job-agent winners in one Agno edition), generic CRM copilot/outreach blaster, booking bot, chatbot-for-a-website — all rejected for "no permissioning, no audit, no artefact; feature not a product" (`04 §(a)(2)(8)(9)(10)`; `09-judge-fit.md §1`). A plain "ask HR docs" chat collapses into slop #1/#9. |
| **B — Guardrailed onboarding/offboarding is white-space** | `onboard_employee_guarded` fuses 8 steps (`_verify_offer → _background_check_gate → _pick_role_bundle → _provision(staged) → _assign_equipment → _schedule_training → _preview → _activate_day_one`) with **least-privilege-by-default, BG-pending block, staged-reversible until day-one 00:00, least-privilege diff in preview** (`03-track2-composite.md §4`). Sibling picks `sunset_vendor` (zombie-spend + lingering keys) and `quarantine_dataset` (lineage-aware freeze) use the same completeness-proof logic; WebMCP RBAC precedent shows permissioning wins. |
| **Root** | Chat-only vs state-change distinction. Judges ding "ChatGPT can do this" text output (`04 §(b)(9)`); they reward **state change + audit record behind an approval gate** (Cite-Before-Act + Blackbox pattern — `09 §1` write-back rule). |
| **Status** | **Leaning-B (conditional).** |
| **Current balance** | Build onboarding **only** as a guarded composite: background-check gate that blocks activation, role-bundle that fails closed to `baseline_readonly`, staged-vs-active separation, `confirm+preview_hash`, receipt with citations. Demo the failure branch (agent tries "just provision admin on day −5" → tool refuses). Without those gates, drop the idea — it reads as slop. |

## Row 5 — RAG chatbots are banned vs Agentic RAG is on the roadmap

| | Claim |
|---|---|
| **A — RAG demos are dead on arrival** | Qdrant "Think Outside the Bot" **banned pure chatbots two years running** ("submissions that are only chatbots are not allowed" — 2026 rules; 2025 "beyond chatbots" recap); TiDB AgentX: "last year… **thousands of simple RAG demos**. This year we want multi-step agents with real-world workflows." Sources: `04 §(b)(1)(2)`; re-verified in `09 §1`. |
| **B — Synapse roadmap bets on RAG + Skills** | Founder essay: three knowledge layers — Systems→MCP servers (done), **Documents→Agentic RAG Pipelines (being built), Workflows→Skills (being built)**; docs/RAG/Skills scope is explicitly *not* the current gradable surface (`01 §2` + blog `synapse-vs-palantir` 4 Aug 2026; `01 §5(6)` open question). |
| **Root** | Basic retrieve-and-chat vs agentic RAG: citations + policy gates + write-back artefact. Winners prove the latter wins (Blackbox lineage evidence gate; Timeline-of-You O-1 packet; Clinical-MIMIC federation over credentialed MIMIC-IV — `04 §(c)`). |
| **Status** | **Resolved as a distinction (not a tie).** Basic RAG-chat loses; evidence-grounded agentic RAG wins. |
| **Current balance** | Do **not** demo "upload PDF, ask questions." If touching documents, copy the winning shape: retrieve → cite clause/row IDs → enforce policy → produce a concrete artefact (EOB letter, O-1 packet, discharge packet) → write back with approval. That satisfies both the ban and the roadmap. |

## Row 6 — Official docs onboarding vs README + source onboarding (stale-docs contradiction)

| | Claim |
|---|---|
| **A — Docs site path (v1 engine)** | `synapse.2ndbrainlabs.ai/docs` documents `--query`, `--output`, `--no-validate/--no-docs/--generate`, `synapse status`, Node 18, Qdrant indexing, "Output defaults to `mcp_server.py`" (`03 §2.1` warning box). |
| **B — README + source path (v2 only)** | README: **v1 removed in SYN-257 (0.1.9)**; passing v1 flags **exits non-zero**; commands are `init / build [--auto\|--custom] / analyze / config / model (local-only) / info`; **Node ≥ 20**; extraction is client-side tree-sitter + Aho-Corasick prefilter, codegen via streaming gRPC or local pipeline (`03 §2.1–2.2`; files `needles.ts`, `tool-shaper.ts`, `schemas.ts`, `custom-flow.ts`, `architecture.md`, `AGENTS.md`). |
| **Root** | Docs lag releases (0.1.5 Sep 3 → 0.1.9 Nov 9; active cadence — `03 §1`). Copy-paste from docs or old tutorials breaks. Companion trap: builds silently reuse `.synapse/surface_cache.json` until `--discover` (`03 §3(5)`). |
| **Status** | **Resolved — B wins.** |
| **Current balance** | Follow **README + `synapse --help` + source files only**; ignore the docs site for flags. Demo contract: Python codebase, `synapse build --discover` every rebuild, headless flags in CI (`--all-endpoints`/`--endpoints`), v1 flags never. Verify `npx -y @2ndbrainlabs-ai/synapse-mcp` early — runner has no README (`03 §4`). |

---

## Cross-row balance (what to do Monday morning)

1. **Graded demo = Python + hosted Auto (discovery) + one Custom composite (write path)** with deployed API behind `ENDPOINT_BASE_URL`.
2. **Every write** goes through preview → `confirm+preview_hash` → idempotent execute → receipt with citations (Cite-Before-Act/Blackbox shape).
3. **1-vs-many table** on the README/slide: tool-calls 1 vs 6–8, plus a live "agent tries to skip policy → blocked" moment.
4. **No chat-only seconds**: each 60-second path ends in a visible state change + audit row (file advanced, claim adjudicated, bed assigned, vendor spend killed).
5. **Trust README over docs site**; re-run `--discover`; pin versions (`0.1.9` CLI / `0.0.4` runner as of 22 Nov 2026).

### Source index (all accessed 22 Nov 2026 per prior files)
- 2BL/Synapse: https://2ndbrainlabs.ai/ · https://2ndbrainlabs.ai/synapse · https://2ndbrainlabs.ai/blog/synapse-vs-palantir · https://synapse.2ndbrainlabs.ai/ · https://synapse.2ndbrainlabs.ai/docs · https://www.npmjs.com/package/@2ndbrainlabs-ai/synapse-cli · https://github.com/2ndbrainlabs-ai/synapse-cli-ts
- Geek Room: https://luma.com/k1fova8c · https://www.geekroom.co.in/partners · https://www.geekroom.co.in/event/vibeathon-2nd-brain-labs
- Judging signals: https://try.qdrant.tech/hackathon-vsd · https://qdrant.tech/blog/vector-space-hackathon-winners-2025 · https://tidb-2025-hackathon.devpost.com · https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon · https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table · https://info.devpost.com/blog/hackathon-judging-tips
- Winners: https://gradio.app/mcp-birthday-winners · https://www.solo.io/blog/celebrating-the-winners-of-the-2026-hackathon-for-mcp-ai-agents · https://datahub.com/blog/meet-the-winners-of-build-with-datahub-the-agent-hackathon
