# 06 — MCP Clients: Config + Live `--discover` Refresh Choreography

> Scope: Claude Desktop (restart model) vs Cursor (hot-reload model), exact `mcpServers` JSON for stdio + HTTP, Inspector/curl fallback, pre-record plan.
> Sources: MCP spec + Inspector docs via Context7 (`/modelcontextprotocol/modelcontextprotocol`, spec 2025-11-25 / 2026-07-28); Cursor docs + forum (tool-list caching threads); Claude Desktop config guides.

## 1. Config file locations

| Client | File | Notes |
|---|---|---|
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` | Open via Settings → Developer → Edit Config |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` | e.g. `C:\Users\<you>\AppData\Roaming\Claude\claude_desktop_config.json` |
| Claude Desktop (Linux) | `~/.config/Claude/claude_desktop_config.json` | Create if missing |
| Cursor (project, share with team) | `<repo>/.cursor/mcp.json` | Preferred for demos — checked in, more reliable per forum reports |
| Cursor (global) | `~/.cursor/mcp.json` | Applies to all projects |
| MCP Inspector (ad-hoc) | any `./mcp.json` passed via `--config` | `mcp-inspector --cli --config ./mcp.json --server <name> --method tools/list` |

## 2. Exact JSON snippets (copy-paste)

### 2a. stdio server — works in Claude Desktop, Cursor, Inspector

```json
{
  "mcpServers": {
    "my-stdio-server": {
      "command": "node",
      "args": ["C:\\ABS\\PATH\\TO\\build\\index.js"],
      "env": { "API_KEY": "sk-..." }
    }
  }
}
```

Python / `uv` variant (official weather example — use **absolute** paths; on Windows double-escape):

```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": ["--directory", "C:\\ABS\\PATH\\TO\\weather", "run", "weather.py"]
    }
  }
}
```

Get the full `uv` path if the client can't find it: `where uv` (Windows) / `which uv` (macOS), then put the absolute path in `command`.

### 2b. Streamable HTTP server (remote / `http`)

Modern Inspector schema (mirrored by Cursor; Claude Desktop ≤ mid-2026 needs the `mcp-remote` shim below):

```json
{
  "mcpServers": {
    "my-modern-server": {
      "type": "http",
      "url": "https://api.example.com/mcp",
      "headers": { "X-Tenant": "acme", "Authorization": "Bearer <token>" }
    }
  }
}
```

Claude Desktop shim for HTTP (Claude Desktop is stdio-native; bridge with `mcp-remote`):

```json
{
  "mcpServers": {
    "kdbx-streamable": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/mcp"]
    }
  }
}
```

### 2c. Cursor `mcp.json` — full demo file (project-level)

```json
{
  "mcpServers": {
    "demo-stdio": {
      "command": "node",
      "args": ["./build/index.js"],
      "env": { "MCP_REV": "1" }
    },
    "demo-http": {
      "type": "http",
      "url": "http://localhost:3000/mcp?v=1"
    }
  }
}
```

> `MCP_REV` / `?v=N` are deliberate cache-buster knobs — see §4.

### 2d. Inspector catalog file (same schema, adds per-server tuning)

```json
{
  "mcpServers": {
    "my-modern-server": {
      "type": "http",
      "url": "https://api.example.com/mcp",
      "protocolEra": "modern",
      "headers": { "X-Tenant": "acme" },
      "roots": [{ "uri": "file:///C:/demo/project", "name": "project" }]
    }
  }
}
```

Run it: `mcp-inspector --cli --config ./mcp.json --server my-modern-server --method tools/list`
Override headers for one run: add `--header "X-Tenant: acme"`.

## 3. Restart vs hot reload — the one rule to memorize

- **Claude Desktop = FULL RESTART.** Editing `claude_desktop_config.json` does nothing until you fully Quit (tray icon → Quit, not just X) and relaunch. If MCP UI elements don't appear, your `mcpServers` has zero valid servers — fix JSON first.
- **Cursor = HOT RELOAD (+ cache gotchas).** Cursor watches `mcp.json` via filesystem events, re-parses, hashes each server, and diffs. Refresh icon / toggle restarts *that server*; no app restart needed. BUT: tool *lists* are cached — changing server code without changing config may show stale tools until you force a hash change (§4).

## 4. Cursor cache-bust tricks (when refresh "does nothing")

1. **Bump a dummy env (stdio):** `"env": { "MCP_REV": "2" }` → save → new hash → Cursor reloads tools from scratch.
2. **Bump a dummy query param (HTTP):** `"url": "http://localhost:3000/mcp?v=2"`.
3. **Toggle off → on**, then hit the **refresh (circular arrow)** in Settings → Tools & Integrations.
4. Nuclear: `Developer: Reload Window` / full Cursor restart; local stdio servers share one background process across windows, so a full restart is the only guaranteed flush.

## 5. Minute-by-minute live `--discover` refresh choreography (10-min demo)

Assumes project-level `.cursor/mcp.json` + a terminal with Inspector CLI ready + pre-recorded fallback video (see §6).

| Time | Action | Narration cue | Verify |
|---|---|---|---|
| 0:00–1:00 | Show starting `tools/list` in Cursor (v1 tools). | "This is our baseline — two tools." | Screenshot/eye-check |
| 1:00–2:30 | Add new tool to server code, rebuild (`npm run build`). | "I just added `summarize`; code is rebuilt." | `ls build/index.js` timestamp |
| 2:30–3:30 | **No-restart attempt:** hit Cursor refresh icon. Show stale list (expected). | "Watch — refresh alone still shows v1. That's the tool-list cache." | Point at missing tool |
| 3:30–4:30 | Bump `"MCP_REV": "1"` → `"2"` (or `?v=2`), save. Cursor file-watcher fires. | "One env bump changes the config hash — Cursor reloads from scratch." | Green dot / server restarts |
| 4:30–5:30 | `tools/list` again — new tool appears. Call it once in chat. | "There it is — live discovery, no app restart." | Tool executes |
| 5:30–6:30 | Claude Desktop contrast (slides or second machine): show config edit → **Quit → relaunch** → tool appears. | "Same change in Claude Desktop costs a full restart — that's the tradeoff." | Before/after screenshots |
| 6:30–8:00 | Deep-verify with Inspector CLI (independent of both clients). | "Trust but verify — ask the protocol directly." | See commands below |
| 8:00–10:00 | Q&A / show fallback video if anything red. | "And if the network dies, here's the same flow pre-recorded." | Play video |

Commands for the 6:30 slot (run while talking):

```bash
# stdio server — list tools
npx -y @modelcontextprotocol/inspector --cli node build/index.js --method tools/list
# Streamable HTTP server — list tools
npx -y @modelcontextprotocol/inspector --cli --transport http --server-url http://localhost:3000/mcp --method tools/list
# Call a tool and pretty-print
npx -y @modelcontextprotocol/inspector --cli node build/index.js --method tools/call --help
```

## 6. Fallback ladder (Inspector → curl → pre-record)

1. **Inspector TUI (visual):** `npx -y @modelcontextprotocol/inspector` → connect stdio command or `http://localhost:3000/mcp` → Tools → List → Call. Best on projector.
2. **Inspector CLI (scriptable, CI-friendly):** commands in §5. Pipe through `jq`; `--protocol-era modern --method tools/list` for noisy servers.
3. **Raw `curl` (Streamable HTTP only):** useful when Inspector won't install:
   ```bash
   curl -s -X POST http://localhost:3000/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | jq .
   ```
   stdio servers have no URL — curl can't reach them; use CLI instead.
4. **Pre-record (mandatory):** record the full §5 flow once end-to-end (Cursor refresh + hash bump + Inspector CLI). Keep `demo-fallback.mp4` < 3 min on desktop + USB. If live fails at 2:30, play video, narrate over it, debug later.

## 7. Pre-demo checklist (night before + morning-of)

- [ ] `node --version`, `npx -y @modelcontextprotocol/inspector --version` work offline (cache populated).
- [ ] Absolute paths in every `command`/`args`; no `~/` or relative tricks in Claude Desktop.
- [ ] `.cursor/mcp.json` committed; `MCP_REV` reset to `"1"` so the live bump reads clearly.
- [ ] Claude Desktop fully Quit-tested once after a config edit.
- [ ] `demo-fallback.mp4` plays with sound off and is understandable.
- [ ] Phone hotspot ready (venue Wi-Fi dies during MCP demos with suspicious regularity).

## 8. Sources

- MCP Inspector config schema + CLI (`configuration.mdx`, `cli.mdx`, spec 2026-07-28) via Context7.
- `tools/list` / `tools/call` JSON-RPC shapes via MCP spec 2025-11-25 via Context7.
- Cursor `mcp.json` locations + refresh-icon behavior: Cursor docs (`cursor.com/help/customization/mcp`), mcpverdict/fast.io setup guides 2026.
- Cursor tool-list caching + `MCP_REV` / `?v=2` hash-bump workarounds: Cursor forum threads (174607, 173112, 167459, 168307).
- Claude Desktop paths (`%APPDATA%\Claude`, `~/Library/Application Support/Claude`) + restart requirement: aiagentskit/fastero/casdoor 2026 guides + MCP `build-server.mdx` weather example.
- Inspector CLI/CI patterns: `modelcontextprotocol/inspector` README + `cli-smoke-testing.md`.
