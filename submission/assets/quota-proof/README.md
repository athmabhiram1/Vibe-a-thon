# `assets/quota-proof/` — checklist (updated 2026-11-24)

Billing target = ₹0 / $0. Every screenshot must visibly show ₹0 / $0 spend.

- `synapse-info.txt` — DONE (`synapse info` text capture 2026-11-24: 2/10 servers, 775/100.0K lines, key redacted; matches `../../evidence/quota-log.md` and `LIMITS.md`). A `.png` screengrab was never taken — this redacted transcript is the source of truth.
- `ollama-ps.txt` + `ollama-ps.png` — DONE 2026-11-24 (raw `ollama ps`/`ollama list` text + monospaced rendering of that exact text; `qwen2.5-coder:7b` 4.7 GB pulled, nothing resident; local = ₹0).
- `ngrok.png` — USER-OWNED freeze-day shot (active tunnel session, free tier). [pending]
- `fly.png` — only if the cloud backup is actually deployed (0 hrs used during build). [pending — only if deployed]
- `ai-dashboard.png` — USER-OWNED freeze-day shot (hosted-frontier request count vs daily quota). [pending]

Status 2026-11-24: agent-capturable proofs done (`synapse-info.txt`, `ollama-ps.txt`/`.png`). `ngrok`/`ai-dashboard` shots stay user-owned — paste at freeze.
