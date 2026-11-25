#!/usr/bin/env bash
# scripts/share.sh — ngrok share mirror. Primary is ALWAYS localhost; this only mirrors it.
# Venue rule: if ngrok drops, keep demoing on localhost without pause (kill-network drill <90s to fallback).
# Usage:
#   NGROK_DOMAIN=<your-dev-domain> ./scripts/share.sh          # single-domain: multiplex hr+it
#   NGROK_DOMAIN_HR=.. NGROK_DOMAIN_IT=.. ./scripts/share.sh both  # two domains via ngrok.yml
#   ./scripts/share.sh hr   # hr :8001 only
set -e
WHAT=${1:-single}
case "$WHAT" in
  single)
    if [ -z "${NGROK_DOMAIN:-}" ]; then echo "[share] set NGROK_DOMAIN (1 free dev domain: https://dashboard.ngrok.com/domains)"; exit 1; fi
    echo "[share] mirroring hr :8001 on https://$NGROK_DOMAIN (it :8002 stays localhost)"
    exec ngrok http 8001 --domain="$NGROK_DOMAIN"
    ;;
  both)
    echo "[share] starting ngrok.yml tunnels hr(:8001) + it(:8002)"
    exec ngrok start --config ngrok.yml hr it
    ;;
  hr)
    exec ngrok http 8001 ${NGROK_DOMAIN:+--domain="$NGROK_DOMAIN"}
    ;;
  it)
    exec ngrok http 8002 ${NGROK_DOMAIN:+--domain="$NGROK_DOMAIN"}
    ;;
  *) echo "usage: $0 [single|both|hr|it]"; exit 1 ;;
esac
