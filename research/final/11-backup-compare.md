# 11 — Onboarding vs Backups: Final Compare (Municipal vs Telecom vs EDI)

**Date:** 2026-11-22 · **Status:** final decision memo
**Inputs:** `research/04-slop-vs-differentiated.md` (slop map + §d scores), `research/brainstorm/09-judge-fit.md` (24/22/21 judge-fit scores), `research/brainstorm/08-tech-feasibility.md` (FastAPI+FastMCP build rules), `research/brainstorm/10-track-choice.md`, + fresh web verification 2026-11-22 (section 1).
**Candidates:** (A) Municipal file workflow = "onboarding" primary · (B) Telecom alarm→dispatch = backup 1 · (C) EDI order-to-cash reconcile = backup 2
**Rubric (same as 09):** Pain / Live / Write / Syn / Wow, 1–5 each, Total /25. Solo-build effort scored separately (hours + risk).

---

## 1. Fresh 2026 judge takes (new since 04/09 — all verified 2026-11-22)

1. **HackathonTracker "AI Agent Hackathons" (2026-11-17):** judges want "a goal, not a prompt + tools + autonomy with guardrails." Prescription: cap steps with a stop condition, **log every step on screen** (plan → tool call → result), keep a human confirm before risky actions, control inputs with a small real dataset, **record a backup run**. One narrow task done reliably beats ten halfway. — <https://hackathontracker.com/blog/ai-agent-hackathons/>
2. **ITKAN judging rubric (2026-11-21, live event):** 35 pts idea / **65 pts build+demo**. Working demo 25% + Quality-of-AI-use 25% = half the score. 5/5 demo = "full core flow runs live on a judge's own input, handles bad input." 5/5 AI-use = team can explain model, cost, failure modes, output checks, data protection. — <https://www.itkan.one/I-Hackathon/judging>
3. **All Things Agentic ($180k, Aug 2026):** Innovation & Operational Utility **40%** ("how much real-world friction does the agent remove on its own… autonomous high-value action over simple chat"), Architectural Discipline 30%, Demo & Production Readiness 30% (unedited live demo + arch diagram + reproducible setup). — <https://allthingsagentichackathon.devpost.com/>
4. **Agentware 2026 (Nov 2026, Raptors rubric):** Autonomy 30% + Usefulness 25% + Reliability 20% + Engineering 15% + Demo 10%, **+4 bonus for guardrails / kill-switch / audit trail**. — <https://www.raptors.dev/hackathon-judging-rubric>
5. **JetBrains × Codex judging-table notes (June 2026):** "Show something working within ~90 seconds. One flow. Pre-fill data, mock the slow call. Be direct about what works / doesn't." Scope to ONE flow. — <https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table>
6. **Google Cloud Rapid Agent Hackathon (14.5k registered, July 2026):** all 3 winners grounded agents in live data via MCP — 1st Unravel (clinical decision-support with expert-review gate, low-confidence withheld), **2nd TruthKeeper (cross-system CRM↔billing reconcile: explain mismatch + estimate financial impact + draft corrective action for human approval)** — direct validation of the EDI-reconcile demo shape; takeaway quote: "intelligence gets headlines, **trusted data is what makes agents useful**." — <https://www.fivetran.com/blog/meet-the-ai-agents-that-won-the-google-cloud-rapid-agent-hackathon>
7. **GitLab AI Hackathon 2026:** "agents that jump into workflows, respond to events, and act on your behalf. **Not chatbots that answer questions.**" — <https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/>
8. **Solo.io MCP 2026 (re-confirmed) + Reskilll MCP ideas (Aug 2026):** Solo.io clinical-MIMIC federation runner-up proves regulated-data appetite; Reskilll "Gov Scheme Finder" (FastMCP + eligibility rules engine: `find_schemes / check_eligibility / get_application_steps`) is an independent second vote for municipal/civic as a judge darling. — <https://www.solo.io/blog/celebrating-the-winners-of-the-2026-hackathon-for-mcp-ai-agents>, <https://reskilll.com/blogs/mcp-hackathon-projects-5-winning-ideas-model-context-protocol/>

**What this changes vs 09:** the bar moved further toward *live write-back + visible trace + approval gate + judge's-own-input robustness*. Pure chat = death everywhere (Qdrant ban, GSA "not a thin wrapper," GitLab, Agentware). The 90-second-one-flow rule (JetBrains) and the 65%-build weighting (ITKAN) both favour the candidate with the shortest reliable live path — municipal.

---

## 2. Head-to-head scorecard (/25 + solo-build effort)

| Lens | (A) Municipal file workflow (onboarding) | (B) Telecom alarm→dispatch | (C) EDI order-to-cash reconcile |
|---|---|---|---|
| **Pain** (integration tax?) | **5** — 3 systems never unified (citizen portal + officer queue + doc store); vernacular + audit-trail pain judges feel instantly | **5** — NMS + CRM + workforce dispatch genuinely separate (TM Forum SID/eTOM); alarm storms + SLA penalties | **5** — X12/EDIFACT dialects, partner-specific segments, idempotency; nobody else will touch it |
| **Live** (real data, not canned) | **5** — 200 seeded applications + doc checklist run live; judge can paste any app ID | **4** — needs synthetic alarm feed + subscriber map; live but simulated; judge input = harder to ad-lib | **4** — synthetic X12 850/810 + inventory state live; judge input = paste an EDI blob (powerful but niche) |
| **Write** (governed state change) | **5** — `advance_file` behind Cite-Before-Act approval → stage change + audit row visible | **4** — dispatch plan drafted + ticket updated; write spans 2 systems so atomicity story is harder | **4** — `reconcile_shipment` drafts invoice / flags mismatch (TruthKeeper shape); write = draft + flag, slightly less visceral than a file advancing |
| **Syn** (does `synapse build` do real work?) | **5** — Python Django/FastAPI file-tracker: `--discover` yields clean `search_file / flag_missing / advance_stage`; composite `advance_file` is the track-2 story | **5** — two Python surfaces (alarm API + task/dispatch API) = perfect "copilot across two systems" track-3 story | **5** — cleanest "many functions → one tool" narrative (`parse_edi + check_inventory + draft_invoice → reconcile_shipment`) |
| **Wow** (60–90s stage moment) | **5** — paste ID → missing-docs callout → officer approves → file advances on screen. Emotional, legible to any judge | **4** — alarm burst → correlated subscribers → dispatch plan on map. High wow *if* map renders; −1 if GIS/time eats the demo | **3** — mismatch found → impact estimated → correction drafted. Judges respect it (TruthKeeper won 2nd at Google Cloud) but it reads drier on stage |
| **TOTAL** | **24/25** ✅ | **22/25** ◐ | **21/25** ◐ |
| **Solo-build effort** | **10–14 h, LOW risk.** 1 FastAPI app (files, stages, audit), seed script (200 apps + vernacular doc names), 6–8 tools → 1 composite `advance_file` + approval gate. No GIS, no X12 grammar. Matches 08's guaranteed-detection patterns verbatim. | **14–18 h, MEDIUM-HIGH risk.** 2 APIs (alarms + tickets/dispatch) + correlation logic + map/timeline UI + storm-simulator. Biggest risks: GIS rendering, alarm-storm tuning, two-system atomicity explanation. | **12–16 h, MEDIUM risk.** 1 API (orders/shipments/invoices) + `pyx12` parse + partner-dialect table + idempotency keys + timeline UI. Biggest risks: X12 grammar rabbit-hole, "looks like a parser demo" perception without a sharp script + denial branch. |
| 60s script | ID-1042 → "missing: land-tax receipt" → approve → STAGE 2→3 + audit #881 | BURST-7 cell alarms → 312 subs affected → crew C-3 dispatched, SLA clock shown | EDI 850 #4471 ↔ ASN mismatch qty 96 vs 120 → $8.4k impact → corrected invoice drafted |

**Carry-over from 09 §2 (unchanged):** municipal 24, telecom 22, EDI 21 — fresh 2026 takes *widen* municipal's lead (90-s rule + 65%-demo weighting + Gov-Scheme-Finder second vote) and *raise* EDI's floor (TruthKeeper precedent) without changing the rank order.

---

## 3. Recommendation

**PRIMARY: (A) Municipal file workflow.** Highest score (24/25), lowest solo cost (10–14 h), maps to all four tracks (legacy-ready Django app, composite `advance_file`, two-system copilot, civic open-innovation), and every fresh-2026 signal points at it: goal+tools+guardrails (HackathonTracker), live-on-judge-input demo (ITKAN 25%), friction-removed-autonomously (All Things Agentic 40%), 90-second one-flow (JetBrains), Gov-Scheme-Finder precedent (Reskilll).

**BACKUP: (B) Telecom alarm→dispatch over (C) EDI.** Both score 22 vs 21, but telecom wins as the live backup because (i) its wow (map + dispatch) survives a tired-judge room better than EDI's ledger diff, (ii) it is the only candidate that owns the "copilot across two systems" track outright, (iii) its seed (alarm generator) is buildable in <2 h while X12 dialect handling is unbounded. Keep EDI as **backup-2 / track-2-pivot**: if judges skew deeply technical (MCP-protocol judges, GSA-style rubric), EDI's many→one composite story outshines telecom.

**Track mapping:** Primary → file under Track 1 (legacy app agent-ready) with Track-2 composite (`advance_file`) as the technical headline; Backup-1 → Track 3 (copilot across NMS + dispatch); Backup-2 → Track 2 (composite `reconcile_shipment`).

---

## 4. Drop conditions — numeric tripwires (check at T+4h, T+8h, T+12h)

**Build the primary; kill/switch only on numbers, not vibes.**

| # | Tripwire | Threshold | Action |
|---|---|---|---|
| D1 | Seed-data time (primary) | Synthetic 200-app + doc-checklist seed not running by **T+4h** | Cut vernacular docs to 1 language, halve to 100 apps; if still red at T+6h → switch to Backup-1 |
| D2 | Tool-surface bloat | Auto-exposed tools **>10** after `synapse build --discover` | Allowlist to ≤8 via `include_operations`; curate 1 composite; re-run `--discover` (per 08 §7) |
| D3 | Live-path length | Happy-path demo (cold start → audit row) **>90 s** in 2 consecutive rehearsals | Cut one retrieval step; pre-fill app ID + officer login; pre-seed the "missing doc" case (JetBrains rule) |
| D4 | Write-back proof | No visible state-change + audit row on screen by **T+8h** | Stop adding retrieval tools; implement approval-gate + audit write first (chat-only = death per Qdrant/GSA/GitLab) |
| D5 | Judge-input robustness | Agent fails **≥2 of 5** unseen app-ID / bad-input probes at T+10h | Freeze scope; add input-validation + "file not found" recovery branch; record backup video (HackathonTracker rule) |
| D6 | Primary→Backup-1 switch | D1 or D4 still red at **T+12h**, OR officer-approval UX unfixable | Pivot to Telecom: reuse FastAPI scaffold + approval-gate + audit pattern; storm-sim replaces seed script |
| D7 | Backup-1→Backup-2 switch | Telecom map/GIS not rendering by **T+16h**, OR two-system atomicity can't be demoed in 90 s | Pivot to EDI: single-system reconcile, TruthKeeper script (mismatch → impact $ → draft correction) |
| D8 | No-pivot past | Any pivot after **T+20h** | FORBIDDEN — ship what runs; record backup run, write README limits (model, cost, failure modes per ITKAN 5/5 bar) |

**Non-negotiable demo contract (all candidates):** Python codebase · `synapse build --discover` shown · deployed API behind `ENDPOINT_BASE_URL` · 1 custom composite · scoped tokens + redacted secrets · Cite-Before-Act approval · visible audit row · backup recording · no free-text diagnosis / no chat-only tab / no dashboard without a write button.

---

## 5. Solo-build plan (primary, ~12 h)

1. **T+0–2h:** scaffold FastAPI (`/applications`, `/stages`, `/documents`, `/audit`) with `operation_id=` + Pydantic models; verify `/openapi.json` + Swagger (08 §2).
2. **T+2–4h:** seed 200 apps + doc checklists; `synapse_auto_server.py` (one adapter, pinned); `mount_http()`; Claude-Debug stdio smoke test.
3. **T+4–7h:** curate ≤8 tools + `advance_file` composite (search→eligibility→stage-advance); scoped tokens; non-touch list.
4. **T+7–9h:** approval gate + audit write; 90-s script; 5-probe robustness set (bad ID, missing doc, already-advanced, unauthorized stage, duplicate submit).
5. **T+9–12h:** deploy (Render/ngrok) + `ENDPOINT_BASE_URL`; backup recording; README (arch diagram, setup, model/cost/failure-modes per ITKAN); D-tripwire review.

## Sources

- 04-slop-vs-differentiated.md §§a–d; 09-judge-fit.md §§1–4; 08-tech-feasibility.md §§2,7,8; 10-track-choice.md
- HackathonTracker agent guide (2026-11-17): <https://hackathontracker.com/blog/ai-agent-hackathons/>
- ITKAN judging rubric (2026-11-21): <https://www.itkan.one/I-Hackathon/judging>
- All Things Agentic criteria: <https://allthingsagentichackathon.devpost.com/>
- Agentware 2026 rubric: <https://www.raptors.dev/hackathon-judging-rubric>
- JetBrains judging-table notes: <https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table>
- Google Cloud Rapid Agent winners (TruthKeeper reconcile): <https://www.fivetran.com/blog/meet-the-ai-agents-that-won-the-google-cloud-rapid-agent-hackathon>
- GitLab AI Hackathon 2026 winners: <https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/>
- Reskilll MCP ideas (Gov Scheme Finder): <https://reskilll.com/blogs/mcp-hackathon-projects-5-winning-ideas-model-context-protocol/>
- Solo.io MCP 2026 winners: <https://www.solo.io/blog/celebrating-the-winners-of-the-2026-hackathon-for-mcp-ai-agents>
