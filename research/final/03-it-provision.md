# Omnilearn Phase 1 — Industry Angle: IT Provisioning / ITSM

**Focus:** equipment assignment, account provisioning, ticketing SLA, least-privilege, offboarding / zombie access.
**Lens for Omnilearn:** how onboard→equip→grant→support→offboard workflows are taught, and where automation + governance fail in practice.

## 1. Equipment Assignment (Service Request Fulfillment)

ITIL 4 treats laptop / peripheral / access requests as **Service Request Management** — pre-approved, standardized, fulfilled via request models with approvals and assignments — distinct from incident resolution.

| Source | How equipment assignment should work | Omnilearn takeaway |
|---|---|---|
| ITIL 4 Service Request Management (Matrix42 / Freshworks / Atlassian summaries) | Define request catalog → standard forms → approval policy → fulfillment workflow → closure; separate routine fulfillment from exceptions | Teach request-model design; lab: "new-hire laptop bundle" with approval gate |
| Atlassian — Service Request fulfillment process | Simple fulfillment: log → approve → assign → fulfill → close; standardize intake | Template for Omnilearn scenario branching |
| GLPI Project — Asset Management + Ticketing | Single open-source tool links **asset inventory ↔ tickets**: assign computer/peripheral/printer to user, track lifecycle, auto-link ticket to asset | Use GLPI as reference implementation for equipment-assign labs (800k tickets/yr, 35k users example cited by GLPI) |
| Oracle Access Governance — JML Joiner flow | Birthright access auto-provisioned on HR create-event via policy match (Create Account + Add permission) | Show HR-driven trigger vs. manual ticket |
| Serval comparison — ServiceNow vs JSM onboarding | ServiceNow: lifecycle events span departments (Employee Journey Mgmt); JSM: one onboarding request fans out tasks/approvals per team | Contrast enterprise vs. mid-market tooling in course |

**Key practice:** every equipment request needs owner, SLA clock, linked asset record, and return path — otherwise "who has what" is lost at offboarding.

## 2. Account Provisioning — JML (Joiner-Mover-Leaver)

| Phase | Automated (modern IGA / HR-driven) | Manual / ticketing-only (legacy gap) |
|---|---|---|
| **Joiner** | HR create → policy match → AD/email/app accounts + birthright roles; notify user/manager (Oracle AG, OpenIAM, Oleria models) | Ticket per system; Day-1 delays, inconsistent roles, no audit trail |
| **Mover** | Attribute change → Remove old permission + Add new; disable/delete stale accounts; adaptive check ("do peers have it?") | Old access retained → permission creep; mover is highest-drift phase |
| **Leaver** | Termination event → disable/delete across connectors + tickets for disconnected systems + nightly reconciliation with timestamps | Basic AD disable misses SaaS, shared drives, API tokens, email delegates |
| **Rehire** | Reactivate with *current* roles only | Restore old image → resurrects stale privilege |

Sources: Oracle Access Governance JML docs; OpenIAM JML Lifecycle; Oleria Identity Lifecycle Management; Lumos JML automation; Cloudworks JML explainer.

## 3. Ticketing & SLA Design

### 3.1 What an SLA must contain (Atlassian / ITIL SLM)

| Component | Example |
|---|---|
| Services covered | ITSM support, specific catalog items |
| Metrics | First response, resolution, update cadence, uptime (e.g., 99.9%), FCR / CSAT |
| Roles | Provider vs. customer duties, handoffs, escalation owner |
| Remedies | Credits, escalation path, management review on breach |
| Types | Customer-based (per-org), Service-based (per-service, e.g., email support), Multi-level (corporate + customer + service) |

Typical internal tiers (Invgate / UCSF Enterprise SLA / NOCDOC ITIL baseline):

| Priority | Example | First response | Resolution |
|---|---|---|---|
| P1 Critical | Company-wide outage | 15 min (80% <15m per UCSF) | 4 hrs |
| P2 High | Team blocked | 1 hr | 8 hrs / 1 business day |
| P3 Medium | Single user blocked / workaround exists | 2–4 business hrs | 3 business days |
| P4 Low / Routine RITM | Standard request | 1 business day (online submit <24h) | 5 business days–30 days by catalog item |

> Broadcom 2024 survey (via Matrix42): **61% of orgs breach SLAs monthly or more** — SLA design is a capacity + prioritization problem, not just timers.

### 3.2 How Zammad implements SLA (open-source reference)

Source: `admin-docs.zammad.org — Manage > SLAs` + Zammad Features/SLA.

| Zammad concept | Behavior |
|---|---|
| Calendar | Business-hours base; multiple calendars per customer/level; 16h SLA on 8h/day = 2 business days |
| Ticket selector | Conditions (customer, org, group) decide which SLA applies; avoid overlapping SLAs |
| First Response | Once per ticket, from creation; not reset by group move |
| Update Time | Two modes: `between agent updates` (must reply every interval) vs. `for an agent to respond` (only after customer reply) |
| Solution Time | To closed-state; pending-close/reminder/closed freeze the clock; reopen can instantly escalate |
| Agent UX | Next-escalation timestamp + hover pop-up; warn ~15 min before + on escalation; `Escalated Tickets` overview (escalated + next 10 min) |
| Automation hook | Triggers / scheduler jobs to re-dispatch *before* escalation; single-level escalation only (community note: no native multi-level) |

**Omnilearn lab idea:** replicate P1–P4 + request SLAs in Zammad; show calendar math, freeze states, and pre-escalation trigger.

### 3.3 GLPI ticketing + assets (open-source reference)

| GLPI strength | Detail |
|---|---|
| Unified asset + ticket | Computers, peripherals, printers, network gear inventoried and assignable; ticket auto-links to asset |
| Source | `glpi-project.org`, `help.glpi-project.org`, GLPI 10 tutorials |
| Teaching value | Demonstrates CMDB-lite: assignment history enables return/revoke at offboarding; contrasts with ticket-only tools that lose asset context |

## 4. Least-Privilege (PoLP) & Access Reviews

Principle: every human / service / process gets **minimum access to do its job, nothing more** (Orca, Proofpoint, BeyondTrust, Okta, Rapid7, NCSC-NZ converge).

| Risk of over-provisioning | Evidence |
|---|---|
| Unused permissions = standing risk | Microsoft 2023 State of Cloud Permissions: workload identities use **<5% of granted permissions** |
| Chaining / lateral movement | Vulnerable app + `s3:* on *` → full-bucket read; Unit 42 2026: attackers moved via valid but over-provisioned paths, unused 60+ days |
| Drift | Roles/services change weekly; one tight policy decays without continuous right-sizing, JIT, and reviews |

| Control | How to teach it |
|---|---|
| Role-based + default-deny | Standard user by default; elevate per-task, time-bound (BeyondTrust, Imprivata) |
| Just-in-time (JIT) access | Provision privileged access for window/task only (NCSC-NZ) |
| Separate admin vs. daily accounts | Admin account for admin tasks only |
| Continuous audit | Quarterly permission audits; track authN/authZ; high-definition audits find termination gaps |
| Cover all layers | Users + apps + services + IoT/machine identities; discover shadow IT first |

## 5. Offboarding & Zombie / Orphaned Access

Definitions (Omada, BeyondTrust, Reco, Josys):

| Term | Meaning |
|---|---|
| **Orphan account** | Active account with no active owner (leaver/transfer, no deprovision) — unowned, over-provisioned, under-monitored |
| **Zombie account** | Looks inactive/disabled but still executes or retains background access (incomplete deactivation) |
| **Abandoned** | Generic idle; often SaaS seat still licensed |

| Cause | Detail |
|---|---|
| HR↔IT coordination gap | Manual revocation misses 1+ systems → partially disabled identity |
| AD/LDAP backend residue | Backend accounts most prone; survive migrations |
| M&A directory merges | Multiple directories → partially revoked identities |
| Grace-period neglect | "Keep awhile in case" becomes years |
| SaaS sprawl | Avg enterprise ~275 SaaS apps (Josys 2025); seats linger months/years |

| Consequence | Detail |
|---|---|
| Stealth foothold | No owner to flag anomalies; prized for lateral movement, privilege escalation, ransomware |
| Aged-out controls | No password rotation / MFA on legacy orphans; group policies stale → more access than intended |
| Cost | Unused licenses wasted |
| Compliance / insurance | GDPR/HIPAA/ISO 27001 failures; audit findings raise cyber-risk profile, hurt cyber-insurance renewal |

Fix playbook (BeyondTrust Identity Security Insights / Omada / CloudFuze):

1. Bring all creds under management (privileged first).
2. Automate provision/deprovision with trackable HR-driven workflows.
3. Granular role-based policies to narrow blast radius.
4. Least-privilege + Zero Trust + session monitoring + segmentation.
5. Reconcile directories vs. HR source; regular access reviews (privileged + high-impact first); ITDR for spray/MFA-fatigue/pass-the-hash.

## 6. Contradiction-Seeking — When Provisioning Fails

### C1. Over-provisioning directly enables breaches (provisioning breaches)

| Finding | Source |
|---|---|
| 27% of 2024 cloud breaches involved dormant credentials, many orphaned | Trustle citing major infosec study (via web research corpus) |
| ~80% of enterprise access breaches involve weak/stolen privileged creds; orphan + privileged = ideal target | Identity Management Institute |
| Insider threats = up to 20% of breaches; paths are excessive permissions + weak offboarding + unmonitored third-party | RFA / Cybersecurity Ventures / Anamo synthesis |
| Unit 42 2026: excessive trust + identity drift let intruders bypass controls without complex exploits | Palo Alto Unit 42 Global IR Report 2026 |

**Lesson:** "Grant generously for speed" trades Day-1 convenience for persistent attack surface. Omnilearn must teach birthright *minimal* bundles + JIT elevation, not blanket grants.

### C2. Auto-provision gone wrong — JML automation failures

| Failure mode | Example / mechanism |
|---|---|
| Mover accumulation (privilege creep) | Transfer adds new role without removing old; employee accrues cross-dept access over years; silent insider path (Deel, Netwrix, RoboMQ/Hire2Retire, Medium/CloudEagle) |
| Leaver partial-kill | AD disabled but SaaS/API tokens/shared drives/email delegates survive; ex-employee or attacker reuses (Lumos "unsecured employee access", LinkedIn offboarding guides) |
| Ticket-only JML gaps | Jira/ServiceNow tickets for disconnected systems never closed or verified; no nightly reconciliation → assumed-done, actually-open (Oleria: legacy ticketing leaves dangerous gaps) |
| Over-automation without reconciliation | Policy mis-match or connector failure silently skips systems; no retry/verify; rehire restores stale roles |

**Lesson:** automation without **remove-on-move, full-kill on leave, and verify-by-reconciliation** is worse than manual — it creates false assurance. Omnilearn labs should include a "failed mover" and "partial leaver" debugging exercise with reconciliation report.

## 7. ITSM Vendor Landscape (for course context)

| Vendor | Provisioning / onboarding story | Fit |
|---|---|---|
| ServiceNow (HRSD + ITSM + Lifecycle Mgmt) | Employee Journey Management; lifecycle events orchestrate cross-dept tasks | Enterprise reference; complex approvals |
| Jira Service Management | Portal request → per-team tasks/approvals; SLA timers, automation, Rovo AI routing | Mid-market reference; simpler approvals (community caveat) |
| Zammad (open-source) | Triggers, macros, webhooks, SLA calendars/escalations, overviews | Hands-on lab: SLA + automation without license cost |
| GLPI (open-source) | Asset inventory + ticketing + user/group admin in one | Hands-on lab: assign/track/return equipment |
| IGA add-ons (Oracle AG, OpenIAM, Omada, Lumos, Oleria) | Policy-based JML, connectors/APIs, reconciliation, peer-based recommendations | Show where ITSM tickets hand off to identity governance |

## 8. What This Means for Omnilearn Phase 1

| Module | Scenario to build |
|---|---|
| Request fulfillment | Catalog item "New-hire bundle" (laptop + accounts) with approval + asset link (GLPI model) |
| SLA | P1–P4 timers in Zammad; calendar math; freeze states; pre-escalation trigger; breach review at 90 days |
| Least-privilege | Birthright minimal role + JIT elevation; peer-comparison check on mover |
| Offboarding | Full-kill checklist (AD, SaaS, tokens, drives, delegates) + reconciliation query for orphans/zombies |
| Failure labs | Privilege-creep mover; partial leaver; overlapping SLAs; auto-provision connector failure |

## Sources (10 queries: 8 base + 2 contradiction-seeking)

| # | Query | Key source used |
|---|---|---|
| 1 | ITIL 4 service request management equipment provisioning | Matrix42 ITIL SRM; Freshworks SRM; Atlassian fulfillment process |
| 2 | ITSM account provisioning JML automation | Oracle Access Governance JML; OpenIAM; Oleria; Lumos; Cloudworks |
| 3 | ITIL ticketing SLA targets | Matrix42 SLM (Broadcom 61%); Atlassian SLAs; Invgate internal SLA; UCSF Enterprise SLA; NOCDOC |
| 4 | Orphaned / zombie access offboarding risk | CloudFuze; Omada; Josys (275 SaaS); BeyondTrust glossary; Reco; FedTech |
| 5 | Zammad SLA / automation docs | admin-docs.zammad.org `manage/slas`, Features/SLA, community #513, Elest triggers guide |
| 6 | GLPI asset + ticketing docs | glpi-project.org asset/ticketing pages; help.glpi-project.org; GLPI GitHub |
| 7 | Least-privilege / over-provisioning | Orca (MS <5% used); Proofpoint; BeyondTrust; Okta; Rapid7; NCSC-NZ; Imprivata |
| 8 | ITSM vendor onboarding comparison | Serval (ServiceNow vs JSM); Atlassian community; Virteva; ServiceNow community |
| C1 | Provisioning breaches (contradiction) | Trustle 27%; IMI 80%; RFA 20%; Unit 42 2026 |
| C2 | Auto-provision gone wrong (contradiction) | Privilege-creep (Deel/Netwrix/RoboMQ); Lumos unsecured access; Oleria ticketing gaps |

*Accessed Nov 2026 via web search + direct doc fetch (Zammad Admin Docs, Atlassian ITSM, BeyondTrust glossary). ITIL content via ITIL-4 practice summaries (PeopleCert/Matrix42) — official ITIL publications are paywalled.*
