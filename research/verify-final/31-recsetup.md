# 31 — Recording-Night Setup Checklist (VERIFIED against actual repo state, 2026-11-25)

> Every item below was verified live on this machine against
> `C:\Users\athma\OneDrive\Desktop\my projects\VIBE_CODE`.
> Commands are the ACTUAL commands for THIS repo — not generic advice.
> Sources read: `run.bat`, `scripts/up.sh`, `scripts/prewarm.sh`,
> `scripts/share.sh`, `demo/SHOTLIST.md`, `submission/captions/demo.srt`,
> `.synapse/config.json`, `.synapse/surface_cache.json`, `.env` / `.env.example`.

## 0. TL;DR status (verified 2026-11-25)

| Item | State |
|---|---|
| Backend boots? | ✅ YES — ports 8001+8002 ALREADY responding (servers running now) |
| `run.bat` golden path | ✅ present, frozen ports 8001/8002, SQLite, no Docker |
| `scripts/prewarm.sh` | ✅ present, probes functional endpoints |
| `demo/SHOTLIST.md` | ✅ present (75s, 6 beats), record path `demo/golden.mp4` |
| `submission/captions/demo.srt` | ✅ present, 6 cues 0:00→1:15 (reuse as-is, do NOT regenerate) |
| `demo/golden.mp4` path | ✅ FREE (no file exists — nothing to overwrite) |
| `demo/quota-proof.png` | ❌ MISSING — capture on recording night (step 6) |
| OBS Studio | ❌ NOT installed (only a leftover `C:\Program Files\obs-studio\data` stub, no exe; `winget list --name OBS` = nothing) |
| CapCut | ❌ NOT installed (`winget list --name CapCut` = nothing) |
| Recorder fallback | ✅ `ffmpeg 9.1-full_build` works; Xbox Game Bar (`Win+G`) also available |
| ngrok | ✅ v3.39.11-msix-stable present |
| Mobile hotspot | ⚠️ legacy `netsh wlan hostednetwork` = NOT supported on this adapter — use Windows Settings → Mobile Hotspot, NOT netsh |
| USB stick | ⚠️ NO removable drive mounted right now — bring + plug one on the night |
| Ollama | ✅ running; 6 models pulled — BUT `qwen2.5:7b` (named in SHOTLIST) is NOT among them (see §7) |
| Synapse quota | ✅ `2/10` servers used (8 headroom), `775/100.0K` lines (99.2K headroom) |
| `MCP_REV` | ✅ `"1"` in both `.env` and `.env.example` — keep at 1 for the take |
| `it_service/routers/live_moment.py` (L1) | ✅ present on disk |

## 1. Backend boot (CHOOSE ONE — run.bat is primary on this Windows box)

`scripts/up.sh local` and `scripts/prewarm.sh` are **bash** scripts (Git Bash/WSL).
On this machine the native path is `run.bat`. Verified contents (lines 22–23):

```bat
cd "C:\Users\athma\OneDrive\Desktop\my projects\VIBE_CODE"
.\run.bat
```

What it does (verified in file): starts
`uvicorn hr_service.main:app --host 127.0.0.1 --port 8001` and
`uvicorn it_service.main:app --host 127.0.0.1 --port 8002`,
waits 5s, then probes `http://localhost:8001/hr/candidates?limit=1`
and `http://localhost:8002/it/tickets/breaches`.
SQLite files auto-create (`HR_DB_PATH=seed/demo.db`, `IT_DB_PATH=seed/demo.db` per `.env.example`).
**Verified right now: both ports already answer (`TcpTestSucceeded: True`), so on recording night just re-run `run.bat` in a fresh boot to guarantee clean state.**

Bash alternative (only inside Git Bash, same dir):

```bash
./scripts/up.sh local      # = pip install + 2x uvicorn + ./scripts/prewarm.sh local
```

## 2. Prewarm (T-10 min, AND after every reboot — ACTUAL command)

```bash
./scripts/prewarm.sh local     # Git Bash
```

Verified probes (from the actual script): 3× `GET /hr/candidates?limit=1`,
`GET /openapi.json` + `/docs` on both services,
3× `GET /it/tickets/breaches`,
`GET /it/oncall-coverage?team=support-night` (expect 200 → EMP-014 Kiran Desai),
plus `ollama /api/ps` (prints "ollama not running (ok — P2 fallback only)" if down — safe to ignore).

Windows-native equivalent (no bash needed, same coverage):

```powershell
curl.exe -s "http://localhost:8001/hr/candidates?limit=1"
curl.exe -s "http://localhost:8002/it/tickets/breaches"
curl.exe -s "http://localhost:8002/it/oncall-coverage?team=support-night"
curl.exe -s http://localhost:8001/openapi.json | Out-Null; "HR ok"
curl.exe -s http://localhost:8002/openapi.json | Out-Null; "IT ok"
```

## 3. Seed reset (before EVERY take, incl. retakes — per SHOTLIST §4)

```powershell
curl.exe -X POST "http://localhost:8001/hr/demo/seed" -H "x-demo-confirm: yes"
curl.exe -X POST "http://localhost:8002/it/demo/seed" -H "x-demo-confirm: yes"
```

(Header + guard verified in `.env.example`: `ALLOW_DEMO_SEED=true`, 6/min/IP.)

## 4. Synapse pre-take verification (ACTUAL frozen IDs on this box)

Verified in `.synapse/config.json`:

- `hr-api` → `6269969f-3f80-4a9f-a6e1-43237197dc42`
- `it-api` → `5fe96a56-ccb4-4483-a7e2-5a9cd2588b15`

Run before recording:

```powershell
synapse info
```

Expect (verified live output 2026-11-25): `MCP servers 2 / 10 used (8 remaining)`,
`Lines indexed 775 / 100.0K (99.2K remaining)`.
Baseline = **13 tools**; after the live `--discover` tail = **14**, SAME server id
(evidence: `research/verify-final/12-synapse-run.md` §4, ~4.8s median over 3 rehearsals).
⚠️ Do NOT run a second plain `synapse build` without `--new` — it would collide with the frozen IDs.

Live-tail command (verbatim from `demo/SHOTLIST.md` §2 cue card — paste, never type):

```bash
synapse build --discover --auto --endpoints "GET /candidates,GET /candidates/{candidate_id},POST /employees,GET /shifts,GET /oncall,GET /equipment,POST /equipment/assign,POST /tickets,GET /tickets/breaches,GET /tickets/{ticket_id},POST /tickets/{ticket_id}/reroute,GET /oncall-coverage" --server-name hr-api
```

## 5. Recorder — OBS/CapCut MISSING, use this instead

- **OBS: not installed.** `C:\Program Files\obs-studio` contains only a `data\` stub (virtual-cam DLL), no `obs64.exe`; `where obs64.exe` empty; winget finds no OBS package. Either `winget install OBSProject.OBSStudio` **before** recording night and set 1920×1080/30fps/x264/12–15 Mbps/MP4 → `demo\golden.mp4` per SHOTLIST §2, or:
- **Fallback (verified working): `ffmpeg 9.1`** is installed. Full-screen 1080p30 capture to the EXACT required path:

```powershell
ffmpeg -f gdigrab -framerate 30 -i desktop -c:v libx264 -preset veryfast -b:v 14M "demo\golden.mp4"
```

(q to stop; keep a second copy as `demo\golden-take2.mp4`.)
- **CapCut: not installed** (winget finds nothing, no `%LOCALAPPDATA%\CapCut`). No edit is needed anyway — SHOTLIST mandates ONE take, no cuts. Upload raw.
- **Captions: reuse `submission/captions/demo.srt` as-is** (verified: 6 cues, 00:00:00→00:01:15, matches shot list). Do NOT regenerate.

## 6. Output paths + USB + upload (verified free / missing)

- `demo\golden.mp4` — **does NOT exist** ✅ (path free, no backup needed).
- `demo\golden-take2.mp4` — does NOT exist ✅.
- `demo\quota-proof.png` — **does NOT exist** ❌ → capture on the night: screenshot of `synapse info` (showing `2/10`, `775/100.0K`) and/or API/quota dashboard, save to `demo\quota-proof.png`.
- USB: **no `DriveType=2` removable drive mounted now** → bring a stick, then:

```powershell
Copy-Item "demo\golden.mp4","submission\captions\demo.srt","demo\quota-proof.png" E:\
```

(replace `E:` with the actual mount; verify with `Get-CimInstance Win32_LogicalDisk -Filter "DriveType=2"`).
- YouTube: upload `golden.mp4` as **Unlisted** → Captions → upload `demo.srt` → paste URL into submission form + README. Play back on phone over venue Wi-Fi to confirm captions + 1:00–1:15 tail.

## 7. Network, hotspot, offline fallback

- Venue rule (`scripts/share.sh`): primary is ALWAYS localhost; share-mirror only:

```bash
NGROK_DOMAIN=<your-dev-domain> ./scripts/share.sh   # ngrok 3.39.11 verified present
```

If ngrok drops → keep demoing on localhost, no pause (kill-network drill <90s).
- Hotspot: `netsh wlan show drivers` → **"Hosted network supported: No"** on this adapter, so do NOT rely on `netsh hostednetwork`. Pair via **Windows Settings → Network → Mobile Hotspot** before the take.
- Offline model fallback: `ollama list` (verified) = `qwen2.5-coder:7b`, `tev1:4b`, `llama3.1:8b`, `llama3.2:3b`, `qwen3:8b`, `qwen3-embedding:0.6b`.
  ⚠️ **Mismatch:** SHOTLIST §4 says "qwen2.5:7b pre-pulled" but that exact tag is NOT installed (`qwen2.5-coder:7b` is the closest). Either `ollama pull qwen2.5:7b` on the night (needs net) or amend the cue card to `qwen2.5-coder:7b`. Golden path needs no model (stub default, `OLLAMA_HOST=http://localhost:11434`), so this is P2-fallback only.

## 8. Night-of sequence (10 min → take → upload)

1. [ ] DND on, taskbar hidden, browser 125–150%, `frontend.html` LEFT 55% + terminal RIGHT-TOP (≥18pt) + audit tail RIGHT-BOT (`tail -f audit.log`, leave up through Q&A).
2. [ ] `.\run.bat` → both probes print HTTP codes.
3. [ ] Seed reset (§3) → prewarm (§2) → `synapse info` (13 tools baseline, `2/10` quota) → oncall-coverage returns EMP-014.
4. [ ] Confirm `MCP_REV=1` untouched; `live_moment.py` on disk (verified present); H5 `GET /hr/oncall` live.
5. [ ] Phone timer 75s visible; press Record; run the 6 beats verbatim (`demo/SHOTLIST.md` §1 + `demo.srt` narration).
6. [ ] Stop; verify `demo\golden.mp4` = 74–76s, peaks −12…−6 dB, tagline `8 tools deleted. 1 decision.` legible; copy + `quota-proof.png` + `demo.srt` to USB; YouTube Unlisted + captions; second-device playback check.

*Fallback ladder if a take fails: P0 play golden ("Here's the golden path recorded this morning…") → P2 `APP_MODE=local` → P3 Inspector `tools/list`+`tools/call` proof → P4 whiteboard flip. Never debug silently >20s (SHOTLIST §6).*
