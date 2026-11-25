# 03 — Secrets Audit (commit 2973b0f+, 2026-11-25)

## Scope
- `git log --all --oneline`: single commit `2973b0f v1.0-judging: Track 3 Onboard Copilot…`. No history to leak beyond HEAD.
- `git show --stat HEAD`: 230 files. Includes `.env.example`, `.synapse/config.json`, `.synapse/surface_cache.json`, `seed/api_keys.csv`. Does NOT include `.env`, `*.db`, `workspace-*/.env`, `*.jsonl`.
- Pattern grep `sk-|ghp_|xoxb|Bearer …|BEGIN …PRIVATE KEY`: only placeholders / fixtures / detector definitions / false positives (details below).
- `.gitignore` reviewed + appended (only file edited). `.synapse/config.json`, `workspace-*/.env` checked. `git ls-files | grep env` run (PowerShell `Select-String` equivalent).

## Findings
1. **LIVE KEY on disk (untracked, ignored — ROTATE/DO NOT COMMIT).** Root `.env:10` holds `SYNAPSE_API_KEY=syn-api-a5xkoy5mx3c2bvm4wik47bfh4rykiz6hmpwildz3918awqr6jr`. `git ls-files --error-unmatch .env` → not tracked; `git check-ignore -v .env` → ignored via `.gitignore:12`. `git log -p -- .env` → empty (never committed). Prior reports (`research/verify-final/15/16`) already flagged rotation. Still valid key material — rotate if ever staged/published.
2. **No secrets in git history.** Single-commit repo; `git log -p` secret search empty; filename search over `git log --name-only` hits only `seed/api_keys.csv` (see #5) and db-schema docs.
3. **`Bearer …` / private-key sweep: CLEAN.** No `Bearer <token>`, no `BEGIN *PRIVATE KEY`, no `ghp_/gho_/AKIA/AIza/hf_/xox[bap]-` values. `sk-` hits are: `guide.txt:168` `sk-ant-…` placeholder, `research/*` `sk-...`/`sk-ant-` placeholders, eval fixtures `sk-live-abc123xyz` in `eval/cases.json` (P03/P08 — synthetic redaction-test vectors, expected), `SECRET_RE`/`SECRET_VALUE_RE` definitions in `eval/run.py` + `safety_check_server.py`, `SN-…` hardware serials in `seed/equipment.csv` (fake inventory IDs), `mask-*` CSS false positives (per `research/ui/readiness.md`).
4. **`.synapse/config.json` (TRACKED): IDs only, OK.** Contains `hr-api`/`it-api` UUIDs + timestamps. No keys/tokens. Safe to keep tracked.
5. **TRACKED `seed/api_keys.csv`: prefixes + hashes only, no plaintext.** Columns `key_prefix` (`dp_/pr_/ci_/adm_` demo prefixes) + `key_hash` (sha256-looking hex). No plaintext secrets. Acceptable as synthetic seed fixtures; flag to judges as non-sensitive. Do NOT add real keys here.
6. **Env-file tracking status: GOOD.** `git ls-files | grep env` → only `.env.example`. Root `.env` + `workspace-25f2ad75-…/.env` both exist on disk, both ignored (` .env`, `workspace-*/`). Workspace `.env` is template defaults (`DATABASE_URL=file:…`, empty `NEXT_PUBLIC_*`, empty `ALLOW_DEMO_SEED`) — no secrets. `.env.example`, `.cursor/mcp.json`, `ngrok.yml` use `$VAR`/placeholder/empty values — safe.
7. **DB / session-jsonl status: GOOD (ignored, untracked).** `seed/demo.db`, `seed/seed-snapshot.db`, `workspace-…/db/custom.db` ignored via `*.db`; 9× `.synapse/discover/sess_*.jsonl` ignored via `.synapse/discover/`. None in `git ls-files`. No tracked `.pem/.key/session/jsonl`.
8. **`.gitignore` gaps closed (this audit's only edit).** Prior file covered `.env` (exact), `*.db*`, `workspace-*/`, `.synapse/discover/`. Appended: `.env.*` + `!.env.example` (variant files), `*.jsonl`, `*session*.json`, `*.pem`, `*.key`. Verified: `.env` still ignored, `.env.example` still tracked (not ignored), `*.jsonl`/`*.db` ignored, no tracked files newly ignored.

## Action taken
- Edited ONLY `.gitignore` (append 6 lines). Nothing else touched.

## Residual risks / recommendations
- Rotate the live `SYNAPSE_API_KEY` if the working tree was ever zipped/uploaded with `.env` included; never `git add .env`.
- Keep `.synapse/config.json` key-free (IDs only) — re-audit if `config set-key` ever writes secrets there.
- `submission/assets/quota-proof/synapse-info.txt` correctly redacts the key — keep that discipline for screenshots/logs.
