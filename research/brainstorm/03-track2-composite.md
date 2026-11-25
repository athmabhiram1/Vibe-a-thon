# Track 2 Brainstorm — One Smart Tool from Many Small Functions

> Constraint: **Synapse Custom, Python only, one `@mcp.tool` per build.** Each build exposes exactly ONE agent-callable tool. All helper logic stays as plain private `def _...()` functions fused inside. Pattern verified in FastMCP docs: `@mcp.tool` returns the original function unchanged, so decorated helpers stay directly callable for testing/reuse/composition (`greet("World")` still works). Each design below follows **Detect → Validate → Dry-run preview → Explicit confirmation → Execute → Receipt**.
>
> Research grounding:
> - Winners that fused beats winners that sprayed: PitchScoop won with 32+ tools but judges flagged tool-sprawl fatigue; OrbitCast (1st, ESA EO hackathon), PRISM (AI Engineer NYC — "decisions to approve, not paragraphs"), WebMCP overall winner (RBAC-gated tools) all won by *reducing* surface area.
> - MCP 1st Birthday **Best Overall: Cite-Before-Act** (`bisonnetworking`) = the safety-middleware template to copy: multi-strategy mutating-tool detection (allowlist/blocklist + `create_/delete_/send_` naming + description keywords) → natural-language preview → concurrent approval (native dialog / Slack buttons / file-based, first-response-wins) → execute-or-reject. Copy this as in-tool `confirm=` gate, not as separate tool.

## Global Build Template (copy-paste per tool)

```python
from fastmcp import FastMCP
from pydantic import BaseModel, Field
mcp = FastMCP("track2-composite")

# 5-8 private helpers — NOT tools, never decorated
def _fetch(...): ...
def _validate(...): ...
def _check_policy(...): ...
def _price_or_compute(...): ...
def _preview(...)-> str: ...   # Cite-Before-Act style dry-run
def _execute(...): ...
def _receipt(...): ...

class In(BaseModel): ...
class Out(BaseModel):
    ok: bool
    preview: str
    receipt_id: str | None
    errors: list[str]
    citations: list[str]  # policy DOC ids / row ids acted on

@mcp.tool
def smart_verb(...) -> Out:
    """ONE public tool. Requires confirm=True with preview hash."""
```

Submission angle for ALL: **1-tool vs many-tools table** — count tool-calls (1 vs 6-8), show agent can't skip policy step, can't half-execute, gets deterministic receipt + citations. Judges love "we deleted 7 tools."

---

## 1. `adjudicate_claim` — insurance / warranty claim adjudicator

**Why non-obvious:** everyone demos "summarize claim." This one *pays or denies with audit trail* — money movement + fraud gate in one call.

- **Fused (6):** `_fetch_claim` → `_fetch_policy` → `_check_coverage` → `_score_fraud` (velocity, duplicate, amount-spike rules) → `_compute_payout` (deductible, cap, depreciation) → `_preview+_execute+_receipt` (ledger append + status flip, idempotency key = claim_id).
- **Params:** `claim_id: str, confirm: bool=False, preview_hash: str|None, override_reason: str|None (requires supervisor flag)`.
- **Error branches:** claim not found → `CLAIM_404`; policy lapsed at incident date → deny with citation; missing evidence (photos/invoice) → `NEEDS_EVIDENCE` listing exactly what's missing; fraud_score>0.8 → hard-block + route to SIU, no confirm accepted; duplicate payout (idempotency hit) → return prior receipt; amount exceeds auto-limit ($5k) → require `override_reason`.
- **Confirmation:** dry-run preview shows: coverage clauses cited, deductible math, payout amount, fraud score + reasons. Returns `preview_hash`; execute requires `confirm=True + preview_hash` match. Cite-Before-Act style: "Pay $1,240.00 on CLM-881 (deductible $500, cap $10k, clauses §4.2, §7.1, fraud 0.12). Approve?"
- **1 vs many:** many-tools = 6 calls (get_claim, get_policy, check_fraud, calc, pay, notify) where agent can pay before fraud check. 1-tool = ordering enforced in code; demo shows agent attempting to skip → impossible.

## 2. `reconcile_shipment` — 3-way receiving match (PO ×ASN × scan)

**Why non-obvious:** not "track package" — resolves the warehouse dock problem: over/short/damaged/substituted in one decision.

- **Fused (7):** `_fetch_po` → `_fetch_asn` → `_fetch_scan` (handheld counts) → `_three_way_match` (qty, SKU, lot, temp excursion) → `_tolerance_policy` (±2% or ±1 unit, hazmat zero-tolerance) → `_disposition` (accept / short-claim / quarantine / refuse) → `_post_receipt` (inventory + claim draft).
- **Params:** `po_id, asn_id, scan_batch_id, confirm=False, preview_hash, allow_partial: bool=True`.
- **Error branches:** SKU substitution (ordered A, shipped B) → `SUBSTITUTION` quarantine; temp excursion on cold-chain → auto-quarantine regardless of tolerance; scan count missing bins → `INCOMPLETE_SCAN` with bin list; PO closed → `PO_CLOSED`; ASN duplicate → idempotent return.
- **Confirmation:** preview table: ordered vs shipped vs received per line, variance %, disposition per line, claim $ if short. Confirm posts inventory movement + creates supplier claim draft atomically.
- **1 vs many:** many-tools = agent must juggle 3 documents across 5 calls and often posts receipt before filing shortage (money lost). 1-tool = match-then-post atomic; comparison angle: "no silent shrinkage."

## 3. `discharge_patient_ops` — discharge *operations* (explicitly NOT diagnosis)

**Why non-obvious + safe:** deliberately avoids diagnosis/treatment advice. Pure logistics: bed turnover, transport, meds-to-bed, follow-up, paperwork. Judges + safety reviewers love the scoping.

- **Fused (7):** `_fetch_encounter` → `_check_discharge_order` (physician order must exist — else hard stop) → `_meds_to_bed` (pharmacy queue) → `_book_transport` (ambulance vs family pickup) → `_book_followup` (slot search) → `_print_packet` (AVS + instructions in patient language) → `_release_bed` (housekeeping task).
- **Params:** `encounter_id, transport_mode: Literal[family, rideshare, wheelchair_van, bls], language: str="en", confirm=False, preview_hash`.
- **Error branches:** NO discharge order → `NO_ORDER` block (never overridable); controlled-substance prescription needs ID check → `ID_REQUIRED`; no follow-up slot within 7d → escalate + still allow discharge with `followup_pending`; transport ETA >2h → offer downgrade/upgrade; bed already released → idempotent.
- **Confirmation:** preview checklist with owner + ETA per item (pharmacy 25 min, van 40 min, follow-up Tue 10:00, bed H-312 → cleaning). Confirm books all + releases bed. Every step cites order ID, never a diagnosis code.
- **1 vs many:** many-tools = agent discharges bed before pharmacy ready (patient waits in lobby). 1-tool = topological order enforced; angle: "ops composite that refuses to practice medicine."

## 4. `onboard_employee_guarded` — hiring onboarding with guardrails

**Why non-obvious:** fuses HR + IT + legal + payroll with *least-privilege by default* and background-check gate.

- **Fused (8):** `_verify_offer` (signed offer + work auth) → `_background_check_gate` (pending/fail = block) → `_pick_role_bundle` (least-privilege RBAC from level+dept matrix) → `_provision_accounts` (IdP, email, HRIS, payroll — staged, not active) → `_assign_equipment` (inventory hold) → `_schedule_training` → `_preview` → `_activate_day_one`.
- **Params:** `candidate_id, start_date: date, role_code, manager: str, confirm=False, preview_hash`.
- **Error branches:** background `PENDING` → `BG_PENDING` (can stage, cannot activate); work-auth expiry <90d → `VISA_RISK` warning + HR ticket; role_bundle unknown → fail closed to `baseline_readonly`; duplicate employee record (rehire) → merge path; start_date is weekend/holiday → auto-shift + note.
- **Confirmation:** preview shows every account + permission + equipment serial + training plan with "least-privilege diff" vs requested. Confirm activates at 00:00 start_date; before that everything is staged-reversible.
- **1 vs many:** many-tools = agent provisions admin on day -5 because it called tools in wrong order. 1-tool = stage-then-activate; angle: "guardrailed composite beats 8-tool footgun," RBAC angle echoes WebMCP winner.

## 5. `refund_with_policy_gate` — refund that *cannot* violate policy

**Why non-obvious:** policy engine is *inside* the tool, cited per decision — agent never sees raw card rails.

- **Fused (6):** `_fetch_order` → `_fetch_payments` → `_evaluate_policy` (window 30d, final-sale list, restocking 15% opened electronics, fraud velocity) → `_compute_amount` (prorate, fee, restock) → `_preview` → `_execute_refund+_receipt` (idempotency = order_id+item_id).
- **Params:** `order_id, items: list[{sku,qty,reason,condition}], confirm=False, preview_hash, goodwill: bool=False (requires manager note)`.
- **Error branches:** outside window → deny with `POLICY §3.1` citation + offer store-credit path; final-sale SKU → hard deny; already-refunded line → idempotent prior receipt; amount >$500 or 3rd refund/90d → manager-approval branch; payment captured=false → void instead of refund (different rail).
- **Confirmation:** preview: per-line eligible/denied + rule cited, restocking math, total, destination (orig card ****1234). Confirm executes once; double-confirm returns same receipt.
- **1 vs many:** many-tools = refund-then-check-policy (money already moved). 1-tool = policy-before-rails; angle: live demo where agent is *prompt-injected* to "just refund it" and tool still denies — best judging moment.

## 6. `sunset_vendor` — vendor offboarding (NON-OBVIOUS pick #1) ⭐ recommended build

**Why it wins:** nobody demos offboarding; every enterprise feels the pain (zombie SaaS spend, lingering access). High "why didn't this exist" score.

- **Fused (7):** `_fetch_contract` → `_spend_audit` (last 12 mo invoices + seats) → `_access_inventory` (SSO apps, API keys, shared drives) → `_data_export` (retention per DPA) → `_final_settlement` (prorate, early-term fee) → `_revoke_all` → `_archive`.
- **Params:** `vendor_id, termination_date: date, confirm=False, preview_hash, retain_data_days: int=30`.
- **Error branches:** auto-renew in <14d → `RENEWAL_TRAP` urgent flag + cancel-renewal subtask; API key still in prod → block revoke until rotated, emit `ROTATE_FIRST`; DPA requires 90d retention but asked 30d → clamp + cite; open POs against vendor → list, require close-or-transfer; sole-owner of critical integration → `SINGLE_POINT` escalation.
- **Confirmation:** preview: spend killed ($/yr), access revoked (n keys, m accounts), data retained until date, final bill/credit. Confirm executes revoke+archive atomically, returns spend-saved receipt.
- **1 vs many:** many-tools = IT revokes SSO but API key lives on for 2 years (breach). 1-tool = inventory-then-revoke completeness proof; angle: "the composite that actually deprovisions."

## 7. `quarantine_dataset` — data-incident freeze + lineage trace (NON-OBVIOUS pick #2) ⭐ sleeper hit

**Why it wins:** data-quality + governance in one tool; demos beautifully with fake lineage graph; zero PII touched.

- **Fused (6):** `_fetch_incident` (dq alert, schema drift, suspected leak) → `_trace_lineage` (upstream tables + downstream dashboards) → `_freeze` (revoke write, snapshot, tag `quarantined`) → `_notify_owners` (draft, not send until confirm) → `_suggest_rollback` (last-good snapshot id) → `_receipt`.
- **Params:** `dataset_id, incident_id, confirm=False, preview_hash, include_downstream: bool=True`.
- **Error branches:** dataset already quarantined → idempotent; downstream prod dashboard affected → `PROD_IMPACT` warning + page owner; no clean snapshot → `NO_ROLLBACK` (freeze only); incident is false-positive (dq rule misconfigured) → `LIKELY_FP` with evidence, still allow confirm; PII columns present → add `PII_MASK` note, never echo values.
- **Confirmation:** preview: blast-radius graph (3 upstream, 5 downstream), freeze scope, notifications queued, rollback target. Confirm freezes + queues notices.
- **1 vs many:** many-tools = analyst freezes table but forgets 5 downstream dashboards still serving bad data. 1-tool = lineage-aware freeze; angle: "composite with blast radius."

---

## Submission Strategy (all builds)

1. **Pick 1 of 7** per repo (one `@mcp.tool` each). Recommended: `sunset_vendor` (most novel) or `refund_with_policy_gate` (easiest to seed + best prompt-injection demo).
2. **Seed data:** small `seed.json` (orders/vendors/claims/POs) + `policies.md` with `§` citations the tool echoes. Citations = Cite-Before-Act credibility.
3. **Demo script:** show many-tools failure (agent skips step / wrong order / double-pay) → show 1-tool success with preview → confirm → receipt. 90 seconds.
4. **Safety slide:** detection (mutating? yes) → preview → `confirm+preview_hash` → idempotency → receipt. Name-drop Cite-Before-Act Best Overall + PRISM "decisions, not paragraphs."
5. **FastMCP note for README:** helpers are plain functions, only one `@mcp.tool`; decorated function stays callable → unit-test helpers directly. Include `1-tool vs 7-tools` call-count table.
