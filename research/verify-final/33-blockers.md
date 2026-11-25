# 33 — Recording-Blocker Hunter: Top-6 ON-CAMERA Risks (Track 3 Demo)

**Date (UTC):** 2026-11-25 · **Role:** recording-blocker hunter, read-only (no code changes)
**Scope:** Track 3 demo = HR :8001 + IT :8002, 60 s script + H5/L1 discover beat, P0–P4 ladder.
**Sources read:** `plan.md` §6–§8 (60 s + fallback + gates/tripwires), `submission/ARCHITECTURE.md` (tool inventory 13→14, failure fallback), `reconcile/RECONCILE.md` (boot/validate/eval green), `research/verify-final/02-boot-endpoints.md`, `05-synapse.md`, `08-demo-critic.md` (K1–K7), `10-verdict.md`, `12-synapse-run.md` (8/8 builds, 4.8 s medians), `13-prewarm-clients.md` (§5 venue warnings), `23-fresh-drill.md` (109 s cold vs <60 s claim).

## Ladder reference (plan §6 / ARCHITECTURE §Failure fallback)

P0 pre-recorded `demo/golden.mp4` → P1 live (localhost:8001/:8002 + ngrok mirror) → P2 `--local` Ollama → P3 Inspector/curl last-good JSON → P4 narrative flip (talk over it, announce-don't-apologize, <90 s to fallback).

## Ranked top-6 (probability × impact)

### R1 — STALE SERVERS: L1 404 on camera (PROB HIGH × IMPACT FATAL = #1)
What: venue :8001/:8002 processes predate L1. Live `GET /it/oncall-coverage` returns FastAPI-level `{"detail":"Not Found"}` (route absent), not the router's designed `no on-call roster` 404. Proven in 13 §5.1 (stale 10 ops vs fresh-disk 11 ops; fresh :8101/:8102 serves L1 200 in 0.045 s). Any discover beat run against stale servers fails before Synapse is even involved.
Mitigation (5 min, night-before + T-10): `taskkill` both ports → boot from current disk → `curl /it/oncall-coverage?team=support-night` must be 200 (Kiran Desai EMP-014) + `curl /openapi.json` shows 9+11 ops → then run `prewarm` probes.
Fallback covering it: **P0** (play golden while rebooting) → else **P3** (curl fresh :8101/:8102 ALT-port proof) → **P4** narrate.

### R2 — DRIFT: breach count 3→14 + script-ID fiction (PROB HIGH × IMPACT HIGH = #2)
What (a): `GET /it/tickets/breaches` predicate is live wall-clock (`due_at < now`). 02 §6–7 measured **14 breached** vs script's "3 breached" (seed `due_at` 11-21…11-24 ages past SLA by showtime). 23 §34 claims "fixed/3" on ALT ports — contradiction itself is the risk: count depends on *when* you ask. Script line "11 tickets / 3 breached" reads as fiction if judge counts 14. What (b): 08 K5 — `03-demo-look.md` stages CAND-1147/LT-4420/T-551 while PITCH/srt/seed stage CAND-002/LT-1005/T-5001. Cross-check fails instantly.
Mitigation: re-seed T-30 min + freeze script to canonical IDs (CAND-002, LT-1005, T-5001/T-5002) + change line to "breaching tickets (live count)" or pin `now`; one grep pass over `03-demo-look.md`.
Fallback: **P4** (narrative flip: "live SLA clock — count grows by design") → **P0** (frozen-count video).

### R3 — STALE CACHE / SPINNER: discover beat dies in silence (PROB MED-HIGH × IMPACT HIGH = #3)
What: rebuilds reuse `surface_cache.json` until `--discover`; Inspector caches tool list till Disconnect→Reconnect (~3 s); CLI 0.1.9 only accepts prefix-stripped allowlists (`GET /candidates`, not `GET /hr/candidates` — 12 §2 fails hard otherwise). Miss any one → L1 never appears, presenter stares at spinner. Medians are kind (12 §4: ~4.8 s baseline + ~4.8 s discover, inside T3 90 s), but T3 is the highest structural risk per 10 §4 and `synapse logs` crashes on all 8 sessions (12 §5.1) so no on-stage log tail.
Mitigation: cue card with exact prefix-stripped 13→14 strings + rehearse Disconnect→Reconnect click path 3× + never type allowlist live (paste).
Fallback: **P3** (Inspector `tools/list` assert 13→14 from rehearsal screenshot) → **P2** (`--local`) → **P4**.

### R4 — NO P0 + AUDIO: failure ladder missing its bottom rung (PROB CERTAIN-if-live-fails × IMPACT FATAL = #4)
What: 08 K1 — recursive `*.mp4` search = zero hits, no `demo/` dir. P0 cue ("recorded this morning") is unperformable; any P1 fail drops straight to P4. Companion: T6 video >90 s/inaudible — `demo.srt` (6 cues, 0:00–1:15) exists but no mixed audio to check levels against; venue mic/speakers untested (08 K6).
Mitigation (tonight, 90 min): OBS 1080p30 3 takes → trim ≤90 s → `demo/golden.mp4` + desktop + USB×2 (tested in 2nd machine) + unlisted YouTube replacing `TODO_YOUTUBE_URL`; soundcheck speech + playback peaks at −12 dB; DND on, 18 pt font.
Fallback: this risk *is* the missing fallback — covers all others once fixed (**P0**). Until then, covering fallback is only **P4**.

### R5 — QUOTA / NETWORK: hosted build 429 or Wi-Fi death mid-discover (PROB MED × IMPACT HIGH = #5)
What: hosted quota was 0/10→2/10 servers, 775/100 K lines (12 §1; rebuilds incl. `--discover` cost 0 lines) — headroom fine *in lab*. Venue NAT/Wi-Fi death kills hosted auth + ngrok P1 equally (10 §F4, 08 K6: no hotspot proof). `evidence/quota-log.md` was all-TODO until 12 appended 8 rows — judge asks "₹0?" with no screenshot.
Mitigation: `synapse info` logged night-before + T-10 (freeze hosted if <40% per T8) + paired hotspot +200 MB free + `synapse model set ollama` + `qwen3:4b`/`qwen2.5-coder:7b` pre-pulled so P2 works offline.
Fallback: **P2** (`--local`, keyless, no quota) → **P1** (localhost survives Wi-Fi death; ngrok does not) → **P0**.

### R6 — 404 TYPO: `?team=` param + port confusion (PROB MED × IMPACT MED-HIGH = #6)
What: `GET /it/oncall-coverage?team=no-such-team` is 404 **by design** (13 §1 row 9, mirrors H5). One live-typed team name → red error pane on camera. Cheaper variant: stale-port curl (`:8000`/`:8008` ghosts in build-era docs — 10 F6) or `/health` vs `/hr/health` path slip.
Mitigation: cue card hardcodes `?team=support-night` only; never type ports/paths live — paste from printed block; pre-flight `grep` kills `:8000`/`:8008` refs.
Fallback: **P3** (retry canned curl in <15 s) → **P4** (talk over: "unknown-team 404 proves roster guard").

## Pre-camera checklist (tape to laptop lid)
1. Kill :8001/:8002 → boot disk → L1 200 + openapi 9+11. 2. Re-seed → breach count noted → script IDs canonical. 3. `synapse info` logged, quota photo. 4. Allowlist strings pasted, Reconnect rehearsed. 5. `demo/golden.mp4` on USB×2 + laptop, tested. 6. Hotspot paired, DND on, `?team=support-night` cue card out.
