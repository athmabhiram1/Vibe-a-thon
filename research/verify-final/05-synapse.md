# 05 — Synapse Readiness Verification

**Date:** 2026-11-24 | **Reviewer:** Verifier (subagent) | **Scope:** Synapse CLI, Node, API key, hosted builds, H5 discover
**Verdict:** ☒ **BLOCKED** (no CLI, no API key — no hosted build run; nothing below is invented)

## 1. CLI + runtime (actually executed)

| Check | Result |
|---|---|
| `synapse --version` | **FAIL — not installed.** PowerShell: `synapse: The term 'synapse' is not recognized… CommandNotFoundException`. Absent from `npm list -g`. `npx -y synapse --version` → `npm error could not determine executable to run`. |
| Latest published (npm registry, `npm view`) | `0.1.9` — meets the 0.1.9+ bar **once installed**. Package: `@2ndbrainlabs-ai/synapse-cli`. |
| `node --version` | **PASS** — `v24.11.0` (≥20 required). `npm 11.13.0`. |
| `synapse info` (quota) | **NOT RUN** — impossible without CLI + key. `evidence/quota-log.md` still all-`TODO` placeholders; no quota recorded. |

## 2. API key (actually checked)

- `$env:SYNAPSE_API_KEY`: **absent**.
- No `.env` file exists (only `.env.example`, which contains **no** key line).
- `Select-String SYNAPSE_API_KEY` over `.env*`: **no matches**.
- Therefore: no hosted auth, no `synapse init` / `synapse config set-key` state, no quota to report.

## 3. Hosted builds — BLOCKED, not run

The following were **deliberately NOT run** (no CLI, no key). Expected outcomes are from `plan.md`/`evidence/quota-log.md`, **not** verified results:

- [ ] `synapse build --auto --all-endpoints --server-name hr-api` → expect H1–H4 tools
- [ ] `synapse build --auto --all-endpoints --server-name it-api --new` → expect I1–I6 tools (10 total)
- [ ] Uncomment H5 in `hr_service/routers/hr.py` (~lines 92–110) → `synapse build --discover --auto --all-endpoints --server-name hr-api` → expect 11th tool (`hr_get_oncall`), **same server ID**

Code readiness (static grep only, not a build): `hr.py` has 4 live `@router.*` decorators (lines 20/37/54/75) + 1 commented (line 94, `hr_get_oncall`); `it.py` has 6 (`it_service/routers/it.py` lines 22/38/56/78/94/109). So the 10-live + 1-commented shape matches the plan, but **tool counts (10, 11th, same server ID) are UNCONFIRMED**.

## 4. `--local` fallback path (keyless option)

- `ollama --version` client `0.40.16`; `ollama list` **works** — models present: `tev1:4b`, `llama3.1:8b`, `llama3.2:3b`, `qwen3:8b`, `qwen3-embedding:0.6b`. Local provider viable.
- Per `guide.txt:170-171`, `synapse init` is **not** needed for local builds (`synapse model set ollama` → `synapse build --local`, no quota).
- BUT: still requires the CLI installed, and `synapse_auto_server.py` does **not** exist yet (`Test-Path` False — expected, it is a build output). So `--local` is key-unblocked but **CLI-blocked**.

## 5. Exact unblock steps for the user

1. **Install CLI:** `npm install -g @2ndbrainlabs-ai/synapse-cli` (Node 20+ already satisfied), then `synapse --version` → expect `0.1.9`.
2. **Get key:** console at **https://synapse.2ndbrainlabs.ai/** (docs: **https://synapse.2ndbrainlabs.ai/docs**) — create account/project, copy API key. (Sources: `research/01-2nd-brain-labs.md:114`, npm README.)
3. **Save key:** `synapse init` in repo root, or `synapse config set-key <key>`.
4. **Record quota:** `synapse info` before/after every build → append to `evidence/quota-log.md` (free tier per plan: 10 servers + 100k indexed lines; rebuilds free until `--discover`).
5. **Baseline builds:** `synapse build --auto --all-endpoints --server-name hr-api`, then `... --server-name it-api --new`; confirm 10 tools.
6. **Live moment:** uncomment H5 (`hr.py` ~L92–110) → `synapse build --discover --auto --all-endpoints --server-name hr-api` → confirm 11th tool, same server ID; bump `MCP_REV` 1→2.
7. **Keyless alternative:** skip 2–3; after step 1 run `synapse model set ollama` + `synapse build --local`.

## 6. Re-check routing

- Status: **BLOCKED** — do not claim 10/11 tools or same-ID until §5 steps 1–6 (or 1+7) are executed with pasted `synapse info` / build output.
- Re-verify after unblock: rerun this file's §1–§3 commands and fill `evidence/quota-log.md`.
- Spec sources: `plan.md:104-112`, `guide.txt:92-112,157-204,232-271`, `research/01-2nd-brain-labs.md`, `research/03-synapse-technical.md` (CLI 0.1.9, 2026-11-09).
