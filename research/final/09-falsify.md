# 09 — Devil's Advocate: Try to Kill Track 3 Onboarding Copilot

**Verdict: ATTEMPTED KILL FAILED — all 4 hypotheses SURVIVED (2 conditionally). Proceed with mitigations.**
**Date:** 2026-11-22 | **Method:** 20 targeted web queries (5 per claim) + local repo context (H1–H5, 15-endpoints, 17-effort-plan)

---

## H-K1: "Judges see onboarding as Track 2 cliché" — Falsification: MODERATE (survived by reframing)

**Kill theory:** HR/onboarding bots are so overdone judges mentally file it as Track 2 chatbot clone and stop scoring.

**Searched (5):**
1. `hackathon judges tired onboarding HR bots cliche`
2. `hackathon judge complaints HR chatbot onboarding overdone`
3. `devpost hackathon winning onboarding copilot track`
4. `hackathon judges what impresses Track 2 vs Track 3`
5. `AI onboarding assistant hackathon cliche judges feedback`

**Incriminating evidence (supports kill):**
- HR onboarding assistants ARE the canonical hackathon filler. IBM Watson Orchestrate agentic hackathon roundup lists "automated HR onboarding assistants" as a default submission cluster (kenhuangus substack). Lablab.ai hosts a literal "HR Chatbot for Personalized Onboarding" template. PagerDuty HackWeek + AIHR "15+ AI Hackathon Ideas for HR" both list onboarding-query automation as idea #1 — i.e., lowest-novelty.
- Cal Hacks 1st-place blog (Dylan Lu): "judged for a hackathon at ASU and almost every project was just a chatbot clone." Copycat = anti-impact under standard rubrics (Eventornado: "a copycat idea doesn't impress anyone"; Relativity: innovation + business value gates).
- Masai 2026 guide: judging ≈ 20% innovation / 25% technical implementation / 25% problem-solving impact. A pure Q&A bot scores ~0 on technical.

**Exonerating evidence (kills the kill):**
- No source found where judges say onboarding = auto-loss. Devpost judge interviews ("How to win a hackathon: Advice from 5 seasoned judges") reward *execution + story*, not topic bans. PagerDuty judges rewarded HR hacks that showed "realistic and valuable" GenAI leverage.
- Track distinction is the escape hatch: Track 3 is judged on *cross-system agency + discovery*, not persona. `05-track3-pairs.md` script shape (Q1 lookup join → Q2 exception/anti-join → live endpoint add → `--discover` → Q3 only answerable post-discover) is structurally NOT a Track 2 chatbot.
- 100+ hackathons retrospective (IG reel, corroborated by HackerEarth "judges form opinions in first 30s"): judges buy *demos with state*, not features. Onboarding with workflow state (approvals, IT provisioning) beats FAQ bot.

**Rating: MODERATE falsification pressure — SURVIVED CONDITIONALLY.**
**Condition:** Never pitch as "HR bot." Pitch as "two-system copilot that closes onboarding exceptions." Keep Q2 (mismatch / missing-record) in the first 45s so judges cannot misfile it.

---

## H-K2: "Two-system join is trivial (just email match)" — Falsification: WEAK (kill fails)

**Kill theory:** HR↔IT join on email is one `WHERE` clause; judges will call it trivial integration.

**Searched (5):**
1. `two system integration demo hackathon trivial email match join`
2. `hackathon multi API integration judging technical difficulty`
3. `HR onboarding identity resolution email match problem fuzzy`
4. `hackathon two API integration winning project judges impressed`
5. `entity resolution record linkage trivial vs hard data integration`

**Incriminating evidence:**
- If seeded data is clean (identical `email` in both APIs), the kill is CORRECT — it is a 3-line join. Nothing found contradicts that narrow case. Hackathon tips (Postman, HackerEarth) warn judges discount demos with "no real integration work."
- No source says "two APIs = impressive" by count alone. Rise.in track-design guide: judges verify *minimum integration depth*, not API count.

**Exonerating evidence (strong — kills the kill):**
- Identity resolution is a recognized hard problem, not a string compare: Salesforce Data 360 match rules (fuzzy name + normalized email/phone cascades), Amperity (match quality measurement; "a successful destination match doesn't prove the complete profile was assembled correctly"), CDP Institute ("identity resolution trap" — probabilistic vs deterministic), Zingg/Torch.ai (schema mismatch, dedup chaining — "a single bad link chains hundreds of records"), Dataiku self-serve ER pipeline (arXiv 2607.26298 lesson: chaining errors).
- Winning pattern per Square+Google, LlamaIndex RAG-a-thon, Anthropic hackathon postmortems: judges rewarded *exception handling + multi-step execution*, not join syntax.
- Our design already exploits this: `19-H1-onboarding-blockers.md` + `15-endpoints.md` imply mismatch cases (name variants, missing IT record, duplicate emails). Q2 anti-join ("who is in HR but has no laptop ticket?") cannot be answered by naive email equality.

**Rating: WEAK — kill FAILS against a properly seeded demo, SUCCEEDS against clean data.**
**Condition:** Seed at least one fuzzy mismatch (e.g., `Jon vs Jonathan`, hyphenated surname, contractor without HR email) + one orphan record. Show confidence/threshold + audit trail. Add H4 `operation_id` lint so tools don't silently drop (build-breaker already flagged).

---

## H-K3: "Live --discover adds no value" — Falsification: FAILED (survived with backup)

**Kill theory:** Judges don't care whether tools were discovered live vs hardcoded; live only adds failure risk. Synapse Auto missing routes proves it.

**Searched (5):**
1. `hackathon live demo API discovery impresses judges vs canned demo`
2. `hackathon live demo fails risk backup video judges`
3. `agentic AI discover APIs dynamically demo value MCP`
4. `hackathon judges prefer live demo vs prerecorded video`
5. `Synapse Auto missing routes API discovery demo` (+ `Synapse vulnerability SynLapse` noise — no product-route evidence found)

**Incriminating evidence (risk is real):**
- Masai 2026 demo-failure table: "Live API call with no fallback — one rate-limit and your demo dies mid-pitch. Cache a real response, use it as backup."
- Rise.in Demo Day guide + CompeteRadar + Reskilll 2026: every live demo needs a backup video; live demos fail on Wi-Fi, auth, quota, testnet.
- No direct evidence found for "Synapse Auto missing routes" as a product failure — closest hits are FastAPI-MCP adoption notes (`03-synapse-technical.md`: `fastapi_mcp` 12k stars, zero-config mount) and our own H4 (auto-generated IDs mangle names like `read_item_items__item_id__get`). So the *mechanism* for a silent miss is confirmed even if the brand-specific complaint is not.

**Exonerating evidence (strong — live discovery is currently the wow moment):**
- 2026 is the year of MCP discovery: Atlan "MCP vs API" (deterministic calls vs dynamic runtime discovery), New Stack "Agentic AI reshaping API self-discovery," Workato connector guide, Octopus MCP multi-server agent. Solo.io **2026 Hackathon for MCP & AI Agents** winners: federated multiple MCP servers into one endpoint with service discovery (Building Cool Agents track). Dynamic discovery is prize-grade, not gimmick.
- HN `pre-record your demos` thread (Oct 2025, ~20 veteran voices): consensus live 10/10 vs recorded 9/10 ceiling; "live says this is real and it works" (oftenwrong), "builds trust" (infiniteregrets), "pre-recorded makes me wonder how many takes" (wanderingstan). Jadbox synthesis: **do it live with one-push fallback to recording** — exactly H3's design ("open with live discover, keep pre-canned fallback on hotkey").
- Our H3 (`19-H3-discover-moment.md`) already predicts +1.5–2.5 wow pts for live discover with ≥5/6 pairwise wins — consistent with external consensus.

**Rating: FAILED TO FALSIFY — SURVIVED.**
**Conditions (non-negotiable):** (1) cached `--discover` output on hotkey, (2) backup video ≤90s, (3) H4 explicit-`operation_id` lint before stage (auto-IDs are the missing-routes mechanism), (4) fail-first beat per `06-track3-demo.md` (show tool-not-found BEFORE fix so fallback is narratively covered).

---

## H-K4: "Solo can't run 2 APIs + agent reliably" — Falsification: WEAK-MODERATE (survived with discipline)

**Kill theory:** One person cannot keep HR API + IT API + agent + discovery alive on stage; failure surface 3×s, no teammate to reboot.

**Searched (5):**
1. `solo hackathon winner single person team tips`
2. `hackathon demo two APIs integration failure rate reliability`
3. `solo developer run multiple APIs AI agent reliability hackathon`
4. `hackathon API outage fallback strategy multi API demo`
5. `single person hackathon win AI agent 2025 2026`

**Incriminating evidence:**
- Reliability engineering sources agree multi-API multiplies risk: HackerEarth ("demo on localhost with flaky API call will fail; conference Wi-Fi will drop"), Thita 24–48h strategy guide, Codiastic 7-failure-cases (retries, ordering, webhooks), NeuralTrust ("agent wired to one AI API goes down the moment that API does").
- Standard solo advice is to *shrink* scope: Reddit r/hackathon winners ("hardcode data, run locally, tunnel via ngrok, focus on front end"), Gary-Yau Chan 8-step guide (role specialization implies team advantage).

**Exonerating evidence (solo + multi-API + agent wins exist in 2026):**
- Solo.io 2026 MCP hackathon: **solo winner Huzefa Hamdard** (India) — Kubernetes-native governance for MCP. Solo-built multi-server agent federation beat teams.
- r/hackathon solohacker thread (Bill Zhang): "going solo can actually help you win 30+ hackathons" (no coordination overhead, full arc control). IndieHackers 2026: solo-built 12-agent system shipped in 2 months. Atomic Object: AI-orchestrated solo builders now run parallel agents.
- AI leverage compresses ops: Builder.aws VibeJudge report (60–70% build 10× faster with AI assistants, "production-grade architectures in 48hrs").
- Known mitigations are cheap and solo-executable: ngrok tunnel, hardcoded seed + cached agent trace, single `docker compose up` for both APIs, one-file `demo.sh`, pre-warmed model + offline fallback answers.

**Rating: WEAK-MODERATE — SURVIVED CONDITIONALLY.**
**Conditions:** (1) both APIs in one compose file, seeded deterministically (`14-seed-data.md`); (2) rehearse triple-failure drill (kill HR, kill IT, kill network — each must degrade to cached answer, never blank); (3) 2-min setup budget; backup track per `17-effort-plan.md` (Track 2 Python Custom safety tool, <1wk pivot) stays warm; (4) keep agent loop to ≤3 tool calls in the golden path (Q1→Q2→Q3) so one retry fits in demo clock.

---

## Cross-cutting: what would actually kill Track 3 (watchlist)

1. **Clean-data demo** → K2 succeeds. Fix: fuzzy + orphan seeds mandatory.
2. **Chatbot framing in first 30s** → K1 succeeds. Fix: open on exception queue, not chat box.
3. **Live discover with no cache** → K3 risk realizes. Fix: hotkey fallback + video.
4. **Three-terminal startup on stage** → K4 realizes. Fix: one-command compose + ngrok.
5. **Missing `operation_id`** → silent tool drop (H4). Fix: lint gate in CI before any rehearsal.

## Queries-run log (20 total, diligence threshold met)

K1 (5) §H-K1 | K2 (5) §H-K2 | K3 (5) §H-K3 | K4 (5) §H-K4. No claim has <5 queries. No additional queries needed to declare survival — but H4 scanner probe (local, 3 FastAPI variants) and H3 A/B dry-run (n≥6) remain open build validations, not research gaps.

## Bottom line

| Hypothesis | Falsification strength | Outcome |
|---|---|---|
| K1 onboarding = cliché | MODERATE | Survived — reframe as exception-closing copilot |
| K2 join = trivial | WEAK | Survived — fuzzy/orphan seeds make it non-trivial |
| K3 live discover = no value | FAILED | Survived — discovery is the 2026 wow moment; ship with fallback |
| K4 solo can't run it | WEAK-MODERATE | Survived — solo wins exist; one-command ops + failure drills required |

**Recommendation: PROCEED with Track 3 primary, Track 2 pivot warm. All four kill attempts survived; three require the mitigations above, none requires abandoning the track.**
