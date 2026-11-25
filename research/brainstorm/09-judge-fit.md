# 09 — Judge-Fit Scoring: Kill the Slop, Pick the Winner

**Date:** 2026-11-22 · **Status:** `research/brainstorm/` contained **zero files** at scoring time — so this scores the de-facto idea pool: the 8 under-explored domains from `research/04-slop-vs-differentiated.md §(d)` (the only evidence-backed candidate set). If separate brainstorm docs land later, re-score them against this same rubric.
**Inputs:** `research/04-slop-vs-differentiated.md` (full read), `research/01-2nd-brain-labs.md`, `research/02-geek-room.md`, `research/03-synapse-technical.md`, `research/winners/05-vibe12.md` (Vibe-a-thon 1.0/2.0), `research/winners/04-hackblr.md` (HackBLR 2026); fresh web verification 2026-11-22 of Qdrant / TiDB / GSA quotes below.

---

## 1. Slop checklist — 11 archetypes to kill on sight

If the idea matches any row, drop it or rebuild it around a write-back. All rows sourced from `04-slop-vs-differentiated.md §(a)`; the three starred quotes were re-verified live on 2026-11-22.

| # | Archetype | Why judges reject it |
|---|---|---|
| 1 | RAG chatbot over PDFs/docs ("upload PDF, ask questions") | ★ Qdrant bans pure chatbots two years running: 2026 rules — "submissions that are **only chatbots are not allowed**" ([rules](https://try.qdrant.tech/hackathon-vsd)); 2025 winners framed as "building **beyond chatbots**" ([recap](https://qdrant.tech/blog/vector-space-hackathon-winners-2025)) |
| 2 | Resume matcher / job-application agent / ATS scorer | 3 separate job-agent winners in one Agno edition; zero defensibility, privacy hand-waving |
| 3 | Study buddy / flashcard generator / lecture summariser | "Feature, not a product"; the "seen it a gazillion times" rejection |
| 4 | Medical symptom checker / generic health chatbot | Unsafe without grounding; judges now demand FHIR/evidence grounding. Note: HackBLR health-voice clones (VoiceRx et al.) clustered but did **not** win overall (`winners/04-hackblr.md`) |
| 5 | Sentiment dashboard / review analyser | 2018-era ML relabelled as GenAI; no agent action |
| 6 | Meeting-notes summariser / action-item extractor | Solved by Granola/Otter/Fireflies; demo = transcript + bullets |
| 7 | Generic AI code reviewer / coding assistant | Marginal vs Copilot/Cursor without evals + repo grounding |
| 8 | "Agent that books appointments" / booking bot | ★ GSA 2026 rubric: "each tool [must represent] a **real agent-facing action, not a thin wrapper around a single REST call**" ([GSA](https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon)) |
| 9 | Chatbot-for-a-website / support widget | No state change; judge question: "what can it DO?" |
| 10 | Generic CRM copilot / outreach blaster | Spam cannon; no permissioning, no audit, no artefact |
| 11 | Crypto/memecoin trader | Demo = PnL chart; flagged as gambling, unverifiable |

**Companion fatigue quotes (re-verified 2026-11-22):**
- ★ **TiDB AgentX 2025 (Devpost):** "Last year's event saw **thousands of developers build simple RAG demos**. This year, we want multi-step AI agents…" ([Devpost](https://tidb-2025-hackathon.devpost.com))
- **HackerEarth 2026:** "AI is table stakes, not a differentiator… If your only AI use is 'we call OpenAI,' rethink the idea."
- **Reddit r/LangChain judge report:** "Judges said '**ChatGPT can do this**'" — ding for text-only demos.
- **JetBrains/OpenAI judges (June 2026):** "Don't start with 'what's the coolest new tool' but with… the annoyance… every second of the demo should earn its place."

**Universal write-back rule (from §(c) winners):** every demo must end in a **state change + audit record** (file advanced, claim adjudicated, bed assigned, PO drafted) behind an approval gate — copy the Cite-Before-Act + Blackbox evidence-gate pattern. Chat-only = death.

---

## 2. Per-idea judge scorecard

Scoring 1–5 on five lenses. **Pain** = enterprise pain (integration tax?) · **Live** = live data (not canned docs) · **Write** = governed write-back · **Syn** = Synapse-central (`synapse build` does real work) · **Wow** = demo wow in 60s. **Total /25.**

| # | Idea (from 04 §d) | Pain | Live | Write | Syn | Wow | Tot | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Municipal e-governance file workflow | 5 | 5 | 5 | 5 | 5 | **24** | ✅ Fund. Emotional + maps to all 4 tracks |
| 2 | Insurance claims adjudication (`adjudicate_claim` composite) | 5 | 4 | 5 | 5 | 4 | **23** | ✅ Fund. Regulated gravitas, cleanest composite-tool story |
| 3 | Hospital ops on FHIR (beds/discharge/lab-routing, NOT diagnosis) | 5 | 5 | 5 | 5 | 4 | **24** | ✅ Fund. Clinical-MIMIC precedent; avoids symptom-checker slop (#4) |
| 4 | EDI / supply-chain reconciliation | 5 | 4 | 4 | 5 | 3 | **21** | ◐ Novel but drier demo; best "many→one tool" narrative |
| 5 | On-prem/air-gapped ERP back-office (ERPNext/Odoo) | 5 | 5 | 4 | 5 | 3 | **22** | ◐ Strong thesis fit, weaker stage wow |
| 6 | Telecom OSS/BSS trouble-ticketing | 5 | 4 | 4 | 5 | 4 | **22** | ◐ Genuinely multi-system copilot; medium demo effort |
| 7 | Legacy mainframe/COBOL modernisation | 4 | 3 | 3 | 5 | 2 | **17** | ❌ Cut. Slideware risk in a 7-day online judging window |
| 8 | Industrial/OT + fleet diagnostics | 4 | 4 | 3 | 3 | 4 | **18** | ❌ Cut. Vehicle-diagnostics already won once (novelty spent); safety-interlock demo risk |

Notes: (a) Idea 3 must be **ops-only** — any diagnostic output collapses it into slop #4. (b) Idea 4/5 wow-scores assume a seeded visual (shipment timeline / stock-ledger trace), otherwise −1. (c) All Syn=5 except OT reflect `03-synapse-technical.md`: Python codebases give runnable files; TS/Java/Go/C#/Rust hosted-Auto gives runner-config only — so build the graded demo on a **Python (FastAPI/Flask/Django)** codebase, `--discover` on every rebuild, deployed API behind `ENDPOINT_BASE_URL` for Auto tools.

---

## 3. Top-3 ranking

### 🥇 #1 — Municipal e-governance file workflow (24/25)
- **2nd Brain Labs thesis:** purest "integration tax" story — citizen portal + officer dashboard + document store that never got unified; "nothing is migrated, systems stay in place" lands verbatim; Synapse Auto exposes both systems, one Custom `advance_file` composite fuses search→eligibility→stage-advance with scoped tokens (governance-at-the-source).
- **Geek Room history:** Sarvam/CivicFix-style civic builds already proved MSME-tender/grievance demos win Indian-track judging; Vibe-a-thon 2.0's winner (ShopperMan — paste-link → analysis → action) shows Geek Room judges reward **single-flow transactional** demos, which a file-advance flow copies exactly.
- **60s wow:** paste application ID → agent shows missing docs → officer approves → file advances with audit entry. State change on screen, zero chat-only seconds.
- **Risk:** needs seeded vernacular docs + 200 synthetic applications; trivial with a script.

### 🥈 #2 — FHIR hospital ops, diagnosis explicitly excluded (24/25)
- **2nd Brain Labs thesis:** "accessibility-first" over "lake-first" — live HAPI-FHIR + OpenMRS reached in real time beats any analytics dashboard; SMART-on-FHIR scoping is the governance story 2BL's Palantir essay demands.
- **Geek Room history:** HackBLR made HealthTech a full track and Solo.io's clinical-MIMIC MCP federation was a runner-up — appetite proven — but HackBLR's generic health-voice clones lost, so the **ops-not-diagnosis** framing is the differentiator.
- **60s wow:** "bed for patient X" → agent checks census → assigns bed → drafts discharge → writes back with approval gate. Regulated, visual, governed.
- **Risk:** FHIR version-skew setup cost; mitigate with HAPI JPA Starter `docker compose up` + synthetic patients only.

### 🥉 #3 — Insurance claims adjudication (23/25)
- **2nd Brain Labs thesis:** cleanest "one composite tool from many functions" (`adjudicate_claim` = eligibility + fraud-score + payout-estimate + explanation artefact) — maps 1:1 to the "composite tool from many functions" track; exclusion-clause grounding answers the anti-slop evidence-gate bar (Blackbox pattern).
- **Geek Room history:** fintech/insurance is a standing Geek Room track (HackBLR FinTech; AI-Race fintech); artefact-generating winners (LlamaIndex "Timeline of You" O-1 packet) show judges pay for **concrete artefacts** — the explanation-of-benefits letter is that artefact.
- **60s wow:** submit claim → agent cites policy clauses → approves/flags with fraud rationale → payout drafted. Every step cites evidence.
- **Risk:** slightly drier than civic/health; needs a sharp 60s script and a visible denial-with-reasons branch.

**What to cut and why:** COBOL modernisation (#7) reads as slides in an async-judged online event; OT/fleet (#8) replays an already-crowned winner. EDI (#4), ERP (#5), telecom (#6) are all fundable backups — EDI first among them for novelty — but none beats the top-3's wow-per-setup-hour.

---

## 4. Demo contract (applies to whichever of the top-3 is built)

1. Python codebase, `synapse build --discover`, show the build output + server ID/config on screen.
2. Deployed API (ngrok/Render) behind `ENDPOINT_BASE_URL`; Auto tools verified live before recording.
3. One Custom composite tool; scoped tokens; redacted `${VAR}` secrets; explicit non-touch list.
4. Cite-Before-Act approval step before every write.
5. 60-second path: live query → reason with cited evidence → approved write-back → audit record visible.
6. No free-text diagnosis, no "ask your docs" chat tab, no dashboard without a write button.
