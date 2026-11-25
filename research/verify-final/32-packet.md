# 32 — Packet + Form Readiness Audit (2026-11-25, read-only)

Scope: README render, server IDs, `submission/` completeness, TODO/WIP markers, eval score line, quota-proof freshness, repo public status. No files edited.

## 1. README renders? YES (with stale publish notes)

- Root `README.md` (62 lines) + `submission/README.md` (71 lines): open clean, headers/badges/tables/code fences intact. Relative links resolve (`submission/*`, `../evidence/quota-log.md`, `assets/*` all exist).
- BUT both carry stale publish language: root `:25-27,50-51,61-62` still says "origin → unrelated `pcb_designing.git`, do NOT push" and `[UPLOAD PENDING]`; submission `:13,15-16,52` same. As of today `git remote -v` = `https://github.com/athmabhiram1/Vibe-a-thon.git` (not pcb_designing) — note is outdated and must be rewritten at publish.

## 2. Server IDs present? YES

- `.synapse/config.json`: `hr-api 6269969f-3f80-4a9f-a6e1-43237197dc42` (created 09:36, updated 09:41), `it-api 5fe96a56-ccb4-4483-a7e2-5a9cd2588b15`. Same-ID rebuilds ×3 logged in `evidence/quota-log.md` (2/10 servers, 775/100.0K lines, 99.2K left). No new build needed; do NOT `--new`.

## 3. `submission/` complete? STRUCTURALLY COMPLETE, content-pending uploads

| File | Status |
|---|---|
| `README.md` | Opens; 2× `[UPLOAD PENDING]` (video, repo) + 1× `<PASTE-REPO-URL-HERE>` |
| `ARCHITECTURE.md` | Opens; mermaid valid; PNG fallback line now TRUE — `assets/arch.png` EXISTS (closes 22-packet-audit gap) |
| `BENCHMARKS.md` | Opens; measured rows (cold 1.3s, p50 10.6/p95 11.6ms, seed 34.1ms, reset 14.4ms, TTFT-local 0.24s qwen3:8b-substitute, payload 3.3KB, eval 97.5%/0% FP MOCK) + 7× `[VENUE-UNMEASURED]` (network, TTFT-hosted, AI cache/fresh, discover median ×5, VRAM target pair, Lighthouse, ngrok) |
| `LIMITS.md` | Opens; Synapse row now carries live numbers (2/10, 775/100K, quota-log + txt proof). Still `[UNMEASURED]` ×3: `:8` ngrok count, `:10` AI dashboard, `:18` CACHE_TTL |
| `PITCH.md` | Opens; 6 beats ≈61s; receipt convention FIXED — now `EMP-021` (closes v3 residual) |
| `captions/demo.srt` | Valid SRT, 6 cues, 00:00–01:15, mirrors PITCH, `EMP-021` consistent |
| `deck/pitch.pdf` (10,897 B, %PDF-1.4, 8 slides) + `deck/pitch.html` + `deck/outline.md` + `deck/build_pdf.py` | All present |
| `assets/README.md`, `assets/render-pngs.py`, `assets/arch.png` | Present |
| `assets/quota-proof/` | `synapse-info.txt` + `ollama-ps.txt` + `ollama-ps.png` + `README.md` present. MISSING: `synapse-info.png`, `ngrok.png`, `ai-dashboard.png`. `ollama-ps.png` is a monospaced rendering of the txt, not an OS screengrab (disclosed in txt header) |

## 4. TODO / UPLOAD PENDING / WIP markers

- `submission/` grep: 14 hits, zero bare `TODO`/`FIXME`/`WIP`/`TBD`. All remaining markers are intentional, user-owned fills: 2× `[UPLOAD PENDING]` + 1× `<PASTE-REPO-URL-HERE>` (README), 7× `[VENUE-UNMEASURED]` (BENCHMARKS), 3× `[UNMEASURED]` (LIMITS). No stale dev TODOs.
- `R-009x` residual GONE (PITCH + srt both `EMP-021`). `96.8%` block figure now consistent (outline `:10` + deck slide 6 match README badge 97.5% acc / 96.8% block).

## 5. Eval score line present? YES

- Badge `submission/README.md:7` + body `:25` + `BENCHMARKS.md:7,21`: **guarded 97.5% acc (39/40 strict) / 96.8% block / 0% FP @ ~11ms MOCK (simulated, disclosed)**; baseline 29.0% block (weak-by-design comparator, disclosed); M05 WARN-as-designed annotated. `eval/scorecard.csv` (40 rows) + `eval/run.py` + `eval/live_scorecard.csv` (5/5 live, measured latencies) all on disk.

## 6. Quota screenshot fresh? PARTIAL

- Text captures dated 2026-11-24 (yesterday — fresh): `synapse-info.txt` (2/10, 775/100K, key redacted, matches quota-log), `ollama-ps.txt` (qwen2.5-coder:7b 4.7GB pulled, ps empty at capture). `ollama-ps.png` = rendering, not screengrab.
- No true OS screenshots anywhere; freeze-day PNGs (synapse info, ngrok session, AI dashboard, all showing ₹0/$0) still owed.

## 7. Repo public? YES — but stale + unpushed delta

- `https://github.com/athmabhiram1/Vibe-a-thon` fetches public (title + full README render). Name mismatch: remote is `Vibe-a-thon`, local dir `VIBE_CODE` — harmless but use exact URL in forms.
- GitHub README still shows `[UPLOAD PENDING]` + `<PASTE-REPO-URL-HERE>` → last push predates publish fills. Local `git status --short`: `M eval/scorecard.csv` (dirty) + `?? .vscode/` (untracked) on top of `2973b0f v1.0-judging`. Must commit + push before submitting the URL.

## Gaps

### MUST-FIX-BEFORE-SUBMIT
1. **Video + `demo/golden.mp4` missing** — `demo/` = `SHOTLIST.md` only, zero `*.mp4` repo-wide; both READMEs `[UPLOAD PENDING]`. Form link empty = rejection risk.
2. **Repo URL placeholders** — replace `<PASTE-REPO-URL-HERE>` (both READMEs) + 2× `[UPLOAD PENDING]` with `https://github.com/athmabhiram1/Vibe-a-thon` (+ YouTube URL); rewrite stale `pcb_designing` warning; commit dirty `scorecard.csv`, push, verify GitHub README renders with real links.
3. **Quota-proof PNGs** — add `synapse-info.png`, `ngrok.png`, `ai-dashboard.png` (₹0/$0 visible) to `assets/quota-proof/`; replace rendered `ollama-ps.png` with real `ollama ps` screengrab if the form requires pixels.
4. **Freeze-day numbers** — fill or explicitly N/A: `LIMITS.md:8,10,18` (ngrok count, AI dashboard, CACHE_TTL seconds) + `BENCHMARKS.md` 7× VENUE rows (speedtest, TTFT-hosted, AI cache/fresh, discover median ×5 — quota-gated, venue only —, `ollama pull qwen3:4b + qwen2.5-coder:7b && ollama ps`, Lighthouse). Unexplained `[UNMEASURED]` in a judged packet reads as incomplete.
5. **Dirty tree** — commit `eval/scorecard.csv`, drop/ignore `.vscode/`; submit from a clean `git status`.

### NICE (venue-day / cosmetic)
- Reconcile "5 cmds vs run.bat 3 cmds" wording (already footnoted; one-line unify).
- Paste deck QR codes on slides 1/4/8 at freeze; second-device playback + USB ×2 + hotspot drill.
- Venue reboot from disk + `GET /it/oncall-coverage` 200 assert + serialize seed/reset (stale-proc hazard per 17-resignoff).
- Rotate `SYNAPSE_API_KEY` if `.env` was ever staged; never publish `.env`.

## Verdict
Packet is **structurally complete and render-clean**; eval line, server IDs, arch.png, PITCH/EMP-021 fixes all closed since v3. Ship = 1 recording session + 1 publish/commit/push pass + freeze-day PNGs/numbers. Not submittable until MUST 1–2 (video, URLs+push) are done.
