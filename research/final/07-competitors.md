# Competitor Check: Onboarding Agents / HR Bots — Why Ours Is Not Slop

**Goal:** Falsification support. Prove the space is crowded with thin wrappers, and differentiate our build (two real systems + explicit approval gate + persistent audit).

**Date:** 2026-11-22
**Queries run (8 minimum met — 11 total):**
1. `AI onboarding agent hackathon winner`
2. `HR onboarding copilot Devfolio`
3. `IT provisioning agent MCP`
4. `AI HR bot hackathon project Devpost`
5. `employee onboarding automation AI agent GitHub`
6. `Devpost onboarding assistant AI chatbot HR`
7. `hackathon judges bored generic chatbot wrapper criticism` [contradiction / failure-pattern query #1]
8. `AI onboarding demo failed thin wrapper hackathon` [contradiction / failure-pattern query #2]
9. Additional discovery via results: `AI onboarding chatbot HR guide`, `Copilot Studio employee onboarding`, `Workato Access Provisioning MCP`

> Rule: No invented entries. Every build below has a real URL returned by search. Characterizations are grounded in what the README / Devpost page itself claims.

---

## 1. Prior builds found (14 with URLs)

### A. GitHub — code-first onboarding agents

| # | Build | URL | What it actually is | Why thin vs. ours |
|---|-------|-----|---------------------|-------------------|
| 1 | **at-amine / ai-onboarding-agent** — "One prompt. 4 agents. 30 seconds." | https://github.com/at-amine/ai-onboarding-agent | Multi-agent demo: parses NL → creates Drive folders, 7 calendar meetings, 4 emails, 15-task checklist, welcome book + HTML presentation. Streamlit UI. 1 commit. | Single-system (Google Workspace only). No approval gate, no audit DB, no idempotency, no IT/HR split. Glorified script runner behind LLM parse. |
| 2 | **cynthia11fire / ai-onboarding-companion** (Google ADK) | https://github.com/cynthia11fire/ai-onboarding-companion | ADK agent for first-90-day Q&A, role clarity, socialization. Kaggle/ADK capstone. | Q&A copilot only. No provisioning actions, no approval, no audit trail, no second system. Read-only guidance. |
| 3 | **Ahmzyjazzy / HireFlow** (Kaggle ADK + MCP capstone) | https://github.com/Ahmzyjazzy/hireflow | Orchestrator + HR/IT sub-agents, MCP `employee_lookup`, `get_onboarding_checklist`, Notion search. | Closest conceptually (MCP + sub-agents) but capstone scope: mock/Notion data, no human-in-the-loop approval described, no persistent audit/proof, no real Workday/Jira/Slack writes. |
| 4 | **sanjbhat / employee-onboarding-mcp** (NewHire Journey MCP) | https://github.com/sanjbhat/employee-onboarding-mcp | MCP server with HTML-config step walkthroughs, local progress JSON, VS Code/Cline UX. | Content-walkthrough server, not provisioning. Local-file progress ≠ SQLite audit. No approval, no cross-system writes. |
| 5 | **GoogleCloudPlatform / generative-ai — new-hire-onboarding** (official ADK sample) | https://github.com/GoogleCloudPlatform/generative-ai/tree/main/agents/adk/new-hire-onboarding | Long-running ReAct + enum state machine, pause/resume demo with HR command-center + employee portal UI. | Reference sample by design. State machine is exemplary, but demo-local artifacts, no real HRIS/IT connectors, no approval policy engine, no metrics/coverage gate. Tutorial, not production pilot. |
| 6 | **gspain89 / crewai-hr-onboarding-cua-agent** (CrewAI + CUA vision) | https://github.com/gspain89/crewai-hr-onboarding-cua-agent | CrewAI 3-agent sequence + MS-FARA 7B vision + Playwright clicking an HR web UI, CSV ingest, email sender. 0 stars, 2 commits. | Browser-click automation ≠ governed provisioning. No APIs, no approval, no audit, brittle vision clicking. Impressive stunt, zero governance. |
| 7 | **Harini-V06 / Onboarding-workflow** (Grok + Gmail) | https://github.com/Harini-V06/Onboarding-workflow | Generates welcome email via Grok, builds Calendar link, sends via SMTP. 3-layer directives pattern. | Single email + calendar link. No HRIS, no IT tickets, no approval, no audit. Literally one LLM call + SMTP. |
| 8 | **saralabiswal / agentic-hr-onboarding-mcp** — Workday/Jira/Slack/Salesforce | https://github.com/saralabiswal/agentic-hr-onboarding-mcp | Guided intake UI, Workday/Jira/Slack/Salesforce agents, MCP-style boundaries, SQLite audit, dry-run mode, Prometheus metrics, 80% CI gate. | Strongest prior — only one with SQLite audit + dry-run + idempotency guards. Differentiator for us must be: live two-system execution with explicit human approval persisted (not just demo mode default) + evidence cards with record IDs/URLs. If we ship that, we beat it on depth. |
| 9 | **Buddyb419 / n8n-AI-Powered-Onboarding-Orchestrator** | https://github.com/Buddyb419/n8n-AI-Powered-Onboarding-Orchestrator | Single n8n workflow: form → Gemini personalized email → Sheets roster + checklist → Slack announce. | No-code wrapper. Google Sheets as DB, no approval, no IT provisioning, no audit beyond Slack alert. |
| 10 | **jhonkomar / n8n-employee-onboarding-automation** (BambooHR) | https://github.com/jhonkomar/n8n-employee-onboarding-automation | Polls BambooHR every 15 min → welcome email + orientation event + buddy notify + manager check-in. | Deterministic n8n IFTTT, AI barely present. Hardcoded role→tools map; unknown role = email HR and stop. No LLM reasoning, no approval flow, no audit. |

### B. Devpost / hackathon builds

| # | Build | URL | What it actually is | Why thin vs. ours |
|---|-------|-----|---------------------|-------------------|
| 11 | **OnboardIQ** (Airia AI Agents Hackathon) — 5 agents, HITL, Knowledge Graph | https://devpost.com/software/onboardiq-tuqsae | Orchestrator + compliance validator (7 countries) + HITL checkpoint + 4 parallel sub-agents (email, IT ticket, docs, calendar) + Apache AGE graph. Claims <$0.01/run. | Best hackathon comp: *does* have HITL. But: Airia-hosted workflow, "What's next" admits no real HRIS (Workday/BambooHR), no real Okta/Azure AD provisioning, DocuSign missing. Knowledge-graph write is the audit — not tamper-evident log + metrics. Ours wins if both systems are real/dry-run-explicit with stored proof. |
| 12 | **HR Setu** (Cloud Run Hackathon, ADK + Gemini) | https://devpost.com/software/to-be-changed-vzxaqw | Multi-agent: policy processor + workflow/action + conversational agent, Pub/Sub + Firestore. | Policy Q&A + leave reminders. No provisioning connectors, no approval gate described, no audit evidence. Classic multi-agent chatbot. |
| 13 | **HR Virtual Assistant with AI** (TiDB + Fetch AI hackathons) | https://devpost.com/software/hr-virtual-assistant-with-ai | NL→SQL over SQLite dummy (Faker) employee data via Gemini + Streamlit. Demo video `youtu.be/GN_zE5FG-oo`. | Textbook wrapper: Faker data, single NL→SQL call. No actions, no approval, no audit, no systems. |
| 14 | **Dudebot / AI onboarding assistant** (Salesforce Agentforce / Einstein Bots) | https://devpost.com/software/dudebot-your-onboarding-buddy ; https://devpost.com/software/ai-onboarding-assistant | RAG over HR PDFs in Data Cloud, Einstein GPT answers with citations; Flow variant fetches tasks. | Platform-locked Q&A. Zero-code is the selling point — i.e., no custom provisioning, no cross-system orchestration, no approval policy, no external audit. |

### C. Commercial / platform references (prove pattern, not counted in 14)

- **Workato Access Provisioning MCP Server** — https://marketplace.workato.com/en/product/access-provisioning-process-mcp-server — *does* gate every write behind human approval and auto-provisions Okta/Entra/Google. Validates our thesis; ours is the hackathon-buildable mini-version of this enterprise pattern.
- **Rajeev Pentyala: Copilot Studio — Build an Agent to Automate Employee Onboarding** — https://rajeevpentyala.com/2026/08/05/copilot-studio-build-an-agent-to-automate-employee-onboarding — Welcome email + Teams + SharePoint row. Single-ecosystem (M365), no approval/audit.
- **Luxapps AI HR onboarding copilot (Luxembourg)** — https://luxapps.lu/en/actualites/ai-hr-onboarding-copilot-luxembourg — Explicitly "proposed, commented, approved" with CNPD controls. Supports our framing: approval + traceability is what separates demo from deployable.
- **LookBook365 New Hire Onboarding Copilot (SharePoint)** — https://lookbook365.com/new-hire-onboarding-copilot-sharepoint — Read-only Q&A scoped to onboarding folder. No writes at all.
- **IBM Storage Scale Provisioning Agent** — https://community.ibm.com/community/user/blogs/dhananjay-sonawane/2026/02/17/ibm-storage-scale-provisioning-agent — MCP + human-in-loop confirmation before fileset ops. Infra-provisioning analogue proving approval-gate is expected pattern.

---

## 2. Contradiction queries — judges ARE bored of wrappers (evidence we must design against)

**Query 7 results:**
- r/csMajors: *"Why do hackathons == chat wrapper competition?"* — "just a React chat wrapper with no backend… written using the very same AI it uses" — https://www.reddit.com/r/csMajors/comments/1fsxmdv/why_do_hackathons_chat_wrapper_competition
- HackerNews `Ask HN: Are hackathons still worth doing?` — "The winning project? A slick UI wrapped around a basic LLM API call" / "vibeathons" — https://news.ycombinator.com/item?id=47077312
- HackerEarth 2026 ideas guide: *"Since GPT-4's release… judges have reported that generic LLM demos no longer stand out… If your only AI use is 'we call OpenAI,' rethink the idea."* — https://www.hackerearth.com/blog/hackathon-ideas
- Pranjul Rathour judge's checklist: *"Is the inference real? Did they evaluate anything? How does it fail? Where does the data go?"* + *"Some of the weakest bolt a chatbot onto a problem that needed a form."* — https://pranjulrathour.scult.in/blog/judging-ai-hackathon-projects-what-to-check
- Devfolio / Push to Prod: *"It can notice that a team claimed a custom model and shipped a wrapper… that a README describes a backend the repo does not contain."* — https://devfolio.co/blog/the-discerning-machine

**Query 8 results:**
- Jarrad Bermingham, *The Wrapper Trap*: single `openai.chat.completions.create()` with "no evaluation, no pipeline, no data integration" — https://dev.to/jarradbermingham/the-wrapper-trap-why-most-enterprise-ai-projects-fail-before-they-start-2nla
- Data#3 marketing-agent hackathon: *"a good demo is not enough… what happens when sources disagree, permissions are too broad"* — scoring rewarded controls over prompt tweaks — https://www.data3.com/knowledge-centre/blog/a-good-demo-is-not-enough-what-a-marketing-agent-hackathon-exposed
- GAR-LCIA hackathon judges: losers were *"just prompts on an existing LLM or LLM wrapper… 'over simple… not much beyond a prompt in Gemini'"* — https://globalarbitrationreview.com/article/what-ideas-emerged-the-gar-lcia-hackathon
- Sea × OpenAI Codex winner reflection: *"Agents that sit inside real workflows, not wrappers floating on top of them"* — https://kpriyadharshan.medium.com/two-of-our-three-demos-failed-live-we-still-placed-third-d42796137fa5

**Takeaway:** Judges explicitly punish what 11 of 14 builds above do. Our defense must be demo-legible in 90 seconds: show the approval pause + the audit proof, not just chat.

---

## 3. Why ours is NOT slop — falsifiable differentiators

| Dimension | Typical prior (11/14) | Ours (must demo) |
|-----------|----------------------|------------------|
| **Systems touched** | One (Gmail *or* Sheets *or* Notion *or* SharePoint) or zero (Faker/SQLite dummy) | **Two real boundaries**: HRIS/people record **and** IT/work system (e.g., Workday-mock + Jira/Slack/Salesforce-style connectors), each with explicit mode |
| **Approval** | None, or inline "LLM decides" | **Explicit human gate**: workflow pauses, HR clicks approve, decision + approver + timestamp persisted; no silent auto-provision |
| **Audit** | None, or chat log, or Sheets row | **Append-only SQLite audit log** (who/what/when/mode/idempotency key) + evidence cards with record IDs, connector mode, stored URLs — queryable after demo |
| **Safety** | Live keys or fully mocked with no label | **Demo vs Production mode switch**, dry-run default, idempotency guards (no duplicate tickets on retry), 80%+ CI gate |
| **Eval** | "Tested on a few examples" / no failures shown | Show 1 failure case (e.g., unknown role → HR alert + stop, duplicate retry → deduped) — per judge checklist |

If a judge asks "isn't this another wrapper?", answer: kill the network and show the audit DB still proves what happened; ask Harini-V06 or HR-Virtual-Assistant to do the same — they can't, because there is no DB.

---

## 4. Verdict

Space is saturated with Q&A chatbots and single-workflow email senders (OnboardIQ and saralabiswal's build excepted as serious attempts, both still admitting mock/no-real-HRIS gaps). **None combines two-system orchestration + blocking human approval + queryable audit + dry-run/idempotency in one runnable pilot.** That combination is our moat for judging. Lead the demo with the pause (approval) and the proof (audit row), not the chat.
