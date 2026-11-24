#!/usr/bin/env bash
# Blue-Green cut-over / rollback: point the live Service at the blue or green slot.
#   scripts/bluegreen-switch.sh green    # go live with the new version
#   scripts/bluegreen-switch.sh blue     # instant rollback to the previous version
set -euo pipefail
SLOT="${1:-}"
case "$SLOT" in blue|green) ;; *) echo "usage: $0 blue|green"; exit 1;; esac

kubectl -n aceest rollout status "deployment/aceest-$SLOT" --timeout=120s
kubectl -n aceest patch service aceest-bluegreen \
    -p "{\"spec\":{\"selector\":{\"app\":\"aceest-bg\",\"slot\":\"$SLOT\"}}}"
echo "Live traffic now goes to: $SLOT"
