# Track 3 Live Demo — `--discover` Beat (0–5 min)

> Goal: add one endpoint, rebuild, agent uses it straight away. Judged on **clean update**.
> Trap to beat: the `surface_cache` — clients cache the tool list at connect time, so a rebuild alone looks like "nothing happened" until you rescan/restart.

## Pre-demo checklist (do 10 min before stage)

- [ ] Pin versions: `synapse --version`, node/npx, client (Claude Desktop ≥ 0.9 / Cursor ≥ 0.45), Ollama (`ollama --version`)
- [ ] Pre-pull fallback model: `ollama pull qwen2.5:7b` (or `gpt-oss:20b` if GPU allows)
- [ ] Pre-build baseline so first build is warm: `synapse build --auto --all-endpoints`
- [ ] Open 3 windows: (1) terminal, (2) agent client with trace/tool pane visible, (3) audit log tail
- [ ] Font ≥ 18pt, terminal contrast high, notifications OFF
- [ ] Have fallback config files ready (see § Fallback)

## Exact commands (copy-paste)

```bash
# 0) Baseline — prove starting state (run before timer)
synapse --version
synapse build --auto --all-endpoints

# 1) Add ONE endpoint (live on stage — keep the diff tiny)
# e.g. add GET /healthz or POST /demo-ping to your router, then:
git diff --stat

# 2) The beat — rescan + rebuild with discovery
synapse build --auto --all-endpoints --discover --server-name demo-track3

# 3) Verify the new tool surfaced (do NOT skip — this is the judged moment)
synapse list-tools | grep -i -E "healthz|demo-ping"
synapse audit --last 1   # show rebuild record

# 4) Force client refresh (surface_cache trap — pick ONE for your client)
# Claude Desktop: Settings → Developer → MCP → Restart server / quit + relaunch
# Cursor: Settings → Tools & MCP → refresh icon next to server (hot reload, no restart)
# CLI / Inspector: disconnect + reconnect session
```

> Flag notes: `--auto` = non-interactive (no prompt stall on stage). `--all-endpoints` = don't silently drop the new route. `--discover` = rescan sources so the new endpoint is picked up. `--server-name demo-track3` = stable name so the client config doesn't need editing mid-demo.

## Client config snippet handling

Same `mcpServers` JSON shape works in Claude Desktop **and** Cursor (official MCP spec, Context7 `/modelcontextprotocol/modelcontextprotocol`). Show it on screen for 10s, don't type it live.

**Claude Desktop** — `claude_desktop_config.json` (restart required after edit):
```json
{
  "mcpServers": {
    "demo-track3": {
      "command": "synapse",
      "args": ["serve", "--server-name", "demo-track3", "--transport", "stdio"]
    }
  }
}
```

**Cursor project-scoped** — `.cursor/mcp.json` (hot reload, no restart — prefer this live):
```json
{
  "mcpServers": {
    "demo-track3": {
      "command": "synapse",
      "args": ["serve", "--server-name", "demo-track3", "--transport", "stdio"]
    }
  }
}
```

**If serving over HTTP/SSE instead of stdio** (e.g. remote or Superset-style pattern):
```json
{
  "mcpServers": {
    "demo-track3": { "type": "http", "url": "http://localhost:5008/mcp" }
  }
}
```

Script line: *"Same config object, two clients — stdio for local, http for remote. Cursor hot-reloads; Claude Desktop needs a restart — that's the cache trap."*

## Minute-by-minute script

| Time | Do | Say | Screen |
|------|----|-----|--------|
| 0:00–0:45 | State the bet. Show baseline agent failing: ask agent "hit the new `demo-ping` endpoint" → tool-not-found. | "Track 3 in one sentence: add endpoint, rebuild, agent uses it immediately. Watch it fail first so the fix means something." | Agent trace showing missing tool |
| 0:45–1:30 | Add ONE route live (`/demo-ping` returning `{"ok":true}`). `git diff --stat`. | "One endpoint, five lines. Nothing else changes." | Editor diff, terminal |
| 1:30–2:30 | Run the beat command: `synapse build --auto --all-endpoints --discover --server-name demo-track3`. Narrate each flag. | "auto so it never prompts, all-endpoints so nothing is skipped, discover so it rescans, server-name so the client config stays stable." | Terminal build output |
| 2:30–3:15 | Verify: `synapse list-tools \| grep demo-ping`. Refresh client (Cursor refresh button / Desktop restart). | "Here's where demos die — the client caches the tool list. Rebuild isn't enough; you must rescan AND reconnect." | `list-tools` hit + client refresh click |
| 3:15–4:15 | Ask agent again, no other changes: "call demo-ping and show the result". Agent calls it first try. | "Same prompt, no re-prompting, no code edit in the agent. Clean update." | Agent trace: tool call → `{"ok":true}` |
| 4:15–5:00 | Show audit: `synapse audit --last 1`. Close. | "And it's auditable — who rebuilt, what changed, when. That's the Track 3 bar." | Audit record fullscreen |

## What to show on screen (all three, always visible if possible)

1. **Terminal** — the exact commands above, large font. Never clear between steps; the scrollback IS the proof.
2. **Agent trace / tool pane** — before (tool missing) vs after (tool called). Judges watch for zero agent-side edits.
3. **Audit record** — `synapse audit --last 1` output: timestamp, endpoint hash, server name. Leave it up during Q&A.

## Fallback if network/quota fails — `--local` + Ollama

Trigger: any cloud-model error, rate-limit, or venue Wi-Fi drop. Say it out loud: *"Venue network is down — switching to local, same server."*

```bash
# Pre-pulled, zero network needed
ollama pull qwen2.5:7b
ollama run qwen2.5:7b "call demo-ping via MCP"

# Or point your agent client at local model, keep Synapse server identical:
synapse build --auto --all-endpoints --discover --server-name demo-track3 --local
synapse list-tools | grep -i demo-ping
```

Why this works as a fallback story: the MCP server is unchanged — only the model endpoint moves local. Qwen 2.5 / `gpt-oss:20b` / Qwen3.x have reliable native function-calling via Ollama; `qwen2.5:7b` runs on CPU-only laptops. Pre-pull before stage — the pull is what fails on bad Wi-Fi, not the run.

## If THAT fails (second fallback, 30s)

- Drop to MCP Inspector or `curl`: `curl localhost:<port>/demo-ping` → `{"ok":true}` + `synapse list-tools` grep. Say: "Server updated cleanly; client transport is the venue issue, not the build."
- Never debug on stage > 60s — cut to the pre-recorded 30s video/GIF of the full beat and keep narrating.

## Sources

- MCP `mcpServers` config shape (stdio vs http, Claude Desktop + Cursor parity): Context7 `/modelcontextprotocol/modelcontextprotocol` `query-docs` ("MCP client configuration mcpServers…") + web (Cursor/MCP config guides, Apache Superset MCP client docs for the http pattern).
- `synapse build --auto/--all-endpoints/--discover/--server-name` + `surface_cache` rescan trap framing: per brief; no authoritative upstream flag reference found via websearch (closest hits: Synapse-MCP Glama page, synapse-mcp.dev, MLflow `refresh_mcp_server_version_tools` dry-run/refresh pattern as the analogous "refresh tools" concept).
- Ollama local fallback (pre-pull, function-calling tags `qwen2.5:7b`, `gpt-oss:20b`, `qwen3.x`, `ollmcp` client pattern): vdf.ai MCP+Ollama setup guide, ollmcp GitHub, LocalLLM MCP+Ollama walkthrough.
