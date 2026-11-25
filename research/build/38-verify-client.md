# 38 — Verify MCP Client Handshake (Fresh Machine)

> Goal: prove your MCP server works from a clean client: Claude Desktop (stdio) + Cursor (`mcp.json`) + Inspector CLI (`tools/list`, `tools/call` valid + invalid). Includes `pip install mcp`, `ast.parse` smoke test, hammer-icon check, and PATH fixes.

## 0. Fresh-machine preconditions

- [ ] OS noted: Windows 11 / macOS / Linux + arch (`python --version`, `node --version`)
- [ ] Python 3.10+ installed: `python --version`
- [ ] Node 18+ installed (Inspector needs npx): `node --version`
- [ ] No stale venv / old `mcp` package: `pip show mcp` → uninstall if version pinned wrong
- [ ] Project path has no uncommitted secrets; server file path absolute, no `~` shortcuts in client JSON

## 1. Install + smoke test (`pip install mcp`, `ast.parse`)

```powershell
# Windows (PowerShell) — fresh machine
py --version
py -m pip install --upgrade pip
py -m pip install mcp
py -c "import mcp; print(mcp.__version__)"
```

```bash
# macOS / Linux
python3 --version
python3 -m pip install --upgrade pip
python3 -m pip install mcp
python3 -c "import mcp; print(mcp.__version__)"
```

Syntax gate before any client test:

```powershell
py -c "import ast; ast.parse(open('server.py').read()); print('ast.parse OK')"
# or: py -m py_compile server.py && echo OK
```

- [ ] `import mcp` prints version, no error
- [ ] `ast.parse` / `py_compile` passes

## 2. Claude Desktop — stdio handshake

Config locations:

| OS | Path |
|---|---|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Minimal config (Windows example — use absolute paths, double backslashes):

```json
{
  "mcpServers": {
    "my-server": {
      "command": "C:\\Python313\\python.exe",
      "args": ["C:\\Users\\you\\project\\server.py"],
      "env": { "PYTHONUTF8": "1" }
    }
  }
}
```

macOS/Linux example:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "/usr/bin/python3",
      "args": ["/home/you/project/server.py"]
    }
  }
}
```

Steps:

- [ ] `File → Exit` Claude completely (tray icon too), then relaunch — config only reloads on cold start
- [ ] Open a new chat → **hammer 🔨 icon** visible in composer input row
- [ ] Click hammer → your server name + tool list appears
- [ ] Ask: `list your MCP tools and call <tool> with a trivial arg`
- [ ] Check logs if hammer missing: `%APPDATA%\Claude\logs\mcp*.log` (Win) or `~/Library/Logs/Claude/mcp*.log` (Mac)

Hammer-icon check matrix:

| Symptom | Cause → Fix |
|---|---|
| No hammer | Bad JSON (trailing comma) → validate at `jsonlint.com` or `py -m json.tool config.json` |
| Hammer + red dot / 0 tools | `command` not found → use absolute python path (see §5 PATH fixes) |
| Hammer shows server, call spins | Server blocking on stdin/readline → remove `input()`; flush prints; add `if __name__=="__main__": mcp.run()` guard |
| Works after restart only | Claude caches config — always fully quit, not just close window |

## 3. Cursor — `.cursor/mcp.json`

Project file: `<project>/.cursor/mcp.json` (workspace scope). Global alternative: `~/.cursor/mcp.json`.

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "${workspaceFolder}",
      "env": { "PYTHONUTF8": "1" }
    }
  }
}
```

Steps:

- [ ] Save file → Cursor `Settings → MCP` shows `my-server` with green dot
- [ ] If red: hover for stderr; fix command/cwd; `MCP → Refresh`
- [ ] Agent chat: run a valid `tools/call` via model (“use my-server to …”)
- [ ] Confirm tool result returns in chat transcript

> Cursor uses `cwd` + `${workspaceFolder}`; Claude Desktop does not support `cwd` — keep both configs in repo (`claude_desktop_config.example.json` + `.cursor/mcp.json`).

## 4. Inspector CLI — `tools/list` + `tools/call` (valid + invalid)

```bash
# stdio server
npx -y @modelcontextprotocol/inspector python server.py
# then open the printed http://127.0.0.1:6274 URL
```

Headless / scripted alternative (no UI):

```bash
# list
npx -y @modelcontextprotocol/inspector --cli python server.py --method tools/list
# valid call (replace names/args with yours)
npx -y @modelcontextprotocol/inspector --cli python server.py --method tools/call \
  --tool-name add --tool-arg num1=2 --tool-arg num2=3
# invalid call — expect structured error, NOT a crash
npx -y @modelcontextprotocol/inspector --cli python server.py --method tools/call \
  --tool-name no_such_tool --tool-arg x=1
npx -y @modelcontextprotocol/inspector --cli python server.py --method tools/call \
  --tool-name add --tool-arg num1=badtype
```

Checklist:

- [ ] `tools/list` returns every expected tool with description + JSON schema
- [ ] Valid `tools/call` returns correct result
- [ ] Invalid tool name → `Method not found`-style error, server stays alive
- [ ] Invalid args → validation error (not traceback leak to client)
- [ ] Server logs handshake: `initialize → notifications/initialized → tools/list`

## 5. PATH fixes (fresh-machine #1 failure)

```powershell
# Windows — find real interpreters
where python
where py
py -0p
$env:PATH -split ';'
# permanent add (new terminal required)
setx PATH "$env:PATH;C:\Python313;C:\Python313\Scripts"
```

```bash
# macOS / Linux
which -a python3
echo $PATH
# add to ~/.zshrc or ~/.bashrc:
export PATH="$HOME/.local/bin:$PATH"
```

Rules:

- [ ] In client JSON prefer **absolute** interpreter path (`where python` output), never bare `python` on fresh machines
- [ ] If using venv: `"command": "<proj>\\.venv\\Scripts\\python.exe"` (Win) or `"<proj>/.venv/bin/python"` (Mac/Linux)
- [ ] After PATH change: fully quit client + open **new** terminal before retest
- [ ] Verify inside client env: point a debug tool at `sys.executable` / `echo PATH` if still failing

## 6. Done / sign-off

- [ ] Claude Desktop hammer → list → valid call works
- [ ] Cursor `mcp.json` green dot → agent call works
- [ ] Inspector `tools/list` + valid `tools/call` + 2 invalid calls recorded (paste outputs into PR/test log)
- [ ] `pip show mcp` version + `ast.parse OK` screenshot/log saved
- [ ] Config examples committed (no secrets), PATH notes added for next fresh machine
