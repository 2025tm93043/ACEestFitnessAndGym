#!/usr/bin/env bash
# Send N requests to /health and count which application version answered.
#   scripts/test-endpoint.sh http://<host>:8083 40            # canary / rolling / blue-green
#   scripts/test-endpoint.sh http://<host>:8085 40 ua         # A/B: vary the "client" so the split shows
#   scripts/test-endpoint.sh http://<host>:8085 5 hdr B       # A/B: force variant B with the header
set -euo pipefail
URL="${1:?usage: $0 <base-url> [count] [ua|hdr <A|B>]}"
COUNT="${2:-20}"
MODE="${3:-plain}"
VARIANT="${4:-B}"
for i in $(seq 1 "$COUNT"); do
    case "$MODE" in
        ua)  curl -s -A "client-$i" "$URL/health" ;;
        hdr) curl -s -H "X-Variant: $VARIANT" "$URL/health" ;;
        *)   curl -s "$URL/health" ;;
    esac
    echo
done | sed -n 's/.*"version":"\([^"]*\)".*/version \1/p' | sort | uniq -c
