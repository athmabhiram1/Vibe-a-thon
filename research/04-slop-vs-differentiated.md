# Slop vs. Differentiated: What Hackathon AI Projects Are Saturated (2025–2026)

**Purpose:** Evidence-based map of what to AVOID (judges have seen it 100×) and where white-space remains for a Synapse-CLI + MCP-server hackathon (tracks: legacy app agent-ready, one composite tool from many functions, copilot across two systems, open innovation).
**Date:** 2026-11-22. All links verified at research time. Anything labelled **[Inference]** is interpretation, not a quoted fact.

---

## TL;DR for team

- **Do NOT build:** RAG-over-PDFs chatbot, resume/job matcher, generic study-buddy/flashcards, symptom checker, sentiment dashboard, AI meeting-notes summariser, AI code reviewer, appointment-booking agent, chatbot-for-a-website, generic CRM copilot. These are explicitly banned or called out as boring in 2025–2026 hackathons.
- **What actually won in MCP/agent tracks:** safety/governance middleware, legacy-code moderniser, vehicle/OT diagnostics via embedded MCP, Kubernetes-native MCP governance, clinical MCP federation over MIMIC-IV, data-lineage-grounded incident response (DataHub Blackbox). Common thread: **real system + read→reason→act→write-back**, not chat.
- **Highest-signal white-space for Synapse:** regulated/legacy systems where integration is genuinely hard: municipal e-governance file workflows, insurance claims adjudication, HL7/FHIR hospital ops, EDI supply-chain, telecom OSS/BSS trouble-ticketing, air-gapped/on-prem ERP (ERPNext/Odoo). All demo-feasible with open-source sample codebases (table in §4).

---

## (a) Saturated archetype table — with evidence

| # | Saturated archetype ("AI slop") | How many instances / where seen | Why judges are tired | Evidence links |
|---|---|---|---|---|
| 1 | **RAG chatbot over PDFs/docs** ("upload PDF, ask questions") | Qdrant explicitly banned pure chatbots in 2025 + 2026 "Think Outside the Bot" hackathons (>10k prizes, global); TiDB AgentX 2025 page says "last year's event saw thousands of developers build simple RAG demos. This year, we want multi-step agents"; LlamaIndex ran "Agentic RAG-a-thon 2" to push *beyond basic chatbots*; tutorial sites list "PDF Chatbot (RAG)" as the #1 cookie-cutter resume project | Indistinguishable from ChatGPT; no workflow, no action; "ChatGPT can do this" judge rejection | [Qdrant Think Outside the Bot 2026 — "no chatbots allowed"](https://try.qdrant.tech/hackathon-vsd), [Qdrant 2025 winners — "beyond simple RAG chatbots"](https://qdrant.tech/blog/vector-space-hackathon-winners-2025), [TiDB AgentX 2025 — "thousands of simple RAG demos"](https://tidb-2025-hackathon.devpost.com), [LlamaIndex Agentic RAG-a-thon 2 winners](https://www.llamaindex.ai/blog/agentic-rag-a-thon-2-winners-and-recap), [MicroDegree "5 GenAI projects" — PDF Chatbot as cliché](https://www.instagram.com/reel/DbueIymzT2r) |
| 2 | **Resume matcher / job-application agent / ATS scorer** | Listed as Project #1 "AI Job Application Agent" in 2026 hackathon-idea roundups; Agno Global Agent Hackathon 2025 had *three* separate job-hunting winners (Launch Job Orbit, SmartApply, Flow); HackerEarth notes "ATS integration, no audit trail" problem | Zero defensibility; every cohort builds one; Händler signal eroded; privacy/compliance hand-waving | [NextAgile 2026 hackathon ideas — Job Application Agent #1](https://nextagile.ai/blogs/gen-ai/top-hackathon-project-ideas), [Agno Global Agent Hackathon winners — 3 job agents](https://www.agno.com/blog/global-agent-hackathon-winners) |
| 3 | **AI study buddy / flashcard generator / lecture summariser** | Devpost Multimodal Agents gallery: "Studdybuddy… quiz cards"; UC Berkeley AI Hackathon 2025 gallery: "offline AI tutor"; TreeHacks 2025 grand prize HiveMind (Zoom learning tool); Instagram resume lists rank "AI Study Buddy" 5/10 difficulty commodity | Feels like a feature, not a product; no hard integration; judges: "I've seen a gazillion times before" | [Devpost Multimodal Agents gallery — Studdybuddy](https://multimodal-ai-agents.devpost.com/project-gallery), [UC Berkeley AI Hackathon 2025 gallery](https://uc-berkeley-ai-hackathon-2025.devpost.com/project-gallery), [TreeHacks 2025 HiveMind grand prize](https://americansouthasiannetwork.com/pulse/samarth-shiramshetty-wins-grand-prize-at-stanford-treehacks-2025) |
| 4 | **Medical symptom checker / generic health chatbot** | Sarvam/Meta Llama hackathon 1st place CurePharmaAI (rural health) + countless symptom-checker submissions; Devfolio "AI for India" lists health as most crowded track; symptom checkers appear in nearly every Devpost AI gallery sampled | Unsafe without grounding; judges now demand FHIR/evidence grounding, not free-text diagnosis | [Sarvam/Llama hackathon — CurePharmaAI 1st](https://www.linkedin.com/posts/sarvam-ai_highlights-from-the-first-ever-llama-hackathon-activity-7264263136243830578-KeS), [AI for India Hackathon winners](https://www.instagram.com/p/DKuQTXiShUS) |
| 5 | **Sentiment dashboard / customer-review analyser** | Bosscoder/Instagram "Most AI projects look the same: chatbot, sentiment model"; Devpost front page: "Insightify… review response generation"; 2025 AI DevSummit gallery full of review analysers | 2018-era ML relabelled as GenAI; no agent action | [Bosscoder — "same chatbot, sentiment model"](https://www.instagram.com/reel/DY_-eCBxxam), [Devpost software listing — Insightify](https://devpost.com/software) |
| 6 | **AI meeting-notes summariser / action-item extractor** | Agno winner "Agent Transponder — meeting-to-CRM pipeline"; YouTube resume lists rank "AI Meeting Copilot" as commodity tutorial (#1 of top-5); dozens of Devpost clones | Solved by Granola/Otter/Fireflies; demo is just a transcript + bullet list | [Awesome hackathon winners — Agent Transponder](https://github.com/unicorn-mafia/awesome-hackathon-winners), [Top-5 AI resume projects — Meeting Copilot](https://www.instagram.com/reel/DcL-YjITEj2) |
| 7 | **AI code reviewer / generic coding assistant** | Anthropic×Forum Ventures NYC Sept 2025 winner was a 60-agent/232-skill harness — but judges stressed *scoped* agents with evals, not another "review my PR" bot; TreeHacks 2026 "Git Police" etc. | Marginal vs. Copilot/Cursor; no evals, no repo grounding | [Anthropic hackathon winner harness breakdown](https://www.youtube.com/watch?v=aY8XuxRbIsU), [TreeHacks 2026 gallery](https://treehacks-2026.devpost.com/project-gallery) |
| 8 | **"Agent that books appointments" / generic booking bot** | Appears in every "50 hackathon ideas" listicle; Devpost AI galleries 2024–2026 saturated; HackerEarth explicitly: "If your only AI use is 'we call OpenAI,' rethink" | Thin wrapper over Calendly API; GSA 2026 rubric explicitly rejects "thin wrapper around a single REST call" | [HackerEarth 2026 — "AI is table stakes"](https://www.hackerearth.com/blog/hackathon-ideas), [GSA MCP hackathon — "not a thin wrapper"](https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon) |
| 9 | **Chatbot-for-a-website / customer-support widget** | Scalingo hackathon "AI assistant with MCP, RAG & OpenSearch" is the *charitable* version — most entries are just docs-chat; Chrome Built-in AI 2025 gallery: "Free AI Sidebar Chatbot in any site" | No state change; judges ask "what can it DO?" | [Scalingo MCP+RAG assistant writeup](https://scalingo.com/blog/hackathon-projects-1-building-an-ai-assistant-with-mcp-rag-opensearch), [Chrome Built-in AI 2025 gallery](https://googlechromeai2025.devpost.com/project-gallery) |
| 10 | **Generic CRM copilot / sales outreach blaster** | LlamaIndex RAG-a-thon winner "Timeline of You" succeeded *because* it generated O-1 visa packets (concrete artefact), while dozens of SDR-spam clones failed; Agno "Superwizard" won by doing real browser clicks, not drafts | Spam cannon; no permissioning, no audit; judges reward artefacts + actions | [LlamaIndex RAG-a-thon winners — Timeline of You](https://www.llamaindex.ai/blog/agentic-rag-a-thon-2-winners-and-recap), [Agno winners — Superwizard browser actions](https://www.agno.com/blog/global-agent-hackathon-winners) |
| 11 | **Crypto memecoin trader / "AgentZero trading"** | TreeHacks 2025 "AgentZero… trading"; Hack&Roll 2025 "AlphaBot… memecoin"; Devpost crypto-agent glut | Demo is a PnL chart; no verifiability; judges flag as gambling | [TreeHacks 2025 gallery — AgentZero](https://treehacks-2025.devpost.com/project-gallery), [Hack&Roll 2025 — AlphaBot](https://hacknroll2025.devpost.com/project-gallery) |

**[Inference]** Count method: gallery sampling (Devpost project galleries show 24–54 entries each; 30–60% match rows 1–10), plus explicit organiser statements that RAG-chatbot submissions numbered in the "thousands" (TiDB) and were then banned (Qdrant).

---

## (b) Judge-fatigue quotes — with links

1. **Qdrant (sponsor + organiser), 2025 & 2026:** "Think Outside the Bot… **Forget the classical RAG chatbot!** … submissions that are **only chatbots are not allowed**." — The strongest possible signal: a vector-DB vendor tired of chatbot demos on its own product.
   - Links: [2026 rules](https://try.qdrant.tech/hackathon-vsd), [2025 winners recap](https://qdrant.tech/blog/vector-space-hackathon-winners-2025)

2. **TiDB AgentX Hackathon 2025 (Devpost):** "Last year's event saw **thousands of developers build simple RAG demos**. This year, we want **multi-step AI agents that demonstrate real-world workflows**."
   - Link: [TiDB AgentX 2025](https://tidb-2025-hackathon.devpost.com)

3. **Qdrant "How They Built It" webinar (Oct 2025):** "A challenge to build an application that was **beyond a RAG chatbot. We see a lot of vector search used for RAG chatbots**… how do you do something **beyond just a RAG chatbot or conversational interface**?"
   - Link: [YouTube — How They Built It](https://www.youtube.com/watch?v=n1nKqhm-WuA)

4. **HackerEarth Hackathon Ideas 2026 (organiser guidance):** "**AI is table stakes, not a differentiator. Judges have seen a hundred GPT wrappers.** Projects that use agentic workflows, RAG, or multimodal models to solve a specific problem beat projects that bolt an LLM onto a generic app. **If your only AI use is 'we call OpenAI,' rethink the idea.**"
   - Link: [HackerEarth](https://www.hackerearth.com/blog/hackathon-ideas)

5. **Devpost judges (Joe Holmes + Darlyze Calixte), "What Do Hackathon Judges Look For?":** Innovation criterion = "**Is this just something I've seen a gazillion times before?** … put your own unique fingerprint on it as opposed to looking like everyone else's AI generated app."
   - Link: [YouTube — 5 Live AI App Reviews](https://www.youtube.com/watch?v=Xh8Ie_VuA_0)

6. **Devpost judge Maria (via Devpost blog "How to win a hackathon"):** "If I see **the same project with a different label** or slightly different interface, it looks like they are just looking for a problem for their solution — **that could be a red flag**."
   - Link: [Devpost — Advice from 5 seasoned judges](https://info.devpost.com/blog/hackathon-judging-tips)

7. **JetBrains + OpenAI judges (June 2026, "Notes From the Judging Table"):** Bonnie Xu (OpenAI): "**Don't start with 'what's the coolest new tool I can use?'** but with 'what's something I can build now that I probably couldn't have built before?' Build from the annoyance." Colin: "**Visualise yourself winning and work backwards**… every second of the demo should earn its place."
   - Link: [JetBrains blog](https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table)

8. **GSA (US Government) MCP + SI Agent Hackathon rubric, Sept–Nov 2026:** "Judges will look for evidence that **each tool represents a real agent-facing action, not a thin wrapper around a single REST call**… designing tools around meaningful user goals rather than mirroring underlying API endpoints."
   - Link: [GSA hackathon](https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon)

9. **Reddit r/LangChain hackathon post (2025):** "The judges said '**ChatGPT can do this**. If the demo just shows a text output that looks similar to what ChatGPT would produce, judges literally [ding you].'"
   - Link: [Reddit thread](https://www.reddit.com/r/LangChain/comments/1re3mp7/i_built_a_graphrag_travel_engine_in_24h_hackathon)

10. **HackerNoon "From the Judge's Seat" (2025):** "What stands out today is **not who used AI the most, but who used it with purpose**… **don't outsource the most human parts** of a hackathon to machines."
    - Link: [HackerNoon](https://hackernoon.com/from-the-judges-seat-standing-out-in-hackathons-in-the-age-of-ai)

11. **Reddit r/csMajors (2024–2025, still cited):** "Why do hackathons == **chat wrapper competition**? … just a React chat wrapper with no backend and the only dynamic content is the response from the AI."
    - Link: [Reddit](https://www.reddit.com/r/csMajors/comments/1fsxmdv/why_do_hackathons_chat_wrapper_competition)

12. **All Things Agentic Hackathon judging Q&A (Devpost Build Session, $180k prizes):** Judges distinguish "**agentic vs. just a chatbot with memory**… if you just use it as a chatbot that will be less attractive to our judges."
    - Link: [YouTube — Judging Criteria Live Q&A](https://www.youtube.com/watch?v=DCXjvKmUIGY)

---

## (c) What WON in MCP / agent-tooling (2025–2026) — and why

These are the anti-slop exemplars. Note the pattern: every winner touches a **real system of record**, enforces **safety/policy**, and demos **read → reason → act → write-back**.

### 1. MCP 1st Birthday Hackathon (Anthropic + Gradio + OpenAI, 7,200 builders, Nov 2025)
Source: [Gradio winners page](https://gradio.app/mcp-birthday-winners), [LinkedIn announcement](https://www.linkedin.com/posts/gradio_announcing-the-first-winners-of-mcps-activity-7406475265473802240-vR-T)

| Winner | What it did | Why it stood out **[Inference]** |
|---|---|---|
| **Cite-Before-Act MCP** (Best Overall) | Human-in-the-loop safety middleware: require explicit approval before state-mutating MCP operations | Solved the #1 enterprise MCP objection (tool poisoning / destructive writes). Judges love safety rails because every other demo ignores them |
| **MCEPTION** (Best Enterprise) | MCP server that creates and deploys *other* MCP servers on Hugging Face Spaces | Meta-tooling: judges reward "picks-and-shovels" over one more chatbot |
| **Portfolio Intelligence Platform** (Best Consumer) | Multi-agent portfolio analysis with transparent orchestration | Multi-agent with *visible* planning trace, not black-box chat |
| **Legacy Code Modernizer** (Modal Innovation Award) | Autonomous agent that modernises legacy codebases via MCP tools (planning → reasoning → execution) | Directly maps to your "legacy app agent-ready" track; proved legacy+MCP wins prizes |
| **Vehicle Diagnostic Assistant** (Track 2 Enterprise 🥇) | Agent connects to car via embedded MCP server for real-time diagnostics | Physical-world grounding; live sensor data, not canned docs |
| **FleetMind AI Agent** (Track 2) | Fleet telemetry agent | Same: OT/IoT data + action |
| **Game Context Protocol** (Best Creative) | Natural-language 3D scene/game generation | Creative track rewards novel modality, not text |

### 2. Solo.io MCP & AI Agents Hackathon 2026 (Feb–Apr 2026, judges incl. Kelsey Hightower)
Source: [Solo.io winners blog](https://www.solo.io/blog/celebrating-the-winners-of-the-2026-hackathon-for-mcp-ai-agents), [hackathon site](https://aihackathon.dev)

| Winner | What it did | Why it stood out |
|---|---|---|
| **AI-Powered K8s-native governance for MCP** (Huzefa Hamdard, track winner) | Monitors agentgateway/kagent, scores MCP-server security posture, AI risk analysis via Gemini/Ollama | Governance + policy at the protocol layer — enterprise buyer pain |
| **MCP.STORE** (runner-up, Mehmet Hilmi Emel) | Full-stack e-commerce proving MCP auth (Keycloak JWT + CEL rules enforced so agents *cannot bypass* security) | AuthN/Z done right; judges explicitly praised "cannot bypass" |
| **Clinical AI agent platform** (runner-up, Oswaldo Gomez) | Federates multiple MCP servers into one endpoint to query **MIMIC-IV** clinical data from IDEs | Real regulated dataset (MIMIC-IV requires credentialing) + federation pattern = exactly your "composite tool" track |
| **agentgateway → identity-aware control plane** (Kevin Cao et al., 9 PRs) | Turned proxy into identity-aware control plane: identity at edge, OTel tracing, multi-model | Open-source contribution depth beat demo flash |

### 3. DataHub "Build with DataHub: The Agent Hackathon" 2026 (600+ projects, $20.5k)
Source: [DataHub winners blog](https://datahub.com/blog/meet-the-winners-of-build-with-datahub-the-agent-hackathon), [Blackbox README](https://github.com/alejandro-publius/blackbox-datahub/blob/main/README.md)

- **Grand prize: Blackbox** — "revenue just jumped, is this real?" → reads lineage, proves root cause against a **machine-enforced evidence gate**, repairs transform code, runs invariant suite, opens PR for human, writes incident back to catalog. Anti-slop because the agent *cannot* invent a root cause without citing lineage evidence (unit-tested rejection paths).
- Pattern across all 7 winners: **"read real context, act on it, write the result back"** on a running DataHub instance — not mocked schemas in a prompt.

### 4. Others worth citing
- **MariaDB AI RAG Hackathon (May 2025):** Integration-track winner was **MCP itself** — judges picked protocol plumbing over another RAG demo. ([MariaDB blog](https://mariadb.org/model-context-protocol-mcp-hackathon-integration-track-winner))
- **Unstructured MCP Hackathon (Apr 2025):** winners DarajaMCP + research-paper structuring MCP (Drive → structured outputs → MongoDB). Won on *tutorial + reusable pipeline*, not chat. ([Recap](https://unstructured.io/blog/unstructured-mcp-hackathon-recap))
- **Browser Use × YC Web Agents Hackathon (Feb 2025, $180k, 78 submissions):** winner **Browser Brawl** — arena where two agents compete on live sites, generating adversarial evaluation traces. Won by producing *evals*, not just automation. ([MiniMax recap](https://www.minimax.io/news/minimax-ycombinator-hackathon-building-the-future-of-agents), [HackHQ case study](https://hackhq.io/customers/browser-use-hackathon))
- **Sarvam BuildIn' Hours (Bengaluru, 2025, 6,272 applied / 100 in):** winners were *concrete Bharat problems*: MSME tender discovery, Indic kids storytelling, non-verbal communication board (Setu). Judges: "solving practical problems for Indian users." ([IT Voice](https://www.itvoice.in/zo-house-bengaluru-hosts-sarvam-ais-buildin-hours-hackathon-6272-applied-in-48-hours-100-got-in))

---

## (d) Under-explored territory — scored for Synapse hackathon

Scoring: 1–5 each. **Nov** = novelty (have judges seen it?); **Demo** = feasible in hackathon timeframe; **Syn** = Synapse centrality (does "CLI generates MCP from existing codebase" shine?); **Val** = real-world value. **Total /20.**

| # | Domain | Why it's hard (and therefore defensible) | Demo feasibility + public sample codebase | Nov | Demo | Syn | Val | Tot |
|---|---|---|---|---|---|---|---|---|
| 1 | **Municipal e-governance file workflow** (building permits, grievance redressal, tender discovery) | Multi-department approvals, paper→digital gaps, vernacular docs, audit trail required; Sarvam winner proved judges love MSME-tender + civic-fix | **High.** Clone a file-tracking Django app or use [OpenG2P](https://github.com/openg2p) / DIGIT urban-stack samples; seed with 200 synthetic applications; Synapse generates MCP (search_file, advance_stage, flag_missing_doc); copilot spans citizen portal + officer dashboard | 5 | 5 | 5 | 5 | **20** |
| 2 | **Insurance claims adjudication** | Policy exclusions, fraud checks, regulated payout rails, explanation-of-benefit artefacts; can't fake with a chatbot | **High.** Use synthetic FHIR Claim resources ([HL7 FHIR R5 Claim](https://hl7.org/fhir)) + open-source [OpenIMIS](https://github.com/openimis) (insurance management); composite tool `adjudicate_claim` fuses eligibility + fraud-score + payout-estimate | 5 | 4 | 5 | 5 | **19** |
| 3 | **Hospital ops on HL7/FHIR (not diagnosis)** — bed management, discharge summaries, lab-result routing | HL7v2 pipe-delimited + FHIR R4/R5 version skew, SMART-on-FHIR auth, compartment scoping; Solo.io clinical-MIMIC winner validates appetite | **High.** [HAPI FHIR JPA Starter](https://github.com/hapifhir/hapi-fhir) (`docker compose up` + Postgres) + [OpenMRS 3](https://github.com/openmrs) / [OpenELIS Global](https://github.com/topics/fhir); load MIMIC-IV demo or synthetic patients; MCP tools: `find_bed`, `route_lab`, `draft_discharge` | 4 | 5 | 5 | 5 | **19** |
| 4 | **EDI / supply-chain order-to-cash** (X12/EDIFACT orders, ASN, invoices) | Cryptic segment syntax (ISA*GS*ST…), partner-specific dialects, idempotency, reconciliation; almost no hackathon team touches it | **Medium-high.** Use [Apache OFBiz](https://github.com/apache/ofbiz-framework) or ERPNext stock module + synthetic X12 850/810 files; python `pyx12` parser; composite tool `reconcile_shipment` (EDI parse + inventory check + invoice draft) | 5 | 4 | 5 | 5 | **19** |
| 5 | **On-prem / air-gapped ERP back-office** (inventory, GST invoicing, MRP) | No cloud webhooks, MariaDB/Postgres on intranet, role-based ledgers, Tally-style compliance; "agent-ready" means read-only-safe tools | **High.** [ERPNext](https://github.com/frappe/erpnext) (100% GPL, Frappe Cloud/Docker) or [Odoo Community](https://github.com/odoo/odoo) (LGPL, Postgres); run via Docker, Synapse points at Python codebase; demo: "why is item X short?" → stock-ledger trace + PO draft | 4 | 5 | 5 | 4 | **18** |
| 6 | **Telecom OSS/BSS trouble-ticketing** (network alarms → customer tickets → field dispatch) | TM Forum SID/eTOM models, alarm storms, SLA penalties, GIS dispatch; genuinely multi-system (NMS + CRM + workforce) | **Medium.** Use [OpenNMS](https://github.com/OpenNMS/opennms) or synthetic alarm feed + ERPNext HR/task module as second system; copilot correlates alarm burst → affected subscribers → dispatch plan | 5 | 3 | 5 | 5 | **18** |
| 7 | **Legacy mainframe / COBOL batch modernisation** (JCL, copybooks, VSAM) | Retiring SME knowledge, JCL/batch semantics, EBCDIC, no tests; 74% of modernisation projects fail (OpenHands whitepaper) | **Medium.** [Azure-Samples Legacy-Modernization-Agents](https://github.com/Azure-Samples/Legacy-Modernization-Agents) ships sample COBOL+JCL (`CUSTOMER.cbl`, `NIGHTLY.jcl`); Synapse generates MCP (explain_paragraph, map_copybook, convert_to_java); but COBOL-in-a-weekend risks "slideware" perception | 4 | 3 | 5 | 5 | **17** |
| 8 | **Industrial/OT + fleet diagnostics** (vehicle CAN, SCADA alarms) | Embedded MCP, real-time streams, safety interlocks; Vehicle Diagnostic Assistant already won once (novelty slightly reduced) | **Medium.** Simulate CAN stream or use OpenELIS/vehicle CSV; MCP server on edge; cite-before-act approval for actuations | 3 | 3 | 4 | 5 | **15** |

**Recommended shortlist for this hackathon [Inference]:**
1. **Municipal file workflow (#1)** — easiest emotional win with judges, maps to all four tracks, trivially demoable, and Sarvam/CivicFix precedent proves it wins in India tracks.
2. **Insurance adjudication (#2) or FHIR hospital ops (#3)** — if you want regulated gravitas and a "composite tool from many functions" story (`adjudicate_claim` / `discharge_patient` fusing 5–8 functions with policy gates).
3. **EDI reconciliation (#4)** — maximum novelty; almost nobody will build it; Synapse's "many functions → one tool" narrative is cleanest here.

**What to avoid even in these domains:** free-text diagnosis, generic "ask your policy docs" chat, or a dashboard with no write-back. Every demo must end with a **state change + audit record** (file advanced, claim adjudicated, bed assigned, PO drafted) gated by an approval step — i.e., copy the Cite-Before-Act + Blackbox evidence-gate pattern.

---

## Sources (core)

- Gradio MCP Birthday winners: https://gradio.app/mcp-birthday-winners
- Solo.io 2026 MCP winners: https://www.solo.io/blog/celebrating-the-winners-of-the-2026-hackathon-for-mcp-ai-agents
- DataHub agent hackathon winners: https://datahub.com/blog/meet-the-winners-of-build-with-datahub-the-agent-hackathon
- Qdrant Think Outside the Bot 2026: https://try.qdrant.tech/hackathon-vsd
- TiDB AgentX 2025: https://tidb-2025-hackathon.devpost.com
- GSA MCP hackathon rubric: https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon
- JetBrains judging-table notes: https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table
- Devpost judging tips: https://info.devpost.com/blog/hackathon-judging-tips
- HackerNoon judge's seat: https://hackernoon.com/from-the-judges-seat-standing-out-in-hackathons-in-the-age-of-ai
- HackerEarth 2026 ideas: https://www.hackerearth.com/blog/hackathon-ideas
- YC Browser Use hackathon: https://hackhq.io/customers/browser-use-hackathon / https://www.minimax.io/news/minimax-ycombinator-hackathon-building-the-future-of-agents
- Sarvam BuildIn' Hours: https://www.itvoice.in/zo-house-bengaluru-hosts-sarvam-ais-buildin-hours-hackathon-6272-applied-in-48-hours-100-got-in
- Sample codebases: ERPNext https://github.com/frappe/erpnext, Odoo https://github.com/odoo/odoo, HAPI FHIR https://github.com/hapifhir/hapi-fhir, Legacy-Modernization-Agents https://github.com/Azure-Samples/Legacy-Modernization-Agents
