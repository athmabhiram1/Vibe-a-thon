# 05-deploy VERIFY — Kill Render $7 Primary (vs Railway / HF / Fly / Vercel+Netlify / localhost+ngrok)

> Verifies `research/build/05-deploy.md` (§0 solo default: "Render $7 + local mirror"). **Verdict: REJECT Render $7 as primary.** New primary: **localhost compose + ngrok tunnel for judging; cloud URL only as backup (Fly.io autostart or Render Free).** Saves $7–13/mo, kills the 15-min-sleep demo risk instead of paying to hide it.

## 1. Head-to-head (FastAPI + MCP demo lens)

| Axis | Render | Railway | HF Spaces Docker | Fly.io | Vercel / Netlify funcs | localhost + ngrok |
|---|---|---|---|---|---|---|
| **Cold start** | Free: sleep 15 min idle → ~25–60s wake. Starter $7 = no sleep. | Free/Trial: sleep 5–10 min idle → slow wake / 502. Hobby $5 always-on. | Free CPU: sleep after 48h idle (community reports 1–2h); paid GPU never sleeps by default = bill shock. Docker rebuild on every push = minutes. ZeroGPU ≠ FastAPI (Gradio-only). | autostop/autostart: **~2s+ cold start** (best in class). Scale-to-zero supported; stopped machines still billed $0.15/GB-mo rootfs. | Vercel: FastAPI → single serverless fn, 10s Hobby timeout (60s Pro, 900s Ent), 250 MB unzip cap. Cold import penalty on heavy deps. Netlify: **no runtime Python** (build-time only) — disqualified. | **Zero.** Uvicorn already running on :8000. ngrok tunnel adds ~50–200 ms, no sleep. |
| **$PORT binding** | MUST bind `0.0.0.0:$PORT` (default 10000). Reserved: 18012/18013/19099. One public port/svc. `healthCheckPath: /health` in render.yaml. Mismatch = #1 boot-crash. | `$PORT` dynamic + private networking. `railway.json` healthcheckPath + `hyperhorn --bind ":::$PORT"`. No public URL until Generate Domain. | MUST `0.0.0.0:7860`, `sdk: docker` + `app_port: 7860`, non-root `USER user`, single foreground proc. 30-min startup health timeout kills slow weight downloads. | `fly.toml [[services]] internal_port` + `$PORT` handling; autostart config per-machine. Most flexible, most knobs. | No ports at all — `api/index.py` handler export. SSE/streaming MCP flaky under 10s cap. | Trivial: `uvicorn --port 8000`. `ngrok http 8000` — no env dance. |
| **Free-tier sleep / bans** | 750h/mo free but sleeps; free Postgres **expires after 30 days** (then $6/mo). UptimeRobot ping mitigates but violates spirit + still slow. | Trial: $5 one-time, 30 days, then containers STOP. Free: $1/mo credit ≈ one 0.5 GB svc, 1 project, no custom domain. Peak-hour free deploy bans reported. | 2026: free CPU Basic effectively gone for new Spaces; free = 2× ZeroGPU apps (acct 30d+, 5 GPU-min/day). Docker Spaces need paid plan. | **No free tier 2026.** <$5/mo waived. Trial = 7 days or 2 VM-hours. Cheapest real box ~256 MB ≈ $2/mo + egress → $8–25/mo realistic. | Vercel Hobby generous but function timeouts kill MCP long-poll; commercial-use restrictions on Hobby. | ngrok Free: 20k req/mo, 1 GB out, 1 dev domain, browser interstitial warning page. No sleep, no ban — laptop is the server. |
| **Postgres add-on** | `fromDatabase` blueprint easy; free 30-day clock is the trap → $6/mo Mini. Overkill for demo (sqlite suffices). | 1-click Postgres + private `DATABASE_URL`, volume persistence; but meters 24/7 unless Serverless-sleep (don't sleep DBs). Blows $5 credit fast. | No native PG; must use external Neon/Supabase over egress. | Managed Postgres **Starter $72/mo** — disqualifies for demo. Self-host PG on volume = ops burden. | Neon/Supabase external only; serverless connection-pooling required (PgBouncer). | `sqlite:///./demo.db` in compose — zero cost, zero latency, survives airplane mode. Promote to PG only if judges ask. |
| **Pre-warm story** | Cron/UptimeRobot `GET /health` q10min + keep `/docs` tab open. Still 30–60s if missed. | Same cron; Serverless wake can 502 first hit — need retry loop. | Keep-alive GH Action ping; wake 60s+; ZeroGPU queue priority paywalled. | `min_machines_running=1` (pay) OR scheduled ping (runhooks) keeps 1 warm; 2s wake means even cold is stage-safe. | No warm story — scale-to-one still cold-imports; provisioned concurrency = $$$. | No warm needed. `scripts/up.sh local` + `ollama ps` check. |
| **Venue Wi-Fi survival** | Dies if captive portal blocks or venue throttles onrender.com. Hotspot fallback still hits public internet. | Same as Render + usage-burn anxiety on hotspot. | Same + hf.space often blocked by corp filters. | Same (any public URL needs uplink). | Same. | **Wins outright.** Pure `localhost:8000` + Ollama works with Wi-Fi OFF. ngrok needs uplink for share URL only; judging continues on localhost even if ngrok drops. Carry `curl` equivalents for every Inspector click (build §5). |

## 2. Why Render $7 primary dies

1. **Pays to hide, not fix, the risk.** $7/mo Starter ($13 with PG) buys no-sleep on a URL judges don't need — they sit next to your laptop. Same $7 funds 0 cold starts if spent on nothing (localhost is free).
2. **Free Postgres 30-day expiry** (verified 2026) turns "cheapest predictable URL" into a demo-week time bomb. Build doc assumes free DB persists — it doesn't.
3. **PORT/health-check fragility** is the #1 boot-crash class (`127.0.0.1:8000` hardcode, `main:app` path drift, missing uvicorn). Localhost removes the class entirely.
4. **Venue Wi-Fi is the real SLA**, not uptime. Every cloud pick (including paid Render) fails closed when the projector room has captive-portal DNS. Localhost fails open.
5. **Pre-warm is choreography debt**: cron + T-10min curl loop + golden.mp4 cover dance exists only to mask 30–60s free-tier wake. Fly wakes in ~2s; localhost in 0s.

## 3. New topology (replaces build §0 decision table)

```
Judges see:  localhost:8000 (/docs + Inspector --cli)  ← PRIMARY, zero cold start
             └─ ngrok dev-domain URL (1 stable URL, free) ← shareable mirror, same laptop
Cloud backup: Fly.io autostart machine (2s wake) OR Render Free (wake + golden.mp4 cover)
P0: golden.mp4 on laptop + USB always (unchanged)
```

- **Primary:** `docker compose up --build` (api:8000 + ollama:11434) → `ngrok http 8000 --domain=<your-dev-domain>` . Claim dev domain once (free, 1 included); paid Hobbyist only if interstitial warning page embarrasses you in front of judges.
- **Backup cloud (pick ONE, free):** Fly.io with `auto_stop_machines=true, auto_start_machines=true` — 2s wake beats Render 30–60s; or keep existing Render Free blueprint with `healthCheckPath` + cron warmer. Do NOT pay $7.
- **DB:** sqlite in compose. Add Neon/Supabase only if a judge explicitly asks "where's Postgres" — answer: `DATABASE_URL` swap, `/readyz` gate already abstracts it.
- **Vercel/Netlify:** rejected for FastAPI+MCP (10s timeout, 250 MB cap, no Python runtime on Netlify). Use only for static slide site if needed.
- **HF Spaces:** rejected unless story is weights/GPU (needs paid Docker compute + Gradio rewrite for ZeroGPU). Keep only as narrative slide.

## 4. Pre-warm + venue drill (amended)

1. Night before: `ollama pull qwen2.5:7b && ollama create demo-qwen-8k -f Modelfile.local-qwen`; `docker compose up --build -d`; `curl localhost:8000/health && curl localhost:8000/readyz`.
2. Claim + test ngrok dev domain over phone hotspot (captive-portal bypass rehearsal). Note interstitial: first load → Click "Visit Site".
3. T-10min at venue: open `/docs` localhost tab (no warmer needed); start ngrok in Terminal 1; `golden.mp4` queued in VLC.
4. Drill: airplane-mode + hotspot-only → P2 local tool result <90s; kill ngrok mid-demo → continue on localhost without pause.
5. If cloud backup used (Fly): leave 1 ping `while true; do curl $API/health; sleep 300; done` running; Fly wake ~2s needs no video cover.

## 5. What to commit (delta vs build §7)

Keep: `Dockerfile` (unified `${PORT:-8000}`), `docker-compose.yml`, `Modelfile.local-qwen`, `scripts/up.sh`, `scripts/prewarm.sh`.
Add: `ngrok.yml` (dev domain) + `scripts/share.sh` (`ngrok http 8000 --domain=$NGROK_DOMAIN`).
Demote: `render.yaml` → `render.backup.yaml` (free plan, no $7 dependency); `railway.json` only if PG/worker story needed. Delete HF `Dockerfile.hf` unless GPU narrative confirmed.

## Sources (10 searches, Nov 2026)

- Render free spin-down 15 min; Starter $7 no-sleep; PORT default 10000 + 0.0.0.0 bind; free PG 30-day clock — render.com/docs (web-services, free, pricing), livemy/temps/expresstech 2026 pricing roundups.
- Railway: Free $0 ($1 credit) / Trial $5 one-time 30d / Hobby $5 incl $5 usage; sleep 5–10 min; per-second CPU/RAM — railway.com/pricing, livemy, nayankyada, temps 2026.
- HF: Docker `sdk: docker, app_port: 7860`; free sleep 48h; 2026 free CPU Basic gone for new Spaces; ZeroGPU Gradio-only, 5 min/day free — huggingface.co/docs, huggingface.health, hackceleration 2026, discuss.hf 177703.
- Fly: no free tier (waive <$5); autostop/autostart ~2s cold; Managed PG $72/mo Starter — fly.io/pricing, docs.fly.io autostop, srvrlss/expresstech 2026.
- Vercel FastAPI → single fn, 10s Hobby/60s Pro, 250 MB cap; Netlify no runtime Python — vercel.com/docs (fastapi, functions/limitations), runxbuild, netlify answers.
- ngrok Free: 20k req/mo, 1 GB out, 1 dev domain, interstitial page, 3 endpoints — ngrok.com/docs pricing-limits, expose.dev 2026.
