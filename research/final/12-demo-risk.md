# 12 — Demo Risk Hardening for Solo Builder

> Deployed API (Render / Railway / HF) + quota 10 servers / 100k lines + `--local` Ollama fallback (qwen2.5:7b, num_ctx) + network death + surface_cache trap. Fallback ladder P0–P4 + rehearsal drills.
> Research: 6+ queries — Render FastAPI deploy, Railway FastAPI, HF Docker Spaces, Ollama num_ctx / context-length, Modelfile reference, MCP Inspector (web/CLI/TUI).

## 0. TL;DR

- **Never demo live-only.** Ship P0 pre-record + live API + local Ollama + Inspector/curl + narrative flip. Any single failure degrades one level, never to black screen.
- **Cold start is the #1 killer** on Render/Railway/HF free tiers (sleep after ~15 min idle). Warm it, pin `/health`, keep a local mirror.
- **Ollama default context will silently truncate your demo** unless you pin `num_ctx`. For qwen2.5:7b use `PARAMETER num_ctx 8192` (Modelfile) + verify with `ollama ps` CONTEXT column.
- **Inspector is your offline proof** that the MCP server speaks protocol correctly even when the model/cloud dies.

## 1. Deployment realities (what actually breaks)

### 1.1 Render — FastAPI Web Service
Standard recipe (verified across Render docs + 3 tutorials):
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT` (newer: `fastapi run main.py --port $PORT`)
- Must bind `0.0.0.0` + `$PORT`, not `127.0.0.1:8000`.
- Add `/health` + `/readyz` endpoints; set `healthCheckPath` in `render.yaml`.
- Free: 750 hrs/mo (one service always-on in theory) but **sleeps after 15 min inactivity** → 30–60s cold start on first demo request.
- Secrets via Environment tab, never in repo. Changing env triggers redeploy.
- IaC: `render.yaml` blueprint pins `runtime: python`, `buildCommand`, `startCommand`, `healthCheckPath`, `DATABASE_URL fromDatabase`.

Demo gotchas: wrong import path (`app.main:app` vs `main:app`) is #1 boot crash; missing `uvicorn` in requirements + stale build cache is #2.

### 1.2 Railway — FastAPI
Four paths: 1-click template, GitHub repo, CLI (`railway init; railway up`), Dockerfile.
- Default start uses **Hypercorn**: `hypercorn main:app --bind "::"` (per `railway.json`).
- No public URL by default → Settings → Networking → Generate Domain.
- Pricing (Oct 2026 check): Trial $5 credit/30d → Free $1/mo (1 project, 3 services, 1 vCPU/0.5GB, sleeps when idle) → Hobby $5/mo incl. $5 usage → Pro $20/mo. Billed per-second CPU/RAM/egress.
- Ephemeral disk 1 GB (Free) / 100 GB (paid); need Volume for persistence.
- Free-tier **peak-hour deploy bans** (8AM–8PM local per region) + Serverless sleep → cold boot on first hit.

Demo gotchas: too many workers OOMs the 0.5 GB box (keep `UVICORN_WORKERS=2`), `DATABASE_URL` format mismatch, migrations silently skipped (add `set -e` deploy hook).

### 1.3 Hugging Face Spaces — Docker (FastAPI)
Use when you need model + API co-located, or free GPU grant story.
- `README.md` frontmatter: `sdk: docker` + `app_port: 7860`.
- Dockerfile must: `CMD ["uvicorn","main:app","--host","0.0.0.0","--port","7860"]`, `USER user` (UID 1000, non-root), single foreground process, no daemons.
- Limits: 16 GB RAM / 2 CPU / 50 GB ephemeral disk on CPU Basic. Gradio/Docker compute requires PRO (or Team/Enterprise for orgs); free personal = max 2 Gradio on ZeroGPU, Static free unlimited.
- Every push rebuilds + restarts. Pre-download weights in build (`HF_HOME` cache) or first request pays download + load latency.

Demo gotchas: listening on `127.0.0.1` = unreachable; forgetting `app_port`; model download at startup needs network at runtime.

### Platform pick for solo demo
| Need | Pick |
|---|---|
| Cheapest predictable live URL | Render ($7/mo fixed avoids Railway variable bills) |
| Postgres+Redis+worker in one project | Railway (1-click DB, private networking) |
| ML weights + API + free GPU story | HF Docker Space + ZeroGPU / grant |
| Zero-network guarantee | None — use `--local` ( §3 ) |

## 2. Quota math: 10 servers / 100k lines

Assume the harness caps at **10 registered MCP servers and 100k indexed lines** (typical solo-builder guardrail against context blowout).

- 10 servers × ~8 tools avg = 80 tools. At ~300 tokens/tool schema, listing alone = 24k tokens — before any file content.
- 100k lines × ~10 tokens/line ≈ 1M tokens if naively stuffed. You never fit that in qwen2.5:7b (32k tag / 128k arch max, 4–8k practical local).
- Harden by **surface reduction**:
  1. Register only 2–3 servers needed for the narrative; disable the rest (`--only`, config allowlist).
  2. Prefer `readOnlyHint:true` + paginated tools (`limit`, `offset`, `path` filters).
  3. Pre-index summaries, not raw lines: `ctags` / embeddings / `HEAD.md` per repo; lazy-load full file only on explicit tool call.
  4. Budget: reserve 2k for system + 2k for tool schemas + N for retrieved chunk + 2k for output = size `num_ctx` accordingly (§3).

Quota-exceeded signal: `429`, `RESOURCE_EXHAUSTED`, truncated `tools/list`, or empty `structuredContent`. Treat as **expected branch**, not exception — jump ladder to P3 (Inspector raw call proves server is fine, quota is the limiter).

## 3. `--local` Ollama fallback: qwen2.5:7b + num_ctx

### 3.1 Why it fails silently
Ollama's default context is **VRAM-tiered, not model-max**:
- `<24 GiB VRAM → 4096`, `24–48 GiB → 32768`, `≥48 GiB → 262144` (current docs; older texts say 2048 — trust `ollama ps`).
- qwen2.5:7b advertises 32k (library tag) / 128k arch (Qwen docs), but Ollama gives you **4k on a typical 8–16 GB laptop unless you override**.
- Overflow = silent truncation of oldest tokens. Symptom: model "forgets" system prompt / top of doc, still returns 200 OK.

### 3.2 The fix (bake it, don't hope it)
```dockerfile
# Modelfile.local-qwen
FROM qwen2.5:7b-instruct
PARAMETER num_ctx 8192
PARAMETER temperature 0.2
PARAMETER num_predict 2048
SYSTEM """You are a concise demo assistant. Answer from provided context only."""
```
```bash
ollama create demo-qwen-8k -f Modelfile.local-qwen
ollama run demo-qwen-8k "Say OK."
ollama ps  # check CONTEXT column == 8192, PROCESSOR == 100% GPU
curl -s 127.0.0.1:11434/api/ps | jq .  # context_length field
```

Rules:
- Sizing: short chat 4k; doc Q&A 8k; agent/coding 16–32k minimum (Ollama docs advise ≥64k for agents — halve that for 7B on 16 GB or you'll OOM).
- Cost: weights Q4_K_M ≈ 4.5–5 GB + KV cache linear in `num_ctx` (~×2 per doubling) × `OLLAMA_NUM_PARALLEL`. On 16 GB leave 2–3 GB for OS; keep `OLLAMA_NUM_PARALLEL=1–2`, `OLLAMA_MAX_LOADED_MODELS=1`.
- Precedence: request `options.num_ctx` > Modelfile `PARAMETER num_ctx` > `OLLAMA_CONTEXT_LENGTH` > VRAM default. **OpenAI `/v1/chat/completions` has no `num_ctx` field** — `/v1` clients must use a Modelfile-baked model.
- Changing `num_ctx` reloads the model; mixed values across clients cause reload stalls. Pin one value per demo.
- Serve explicitly: `OLLAMA_CONTEXT_LENGTH=8192 ollama serve` (systemd `Environment=` / Docker `-e`). Never rely on bare `ollama` in scripts (post-v0.32 launches agent mode).

### 3.3 Local switch command
```bash
# .env.demo
# MODEL_URL=https://my-api.onrender.com/mcp
MODEL_URL=http://127.0.0.1:11434/v1
MODEL_NAME=demo-qwen-8k
APP_MODE=local
```
One-flag flip in your CLI (`--local` sets the above) + pre-pulled model = works on airplane Wi-Fi.

## 4. Network death (assume it *will* happen)

Venue Wi-Fi + free-tier cold start + DNS captive portal = the classic triple-kill.

Mitigations:
- Pre-warm: `curl $API/health` + one real `tools/call` 10 min before stage; keep tab open (prevents Render/Railway sleep).
- Bundle: local clone of slides, video file (not YouTube link), `requirements.txt` + Docker image pre-pulled, Ollama model pre-pulled (`ollama pull qwen2.5:7b` night before).
- Tether: phone hotspot name/password in clipboard; test `curl` over hotspot in rehearsal.
- Ports: Ollama `11434`, Inspector `6274`/`6275` — confirm no firewall block; carry `curl` equivalents for every Inspector click (below).
- No auth-at-demo-time: pre-fetch tokens; short-lived OAuth will expire mid-talk. Use static `Authorization: Bearer $TOKEN` header saved in password manager + Inspector Server Settings.

## 5. surface_cache trap

The harness caches **tool surfaces** (`tools/list` schemas + descriptions) separately from data. Stale cache → model calls a tool with old args, gets `invalid params`, blames the model.

Symptoms: Inspector shows new schema but agent uses old args; fixed by restart but reappears after edit.

Fixes:
- Version your surfaces: bump `serverInfo.version` on every schema change; assert it in `/health`.
- Invalidate on deploy: `rm -rf ~/.mcp-inspector/mcp.json` cache or start Inspector with fresh `--catalog`; restart MCP client session after server rebuild.
- Demo-proof: run `tools/list` live in Inspector Protocol tab at start of demo — audience sees ground truth, and you catch drift before `tools/call`.
- Stdio hygiene: only JSON-RPC on stdout; logs to stderr. A stray `print()` on stdout poisons the surface and looks like a protocol bug.

## 6. Pre-flight checklist (print this)

### T-24h
- [ ] `pip freeze > requirements.txt` includes `fastapi uvicorn`; start command binds `0.0.0.0:$PORT` (Render) / `7860` (HF) verified from clean clone.
- [ ] `/health` + `/docs` return 200 on deployed URL. Save `curl` outputs to `demo/logs/`.
- [ ] `render.yaml` / `railway.json` / `Dockerfile` committed; auto-deploy from `main` tested with trivial commit.
- [ ] `ollama pull qwen2.5:7b && ollama create demo-qwen-8k -f Modelfile.local-qwen`; `ollama ps` shows CONTEXT 8192, GPU.
- [ ] `npx @modelcontextprotocol/inspector --cli <server> --method tools/list` passes from laptop (no browser needed).
- [ ] P0 video recorded (1080p, captions, <3 min), exported to `demo/golden.mp4` + USB stick.
- [ ] Quota audit: `servers ≤10`, indexed lines sampled, `tools/list` token estimate <4k.

### T-1h (venue)
- [ ] Warm API: `for i in 1 2 3; do curl -s $API/health; sleep 5; done`; open `/docs` in tab.
- [ ] Local: `ollama ps`, `curl 127.0.0.1:11434/api/chat -d '{"model":"demo-qwen-8k","messages":[{"role":"user","content":"ping"}]}'`.
- [ ] Inspector: `npx @modelcontextprotocol/inspector` opens with token URL; test one `tools/call` (valid + one invalid to show error handling).
- [ ] Network: speedtest + hotspot paired; `MCP_INSPECTOR_API_TOKEN` noted; `CLIENT_PORT` fallback if 6274 taken.
- [ ] Battery + charger + HDMI/USB-C adapter + offline copy of this file.

### T-10min (stage)
- [ ] Close Docker/Chrome tabs; `OLLAMA_NUM_PARALLEL=1`; phone on DND, hotspot ready.
- [ ] Terminal 1: API logs tail. Terminal 2: `curl` one-liners. Terminal 3: Inspector. Browser: golden video paused at 0:00.
- [ ] Say out loud: "If live fails I play video; if net fails I go local; if model fails I show protocol." (ladder below).

## 7. Fallback ladder P0–P4

> Rule: announce the level, don't apologize. Each level is a *feature* (resilience), not a failure.

| Level | Name | Trigger | Script (30s) | Commands |
|---|---|---|---|---|
| **P0** | **Pre-record (golden)** | Anything dead, or cold-start >20s | "Here's the golden path recorded this morning — I'll narrate the live signals underneath." Play `golden.mp4`. | `mpv demo/golden.mp4` / VLC; keep live logs scrolling beside it |
| **P1** | **Live deployed** | Happy path | Full story on Render/Railway/HF URL + `/docs` Swagger `Try it out`. | `curl $API/health; curl $API/docs` |
| **P2** | **Local switch (`--local`)** | Network death, 5xx, cold-start loop, quota 429 | "Venue Wi-Fi is doing venue things — flipping to the local build, same tools, no cloud." `APP_MODE=local`. | `OLLAMA_CONTEXT_LENGTH=8192 ollama serve &`; `mycli --local --model demo-qwen-8k` |
| **P3** | **Inspector / curl (protocol proof)** | Model hallucinates, tool args drift, surface_cache suspected | "Let's drop below the model and prove the server is correct." Show `tools/list` → `tools/call` valid → invalid. | `npx @modelcontextprotocol/inspector --cli ./server --method tools/list --format json`; `... --method tools/call --tool-name <t> --tool-arg k=v`; `curl $API/mcp -H "Authorization: Bearer $TOKEN"`; compare Protocol vs Network tabs |
| **P4** | **Narrative flip** | Total loss (power, projector, time cut) | "The failure *is* the lesson: cold starts, silent truncation, stale surfaces — here's the 60s version and the checklist." Whiteboard the three traps + ladder. | 1 slide: trap → fix → verify (`ollama ps`, `/health`, `tools/list`). End on P0 video link + repo QR |

Escalation order: P1 → (fail in <15s) → P0 playing while you attempt P2 in background → P3 as commentary over P0 → P4 if time remains. Never debug silently on stage >20s.

## 8. Rehearsal drills (run both, twice)

### Drill A — kill-network (15 min)
1. Start live demo. Teammate runs `sudo iptables -A OUTPUT -d <api-host> -j DROP` or simply enable airplane mode + kill hotspot.
2. You must reach P2 in <60s: `APP_MODE=local`, `ollama run demo-qwen-8k`, one tool call via Inspector `--cli` (no browser network needed for stdio servers).
3. Pass criteria: audience sees a tool result in <90s of cut; `ollama ps` CONTEXT still 8192; no secrets pasted on screen.
4. Reset: restore net, `curl $API/health` to re-warm, note cold-start seconds in log.

### Drill B — quota-exceeded (15 min)
1. Temporarily set server allowlist to 3 tools + inject `429` on 4th call (or revoke API key / set `MAX_LINES=100`).
2. You must reach P3 in <60s: show `tools/list` in Inspector, call allowed tool (success JSON via `| jq .result`), call blocked tool (clean `isError:true`, no key leak), narrate surface budget (§2).
3. Then flip to P4: "With 10 servers we'd page; with 3 we finish the story."
4. Pass criteria: no stack trace on projector; error shown is user-readable; `surface_cache` invalidated (`version` bump visible in `serverInfo`).

Log both drills: date, seconds-to-fallback, what broke, one-line fix. Two clean runs = demo-ready.

## 9. One-page cue card (tape to laptop)

```
HEALTH: curl $API/health  |  LOCAL: mycli --local --model demo-qwen-8k
LIST:   npx @modelcontextprotocol/inspector --cli ./server --method tools/list
CALL:   ... --method tools/call --tool-name T --tool-arg k=v --format json | jq .result
PS:     ollama ps  (CONTEXT must be 8192, GPU)
VIDEO:  demo/golden.mp4  |  HOTSPOT: <ssid>/<pass>  |  TOKEN in keychain, not slides
SAY:    "Golden → Live → Local → Protocol → Lesson. We never go black."
```

## Sources (spot-check Nov 2026)

- Render FastAPI deploy: Build `pip install -r requirements.txt`, Start `uvicorn main:app --host 0.0.0.0 --port $PORT`; 750 free hrs, sleeps 15 min; `render.yaml` + `healthCheckPath` — render.com/docs/deploy-fastapi, render.com/hosting/fastapi.
- Railway FastAPI: template/GitHub/CLI/Dockerfile; Hypercorn `main:app`; Generate Domain; trial $5 → Free $1 → Hobby $5; peak-hour free-deploy bans — docs.railway.com/guides/fastapi, railway.com/pricing.
- HF Spaces Docker: `sdk: docker`, `app_port: 7860`, non-root `USER user`, single `uvicorn --host 0.0.0.0 --port 7860`; 16GB/2CPU/50GB; Docker needs PRO — huggingface.co/docs/hub/spaces-sdks-docker, spaces-overview.
- Ollama context: VRAM tiers 4k/32k/256k; `PARAMETER num_ctx`, `OLLAMA_CONTEXT_LENGTH`, per-request `options.num_ctx`; verify `ollama ps` CONTEXT + `/api/ps context_length`; OpenAI `/v1` can't set ctx (use Modelfile); KV cache linear cost — docs.ollama.com/context-length, docs.ollama.com/modelfile, docs.ollama.com/api/openai-compatibility.
- qwen2.5:7b: 32k tag / 128k arch, Q4_K_M ~4.5–5GB; default 2048/4096 truncates long prompts silently — ollama.com/library/qwen2.5, markaicode Qwen2.5+Ollama integration.
- MCP Inspector: `npx @modelcontextprotocol/inspector` (web) / `--cli` / `--tui`; `--method tools/list|tools/call --tool-name --tool-arg`; `--server-url …/mcp --transport http`; token `MCP_INSPECTOR_API_TOKEN`, ports 6274/6275; stdout=protocol, stderr=logs; Protocol vs Network tabs — modelcontextprotocol.io/docs/tools/inspector, scalar.com/learn/mcp/test-mcp-servers, hostedmcp.org/learn/mcp-inspector.
