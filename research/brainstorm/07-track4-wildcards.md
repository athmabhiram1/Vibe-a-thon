# Track 4 Open-Innovation Wildcards — Synapse-Core Ideas (Avoiding Guide Clichés)

> Guide examples to AVOID: small-business booking assistant, generic bug-triage, study copilot on course portal.
> All ideas below require `synapse build` (Auto / Custom / both) at the core — no Synapse = disqualified.
> Judged on: originality + real-world value, Synapse centrality, technical execution, demo quality.

## Scoring rubric (total /20)

Each idea scored on 4× /5:
- **N Novelty** (originality vs hackathon field)
- **D Demo power** (can you show E2E in 3 min with live `synapse build --discover`?)
- **S Synapse centrality** (does agent *depend* on generated MCP tools? Auto vs Custom fit?)
- **V Real-world value** (who pays / who hurts without it?)

---

## W1 — Telecom OSS/BSS: Alarm → Ticket → Dispatch Autopilot

**Pain:** NOC engineers drown in SNMP alarms. OSS (network monitoring) and BSS (ticketing/billing/dispatch) live in different systems. Correlating "fiber-cut + 40 down alarms" into 1 ticket + dispatching field tech takes 30-60 min.

**Idea:** Two Synapse MCP servers: (1) Auto over OSS alarm API (OpenNMS-style), (2) Auto over BSS ticketing/dispatch API (Spring-Boot helpdesk). Agent flow: `storm of alarms → correlate to situation → open/update ticket → find nearest free tech → dispatch + SMS draft → resolve when clear alarms arrive`.

**Why original:** No team will bring telco OSS. Combines Track-3 pattern (two systems) but Track-4 eligible as novel domain. ALEC-style correlation is ML-heavy — agent + tools version is fresh.

**Sample codebases:**
- OSS: `OpenNMS` (open source NMS, alarms/events/correlation workflows, ALEC Architecture for Learning Enabled Correlation groups related alarms into situations) — https://github.com/OpenNMS/opennms + docs https://docs.opennms.com + ALEC integration https://docs.opennms.com/alec/3.0.4/reference/architecture/opennms_integration.html
- For hackathon, don't run full OpenNMS — build mini OSS in Python/FastAPI: `POST /alarms`, `GET /alarms?severity`, `POST /situations/correlate`, `POST /alarms/clear`. Seed with OpenNMS event reduction logic (counter + down/up matching).
- BSS: Spring-Boot helpdesk e.g. `bdaubry/helpdesk`, `alfahami/it-support-ticket-system`, `soaresdiogo/ticket-management-system` (microservices Spring Boot 4) — expose `POST /tickets`, `GET /technicians?skill=&zone=`, `POST /dispatches`.
- Synapse reads TypeScript/Java/Python — all three work in Auto mode.

**Synapse architecture:**
- `synapse build --auto --all-endpoints` in `mini-oss/` → server-id OSS
- `synapse build --auto --all-endpoints` in `mini-bss/` → server-id BSS
- Agent (Claude Desktop / Semantic Kernel triage agent — see Context7 `/microsoft/semantic-kernel` orchestration: `TriageAgent` with `BillingAgent+RefundAgent` as plugins; same pattern with `AlarmAgent+DispatchAgent`) needs both to answer: "Which customers affected by router R-Edg-04 outage and are tickets already open?"
- Live update moment: `POST /technicians/location` new endpoint → `synapse build --discover` → agent immediately uses geo-dispatch.

**Demo (3 min):**
1. Inject 25 synthetic alarms (fiber degradation) → agent calls `correlate_alarms` → 1 situation.
2. Agent checks `list_tickets`, creates `TKT-1042` with impacted nodes, assigns tech via `list_technicians`.
3. Inject `clear` alarms → agent auto-resolves ticket, drafts closure SMS.

**Risks:** Running real OpenNMS too heavy → mitigate with mini-OSS stub + cite OpenNMS mapping. Safety: dispatch needs human confirm (`--smart-names` + confirmation step).

**Score: 17/20** — N5 D4 S4 V4. Highest enterprise value; demo needs good seeding.

---

## W2 — COBOL Batch Explain & Convert Copilot

**Pain:** Banks/insurers run 40-year-old COBOL batch (payroll, interest, claims). No one dares touch JCL + copybooks. Modernization estimates take weeks of manual reading.

**Idea:** Synapse Custom single smart tool `explain_and_convert_job(cobol_source)` composed from Python functions: `parse_copybook() + build_call_graph() + explain_paragraph() + convert_to_python_stub() + generate_tests()`. Auto server over a batch-metadata API (`GET /jobs`, `GET /runs/failed`) for ops questions. Agent answers: "Why did PAYROLL-07 fail last night? Show COBOL paragraph, explain in plain English, propose Python equivalent + test."

**Why original:** COBOL + Synapse Custom is unexpected; judges remember it. Directly enterprise-relevant to 2nd Brain Labs thesis (make legacy usable without rewrite).

**Sample codebases:**
- `Azure-Samples/Legacy-Modernization-Agents` — AI-powered COBOL→Java Quarkus agents on Microsoft Agent Framework, smart-chunking architecture for token management, `CobolToQuarkusMigration.csproj`, `Program.cs` multi-provider (AzureOpenAI/GH Copilot/OpenAI) — https://github.com/Azure-Samples/Legacy-Modernization-Agents
- For hackathon: vendor 2-3 tiny COBOL files (PAYROLL, INTEREST-CALC with PERFORM loops, COPY books) + Python shim that parses them (no mainframe needed). Custom mode reads Python only — perfect.
- Ops API: Python FastAPI `mini-batch-ops` with `/jobs`, `/runs`.

**Synapse architecture:**
- Custom: `synapse build --custom -q "Explain COBOL paragraph and convert to tested Python stub"` → `<tool>_server.py` in repo root (Custom output is always Python file).
- Auto (optional second server): `synapse build --auto` over batch-ops API for run history.
- Agent depends on Custom tool — cannot do conversion without it → strong Synapse centrality.

**Demo:**
1. "Why did nightly interest job abend at STEP03?" → agent pulls run log via Auto tool, maps to COBOL line via Custom tool.
2. "Explain CALC-INTEREST in plain English for auditor" → paragraph summary + data-flow.
3. "Convert to Python + pytest" → side-by-side diff, runs `pytest` live.

**Risks:** Hallucinated conversion → mitigate with tests + `show confidence + human approve before write`. Keep COBOL tiny so chunking works.

**Score: 16/20** — N5 D3 S5 V3. Best Synapse-Custom showcase; slightly weaker live wow vs alarms/voice.

---

## W3 — OT / Fleet Diagnostics: CAN/J1939 Doctor

**Pain:** Fleet operators get cryptic DTCs (P0420, SPN 100 FMI 1). Drivers call depot, mechanic guesses. Telematics and workshop manuals disconnected.

**Idea:** Synapse Auto over (1) telematics/CAN-ingest API, (2) diagnostics knowledge API (DTC library + work orders). Agent: `stream of J1939 frames → decode PGN/SPN → lookup DTC severity → recommend limp-home vs tow + parts + open work order`. Use virtual CAN bus — no truck needed.

**Sample codebases:**
- `Embedded-Verse/j1939-emulator` — SAE J1939 multi-ECU emulator, PGNs/DTCs/VIN/engine data on virtual CAN via `python-can`, DM1(65226)/DM2/DM3 handling — https://github.com/Embedded-Verse/j1939-emulator
- `zombieCraig/UDSim` — UDS simulator for training, emulates ECUs responding to UDS requests.
- `EcuBus-Pro / EcuBus`, `AKJ7/CANExplorer`, `oussama-gobji/Automotive-Diagnostic-Simulator` — GUI + simulation alternatives.
- `iDoka/awesome-canbus` curated list.
- Mini-API: FastAPI `POST /can/ingest`, `GET /dtcs/{code}`, `POST /workorders`.

**Synapse architecture:**
- Both servers Auto. Python project → can also do `--local` (`synapse_auto_server.py`) with own key — good for OT offline story.
- Agent orchestration (Semantic Kernel `SequentialOrchestration`: decode → triage → act — cf. Context7 docs `/microsoft/semantic-kernel` GroupChat/Sequential patterns retrieved via `query-docs`).
- Live update: add `GET /parts/availability` → `--discover` → agent now checks stock before recommending repair.

**Demo:**
1. Start `j1939-emulator` virtual bus → stream DM1 frames → agent decodes "SPN 100 Engine Oil Pressure, FMI 1 critical".
2. Agent looks up severity, asks driver 1 clarifying question, opens work order + parts hold.
3. Show before/after: many small functions vs one Custom `diagnose_fault()` wrapper (optional Custom kicker).

**Risks:** CAN hardware confusion → emphasize virtual bus. Safety: never actuate — read-only + work-order draft needs confirm.

**Score: 16/20** — N4 D5 S4 V3. Best live demo (blinking frames, gauges); value niche but memorable.

---

## W4 — Municipal Tender Discovery & Fit Copilot

**Pain:** Small contractors miss GeM/CPPP/state-portal tenders; documents are 80-page PDFs with eligibility traps (turnover, EMD, MSME clauses). Tender247/Tenderkart charge for aggregation.

**Idea:** Synapse Auto over (1) tender-aggregator API (scraped/normalized GeM + CPPP + eProcure), (2) company-profile/eligibility API. Custom smart tool `score_fit(tender_id)` = `check_eligibility() + extract_deadlines() + draft_checklist() + price_benchmark()`. Agent: "Find civil works in Hyderabad < ₹50L closing in 14 days that we qualify for, rank + draft document checklist."

**Sample codebases:**
- Official: GeM CPPP listings https://gem.gov.in/cppp, `bidplus.gem.gov.in/all-bids`, eProcurement https://etenders.gov.in
- `r3tr056/gem_mcp` — reverse-engineered GeM MCP (listings endpoints) — useful reference for tool shapes.
- Build mini-aggregator: FastAPI with `GET /tenders?city=&value_max=&days=`, `GET /tenders/{id}`, seeded from real GeM/CPPP samples (cite Tenderkart/Tender247 coverage of 500+ portals as motivation).

**Synapse architecture:**
- Auto for both APIs + Custom for `score_fit` composite — shows Auto+Custom both (Track-4 allows both; strong execution signal).
- `--smart-names` critical: `GET /tenders` → `search_live_tenders` with clear descriptions → agent picks right tool.

**Demo:**
1. "What closes this week for electrical contractors?" → ranked table with EMD/fees/deadlines.
2. "Do we qualify for GEM/2026/B/81234?" → eligibility verdict + missing certs.
3. Add `POST /alerts/subscribe` endpoint → `--discover` → agent subscribes live.

**Risks:** Live scraping fragile → seed static JSON + one live GeM fetch fallback. Legal: read-only, no auto-bid (safety + confirmation).

**Score: 15/20** — N4 D4 S4 V3. High India relevance (Hyderabad R&D angle); demo less visual than CAN/voice.

---

## W5 — Voice Copilot for the Officer / Front Desk

**Pain:** Police station / municipal desk / clinic reception: officers juggle registers, phone, walk-ins. Typing is bottleneck; e-governance portals unloved.

**Idea:** Voice-first agent over existing desk system (FIR/complaint register + duty roster + case status APIs). Officer speaks (Hindi/English/Telugu code-mix) → Whisper STT → agent calls Synapse MCP tools → TTS reply + screen card. "Nayi complaint likho, FIR 212 ki status batao, duty roster me kaun free hai?"

**Sample codebases:**
- Voice stack: `alexandrmotologa/voiceforge` (WebRTC + Silero VAD barge-in <80ms, streaming STT/LLM/TTS, local mode Whisper+Sherpa-ONNX+Ollama+Kokoro), `ictinnovations/asterisk-ai-voice-agent` (Asterisk AudioSocket, Whisper/ElevenLabs Scribe, Piper/ElevenLabs TTS), `aiwithvd/voiceai` (LiveKit Agents self-hosted), `voicedesk` (Whisper→LLM Sarvam-30B→Cartesia/Sarvam Saaras — India-language relevant).
- Desk system: reuse Track-1 style clinic/support-ticket backend or OpenELIS-Global-2 (Java/Spring+React Carbon, FHIR R4, Docker — https://github.com/DIGI-UW/OpenELIS-Global-2) as "register" analogue; or mini FastAPI `complaints/roster`.
- OpenELIS note: heavy Java system — for hackathon build mini desk API mirroring its resources, cite OpenELIS as production mapping.

**Synapse architecture:**
- Auto over desk API (TypeScript/Python/Java all scannable; generated server always Python).
- Voice layer is thin client calling MCP tools — Synapse remains core (without MCP server agent is mute). Emphasize in write-up + architecture diagram.
- Live update: add `POST /complaints/{id}/escalate` → `--discover` → voice command "escalate karo" works mid-demo.

**Demo (crowd-pleaser):**
1. Push-to-talk: "Ek water-logging complaint register karo, caller Ravi, area Kukatpally" → agent creates ticket, reads back ID via TTS.
2. "FIR 212 me kya update hai?" → status + next hearing.
3. "Night shift me kaun available hai?" → roster lookup + dispatch suggestion.

**Risks:** Audio fails on stage → always have text fallback box + pre-recorded audio. STT for code-mix needs Sarvam/Whisper-large; keep utterances short. Privacy: on-device option via `--local` + Ollama.

**Score: 17/20** — N4 D5 S3 V5. Highest wow + social value; must work hard to prove Synapse centrality (keep voice logic tool-dependent, no hardcoded answers).

---

## Comparison matrix

| Idea | N | D | S | V | Total | Best for |
|---|---|---|---|---|---|---|
| W1 Telecom alarm→ticket→dispatch |5|4|4|4|**17**| Enterprise $ value, Track-3-like rigor |
| W5 Voice officer desk |4|5|3|5|**17**| Crowd wow, civic impact |
| W2 COBOL explain/convert |5|3|5|3|**16**| Synapse-Custom purists, memorable |
| W3 Fleet CAN doctor |4|5|4|3|**16**| Most visual live demo |
| W4 Tender discovery |4|4|4|3|**15**| India-fit, GeM relevance |

**Recommendation:** Primary = **W1** (safest win: two-system, clear ROI, easy seeding, live `--discover` moment judges love). Stretch/backup = **W5** if team has WebRTC/voice chops and wants standing-ovation demo — pair with W1's BSS API as desk backend to hedge. If team is Python-only and wants Custom glory, pick **W2**.

## Build checklist (all wildcards)

1. `npm i -g @2ndbrainlabs-ai/synapse-cli; synapse --version`
2. Keep original app code untouched ( judging criterion).
3. `synapse build --auto --smart-names` (fewer, well-named tools) or `--custom -q "<workflow>"`.
4. MCP config snippet → Claude Desktop/Cursor; `synapse build --discover` rehearsed for live update.
5. Safety: confirmation before any write/dispatch/convert; `${ENV}` for secrets; `--local` if sensitive.
6. Submit: repo + MCP setup + write-up (problem + why Synapse) + E2E demo (≥2 cross-system questions for W1/W3/W5).

## Sources

- Participant guide (Tracks + Synapse modes, quota, commands) — `guide.txt` / Vibe-a-thon PDF.
- OpenNMS platform, ALEC correlation, event reduction — websearch `OpenNMS alarm correlation`.
- Azure-Samples/Legacy-Modernization-Agents (COBOL→Quarkus, smart-chunking) — websearch.
- OpenELIS-Global-2 / openelisglobal-core (LIS/LIMS, FHIR R4) — websearch.
- j1939-emulator (python-can virtual bus, DM1/DM2/DM3), UDSim, EcuBus, awesome-canbus — websearch.
- GeM CPPP/etenders, gem_mcp reverse-engineering, Tenderkart/Tender247 coverage — websearch.
- Voice frameworks: voiceforge, asterisk-ai-voice-agent, voiceai/LiveKit, voicedesk — websearch.
- Context7 `/microsoft/semantic-kernel` — `resolve-library-id` + `query-docs` (multi-agent orchestration: concurrent/sequential/group-chat/handoff, triage-plugin pattern) via Code Mode `execute`.
