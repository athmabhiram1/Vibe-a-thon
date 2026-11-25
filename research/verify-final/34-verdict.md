# 34 — FINAL RECORD VERDICT (brutal synthesizer, 2026-11-25)

**Evidence read:** 18-greenpass, 19-frontend-rescore, 20-public-url, 22-packet-audit, 23-fresh-drill, 24-signoff-v3, 10-verdict, 16-signoff, 17-resignoff, reconcile/RECONCILE.md.
**Files 25–33: ABSENT — marked UNVERIFIED.** No evidence invented. Fallback used: 24-signoff-v3 (GO-WITH-FIXES) + 18-greenpass (8/8 PASS) + 23-drill timings. Anything claiming 25–33 proved something is lying.

## Verdict: RECORD-WITH-CAUTION

Not clean RECORD (packet has holes, public-URL BLOCKED, cold-claim false). Not DO-NOT-RECORD (core 4 beats are live: real EMP-021 mint, real ledger/audit, 13→14 discover ×3 same-ID, 3-breach board, 18/20 frontend). Record now, but stay inside the cage below. One deviation = failed take, re-shoot, no heroics.

## What is GREEN (camera-safe)
- HR :8001 + IT :8002 boot from disk, `{"ok":true}` ×2, seed v14 20/20/20/20/8/6/5, `validate --db` 0 failures.
- H5 `GET /hr/oncall?team=support-night` → EMP-014 Kiran Desai 200. L1 `GET /it/oncall-coverage?team=support-night` → breach_count=3 [T-5001,T-5019,T-5002], owned vs needs_reroute split correct.
- `eval/run.py` 96.8% block / 0% FP label + spoken "regex-over-JSON MOCK + 11ms simulated, 5 live measured cases pass" + pytest 11 passed + `probe_live.py` ALL PASSED.
- Frontend 42KB wired: queue CAND-002 Priya Nair, 3-breach literal path, approve-gated writes, CORS `*` verified.

## DO NOT SHOW ON CAMERA (exact avoid-list)
1. **Never hit unprefixed `/demo/status`** — 404 by design. Only `/hr/demo/*`, `/it/demo/*`.
2. **Never say "<60s fresh clone."** Measured cold = 109s (venv 21.5s + pip 79.5s). Say: "<60s warm, ~2 min cold first install."
3. **Never utter dead IDs/numbers:** CAND-1147, LT-4420, R-0091/R-0092, 10→11, `srv_xxxx`, `96.8%` headline, TODO/UPLOAD PENDING/PASTE-REPO-URL, `pcb_designing.git` origin. Canonical only: CAND-002 / LT-1005 / EMP-021 / 13→14 / 97.5% MOCK.
4. **Never click I3 `it_create_ticket` in frontend** — registered, never called (dead button hunt). Never claim TOOLS pane is live-fetched — it is static-const + seen-markers. L1 moment lives in terminal/Inspector, not a frontend button.
5. **Never touch ngrok / public URL / `synapse --new` live.** 20-public-url = BLOCKED (no authtoken, ERR_NGROK_4018). Stay localhost. Never paste `.env` / SYNAPSE_API_KEY. Never run seed/reset concurrently (serialize). Never run extra `--discover` (quota 2/10, 775/100K — rehearsed ×3 is enough).
6. **Never defend M05, never promise `available` laptop.** M05 WARN = block-intent by design; laptop assign uses monitor stand-in — stage it, don't explain it.

## Single 5-command pre-record ritual (all must PASS, else no record)
```powershell
python seed/validate.py --db seed/demo.db
curl.exe -s http://127.0.0.1:8001/health
curl.exe -s http://127.0.0.1:8002/health
curl.exe -s "http://127.0.0.1:8002/it/oncall-coverage?team=support-night"
python probe_live.py
```
Expect: `0 failure(s)` / `{"ok":true}` / `{"ok":true}` / `EMP-014 + breach_count 3` / `ALL LIVE-ENDPOINT CHECKS PASSED`. Venue-day prepend: kill stale :8001/:8002, boot both uvicorn from disk, sleep 6s, then the 5 above.

## Abort-to-P0 rule
**Any stall >20s = stop talking, play video.** Cut to `demo/golden.mp4` (USB ×2 + second-device copy on venue Wi-Fi). Never debug live, never `pip install`, never re-seed, never re-discover on camera. Say: "Backup playback — live backend stays up for Q&A," then continue cue-card. Two stalls in one take = scrap take, reboot, re-ritual.

## Post-record close-out (not camera work, ~70 min)
LIMITS numbers paste (5) + arch.png render (15) + PITCH/srt EMP-021 sweep (10) + README links at publish (5) + quota PNGs at freeze (20) + cold-claim doc fix (5) + prewarm twin (10). Video + YouTube unlisted + captions = ship.
