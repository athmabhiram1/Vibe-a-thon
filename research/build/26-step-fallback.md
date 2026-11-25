# 26 — Fallback Ladder P0–P4 + 60s Golden Video (Demo Never Dies)

> Companion to `research/final/12-demo-risk.md` (risk register) and `05-deploy.md` (topology). Principle: **every live call has a pre-recorded twin**. If P1 fails you drop one rung in <10s with a narrative flip line — audience sees competence, not panic.

## 0. Ladder at a glance

| Level | Name | What it is | When to use | Prep cost |
|---|---|---|---|---|
| **P0** | Golden video | 60s pre-recorded `demo/golden.mp4` — full happy path, no network | Cloud down + local dead + no Wi-Fi | 1 hr record once |
| **P1** | Live cloud | Real `$API` (Render/Railway/HF) + live LLM | Default — everything warm | Pre-warm cron |
| **P2** | Local Ollama | `docker compose up` → `localhost:8000` + Ollama `demo-qwen-8k` | Cloud cold-start / 429 / venue Wi-Fi blocks egress | `ollama pull` + compose |
| **P3** | Protocol proof | No LLM — Inspector `--cli` + `curl` JSON-RPC receipts | LLM slow/hallucinating, but MCP server alive | Canned `receipts/*.json` |
| **P4** | Lesson close | Whiteboard the architecture + lesson learned | Nothing runs (laptop dies) | 1 cue card |

**Rule: rehearse every drop.** Run `P1→P2→P3→P0` drill twice before demo day. Each transition must be <10s and have a flip line (§5).

```
P1 live ──(timeout/5xx/cold-start>8s)──▶ P2 local ollama ──(ollama slow)──▶ P3 inspector/curl receipts ──(laptop dead)──▶ P0 golden.mp4 ──(no projector)──▶ P4 lesson close
```

## 1. P0 — 60s golden video (record once, carry on USB)

### 1.1 Pre-record script (60s, 6 shots × 10s)

| # | Sec | Screen | Narration (read verbatim) | Command running |
|---|---|---|---|---|
| 1 | 0–10 | Title card `demo/title.png` | "MCP server in 60 seconds: one endpoint, three tools, verified live." | — |
| 2 | 10–20 | Terminal: `curl tools/list` | "First, discovery — the client asks what tools exist, pins the server version." | §4 cmd 1 |
| 3 | 20–30 | Inspector UI: `search_docs` call | "Second, a tool call — search the docs, with citations, not hallucinations." | Inspector `tools/call` |
| 4 | 30–40 | Terminal: `curl tools/call` receipt | "Third, the receipt — JSON-RPC with timing, cache header, version stamp." | §4 cmd 2 |
| 5 | 40–50 | Browser: `/docs` Swagger + `/health` | "Health and docs ship with the server — one container, one port." | `open $API/docs` |
| 6 | 50–60 | Title card + repo URL + QR | "Code, Dockerfile, and compose are linked — clone and run `docker compose up`." | — |

Record with OBS (1080p, mic on), export `demo/golden.mp4` (H.264, <50 MB). Copies: laptop `demo/`, USB stick `GOLDEN/`, phone gallery, and one cloud link (unlisted YouTube / Drive).

### 1.2 Play commands (no network needed)

```bash
# mpv (preferred — fast seek, fullscreen, stays on top)
mpv --fs --ontop --no-terminal demo/golden.mp4
# pause/resume: Space | seek ±10s: ←/→ | quit: q

# VLC fallback (every venue laptop has it)
vlc --fullscreen --no-qt-bgcone demo/golden.mp4
# Windows absolute path variant:
"C:\Program Files\VideoLAN\VLC\vlc.exe" --fullscreen "demo\golden.mp4"

# If projector is 4:3, force aspect so receipts stay readable:
mpv --fs --video-aspect-override=16:9 demo/golden.mp4
```

**Flip line (P-any → P0):** *"The cloud is having a moment — good news, I recorded the exact run this morning. Sixty seconds, then I'll take questions while it retries in the background."* → hit play, keep talking over it.

## 2. P1 — Live cloud (default path + pre-warm)

```bash
export API=https://<svc>.onrender.com   # or Railway / HF :7860 URL
# Pre-warm (run 10 min before stage + keep Swagger tab open as warmer):
curl -s $API/health; curl -s $API/readyz
# Abort threshold: if ANY call >8s or non-2xx twice → drop to P2, do not retry on stage.
curl -m 8 -s -X POST $API/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | head -c 500
```

Pre-warm cron (categorical — cold start is killer #1): UptimeRobot / GitHub Action `*/5 * * * * curl $API/health`.

## 3. P2 — Local Ollama switch (hotspot-safe, ~15s)

Pre-pull once (venue night before, hotel Wi-Fi):

```bash
ollama pull qwen2.5:7b
ollama create demo-qwen-8k -f ./Modelfile   # Modelfile: FROM qwen2.5:7b / PARAMETER num_ctx 8192
ollama ps   # confirm CONTEXT 8192, PROCESSOR 100% GPU
docker compose -f docker-compose.demo.yml up --build -d
curl -s localhost:8000/health && curl -s localhost:11434/api/ps
```

On-stage switch (single alias — put in `demo/switch.sh`):

```bash
export API=http://localhost:8000
# same curl as P1, just repointed — audience sees identical receipt shape
curl -m 8 -s -X POST $API/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_docs","arguments":{"query":"fallback ladder"}}}' | python -m json.tool
```

**Flip line (P1 → P2):** *"That latency is the free-tier cold start I warned about — let's remove the network entirely. Same server, now on this laptop."* → `docker compose up`, continue.

## 4. P3 — Protocol proof: Inspector CLI + curl receipts (no LLM needed)

Use when the model is slow but the MCP server answers. Prove the **protocol**, not the intelligence.

```bash
# 1. Discovery receipt (always works, no model involved)
curl -s -X POST $API/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | tee receipts/tools-list.json | python -m json.tool
# assert: .result.serverInfo.version == deployed version (surface_cache check)

# 2. Canned tool-call receipt (deterministic fixture — checked into repo)
curl -s -X POST $API/mcp -H 'Content-Type: application/json' \
  -d @receipts/search-docs.call.json | tee receipts/search-docs.receipt.json | python -m json.tool
# receipts/search-docs.call.json:
# {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_docs","arguments":{"query":"deployment cold start"}}}

# 3. Inspector CLI (proves schema without browser)
npx @modelcontextprotocol/inspector --cli --transport sse --server-url $API/mcp tools/list
npx @modelcontextprotocol/inspector --cli --transport sse --server-url $API/mcp tools/call \
  --name search_docs --args '{"query":"fallback ladder"}'
# Stdio variant (local server file, zero network):
npx @modelcontextprotocol/inspector --cli server.py tools/list

# 4. Replay a golden receipt if server is fully dead (diff proves parity)
diff <(python -m json.tool receipts/golden-tools-list.json) \
     <(python -m json.tool receipts/tools-list.json) && echo "PARITY OK"
```

Keep `receipts/` in repo: `golden-tools-list.json`, `search-docs.call.json`, `search-docs.receipt.json` (recorded from a known-good run). On stage: `cat` the golden receipt — *"this is byte-identical to this morning's run."*

**Flip line (P2 → P3):** *"The model is thinking — while it does, let me show you what's actually on the wire. This is the raw JSON-RPC any client sends; no SDK magic."* → run curl, show receipt.

## 5. P4 — Lesson close (nothing runs)

Cue card (print, pocket):

> **Lesson:** MCP moves the integration surface from N×M clients to 1 versioned protocol. Version pin (`serverInfo.version`) + `surface_cache` + `/health` = the whole reliability story. Golden video + local compose + protocol receipts = demo that can't die.

**Flip line (P-any → P4):** *"And that's the real lesson — I built this so a single endpoint survives even this. Slides over, here's the architecture on the whiteboard, and the repo link for later."*

## 6. Cue card (tape to laptop lid)

```
P0 ▶ mpv --fs demo/golden.mp4          | line: "recorded this morning, 60s"
P1 ● curl -m 8 $API/health             | abort if >8s twice → P2
P2 ● docker compose up + API=localhost  | line: "remove the network entirely"
P3 ● curl tools/list + inspector --cli  | line: "what's actually on the wire"
P4 ● whiteboard + repo QR               | line: "single endpoint survives this"
USB: GOLDEN/ | phone: golden.mp4 | receipts/: golden-*.json
```

## 7. Pre-flight checklist (night before + 10 min before)

- [ ] `demo/golden.mp4` plays offline (mpv + VLC tested, USB + phone copies)
- [ ] `ollama ps` → 8192 ctx; `docker compose up` → `/health` 200 offline (airplane-mode test)
- [ ] `receipts/golden-*.json` fresh (re-recorded after last schema change)
- [ ] Pre-warm cron green; Swagger tab open; `export API=` + `switch.sh` tested
- [ ] Inspector installed (`npx --yes @modelcontextprotocol/inspector --version`)
- [ ] Cue card printed; QR to repo works; phone hotspot named + password known
- [ ] Drill: P1→P2→P3→P0 each <10s with flip lines said aloud twice
