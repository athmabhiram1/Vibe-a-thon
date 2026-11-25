# 39 — Verify Fallback: Kill-Network, Quota-Exceeded, Wrong-Model Drills

**Sources:** `research/final/12-demo-risk.md` (P0–P4 ladder, Drill A/B, cue card) · `research/build/05-deploy.md` (§5 hotspot/network-death, §6 verify matrix) · `research/final/17-effort-plan.md` (§6–§7 drills, freeze D12) · `research/build/10-lib-models.md` (qwen2.5-coder:7b primary, gemma3:4b fallback, num_ctx 8192) · `research/final/20-open-questions.md` Q12 (`no emit_tool_plan` floor).
**Goal:** prove every fallback works *before* stage. Two clean runs per drill = demo-ready.
**Rule:** never debug silently on stage >20s. Announce the level — Golden → Live → Local → Protocol → Lesson — don't apologize.

## 0. Pre-reqs (do once, night before)

```bash
# models pre-pulled + pinned
ollama pull qwen2.5-coder:7b && ollama pull gemma3:4b
ollama create demo-qwen-8k -f Modelfile.local-qwen
ollama ps  # must show CONTEXT 8192, 100% GPU
curl -s 127.0.0.1:11434/api/ps | jq .  # context_length == 8192

# local stack + golden video + canned JSON on disk
docker compose up --build -d
curl -s localhost:8000/health  # {"status":"ok",...} <2s
ls -lh demo/golden.mp4 demo/canned/{oncall.json,breach_list.json,reroute_result.json}
npx @modelcontextprotocol/inspector --cli ./server --method tools/list --format json | head -c 500

# .env.demo flip contract
# APP_MODE=local  MODEL_URL=http://127.0.0.1:11434/v1  MODEL_NAME=demo-qwen-8k
# SYNAPSSE_TELEMETRY=0 for offline claim
```

> `Modelfile.local-qwen`: `FROM qwen2.5:7b-instruct` + `PARAMETER num_ctx 8192` + `PARAMETER temperature 0.2` + `PARAMETER num_predict 2048`. OpenAI `/v1/chat/completions` has no `num_ctx` field — Modelfile-baked value is the only pin for `/v1` clients (12 §3.2).

## 1. Drill K — Kill-network (airplane mode → local)

**Simulates:** venue Wi-Fi death, captive-portal DNS fail, Render/Railway cold-start loop, 5xx.

### Steps (roles: Presenter + Killer)

| T+ | Killer does | Presenter does + says |
|---|---|---|
| 0s | Airplane mode ON (or `sudo iptables -A OUTPUT -d <api-host> -j DROP`), kill hotspot | Keep talking. Start timer on screen: `time ( ... )` |
| 5s | Confirm `curl $API/health` times out | Say: **"Venue Wi-Fi is doing venue things — flipping to the local build, same tools, no cloud."** |
| 10s | — | `APP_MODE=local mycli --local --model demo-qwen-8k` (or `docker compose up -d` if down) |
| 20s | — | `ollama ps` on projector (prove CONTEXT 8192) + `curl -s localhost:8000/health` |
| 30s | — | Inspector CLI, no browser net needed for stdio: `npx @modelcontextprotocol/inspector --cli ./server --method tools/call --tool-name hr_get_oncall --tool-arg team=support-night --format json \| jq .result` |
| 60s | — | **Local claimed.** Continue Q3 chain on local: `it_sla_breach_list → hr_get_oncall → it_reroute_ticket` |
| +5min | Restore net (`iptables -D ...` / airplane OFF), re-warm `for i in 1 2 3; do curl -s -w "[%{http_code} %{time_total}s]\n" $API/health; sleep 5; done` | Log cold-start seconds |

Canned fallback if local also slow: play `demo/golden.mp4` *while* local boots — audience sees motion during the gap (05 §4.5). Never a spinner.

### Pass criteria (ALL must hold)

- [ ] Airplane → `APP_MODE=local` announced in **<60s** (timer visible in rehearsal video).
- [ ] Local **tool result on screen in <90s** from cut (Inspector JSON or `curl` + `jq .result`).
- [ ] `ollama ps` shows CONTEXT **8192**, PROCESSOR 100% GPU — no silent-truncation fallback.
- [ ] No secrets on projector (Bearer token from keychain, never slides).
- [ ] `localhost:8000/health` 200 warm <2s; cold-boot seconds logged.

### Fail → fix

| Fail | Fix |
|---|---|
| Local takes >90s | Pre-pull image + model night before; `docker compose pull`; keep `ollama serve` running, don't cold-start on stage |
| `ollama ps` shows 4096 / CPU | `OLLAMA_NUM_PARALLEL=1 OLLAMA_CONTEXT_LENGTH=8192 ollama serve`; recreate `demo-qwen-8k` from Modelfile; close Chrome/Docker tabs |
| Ports blocked (11434/8000/6274) | Confirm firewall exception in rehearsal; carry `curl` equivalents (05 §5.3); hotspot SSID/pass in clipboard |
| Model "forgets" system prompt | That's truncation, not reasoning — ctx too small. Pin 8192, reduce `num_predict`, shorten retrieved chunk |

## 2. Drill Q — Quota-exceeded (429 → Inspector proof + narrative flip)

**Simulates:** Synapse `429 / RESOURCE_EXHAUSTED`, >10 servers, >100k indexed lines, truncated `tools/list`, empty `structuredContent`. Treat as **expected branch**, not exception (12 §2).

### Steps

```bash
# 1. Inject fault (pick ONE):
# a) temporarily set allowlist to 3 tools, call 4th -> 429
# b) revoke API key / set MAX_LINES=100
# c) point at staging server with quota exhausted
synapse info  # screenshot: servers/lines vs 10 / 100k cap -> quota-proof/

# 2. Reach P3 in <60s: prove SERVER is fine, QUOTA is the limiter
npx @modelcontextprotocol/inspector --cli ./server --method tools/list --format json | jq '{version: .serverInfo.version, tools: [.tools[].name]}'
# allowed tool -> success
npx @modelcontextprotocol/inspector --cli ./server --method tools/call --tool-name it_sla_breach_list --format json | jq .result
# blocked tool -> clean isError, no key leak, no stack trace on projector
npx @modelcontextprotocol/inspector --cli ./server --method tools/call --tool-name hr_get_oncall --tool-arg team=support-night --format json | jq '{isError, content}'

# 3. Narrative flip to P4 (say verbatim):
# "With 10 servers we'd page. With 3 we finish the story — same join, smaller surface."
# then: --only allowlist rebuild OR --local switch (no quota):
synapse build --local --server-name hr-api  # quota-free path
```

Inspector web alternative (projector-friendly): Protocol tab `tools/list` → `tools/call` valid → invalid; Network tab to show the raw 429. `curl` equivalent:

```bash
curl -s $API/mcp -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '{tools: [.result.tools[].name], error}'
```

### Pass criteria (ALL must hold)

- [ ] P3 reached in **<60s**: `tools/list` visible + 1 success JSON (`jq .result`) + 1 blocked call showing user-readable `isError:true` (no stack trace, no key leak).
- [ ] Screenshot saved: `synapse info` (quota numbers) + Inspector 429 frame → `assets/quota-proof/`.
- [ ] Narrative flip delivered: budget story (§2 surface-reduction: `--only` / allowlist / `readOnlyHint` + paginated `limit/offset`).
- [ ] `surface_cache` invalidated: `serverInfo.version` bump visible; `tools/list` matches deployed schema (catches stale-cache misdiagnosis as quota).
- [ ] Recovery path shown: allowlist rebuild **or** `--local` (quota-free) with tool result.

### Fail → fix

| Fail | Fix |
|---|---|
| Raw traceback / key on screen | Wrap calls with `jq '{isError, content}'`; token from keychain; rehearse the invalid call once |
| Audience reads it as "broken" | Lead with "expected branch": show `synapse info` quota frame FIRST, then Inspector proof |
| `tools/list` truncated silently | Budget check: `tools/list` token estimate <4k; disable unused servers (`--only`), pre-index summaries not raw lines (12 §2) |
| Confused with stale surface_cache | Bump `APP_VERSION`/`serverInfo.version` per deploy; run `tools/list` live at demo start as ground truth |

## 3. Drill W — Wrong-model (weak/small model → no tool calls)

**Simulates:** wrong Ollama tag loaded (`llama3.2:3b` / `tinyllama` instead of `demo-qwen-8k`), `num_ctx` truncation, OpenAI-compat client ignoring ctx, `returned no emit_tool_plan call` (Guide p.8, Q12).

### Steps

```bash
# 1. Inject: load the WRONG model on purpose
ollama run llama3.2:3b "Call hr_get_oncall for team support-night"
# observe: hallucinated args, missing tool call, or `no emit_tool_plan`

# 2. Diagnose on screen (<30s):
ollama ps  # MODEL column shows wrong tag and/or CONTEXT != 8192
curl -s 127.0.0.1:11434/api/ps | jq '.models[] | {name, context_length}'

# 3. Recover (<60s):
ollama create demo-qwen-8k -f Modelfile.local-qwen
OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 ollama serve &
mycli --local --model demo-qwen-8k
# re-prove: one tool call via Inspector --cli, then drop BELOW the model:
npx @modelcontextprotocol/inspector --cli ./server --method tools/list --format json | jq '.tools[].name'
# say: "Let's drop below the model and prove the server is correct." (P3)

# 4. If still failing -> P0 golden + canned JSON, narrate tool args over video
cat demo/canned/oncall.json | jq .
```

Primary/fallback registry (10-lib-models): default `qwen2.5-coder:7b` (balanced tool use) → low-VRAM `gemma3:4b` → avoid `llama3.2:3b` for tool loops. `qwen3-coder:30b` only on 24 GB+ GPUs. Never bump ctx "just because" — 8192 pinned per demo.

### Pass criteria (ALL must hold)

- [ ] Wrong tag diagnosed on screen in **<30s** via `ollama ps` (MODEL + CONTEXT columns).
- [ ] Correct model reloaded + **tool result in <90s**; or P0 video + canned JSON playing with narration (no dead air).
- [ ] P3 protocol proof shown at least once: `tools/list` → `tools/call` valid → invalid (decouples "model wrong" from "server wrong").
- [ ] No `qwen3-coder:30b` attempted on <24 GB box; `OLLAMA_NUM_PARALLEL=1`, one loaded model.
- [ ] 10-prompt baseline exists (`research` registry): correctness / fields-present / TTFT / total / RAM per model.

### Fail → fix

| Fail | Fix |
|---|---|
| `no emit_tool_plan` mid-demo | Instant P3: Inspector proves server fine → swap to `demo-qwen-8k`, retry; keep canned JSON hotkey |
| Mixed ctx reload stalls | Pin ONE `num_ctx` (8192) across Modelfile + serve env + request options; never mix per-client values |
| `/v1` client ignores ctx | Use Modelfile-baked model; don't pass `num_ctx` in `/v1/chat/completions` (no such field) |
| GPU-split (CPU offload) | `ollama ps` PROCESSOR must be 100% GPU; free 2–3 GB (close browsers), `OLLAMA_MAX_LOADED_MODELS=1` |

## 4. Pass gate + log template

**Demo-ready = 2 consecutive clean runs of EACH drill (K, Q, W), logged.** Feature freeze D12 — after that only fallback/docs/rehearsal.

```markdown
## Fallback drill log — YYYY-MM-DD HH:MM (venue/home)
- Drill: K / Q / W (circle; fault injected: airplane / 429-allowlist / wrong-tag ___)
- Seconds to announce fallback: ___s (target <60s K+Q, <30s diagnose W)
- Seconds to tool result on screen: ___s (target <90s all)
- Evidence: [ ] photo/video timestamp  [ ] ollama ps CONTEXT=___ GPU=___%
-         [ ] synapse info shot (Q)  [ ] Inspector tools/list version ___ (Q/W)
- What broke: ___
- One-line fix: ___
- Verdict: PASS / FAIL — initials ___
```

File logs in `demo/logs/drill-YYYYMMDD-HHMM.md` + keep `synapse info` + `ollama ps` screenshots in `assets/quota-proof/`.

## 5. Cue card (tape to laptop lid)

```
HEALTH: curl $API/health | LOCAL: mycli --local --model demo-qwen-8k
LIST:   npx @modelcontextprotocol/inspector --cli ./server --method tools/list --format json | jq '{version: .serverInfo.version, tools: [.tools[].name]}'
CALL:   ... --method tools/call --tool-name T --tool-arg k=v --format json | jq .result
PS:     ollama ps  (MODEL=demo-qwen-8k CONTEXT=8192 GPU 100%)
QUOTA:  synapse info  (<=10 servers, <=100k lines) | shot -> assets/quota-proof/
VIDEO:  demo/golden.mp4 + demo/canned/*.json | HOTSPOT: <ssid>/<pass>
SAY:    K:"flipping to local, same tools, no cloud" Q:"expected branch — server fine, quota is limiter" W:"dropping below the model to prove the server"
RULE:   Golden -> Live -> Local -> Protocol -> Lesson. Never black. Never debug >20s silent.
```

## 6. Verify checklist (copy into runbook T-1h)

- [ ] K×2 logged, both <60s announce / <90s result
- [ ] Q×2 logged, both <60s P3, `isError:true` clean, quota screenshots saved
- [ ] W×2 logged, wrong tag diagnosed <30s, recovery <90s
- [ ] `demo/golden.mp4` (<3 min, captioned) on laptop + USB, plays silent-intelligible
- [ ] `demo/canned/` 3 JSON valid (`jq .` clean): `OnCall`, `breach_list`, `reroute_result`
- [ ] Hotspot paired, ports 8000/11434/6274 reachable, token in keychain
