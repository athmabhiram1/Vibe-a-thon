# 10 — Differentiation Matrix: Onboarding Copilot vs. Six Competitor Classes

**Date:** 2026-11-22 · **Status:** final · **Lane:** diff synthesis (no `research/diff/01-09` existed — built from `research/final/07-competitors.md`, `16-judge-score.md`, `09-falsify.md`, `19-H1/H2`, `research/04-slop-vs-differentiated.md` + live websearch fallback 2026-11-22)
**Our build under test:** `onboard_employee_guarded` — approval-gated composite: HR + IT two-system join, `confirm + preview_hash` gate, idempotent replay, append-only SQLite audit + evidence cards, live `--discover`, local/offline-capable, hours-to-seed.

---

## 1. Matrix

Legend: ✅ yes · ❌ no · ~ partial / claims-without-proof. "Setup" = hours from clone to demoable.

| Competitor class | Two-system join? | Approval-bound hash? | Idempotency? | Audit chain? | Live `--discover`? | Offline? | Setup hours? | **Verdict + one-line why** |
|---|---|---|---|---|---|---|---|---|
| **Paperclip (agent-hire + governance checklist vendor)** — dashboard to "hire agents," 9-part agent-governance checklist incl. approvals (`paperclip.ing/blog`, `paperclip.com` security outlook; cf. `07-competitors.md` §C pattern) | ~ (orchestrates tools, no HR+IT join shown) | ~ (checklist *recommends* approvals; no `preview_hash`-bound execution proof) | ❌ | ~ (governance guidance, no queryable per-run receipt shown) | ❌ | ❌ (cloud dashboard) | Days–weeks (platform onboarding) | **BEAT — they publish the checklist, we execute it: our approval is a persisted hash-gate, not a blog post.** |
| **HRIS / ITSM suites (Workday + ServiceNow/Moveworks/Workativ, Composio-scoped agents)** — full lifecycle, OAuth token-exchange least-privilege, human approvals, SIEM-exportable audit (`composio.dev/content/ai-agents-for-hr`, `moveworks.com` lifecycle-compliance, `workativ.com` HR agents, `servicenow.com` HRSD approvals) | ✅ (Workday↔ServiceNow triggers, e.g. `tray.ai` Workday→ServiceNow provisioning) | ✅ (approval workflows, phased write-gating) | ✅ (enterprise idempotent workflows) | ✅ (SIEM-exportable, incl. denied calls) | ❌ (static integrations, no runtime discovery moment) | ❌ (cloud SaaS, quarter-long rollouts: 4-phase read-only→production) | 100s of hours (4-week read-only phase alone) | **LOSE on production depth — a pilot cannot out-suite Workday; BEAT on demo economics (hours vs. quarters) + the live `--discover` moment no suite has.** Lead with cost-of-proof, never feature parity. |
| **Agent harnesses (CrewAI / ADK / LangGraph flat agents + hackathon clones)** — `gspain89/crewai-hr-onboarding-cua-agent` (vision-clicking, 0 stars), `HireFlow` (mock/Notion data, no HITL), Google ADK `new-hire-onboarding` sample (demo-local artifacts), `Harini-V06` (1 LLM call + SMTP), n8n wrappers (`Buddyb419`, `jhonkomar` — Sheets-as-DB, hardcoded role maps) (`07-competitors.md` §A rows 1–7, 9–10) | ❌ (single-system Google Workspace / Sheets / Notion, or zero systems — Faker data) | ❌ ("LLM decides"; no blocking gate) | ❌ (retry = duplicate tickets) | ❌ (chat log or Sheets row at best) | ❌ (hardcoded tool lists) | ~ (local but trivially so — nothing to be offline *from*) | Hours (but hours to build slop) | **BEAT — flat agents execute; ours pauses and proves: blocking approval + deduped replay + audit DB they structurally lack.** |
| **Skills marketplaces (skill-store / 232-skill harness pattern)** — Anthropic-hackathon 60-agent/232-skill harness breakdown (judges stressed *scoped* agents with evals, `04-slop-vs-differentiated.md` §a row 7); Lablab "HR Chatbot" template; Agno winners (Launch Job Orbit, SmartApply — distribution over governance) | ❌ (skills are single-domain: job-hunt, study, SDR-spam) | ❌ (install-and-run; no cross-skill approval boundary) | ❌ | ❌ | ~ (marketplace *lists* tools; nothing is discovered live into a running join) | ❌ (cloud skills) | Hours (install fast, integrate never) | **BEAT — they distribute tools; we gate them: 8 functions fused behind one evidence-gate beats 232 ungated skills.** |
| **Single-purpose MCP servers (thin wrappers)** — `sanjbhat/employee-onboarding-mcp` (HTML walkthroughs, local JSON progress), generic per-endpoint servers; GSA 2026 rubric explicitly rejects "thin wrapper around a single REST call" (`07-competitors.md` §A row 4; `16-judge-score.md` §3 GSA quote) | ❌ (one server, one system, zero joins) | ❌ | ❌ | ❌ (local progress JSON ≠ audit) | ❌ (static mount; auto-IDs even *hide* routes — H4 mechanism, `09-falsify.md` H-K3) | ✅ (local — their only win) | Hours | **BEAT — one server per endpoint is exactly what GSA told judges to reject; our 1-vs-8 table (one goal-tool fusing 8 functions) is the rubric's model answer.** |
| **Governance proxies (enterprise control planes)** — Workato Access Provisioning MCP (every write approval-gated, Okta/Entra auto-provision), Composio (scoped OAuth, unified audit w/ denials), Solo.io 2026 winner (K8s-native MCP governance, Huzefa Hamdard — solo-built), MCP.STORE (Keycloak JWT + CEL "cannot bypass"), **Cite-Before-Act MCP** (Best Overall, MCP Birthday Hackathon), DataHub **Blackbox** (evidence-gate) (`07-competitors.md` §C; `04-slop-vs-differentiated.md` §c) | ✅ (Workato/Composio span HR+IT) | ✅ (approval-gated writes) | ✅ | ✅ (incl. denials — the compliance bar) | ~ (federation/discovery exists at Solo.io level, not as a 60-second demo beat) | ❌ (platform/cloud) | Weeks (enterprise procurement) | **TIE — same thesis, different weight class: we are their hackathon-buildable mini-version; win on live `--discover` + solo-reproducibility (one compose file, 2-min setup), concede platform depth.** Never claim to out-govern Workato — claim to *demo* its pattern in 60 seconds. |

**Honest scorecard:** 4 BEAT · 1 TIE · 1 LOSE. The LOSE (suites) and TIE (proxies) are load-bearing: judges trust a team that concedes depth and competes on proof-cost.

---

## 2. Judge-ready one-liners (memorize verbatim)

1. "Unlike Paperclip, we don't checklist governance — every write is bound to a `preview_hash` approval you can replay on stage."
2. "Unlike Workday and ServiceNow, we go from clone to governed Day-1 activation in hours, not a four-phase quarterly rollout."
3. "Unlike flat CrewAI and ADK agents, ours cannot silently provision: no `confirm + preview_hash`, no execution — injection attempts die in code, not in prompt."
4. "Unlike single-purpose MCP servers, we fuse eight functions into one goal-tool — the GSA rubric's literal definition of a real agent action."
5. "Unlike enterprise governance proxies, our entire control plane fits in one compose file: kill the network and the audit DB still proves what happened."

---

## 3. Kill criteria — if H1 falsifies, pivot (not persist)

**H1 recap** (`19-H1-onboarding-blockers.md`): Day-1 failures are join-dependent (HR record + IT provisioning). **Falsified if:** in ≥20 tickets or a 5-user concierge walkthrough, ≥80% of failures resolve with form-only fixes and zero cases need HR+IT coordination.

**If falsified, the two-system join is unjustified scope — execute within 48h:**

| Step | Action |
|---|---|
| 1. Drop | Cross-system orchestration + approval-join logic (scope shrinks ~50%; do not demo a join nobody hits). |
| 2. Pivot A | `sunset_vendor` (Track 2 composite backlog, `03-track2-composite.md`): staged-then-revoke vendor/license cleanup — single-system, same `confirm + preview_hash` + audit machinery, zero join dependency. |
| 3. Pivot B | `adjudicate_claim` (insurance, `04-slop-vs-differentiated.md` §d #2, score 19/20): eligibility + fraud-score + payout-estimate fused behind the same evidence-gate; regulated gravitas without HR/IT data. |
| 4. Keep regardless | Approval gate, idempotency, audit receipt, `--discover` beat — the governance stack transfers verbatim; only the domain changes. |
| 5. Tell judges | "We killed our own join hypothesis in concierge testing — here's the audit log that killed it." Falsification *performed* outscores a join *asserted* (per `09-falsify.md` watchlist + judge checklist "how does it fail?"). |

**Do-not-pivot trap:** reframing as an "HR Q&A bot" on H1-failure = walking into Qdrant's ban and TiDB's "thousands of simple demos" fatigue (`16-judge-score.md` §3). If the join dies, change the domain — never retreat to chat.

---

### Sources
- Local: `research/final/07-competitors.md` (14 builds + contradiction queries) · `research/final/16-judge-score.md` (23/25 scorecard, fatigue quotes, kill criteria) · `research/final/09-falsify.md` (K1–K4 survival + watchlist) · `research/final/19-H1/H2` · `research/04-slop-vs-differentiated.md` (winners: Cite-Before-Act, Blackbox, Solo.io governance) · `research/brainstorm/03-track2-composite.md` (pivot tools).
- Web (2026-11-22): Composio scoped-permissions guide (`composio.dev/content/ai-agents-for-hr`) · Moveworks lifecycle compliance (`moveworks.com`) · Workativ HR agents (`workativ.com/hr`, `/blog/ai-agent-for-hr-onboarding-how-it-works-and-what-it-automates`) · Paperclip governance checklist (`paperclip.ing/blog`) · ServiceNow HRSD approvals (`servicenow.com/docs`) · Tray Workday→ServiceNow (`tray.ai/connectors/workday-rest-servicenow-integrations`).
