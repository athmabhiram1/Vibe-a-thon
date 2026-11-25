# 44 — Fast Quota: Stay Under 10 Servers / 100k Lines (Quota-Proof Build)

> Goal: finish HR+IT copilot (Track 3 = 2 servers) using ≤3 hosted builds total, ≤10 tools exposed, zero quota surprises. Free tier = **10 MCP servers + 100,000 indexed lines/account** — rebuild of unchanged repo costs nothing, `--local` never counts (guide p.7).

## 1. Quota budget (plan it once, log it always)

| Budget item | Limit (free tier) | Our plan | Headroom |
|---|---|---|---|
| Hosted MCP servers | 10 / account | **2** (hr + it) + 1 spare for live-update demo = **≤3** | 7 spare |
| Indexed lines | 100k / account | HR (~2k) + IT (~2k) + rescan deltas only = **<10k** | ~90k spare |
| Exposed tools | judge rule: fewer = better | **≤10** allowlisted (5 HR + 5 IT, + 2 health = 12 max → trim to 10, see §2) | reliable agent |
| `--local` iterations | unlimited, uncounted | **all** prompt-tuning / naming experiments here | ∞ |

> Rule: **hosted = demo only, local = iteration.** Every `synapse build` without `--local` must be a logged, deliberate event (§4).

## 2. Expose only what the agent needs (≤10 tools via allowlist)

Don't use `--all-endpoints` on a big app — it burns tools and confuses the agent. Allowlist explicitly:

```bash
# HR server — 5 tools max (adjust to your 11-endpoint contract in 43-fast-ci)
synapse build --auto --endpoints "GET /candidates,GET /candidates/{id},POST /employees,GET /shifts/calendar,GET /oncall" --server-name hr-prod

# IT server — 5 tools max
synapse build --auto --endpoints "GET /equipment,POST /equipment/assign,POST /tickets,GET /tickets/breaches,POST /tickets/{id}/reroute" --server-name it-prod
```

If your CLI version supports operation-ID filtering instead of `METHOD /path`, use it (same idea, ≤10 IDs):

```bash
# alternative spelling on newer CLIs — pick whichever flag your --help shows
synapse build --auto --include-operations "hr_list_candidates,hr_get_candidate,hr_create_employee,hr_shift_calendar,hr_get_oncall" --server-name hr-prod
synapse build --auto --include-operations "it_list_equipment,it_assign_laptop,it_create_ticket,it_sla_breach_list,it_reroute_ticket" --server-name it-prod
```

> Keep `hr_health_check` / `it_health_check` out of the agent surface if you need to hit exactly 10 — health is for `curl`, not the LLM.

## 3. One `--smart-names` pass only (Auto only, costs one build)

`--smart-names` reads each handler + README to give clearer tool names/descriptions (guide p.4). Agents pick the right tool more often — but it sends function details to Synapse, so do it **once, at the end**:

```bash
# 1. build plain hosted servers first (2 builds)
synapse build --auto --endpoints "GET /candidates,GET /candidates/{id},POST /employees,GET /shifts/calendar,GET /oncall" --server-name hr-prod
synapse build --auto --endpoints "GET /equipment,POST /equipment/assign,POST /tickets,GET /tickets/breaches,POST /tickets/{id}/reroute" --server-name it-prod

# 2. single smart-names polish pass (reuses same server IDs — no new servers)
synapse build --smart-names --server-name hr-prod
synapse build --smart-names --server-name it-prod
# If --smart-names forces a rebuild counter, skip the plain builds and go straight to smart-names (2 builds total).
```

> Never iterate on names with hosted builds. Tune wording in `--local` first (§5), then apply once.

## 4. `synapse info` before/after log (mandatory pair)

Run `synapse info` before **and** after every hosted build — it shows project state + remaining quota (guide p.3, p.7). Append both to `quota-log.md`:

```bash
# before (log it)
synapse info | tee -a quota-log.md
# build (log the exact command too)
echo '### $(date -u +%FT%TZ) — synapse build --auto ... --server-name hr-prod' >> quota-log.md
synapse build --auto --endpoints "GET /candidates,..." --server-name hr-prod
# after (log it)
synapse info | tee -a quota-log.md
```

Copy-paste `quota-log.md` starter:

```markdown
# quota-log.md — append-only, commit every hosted build

## 2026-11-22T10:00Z — BEFORE hr-prod #1
```
$ synapse info
# paste full output here (servers used, lines indexed, server IDs)
```

## 2026-11-22T10:02Z — BUILD hr-prod #1
cmd: synapse build --auto --endpoints "GET /candidates,GET /candidates/{id},POST /employees,GET /shifts/calendar,GET /oncall" --server-name hr-prod
result: OK, server ID syn_xxx (paste Session: id on failure)

## 2026-11-22T10:03Z — AFTER hr-prod #1
```
$ synapse info
# paste full output here — delta should be +1 server, +~2k lines
```
```

> Demo tip: `cat quota-log.md` on screen during judging = proof you stayed quota-proof. Rebuilds of unchanged repos cost nothing — if `info` delta is 0 lines, say so out loud.

## 5. `--local` for iteration (zero quota, zero risk)

```bash
# no `synapse init` needed for local; needs own model key, code never leaves machine
export ANTHROPIC_API_KEY=sk-ant-...   # or GROQ_API_KEY + `synapse model set groq`
synapse model                          # check provider + key source before building
synapse build --local                  # Python projects → synapse_auto_server.py (real file)

# iterate freely: rename handlers, rewrite docstrings, re-run until tool names look right
# then promote the winners to ONE hosted build per server
```

Limits (guide p.5): local writes a file **only for Python** — on TS/Java/C#/Go/Rust it names tools but writes nothing (use hosted). Small local models fail with `returned no emit_tool_plan call` → switch to stronger model (Anthropic default, Groq/OpenAI/Grok/OpenRouter, or Ollama/Bedrock/Vertex per `synapse model set`).

```bash
export GROQ_API_KEY=gsk_...
synapse model set groq
synapse build --local
```

## 6. `quota-proof.md` template (submit with repo)

Save as `quota-proof.md` in repo root — judges + teammates read this in 60s:

```markdown
# Quota Proof (Synapse free tier: 10 servers, 100k lines)

- Account servers used: 2/10 (hr-prod syn_xxx, it-prod syn_yyy) + 0 spare used
- Indexed lines: ~4.2k/100k (HR 2.1k + IT 2.1k, from `synapse info` AFTER logs)
- Hosted builds total: 2 (1 per server, both with --smart-names in one pass)
- Local builds: ~15 (all naming/docstring iteration, uncounted)
- Tools exposed: 10 (5 HR + 5 IT, allowlisted — no --all-endpoints)
- Rebuild policy: `--discover` only after router changes; unchanged rebuilds cost 0
- Log: see quota-log.md (info BEFORE/AFTER every hosted build)
- Contingency: second-account procedure tested, not used (see §7)
```

## 7. Second-account contingency (break glass, don't plan on it)

Trigger: `synapse info` shows `Quota Exceeded` or `AUTH_INVALID` mid-hackathon.

```bash
# 1. confirm it's really quota (not auth)
synapse info
synapse config            # shows which API key is in use and where it came from
# Quota Exceeded → quota. AUTH_INVALID → `synapse config set-key` with a valid key.

# 2. fall back to local immediately (demo continues, zero downtime)
synapse build --local     # keep hacking; Custom/--local writes <tool>_server.py locally

# 3. only if a hosted server is mandatory for the demo: second account
# a. create 2nd key in Synapse console (teammate's account, new email)
# b. in a CLEAN checkout (never mix keys in one dir):
synapse config set-key     # paste 2nd-account key when asked
synapse init               # re-init under 2nd account
synapse build --auto --endpoints "..." --server-name hr-prod-bak  # minimal allowlist only
synapse info | tee -a quota-log.md   # log it as ACCOUNT-2
```

> Rules: one key per checkout (don't overwrite main repo's key), minimal allowlist on account-2, note `ACCOUNT-2` in both `quota-log.md` and `quota-proof.md`. Never commit API keys — headers use `${ENV}` placeholders (guide p.7).

## 8. Commands cheat-card (tape to monitor)

```bash
synapse info                                                     # quota BEFORE + AFTER every hosted build
synapse config                                                   # which key is active
synapse build --auto --endpoints "GET /a,POST /b" --server-name X # allowlisted hosted build (counts)
synapse build --smart-names --server-name X                      # one polish pass (counts — do once)
synapse build --discover --auto --endpoints "..." --server-name X # rescan after router change (counts delta only)
synapse build --local                                            # free iteration (never counts, no init needed)
synapse model / synapse model set groq                           # local provider check/switch
SYNAPSE_TELEMETRY=0 synapse build --local                        # opt out of telemetry (never includes code/prompts)
```

## 9. Sources

- Participant guide pp.3–7: install → `init` → `build` → `info`; `--smart-names` (Auto only); `--local` + `synapse model set` provider table; free tier 10 servers/100k lines, unchanged rebuilds free, `--local` uncounted; `config`/`set-key`; `AUTH_INVALID`/`Quota Exceeded` fixes; `${ENV}` secret rule; telemetry opt-out.
- `research/build/43-fast-ci.md` §2 `discover-reminder` job (never auto-`--discover` in CI) + 11-endpoint contract used for allowlists above.
- `research/build/25-step-discover.md` (when `--discover` vs `--new` vs `--server-name`).
