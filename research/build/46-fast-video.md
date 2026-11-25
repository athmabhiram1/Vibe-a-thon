# 46 — Fast Video: 60s Demo Script (Hook → Stage → Refusal → Approve → Audit)

> One-take 60s (extends to 90s with buffer). Single screen-record, no editing except captions. If backend dies mid-take, paste fallback JSON (§6) and keep talking.

Source: `build/18-step-seed.md` (seed/reset), `final/14-seed-data.md v14` · Seed: 79 rows · `seeded_at=2026-11-23T00:00:00Z`

---

## 1. Runtime Map (60s hard, 90s max)

| Block | Time | Seconds | Goal |
|---|---|---|---|
| Hook | 0:00–0:08 | 8s | Problem + promise |
| Stage | 0:08–0:20 | 12s | Seed + stage risky action |
| Refusal | 0:20–0:32 | 12s | Policy blocks double-hold |
| Approve | 0:32–0:48 | 16s | Manager approves clean request |
| Audit | 0:48–1:00 | 12s | Immutable log + CTA |
| Buffer | 1:00–1:30 | +30s | Only if typing lags; cut in editor |

Target WPM: 140–150. Total script ≈ 145 words. Do NOT ad-lib.

## 2. Voiceover + Captions (word-for-word)

Burn captions in, plus upload `.srt`. Format: `MM:SS → TEXT (≤42 chars/line, 2 lines max)`.

```
00:00 HOOK
VO: "Every demo breaks on seed. Ours reloads in one second — then blocks the bad approval automatically."
CAPTION: Every demo breaks on seed. / Ours reloads in 1 second.

00:08 STAGE
VO: "Fresh database, seventy-nine rows. I stage an equipment hold on LT-1005, plus three SLA-breached tickets."
CAPTION: Fresh DB · 79 rows / Stage hold on LT-1005

00:20 REFUSAL
VO: "Second hold on the same laptop? Refused. Policy double-hold fires, nothing writes, four-twenty explained."
CAPTION: ❌ Double-hold refused / Policy: double-hold · 409 conflict

00:32 APPROVE
VO: "Clean request goes to the manager. One click, approve — ticket TCK-014 assigned, shift covered, visa flag intact."
CAPTION: ✅ Manager approves TCK-014 / Assigned + shift covered

00:48 AUDIT
VO: "Every step is logged — who, what, when. Seed, refuse, approve. Replayable in under sixty seconds. Try /demo/seed yourself."
CAPTION: Audit: who · what · when / Try POST /demo/seed ↓
```

`.srt` snippet (copy to `demo.srt`):

```srt
1
00:00:00,000 --> 00:00:08,000
Every demo breaks on seed.
Ours reloads in 1 second.

2
00:00:08,000 --> 00:00:20,000
Fresh DB, 79 rows.
Stage hold on LT-1005.

3
00:00:20,000 --> 00:00:32,000
❌ Double-hold refused.
Policy: double-hold, 409 conflict.

4
00:00:32,000 --> 00:00:48,000
✅ Manager approves TCK-014.
Assigned, shift covered.

5
00:00:48,000 --> 00:01:00,000
Audit: who, what, when.
Try POST /demo/seed.
```

## 3. Shot List (single window, 1920×1080, 60fps)

| # | Time | Shot | On screen | Action |
|---|---|---|---|---|
| 1 | 0:00–0:08 | Face + title card | OBS: webcam bottom-right 320px, title `Seed in 1s. Policy blocks bad approvals.` | Read hook, cut webcam at 0:08 |
| 2 | 0:08–0:20 | Full terminal | `curl POST /demo/seed` → `{"ok":true,…}` + `POST /demo/stage` | Type cmd 1–2, highlight `duration_ms: 1420` |
| 3 | 0:20–0:32 | Split: terminal left / UI right | Second `POST /holds {asset: LT-1005}` → `409 {error: double_hold}` + red toast | Show refusal, hover policy line |
| 4 | 0:32–0:48 | Browser UI full | Approvals queue → click `Approve TCK-014` → green `200 {ok:true}` | Click once, show assigned shift |
| 5 | 0:48–1:00 | Terminal + lower-third | `GET /audit?limit=5` → 3 rows + CTA link | Scroll log, end on CTA 3s hold |

No zoom. Mouse: slow, click rings on. Hide bookmarks, notifications off, `code --new-window`.

## 4. Font Sizes (readable at 720p / phone)

- Burned captions: **Inter Bold 48px**, white `#FFF` + black stroke 4px + bg `rgba(0,0,0,0.65)`, bottom-center, safe margin 80px.
- Terminal: **JetBrains Mono 22–24pt**, `140×36` window, theme Dracula / black `#0B0E14`, font scale `1.25x` in VS Code (`"terminal.integrated.fontSize": 22`).
- Lower-thirds / callouts: **Inter SemiBold 32px**, pill `rounded 12px`, red `#FF3B30` for refusal, green `#30D158` for approve.
- Title card: **64px Bold**, subtitle 28px Regular. Export: H.264, 1080p, 12 Mbps, AAC 192k.

CapCut/Premiere preset: `Caption → Style → Bold Outline → Size 48 → Stroke 4`.

## 5. Terminal Commands On Screen (type exactly this)

Pre-run `export BASE=localhost:8001` before recording. Keep each command on ONE line.

```bash
# [0:08 STAGE] — seed + status (expect duration_ms <5000)
curl -X POST $BASE/demo/seed -H 'x-demo-confirm: yes' -H 'Content-Type: application/json' -d '{"version":"v14"}'
# expect: {"ok":true,"seed_version":"v14","counts":{"candidates":20,"employees":20,"equipment":20,"tickets":20},"duration_ms":1420}

# [0:12 STAGE] — stage hold (first hold succeeds)
curl -X POST $BASE/demo/stage -H 'Content-Type: application/json' -d '{"asset_tag":"LT-1005","by":"mgr-02"}'
# expect: {"ok":true,"hold_id":"H-101","asset_tag":"LT-1005"}

# [0:20 REFUSAL] — double-hold (must 409, copy this output to camera)
curl -X POST $BASE/holds -H 'Content-Type: application/json' -d '{"asset_tag":"LT-1005","by":"mgr-07"}'
# expect: 409 {"ok":false,"error":"double_hold","policy":"equipment.no_double_hold","asset_tag":"LT-1005"}

# [0:32 APPROVE] — approve clean ticket
curl -X POST $BASE/approvals/TCK-014/approve -H 'Content-Type: application/json' -d '{"approver":"mgr-02"}'
# expect: {"ok":true,"ticket":"TCK-014","assignee":"EMP-011","shift_covered":true}

# [0:48 AUDIT] — proof log (end frame, leave on screen 3s)
curl "$BASE/audit?limit=5"
# expect: 3 rows: seed → refuse → approve with actor + timestamp
```

Pre-warm: run `/demo/reset` once so second take is instant (`duration_ms ~600`).

## 6. Fallback Canned JSON (backend down → paste, keep talking)

Save as `fallback/*.json`, `cat` them on camera if API fails. Say: "Live API is napping — here's the exact payload."

`fallback/seed.json`:
```json
{"ok":true,"seed_version":"v14","counts":{"candidates":20,"employees":20,"equipment":20,"tickets":20,"shifts":8,"subscriptions":6,"api_keys":5},"duration_ms":1420,"seeded_at":"2026-11-23T00:00:00Z"}
```

`fallback/refuse.json`:
```json
{"ok":false,"error":"double_hold","policy":"equipment.no_double_hold","asset_tag":"LT-1005","hint":"asset already on_hold by H-101"}
```

`fallback/approve.json`:
```json
{"ok":true,"ticket":"TCK-014","assignee":"EMP-011","shift_covered":true,"approver":"mgr-02","decided_at":"2026-11-23T00:01:12Z"}
```

`fallback/audit.json`:
```json
{"ok":true,"rows":[
  {"seq":1,"action":"seed","actor":"demo","at":"2026-11-23T00:00:00Z"},
  {"seq":2,"action":"hold.refused","actor":"mgr-07","at":"2026-11-23T00:00:41Z","reason":"double_hold"},
  {"seq":3,"action":"ticket.approved","actor":"mgr-02","at":"2026-11-23T00:01:12Z","ticket":"TCK-014"}
]}
```

Fallback stage direction: `cat fallback/refuse.json` fullscreen, point at `"error":"double_hold"`. Judges accept canned if narration matches timestamps.

## 7. Recording Checklist (5 min before)

- [ ] `ALLOW_DEMO_SEED=true`, `curl /demo/status` → `seeded:false` (so seed moment is real)
- [ ] Terminal cleared (`clear`), font 22pt, window 140×36, close secrets
- [ ] UI logged in as `mgr-02`, queue shows `TCK-014 pending`
- [ ] Phone timer visible; rehearse once at 150 WPM
- [ ] `ffmpeg -f avfoundation -i "1" -r 60 demo.mp4` or OBS Record; mic -12dB, no fan
- [ ] If any command >4s → abort take, `POST /demo/reset`, re-record (reset is 0.6s)

*60s cut · 145 words · cmds: seed → stage → 409 → approve → audit · fallback/ ready · captions 48px Bold.*
