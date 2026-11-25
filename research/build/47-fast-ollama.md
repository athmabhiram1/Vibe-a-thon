# 47 — Fast Ollama Stack (Local-First LLM Pins)

> Goal: sub-2s TTFT on laptop GPU/CPU with deterministic model pins, 8K context, no cloud fallback.

## 1. Model Pin Table

| Role | Model Pin | Digest / Tag | VRAM (Q4) | Use For |
|------|-----------|--------------|-----------|---------|
| **Primary** | `gemma3:4b` | `gemma3:4b-instruct-q4_K_M` | ~3.2 GB | chat, reasoning, RAG answer, default `opencode` model |
| **Fallback** | `llama3.2:3b` | `llama3.2:3b-instruct-q4_K_M` | ~2.0 GB | low-VRAM / CPU-only, fast triage, offline backup |
| **Codegen** | `qwen2.5-coder:7b` | `qwen2.5-coder:7b-instruct-q4_K_M` | ~4.7 GB | code completion, patch gen, test gen — never chat default |

Pin rule: always reference full tag (`:4b`, `:3b`, `:7b-instruct`), never `latest`.

```powershell
ollama pull gemma3:4b
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:7b
ollama list   # verify all three present
```

## 2. Modelfile — num_ctx 8192

Ollama default `num_ctx` is 4096 (older builds 2048) — too small for repo + tool traces. Create one override per model:

`Modelfile.gemma3-4b`:
```
FROM gemma3:4b
PARAMETER num_ctx 8192
PARAMETER temperature 0.2
PARAMETER num_predict 2048
PARAMETER repeat_penalty 1.1
```

`Modelfile.llama32-3b`:
```
FROM llama3.2:3b
PARAMETER num_ctx 8192
PARAMETER temperature 0.2
PARAMETER num_predict 1024
```

`Modelfile.qwen25coder-7b`:
```
FROM qwen2.5-coder:7b
PARAMETER num_ctx 8192
PARAMETER temperature 0.1
PARAMETER num_predict 4096
```

Build + verify:
```powershell
ollama create gemma3:4b-8k -f Modelfile.gemma3-4b
ollama create llama3.2:3b-8k -f Modelfile.llama32-3b
ollama create qwen25coder:7b-8k -f Modelfile.qwen25coder-7b
ollama show gemma3:4b-8k | Select-String -Pattern "num_ctx|Context"
```

> Use the `-8k` variants in `opencode.json` / agent config; keep base tags untouched for clean re-pull.

## 3. `ollama ps` CONTEXT Check

`ollama ps` shows live loaded models + context utilisation:

```powershell
ollama ps
# NAME               ID   SIZE   PROCESSOR   CONTEXT   UNTIL
# gemma3:4b-8k       abc  5.1GB  100% GPU    6144/8192  4 minutes from now
```

Interpretation:

| Column | Meaning | Red Flag |
|--------|---------|----------|
| `PROCESSOR` | `100% GPU` = fully offloaded; `CPU` = spilling to RAM | Anything `<80% GPU` on 7b = slow |
| `CONTEXT` | `used/total` tokens in KV cache | `8192/8192` = full → eviction / hallucination; restart or shorten prompt |
| `UNTIL` | keep-alive countdown | `Expired` + reload loop = thrash; raise `OLLAMA_KEEP_ALIVE` |

Diagnostic one-liner:
```powershell
ollama ps; ollama show --system gemma3:4b-8k | Select-Object -First 20
```

If CONTEXT stuck at 100%: `ollama stop gemma3:4b-8k` then re-run with shorter history, or split into summarize → answer passes.

## 4. TTFT Table (Time-To-First-Token)

Measured on RTX 4060 laptop / 16 GB RAM, Q4_K_M, `num_ctx 8192`, prompt ~1.5K tokens. Your numbers vary — re-measure with `time ollama run <model> "Say hi"`:

| Model | Cold Load | Warm TTFT | Tok/s | Notes |
|-------|-----------|-----------|-------|-------|
| `gemma3:4b-8k` | ~4–6 s | **0.6–1.2 s** | ~35–55 | default; best quality/speed balance |
| `llama3.2:3b-8k` | ~2–4 s | **0.3–0.7 s** | ~50–80 | fallback; fastest, weakest reasoning |
| `qwen2.5-coder:7b-8k` | ~6–10 s | **0.9–1.8 s** | ~25–40 | codegen only; slow on CPU |

Rules:
- Warm = model already in `ollama ps`. Keep warm with `OLLAMA_KEEP_ALIVE=30m`.
- Cold + `CPU only` ≈ 3–5× slower. If warm TTFT > 3 s on GPU, check VRAM contention (`nvidia-smi`).
- Route: chat → gemma3, quick classify/triage → llama3.2, any `*.patch`/`*.diff` gen → qwen-coder.

## 5. Pre-Pull Night-Before Commands (Windows)

Run the evening before a demo / flight / offline sprint so nothing downloads live:

```powershell
# 1. Pull + verify
ollama pull gemma3:4b; ollama pull llama3.2:3b; ollama pull qwen2.5-coder:7b

# 2. Rebuild 8k variants (idempotent)
ollama create gemma3:4b-8k -f Modelfile.gemma3-4b
ollama create llama3.2:3b-8k -f Modelfile.llama32-3b
ollama create qwen25coder:7b-8k -f Modelfile.qwen25coder-7b

# 3. Warm the KV cache (loads into VRAM)
ollama run gemma3:4b-8k "Reply with OK" --verbose
ollama run llama3.2:3b-8k "Reply with OK" --verbose
ollama run qwen25coder:7b-8k "Reply with OK" --verbose

# 4. Confirm
ollama list; ollama ps
```

Schedule via Task Scheduler (`taskschd.msc`) at 02:00 with `OLLAMA_KEEP_ALIVE=30m` so the morning session starts warm.

## 6. OLLAMA_NO_CLOUD=1 Guard

Ollama 0.12+ can route to Ollama Cloud when a model tag is missing locally — leaks prompts. Guard:

```powershell
# PowerShell — per-session
$env:OLLAMA_NO_CLOUD = "1"

# Permanent (machine-wide)
setx OLLAMA_NO_CLOUD "1"
# Then restart the Ollama service / tray app
```

Verify:
```powershell
[Environment]::GetEnvironmentVariable("OLLAMA_NO_CLOUD","Machine")
ollama run nonexistent-model-xyz "hi"   # must ERROR locally, must NOT silently succeed via cloud
```

Add to project `.env.example` and `opencode` bootstrap script:
```
OLLAMA_NO_CLOUD=1
OLLAMA_HOST=127.0.0.1:11434
OLLAMA_KEEP_ALIVE=30m
```

> Airline / client-VPN rule: set `OLLAMA_NO_CLOUD=1` **before** `ollama serve` starts; changing it after serve has no effect until restart.

## 7. Quick Troubleshooting

| Symptom | Fix |
|---------|-----|
| `model not found, trying cloud` | `OLLAMA_NO_CLOUD` not set or serve not restarted; then `ollama pull <pin>` |
| `out of memory` on 7b | `ollama stop` others; run only qwen-coder, or drop to `qwen2.5-coder:3b` |
| Slow TTFT after sleep | GPU re-init; `ollama stop <m> && ollama run <m> "OK"` to rewarm |
| CONTEXT 8192/8192 | prompt too long; summarize history, reduce `num_predict` |

---
*File: `research/build/47-fast-ollama.md` — pins: gemma3:4b / llama3.2:3b / qwen2.5-coder:7b @ num_ctx 8192, local-only.*
