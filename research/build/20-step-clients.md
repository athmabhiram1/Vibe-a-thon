# Step 20 — MCP Client Wiring: Claude Desktop + Cursor + Inspector

> Source: `research/final/06-mcp-clients.md`. Goal: get the same server visible in all three clients, with a rehearsed live-refresh flow and a way out when caching bites.

## 1. Claude Desktop config (FULL RESTART model)

**File locations:**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json` (via Settings → Developer → Edit Config)
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Copy-paste — stdio (Node):**
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

**Copy-paste — stdio (Python / uv, official weather pattern):**
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
If the client can't find `uv`/`node`, use the absolute binary path (`where uv` / `which uv`).

**Copy-paste — Streamable HTTP via shim (Claude Desktop is stdio-native):**
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

**Refresh choreography (memorize):**
1. Edit JSON (absolute paths only — no `~/`, no relative `args`).
2. Validate JSON (a trailing comma = zero servers load, and the MCP UI silently disappears).
3. Fully **Quit** Claude Desktop (tray icon → Quit, not just window X) → relaunch.
4. Verify: MCP tools/menu appear. If absent, config parsed to zero valid servers — fix paths first.

## 2. Cursor config (HOT RELOAD + cache gotchas)

**Files (project-level preferred for demos — check it in):**
- Project: `<repo>/.cursor/mcp.json`
- Global: `~/.cursor/mcp.json`

**Copy-paste — full demo file:**
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

**Copy-paste — modern HTTP server with headers:**
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

**Refresh choreography:**
1. Save `mcp.json` → Cursor's file-watcher re-parses, hashes each server, and diffs. No app restart.
2. Hit the **refresh (circular arrow)** in Settings → Tools & Integrations, or toggle the server off → on, to restart *that server*.
3. Re-run `tools/list` to confirm the new tool appears.

**Cache-bust (when refresh "does nothing" — stale tool list):**
1. stdio: bump `"MCP_REV": "1"` → `"2"` and save (new hash → full reload).
2. HTTP: bump `?v=1` → `?v=2` in the URL.
3. Toggle off → on + refresh icon.
4. Nuclear: `Developer: Reload Window` or full Cursor restart (local stdio servers share one background process across windows — only a full restart guarantees a flush).

## 3. Inspector CLI (independent verifier)

**Catalog file (same schema + tuning):**
```json
{
  "mcpServers": {
    "my-modern-server": {
      "type": "http",
      "url": "https://api.example.com/mcp",
      "headers": { "X-Tenant": "acme" },
      "roots": [{ "uri": "file:///C:/demo/project", "name": "project" }]
    }
  }
}
```

**Copy-paste commands:**
```bash
# Config-file mode — list tools
mcp-inspector --cli --config ./mcp.json --server my-modern-server --method tools/list
# Per-run header override
mcp-inspector --cli --config ./mcp.json --server my-modern-server --method tools/list --header "X-Tenant: acme"

# Ad-hoc stdio — no config file
npx -y @modelcontextprotocol/inspector --cli node build/index.js --method tools/list
# Ad-hoc Streamable HTTP
npx -y @modelcontextprotocol/inspector --cli --transport http --server-url http://localhost:3000/mcp --method tools/list
# Tool call (+ help for args shape)
npx -y @modelcontextprotocol/inspector --cli node build/index.js --method tools/call --help

# Raw curl fallback (HTTP only; stdio has no URL)
curl -s -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | jq .
```

Visual fallback on a projector: `npx -y @modelcontextprotocol/inspector` (TUI) → connect → Tools → List → Call.

## 4. Live `--discover` choreography (10 min)

| Time | Action | Narration cue |
|---|---|---|
| 0:00–1:00 | Show baseline `tools/list` in Cursor (v1). | "Baseline — two tools." |
| 1:00–2:30 | Add tool, rebuild (`npm run build`). | "Added `summarize`; rebuilt." |
| 2:30–3:30 | Hit Cursor refresh; show **stale** list (expected). | "Refresh alone shows v1 — tool-list cache." |
| 3:30–4:30 | Bump `MCP_REV` → `2` (or `?v=2`), save. | "Env bump changes the hash — full reload." |
| 4:30–5:30 | `tools/list` again, call the new tool in chat. | "Live discovery, no restart." |
| 5:30–6:30 | Contrast slide: Claude Desktop edit → Quit → relaunch. | "Same change costs a full restart there." |
| 6:30–8:00 | Inspector CLI verify (commands §3). | "Trust but verify — ask the protocol directly." |
| 8:00–10:00 | Q&A / fallback video if red. | Pre-recorded `demo-fallback.mp4` (<3 min, on desktop + USB). |

## 5. Pre-demo checklist

- [ ] `node --version` + `npx -y @modelcontextprotocol/inspector --version` work offline (cache warm).
- [ ] Absolute paths in Claude Desktop config; `MCP_REV` reset to `"1"`.
- [ ] `.cursor/mcp.json` committed; Quit-relaunch tested once for Claude Desktop.
- [ ] `demo-fallback.mp4` plays silent-intelligible; phone hotspot ready.
