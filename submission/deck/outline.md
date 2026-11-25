# Deck outline — 8 slides (5-min pitch)

> Build in Canva (Hackathon Pitch template) / Google Slides. 1 idea/slide, 24pt+, dark-on-light, export PDF backup. QR scannable.

1. **Title** — Onboard Copilot · HR + IT copilot that closes onboarding exceptions live · Track 3 · QR (live + repo) + tagline "8 tools deleted. 1 decision."
2. **Problem** — Priya starts Monday; SSO/laptop/payroll/training in 5 systems; 11 tickets, 4 owners, 0 accountability · 1 stat (Day-1 blockers hit every company) + pain quote
3. **Solution** — Exception queue → staged preview with citations → `APPROVE <hash>` → flip + receipt → audit row · 3 bullets + screenshot (preview pane)
4. **Demo** — QR + 3 steps (Stage → Approve → Activate) + live-discover beat (`GET /it/oncall-coverage` → `synapse build --discover` → `it_oncall_coverage` → reroute breaching tickets)
5. **Architecture** — mermaid PNG (two FastAPIs → two MCP servers → one agent) + 3-line flow (read live → stage draft → approve + audit) · same server ID, no client re-config
6. **Benchmarks + quota-proof** — 1 table (cold start, p50/p95, TTFT, VRAM) + ₹0 badge + guarded 97.5% acc / 96.8% block / 0% FP (40 cases: 39/40 acc, 30/31 block) · guards: cache + rate limit + cached-JSON fallback
7. **Roadmap** — Now (freeze D12, 10 dry runs) / Next (Frappe HRMS backend, second breach) / Later (payroll rails read-only, multi-tenant isolation)
8. **Team + Ask** — Solo builder (APIs + Synapse + safety/evals + demo) + contact + repo link + CTA "Try it live"

Design: screenshots 150% zoom; audit + `synapse build` output on slides 4–6; PDF backup at `deck/pitch.pdf` (built 2026-11-24 via `deck/build_pdf.py` from this outline) + single-file fallback `deck/pitch.html`.
