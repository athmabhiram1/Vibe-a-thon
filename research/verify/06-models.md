# 06 — Models: Kill the Ollama Pins?

> Verdict: **KILL `llama3.2:3b` entirely. DEMOTE `gemma3:4b` to low-VRAM emergency only. KEEP ONE local pin: `qwen2.5-coder:7b @ num_ctx 8192` as offline fallback. DEFAULT = hosted frontier + cached-JSON fallback. Do NOT add 30B. Do NOT switch runners. Do NOT go no-local-only.**

Date: 2026-11-22 | Context: 16 GB laptop (typical: 8 GB VRAM dGPU or 16 GB unified / iGPU-only), Ollama 0.32–0.40, Q4_K_M, `num_ctx 8192`

## 1. Pins under test

| Pin | Ollama tag | Params / quant | Download | Max ctx |
|---|---|---|---|---|
| Primary (claimed) | `gemma3:4b` | 4.3B dense + 0.42B vision, Q4_K_M | 3.4 GB | 128K |
| Fallback (claimed) | `llama3.2:3b` | 3.21B dense, Q4_K_M | 2.0 GB | 128K |
| Codegen (claimed) | `qwen2.5-coder:7b` | 7.6B dense, Q4_K_M | 4.7 GB | 32K |
| Config | `num_ctx 8192` | — | — | — |

## 2. VRAM math on 16 GB laptop — all three FITS, 30B DOES NOT

Formula: `total = weights + KV_cache + overhead (~0.5–1.2 GB Ollama/CUDA)`.
`KV/token = 2 × layers × KV_heads × head_dim × bytes_per_elem`. Ollama pre-allocates full `num_ctx × OLLAMA_NUM_PARALLEL` at load.

| Model | Weights Q4_K_M | KV/token (fp16) | KV @ 8K | `ollama ps` SIZE @ 8K | Fits 16 GB laptop? |
|---|---|---|---|---|---|
| `llama3.2:3b` | ~1.8 GB | ~110 KB (28L, GQA) | ~0.9 GB | **3.1–3.5 GB** (2.2 GB @2K → 6.1 GB @32K) | Yes, trivially |
| `gemma3:4b` | ~2.5 GB (+0.8 GB vision if images) | ~136 KB, sliding-window capped (34L, 4 KV heads, window 1024) | ~0.3 GB | **3.5 GB text / 4.3 GB Ollama tag @8K** (5.8 GB @128K) | Yes, easily |
| `qwen2.5-coder:7b` | ~4.4–4.7 GB | ~56 KB (28L, 4 KV heads, d=128) | ~0.46 GB | **5.5–6.4 GB @8K** (5.8 GB @4K, 6.4 GB @16K, 8.0 GB @32K) | Yes — 8 GB VRAM card or 16 GB RAM CPU-only |
| `qwen3-coder:30b` / 30B-A3B MoE | ~17 GB | ~200+ KB | +2–5 GB @32K | **~22–25 GB @4K, ~25–28 GB @32K** | **NO — needs 24 GB+ GPU. Impossible on 16 GB laptop. Even Q3_K + q4_0 KV (~23 GB) overflows.** |

Sources: RunOnMy gemma-3-4b-it (3.5 GB @8K), vramcalculator llama-3.2-3b (3.5 GB @8K), RunOnMy qwen2.5-coder-7b (5.5 GB @8K), willitrunai/spheron/contabo 30B tables (16.8 GB weights + KV + 1–2 GB overhead).

Key trap: 4 GB cards spill at 8K. Measured: `llama3.2:3b` fits 100% GPU only to `num_ctx 2048`; at 4096 → 80% GPU, 61% speed; at 8192 → 68% GPU, 43% speed. `qwen2.5-coder:3b` fits to 8192. Ollama reserves ~1 GB headroom (`nvidia-smi` showed >1.1 GB free even when spilling) — check `PROCESSOR` column, not just free VRAM.

CPU-only reality (i5-6500T, 16 GB, no GPU): `qwen2.5-coder:7b` @8K = 5.5 GB RAM, **4 tok/s write, 14 tok/s prompt-read** — a 2K-token file costs 144 s first read (1.9 s cached). Usable offline, unusable for live demo loops.

## 3. `emit_tool_plan` success — the kill shot for 3B/4B

`emit_tool_plan` = single valid JSON tool-call object (`tool_name, description, param_names/types, body_source, imports, env_vars, is_async`). `guide.txt:196,273` warns: `returned no emit_tool_plan call → model too small, switch to stronger model`.

| Model | Success rate (50-prompt harness, temp 0–0.2 + strict schema) | Failure mode |
|---|---|---|
| `qwen2.5-coder:7b` ✅ | **80–90%** | Reliable; occasional arg truncation, fixed with 1 retry |
| `gemma3:4b` | 60–70% | Extra prose, truncated args; needs stop-string + retry |
| `llama3.2:3b` ❌ | **40–55%** | Hallucinated keys, multi-object output; needs validator + 2 retries — still <60% |
| Hosted frontier (GPT-6.1-sol / Opus 5.5 / DeepSeek V4.1 Flash) | **95–100% + self-tests** | 20/20 hidden tests, catches 8–9/9 planted wrong fixes |

Local-vs-cloud agent benchmark (minibank 700-line ledger, 20 hidden tests): cloud 0.96–1.00 in 91–288 s ($0.14–$1.79); laptop Gemma-12B 0.21 in 575 s; Qwen-30B-MoE 0; dense-27B timeout. Cheap hosted DeepSeek V4.1 Flash: **1.00 in 112 s for $0.008**. Spinal review eval: frontier precision 40% vs local-27B 24% / 7%; local detection intervals overlap but noise (false positives) 2–3× worse.

**Conclusion: neither 3B nor 4B clears the T5 gate (`emit_tool_plan <60% → cached-JSON`). 3B fails it outright. 4B sits on the line and needs retry scaffolding that blows TTFT.**

## 4. TTFT & throughput

| Path | Cold start → first token | Decode | Notes |
|---|---|---|---|
| Local GPU (RTX 5070/5080, Qwen3-8B Q4) | 6.5–11 s (Ollama fastest on some iGPUs: 10.3 s vs 14.3 s llama.cpp) | 40–70 tok/s; 314 tok/s (3B, 16 GB card) | Ollama ~10% behind raw llama.cpp on Nvidia (69 vs 77 tok/s); LM Studio ~0.3% behind on Nvidia but 29% behind on M3 Max (version lag). Within noise for demo. |
| Local CPU-only (7B) | 13–36 s load | 4 tok/s write | Prompt-read dominates; keep one chat per file (KV cache reuse). |
| Spill (model > VRAM) | 12–26 s | Ollama 43.6 tok/s vs llama.cpp 38.8 vs LM Studio 27.8 | Ollama's auto-split beats LM Studio when overflowing — another reason not to switch. |
| Hosted frontier | +20–50 ms network | 50–150 tok/s server-side | vLLM TTFT flat under concurrency; Ollama TTFT rises sharply with `NUM_PARALLEL>1`. For multi-agent demo, hosted wins. |

Ollama vs LM Studio vs llama.cpp (Mozilla 2026, Kingy Nov-2026, Zenodo RTX-5080 controlled sha256): **same GGUF → ±3–6% PP, ±5–11% decode. All three are llama.cpp underneath.** Switch runners only for UX (LM Studio GUI/slider, llama.cpp manual `-ncmoe` MoE offload), never for speed.

## 5. Context-truncation risk (`num_ctx 8192`)

- Ollama default: **4096** below 24 GiB VRAM (32K at 24–48 GiB, 256K at 48 GiB+). Unpinned 8K+ system prompts (agent prompt alone ~15K tokens in one eval) **silently truncate → `no emit_tool_plan` / empty diffs**. LM Studio default 8192 caused the same silent failures.
- KV is pre-allocated: requesting 8192 pays 8192 even for a 1-line prompt. Doubling ctx ≈ doubles KV (7B: +0.5 GB per 8K; 32B: +2.1 GB per 8K). `NUM_PARALLEL=4` × 8K = 32K of KV.
- Mitigation (already in `build/05-deploy.md`, `build/10-lib-models.md`): Modelfile `PARAMETER num_ctx 8192`, verify `ollama ps` → `CONTEXT==8192`, `PROCESSOR==100% GPU`, `GET /api/ps → context_length`. Optional `OLLAMA_KV_CACHE_TYPE=q8_0` halves KV (needs flash attention, ~no quality loss); `q4_0` quarters it.
- 8192 is the sweet spot: holds tool schema + 2–3 files; 32K on 7B costs +5 GB and 30-min CPU reads. Never set max (128K) "just because" — Gemma-4B @128K = 5.8 GB KV alone.

## 6. Alternatives scored

| Option | Quality | Cost/latency | Offline | Verdict |
|---|---|---|---|---|
| **A. Hosted frontier only** (Codex/Opus/Sonnet/DeepSeek Flash) | 0.96–1.00, 40% precision | $0.008–$0.30/run, ~100 s, flat TTFT | ❌ dead without net | **DEFAULT for demo/judged runs** |
| **B. LM Studio / llama.cpp instead of Ollama** | Same weights → same quality | ±10% tok/s, Ollama better on spill | ✅ | **NO SWITCH — keep Ollama; runner is not the bottleneck** |
| **C. Bigger 30B (qwen3-coder:30b)** | Near-frontier on big rigs (0.92–0.96 but 472–987 s) | 110 min vs 19 min frontier; 96 GiB resident | ❌ on 16 GB laptop | **KILL — requires DGX Spark / 24 GB+; exclude from pins** |
| **D. No-local (cached-JSON fallback only)** | Deterministic, 0% hallucination | Instant, $0 | ✅ | **KEEP as P3 fallback** (T5 gate: `emit_tool_plan <60% → cached-JSON`). Stale by design — pair with A, don't ship alone |
| **E. Single local pin `qwen2.5-coder:7b @8192`** | 80–90% tool-JSON, best ≤10B | 5.5–7 GB, 40–70 tok/s GPU / 4 tok/s CPU | ✅ | **KEEP as P2 offline fallback. Pre-pull night before.** |

## 7. Decision (falsification log)

1. `llama3.2:3b` — KILLED. Fails T5 (<60%), weakest codegen, spills earliest (2K limit on 4 GB cards). Remove from pull list; keep mention only as "never default for agentic runs."
2. `gemma3:4b` — DEMOTED. Keep one line in Modelfile (`FROM gemma3:4b` swap) for <8 GB VRAM emergency. Not primary: vision overhead + 60–70% tool rate + terse reasoning.
3. `qwen2.5-coder:7b @8192` — KEPT as sole local pin. Only model in class clearing 80%+ tool-JSON within 8 GB budget. Freeze tag (`dae161e27b0e`), pin Modelfile, pre-pull + `ollama ps` screenshot.
4. `num_ctx 8192` — KEPT. Prevents silent truncation; affordable (+0.5–1 GB vs 4K). Enforce via health check (`/api/ps`).
5. Runner — KEEP Ollama (`ollama/ollama:0.6.8` pinned). No migration to LM Studio/llama.cpp for speed; document `lms`/`llama-cli` one-liners only as backup install paths.
6. 30B — REJECTED on 16 GB laptop (math above). Gate behind `--local-max` + 24 GB VRAM check.
7. Topology — **Hosted (P0/P1) → qwen-7B-8K local (P2) → cached-JSON protocol (P3) → lesson (P4)**. T5 tripwire: `emit_tool_plan <60% → cached-JSON; quota <40% → freeze hosted (D12)`.

## 8. Pre-flight (copy-paste)

```bash
ollama pull qwen2.5-coder:7b  # + gemma3:4b only if <8GB VRAM machine in play
ollama create demo-qwen-8k -f Modelfile.local-8k  # FROM qwen2.5-coder:7b + PARAMETER num_ctx 8192
ollama ps  # expect CONTEXT 8192, PROCESSOR 100% GPU, SIZE ~5.5-7GB
curl -s 127.0.0.1:11434/api/ps | jq '.models[] | {name, context_length, size_vram}'
# local-first drill: mycli --local --model demo-qwen-8k ; hosted drill: default flags
```

## Sources (8+ web)

1. RunOnMy Gemma-3-4B-IT VRAM (3.5 GB @8K, KV table, GQA+sliding-window arch) + Ollama tag 3.4 GB
2. vramcalculator Llama-3.2-3B (3.5 GB @8K, 6.1 GB @32K) + Jeremiah Fisher `num_ctx` spill test (2K GPU limit, 61%/43% speed on split)
3. RunOnMy/localmodel.run Qwen2.5-Coder-7B (5.5–5.8 GB @8K, 4.36 GB GGUF, 32K native) + CPU-only test (5.5 GB, 4 tok/s)
4. Mozilla exp-llama-benchy (Ollama/LM Studio/llama.cpp share core, ±3%) + InventiveHQ overhead test (Ollama −10%, LM Studio −0.3% Nvidia / −29% Mac) + Kingy Nov-2026 3-machine + Zenodo RTX-5080 controlled
5. BizStack minibank (cloud 1.00/91 s vs local 0.21/575 s), Spinal frontier-vs-27B review (40% vs 24%/7% precision), Zack Proser 60-run eval, DeepSeek-V4-Flash $0.008 perfect score
6. willitrunai / spheron / contabo VRAM tables (30B-A3B 16.8 GB weights, 24 GB+ needed), Qwen3-KV-cache quantization study
7. Ollama FAQ + RunLocal context guide (`num_ctx` default 4K, `ollama ps` PROCESSOR/CONTEXT), BigIron KV math (`2·L·KV·d·bytes`), llama-paddock fit estimates, CUDA-OOM thread
8. RedHat Ollama-vs-vLLM TTFT (Ollama TTFT rises with concurrency), SitePoint local-vs-cloud harness, TinyWeights overhead table
9. Repo ground truth: `research/build/10-lib-models.md` (80–90%/60–70%/40–55% tool rates, 8192 Modelfile), `research/build/05-deploy.md` (P0–P4 ladder), `guide.txt:196,273` (`no emit_tool_plan → stronger model`), `plan.md:136` (T5 gate)
