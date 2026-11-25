# Track-Choice Decision Matrix — Win, Not Participation

**Context:** LOTS of time available. Team 2–4 likely. Python OK. Goal = WIN.
**Tracks:**
- **T1:** 1 system, 3 tasks — easiest, most crowded
- **T2:** Python Custom, 1 tool — safety judging
- **T3:** 2 systems + live `--discover` — highest wow + highest setup
- **T4:** Open — highest ceiling + must prove Synapse centrality

## 1. Effort Signals (web research)

**FastAPI scaffold time: 10 min → 1 hr → weekend**
- 10-min production-ready CRUD scaffold (`fastapi + uvicorn`, auto Swagger at `/docs`) — multiple 2025/2026 guides agree.
- <60 min: 4-endpoint book/notes API with validation, status codes, testable (pythonskillset, techpresentations.org).
- Weekend: full CRUD + SQLite + routers + tests + JWT/auth + Docker (themissingmanual.dev, howlongfor.com: senior Python 2–3 days to basics, 1 wk to prod; intermediate 1–2 wks).
- **Implication:** Python/FastAPI is NOT the bottleneck. T2 custom-tool cost is ~1–2 days for strong Python team. Budget remaining time for polish/demo/safety evals.

**Synapse quota / infra: 10 servers / 100k lines (assumed constraint)**
- Official Synapse docs found no "10 servers/100k lines" hard quota — configurable MAU blocking (`limit_usage_by_mau`, `max_mau_value`), room-complexity limits, worker scaling via Redis + replication listeners instead.
- **Implication:** Treat "quota" as competition-rule constraint, not Synapse default. Design to stay well under: 2–3 homeservers max for T3, minimal federation traffic, small rooms, disable presence if needed. Document quota-compliance in README/judging packet — judges love constraint-awareness.

**`--local` Ollama model strength needs**
- Proven pattern: `gemma3:4b` = laptop default (capable + runs on modest HW); `llama3.2:3b` (~2GB) = safest first pull, CPU-usable; 7–8B needs ~16GB RAM / ~8GB VRAM; 27B+ needs 32–64GB RAM / 24GB+ VRAM.
- Verified hack pattern (Hack-Day-Starter, 2026): Gemma 4 12B did full local tool-calling loop via Ollama (`model → tool → exec → result → response`).
- Arm guide: start `gemma3:4b`, only upscale to 27B on DGX/high-mem; larger = stronger reasoning but slower + memory-hungry.
- **Implication for T3 `--discover`:** pre-pull TWO models (primary 4B + fallback 1B/3B), pin exact Ollama tags in Verified Registry, test 10–20 real prompts, set conservative context, `ollama ps` to confirm GPU vs CPU-split. Never bump context "just because." Record benchmark: correctness, fields-present, TTFT, total time, memory.

**Prior winner patterns: consumer wins overall, infra gets honorable**
- Hack Synapse 2026 (MITS-DU, 901 builders/325 teams): overall winner = applied consumer outcome (Agrivaidya agri-robotics), judged on problem relevance + usable product + communication, not raw infra depth.
- ASI/ETHGlobal NYC track: grand prizes to composed agentic UX; pure infra (Uniswap/CCTP portfolio infra, ad-subsidy protocol, credit layer) → honorable / track-second.
- GKE Hackathon (4,773 participants): grand prize to elevated end-user app; ADK/MCP/A2A plumbing → honorable mentions.
- CreatorCon 2026: overall = Hack4Good consumer app (Free Food 4 You); prescriptive multi-module infra category produced finalists, not overall.
- **Implication:** Judges award overall to visceral consumer demo; deep infra wins *track* or *honorable* unless framed as consumer magic. T3/T4 must lead with user story, hide infra as superpower.

## 2. Decision Matrix (1–5, 5 = best except Effort/Risk where 5 = highest)

| Criterion | T1: 1 system / 3 tasks | T2: Python Custom / 1 tool | T3: 2 systems + live --discover | T4: Open / prove centrality |
|---|---|---|---|---|
| **Win-probability (overall)** | 2 — easiest = most crowded; tie-breaks kill you | 3 — fewer entrants, but safety judging is subjective | **5 — live discovery = unforgettable; wins overall when it works** | 4 — highest ceiling, but must argue centrality |
| **Win-probability (track prize)** | 3 — high variance lottery | 4 — Python OK + lots of time = strong fit | 4 — if demo lands, sweeps track | 3 — depends on judge belief |
| **Effort (5=most)** | 1 — days | 2 — 1 wk (FastAPI 1–2d + safety evals + polish) | 5 — 2–3 wks (2 systems, federation, Ollama matrix, network hardening) | 4 — open scope creep; +proof burden |
| **Risk (5=most)** | 2 — low tech risk, high crowding risk | 2 — low; safety rubric is main risk | 5 — live net, federation, model VRAM, `--discover` flake | 3 — narrative risk, tech-controllable |
| **Differentiation** | 1 — everyone does same 3 tasks | 3 — custom tool can stand out if novel | 5 — nobody else dares live 2-system discover | 5 — wide-open blue ocean |
| **Synapse-showcase** | 2 — minimal (1 system = commodity) | 3 — good if tool is Synapse-native (moderation, bridge, audit) | 5 — Synapse *is* the demo (federation + discovery) | 2–5 — variable; must manufacture centrality |
| **Team 2–4 fit** | 5 — even solo can finish | 5 — perfect split: 1 API + 1 safety/eval + 1 demo/video | 3 — needs roles: sysadmin/federation + model/local + frontend/demo + fallback ops | 4 — flexible roles |
| **Time-leverage (lots of time)** | 1 — wasted; extra time doesn't separate | 3 — extra time → evals + hardening help | 5 — extra time is the moat; crowded teams can't replicate | 5 — extra time enables ceiling |

**Weighted take (Win-first weighting: win% ×3, differentiation ×2, showcase ×2, minus effort+risk):**
T3 (28) > T4 (24) > T2 (22) > T1 (12). T1 is participation trap.

## 3. Track-by-track Verdict

**T1 — Avoid as primary.** Easiest brief + most entries = judged on pixel-polish and luck. Lots of time gives zero ROI. Only pick if team collapses to 1 person or <48h remains.

**T2 — Safest winning bet.** One Python tool + FastAPI scaffold (hours) leaves 80% of time for what actually wins safety track: threat model, red-team eval set (30–50 cases), false-positive/UX story, benchmarks vs baseline. Risk: judging subjectivity; mitigate with quantified safety scorecard + live abuse-demo.

**T3 — Highest EV for overall win.** 2 systems + live `--discover` is the only "arena moment" judges remember. High setup is *feature* with lots of time + 2–4 people. Risk is live failure — must engineer fallback (below).

**T4 — Highest ceiling, hardest story.** Pick only if you have a genuinely novel Synapse-central thesis (e.g., Synapse as agent-memory / trust fabric / offline-first coordination). Otherwise judges ask "why Synapse?" and you lose to T3's live proof.

## 4. Final Recommendation

**PRIMARY: Track 3 (2 systems + live `--discover`)**
Why: team fits the "win not participate" brief — Python OK removes T2 edge, lots of time neutralizes T3's setup tax, crowded T1 avoided, and consumer-win bias is satisfied by making discovery *feel* like consumer magic (not infra). Pre-build quota-compliance + Ollama registry + rehearsed discovery moment = overall-winner shape.

Winning T3 concept shape: *"Type a name → live federated discovery across 2 Synapse homeservers → local-model-verified result in <10s"* with human-readable story (find people/rooms/agents, safety badge from local model, offline-capable).

**BACKUP: Track 2 (Python Custom safety tool)**
Why: lowest risk, fastest to MVP, reuses T3 work (local model eval harness + FastAPI + Synapse client become the safety tool). If T3 infra blocks (no federation network, quota cut, hardware without VRAM), pivot in <1 week.

**DO NOT:** T1 unless emergency. T4 only if T3 discovery idea upgrades into platform thesis — then enter T4 *with T3 demo inside it* (dual-enter if rules allow, else stay T3).

## 5. Fallback Plan — If `--discover` Fails Live

**Principle: never let judges see a spinner. Every live call has a cached/local counterpart.**

1. **P0 — Pre-record + pre-cache:** Full-screen 60s video of successful `--discover` (timestamped, both servers visible). Plus canned JSON responses for 3 scripted queries baked into demo.
2. **P1 — Mode switch:** `--discover --mode=local|cached|live` flag. Rehearse sentence: *"Live federation is flaky on venue Wi-Fi — switching to local replica, same code path."* Judges reward composure.
3. **P2 — Local-only stack:** Both "systems" as Docker Synapse containers on one laptop + pre-pulled `gemma3:4b` (fallback `llama3.2:3b`); `ollama ps` screenshot ready; `localhost:11434` health check on boot.
4. **P3 — Venue hardening:** phone hotspot + venue Wi-Fi + offline; federation via Tailscale/static IPs; `serve_server_wellknown` preconfigured; MAU/complexity limits raised; second laptop as hot spare with cloned images.
5. **P4 — Narrative flip:** if live fails, frame as *resilience demo*: "This is why local-first + Synapse matters — discovery still works partitioned." Turn failure into thesis.
6. **Rehearsal checklist:** 10 dry runs, kill-network drill,incompatible-model drill, quota-exceeded drill, 3 scripted Q&A answers on centrality/privacy/safety.

**Build order (lots of time, team 2–4):** Wk1: FastAPI + 2-server Docker + Ollama registry → Wk2: `--discover` live path + T2 safety-tool branch → Wk3: fallback modes + video + judging packet (quota proof, benchmarks, consumer story).

---
*Sources: FastAPI scaffold guides (dev.to, pythonskillset, themissingmanual.dev, howlongfor.com); Synapse sample config / MAU / workers docs (matrix-org.github.io); Ollama sizing (ollama.com, Arm Learning Paths, itechguides 2026, swarmz.net, Hack-Day-Starter 2026); winner patterns (HackIndia Hack Synapse 2026, ASI ETHGlobal NYC, GKE Hackathon, CreatorCon 2026).*
