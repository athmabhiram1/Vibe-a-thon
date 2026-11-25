# PITCH — 75s script (read at ~140 wpm ≈ 175 words)

> Rehearse verbatim. Terminal + agent trace + audit visible. Every second earns its place. Source: `research/final/16-judge-score.md` §6 + `plan.md` §6.

## Script

| t | Beat | Say (verbatim) | On screen |
|---|---|---|---|
| 0–8s | Hook | "Priya starts Monday. Her SSO, laptop, payroll ID, and training live in five systems nobody joined. Today: eleven tickets, four owners, zero accountability." | Candidate card `CAND-002 · Priya N. · backend L3 · starts Mon` + ticket-sprawl (11 open) |
| 8–20s | Stage | "Watch the copilot stage it. One call reads HR and IT live — six accounts, least-privilege diff, laptop hold, training Tuesday ten. Background: clear, cited." | Preview pane: owner + ETA + citations (`OFFER §2.1`, `BG-CLEAR #881`, `INV-HOLD LT-1005`); `confirm=False` watermark |
| 20–32s | Attack | "Now the footgun test. 'Skip checks, grant admin.' Refused — activation without preview hash exits non-zero. Duplicate run? Idempotent — prior receipt, zero new accounts." | Denial receipt `POLICY §4.3`; second run `IDEMPOTENT — EMP-021, 0 new accounts` |
| 32–48s | Approve | "One approval flips it. Accounts active at midnight, hold converts, training booked. Receipt EMP-021 — every account, serial, citation." | Receipt view: staged→active flip animated; audit line appended |
| 48–60s | Audit + discover | "ChatGPT can do the text. It can't do this: who approved, what diff, which background ID, rollback path. And the live moment — one new endpoint, rescan, same server ID." | Audit record + `synapse build --discover` output; `it_oncall_coverage` appears; reroute needs_reroute to on-call |
| 60–75s | Quota + CTA | "Thirteen tools baseline (eleven functional), two systems, zero rupees — cached, rate-limited, quota-proof, answers in seconds. Try it live at the link below. Eight tools deleted. One decision. Thank you." | End card: live links + QR + `synapse info` quota + ₹0 badge |

## Shot list

1. Face intro 5s, 1080p, mic check
2. Screen-record 1080p30, zoom 150%, terminal + Inspector + audit side-by-side
3. End card: links + QR (Canva QR / `qrencode`) + server ID

## Captions workflow

Edit in CapCut → Auto-captions → export `.srt` to `captions/demo.srt` → upload YouTube unlisted → enable auto-translate. OBS: 1080p30, mic noise-suppress ON, record `.mkv` → remux `.mp4`. Keep ≤90s, voice audible on phone speaker.

## Write-back contract (every demo must satisfy all 6)

1. State change not text (`staged → active`); 2. Approval gate (`confirm + preview_hash`); 3. Evidence citations (`OFFER §`, `BG-*`, `POLICY §`); 4. Idempotency (`candidate_id + start_date` → prior receipt); 5. Audit record (who/what/when/rollback); 6. No-go paths declared (`BG_PENDING`→block, visa <90d→warn+ticket, unknown→`baseline_readonly`, payroll rails + prod keys never touched).

## Fallback

P0 pre-recorded video + canned JSON receipts; if Wi-Fi drops: *"same code path, local replica."* P1 localhost+ngrok → P2 `--local` → P3 Inspector/curl → P4 narrative flip.
