# VENUE.md — Demo-Day Readiness (print this + tape the cue card to the laptop)

> Grounding: `research/final/12-demo-risk.md` (fallback ladder P0–P4, pre-flight),
> `research/verify-final/13-prewarm-clients.md` (counts 13/14, stale-server + bash warnings),
> `docs/CLIENTS.md` (Inspector live script), `demo/SHOTLIST.md` (75s golden take).
> Verified 2026-11-24 UTC: `scripts/prewarm.sh local` all-200 ( incl. ollama after
> OLLAMA_HOST normalize fix); HR :8001 + IT :8002 live on disk code; synapse quota
> 2/10 servers, 775/100K lines; Inspector CLI 2.13.0.

## 0. Known gaps before venue (do not skip)

- [ ] `demo/golden.mp4` NOT recorded yet — **user records** per `demo/SHOTLIST.md`
      (75s one-take, captions reused from `submission/captions/demo.srt`). No P0 until this exists.
- [ ] `qwen2.5:7b` NOT in `ollama list` (have qwen3:8b, llama3.1:8b, tev1:4b).
      Night-before pull required (see §1).

## 1. Night-before checklist (T-12h, on home network)

- [ ] Models: `ollama pull qwen2.5:7b` then
      `ollama create demo-qwen-8k -f Modelfile.local-8k`;
      `ollama ps` must show CONTEXT 8192 (12-demo-risk §3 — default 4k silently truncates).
- [ ] Charge: laptop 100% + charger + HDMI/USB-C adapter + phone charger packed.
- [ ] USB stick (FAT32/exFAT): `/golden.mp4` (verify 74–76s, audio −12…−6 dB, tagline legible),
      `/demo.srt` (= `submission/captions/demo.srt`), `/quota-proof.png`
      (synapse quota screenshot), **repo zip** (fresh `git archive` so :8001/:8002 code = disk).
- [ ] Hotspot creds card (paper): SSID / password / phone PIN; test `curl` over hotspot once.
- [ ] Token line: cloud/API bearer token in password manager + Inspector Server Settings
      (never pasted on slides); note `MCP_INSPECTOR_API_TOKEN`, fallback `CLIENT_PORT` if 6274 taken.
- [ ] Offline bundle on laptop: this file, `docs/CLIENTS.md`, `demo/SHOTLIST.md`,
      `requirements.txt`, ngrok config; `pip freeze` shows `fastapi uvicorn`.

## 2. T-60min ritual (venue, in order — ~10 min)

1. **Kill stale.** The :8001/:8002 processes predate the L1 route (13-prewarm §5.1) —
   prewarm alone cannot add it. Kill ALL python/uvicorn windows, then boot from disk:
   `run.bat` (frozen ports HR 8001 / IT 8002 — never 8008/8009/8000).
2. **Boot.** Two uvicorn windows up; expect cold boot ≈1.1s each (13-prewarm §6).
3. **Seed.** `POST /hr/demo/seed` + `POST /it/demo/seed` (header `x-demo-confirm: yes`);
   confirm `seeded_at` via Status button or `/demo/status`.
4. **Health.** Git-bash only (prewarm is bash — 13-prewarm §5.2):
   `C:/Program\ Files/Git/bin/bash.exe ./scripts/prewarm.sh local` → **every line 200**.
   Tripwire: any candidates/breaches/openapi/docs probe >5s or non-200 = dead/stale service,
   not slowness — reboot, don't debug.
5. **Inspector.** `npx -y @modelcontextprotocol/inspector --cli … --method tools/list`
   → **13 baseline** (11 functional + 2 health; 12-demo-risk §2 surface budget).
   Drill discover once: rebuilt allowlist +L1 `GET /oncall-coverage` → **14, same server ID**,
   `it_oncall_coverage` present; then rebuild baseline → 13 for showtime
   (discover is the LIVE moment — `docs/CLIENTS.md` §1, SHOTLIST §4).
6. **Frontend.** Open `frontend.html`: queue loads, CAND-002 selected,
   `/it/oncall-coverage?team=support-night` → 200 (EMP-014 Kiran Desai).
7. **Video.** `demo/golden.mp4` (or USB copy) open, **paused at 0:00**;
   audit tail terminal + health terminals staged behind.
8. Say out loud: "Golden → Live → Local → Protocol → Lesson. We never go black."

## 3. Kill-network drill (rehearse twice, 15 min each — 12-demo-risk §8)

1. Start live demo. Teammate enables airplane mode / kills hotspot.
2. You reach P2 in <60s: `APP_MODE=local`, pre-pulled `demo-qwen-8k`, one tool call
   via Inspector `--cli` (stdio needs no browser network).
3. Pass: audience sees a tool result in <90s; `ollama ps` CONTEXT still 8192;
   no secrets on screen. Log: date, seconds-to-fallback, one-line fix.
4. Reset: restore net, `curl $API/health` to re-warm, note cold-start seconds.
5. Quota twin-drill: allowlist to 3 tools (or revoke key) → P3 in <60s:
   `tools/list` → allowed call (JSON `| jq .result`) → blocked call
   (clean `isError:true`, user-readable, no stack trace, `version` bump visible).

## 4. Fallback ladder (announce the level, never debug silently >20s)

| Level | Name | Trigger | 30s script |
|---|---|---|---|
| P0 | Pre-record | Anything dead, cold-start >20s | "Golden path recorded this morning — narrating live signals." Play `golden.mp4`. |
| P1 | Live | Happy path | Full story on :8001/:8002 + `/docs` Try-it-out. |
| P2 | Local `--local` | Net death, 5xx, quota 429 | "Venue Wi-Fi is doing venue things — flipping local, same tools." |
| P3 | Inspector/curl proof | Hallucination, arg drift, stale cache | "Dropping below the model — proving the server." `tools/list` → valid call → invalid call. |
| P4 | Narrative flip | Total loss | "The failure *is* the lesson: cold starts, silent truncation, stale surfaces." Whiteboard 3 traps. |

Escalation: P1 → fail <15s → P0 plays while P2 attempted in background → P3 over P0 → P4.

## 5. Cue card (tape to laptop)

```bash
HEALTH: curl.exe -s http://localhost:8001/health; curl.exe -s http://localhost:8002/health
LIST:   npx -y @modelcontextprotocol/inspector --cli python synapse_auto_server.py --method tools/list   # 13 → 14 post-discover
CALL:   ... --method tools/call --tool-name T --tool-arg k=v --format json | jq .result
PS:     ollama ps  (CONTEXT must be 8192, GPU)
VIDEO:  demo/golden.mp4 (paused 0:00)  |  HOTSPOT: <ssid>/<pass>  |  TOKEN in keychain, not slides
SAY:    "Golden → Live → Local → Protocol → Lesson. We never go black."
```

Prewarm fix log 2026-11-24: ollama probe read `OLLAMA_HOST=0.0.0.0` (bind addr) as a URL
→ false 000 "not running". `scripts/prewarm.sh` now normalizes to `http://127.0.0.1:11434`
— verified all-200. Run prewarm under Git-bash on Windows (`where bash` is empty in PowerShell).
