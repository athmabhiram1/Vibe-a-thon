#!/usr/bin/env bash
# scripts/prewarm.sh — warm loop + health probe. Run T-10min at venue + after every boot.
# Probes functional endpoints (no /health assumption): HR candidates + IT breaches, plus /docs + /openapi.json.
# Usage: ./scripts/prewarm.sh [local|cloud <url>]   (default local)
set -e
MODE=${1:-local}
BASE_HR=${HR_BASE_URL:-http://localhost:8001}
BASE_IT=${IT_BASE_URL:-http://localhost:8002}
if [ "$MODE" = cloud ]; then API=${2:-${API:-}}; BASE_HR="$API"; BASE_IT="$API"; fi

echo "[prewarm] HR=$BASE_HR IT=$BASE_IT"
for i in 1 2 3; do
  curl -s -o /dev/null -w "HR /hr/candidates?limit=1 [$i: %{http_code} %{time_total}s]\n" "$BASE_HR/hr/candidates?limit=1" || true
  sleep 2
done
curl -s -o /dev/null -w "HR /openapi.json [%{http_code} %{time_total}s]\n" "$BASE_HR/openapi.json" || true
curl -s -o /dev/null -w "HR /docs [%{http_code} %{time_total}s]\n" "$BASE_HR/docs" || true
for i in 1 2 3; do
  curl -s -o /dev/null -w "IT /it/tickets/breaches [$i: %{http_code} %{time_total}s]\n" "$BASE_IT/it/tickets/breaches" || true
  sleep 2
done
curl -s -o /dev/null -w "IT /it/oncall-coverage?team=support-night [%{http_code} %{time_total}s]\n" "$BASE_IT/it/oncall-coverage?team=support-night" || true
# L1 on-call identity: EMP-014 Kiran Desai (seed SH-08 support-night); CAND-002 converts → EMP-021, laptop LT-1005, breaches T-5001/T-5002/T-5019.
curl -s -o /dev/null -w "IT /openapi.json [%{http_code} %{time_total}s]\n" "$BASE_IT/openapi.json" || true
curl -s -o /dev/null -w "IT /docs [%{http_code} %{time_total}s]\n" "$BASE_IT/docs" || true
# Ollama P2 replica (optional — skip silently if not running; golden path = stub).
# OLLAMA_HOST is a server bind addr (often 0.0.0.0), not a URL — normalize before dialing.
_OLLAMA_RAW="${OLLAMA_HOST:-127.0.0.1:11434}"
case "$_OLLAMA_RAW" in
  *://*) OLLAMA_BASE="$_OLLAMA_RAW" ;;
  *:*)     OLLAMA_BASE="http://$_OLLAMA_RAW" ;;
  *)       OLLAMA_BASE="http://$_OLLAMA_RAW:11434" ;;
esac
OLLAMA_BASE="${OLLAMA_BASE//0.0.0.0/127.0.0.1}"
curl -s -o /dev/null -w "ollama /api/ps [%{http_code} %{time_total}s]\n" "$OLLAMA_BASE/api/ps" || echo "[prewarm] ollama not running (ok — P2 fallback only)"
echo "[prewarm] done. Expect 13 tools baseline, 14 post-discover (11/12 functional-only, health excluded; L1 it_oncall_coverage is the live-add)."
