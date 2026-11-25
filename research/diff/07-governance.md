# 07 — Governance / Safety Harnesses vs Ours (Cite-Before-Act + Hash-Bound Approval + Idempotency Ledger + Hash-Chained audit.jsonl)

> Our baseline (from `research/final/13-safety-audit.md` + `research/brainstorm/04-track2-safety.md`):
> **Cite-Before-Act proxy** (CITE → CHECK → ACT → RECORD, deny-closed) +
> **preview_hash binding** (`sha256(canonical_json(tool,args,schema_v))`, arg drift voids approval, `base_hash`/`If-Match` optimistic concurrency) +
> **double-approve for Class C** (2 distinct approvers or same-approver +30s cool-down, same `preview_id+preview_hash`, ≤10 min TTL) +
> **idempotency ledger** (Postgres PK `(actor_id,operation,key)`, `IN_PROGRESS/SUCCEEDED/FAILED`, fencing `lease_token`, commit-together rule, `409 CONFLICT` on key-reuse) +
> **`${ENV}` redaction** (resolve server-side, hash redacted form, `secret_leak_blocked` deny) +
> **hash-chained `audit.jsonl`** (`seq`, `prev_hash→hash = sha256(prev‖canonical(line))`, args never raw, denials logged, external head-anchor for truncation detection).
> Axes used below: **preview_hash binding? double-approve? redaction? tamper-evident chain?** (+ idempotency noted where relevant).

---

## 0. Scorecard (at a glance)

| Harness | Enforces (1-line) | preview_hash binding | Double-approve | Redaction | Tamper-evident chain | Idempotency |
|---|---|---|---|---|---|---|
| **1. Cite-Before-Act proxy** (MCP-1st-Birthday / bisonbet) | Transparent `tools/call` middleware: detect mutating → explain → multi-channel approve → execute/reject | ❌ (preview is human-readable text; approval token not cryptographically bound to arg bytes) | ❌ (single approve/reject + timeout, no destructive tier) | ⚠️ partial (two-tier `.env` + secret-regex; no hash-over-redacted-form rule) | ⚠️ append audit log but no hash chain / seq / verifier contract | ⚠️ `idempotency_key` echoed, sqlite store; no fencing / commit-together / conflict-vs-replay matrix |
| **2. MCP.STORE Keycloak + CEL** (`AgentgatewayPolicy`, wristband JWT) | Identity authN (JWKS, iss/aud/exp) + gateway CEL authZ per tool/target/claim + `tools/list` filtering | ❌ (CEL sees `mcp.tool.arguments` post-request but does not hash-bind approval to bytes) | ❌ (RBAC yes; no second-human / cool-down semantics) | ❌ (not its job; relies on downstream) | ❌ (Keycloak events ≠ per-decision tool audit chain) | ❌ |
| **3. DataHub Blackbox evidence gate** (`confirm_root_cause`, ACCEPTANCE.md) | No-repair-without-proven-cause: lineage + quantitative + exact-URN citations; verified repair → PR → writeback | ❌ (binds action to *evidence IDs*, not to arg hash; closest cousin to our cite rule but different object) | ❌ (gate is conjunctive-evidence, not N-human approvals) | ❌ | ⚠️ acceptance results committed + DataHub incident writeback; no hash-chained per-decision log | ❌ |
| **4. Solo.io agentgateway** (registry + signatures + CEL + audit) | Tool onboarding/fingerprint/version/sign → signature verify on `tools/list` (anti-poisoning/rug-pull/shadow) + JWT/CEL per-tool authZ + centralized audit | ❌ (integrity of *tool definition*, not of *this call's args*) | ❌ | ⚠️ CEL guardrails can mask/reject fields in-process, but no `${ENV}`-style canonical-redacted-hash rule | ⚠️ centralized audit log (who/what/args); not hash-chained, no seq/prev_hash verifier | ❌ (rate-limit, not exactly-once) |
| **5. AWS HITL lens** (Bedrock Agents + Step Functions + DynamoDB; Agentic-AI lens `AGENTSEC04-BP02`) | Decouple reasoning from high-stakes execution: pause on critical actions, approver gets full context, approve/deny/timeout (`deny` default), async resume | ❌ (approval keyed to task/step token; arg mutation between approve and execute not hash-checked) | ⚠️ partial (multi-level / SME review possible, but ad-hoc per-workflow, not a Class-C-by-default rule) | ⚠️ (IAM + redaction possible via policy, not built-in canonical rule) | ⚠️ (CloudTrail + DynamoDB record; mutable store, no hash chain; truncation not detectable without extra anchoring) | ⚠️ DynamoDB conditional-write gives de-dup if designed; no canonical request_hash + fencing + semantic-replay standard |
| **6. LangGraph `interrupt()`** (checkpoint + `Command(resume=)`, HITL middleware) | Pause graph anywhere, persist checkpoint, resume with human payload; `interrupt_before/after`, tool-approval / batch-approval patterns | ❌ (resumed payload re-enters state; no server-side re-derivation + hash-compare; known race: parallel-tool `durability="exit"` double-ask / double-run bug #9676) | ❌ (batch approval = 1 click for N calls; opposite of double-approve) | ❌ | ⚠️ checkpoints are resumable state, rewritable; no append-only hash-chained decision log | ❌ (checkpoints dedupe by thread/run, not by action-key + request-hash; replay can re-execute) |

Legend: ✅ ours-grade · ⚠️ partial / adjacent · ❌ absent.

---

## 1. Cite-Before-Act proxy (MCP-1st-Birthday `cite-before-act-mcp` / `bisonbet/Cite-Before-Act-MCP`)

**What it enforces.** Transparent FastMCP proxy wrapping any upstream (stdio) server. Pipeline `Client → Proxy → Middleware → Detection → Explain → Approval → Upstream`, with multi-method approval (dialog + Slack + file + Teams bot) and 300 s default timeout. Detection = allowlist + blocklist + naming convention (`create_*/update_*/delete_*/merge_*/push_*/*write*`) + description scan, **default-deny** (unknown = mutating). Reads stream through; mutating calls get an LLM-readable preview and block until explicit approve/reject. Two-tier secret config (`.env` defaults never committed + per-server client JSON with `${input:…}` refs; `load_dotenv` never overrides real env).

**What it lacks vs ours.**
- **preview_hash binding — NO.** Its "cite" is *citation-first UX* (show the call before acting), not a cryptographic receipt. No `sha256(canonical_json)` minted at preview, no server-side re-derivation + hash-compare at commit, no `base_hash`/`If-Match` concurrency check. Post-approval arg edits are a policy violation only if re-detected, not structurally void.
- **Double-approve — NO.** Single approve/reject per call; no Class B vs Class C split, no distinct-second-approver or 30 s cool-down, no ticket-ref requirement for destructive.
- **Redaction — PARTIAL.** Good hygiene (secret-regex `ghp_|xoxb-|sk-`, `--read-only` rehearsal flag, DuckDB file-access hardening) but no rule that *hash is computed over the redacted canonical form* and no `secret_leak_blocked` deny-on-secret-shaped-sink.
- **Tamper-evident chain — NO.** It appends an audit log (approve/reject entries), but lines carry no `seq/prev_hash/hash`, no genesis hash, no `firstBadSeq` verifier, no external head-anchor guidance. An edited history is undetectable.
- **Idempotency — WEAK.** Preview echoes an `idempotency_key` and sqlite caches results, but no `(actor,operation,key)` PK discipline, no `IN_PROGRESS` fencing/`lease_token`, no `SUCCEEDED-same-hash replay vs different-hash CONFLICT` matrix, no commit-together (business row + ledger + audit in one TX) rule.
- **Verdict:** adopt as the *proxy skeleton and demo UX* (detection table, explain text, Slack/dialog approval), then bolt our four hardeners on top: hash-bound receipts, Class-C double-approve, redacted-hash rule, hash-chained audit.

## 2. MCP.STORE / Keycloak JWT + CEL (`AgentgatewayPolicy`, wristband `x-authorized-tools`)

**What it enforces.** Enterprise authN/authZ at the gateway, not in each tool. Keycloak as MCP authorization server (OAuth 2.1 resource-server pattern, JWKS validation of `iss/aud/exp`, RFC 8707 resource indicators; one Keycloak client per MCP server so `aud` is meaningful; 2025-06-18+ needs `--features=cimd,resource-indicators`). Per-request CEL rules such as `mcp.tool.target == "admin-tools" && "admin" in jwt.roles`, with variables `mcp.tool.name/target/arguments`, `mcp.methodName`, `jwt.sub/roles/claims`. Signed wristband JWT (`x-authorized-tools`) filters `tools/list` so users only *see* tools they may call (least privilege, anti-confusion). Short-lived access + rotating refresh tokens; `403 insufficient_scope` with `WWW-Authenticate` challenge.

**What it lacks vs ours.**
- **preview_hash binding — NO.** CEL *authorizes who may call what*; it never mints a per-diff receipt or compares arg bytes at commit. `mcp.tool.arguments` is visible post-request but there is no approve-then-re-derive-and-hash-compare step — a TOCTOU gap ours closes.
- **Double-approve — NO.** RBAC/claims express *role*, not *N-human confirmations with cool-down on the same hash*. Achievable only by custom workflow above it.
- **Redaction — NO.** Out of scope; token claims and tool args flow through the gateway without a canonical-redaction + redacted-hash rule.
- **Tamper-evident chain — NO.** Keycloak events + gateway access logs record decisions but are mutable, unchained, per-system rather than per-decision canonical lines.
- **Idempotency — NO.**
- **Verdict:** keep as the **identity + coarse-authZ layer** (our §2 `JWTTokenVerifier + AuthSettings + per-tool scope middleware` is exactly this pattern). It answers *may this identity call this tool class*; our proxy answers *may this exact byte-string execute under this approval right now*. Complementary, not competing — stack them.

## 3. DataHub Blackbox evidence gate (`confirm_root_cause`, `ACCEPTANCE.md`, `ARCHITECTURE.md`)

**What it enforces.** The strongest *pre-mutation justification* of the six: `READ → PROVE → ACT → VERIFY → WRITE`. `confirm_root_cause` **rejects** unless citations include ≥1 DataHub lineage/metadata evidence + ≥1 quantitative evidence (profile diff / SQL count / baseline) + exact asset+field URN match (wrong-URN citation = reject) + `NO_INCIDENT` itself gated; repair scoped to an allowlist (`pipeline/transforms/*.sql`), branch `blackbox/fix-*`, revert-on-failed-verification, remote PR only after `VERIFIED`, DataHub marked resolved only after KPI check. `ACCEPTANCE.md` 22-gate harness (`positive_incident`, `control_no_incident`, `bad_repair_rejected`, `datahub_ablation`) committed with results. Facts are tool-created structs, never LLM free-typed.

**What it lacks vs ours.**
- **preview_hash binding — NO (adjacent).** It binds the *action to evidence IDs* ("prove why"), we bind the *execution to arg bytes* ("prove what exactly"). Both are cite-before-act in spirit; only ours voids approvals on byte drift and re-checks `base_hash` at commit.
- **Double-approve — NO.** Conjunctive-evidence (all four citation types) substitutes for N-human approvals; a destructive repair still needs only the gate + one execute decision, not two humans / cool-down / ticket ref.
- **Redaction — NO.** Evidence payloads (SQL, profiles, lineage) are logged verbatim; no secret-reference-by-name + redacted-hash discipline.
- **Tamper-evident chain — PARTIAL.** Acceptance results + DataHub writeback give *provenance*, but there is no per-decision `seq/prev_hash/hash` chain with a verifier and external anchor. History can be rewritten without detection.
- **Idempotency — NO.**
- **Verdict:** steal the **evidence gate as the justification half** of Class B/C (require `evidence_ids` alongside `preview_id` in the approval record and audit line), keep our **hash-bound approval + ledger + chain as the execution half**. Together: *why* (Blackbox) + *what-exactly + exactly-once + provably-logged* (ours).

## 4. Solo.io agentgateway (registration catalog + signature verification + CEL + audit)

**What it enforces.** Supply-chain + runtime governance for tool *definitions*: onboarding/registration workflow (fingerprint + version + sign every tool description), gateway verifies signatures on `tools/list` → blocks tool poisoning, rug-pulls, shadowing, name collisions before the agent ever sees them; description sanitization (strip directives, length-limit). Runtime: strict-auth-by-default, per-request JWT/CEL evaluation (`mcp.tool.name/target`, `jwt.*`), CEL guardrails that reject/mask calls in-process, rate-limiting, centralized audit (who called what with what args). Pairs with `agentregistry` (curated reusable artifacts) and Solo Enterprise onboarding/versioning/runtime policy.

**What it lacks vs ours.**
- **preview_hash binding — NO.** Integrity is of the *catalog entry* (this tool description is untampered), not of *this invocation's args under this approval*. Complementary axis: Solo stops a poisoned tool from appearing; we stop an approved call from silently mutating.
- **Double-approve — NO.** No N-human / cool-down / blast-radius-tiered approval model.
- **Redaction — PARTIAL.** CEL guardrails *can* mask fields, but there is no `${ENV:VAR}`-by-reference + hash-over-redacted-form + `secret_leak_blocked` deny contract.
- **Tamper-evident chain — NO.** Centralized audit log is queryable but mutable and unchained (no `prev_hash`, `seq` continuity check, or anchor guidance). Good for ops, insufficient for forensic non-repudiation.
- **Idempotency — NO** (rate limits ≠ exactly-once; no request-hash ledger).
- **Verdict:** adopt as the **tool-supply-chain front door** (registration, signing, poisoning defense, CEL coarse-authZ) and keep our proxy as the **per-call execution gate** behind it. The two "hashes" compose cleanly: theirs pins *which tool version*, ours pins *which arg bytes*.

## 5. AWS HITL lens (Bedrock Agents + Step Functions + DynamoDB; Agentic-AI lens `AGENTSEC04-BP02`, governed observable loop)

**What it enforces.** The most production-hardened *human-pause pattern*: decouple reasoning from high-stakes execution; route money/data/external-comms actions through an approval step where the reviewer sees proposed action + agent rationale + context; async pause/resume with approval keys, `approvalTimeout` (e.g. `{after: 1h, action: deny}` — deny-by-default), multi-level/SME review, offline review queues. Surrounding lens adds IAM permission boundaries, CloudTrail observability, policy-as-code (permit-if-A/B/C) instead of burying authZ in app code. re:Invent CNS428 pattern: asynchronous multi-agent workflows with explicit HITL control points.

**What it lacks vs ours.**
- **preview_hash binding — NO.** Approval is keyed to a *task/step token*; nothing recomputes `sha256(canonical args)` at execute time and voids the approval on drift. The reviewer approves intent; the bytes can still shift underneath.
- **Double-approve — PARTIAL.** Multi-level review is expressible per-workflow, but there is no standing Class-C rule (distinct second approver or same-approver-after-30 s + ticket ref + `If-Match: base_hash`, all citing the same hash). Each team re-invents it.
- **Redaction — PARTIAL.** Achievable via IAM/policy + payload filtering, but no built-in canonical-redaction + redacted-hash + sink-deny contract.
- **Tamper-evident chain — NO.** CloudTrail + DynamoDB give durable searchable history, but both are mutable stores without a hash chain / `firstBadSeq` verifier / external-anchor story. Tampering is an IAM-control problem, not a structurally-evident one.
- **Idempotency — PARTIAL.** DynamoDB conditional writes *can* implement de-dup, but there is no standard `(actor,operation,key)+request_hash` ledger with `IN_PROGRESS` fencing, `CONFLICT`-on-different-hash, commit-together, and semantic-replay rules.
- **Verdict:** borrow the **operational semantics** (deny-by-default timeouts, reviewer context bundle, async queues, policy-as-code) and implement them *over* our hash-bound receipts and ledger. AWS tells you where to pause; we tell you what makes the pause cryptographically meaningful.

## 6. LangGraph `interrupt()` (+ checkpointer, `Command(resume=)`, HITL middleware)

**What it enforces.** The cleanest *developer primitive* for pauses: call `interrupt({question, tools})` inside any node; run halts, checkpoint persists, app collects human payload, `Command(resume=…)` continues exactly where it left off. Supports `interrupt_before/after`, tool-approval, batch approval, and durable execution across restarts. Minimal code, framework-native, works with any checkpointer (memory/Postgres).

**What it lacks vs ours.**
- **preview_hash binding — NO.** Resume payload re-enters graph state without server-side re-derivation + canonical-hash comparison. Approval is *control-flow resumption*, not *a receipt for one diff*. There is even a known soundness bug class (parallel tool calls + `durability="exit"` under `HumanInTheLoopMiddleware`: approved call re-asked and run twice / pending approval lost in `PregelLoop.put_writes` race, issue #9676) — exactly the double-execute our ledger rules out.
- **Double-approve — NO (anti-pattern present).** Batch approval approves N calls with one click — the inverse of Class-C double-approve. No distinct-approver, cool-down, TTL, or same-hash-citation semantics.
- **Redaction — NO.** State snapshots persist raw args; no redacted-canonical-hash rule.
- **Tamper-evident chain — NO.** Checkpoints are *rewritable resumable state*, not append-only evidence. No `seq/prev_hash/hash`, no denial logging, no verifier.
- **Idempotency — NO.** Dedupe is by thread/run checkpoint, not by `(actor,operation,key)+request_hash` with fencing and conflict-vs-replay distinction — so retries can re-mutate.
- **Verdict:** use `interrupt()` as the **pause/resume UX primitive inside the agent**, but never as the safety boundary. The safety boundary stays in our proxy: LangGraph pauses for a human string; the proxy mints the preview, binds the hash, checks the double-approval, enforces idempotency, and writes the chained audit line. Demo both: interrupt collects `APPROVE <preview_id>`; only the proxy may act on it.

---

## 7. What ours uniquely contributes (the delta worth defending)

1. **Hash-bound approval (receipt for one diff).** `preview_hash = sha256(canonical_json(tool, args, schema_version))`; approval cites `(preview_id, preview_hash)`; server re-derives and hash-compares at commit; any byte drift → `preview_hash_mismatch` deny; `base_hash`/`If-Match` closes the read-to-write race. None of the six has this.
2. **Tiered double-approve by default.** Class B = 1 approval; Class C (destructive/bulk/scope-escalating) = 2 approvals citing the same hash + cool-down + ticket ref; ambiguous = deny-closed. The six offer single-approve (CBA, LangGraph), RBAC (Keycloak, agentgateway), evidence-conjunction (Blackbox), or ad-hoc workflow review (AWS) — none has the standing destructive tier.
3. **Redaction with stable hashes.** Secrets only as `${ENV:VAR}`, resolved server-side at invoke, redacted at every sink, hash computed over the redacted form, `secret_leak_blocked` deny on leak. The six have regexes, masking, or IAM — none ties redaction to hash stability.
4. **Tamper-evident per-decision chain.** One `audit.jsonl` line per decision *including denials*, `args_hash` never raw args, `seq + prev_hash → hash` with `firstBadSeq` verifier and external head-anchor for truncation detection. The six have logs, trails, checkpoints, or writebacks — none has the chain.
5. **Ledger-grade idempotency.** `(actor_id, operation, key)` PK + `request_hash`, `IN_PROGRESS/SUCCEEDED/FAILED` + `lease_token` fencing, commit-together rule, full replay-vs-conflict matrix, semantic-replay corollary. The six have keys, caches, conditional writes, or checkpoints — none has the full contract.

**Recommended stack (no false choices):** Solo.io registry (trusted tools) → Keycloak/CEL (right identity, right tool class) → Blackbox gate (proven cause + evidence IDs) → **our proxy** (hash-bound approval + double-approve + ledger + redacted chain) → AWS HITL ops (queues, timeouts, reviewers) with LangGraph `interrupt()` as the in-agent pause primitive and CBA proxy as the code skeleton.

---

## Sources

- Prior files: `research/final/13-safety-audit.md` (§§1–9: proxy, AuthSettings+JWT, detection table, UX strings, idempotency binding, `${ENV}` redaction, ambiguous-scope/double-approve, hash-chained audit schema); `research/brainstorm/04-track2-safety.md` (§§1–8: golden rule, CBA Pattern A/B, Keycloak+CEL, secret handling, idempotency, Blackbox evidence gate, scaffold).
- Cite-Before-Act: `MCP-1st-Birthday/cite-before-act-mcp` HF Space + `bisonbet/Cite-Before-Act-MCP` GitHub (proxy, detection/explain/approval/middleware, 300 s timeout, two-tier `.env`, Teams/Slack/file approvals).
- Keycloak/CEL: `keycloak.org/securing-apps/mcp-authz-server` + Keycloak `mcp-authz-server.adoc`; `agentgateway.dev` MCP auth/tool-access/mcp-authz docs; Red Hat connectivity-link Ch.6 (wristband `x-authorized-tools`); `modelcontextprotocol.io` authorization tutorial (2026-07-28); `aaif.io` enterprise-managed MCP authorization.
- Blackbox: `alejandro-publius/blackbox-datahub` (`docs/ARCHITECTURE.md`, `ACCEPTANCE.md`, `JUDGE_SCORECARD.md`, `CLAUDE.md`) + DataHub blog "Meet the 2026 Winners".
- agentgateway: `solo.io/products/agentgateway`, `solo.io/blog/prevent-mcp-tool-poisoning-with-registration-workflow`, `…/introducing-solo-enterprise-for-agentgateway`, `…/enterprise-challenges-with-mcp-adoption`, `docs.solo.io/agentgateway` (tool-access, mcp-authz/authn, CEL guardrails).
- AWS HITL: `aws.amazon.com/blogs/architecture/inside-an-enterprise-ai-agent-a-governed-observable-loop-architecture`; Builder Center Bedrock Agents HITL with Step Functions+DynamoDB; `aws.amazon.com/blogs/machine-learning/implement-human-in-the-loop-confirmation-with-amazon-bedrock-agents`; `AGENTSEC04-BP02`; re:Invent 2025 CNS428; AgentExpress `Human_in_the_Loop.md` (`approvalTimeout … deny`).
- LangGraph: `docs.langchain.com/oss/python/langgraph/add-human-in-the-loop`; `langchain-ai/langchain-skills` HITL skill; `interrupt()`/resume + checkpointer guides; issue #9676 (`durability="exit"` parallel double-run race).
