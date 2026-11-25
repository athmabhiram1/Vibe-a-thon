# MCP Clients — Inspector LIVE, IDE configs BACKUP ONLY

> Plan §6 + `research/final/06-mcp-clients.md`. **LIVE demo client = MCP Inspector Web UI only.**
> `.cursor/mcp.json`, `.vscode/mcp.json`, `claude_desktop_config.example.json` are
> **backup proof** (judge rerun / screenshots). Never live — they cache tool lists till restart/hash-bump.

## 1. LIVE script — Inspector Reconnect (~3s)

Preconditions: `hr` on :8001, `it` on :8002, Synapse server built (13 baseline tools, 14 post-discover — 11/12 functional-only with health excluded via `--endpoints` allowlist; H5 `hr_get_oncall` is live on disk, L1 `it_oncall_coverage` is the live-add, ~5s, same server ID — evidence `research/verify-final/12-synapse-run.md` §4).

```bash
# 1. Open Inspector TUI (projector-friendly)
npx -y @modelcontextprotocol/inspector
# Connect → stdio: command `python synapse_auto_server.py`
#   OR Streamable HTTP: http://localhost:8001/mcp  (per Synapse snippet)

# 2. Baseline: Tools → List (expect 13) → call it_sla_breach_list once
```

Live `--discover` moment (restore `it_service/routers/live_moment.py` = L1 `GET /it/oncall-coverage` → rebuild with expanded allowlist):

```bash
# Baseline (pre-discover) allowlist — 11 functional ops (H1-H5 + I1-I6), prefix-STRIPPED (CLI 0.1.9 detects `GET /candidates`, not `GET /hr/candidates`).
# /demo/* (6 ops) + 2 health probes excluded from the functional list; L1 excluded until the live moment.
synapse build --auto --endpoints "GET /candidates,GET /candidates/{candidate_id},POST /employees,GET /shifts,GET /oncall,GET /equipment,POST /equipment/assign,POST /tickets,GET /tickets/breaches,GET /tickets/{ticket_id},POST /tickets/{ticket_id}/reroute" --server-name hr-api
# LIVE: expanded allowlist adds L1 (+1 = 12 functional, 14 with health):
synapse build --discover --auto --endpoints "GET /candidates,GET /candidates/{candidate_id},POST /employees,GET /shifts,GET /oncall,GET /equipment,POST /equipment/assign,POST /tickets,GET /tickets/breaches,GET /tickets/{ticket_id},POST /tickets/{ticket_id}/reroute,GET /oncall-coverage" --server-name hr-api
# same server ID, no client re-config (~5s; 12-synapse-run.md §4 median ~4.8s ×3 rehearsals)
```

Then in Inspector: **Disconnect → Reconnect (~3s) → Tools → List → 14 tools, `it_oncall_coverage` appears.**
Call it, then chain `it_reroute_ticket` for anything in `needs_reroute` (seeded breaches T-5001/T-5002/T-5019 → on-call EMP-014 Kiran Desai). Narrate: "Same server ID. Reconnect re-lists. No restart."

Headless / CI equivalent (no UI):

```bash
# stdio list
npx -y @modelcontextprotocol/inspector --cli python synapse_auto_server.py --method tools/list
# Streamable HTTP list
npx -y @modelcontextprotocol/inspector --cli --transport http --server-url http://localhost:8001/mcp --method tools/list
# call (+ arg-shape help)
npx -y @modelcontextprotocol/inspector --cli python synapse_auto_server.py --method tools/call --help
```

No `inspector/` directory is written — Inspector is a runtime tool, this file is its runbook.

## 2. Why NO live IDE restart

| Client | Refresh model | Why it kills a live demo |
|---|---|---|
| MCP Inspector | Disconnect → Reconnect re-lists from the protocol (~3s) | — (this is why it is LIVE) |
| Cursor | Hot-reload config, but **tool list cached** till hash change + toggle/refresh | Refresh alone shows stale v1; needs `MCP_REV` bump dance (30–60s of dead air) |
| VS Code | Same cache + reload-window tax; `servers` schema differs | Stale list + wrong-key silent zero-server failure |
| Claude Desktop | **FULL Quit → relaunch** (tray Quit, not window X) | 15–30s restart on stage; zero valid servers = MCP UI silently disappears |

Backup-only rule: IDE configs exist so a judge can rerun without Inspector.
On stage, any "let me restart Cursor" = fallback to P0 video (`demo/golden.mp4`).

Cursor cache-bust (backup path only, when refresh "does nothing"):

1. stdio: bump `"MCP_REV": "1"` → `"2"`, save (new hash → full reload).
2. HTTP: bump `?v=1` → `?v=2`.
3. Toggle server off → on, hit refresh in Settings → Tools & Integrations.
4. Nuclear: `Developer: Reload Window` / full restart.

Claude Desktop: edit JSON (absolute paths only, `py -m json.tool` to validate) →
tray Quit → relaunch → hammer 🔨 icon → tool list.

## 3. Backup table — what is checked in

| File | Top-level key | Why this key | Refresh |
|---|---|---|---|
| `.cursor/mcp.json` | `mcpServers` | Cursor spec (verified 2026-11-22) | File-watcher hot reload + `MCP_REV` hash bump |
| `.vscode/mcp.json` | `servers` | VS Code editor-managed format (NOT `mcpServers`); needs per-entry `"type": "stdio"` | Reload window / MCP refresh |
| `claude_desktop_config.example.json` | `mcpServers` | Claude Desktop stdio-native format; copy to `%APPDATA%\Claude\claude_desktop_config.json` (Win) with absolute paths | Full Quit → relaunch |
| (no `inspector/` dir) | n/a — Inspector reads ad-hoc CLI args or any `--config` catalog | — | Reconnect (~3s) |

> Gotcha that eats demos: pasting a `mcpServers` block into `.vscode/mcp.json`
> (or a `servers` block into Cursor/Desktop) is **valid JSON that silently loads zero
> servers**. Check the key first. CI asserts this (see §5).

`MCP_REV=1` in the checked-in files is a deliberate cache-buster knob — the live bump
reads `"1"` → `"2"` (see `research/final/06-mcp-clients.md` §4).

## 4. curl equivalents (Streamable HTTP only)

stdio servers have no URL — curl cannot reach them; use Inspector CLI instead.
For HTTP transports (Synapse hosted / Streamable HTTP endpoints):

```bash
# initialize
curl -s -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}' | jq .

# tools/list (needs session header from initialize if server requires it)
curl -s -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | jq .

# tools/call example (replace name/args with real tool)
curl -s -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"it_sla_breach_list","arguments":{}}}' | jq .
```

## 5. Verify (fresh machine)

```bash
# JSON parses + correct top-level keys
python -c "import json; d=json.load(open('.cursor/mcp.json')); assert 'mcpServers' in d, d.keys(); print('cursor OK:', list(d['mcpServers']))"
python -c "import json; d=json.load(open('.vscode/mcp.json')); assert 'servers' in d, d.keys(); print('vscode OK:', list(d['servers']))"
python -c "import json; d=json.load(open('claude_desktop_config.example.json')); assert 'mcpServers' in d, d.keys(); print('desktop OK:', list(d['mcpServers']))"
# absolute-path check for Desktop example is manual (reviewer replaces C:\ABS\PATH)
```

Inspector handshake (needs built server):

```bash
npx -y @modelcontextprotocol/inspector --cli python synapse_auto_server.py --method tools/list
```

## 6. Sources

- `research/final/06-mcp-clients.md` (Context7 MCP spec + Inspector docs, Cursor docs/forum, Desktop guides).
- `research/build/20-step-clients.md`, `research/build/38-verify-client.md`.
- Key-schema check 2026-11-22: Cursor `mcpServers` (cursor.com/docs/mcp),
  VS Code `.vscode/mcp.json` `servers` + `"type"` (code.visualstudio.com + 1.146 deprecation notes).

## 7. `--endpoints` allowlist (why G2/G6 hold)

Synapse `--all-endpoints` would ingest every `operation_id` in both openapis —
HR 9 + IT 11 = 20 ops (verified via `/openapi.json`: 5+7 functional incl. H5 +
L1, 2×`/health`, 6×`/demo/*`). The gates assume a curated surface, so both
builds pass an explicit `--endpoints` allowlist instead. **Paths are
prefix-STRIPPED: CLI 0.1.9 detects `GET /candidates`, not `GET /hr/candidates`
(prefixed form fails `Endpoints Not Found` — load-bearing finding,
`research/verify-final/12-synapse-run.md` §2).** Both health endpoints share
`GET /health`, so tool names disambiguate (`hr_health_check,it_health_check`).

- **Always excluded:** 6 `/demo/*` ops — `hr_demo_seed`, `hr_demo_reset`,
  `hr_demo_status`, `it_demo_seed`, `it_demo_reset`, `it_demo_status`
  (judge-rerun helpers, never agent tools). Without this exclusion the counts
  blow to 20 and G2 (openapi operationIds) / G6 (discover == 14) fail.
- **Excluded for functional-only counts:** 2 health ops — `hr_health_check`,
  `it_health_check` (liveness probes, ingested by `--all-endpoints`).
- **Baseline allowlist (13 tools):** 11 functional (H1-H5 + I1-I6) + 2 health.
  Functional-only = 11. L1 `it_oncall_coverage` excluded until the live moment.
  Working form: `GET /candidates,GET /candidates/{candidate_id},POST /employees,GET /shifts,GET /oncall,GET /equipment,POST /equipment/assign,POST /tickets,GET /tickets/breaches,GET /tickets/{ticket_id},POST /tickets/{ticket_id}/reroute,hr_health_check,it_health_check`.
- **Post-discover allowlist (14 tools):** baseline + `GET /oncall-coverage`
  (`it_oncall_coverage`). Functional-only = 12. Same server ID (`hr-api`).

Canonical counts: **13 baseline / 14 post-discover** (11/12 functional-only).
`GET /it/oncall-coverage?team=support-night` must return 200 on seeded data
(prewarm asserts it; on-call = EMP-014 Kiran Desai via SH-08); unknown team 404s exactly like H5 `GET /hr/oncall`.
