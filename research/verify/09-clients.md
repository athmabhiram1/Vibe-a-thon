# 09 — Client Pick for Live `--discover` Moment: Kill Cursor-Primary + Claude Desktop, Demo in Inspector Only

**Verdict: YES — kill both Cursor-primary and Claude Desktop as live demo clients. Demo `--discover` in MCP Inspector Web UI only (not `--cli`). Keep VS Code as silent backup. Skip Windsurf + web chatbot entirely.**

Live `--discover` needs: (1) zero-restart re-discovery, (2) `MCP_REV` cache-bust visibly working, (3) projector-readable output, (4) runs on a cold judge laptop with no login. Neither Cursor nor Claude Desktop meets any of the four. Inspector Web UI meets all four.

## Comparison Matrix

| Dimension | Cursor | Claude Desktop | Windsurf (Cascade) | VS Code + Copilot (Agent) | Web Chatbot (claude.ai / ChatGPT) | **MCP Inspector Web UI (pick)** | Inspector `--cli` / `--tui` |
|---|---|---|---|---|---|---|---|
| **Hot-reload vs restart** | ❌ Full restart required. `mcp.json` edits ignored; Refresh/Reconnect broken for non-stdio (known regression). | ❌ Worst. Every `claude_desktop_config.json` edit needs full quit + relaunch. #1 "it doesn't work" cause. | ⚠️ Reload Window (`Cmd+Shift+P → Reload Window`), no full quit. Better but still a visible interruption. | ✅ Best client. `Developer: Reload Window`; dev-mode `dev.watch: src/**/*.ts` auto-restarts server; experimental `chat.mcp.autostart` | ❌ No local stdio at all (remote connectors only). Cannot demo local `--discover`. | ✅ No restart. `npx @modelcontextprotocol/inspector node build/index.js` reconnects in 1 click. Deterministic re-list. | ✅ No restart, but — |
| **`MCP_REV` cache-bust reliability** | ❌ Tool list cached for process lifetime; forum asks for explicit "Force Refresh / Clear Cache" because bump is ignored until restart. | ❌ Cached + `Help → Troubleshooting → Clear Cache and Restart` needed. Bumping env in config does nothing live. | ⚠️ Cascade caches; reload-window usually picks up env change, occasionally stale. | ✅ `MCP: Reset Cached Tools` command explicitly clears stale list; most reliable client-side bust. | N/A — no env passthrough to local server. | ✅ Trivially reliable: restart server process or reconnect; no client-side tool cache. `MCP_REV=$(date +%s)` visibly re-lists. | ✅ Same, but output scrolls away. |
| **Projector readability** | ⚠️ Chat-sized monospace, dark-only, small tool cards. Readable to row 2. | ❌ Small chat font, no zoom-friendly tool inspector. Worst on projector. | ⚠️ Cascade panel narrow, cramped diff. | ✅ Agent-mode tool calls expandable, VS Code zoom (`Ctrl+=`) works. Second-best. | ✅ Large chat bubbles, but can't show tools/resources/prompts tabs. | ✅ Best: full-browser UI with Tools / Resources / Prompts tabs, big JSON panes, light theme. `Ctrl+Plus` fills a projector. | ❌ Tiny terminal text, unreadable past row 3. Kill `--cli` for live. |
| **Judge laptop compatibility** | ❌ Needs Cursor installed + OpenAI/Anthropic key + restart ritual. 5-min setup, fails offline. | ❌ Needs install + manual `claude_desktop_config.json` edit (path differs Mac/Win) + restart + admin rights. Slowest. | ❌ Needs Windsurf + account/login. | ⚠️ Needs VS Code + GitHub Copilot subscription/login. Common but paywalled. | ⚠️ Needs network + OAuth connector; venue Wi-Fi risk. | ✅ Needs only Node + `npx`. No login, no key, no config file, works offline with stdio. Cold-laptop king. | ✅ Same, but readability kills it. |
| **Config file portability** | `.cursor/mcp.json` (`mcpServers` + `command/args/env`). Not shared with others. | `claude_desktop_config.json` (OS-specific path, same `mcpServers` shape). Least portable. | `mcp_config.json` (`mcpServers` + `serverUrl` variant, `${env:}` interpolation). | `.vscode/mcp.json` (`servers` + `type: stdio`, `cwd`, `dev.watch`). Different top-level key! | No file — server must be deployed remote. | **No file needed**: `npx @modelcontextprotocol/inspector --server-url …` or `… node server.js`. Zero-file = maximally portable. | Same. |

## Evidence (websearch, Nov 2026)

1. **Cursor = restart required, reload broken:** "Save the file and restart Cursor completely. A common mistake is editing the config and expecting it to hot-reload" (evomap.ai); "Reconnect/reload and changes in mcp.json don't always pick up updates… Only a full Cursor restart" (forum.cursor.com/t/mcp-server-regression); comparison table: "Cursor: Restart Cursor required for config changes" (claudefa.st/blog/tools/mcp-extensions/cursor-mcp-setup).
2. **Claude Desktop = full restart every time:** "add the server to claude_desktop_config.json, and completely [restart]" (designrevision.com); "This restart is the single most common reason local MCP setups 'don't work'" (amie.so/mcp/claude-desktop); "Fully restart Claude Desktop after every fix" (phrasly.ai); "Choose Clear Cache and Restart" (docs.oracle.com + support.claude.com).
3. **Windsurf = reload-window, middle ground:** "Save the config file and reload the Windsurf window (Cmd/Ctrl+Shift+P → Reload Window)" (docs.ionos.com/cloud/ai/mcp-server); Cascade `mcp_config.json` docs (docs.devin.ai/windsurf/plugins/cascade/mcp); breakage reports when adding servers (r/Codeium).
4. **VS Code = best client hot-reload:** "VS Code does not always hot-reload… run Developer: Reload Window" (fast.io/resources/vscode-mcp-server-setup) BUT dev-mode offers `"dev": {"watch": "src/**/*.ts"}` auto-restart (code.visualstudio.com/api/extension-guides/ai/mcp); plus `MCP: Reset Cached Tools` clears stale list (offlinecreatorstudio.com).
5. **Inspector = deterministic, scriptable:** `npx @modelcontextprotocol/inspector` (web UI default), `--cli`, `--tui`, `mcpdo` (github.com/modelcontextprotocol/inspector); "Inspecting published servers: npx … --server-url … --transport http" (modelcontextprotocol.io/docs/tools/inspector); "official starting point… test tools, resources and prompts, script it in CI" (mcp.so/blog/mcp-inspector-guide, mcpjam.com, mcpplaygroundonline.com).
6. **Cache-bust is a process-lifetime problem everywhere except Inspector:** "MCP client sessions are cached for the process lifetime. The only way to recover is to restart" (abp.io/support/questions/10919); "Feature Request: Clear MCP Tool Cache / Force Refresh… reduce time spent debugging" (forum.cursor.com/t/167459).

## Why `MCP_REV` Fails Live in Clients

All GUI clients cache the tool list at connection time. Bumping `MCP_REV=2` in the JSON does nothing until the client process re-spawns the server — which in Cursor/Desktop means a full app restart (~15–30 s + projector dead air + "don't touch anything" moment). In front of judges that reads as broken. In Inspector Web UI the flow is: change env → click Reconnect → tools re-list instantly, with the new `MCP_REV` visible in the output pane. Deterministic, narratable, 3 seconds.

## Live Show Script (Inspector Web UI only)

1. `npx @modelcontextprotocol/inspector node build/index.js` — browser opens, zoom to 150%.
2. Tools tab → `List Tools` → count = N (point at projector).
3. Terminal: `MCP_REV=$(date +%s)` edit or add one tool → Inspector: Reconnect → `List Tools` → N+1. Crowd sees discovery.
4. Say once: "Same server works in Cursor / VS Code / Claude Desktop — configs in `research/verify/configs/` — but we won't restart an IDE on stage." Pre-empts "does it work in X?" without paying the restart tax.
5. Do NOT use `--cli`/`--tui` live: terminal JSON is unreadable past row 3 and scrolls the proof away. CLI is for CI (`--cli` exit codes), not the stage.

## Portability Note

Ship three one-screen config snippets in appendix only (don't live-demo them): `.vscode/mcp.json` (`servers`), `.cursor/mcp.json` / `mcp_config.json` / `claude_desktop_config.json` (`mcpServers`). Schemas differ at the top-level key, so copy-paste across clients fails — another reason Inspector (zero-file CLI args) is the portable demo. Web chatbot requires deploying to a public URL + OAuth; disqualifies it for a local `--discover` beat.

## Final Call

- **Kill:** Cursor-primary live, Claude Desktop live, Inspector `--cli` live, Windsurf live, web chatbot live.
- **Show:** Inspector Web UI only.
- **Backup (laptop, not projector):** VS Code Agent mode with `MCP: Reset Cached Tools` if a judge insists on "real client proof" after the talk.
