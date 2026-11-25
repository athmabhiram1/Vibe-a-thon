# 20 — Open Questions + Build Recommendations (Start-Building Brief)

Date: 2026-11-22 | Source of truth: `guide.txt` (Vibe-a-thon Participant Guide, Oct 2026, 8 pp.) + `research/brainstorm/08-tech-feasibility.md`, `09-judge-fit.md`, `10-track-choice.md`
Status: Pre-build gate. Answer P0 questions before `synapse init`; P1 before demo record.

---

## 1. Falsifiable open questions

Each question states the exact evidence that closes it. Priority: **P0** = blocks Day-1 build choices; **P1** = blocks demo/judging packet; **P2** = nice-to-have polish.

| # | Question (falsifiable) | Why it blocks building | Evidence that answers it (where to look) | Priority |
|---|---|---|---|---|
| Q1 | **Quota: is the free tier really 10 MCP servers + 100,000 indexed lines per account, and do `--local` builds bypass it?** | Determines hosted-vs-local split, how many rebuilds we can afford, whether T3 (2 servers + `--discover` loop) is safe on one account. | `synapse info` output on our key (screenshot remaining quota) + re-run after 1 hosted build + 1 `--local` build; confirm hosted decrements, local does not. Guide p.7 asserts this — verify empirically. | **P0** |
| Q2 | **Does `Synapse --local` write a runnable file ONLY for Python projects, and produce tool-names-only (no file) on TS/Java/C#/Go/Rust?** | Decides language: if true, non-Python T1/T3 entries have no offline fallback and must burn hosted quota. | Build minimal FastAPI app + minimal Express/TS app each with `synapse build --local`; record: file written? (`synapse_auto_server.py` vs nothing). Guide p.5 asserts limit — reproduce. | **P0** |
| Q3 | **Custom mode: Python-only — confirmed? Can a Custom composite tool be built from a TS/Java repo at all?** | Kills-or-confirms T2 language options and whether T3's composite piece must be Python. | `synapse build --custom -q "<desc>"` inside a TS repo; record accept/reject error. Guide p.4 table says Custom = Python only. | **P0** |
| Q4 | **What is the allowed team size (min/max), and must all members register before deadline?** | Determines whether to recruit to 3–4 or stay lean; affects track choice (T3 needs 3 roles). | Official hackathon registration page / Devpost / Geek Room announcement + organizer DM. Guide PDF is silent — do not assume 2–4. | **P0** |
| Q5 | **Who are the judges, what is the scoring rubric weight per criterion, and is judging live, async video, or both?** | T3's live-`--discover` moment only pays off live; async judging rewards pre-recorded reliability + README packet instead. Safety-track (T2) weight determines eval-set investment. | Judging section of event site + past Vibe-a-thon 1.0/2.0 rubric (`research/winners/05-vibe12.md`); ask organizers for rubric weights (e.g., usefulness x%, tool-choice x%, reliability x%). | **P0** |
| Q6 | **Prize split: total pool, per-track vs overall, cash vs credits vs kind, split per team or per head, tax/transfer mechanics?** | Determines effort allocation (overall-win swing for T3 vs safe track-prize T2) and whether to dual-enter. | Prize page + rules fine print; confirm with organizer message. Guide PDF lists no prizes. | **P0** |
| Q7 | **Track eligibility: one track per team only, or can one repo enter T3 + T4 (T3 demo inside T4 thesis)?** | Enables/disables the recommended hedge (primary T3, backup T2/T4 reuse). | Rules FAQ / organizer confirmation in writing. | **P0** |
| Q8 | **Does `synapse build --discover` rescan only changed files, preserve server ID/client config, and what breaks it (new routes ignored until rescan)?** | Core T3 demo mechanic — live endpoint add must work on camera in <60s. | Controlled test: build → add 1 route → rebuild without `--discover` (assert route missing) → `synapse build --discover` (assert route present, same server ID). Time it 3×. Guide p.5 asserts behavior — measure latency. | **P0** |
| Q9 | **Hosted Auto output shape: truly no file (config in Synapse account via `@2ndbrainlabs-ai/synapse-mcp` runner), vs Custom/local writing `<tool>_server.py`?** | Determines repo layout, what we submit, and offline-fallback story. | Run one hosted Auto build + one Custom build; record artifacts (server ID + npx snippet vs `.py` file). Guide pp.4–6 asserts this. | **P0** |
| Q10 | **Which MCP clients must the demo support (Claude Desktop AND Cursor AND any-MCP, or one suffices)? Does venue/judge machine have Node 20+, Python 3.10+, `uv`, network for npx?** | A hosted-Auto demo dies if judges can't run the npx runner; a `.py` stdio demo dies on PATH issues. | Test both snippets on clean laptop: hosted npx snippet + `uv run` stdio snippet; record cold-start time, failures. Guide p.6 (Node 20+, paste-snippet-don't-handwrite). | **P1** |
| Q11 | **What leaves the machine per mode (hosted Auto sends routes+docstrings; `--smart-names`/Custom also sends source; `--local` sends nothing to Synapse)?** | Determines whether we can use real civic/health/claims code or must use synthetic data; privacy story for judges. | Guide p.7 "Know what leaves" + Wireshark/`--help` inspection + `SYNAPSE_TELEMETRY=0` test. Confirm local truly zero-egress with network-off build. | **P1** |
| Q12 | **Small-model floor: which `--local` provider/model reliably emits `emit_tool_plan` (Ollama `qwen2.5-coder:7b` vs `gemma3:4b` vs hosted frontier)? What `num_ctx` is required?** | Picks the pinned offline model; weak models throw `returned no emit_tool_plan call` (Guide p.8). | Matrix test per `08-tech-feasibility.md §6`: 3 models × 2 ctx sizes (8K/32K); record success rate, TTFT, `ollama ps` GPU/CPU split. | **P1** |
| Q13 | **Original-app constraint (T1: "no changes to original app's code") — enforced how, and does adding a route for the T3 live-update violate it?** | T3's live-update *requires* adding an endpoint on camera; must confirm this is legal in T3 (vs T1's freeze). | Guide p.2 wording (T1 freeze vs T3 "add a new endpoint, rebuild") + organizer clarification; keep `git diff` of original vs added file as proof. | **P1** |
| Q14 | **Submission bundle: repo + generated MCP setup + demo video length/format + write-up — exact checklist and deadline timezone?** | Prevents last-day disqualification on missing artifact (server ID, comparison table for T2, two dual-system questions + live-update clip for T3). | Checklist per track on event site (Guide pp.2–3 per-track "Submit" lines) + submission portal dry-run upload. | **P1** |
| Q15 | **Plain-JS exclusion: are `.js/.jsx` repos truly unscanned — does renaming/wrapping as TS change detection?** | Kills any plan to Synapse-wrap an existing JS codebase without a TS/Python port. | `synapse build` inside a plain-JS repo; record 0-routes result (Guide p.4 asserts). | P2 |

Dropped/non-questions: exact API-key issuance latency (answer by just requesting key now); telemetry opt-out (already documented `SYNAPSE_TELEMETRY=0`).

---

## 2. Recommendations — decisions with tradeoffs, next actions, drop tripwires

Convention: **Decision: choose X over Y.** Then tradeoffs, then next actions (`Verb + Artifact + Owner`), then numeric drop condition (tripwire that kills the decision).

### R1. Track: choose T3 primary (2 systems + live `--discover`) over T1 (crowded) — keep T2 branch as hot backup, do not start T4
- **Why:** Per `10-track-choice.md` weighted scoring T3 (28) > T4 (24) > T2 (22) ≫ T1 (12). T3 is the only "arena moment" (live discovery) that wins overall; T1 is a polish lottery; T4 adds centrality-proof burden. T2 reuses 80% of T3 work (FastAPI + eval harness) so the hedge is cheap.
- **Tradeoffs:** T3 costs 2–3 weeks + live-failure risk vs T2's 1-week safety. Mitigate with R6 fallback stack (cached mode + video).
- **Next actions:** (1) Freeze track memo (1-pg `decision-track.md` + owner: lead) by Day 2. (2) Scaffold both FastAPI systems (repos + `/docs` green + owner: backend) by end Wk1. (3) Draft T2 composite-tool spec in parallel (owner: safety) so pivot <1 week.
- **Drop condition:** If Q8 test shows `--discover` median latency >90s over 5 trials OR success <3/5, downgrade T3→T2 primary within 48h.

### R2. Language: choose Python/FastAPI for BOTH graded systems over TS/Java/Go/C#/Rust
- **Why:** Only Python gets runnable `--local` file output (Q2), Custom composites (Q3), and full MCP file artifacts — everything else is hosted-runner-only with no offline fallback. `09-judge-fit.md` mandates Python for the same reason.
- **Tradeoffs:** Forgoes "legacy Java/C#" narrative realism; gains reproducibility + offline story. If a legacy narrative is wanted, frame FastAPI systems as "the modernized slice" — judges score agent-usefulness, not legacy authenticity (Guide p.3: "small sample apps are fine").
- **Next actions:** (1) Create `system-a/` + `system-b/` FastAPI repos with `operation_id=` + Pydantic models (owner: backend). (2) Record `/openapi.json` cleanliness screenshot per system (owner: backend).
- **Drop condition:** If either system needs a non-Python dependency that blocks `synapse build --local` file emission (0 `.py` files over 2 attempts), port that slice to Python rather than burning hosted quota — abort non-Python path.

### R3. Server adapter: choose curated `FastMCP.from_fastapi` allowlist (≤10 tools) over raw auto-expose-all
- **Why:** Per `08-tech-feasibility.md §4`, both vendors warn auto-converted REST→MCP bloats tool UX and confuses agents. Judges explicitly score "which endpoints you chose and why" (T1) / tool design (T2) / combined-answers (T3). `include_operations` allowlist + `--smart-names` wins points.
- **Tradeoffs:** More curation labor vs one-flag `--all-endpoints` speed. Use `--all-endpoints` only for Day-1 smoke test, then curate.
- **Next actions:** (1) Publish endpoint allowlist with 1-line why-per-tool (`tools.md` + owner: backend). (2) Rebuild with `--smart-names` and diff tool names (owner: backend).
- **Drop condition:** If agent tool-selection accuracy <70% on 10 scripted tasks with full exposure, cut to ≤8 tools; if still <70%, hand-write one Custom curated tool (T2-style) and re-measure.

### R4. Build mode: choose hosted-Auto for graded demo + `--local` (Ollama, pinned model) as rehearsed fallback over local-only or hosted-only
- **Why:** Hosted gives real server IDs + npx runner judges expect; local gives zero-quota, zero-egress, offline resilience story ("works partitioned"). Hybrid is the recommended pattern in `08 §6` and the T3 narrative flip (resilience demo).
- **Tradeoffs:** Two code paths to maintain; local small models fail on strict schema. Pin ONE local model + ctx and never bump casually.
- **Next actions:** (1) Run Q1/Q9/Q12 matrix and log quota + files + model scores (`evidence/quota-local-matrix.md` + owner: infra). (2) Pin `Modelfile` + `ollama ps` screenshot in repo (owner: infra).
- **Drop condition:** If local success rate <60% on 20 tool-call trials OR `emit_tool_plan` failure appears ≥3× consecutively, switch local fallback to `cached-JSON mode` (no model) and stop debugging models.

### R5. Team: choose freeze at 3 (backend + infra/model + demo/judging-packet) over solo or 4+ — pending Q4 answer
- **Why:** T3 needs three parallel roles; 2 leaves no hot-spare for live demo; 4+ adds coordination tax in a short event. `10-track-choice.md §4` build order assumes 2–4 with defined roles.
- **Tradeoffs:** Recruiting cost vs coverage. If capped at 2 by rules, drop live-federation scope to single-laptop Docker (R6-P2) rather than cutting the safety-eval role.
- **Next actions:** (1) Confirm cap via Q4 (owner: lead, 24h). (2) Assign roles + hot-spare laptop owner in `team.md` (owner: lead).
- **Drop condition:** If team <2 confirmed by Wk1 end, abandon T3 → T2 solo-safe scope (1 tool + eval set).

### R6. Demo contract: choose write-back-with-approval-gate + audit record in ≤60s over chat-only or dashboard-only
- **Why:** `09-judge-fit.md` slop checklist: chat-only, booking-bot, RAG-PDF, symptom-checker all die without a governed state change. Winners end in an artifact (PO drafted, bed assigned, claim adjudicated, file advanced) behind Cite-Before-Act.
- **Tradeoffs:** Approval gate adds a click; gains safety-track points + differentiates from "thin wrapper around a single REST call" (GSA rubric).
- **Next actions:** (1) Script 3 dual-system questions + 1 live-update beat with timestamps (owner: demo). (2) Pre-record 60s video + bake canned JSON for all 3 (owner: demo) before venue.
- **Drop condition:** If end-to-end happy-path p95 latency >60s over 10 runs, cut scope (fewer fields, smaller seed data) until p95 ≤45s — never demo a spinner.

### R7. Quota discipline: choose ≤3 hosted servers + `--discover` reuse + `--local` for iteration overAd-hoc rebuilds
- **Why:** Free tier is 10 servers / 100k lines (Guide p.7); T3 needs headroom for the live moment. Rebuilding unchanged repos costs nothing — so iterate locally, spend hosted only on graded builds.
- **Tradeoffs:** Slight iteration friction vs quota-exhaustion disqualification risk.
- **Next actions:** (1) Log every hosted build in `quota-log.md` with `synapse info` before/after (owner: infra). (2) Set `ENDPOINT_BASE_URL` + `${ENV}` secrets hygiene check in CI (owner: infra).
- **Drop condition:** If remaining quota <40% before demo week with >2 hosted builds still planned, freeze hosted builds; all remaining iteration `--local` only; request second account/key as contingency.

---

## 3. Build order (first 7 days after P0 closed)

1. Day 1: Q1–Q4, Q8–Q9 evidence runs → `evidence/` folder (owner: infra + lead).
2. Day 2–3: Two FastAPI systems green at `/docs` + first hosted Auto + first `--local` file (owner: backend).
3. Day 4–5: Allowlist curation + `--smart-names` + Custom composite draft + approval gate (owner: backend + safety).
4. Day 6–7: Dual-system agent script + `--discover` live-update rehearsal ×5 + fallback video + quota log (owner: demo + infra).

*File path: `research/final/20-open-questions.md`*
