# 04 — Skills in the Market vs `onboard_employee_guarded` (Single Composite Tool)

> Date: 2026-11-22 | Track: research/diff | Question: What is a "skill" in each ecosystem, how is it installed, can it do cross-system write-back with approval + audit? How does that compare to our 1-tool `onboard_employee_guarded`?
> Sources: 11× websearch + 2× Context7 query-docs (`/modelcontextprotocol/modelcontextprotocol`, `/prefecthq/fastmcp`). URLs inline.

## TL;DR

Every major ecosystem converged on the **same file format** — Agent Skills (`SKILL.md` + frontmatter `name`/`description` + bundled scripts/resources) donated by Anthropic to the Agentic AI Foundation (Oct 2026) — but they differ on **execution power**. Claude / Copilot / VS Code / Replit skills are **prompt+script packages**: portable, auto-discovered, but they still call N separate tools and rely on the host for approval/audit. OpenAI GPT Actions, Notion connectors, LangChain templates are **connector/tool wrappers**, not Skills-spec. MCP (+ FastMCP) is the **execution substrate** underneath all of them. Our `onboard_employee_guarded` inverts the market: **one `@mcp.tool` fusing 8 private helpers** (`_verify_offer → _background_check_gate → _pick_role_bundle → _provision(staged) → _assign_equipment → _schedule_training → _preview → _activate_day_one`) with enforced order, `confirm + preview_hash` gate, least-privilege diff, staged-reversible-until-day-one, idempotent receipt + citations. Market skills optimize **reuse/portability**; our tool optimizes **safety/atomicity** — agent *cannot* skip the BG gate or provision admin early.

## 1. What "skill" means per ecosystem

### 1.1 Claude / Agent Skills (the canonical spec)
- **What:** Folder with `SKILL.md` (`--- name, description ---` + Markdown instructions) + optional `scripts/`, `references/`, `assets/`. Dynamically loaded when description matches task. Now stewarded by Agentic AI Foundation (Linux Foundation, also hosts MCP) since 2026-10-22. Spec: `agentskills.io/specification`.
- **Install:** `/plugin marketplace add anthropics/skills` then `/plugin install document-skills@anthropic-agent-skills`; or clone `github.com/anthropics/skills`. Works in Claude Code, Claude.ai, API.
- **Write-back / approval / audit:** Skill itself is *advisory* — it tells Claude *how* to use tools (often MCP tools). Approval comes from host (Claude Code consent dialog / `agent_toolset_20260401` deny-by-default config). Audit = host transcript, no built-in immutable receipt. Cross-system writes possible only if host grants tools.
- URLs: https://www.anthropic.com/news/skills · https://agentskills.io/specification · https://github.com/anthropics/skills · https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview · https://www.anthropic.com/research/equipping-agents-for-the-real-world-with-agent-skills

### 1.2 OpenAI GPT Actions (GPTs → Plugins/Skills migration)
- **What:** Custom GPT = instructions + knowledge files + **Actions** (OpenAPI JSON → Function Calling → 3P API with auth). 2026 migration: GPTs retiring; *instructions become portable Skills, Actions must be rebuilt as connectors/your own server*. Community note: "A Skill is not a Custom GPT; a Skill provides a capability/behavior."
- **Install:** GPT Builder (no code) → publish to GPT Store; new world: rebuild as App/connector. Tool `GPT2Skill` converts GPT instructions → Claude Skill zip.
- **Write-back / approval / audit:** Actions *can* POST/mutate external systems via user auth, with per-action consent popup. No cross-action atomicity, no ordering enforcement, no unified audit receipt — each API call logged separately. Prompt-injection can trigger unwanted Action.
- URLs: https://developers.openai.com/api/docs/actions/introduction · https://openai.com/index/introducing-gpts · https://rethinksoft.com/blog/custom-gpts-to-plugins-and-skills · https://community.openai.com/t/chatgpt-skills-do-not-replace-custom-gpt-s/1402690 · https://ryandoser.com/claude-skills-vs-custom-gpts/

### 1.3 GitHub Copilot Extensions + Copilot CLI Plugins
- **What:** Two different things: (a) **Extensions** = GitHub Apps published to GitHub Marketplace (`marketplace?type=apps&copilot_app=true`), add chat commands/side-effects; (b) **CLI plugins** = git-repo packages bundling `agents/ + skills/ (SKILL.md) + hooks + MCP servers + LSP` with `plugin.json` manifest.
- **Install:** Extensions: Install on GitHub.com → enable in IDE. Plugins: `copilot plugin marketplace add …` / `browse awesome-copilot` / `copilot plugin install azure@awesome-copilot`; lands in `~/.copilot/installed-plugins/<marketplace>/<plugin>`. Per-developer, not per-repo.
- **Write-back / approval / audit:** Extension writes run under GitHub App identity + repo permissions, need explicit user accept in chat. CLI skill scripts (e.g. `list_workflow_runs` → `get_job_logs` via GitHub MCP Server) demo debugging but no built-in maker-checker; audit = repo audit log, not tool-level receipt.
- URLs: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills · https://github.com/github/awesome-copilot · https://chris-ayers.com/posts/agent-skills-plugins-marketplace/ · https://dev.to/pwd9000/github-copilot-cli-plugins-and-marketplaces-extend-your-terminal-agent-16 · https://docs.github.com/copilot/managing-copilot/configure-personal-settings/installing-the-github-copilot-extension-in-your-environment

### 1.4 VS Code Agent Skills
- **What:** Same Agent Skills standard, surfaced as reusable runbooks in the editor. Distinct from sibling primitives: Custom Instructions (always-on standards), Prompts (reusable one-off tasks), Custom Agents (mode configs). Skill = `SKILL.md` + scripts/templates/examples, on-demand + auto-discovered.
- **Install:** Customization Marketplace (Preview) → Skills pane `vscode://chat-customizations/open?page=skills`; locations: project `.github/skills/`, personal `~/.copilot/skills/`, plus `.agents/skills/` (Codex), `.gemini/skills/` shims for cross-tool compat. Toggle via Settings → Agent Skills (experimental).
- **Write-back / approval / audit:** Can bundle scripts that edit workspace + invoke MCP tools; approval via VS Code tool-approval UI, deny-by-default toolsets possible. No cross-system atomic transaction or tamper-evident receipt out of box.
- URLs: https://code.visualstudio.com/docs/agent-customization/agent-skills · https://code.visualstudio.com/docs/agent-customization/overview · https://code.visualstudio.com/learn/customizations/3-skills · https://dev.to/pwd9000/github-copilot-instructions-vs-prompts-vs-custom-agents-vs-skills-vs-x-vs-why-339

### 1.5 LangChain Templates / LangSmith Hub + Context Hub
- **What:** Not `SKILL.md`; **templates** = prebuilt LangGraph agents/chains (e.g. `react-agent-template`) + 30+ reusable evaluator templates + prompt templates (f-string/mustache). New **Context Hub**: "packages a reusable capability an agent can invoke" + references/schemas — closest to Skills.
- **Install:** `smith.langchain.com/hub` → clone template repo / pull prompt; LangSmith for tracing/eval.
- **Write-back / approval / audit:** LangGraph gives durable state, branching, approval *nodes*, LangSmith tracing/eval — the strongest native approval+audit story (traces link decision→policy→data). But building an 8-system atomic onboarding still requires hand-wiring; template does not enforce ordering by itself.
- URLs: https://smith.langchain.com/hub · https://docs.langchain.com/langsmith/context-engineering-concepts · https://www.langchain.com/blog/reusable-langsmith-evaluator-templates · https://docs.langchain.com/langsmith/prompt-template-format

### 1.6 Replit Agent Skills
- **What:** Same Skills-spec compatible. Two tiers: pre-defined/partner skills (Stripe, PayPal, RevenueCat, Mixpanel, BigQuery, Resend, Google Workspace, Atlassian, Google Maps — each teaches Agent integration patterns) + community skills via directory.
- **Install:** Chat `+ → Use a skill` picker (attach to one message, no install) OR `Install` to project OR `npx skills <skill> -a replit` / `skills.sh`. Import from GitHub auto-detects Skills.
- **Write-back / approval / audit:** Agent executes in Replit workspace (code + deploy + integrations via MCP). Writes gated by Replit Agent confirm step; no staged-reversible-until-date, no least-privilege diff, no idempotency receipt standard.
- URLs: https://docs.replit.com/features/agent/skills · https://docs.replit.com/build/use-agent-skills · https://docs.replit.com/features/agent/skills-directory · https://www.analyticsvidhya.com/blog/2026/04/replit-agent-skills/

### 1.7 Notion AI Skills / Connectors / Automations
- **What:** No public "Skill" spec. "Skills" = Notion AI features + **AI Connectors** (Slack, Drive, Jira…) + **Connections gallery** (60+ via Darkmatter Agents etc.) + database automations (trigger → action) + 3P glue (Zapier/Make/Carly/Caddi for cross-app sync/approvals).
- **Install:** Settings → Connections → OAuth to 3P; Automations builder inside database; no `SKILL.md` sideload.
- **Write-back / approval / audit:** Edits pages/databases, can sync CRM → Notion, run approvals. Cross-system writes are per-integration, user-token scoped, automation-run log only. No composite guardrail (cannot fuse HRIS+IdP+payroll+inventory atomically).
- URLs: https://www.notion.com/connections · https://www.notion.com/help/notion-ai-connectors · https://www.usecarly.com/blog/best-ai-automation-tools-notion/ · https://www.trycaddi.com/integrations/notion

### 1.8 Substrate: MCP + FastMCP (Context7)
- **MCP** (`/modelcontextprotocol/modelcontextprotocol`, 5576 snippets): JSON-RPC `tools/call`, `resources`, `prompts`; security via client-side approval, OAuth, `ToolAnnotations(readOnlyHint/destructiveHint/idempotentHint/openWorldHint)`; new patterns **Elicitation** + **Sampling/MRTR** (`InputRequiredResult` → `sampling/createMessage` → human review → retry with `inputResponses`). Client "should inform user before sampling… approve/deny/modify", can show prompt/model/tokens, auto-approve trusted ops.
- **FastMCP** (`/prefecthq/fastmcp`, 8349 snippets): `@mcp.tool` from plain Python fn with schema gen; annotations for read-only vs destructive; `Middleware/on_call_tool` → structured audit record per call (tool name, call id, schema hash, redacted args, status, duration; raw I/O excluded); client `Client(...)` + `fastmcp run`. Decorated fn stays callable → unit-test helpers directly.
- URLs: https://modelcontextprotocol.io/specification/2025-06-18/server/tools · https://gofastmcp.com/docs/servers/tools · https://gofastmcp.com/docs/getting-started/welcome · https://github.com/prefecthq/fastmcp · https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices

## 2. Comparison table

| Ecosystem | What is a "skill"? | Install | Cross-system write-back? | Approval gate | Audit trail | vs `onboard_employee_guarded` (1 composite `@mcp.tool`, 8 fused helpers) |
|---|---|---|---|---|---|---|
| Claude Agent Skills (AAIF std) | `SKILL.md` + scripts/refs; auto-loaded playbook | `/plugin marketplace add` + `/plugin install` | Yes, via host tools/MCP | Host dialog; `agent_toolset deny-by-default` | Transcript only | Guidance only; ours **enforces order + atomic stage→activate**, agent can't skip BG check |
| OpenAI GPT Actions | OpenAPI action behind Custom GPT | GPT Builder → Store; now rebuild as connector | Yes, per-API POST | Per-action consent popup | Per-call logs, no receipt | Per-action, no transaction; ours single `confirm+preview_hash`, idempotent receipt, prompt-injection still denied by policy-inside-tool |
| Copilot Extensions / CLI plugins | GitHub App OR repo pkg (`agents+skills+hooks+MCP`) | Marketplace Install / `copilot plugin install x@y` | Yes, repo/API scoped | Chat accept | GitHub audit log | Scattered tools; ours fuses HRIS+IdP+payroll+inventory in one call (1 vs 8 calls) |
| VS Code Agent Skills | Same spec; runbook vs instructions/prompts/agents | Marketplace Skills pane; `.github/skills/` | Workspace + MCP tools | Tool-approval UI | Editor history | Portable runbook; ours adds least-privilege diff + staged-reversible + citations |
| LangChain Hub / Context Hub | Agent template + prompt/evaluator lib | Hub pull/clone | Yes, via LangGraph nodes | Custom approval nodes + HITL | LangSmith traces (strongest) | Closest on audit; ours still wins on **atomicity/completeness proof** without hand-wired graph |
| Replit Skills | Partner/community skills teaching integration patterns | `+ → Use a skill` / `npx skills <s> -a replit` | Yes, inside Repl + integrations | Agent confirm step | Run log | Attach-per-message convenience; ours persists staged state to Day-1 00:00 with auto-shift for weekends |
| Notion AI/Connectors | Connectors + automations, no SKILL.md | OAuth Connections gallery | Page/DB edits + sync | Implicit (token scope) | Automation run log | Single-system edits; ours spans 5 systems with BG-pending block + VISA_RISK + rehire-merge |
| MCP (protocol) | `tools/call` + annotations + elicitation/sampling HITL | Add MCP server | Yes, any tool | Client must approve; MRTR flow | Host-dependent | Protocol allows our pattern; doesn't provide it |
| FastMCP (framework) | `@mcp.tool` decorator + middleware | `pip install fastmcp`, `fastmcp run` | Yes, Python fn | `confirm` param pattern + `AuditMiddleware` | Structured per-call record (redacted) | **Our implementation substrate** — proves 1-tool + 8 private `def _...()` + receipt pattern |

## 3. Why our single composite wins for onboarding

From `research/brainstorm/03-track2-composite.md §4` + `research/final/16-judge-score.md` + `18-contradictions.md`:

```
_verify_offer → _background_check_gate → _pick_role_bundle → _provision(staged)
→ _assign_equipment → _schedule_training → _preview → _activate_day_one
Params: candidate_id, start_date, role_code, manager, confirm=False, preview_hash
```

- **Footgun removed:** many-tools = agent calls provision in wrong order → admin on day -5. 1-tool = stage-then-activate enforced in code.
- **Guardrails inside, not beside:** `BG_PENDING` blocks activation (can still stage); `VISA_RISK` (<90d auth) + HR ticket; unknown bundle → fail-closed `baseline_readonly`; rehire → merge; weekend start → auto-shift.
- **Cite-Before-Act gate:** preview lists 6 accounts + RBAC diff ("asked admin → granted deploy-read") + laptop SN hold + training Tue 10:00 with citations (`OFFER §2.1`, `BG-CLEAR #881`, `INV-HOLD LT-4420`); execute needs `confirm=True + preview_hash`.
- **Receipt, not transcript:** `Out(ok, preview, receipt_id, errors, citations)`; idempotency on re-confirm; staged-reversible until 00:00 start-date.
- **Audit:** FastMCP `AuditMiddleware` per-call record + our domain receipt links decision→policy version→row IDs→approver — matches Rocket/IDC 8-part audit framework (agent identity, context, evidence, authority, approver, action, outcome) where market skills give only "we have logs".
- Extra proof: WebMCP RBAC precedent, PRISM "decisions to approve, not paragraphs", Cite-Before-Act Best Overall (MCP 1st Birthday) — all cited as template sources.

Market skills win on **portability** (one SKILL.md runs in Claude/Copilot/VS Code/Replit). We win on **safety + demo punch**: "we deleted 7 tools; agent cannot half-execute."

## 4. Recommendation

- Ship `onboard_employee_guarded` as FastMCP server (helpers plain, one `@mcp.tool`).
- Also publish a thin `SKILL.md` wrapper (name `onboard-employee-guarded`, description "Use when onboarding…") so it is discoverable in Claude/Copilot/VS Code/Replit marketplaces — best of both: portable discovery + atomic execution.
- Reuse `ToolAnnotations(destructiveHint=True)` + `AuditMiddleware` for receipt; document 1-vs-8 call table + failed many-tools run for judges.

## 5. Sources (all URLs)

Claude/Skills: https://www.anthropic.com/news/skills · https://agentskills.io/specification · https://github.com/anthropics/skills · https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
OpenAI: https://developers.openai.com/api/docs/actions/introduction · https://rethinksoft.com/blog/custom-gpts-to-plugins-and-skills
Copilot: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills · https://chris-ayers.com/posts/agent-skills-plugins-marketplace/ · https://github.com/github/awesome-copilot
VS Code: https://code.visualstudio.com/docs/agent-customization/agent-skills
LangChain: https://smith.langchain.com/hub · https://docs.langchain.com/langsmith/context-engineering-concepts
Replit: https://docs.replit.com/build/use-agent-skills · https://docs.replit.com/features/agent/skills-directory
Notion: https://www.notion.com/connections · https://www.notion.com/help/notion-ai-connectors
MCP/FastMCP: https://modelcontextprotocol.io/specification/2025-06-18/server/tools · https://gofastmcp.com/docs/servers/tools · https://github.com/prefecthq/fastmcp
Governance/audit framing: https://www.rocketsoftware.com/en-us/insights/ai-agent-audit-trail · https://www.cloudsufi.com/resources/articles/ai-agent-platforms-for-enterprises-in-2026-what-to-compare-before-you-buy/ · https://assistents.ai/blogs/ai-agent-platform-for-enterprise
Internal: `research/brainstorm/03-track2-composite.md §4` · `research/final/16-judge-score.md` · `research/final/18-contradictions.md` · `research/03-synapse-technical.md`
