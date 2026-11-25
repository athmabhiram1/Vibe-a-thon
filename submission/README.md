# Onboard Copilot — HR Directory + IT Ticketing (Track 3)

![build](https://img.shields.io/badge/build-passing-brightgreen)
![track](https://img.shields.io/badge/track-T3_copilot_across_two_systems-blue)
![synapse](https://img.shields.io/badge/synapse-auto_%2B_discover-purple)
![cost](https://img.shields.io/badge/cost-%E2%82%B90_free_tier-success)
![evals](https://img.shields.io/badge/guarded-97.5%25_acc_(39%2F40)_0%25_FP_MOCK-informational)

> 30-sec pitch: New-hire Day-1 readiness is blocked by join-dependent steps scattered across HRIS, payroll, and IT inventory. Onboard Copilot stages everything as reversible drafts with citations, then activates on one explicit `APPROVE <hash>` — closing onboarding exceptions live across two systems.

## Demo (2 links max)

- 🎥 Video (60–90s): `[UPLOAD PENDING — record per PITCH.md, save USB copy to demo/golden.mp4, upload unlisted, paste URL here]`
  - Upload checklist: 1) rehearse PITCH.md verbatim ≤90s · 2) screen-record 1080p30 + mic · 3) export `captions/demo.srt` (already drafted) in CapCut → 4) YouTube upload **unlisted** + auto-translate → 5) paste URL here + QR on deck slide 4
- 🚀 Live: `http://localhost:8001/docs` + `http://localhost:8002/docs` | 📦 Repo: `[UPLOAD PENDING — create repo, push, paste URL here]`
  - Publish checklist: 1) `gh repo create VIBE_CODE --public --source .` (current `origin` points at unrelated `pcb_designing.git` — do NOT push there) · 2) `git push -u origin main` · 3) paste URL here + replace `<PASTE-REPO-URL-HERE>` below

## What it does (≤6 bullets)

- Exception queue → staged preview with citations → `APPROVE <hash>` → flip + receipt → audit row
- Joins `assignee_email ↔ email` and `ticket.created_at ↔ shift_calendar` across HR (8001) + IT (8002)
- Live moment: add `GET /it/oncall-coverage` (L1) on stage → `synapse build --discover` (expanded `--endpoints` allowlist) → agent re-routes breaching tickets (same server ID, no client re-config)
- Cite-Before-Act safety: CITE preview+hash → CHECK scope/hash/approval → ACT → RECORD audit line (allow AND deny)
- Guarded 30 BLOCK + 1 WARN + 9 ALLOW = 97.5% acc (39/40 strict) / 0% FP @ ~11ms MOCK latency (simulated, not measured) (`eval/run.py`, 40 cases); M05 WARN-as-designed - citation-flag means block-intent (flag + require real doc link); baseline 29.0% block (weak-by-design single-signal comparator, not 0% tautology)
- Quota-proof: single-process golden path, SQLite WAL, `--local` fallback, cached-JSON P3

## How it works (3 steps + diagram link)

1. **Stage** — agent reads live HR/IT state (offer, BG-check, inventory holds, shift calendar) → reversible draft + `preview_hash`
2. **Approve** — human replies `APPROVE <hash>` (mutating = 1 approval, destructive = double; unknown = deny-closed)
3. **Activate + audit** — `staged → active` flip in one TX + hash-chained `audit.jsonl` receipt

See [ARCHITECTURE.md](./ARCHITECTURE.md).

## Tech stack table

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (`hr-directory` :8001, `ticketing-sla` :8002) | Best static detection + `operation_id` control + `/docs` rerun |
| MCP | FastMCP 4.2.4 (13 hand-curated `@mcp.tool`s baseline, 14 post-discover) + Synapse Auto hosted | `fastapi_mcp` stale ~16mo; `on_duplicate_tools=error`, CI asserts count == 13 baseline (11 functional; 14/12 post-discover with L1) |
| DB | SQLite WAL golden (`schema.sql`, 79 rows, `VACUUM INTO` snapshot) | Offline, zero cold start; Postgres/Neon = opt-in backup only |
| Models | Hosted frontier (judged) → qwen3:4b-8k agent + qwen2.5-coder:7b-8k codegen → cached-JSON | gemma3:4b = no native tools (HTTP 400); llama3.2:3b emergency-only |
| Clients | MCP Inspector Web UI live (Reconnect re-lists in 3s) | Cursor/Desktop cache tool lists till restart — backup proof only |
| Deploy | localhost + ngrok primary; Fly/Render Free backup | Zero cold start, survives Wi-Fi death |

## Run locally (5 cmds, fresh clone, Windows, <60s warm; ~2 min cold (venv+pip))

> `run.bat`'s header says "3 cmds" — that is the boot subset (clone + install + run). The canonical
> quickstart is **5 cmds**: boot + open UI + seed-gate. `requirements.txt` exists at repo root.

```bat
git clone <PASTE-REPO-URL-HERE> ^&^& cd VIBE_CODE   :: see publish checklist above
pip install -r requirements.txt
run.bat                                            :: boots HR :8001 + IT :8002, probes both
start frontend.html                                :: single-file demo UI (double-click works too)
python seed/validate.py                            :: expect "0 failure(s)"
```

Seed/reset: `POST /demo/seed` (headers `x-demo-confirm: yes`, `ALLOW_DEMO_SEED=true`) → `POST /demo/reset` → `GET /demo/status`. Ports frozen: hr 8001, it 8002, ollama 11434.

## Benchmarks → [BENCHMARKS.md](./BENCHMARKS.md) | Quota-proof → [LIMITS.md](./LIMITS.md)

## Docs

- Architecture: [ARCHITECTURE.md](./ARCHITECTURE.md) · Pitch script: [PITCH.md](./PITCH.md) · Deck: [deck/outline.md](./deck/outline.md) · Captions: [captions/demo.srt](./captions/demo.srt)
- Quota log: [../evidence/quota-log.md](../evidence/quota-log.md)

## Team + roles | License (MIT)

- Solo builder — HR/IT APIs + Synapse + safety/evals + demo/video
- License: MIT
