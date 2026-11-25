# 01 — Paperclip: Identity + Feature Diff

**Date:** 2026-11-22
**Verdict: User means `paperclipai/paperclip` (paperclip.ing) — open-source “company of agents” orchestration / control plane.**
Confidence: HIGH. 12x websearch + docs fetch + Context7 + gh_grep all converge. No credible “Paperclip HR SaaS” or “Paperclip design tool” company found.

> Tagline: “If OpenClaw is an *employee*, Paperclip is the *company*.” Node.js server + React UI. Bring-your-own agents, assign goals, track work/cost from one dashboard. Looks like a task manager; under the hood: org charts, budgets, governance, goal alignment.

## 1. Identity verdict

| Candidate | Verdict | Evidence |
|-----------|---------|----------|
| **paperclipai/paperclip (paperclip.ing) — agent harness / control plane** | **MATCH — this is the tool** | GitHub ~114–115k stars, MIT, `npx paperclipai onboard --yes`, docs.paperclip.ing, 4 pillars (Task Manager / Org Chart / Training / Agentic OS) |
| Paperclip HR onboarding SaaS | NOT FOUND as standalone company | Only hits are *agents running inside* Paperclip: janovaai “HR Onboarding Assistant” demo ($49/mo single / $199 catalog — third-party), `persona-hr-coordinator` skill, blog “HR and onboarding” use-case. No HRIS product named Paperclip. |
| Paperclip (Anthropic skills) | PARTIAL — uses Anthropic Agent Skills spec, not owned by Anthropic | `SKILL.md` frontmatter `name+description` routing, Skill Studio, catalog `bundled/optional`, import via `skills.sh`/GitHub/URL. Separate from `anthropics/skills` repo. |
| Paperclip skills marketplace | Third-party ecosystem, not core | paperclipskills.com (URL-based skills, x402 USDC payments, security scan), paperclipmarket.com (curated directory, “No skills published yet”), skills.sh registry, `paperclipai/companies` templates repo |
| Paperclip MCP | YES — bi-directional, core feature | Agents consume any MCP server (Allowed/Ask-first/Off per action); Paperclip *serves* MCP at `/mcp/paperclip` (37 tools, experimental, OAuth). Plus `@paperclipai/mcp-server` (stdio, ~45 tools) + community `Wizarck/paperclip-mcp` (95 tools) |
| Paperclip automation | YES — routines/heartbeats, not Zapier-style | Scheduled routines (cron/webhook/API), heartbeat execution (assignment/comment/schedule/manual), not a generic workflow builder |
| Paperclip design tool | NOT FOUND | No Figma/Moqups competitor named Paperclip. Only “wireframe” skill (low-fi SVG) + “design-critique” skill inside catalog. |
| **Confusable: paperclip.gxl.ai** | **DIFFERENT PRODUCT — do not conflate** | Literature search (papers/preprints/trials/FDA/patents) via remote MCP at `paperclip.gxl.ai/mcp`, API at `/api/v1`, pricing page Free/$200-mo Pro with “rows per dataset”. Found via K-Dense BYOK code + `paperclip.gxl.ai/pricing`. |

## 2. What it does (4 pillars)

1. **Agentic Task Manager** — tasks/issues with single owner, atomic checkout + execution locks, blockers, threads, diffs/screenshots/tests verification, routines.
2. **Org Chart for Agents** — mixed human+agent chart, roles/delegation, governance “who can do what”, scoped secrets, connection permissions, responsible-user identities, multi-org isolation.
3. **Agent Employee Training** — Skill Studio, shared org-wide skills, evals/saved test runs, active-learning loops, performance reviews, version history/restore, team templates.
4. **Agentic OS** — cross-provider runtime (Claude Code, Codex, Cursor+Cloud, Gemini CLI, OpenCode, Pi, Hermes+Gateway, Grok Build, Kimi Code, OpenClaw, custom process/HTTP/external adapters), sandboxing, integrations + MCP servers, SSO/GRC/RBAC/cost, privacy, personal+shared connections, run history/opt-in tracing.

Heartbeat model: trigger → adapter invocation → agent process → Paperclip API calls → result capture → run record. Timer heartbeats OFF by default; @-mention does not wake.

## 3. Features table

| Area | Support | Notes |
|------|---------|-------|
| Org chart / roles / reporting | ✅ | CEO first hire, titles, delegation up/down chart |
| Goals → projects → tasks | ✅ | Goal ancestry passed to agents (“why” not just title) |
| Approvals / review gates | ✅ | Board approvals, execution policy, plan-version binding, hiring approval flag |
| Audit trail | ✅ | Per-run logs (commands/commits/comments/costs), activity feed, immutable log claim, decision tracking |
| Pause / resume / terminate | ✅ | 1-click pause agent or whole company; auto-pause at 100% budget |
| Budgets / cost control | ✅ | Company/agent/project scopes; 80% warn → 100% hard-stop (cancels queued+running, refuses new); per-run provider/model/tokens/cost; enforcement on *recorded* spend → overshoot possible |
| HR onboarding | ⚠️ Use-case only | No native HRIS; pattern = HR agent + checklist + policy Q&A + schedule + reminders + 30-day check-ins. Requires handbook/templates integration. |
| IT features | ✅ Partial | Workspaces (repos, git worktrees, dev/preview servers), sandbox providers (e2b/Cloudflare/Daytona/Modal/Novita/boxd/K8s), secrets manager (company + per-person, encrypted, per-agent access), SSO/RBAC/GRC (listed under Agentic OS), Docker/VPS/Fly deploy, OTel + Sentry opt-in |
| SSO / RBAC / GRC | ✅ Claimed | Listed as enterprise controls; docs: `roles-and-permissions`, `company` admin, authenticated vs trusted-local modes. Depth NOT FOUND — needs hands-on verification |
| Skills | ✅ | `SKILL.md` + references/scripts/assets; trust levels `markdown_only/assets/scripts_executables`; externals must be markdown/assets only + pinned 40-char SHA; `search_skills`/`load_skill` on native runner |
| Skills marketplace/store | ✅ Built-in + external | Bundled (issue-triage, task-planning, qa-acceptance, github-pr-workflow, wireframe…) + optional (agent-browser, release-announcement…); import GitHub/skills.sh/URL/local/scan; share scopes private/company/public_link |
| MCP consume | ✅ | Connectors page → paste URL → OAuth/key/none → per-action Allowed/Ask-first/Off → choose people+agents; Refresh on server change |
| MCP serve | ✅ Experimental | `POST /mcp/paperclip`, OAuth PKCE, scopes `paperclip:read/write/configure/offline_access`, 37 tools; enable `enablePublicMcp`, needs authenticated mode + public HTTPS URL |
| Multi-org | ✅ | One deployment, many orgs, isolated tasks/agents/permissions/history; export/import with secret scrubbing |
| Mobile | ✅ Claimed | “Monitor from phone”; `pnpm dev:mobile` :3101 proxy |
| Analytics/evals | ✅ | Costs by agent/model/project/provider/user, Finance ledger reconcile, skill test runs, agent evals |
| HRIS / payroll / ATS native | ❌ NOT FOUND | No evidence of Workday/Greenhouse/payroll connectors |

## 4. Pricing

| Item | Price |
|------|-------|
| Paperclip software license | **$0 — MIT open-source, self-hosted, no account required** |
| Managed cloud | NOT FOUND — waitlist only (`paperclip.ing/waitlist`) |
| Try-it model cost | $5–20 (own docs) |
| Active company model cost | $20–100/mo (own docs); reviewers/routines/heartbeats multiply usage |
| Hosting | ~$6–10/mo VPS (Contabo/Hetzner/DO examples); embedded Postgres default, `DATABASE_URL` for own DB; Node 24.11+, Python 3 for Claude/Codex subscription login |
| Third-party confusion | janovaai HR agent $49/$199; paperclip.gxl.ai Pro $200/mo — **not** paperclipai pricing |
| Telemetry | Anonymous, on by default; off via `PAPERCLIP_TELEMETRY_DISABLED=1` / `DO_NOT_TRACK=1` / `CI=true` / config |

Budget semantics: monthly (company/agent, reset 00:00 UTC 1st) vs lifetime (project default); warn-only vs hard-stop; resume = board raises cap or month resets.

## 5. Approval / audit (HR+IT relevance)

- Gates on external posts, spend, deploys, custom triggers; request carries context/diffs/recommendation; deny-with-note reroutes agent.
- Plan review: versioned plan docs, approval binds to revision, superseding comments invalidate stale approvals; approved plan → issue tree.
- Task lifecycle `PAP-1041…1044` example: Done / In progress / Blocked-by / In review; reviewer send-back loop.
- API: `POST /api/companies/:id/approvals {type: request_board_approval, requestedByAgentId, issueIds, payload{title,summary,recommendedAction,risks}}`; wake via `PAPERCLIP_APPROVAL_ID/STATUS`.
- CLI: `paperclipai skills …`, `paperclipai mcp login --device --url …/mcp/paperclip`, `mcp proxy`.
- IT gap: approval *of task completion* ≠ blocking arbitrary shell inside runtime; connector actions governable (Ask-first), runtime shell containment depends on Runner (experimental) vs Legacy sandbox.

## 6. MCP support (detail)

- **Consume:** any `http(s)` MCP URL; rules per action (read/write/destructive → Allowed/Ask-first/Off); Ask-first → human decision; call log; shared connection + per-person/per-agent eligibility.
- **Serve (Assistant MCP):** stateless HTTP JSON, OAuth discovery `.well-known/oauth-*`, S256 PKCE, 15-min access + rotating 30-day refresh (`offline_access`), device flow `paperclipai mcp login --device`. Tools: `paperclip_connection`, list/search/read tasks/agents/projects/skills, create/update/finish/block tasks, write docs/deliverables, pending approvals (read-only — human decides in Paperclip), agent/project/skill config (with `configure` scope), upload/download URLs, `paperclip_search_api`/`paperclip_call_api` closed catalog. No arbitrary REST.
- **Packages:** `@paperclipai/mcp-server` (stdio thin REST wrapper; `PAPERCLIP_API_URL/_KEY/_COMPANY_ID/_AGENT_ID/_RUN_ID`; tools `paperclipCheckoutIssue`, `paperclipCreateIssue`, `connections_search/request`, escape-hatch `paperclipApiRequest` limited to `/api`); community `Wizarck/paperclip-mcp` (Python, HTTP-or-stdio, 95 tools incl. wake/pause/hire/budgets/routines/decisions/attention feed — use for board-operator vs agent-inside-heartbeat).
- gh_grep verified: `paperclipCheckoutIssue` in `packages/mcp-server/src/tools.ts:524`, `PAPERCLIP_API_KEY` flow in `hermes/kimi/gemini/cursor-cloud/process` adapters.
- Context7 IDs: `/paperclipai/paperclip` (30k snippets), `/paperclipai/paperclip-docs` (7.4k), `/paperclipai/docs`, `/nousresearch/hermes-paperclip-adapter`.

## 7. Repos / docs / links

- Repo: https://github.com/paperclipai/paperclip (MIT, `LICENSE` at root)
- Templates: https://github.com/paperclipai/companies
- Hermes adapter: https://github.com/NousResearch/hermes-paperclip-adapter
- Docs home: https://docs.paperclip.ing/ · llms.txt: https://docs.paperclip.ing/llms.txt
- Product: https://paperclip.ing/ · Product overview: https://paperclip.ing/product/ · Open-source: https://paperclip.ing/product/open-source/
- Governance: https://paperclip.ing/product/governance/ · Budgets: https://paperclip.ing/product/budgets/ · MCP: https://paperclip.ing/integrations/mcp/
- Docs deep: `guides/org/agents`, `guides/org/skills`, `guides/day-to-day/approvals`, `guides/day-to-day/costs`, `guides/projects-workflow/routines`, `reference/adapters/overview`, `reference/cli/skills`, `reference/api/*`, `reference/cli/mcp`, `administration/roles-and-permissions`, `connectors/*`, `experimental/assistant-connections`
- Raw code browsed: `packages/mcp-server/README.md`, `packages/mcp-server/src/tools.ts`, `server/src/routes/costs.ts`, `skills/paperclip/SKILL.md`, `doc/PRODUCT.md`, `doc/public-mcp.md`, `ROADMAP.md`
- Community: Discord `discord.gg/paperclipai`, X `@papercliping`, awesome list `gsxdsm/awesome-paperclip`
- Third-party (not official): https://www.paperclipskills.com/marketplace, https://paperclipmarket.com/, https://www.skills.sh/paperclipai/paperclip, https://www.janovaai.com/agents/hr-onboarding-agent

## 8. Overlap vs our HR+IT copilot

| Our need | Paperclip provides | Use as-is vs build |
|----------|-------------------|--------------------|
| Ticketed onboarding/offboarding with owner + thread | Issues, checkout locks, blockers, comments, artifacts | **Adopt pattern**; build HRIS-joined templates on top |
| Human approval before offer letter / prod deploy / spend | Board approvals, execution policy, Ask-first connector actions | **Adopt**; add HR-specific triggers (offer, background check, access grant) |
| Audit “who did what, when, for how much” | Activity log, run transcripts, per-issue cost incl. sub-issues | **Adopt**; pipe to our compliance store |
| Cost guardrails per employee/agent/project | 3-scope budgets + warn/hard-stop | **Adopt**, but note overshoot caveat; add real-time pre-flight for HR/IT spend |
| Knowledge reuse (handbook, runbooks) | Skills library + versioning + evals | **Adopt**; author `hr-onboarding`, `it-provisioning`, `policy-qa` skills |
| Integrations via MCP | Consume any MCP + serve 37-tool MCP | **Adopt** for IT connectors (GitHub/Notion/Railway/custom); expose our HRIS as MCP behind Ask-first |
| Org chart + delegation | Mixed human+agent chart, CEO→team delegation | **Borrow mental model**; map to real HR reporting lines, not fictional CEO |

## 9. Gaps / what Paperclip is NOT (for us)

1. **Not HRIS/ITSM.** No native Workday/BambooHR/Greenhouse/Jira/ServiceNow sync found. HR/IT “features” are DIY agents + skills + routines, not certified connectors.
2. **Not real-time budget meter.** Hard-stop on recorded cost; in-flight runs overshoot. Do not promise exact invoice ceiling.
3. **Not a shell firewall.** Task approval ≠ tool-call policing; agent-config MCP bypasses connector rules on Legacy runner; Runner isolation experimental — verify per adapter.
4. **Assistant MCP cannot approve.** Lists pending approvals, links to Paperclip; human clicks in UI. Good for SoD, bad if we wanted agent auto-approval.
5. **Evals/memory roadmaps incomplete.** Memory/Knowledge 🟡, MAXIMIZER/queues/self-org ⚪, Desktop ⚪, BYO-ticket (Asana/Linear/Jira) ⚪.
6. **SSO/GRC depth unverified.** Marketing lists SSO/GRC/RBAC; docs only show roles/permissions + auth modes. Do not claim compliance coverage without trial.
7. **Pricing risk is model-side.** Software free, but multi-agent review loops + routines silently multiply tokens. Must ship single-task cost pilot before org-wide rollout.

*Screenshots: no static screenshots in repo (营销 site is interactive + `full-tour.webm`); references above are docs/product page links in lieu of images. No invented URLs — all links fetched or returned by search.*
