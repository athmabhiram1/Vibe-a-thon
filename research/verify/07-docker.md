# 07 — Docker Compose: Kill It? (api+api+postgres+redis+ollama)

**Verdict: KILL Docker Compose as the default path. Make single-process (2× uvicorn + SQLite, no Docker) the golden path. Keep Docker as an opt-in `compose.opt.yml`, not the README step 1. Docker is the single highest D3-eat risk on this stack — mostly because of Ollama + cold-pull + healthcheck-gating, not because Docker is "bad".**

## TL;DR comparison

| Option | Solo setup time (fresh laptop) | Cold-start T1 tripwire (>90s) risk | Hot-spare clone story | Judge rerun (fresh clone, ≤3 cmds?) | D3 risk |
|---|---|---|---|---|---|
| **A. Docker Compose (api+api+postgres+redis+ollama)** | 30–90+ min if uncached (Docker Desktop install + first `pull` + first `build` + model pull) | **HIGH — likely FAIL.** Ollama image + model pull alone blows 90s; postgres `start_period` + `depends_on: service_healthy` adds 10–30s even warm | Bad: 2nd machine must also pull GBs; GPU flags diverge (`--gpus=all` vs `:rocm` vs CPU); volume-perf traps on Win/Mac | NO — `git clone; docker compose up` is 2 cmds but wall-time is 5–30 min cold, plus `ollama pull <model>` hidden 3rd+ step | **Highest** |
| **B. Single-process (2× uvicorn + SQLite, no Docker) ✅ RECOMMENDED** | ~5–15 min (`python -m venv; pip install -r requirements.txt; uvicorn …`) | **LOW — passes.** No pulls, no healthcheck gates; T1 = process spawn + lazy model load | Excellent: `git clone; pip install; run.bat` works on any spare laptop, no admin/Docker Desktop, no daemon | **YES — exactly 3:** `git clone <url>`, `pip install -r requirements.txt`, `uvicorn app:app` (or `run.bat`) | Lowest |
| C. Nix (`flake.nix` devShell) | 20–60 min first pin (Nix install + first cache/build; cache-miss builds from source) | Medium: no container pulls, but first `nix develop` can build — misses 90s cold | Good once pinned, terrible for a judge who doesn't have Nix | NO — requires Nix install (cmd 0) + learning curve; overkill for Python+SQLite where `.nvmrc/pyenv+requirements` already pins enough | Medium — solves reproducibility, adds onboarding friction |
| D. Devcontainers (VS Code + Docker) | 30–90+ min (Docker + image build + extensions) | HIGH — still Docker pulls + builds under the hood, plus editor attach | Worst for hot-spare: needs VS Code + extension + Docker all working | NO — `clone; open in VS Code; reopen in container` is 3 clicks but 10+ min wall-time; Codespaces variant needs network+quota | High — compose problems + IDE coupling |
| E. Managed DBs (Neon/Supabase Postgres + Upstash Redis) | ~10–20 min (provision + paste `DATABASE_URL`/`REDIS_URL`) | Medium: removes local DB boot, but adds network + cold-start (Neon scale-to-zero) + secrets setup; offline demo dies without net | Mixed: spare works if secrets shared, dead if no Wi-Fi / expired token / IP-allowlist | MAYBE 3 cmds but hidden step 0 (create project, copy keys); judge won't do this | Medium — trades Docker complexity for network/secrets fragility |

## Why Docker-compose is the D3-eater here

1. **Ollama dominates the bill.** The `ollama/ollama` image path is officially Docker-supported (`docker run -d -v ollama:/root/.ollama -p 11434:11434 ollama/ollama`, GPU via `--gpus=all`, AMD via `:rocm`), but the image is large (reporter: ">1 GB larger than 0.3.10" regression chatter) and the *model weights* are a second, much larger pull (`ollama pull llama3.2:1b…`). Fresh-clone cold start = image pull + model pull + model load into memory. That alone breaks any 90s T1 tripwire. Sources: Ollama official Docker image docs; Ollama Docker-hub overview; "pull-first Ollama image" pattern; WSL/volume memory-allocation slowness reports.
2. **Compose startup-order tax is real.** `depends_on` alone does NOT wait for readiness — classic race is Postgres still ~10s from accepting connections when `api` starts. The correct fix is `depends_on: condition: service_healthy` + `healthcheck: pg_isready` / `redis-cli ping` with `start_period` (official Docker docs pattern: postgres `start_period: 30s, interval: 10s`; common recipe `interval: 5s, start_period: 10s`). That correctness costs seconds on every boot and hangs the whole graph if one healthcheck is misconfigured. Solo dev pays orchestration tax for 2 processes that could just retry-connect.
3. **Solo-dev overhead consensus.** "If You're a Solo Dev, You Don't Need Docker" (HackerNoon) + "Docker Compose Is Holding Back Your Local Development" + "Why We Stopped Using Docker Compose in 2025" (fragile networking, no secrets, dev/stage drift) all converge: for a single owner, native run is faster; containerize at deploy, not at dev. Docker Desktop on Win/Mac adds VM + volume-mount I/O pain that Nix-native and single-process avoid.
4. **Nix/devcontainers don't save D3.** Nix gives true content-addressed reproducibility vs Docker's merely reusable images (`apt-get upgrade` non-determinism; `latest` tag drift), but Nix installs slowly, builds from source on cache miss, and its reproducibility story is weakest exactly for Python/JS ecosystems with their own lockfiles. Devcontainers are *still Docker* plus editor coupling (VS Code `devcontainer.json` + `dockerComposeFile`), so they inherit all of A's cold-start. Both are wrong for a 3-day solo demo with a 90s tripwire.
5. **Managed DBs don't save D3 either.** Neon (serverless Postgres, scale-to-zero, branching) + Supabase (Postgres+auth/storage) + Upstash (serverless Redis) remove local `postgres`/`redis` containers, but substitute network dependency, scale-to-zero cold starts, second vendors/bills, and secret distribution. Great for preview/test branching; bad as the *only* demo path in a judging room with unknown Wi-Fi. Self-hosted-vs-managed 2026 breakdowns agree: managed wins on ops, loses on offline resilience and setup-step-0.

## What to do instead (concrete)

- **Golden path (judge + hot spare): single-process.**
  - `git clone <repo>` → `pip install -r requirements.txt` → `run.bat` (or `uvicorn app:app --port 8000` + second worker process). SQLite file auto-creates. No Docker, no `DATABASE_URL`, no `REDIS_URL`.
  - Keep Redis usage behind an interface with in-process fallback (dict/queue) so `redis` is optional, not required, in dev.
  - Lazy-load / stub the LLM: T1 must not block on Ollama model load. Gate Ollama behind `LLM_BACKEND=stub|ollama` env; default `stub` for T1, flip to `ollama` only when needed.
- **Docker becomes opt-in:** move compose to `compose.opt.yml` (profiles: `api, worker, postgres, redis, ollama`), document as "production-like" alternative. Never let README step 1 require Docker Desktop.
- **T1 tripwire budget (target <60s warm, <90s cold):** single-process ~2–10s; compose-warm ~20–60s (healthchecks); compose-cold ~5–30 min (pulls). Only B clears cold with margin.
- **Hot-spare drill (nightly):** fresh clone on 2nd machine, run the 3 commands, hit T1 with timer. If it needs Docker pull or a cloud key, it fails the drill — fix by deleting the dependency, not documenting it.
- **Judge rerun card (put in README + demo script):**
  ```
  git clone <repo-url> && cd <repo>
  pip install -r requirements.txt
  run.bat   # or: uvicorn app:app --port 8000
  ```

## Sources (8 web searches, min-6 satisfied)

- Docker Compose startup-speed optimization (parallel, healthchecks, config) — oneuptime guide.
- "Docker Compose Is Holding Back Your Local Development" — Stackademic proof piece.
- "Why We Stopped Using Docker Compose in 2025" — fragile networking/secrets/drift.
- Modal/container cold-boot (6–10 min fresh-node) + scale-from-zero context.
- "If You're a Solo Dev, You Don't Need Docker" — HackerNoon native-faster argument.
- Nix vs Docker reproducibility (TheNewStack/Flox: reusable vs reproducible; `apt-get upgrade` non-determinism; `latest` drift; clean-room builds) + Nix-vs-Docker dev-env table (native shell vs VM/volume overhead; cache-miss source builds; weak story for Python/JS).
- Devcontainers vs Compose (devcontainer.json + dockerComposeFile; still Docker underneath; VS Code integration costs).
- Managed Postgres/Redis 2026 (Neon scale-to-zero + branching; Supabase platform; Upstash Redis; self-hosted vs managed cost/reliability; cold-start + second-vendor tradeoffs; Encore comparison).
- Ollama official Docker image (CPU `--gpus` / `:rocm` variants, `-v ollama:/root/.ollama`), Docker Hub overview, image-size regression issue, pull-first image pattern, WSL volume memory slowness.
- SQLite vs Postgres switch signal (single-writer/concurrent-write pressure; prototype-first SQLite stories; Tinybird Postgres-vs-SQLite).
- Compose startup-order official docs (`depends_on: condition: service_healthy`, `pg_isready`, `start_period`) + healthcheck recipes (`redis-cli ping`, `pg_isready -U postgres`).
