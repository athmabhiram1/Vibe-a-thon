# HR Onboarding / HRIS Market — Track 3 Onboard Copilot Competitors

> Scope: BambooHR, Workday, Greenhouse, Sapling (Kallidus) + Enboarder, Deel, Rippling, HiBob, Freshteam
> Lens: Day-1 provisioning story, HR↔IT handoff, approval gates, audit log, API/MCP extensibility, pricing per emp/mo, and what they DON'T do vs Track 3 (two-system live discover + approval-bound write-back).
> Date: 2026-11-22. Prices are vendor list + third-party benchmarks; enterprise = quote.

## TL;DR

- Only **Rippling** and **Deel IT** do true Day-1 app+device provisioning natively. Everyone else does checklists/tasks + raises IT tickets.
- **Workday** has the strongest approval/audit engine (Business Process Framework), but is heavyweight, quote-only (~$34–100/emp/mo) and is a system-of-record, not a cross-system reconciler.
- **BambooHR / HiBob / Freshteam / Greenhouse / Sapling / Enboarder** orchestrate *tasks and paperwork* — IT provisioning is delegated to Okta/Entra/Google or ServiceNow/Jira tickets.
- **Nobody** offers Track 3's combo: (1) **two-system live discover** (read HRIS + IdP/IT/SaaS side-by-side, diff drift pre-Day-1) + (2) **approval-bound write-back** (no writes until human approves, then atomic write-back with immutable log). Rippling/Deel auto-provision *inside their own graph*; Workday needs integration builds; others don't write to IT at all.
- MCP: **none publish an MCP server**. All have REST + webhooks + marketplace. Track 3 MCP tool surface is a greenfield differentiator.

## Comparison table

| Vendor | Day-1 provisioning story | HR↔IT handoff | Approval gates | Audit log | API / MCP extensibility | Pricing (per emp/mo, USD) | What they DON'T do (vs Track 3) |
|---|---|---|---|---|---|---|---|
| **BambooHR** | New-hire packet, e-sign, onboarding checklists. No native app/device provisioning; via Okta/Google/Slack integrations. | Tasks assigned to IT/manager with email nudges; no shared IT queue. Needs Zapier/Tray or ticket. | Workflows & approvals (time-off, records, onboarding tasks). Not entitlement-level with rollback. | Employee-record change history + workflow history. Exportable reports. | Open REST API + webhooks + marketplace (Okta, Tray). No MCP. | **Core ~$10–10.25** (>25 emp) or **$250/mo flat ≤25 emp**; Pro ~$17–17.50; Elite ~$25. Onboarding in Core. | No live discover across HRIS+IdP/SaaS. No approval-bound write-back to IT — writes are HR-record only. |
| **Workday HCM + Onboarding** | Personalized preboarding/onboarding tied to single HCM data model + Learning. Provisioning via Entra ID SCIM / lifecycle integrations. | Business Process Framework routes inbox items to HR/IT/manager sequentially. Strongest enterprise handoff, but config-heavy. | Best-in-class: configurable BPs with Approve/Deny/Send-Back; Extend custom BPs + orchestrations; security-domain gated. | Reportable/auditable BP events (in-progress/completed/remaining steps, comments, attachments); Extend user-activity audit 30-day rolling + core retention. | Workday Extend, REST/SOAP, Integration API Gateway, Orchestrate, Event/Events APIs. No MCP. | **Quote only; ~$34–42** est., commonly **$50–100+**; ~$400–500/yr; +1–2× implementation + middleware. | Not a cross-vendor live-discover reconciler (it *is* the SoR). No lightweight approval-gated write to arbitrary SaaS without integration build. |
| **Greenhouse (ATS + Onboarding add-on)** | Recruiting→onboarding handoff; paperwork, tasks, intros. Equipment provisioning via HRIS-triggered automations. | Conditional automations by role/team/location; raises HRIS/IT tasks, not direct provision. | Offer approvals strong; onboarding approvals light. | Hiring activity logs; onboarding audit limited vs HCM. | Harvest + Onboarding APIs, webhooks, prebuilt HRIS integrations. No MCP. | **Quote; base ~$6k–12k+/yr**; Onboarding add-on est. **$4–10/emp/mo**, scales by hiring volume. | Not an HRIS. No live discover; no write-back beyond HRIS sync. |
| **Sapling by Kallidus** | Deep onboarding/offboarding workflows, e-sign, task branching by role/location. Provisioning via ATS/payroll/IdP integrations. | Assigns IT tasks with reminders; Gusto/Lever/ADP sync. No native MDM/provisioning. | Workflow approvals; journey gating lighter than Workday. | Workflow analytics; not immutable compliance ledger. | Prebuilt ATS/HRIS/IdP connectors + API; custom = PS. No MCP. | **Quote; est. ~$5–8/emp/mo**. Sold with Kallidus LMS suite. | No live two-system diff; no approval-bound SaaS write-back. Now LMS-bundle sale. |
| **Enboarder** | Journey orchestration: preboarding, nudges, DocuSign/Adobe Sign, ServiceNow/Jira laptop ticket raise, calendar invites, 30-60-90 AI ramp plans. | Coordinates buddy/manager/IT stakeholders with escalations; ticket-raise ≠ provision. Manager makes readiness call, journey waits. | Routing approvals (e.g., 30-60-90 sign-off, role-play readiness). Branching if/then + sentiment triggers. | Dashboards + journey insights; launch caps by tier (1/3/unlimited journey types). Not immutable ledger. | Prebuilt HRIS/ATS/Slack/Teams; Video + Registry Sync + Compliance as add-ons; custom via PS. No MCP. | **Quote only**; aggregators **$4–15/emp/mo** (mid ~$5–10); GetApp floor **$9,950/yr**; Vendr median **$17k/yr**; Enterprise **$75–200k+/yr**; impl. **$5–20k**. +7% renewal uplift + audit clause. | No live discover of HRIS vs IdP drift. No direct approval-bound provisioning — raises tickets, waits on humans. |
| **Deel (HRIS + Deel IT)** | Auto HR-IT triggers on hire record; contracts, payroll, benefits + **zero-touch app provisioning, MDM (JumpCloud), device logistics in 130+ countries**. | Shared HR/IT triggers; device provisioning from hire event, no manual handoff. Best for global/EOR. | Roles/permissions + onboarding/offboarding approvals; lighter than Workday/Rippling policy engine. | Payroll/compliance audit logs + IT action logs. | Deel API + HRIS integrations + ATS/Slack/mobile. No MCP. | **HRIS from ~$5/emp/mo** (often bundled/free); Talent **$14/worker/mo**; Contractors **$49**; EOR **$599**; US PEO **$125**; Payroll Core **$50 + $6/emp**. | Wants to *be* both systems — no brownfield live-discover of customer's existing HRIS+IdP. Write-back is inside Deel graph, not approval-gated overlay to external SaaS. |
| **Rippling (closest rival)** | **Single action → payroll + laptop + app access + benefits + training.** Device ordering, MDM, SSO/MFA, SaaS entitlements from one workflow; attribute-based auto-trigger. | Unified HR/IT/finance SoR; auto-triggers on role/entity/location. No handoff gap *if* all-in on Rippling. | Immutable, exportable workflow/approval logs; policy automation (e.g., Compliance 360). | Strong: every approval/action logged, audit-ready. Public support CSAT disclosed; logs exportable. | Rich API with nested worker/device/entitlement graph + App Store + RFP-grade automation hooks. No MCP. | **Base ~$8/emp/mo per module**; full stacks **$15–25**; IAM **~$8/user/mo**; MDM **~$8**; impl. **$2k–75k**. Quote for exact. | Single-vendor graph, not cross-vendor live discover. Auto-provisions natively — not an approval-bound copilot overlay that leaves incumbent systems untouched until approved. Steep learning curve, mixed support reviews. |
| **HiBob (Bob)** | Lifecycle workflows, docs, pre-Day-1 collection, culture/engagement focus. IT via Okta/Google/JumpCloud integrations. | Task + nudge model to IT; no native provisioning/MDM. | Lifecycle approvals (time-off, comp, onboarding tasks); light on IT entitlement gating. | Change logs + analytics; Core includes DB/docs/workflows/integrations/reporting. | Open API + marketplace + Bob AI Companion. No MCP. | **Quote; base ~$8–12/emp/mo**; typical bundles **$16–25**; list **~$20/user/mo**. Per-employee, modular. | No live discover; no approval-bound IT write-back. US payroll/benefits add-on only. |
| **Freshteam (Freshworks)** | Task automation, welcome portals, equipment tracking; ATS+onboarding bundle for SMB. | Checklist assigned to HR/IT/manager via Employees > Onboarding. | Basic offer/onboarding approvals. | Basic activity logs. | Limited REST + Freshworks marketplace. No MCP. | **Free ≤50 emp**; Growth **$71 + $1.20/emp/mo**; Pro **$99 + $2**; Enterprise **$169 + $4**. **Sunsetting from 2026-01-05 — migration risk.** | No advanced provisioning, approvals, audit, or write-back. Do not build against for Track 3. |

## Detail notes (provisioning / handoff / gates / audit / API)

### BambooHR
- Onboarding = paperwork automation + workflows, not provisioning. Bamboo AI explicitly does not create accounts/grant app access.
- Handoff is checklist + notification; IT fulfillment lives in IdP.
- API docs: open API + webhooks; marketplace via Tray/Okta.

### Workday
- Onboarding module = concierge journeys + AI insights on top of HCM single model.
- Provisioning path is Entra ID inbound tutorial / SCIM — IT-owned integration, not Day-1 magic.
- Extensibility is powerful (Extend BPs, Event REST `GET /events`, `POST /events/{id}/cancel`, step submit) but requires Workday developer tenant + security-domain config. Audit is first-class.

### Greenhouse / Sapling / Enboarder
- All three are *orchestration* layers: they coordinate humans and raise tickets (ServiceNow/Jira), send DocuSign, branch content. None directly provisions SaaS accounts or devices.
- Enboarder is the most Track-3-adjacent on journey-wait-for-approval, but approval is a manager readiness call, not an IT entitlement gate with atomic write-back.

### Deel vs Rippling (the only true provisioners)
- Rippling owns HR+IT+finance in one DB; Deel couples HRIS/EOR/payroll with Deel IT (JumpCloud MDM, 130-country logistics).
- Both trigger provisioning automatically on hire — Track 3 differentiates by being **system-agnostic copilot**: discover drift between *any* HRIS and *any* IdP/IT, propose plan, wait for approval, then write back with log. Neither Rippling nor Deel does that overlay motion.

### HiBob / Freshteam
- HiBob wins on UX/culture for mid-market global; IT story is integration-only.
- Freshteam is cheapest but functionally thinnest and being sunset — note as exclusion, not target.

## Pricing sources (spot checks)
- BambooHR Core $10 / Pro $17 / Elite $25 per emp/mo; ≤25 emp $250/mo flat.
- Workday quote-only; benchmarks $34–100/emp/mo.
- Greenhouse custom; onboarding add-on $4–10/emp/mo.
- Sapling ~$5/emp/mo est.; Enboarder $4–15/emp/mo, median $17k/yr.
- Deel HRIS from $5/emp/mo; EOR $599; PEO $125; contractors $49.
- Rippling base $8/emp/mo/module; stacks $15–25; IAM/MDM ~$8 each.
- HiBob base $8–12, bundles $16–25.
- Freshteam $1.20–4/emp/mo + platform fee; sunsetting.

## Track 3 wedge (what to build to win)
1. **Two-system live discover**: read-only connectors to HRIS (Bamboo/HiBob/Workday) + IdP/IT (Entra/Okta/Google + Rippling/Deel where present), diff expected vs actual entitlements/devices pre-Day-1. Nobody does this vendor-neutrally.
2. **Approval-bound write-back**: draft plan → route to manager + IT approvers → on approve, execute SCIM/API writes + ticket closes, with immutable hash-chained log exportable to SIEM. Workday/Rippling log *their* actions; none gate *external* writes this way.
3. **MCP tool surface**: `hr.discover`, `it.discover`, `diff`, `plan`, `requestApproval`, `executeAfterApproval`, `audit.export` — greenfield; no competitor publishes MCP.
4. Price to undercut Rippling stack ($15–25) and Workday ($50+): land as overlay at **$3–6/emp/mo** + implementation waiver, no rip-and-replace.

## Sources / URLs
- BambooHR onboarding: https://www.bamboohr.com/platform/onboarding/
- BambooHR pricing: https://www.bamboohr.com/pricing
- BambooHR API getting started: https://documentation.bamboohr.com/docs/getting-started
- BambooHR AI limits: https://harmony.io/insights/bamboohr-ai
- Workday onboarding: https://www.workday.com/en-us/products/talent-management/onboarding.html
- Workday Entra provisioning: https://learn.microsoft.com/en-us/entra/identity/saas-apps/workday-inbound-tutorial
- Workday Extend BPs: https://developer.workday.com/documentation/GUID-c5613e86-0c6e-4537-a747-b47814a784a3-enHYPHENus/BusinessProcessesinExtendApps
- Workday Events REST: https://developer.workday.com/documentation/GUID-2c36ee1b-1364-45ff-aa8e-c78060c9a1f5/ReferenceAuditUserActivity
- Greenhouse onboarding: https://www.greenhouse.com/onboarding (redirect) — https://greenhouse.com/blog/onboarding-automation
- Sapling/Lever integration: https://help.lever.co/hc/en-us/articles/20087446439581-Enabling-and-using-the-Sapling-Onboarding-by-Kallidus-integration
- Sapling review: https://www.hr.software/reviews/sapling
- Enboarder pricing: https://enboarder.com/pricing/
- Enboarder automation: https://enboarder.com/employee-onboarding-automation/
- Enboarder costs (Vendr): https://www.vendr.com/marketplace/enboarder
- Deel pricing: https://www.deel.com/pricing/
- Deel IT HRIS integrations: https://help.letsdeel.com/hc/en-gb/articles/35347527772817-Deel-IT-HRIS-integrations
- Deel IT vs HR responsibilities: https://www.deel.com/blog/it-vs-hr-who-is-responsible-for-what-during-onboarding-and-offboarding-mid-market/
- Rippling onboarding picks: https://www.rippling.com/blog/best-employee-onboarding-software
- Rippling IAM: https://rippling.com/blog/rippling-identity-and-access-management-review
- Rippling vs BambooHR: https://rippling.com/blog/rippling-vs-bamboohr-hcm-payroll-comparison
- Rippling pricing benchmarks: https://marketplace.workology.com/rippling/ , https://www.activepieces.com/blog/rippling-pricing-2026-what-each-module-costs
- HiBob pricing: https://www.hibob.com/pricing-plans
- HiBob onboarding SMB: https://www.hibob.com/solutions/small-businesses/onboarding-software/
- Freshteam onboarding how-to: https://support.freshteam.com/support/solutions/articles/19000100355-onboarding-a-new-hire
- Freshteam sunset/pricing: https://pin.com/blog/freshteam-pricing (sunset 2026-01-05)
- Market roundups: https://www.lever.co/insights/best-onboarding-software , https://effy.ai/blog/employee-onboarding-software , https://workativ.com/hr/blog/10-best-employee-onboarding-software-tools-in-2026
