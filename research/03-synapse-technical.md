# Synapse CLI — Technical Due Diligence

**Researched:** 2026-11-22 · **CLI latest:** `0.1.9` (2026-11-09) · **Repo:** `2ndbrainlabs-ai/synapse-cli-ts` (Apache-2.0)
**Companion runner:** `@2ndbrainlabs-ai/synapse-mcp` `0.0.4` (2026-08-24)
**Method:** npm registry API, GitHub API + raw source reads, official README, docs site (`synapse.2ndbrainlabs.ai/docs`).
Claims without a cited file/URL are marked **(unverified)**.

---

## 1. Project snapshot

| Item | Value | Evidence |
|---|---|---|
| Latest CLI version | **0.1.9**, published **2026-11-09** | `registry.npmjs.org/@2ndbrainlabs-ai/synapse-cli` `time` field (`0.1.9: 2026-11-09T12:18:45`) |
| Release cadence | 0.1.5 (Sep 3) → 0.1.6/0.1.7/0.1.8 (Nov 1–2) → 0.1.9 (Nov 9); active | Same registry `time` map; CHANGELOG.md |
| Downloads | **1,212 last month / 139 last week** (`synapse-cli`); **143 last month** (`synapse-mcp`) | `api.npmjs.org/downloads/point/last-month/...` (both packages) — tiny adoption |
| GitHub | **7 stars, 4 forks, 0 subscribers**, created 2026-05-18, pushed 2026-11-19 | `api.github.com/repos/2ndbrainlabs-ai/synapse-cli-ts` |
| Open issues/PRs | **3 open** — #66 hackathon-badge PR, #65 CI/branch-protection PR, (+1 more); no user bug reports visible | Same API, `open_issues_count: 3` |
| License | **Apache-2.0, genuinely open source** (LICENSE + NOTICE files; `license: Apache-2.0` on npm since 0.1.4). Note: npm 0.1.0–0.1.3 were **MIT**; docs-site footer still says "MIT" (stale) | npm registry `license` per version; repo `LICENSE` blob; docs footer |
| Runtime req | **Node.js ≥ 20** (`engines: >=20` since 0.1.9; README "Requires Node.js 20+") | npm 0.1.9 manifest; README `#install` |
| Provenance | 0.1.6+ published via **trusted publisher (GitHub OIDC)** with SLSA attestations | npm manifest `trustedPublisher`, `attestations` |
| Backend openness | CLI is open; **hosted backend (gRPC `grpc.synapse.2ndbrainlabs.ai:443`) is NOT open source** ("the backend isn't open source", maintainers only) | `docs/architecture.md`; `AGENTS.md` ("Code generation runs… on the hosted Synapse backend") |

---

## 2. Verified capabilities

### 2.1 Exact CLI surface (README-confirmed; participant guides often stale)

| Command | Purpose | Source |
|---|---|---|
| `synapse init [--force]` | One-time: validate Synapse API key, create `.synapse/` | README `#commands` |
| `synapse build [--auto\|--custom] [-q <query>] [--smart-names] [--local] [--resume] [--discover]` | v2-only generation. No flag → interactive Auto/Custom picker | README `#commands`, `#how-build-works` |
| `synapse build --auto --all-endpoints \| --endpoints "GET /x,…"` | Headless/CI endpoint selection; either flag implies `--auto` | README `#reusing-discovered-endpoints` |
| `synapse build --auto --server-name <n> / --new` | Rebuilds update same server id; `--new` forks a new server | README `#rebuilding` |
| `synapse analyze [-o <dir>] [-v]` | Python-only scan → `.synapse/project_schema.txt`, `statistics.json`; counts indexed lines | README `#the-v1-engine-was-removed` |
| `synapse config` / `config set-key [<k>] [--global]` / `config keys` / `config revoke <id>` | Key lifecycle (Fernet-encrypted, machine-bound; `SYNAPSE_API_KEY` env wins) | README `#synapse-api-key` |
| `synapse model` / `model list` / `model set <p> [...]` / `model reset` | **Local-mode only** provider/model selection (9 providers) | README `#choosing-a-provider` |
| `synapse info` / `update` / `uninstall` | Quota + project state / self-update / remove | README `#commands` |

**README items most participant guides omit:** `--discover` (rescans; builds otherwise reuse `.synapse/surface_cache.json`), `--resume` (continues scans paused by `--max-time`/Ctrl-C via JSONL ledger, `synapse logs`), `--smart-names` (Auto-only LLM naming from handler source + README), `--server-name/--new` (multi-server projects), `--dev` (localhost:50051 backend), exit-nonzero contract on any unfinished build, `.env.example` merging on Custom builds, `${VAR}`/gRPC telemetry details.

**⚠️ Docs site is stale — do not trust it over the README:** `synapse.2ndbrainlabs.ai/docs` still documents the **removed v1 engine** (`--query`, `--output`, `--no-validate/--no-docs/--generate`, `synapse status`, Node 18, Qdrant indexing, "Output defaults to `mcp_server.py`"). The README states v1 was removed in SYN-257 (0.1.9) and passing v1 flags now **exits non-zero**. Evidence: docs page sections "Analyze Your Codebase… Qdrant", "`synapse build --query … --output … --no-validate`", "`synapse status`", footer "Synapse v1.0.0 | MIT License".

### 2.2 Auto-mode mechanics (static parse — app does NOT need to run)

- **No running app, no OpenAPI needed.** Detection is fully static: a 64 KB head-sniff + Aho-Corasick needle prefilter (`src/extractors/core/prefilter.ts`, `core/needles.ts`) selects candidate files, then **tree-sitter** parses decorators/annotations per language (`docs/architecture.md` "Surface extraction"; `AGENTS.md` "Code exploration always runs on the user's machine").
- **Per-language route markers** (`src/extractors/core/needles.ts`, plus `src/extractors/languages/python.ts` `decoratorToRoute()`):
  - **Python:** `@app.get/post/…`, `@router.*`, `@*.route(..., methods=[…])`, `api_route`, Flask `add_url_rule`, Django `path()/re_path()/url(`, aiohttp `router.add_get…`, `@get/@post…`. Covers FastAPI/Flask/Starlette/Django.
  - **TypeScript:** Express-style `.get()/.post()…`, `app.*`, `server.route`, Nest `@Get/@Post…/@Controller`, Next.js `NextApiRequest/Response`.
  - **Java:** `@GetMapping/@PostMapping/…`, `@RequestMapping`, JAX-RS `@GET/@POST…`, `@Path`, Vert.x `router.get(`.
  - **C#:** `[HttpGet…]`, `[Route]`, `[ApiController]`, minimal-API `MapGet/MapPost…`, `app.Map`.
  - **Go:** gin `r.GET(`/`engine.`, echo `e.GET(`, fiber `app.Get(`, stdlib `http.HandleFunc`, gorilla `mux.HandleFunc`, beego.
  - **Rust:** `#[get/post…]`, `web::get()`, `.route("`, `Router::new()`, `warp::path(`, actix macros.
- **Plain `.js/.jsx` is NOT scanned** (README language table). Language is chosen by root marker file (`pyproject.toml`, `tsconfig.json`, `pom.xml`, `go.mod`, `Cargo.toml`, …) else majority extension.
- **Your API must be deployed separately for hosted Auto tools to work:** each generated tool is an HTTP forward (`requests.<method>(url, …)`, base URL from `ENDPOINT_BASE_URL` env) to your live API — Synapse only proxies, it does not host your code. Evidence: `src/backend/server-renderer.ts` `renderEndpointTool()`; endpoint config stores method/path/header hints + example payload.

### 2.3 Generated server reality

- **Everything generated is Python (FastMCP). No TS/JS servers, ever.** (README language-support table.)
- **Hosted Auto → no file at all.** Endpoint config is saved to your Synapse account; the MCP client runs the generic runner:
  ```json
  {"command":"npx","args":["-y","@2ndbrainlabs-ai/synapse-mcp"],
   "env":{"SYNAPSE_API_KEY":"…","SYNAPSE_SERVER_ID":"…","SYNAPSE_API_URL":"https://api.synapse.2ndbrainlabs.ai","MY_TOKEN":""}} 
  ```
  The runner fetches endpoint config at runtime. (Docs "Generated claude_desktop_config.json"; runner description "fetches endpoint config at runtime using your Synapse API key".)
- **Local Auto (Python only) → `synapse_auto_server.py`:** one `requests`-forwarding tool per endpoint; path params `{x}` + JSON-body keys become tool params (all `Any = None`); auth via `${VAR}` env placeholders; response = `resp.json()` or `{status_code, text}` fallback; `resp.raise_for_status()` on HTTP errors. (`server-renderer.ts` `renderPassthroughPython`.)
- **Custom (hosted or `--local`, Python only) → `<tool_name>_server.py`:** single `@mcp.tool` FastMCP file with LLM-written `body_source`, model-chosen params, `FastMCP("<name>")` + `mcp.run()`. (`server-renderer.ts` `renderPython`.)
- **No streaming, pagination, resources, prompts, or subscriptions appear anywhere** in the renderer, schemas, or docs — tools return `dict`. **(Unverified inference:** out of scope for the generator; confirm at event.)

### 2.4 Custom mode ("compose functions into one tool") — what actually happens

1. You describe a workflow (`-q`) or cherry-pick 2+ functions from the ranked list (`src/commands/v2/custom-flow.ts` `collectIntent()`).
2. The pipeline (hosted backend, or your own model with `--local`) runs **classify → shape → render → verify**: candidate classifier bands functions HIGH/MEDIUM/LOW/SKIP; `tool-shaper` forces **one `emit_tool_plan` tool call** returning a `ToolPlan` (`tool_name, description, param_names/types, body_source, imports, env_vars, is_async`); `server-renderer` emits the file; `smoke-verifier` AST-checks + repairs (≤3 attempts). Evidence: `CONTEXT.md` "Local codegen pipeline"; `src/backend/tool-shaper.ts`, `src/backend/schemas.ts`.
3. **Mechanically it is a generated wrapper, not inlining or live imports of your app:** the model writes fresh `body_source` that may **only call functions present in the extracted manifest** (AST audit rejects unknown callees and inline `def` helpers), and the renderer auto-adds `from <module> import <qualname>` for each referenced function (`server-renderer.ts` `canonicalImports()`; `tool-shaper.ts` `auditBody()` + `BUILTINS_ALLOW`).
4. Output is written to the **project root** with numeric-suffix collision avoidance (`writeWithSuffix()`), and required env vars are merged into `.env.example` (`mergeEnvExample()`).

### 2.5 Hosted vs `--local`, quotas, offline

| | Hosted (default) | `--local` |
|---|---|---|
| Codegen | Synapse gRPC backend (streaming progress), central model/quota | In-process pipeline on **your** key: Anthropic, OpenAI, Groq, xAI, OpenRouter, **Ollama (no key)**, Bedrock, Vertex, or any OpenAI-compatible `--base-url` |
| Needs `synapse init`? | Yes (API key) | **No** — one-shot `synapse build --local --llm-api-key …` works in a fresh repo |
| Output | Auto: account-side config + `npx synapse-mcp` runner. Custom: `<tool>_server.py` | Auto: `synapse_auto_server.py` (**Python projects only**; TS/Java/C#/Go/Rust get `--smart-names` names but **no file**). Custom: `<tool>_server.py` (Python only) |
| Quota | **10 MCP servers, 100,000 indexed lines**; rebuilds of unchanged repos cost ~nothing (delta-only reporting) | **No quota, no signup** |
| Offline demo? | **No** — needs gRPC backend + REST quota + hosted runner fetch | **Mostly yes:** Ollama or any local OpenAI-compatible endpoint keeps code + inference on-machine; but **anonymous telemetry still phones home** unless `SYNAPSE_TELEMETRY=0` |

### 2.6 Free-tier / latency notes

- Free tier: **10 servers / 100k indexed lines** (`synapse info` shows usage; `Quota Exceeded` error documented).
- No published per-minute rate limits or latency SLOs **(unverified — nothing in README/docs states them)**. Live-hackathon risks: gRPC codegen round-trip + streaming; `--local` latency = your provider (default 5-min per-request timeout, raisable via `SYNAPSE_LLM_TIMEOUT_MS`); small/weak local models fail codegen with `returned no emit_tool_plan call` — "fix is a stronger model".
- Only **3 open GitHub items, both PRs** (hackathon badge, CI branch protection) — **no public failure reports to mine**; reliability must be tested live.

---

## 3. Hard limits / gotchas (hackathon-relevant)

1. **Python-or-nothing for files.** Any demo that must show a runnable server must use a Python codebase. A TS/Java/Go/C#/Rust repo on `--local` yields names but no file; hosted yields no file for any language (runner instead).
2. **No `.js/.jsx` scanning.** A Next.js/Express-in-JS project is invisible; needs `.ts/.tsx` (or a marker file that still won't help JS).
3. **Auto tools are dumb HTTP forwards.** They call your *deployed* API at demo time — localhost/ngrok/deploy required, plus `ENDPOINT_BASE_URL` + secrets configured. No deployed API = dead demo for Auto.
4. **Custom mode is one tool per build** (single `@mcp.tool`), Python functions only, no inline helpers, every call must resolve to an extracted function. Multi-step "agent workflows" = multiple builds or hand-editing.
5. **Stale cache trap:** builds reuse `.synapse/surface_cache.json` silently ("Using the endpoints discovered on …"). Code changed since last scan is **ignored until `--discover`**. During a live demo, always `build --discover`.
6. **Headless builds need flags:** no TTY + no `--all-endpoints`/`--endpoints` = hard error, not a default.
7. **v1 flags are now fatal:** `--query/--output/--no-validate/--no-docs/-g/--engine v1` exit non-zero. Old tutorials (including Synapse's own docs site) will break copy-paste.
8. **Hosted = network + account dependency:** Synapse key, gRPC `grpc.synapse.2ndbrainlabs.ai:443`, REST quota, runner fetch of endpoint config. Judge laptops need keys + env filled in.
9. **`--local` still leaks metadata** (event names, counts, token/timing, hashed paths) unless `SYNAPSE_TELEMETRY=0`; quota calls never fire for `--local`.
10. **No schema for streaming/pagination/shaping** in the generator — if the idea needs paginated search, file streaming, or MCP resources/prompts, plan hand-written code on top.
11. **Tiny footprint = thin support surface:** 7 stars, ~1.2k monthly downloads, 0.1.x versioning, backend closed-source. Fine for a hackathon, risky as a "production dependency" story.

---

## 4. Unknown / must test at the event

- [ ] End-to-end hosted Auto on a real FastAPI app: does the runner tool actually call the deployed API through Claude Desktop/Cursor?
- [ ] End-to-end `--local` with Ollama (`qwen3-coder:30b`-class) — does codegen succeed or hit `no emit_tool_plan call`?
- [ ] Custom-mode quality: does the composed tool handle errors/retries, or just happy-path?
- [ ] Authenticated routes: do `${VAR}` header placeholders + `.env.example` merge work first try?
- [ ] Multi-method/path edge cases (query strings, webhooks, websockets, file uploads) — detection is decorator-regex based, so exotic routing likely misses **(unverified)**.
- [ ] Rate limits / cold-start latency of hosted gRPC codegen under event Wi-Fi — nothing published.
- [ ] `synapse-mcp` runner has **no README** on npm and no source in the CLI repo — runtime failure modes unknown; test `npx -y @2ndbrainlabs-ai/synapse-mcp` early.
- [ ] Whether generated servers validate/install cleanly (`pip install mcp`, `ast.parse`, MCP client handshake) on a fresh machine.

---

## 5. Competitor landscape — what is already commoditised

| Project | Stars (≈ Nov 2026) | Language / License | What it does | vs Synapse |
|---|---|---|---|---|
| `PrefectHQ/fastmcp` | **~28,700** | Python / Apache-2.0 | The Pythonic MCP framework: decorators, `FastMCP.from_openapi()`, `fastmcp generate` CLI, enterprise gateway | The substrate Synapse *generates into*; full framework, not just a generator |
| `modelcontextprotocol/python-sdk` | **~24,900** | Python / MIT | Official MCP Python SDK (server + client primitives) | Lower-level official SDK; any hand-written fallback builds on this |
| `tadata-org/fastapi_mcp` | **~12,000** | Python / MIT | Zero-config: mount an MCP server onto an existing FastAPI app (`FastApiMCP(app).mount()`) | Direct overlap with Synapse Auto-for-FastAPI, 1000× the adoption; no LLM step, fully offline |
| `harsha-iiiv/openapi-mcp-generator` | **~645** | TypeScript / MIT | CLI: OpenAPI spec → standalone TS MCP server | Covers the spec-driven path Synapse skips (Synapse needs no OpenAPI, but also can't consume one) |
| `strowk/mcp-k8s-go` | **~380** | Go / MIT | Hand-built domain MCP server (Kubernetes) | Example of the "just write it with an SDK" alternative |
| `cnoe-io/openapi-mcp-codegen` | **~43** | Python / Apache-2.0 | OpenAPI → MCP server codegen (CNCF-adjacent) | Same niche as above, smaller |
| Synapse CLI (this) | **7** | TS CLI → Python out / Apache-2.0 | Codebase → MCP server via static extraction + LLM composition | Differentiator is *source-code-in, multi-language detection, Custom composition* — but adoption is 3–4 orders of magnitude behind |

Sources: GitHub API `stargazers_count` for `PrefectHQ/fastmcp`, `modelcontextprotocol/python-sdk`, `harsha-iiiv/openapi-mcp-generator`, `cnoe-io/openapi-mcp-codegen`, `strowk/mcp-k8s-go` (queried 2026-11-22); `tadata-org/fastapi_mcp` via star-history/gitranks (~12.0k). **Takeaway for judging:** "generate an MCP server from code" is commoditised (FastMCP, fastapi_mcp). A Synapse-based hack must win on *composition/workflow*, *multi-language detection*, or *hosted-runner zero-file UX* — not on generation per se.

---

## 6. Key URLs & file evidence

- npm CLI: `https://www.npmjs.com/package/@2ndbrainlabs-ai/synapse-cli` · registry JSON: `https://registry.npmjs.org/@2ndbrainlabs-ai/synapse-cli` (versions, dates, licenses, deps)
- npm runner: `https://www.npmjs.com/package/@2ndbrainlabs-ai/synapse-mcp` (v0.0.4, no README)
- Repo: `https://github.com/2ndbrainlabs-ai/synapse-cli-ts` · issues: `…/issues` · examples: `https://github.com/2ndbrainlabs-ai/synapse-examples` (linked from README)
- Docs (stale, v1-era): `https://synapse.2ndbrainlabs.ai/docs` · console: `https://synapse.2ndbrainlabs.ai`
- Source files cited: `src/extractors/core/needles.ts` (route markers), `src/extractors/languages/python.ts` (`decoratorToRoute`), `src/backend/server-renderer.ts` (`renderPython`, `renderPassthroughPython`), `src/backend/tool-shaper.ts` (3-attempt shape + `auditBody`), `src/backend/schemas.ts` (`ToolPlan`, forced `emit_tool_plan`), `src/commands/v2/custom-flow.ts` (`collectIntent`, `writeWithSuffix`, `mergeEnvExample`), `docs/architecture.md`, `docs/LOCAL_MODE_VERIFICATION.md`, `AGENTS.md`, `CONTEXT.md`, `CHANGELOG.md`
