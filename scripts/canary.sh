#!/usr/bin/env bash
# Canary helper (traffic share = canary replicas / total replicas).
#   scripts/canary.sh weight 2     # 2 canary pods + 4 stable  => about 33% canary
#   scripts/canary.sh promote      # stable takes the canary image, canary scaled to 0
#   scripts/canary.sh abort        # rollback: canary scaled to 0, stable untouched
set -euo pipefail
CMD="${1:-}"
case "$CMD" in
    weight)
        kubectl -n aceest scale deployment/aceest-canary --replicas="${2:?usage: $0 weight <canary-replicas>}"
        ;;
    promote)
        IMAGE="$(kubectl -n aceest get deployment aceest-canary -o jsonpath='{.spec.template.spec.containers[0].image}')"
        kubectl -n aceest set image deployment/aceest-stable aceest="$IMAGE"
        kubectl -n aceest rollout status deployment/aceest-stable --timeout=180s
        kubectl -n aceest scale deployment/aceest-canary --replicas=0
        echo "Promoted $IMAGE to stable"
        ;;
    abort)
        kubectl -n aceest scale deployment/aceest-canary --replicas=0
        echo "Canary removed, all traffic on stable"
        ;;
    *) echo "usage: $0 weight <n>|promote|abort"; exit 1;;
esac
kubectl -n aceest get pods -l app=aceest-canary -L track
