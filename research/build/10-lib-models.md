# 10 — Local Models for `--local` Fallback

> Pick: **default `qwen2.5-coder:7b`** (balanced). Low-VRAM fallback: `gemma3:4b`. Avoid `llama3.2:3b` for tool use. Use `qwen3-coder:30b` only on 24 GB+ GPUs.

## 1. Candidates at a glance

| Model (Ollama tag) | Params / arch | Quant default | Disk / pull size | Native ctx | Tool-calling | Code quality |
|---|---|---|---|---|---|---|
| `qwen2.5-coder:7b` ✅ default | 7.6B dense, Qwen2 | Q4_K_M | ~4.7 GB | 32K | **Yes, strong** | Best in class ≤10B |
| `gemma3:4b` (low-VRAM pick) | 4.3B dense, Gemma3 | Q4_K_M | ~3.3 GB | 128K | Yes, weak-moderate | OK, terse |
| `llama3.2:3b` (smallest) | 3.2B dense, Llama3 | Q4_K_M | ~2.0 GB | 128K | Barely / inconsistent | Weakest |
| `qwen3-coder:30b` (`qwen3:30b-a3b` MoE) | 30B total / 3B active MoE | Q4_K_M | ~18–19 GB | 32K–256K variant-dependent | **Yes, best** | Best overall, heavy |

Sources: Ollama library tags + model cards. MoE note: `qwen3-coder:30b` is `Qwen3-30B-A3B` (3B active params per token) — compute is ~3B-class but **VRAM is 30B-class**.

## 2. VRAM table (`num_ctx 8192`, Q4_K_M, 100% GPU)

> Weights + KV-cache + ~0.5–1 GB Ollama overhead. Measured via `ollama ps` SIZE column. CPU-offload splits (e.g. `48%/52% CPU/GPU`) mean you exceeded VRAM.

| Model | Weights | KV @ 8K ctx (fp16 cache) | `ollama ps` SIZE ≈ | Min VRAM (8K) | Fits |
|---|---|---|---|---|---|
| `llama3.2:3b` | ~2.0 GB | ~0.5 GB | **2.5–3.5 GB** | 4 GB | Any iGPU / 6 GB card |
| `gemma3:4b` | ~3.3 GB | ~0.8–1.0 GB | **4.0–5.0 GB** | 6 GB | 6–8 GB cards |
| `qwen2.5-coder:7b` ✅ | ~4.7 GB | ~1.0–1.5 GB | **5.5–7.0 GB** | 8 GB | 8 GB+ cards (RTX 3060/4060) |
| `qwen3-coder:30b` | ~18.5 GB | ~2.5–3.5 GB | **19–23 GB** | 24 GB | RTX 3090/4090, A10, M-series unified ≥32 GB |

Scaling rule: doubling `num_ctx` roughly doubles KV-cache. 32K ctx adds ~4× the KV column above (7B @32K ≈ +5 GB; 30B @32K ≈ +12 GB). That is why we pin **8192**.

## 3. `num_ctx` Modelfile (8192)

Ollama default `num_ctx` is **2048** — too small for agentic tool loops. Pin 8192 via Modelfile (`FROM` + `PARAMETER num_ctx`; cf. [Modelfile docs](https://github.com/ollama/ollama/blob/main/docs/modelfile.mdx), [context-length guide](https://docs.ollama.com/context-length)):

```dockerfile
# Modelfile.local-8k
FROM qwen2.5-coder:7b
PARAMETER num_ctx 8192
PARAMETER temperature 0.2
PARAMETER num_predict -1
```

Build + run per model:

```bash
# default
ollama create local-coder-7b -f Modelfile.local-8k
ollama run local-coder-7b

# low-VRAM variant (swap FROM line to gemma3:4b)
# FROM gemma3:4b
ollama create local-coder-4b -f Modelfile.local-4b
```

Ad-hoc override without rebuild (current session only):

```bash
ollama run local-coder-7b
>>> /set parameter num_ctx 8192
```

## 4. `ollama ps` verification

```bash
ollama ps
# NAME              ID          SIZE    PROCESSOR  CONTEXT  UNTIL
# local-coder-7b    abc123…     6.2 GB  100% GPU   8192     5 minutes from now
```

Checklist:
1. `CONTEXT` == `8192` — else the Modelfile did not apply (rebuild).
2. `PROCESSOR` == `100% GPU` — `100% CPU` or split `CPU/GPU` = VRAM spill; drop to `gemma3:4b` or shorten ctx.
3. `SIZE` matches §2 row ±1 GB — large deviation = wrong quant or partial load.
4. JSON probe: `ollama ps` ↔ `GET /api/ps` exposes `size_vram` + `context_length` (see [api/ps](https://docs.ollama.com/api/ps)).

## 5. `emit_tool_plan` success rates

> `emit_tool_plan` = model must emit a single valid JSON tool-call object. Estimates from Qwen/Gemma/Llama tool-use reports + Ollama community evals; **re-measure with your harness** (`--local --dry-run` × 50 prompts).

| Model | Valid-JSON first try | Notes |
|---|---|---|
| `qwen3-coder:30b` | **~90–95%** | Best schema adherence; unusable without 24 GB VRAM |
| `qwen2.5-coder:7b` ✅ | **~80–90%** | Reliable with temp 0–0.2 + explicit JSON schema in system prompt |
| `gemma3:4b` | ~60–70% | Extra prose / truncated args; needs strict stop + retry |
| `llama3.2:3b` | ~40–55% | Frequent hallucinated keys, multi-object output; needs validator + 2 retries |

Recommendation: ship retry-with-repair (re-prompt with JSON error) so even the 4B tier reaches >90% effective success within 2 attempts.

## 6. Pre-pull commands (copy-paste)

```bash
# default — 8 GB GPUs
ollama pull qwen2.5-coder:7b

# low VRAM — 6 GB GPUs / iGPU
ollama pull gemma3:4b

# smallest — testing only, not recommended for tools
ollama pull llama3.2:3b

# workstation only — 24 GB+ VRAM, ~19 GB download
ollama pull qwen3-coder:30b
# alias: ollama pull qwen3:30b-a3b

# verify
ollama list | grep -E "qwen|gemma|llama"
```

Offline / hackathon kit: run all four pulls **before** the event; `ollama list` is your pre-flight.

## 7. Decision

1. **Default `--local` → `qwen2.5-coder:7b` + 8K Modelfile.** Best tool-JSON × VRAM tradeoff.
2. **Detect <8 GB VRAM → auto-fall back to `gemma3:4b`.**
3. **Flag `--local-max` → `qwen3-coder:30b`, warn if `ollama ps` shows CPU offload.**
4. Never default to `llama3.2:3b` for agentic runs — demo-only.
