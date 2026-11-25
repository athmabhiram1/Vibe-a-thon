#!/usr/bin/env bash
# scripts/up.sh — cloud/local boot + warm loop. Golden path needs NO Docker.
# Usage:
#   ./scripts/up.sh local   # DEFAULT: pip install + 2x uvicorn (hr 8001, it 8002) + health probe
#   ./scripts/up.sh opt     # backup: docker compose -f compose.opt.yml --profile opt up --build -d
#   ./scripts/up.sh cloud   # pre-warm loop against $API (backup cloud URL) + open /docs
set -e
MODE=${1:-local}

local_boot() {
  echo "[up] local golden path — 2x uvicorn + SQLite (no Docker)"
  if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
  (uvicorn hr_service.main:app --host 127.0.0.1 --port 8001 & echo $! > /tmp/vibe-hr.pid) || true
  (uvicorn it_service.main:app --host 127.0.0.1 --port 8002 & echo $! > /tmp/vibe-it.pid) || true
  sleep 5
  echo "[up] pids: hr=$(cat /tmp/vibe-hr.pid 2>/dev/null) it=$(cat /tmp/vibe-it.pid 2>/dev/null)"
  ./scripts/prewarm.sh local || true
}

opt_boot() {
  echo "[up] opt profile — compose.opt.yml backup (postgres/redis/ollama). NOT the golden path."
  docker compose -f compose.opt.yml --profile opt up --build -d
  sleep 5
  curl -s -o /dev/null -w "HR [%{http_code} %{time_total}s]\n" "http://localhost:8001/hr/candidates?limit=1" || true
  curl -s -o /dev/null -w "IT [%{http_code} %{time_total}s]\n" "http://localhost:8002/it/tickets/breaches" || true
}

cloud_warm() {
  API=${API:-${1:-}}
  if [ -z "$API" ]; then echo "[up] set \$API to cloud URL (backup only; primary is localhost+ngrok)"; exit 1; fi
  echo "[up] warming $API"
  for i in 1 2 3; do curl -s -o /dev/null -w "[%{http_code} %{time_total}s]\n" "$API/health" || true; sleep 5; done
  (xdg-open "$API/docs" 2>/dev/null || open "$API/docs" 2>/dev/null || true)
}

case "$MODE" in
  local) local_boot ;;
  opt) opt_boot ;;
  cloud) cloud_warm "$2" ;;
  *) echo "usage: $0 [local|opt|cloud <url>]"; exit 1 ;;
esac
