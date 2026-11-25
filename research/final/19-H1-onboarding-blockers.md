# H1 — Onboarding Day-1 Blockers Span HR+IT Join

**Claim:** The dominant Day-1 onboarding failures are not form UX but join-dependent blockers spanning HR (offer/ID/payroll record) + IT (laptop, SSO, app provisioning). Fixing the form alone does not unblock Day-1 productivity.

**Null (H0):** Day-1 blockers are contained within a single domain (HR form completeness); IT provisioning succeeds independently once the form is submitted, with join-failure rate ≤10%.

**Falsification criterion (specific observation that kills H1):** In a sample of ≥20 recent onboarding tickets/cases OR a 5-user concierge walkthrough, if ≥80% of Day-1 failures resolve with form-only fixes and zero cases require both HR-record + IT-provisioning coordination (i.e., no cross-system wait, no manual join on employee ID/email), H1 is FALSIFIED.

**Alternative (if falsified):** Build a single-domain form-autofill agent (Track 1 legacy scope); drop cross-system orchestration and approval-join logic.

**Priority:** P0 — must verify before Track 1 scope lock. If true, it justifies a composite join-agent; if false, scope shrinks 50%.

**Verification method:**
1. Ticket-log sample: pull last 20–30 IT/HR Day-1 tickets; code each as HR-only / IT-only / join (needs both + time-wait).
2. Concierge test: 5 mock new-hires attempt Day-1 checklist (SSO login, payroll confirm, laptop setup, app access); log blocker location + resolution time.
3. Threshold: H1 holds if ≥40% of cases are join-type AND ≥3/5 concierge users hit a join blocker.

**Expected outcome:** ≥3/5 users blocked on join step (e.g., SSO exists but payroll ID missing; laptop ready but account not provisioned); ticket sample shows 40–60% join-type. Action on confirm: design Track 1 agent around employee-ID join + status dashboard + nudge/HR-IT handoff.
