# 22 — Packet completeness audit (2026-11-24, read-only)

Scope: `submission/` — every file opened and render-checked.

## Open/render check (all PASS to open)

| File | Status |
|---|---|
| `README.md` (68 lines) | Opens. 2× `[UPLOAD PENDING]` (video URL, repo URL) + 1× `<PASTE-REPO-URL-HERE>` — all user-owned uploads, no other TODOs |
| `ARCHITECTURE.md` (67 lines) | Opens. Mermaid `flowchart LR` syntactically valid (HR→MCP_HR, IT→MCP_IT→AGENT→HUMAN→LEDGER/DB + LIVE subgraph). PNG note present (line 24) but `assets/arch.png` NOT on disk |
| `BENCHMARKS.md` (38 lines) | Opens. Every `[VENUE-UNMEASURED]` has an exact fill command → criterion PASS. Measured: cold 1.3s, p50 10.6ms/p95 11.6ms, seed 34.1ms, reset 14.4ms, TTFT-local 0.24s (qwen3:8b substitute), payload 3.3KB, eval 97.5%/0% FP MOCK |
| `LIMITS.md` (30 lines) | Opens. Line 7 still carries `[AWAITING quota-lane synapse info]` — STALE: numbers already exist in `evidence/quota-log.md` (2/10, 775/100.0K) + `assets/quota-proof/synapse-info.txt` |
| `PITCH.md` (32 lines) | Opens. 6 beats ≈142 spoken words → ~61s @140wpm, inside 75s budget with headroom for pauses |
| `captions/demo.srt` (786 B, 6 cues) | Valid SRT, 00:00:00 → 00:01:15, mirrors PITCH beats verbatim |
| `deck/pitch.pdf` (10,897 B, %PDF-1.4) | Valid PDF header, built via `deck/build_pdf.py` (reportlab, 8 slides) |
| `deck/pitch.html` (6,479 B) | Valid single-file fallback, 8 slides + nav/print CSS |
| `deck/outline.md`, `deck/build_pdf.py` | Open, consistent with PDF/HTML (8 slides) |
| `assets/README.md`, `assets/quota-proof/README.md`, `assets/quota-proof/synapse-info.txt` | Open. txt capture matches quota-log (2/10, 775/100.0K, key redacted). PNG screenshots absent |

## Quota cross-check

`evidence/quota-log.md` (5 rows 2026-11-24): hr-api 0→1/10, it-api 1→2/10, discover R1–R3 2/10 stable, 775/100.0K lines throughout. `synapse-info.txt` matches. `LIMITS.md` line 7 does NOT yet carry the numbers inline (placeholder only) — 1-edit fix.

## Gaps

### SHIP-BLOCKER

1. **Video URL + `demo/golden.mp4`** — no recording exists (`Test-Path demo/golden.mp4` = False). Owner: **user-only** (rehearse PITCH.md, record 1080p30, CapCut SRT, YouTube unlisted + paste URL + QR).
2. **Repo URL** — `origin` points at unrelated `pcb_designing.git`; `<PASTE-REPO-URL-HERE>` unfilled. Owner: **user-only** (`gh repo create VIBE_CODE --public`, push, paste).
3. **`assets/arch.png` missing** — referenced by ARCHITECTURE.md + deck slide 5. Owner: **agent-fixable** (render mermaid via Mermaid Live/mermaid-cli → 2x PNG) or user via Excalidraw.
4. **`LIMITS.md` line 7 `[AWAITING]` placeholder** — numbers already measured. Owner: **agent-fixable** (paste `2/10 servers, 775/100.0K lines` + link proof).
5. **Quota-proof PNGs** — `synapse-info.png`, `ngrok.png`, `ollama-ps.png`, `ai-dashboard.png` absent (txt only). Owner: **mixed** — `ollama-ps` agent-fixable now (`ollama ps` screenshot); `ngrok`/`ai-dashboard`/`synapse-info.png` user-only at freeze (need live sessions).

### NICE (deferrable, venue/freeze-day)

- BENCHMARKS venue fills: TTFT-hosted, AI cached/fresh latency, `synapse build --discover` ×5 (freeze-gated, spends quota — do NOT run now), Lighthouse, venue speedtest, `ollama pull qwen3:4b + qwen2.5-coder:7b`. Owner: user-only at venue.
- `CACHE_TTL` confirm (LIMITS line 18 — no constant found). Owner: agent-fixable (grep + paste seconds).
- Deck QR paste (slides 1/4/8 say "paste at freeze"). Owner: user-only.
- Compose cold-start N/A (no Docker on bench) — correctly documented as opt-in backup; no action.

## Verdict

Packet is **structurally complete and render-clean**; no broken files. Ship requires 3 user-only uploads (video, repo, freeze screenshots) + 2 agent-fixable edits (LIMITS numbers, arch.png). Everything else is venue-day fill.
