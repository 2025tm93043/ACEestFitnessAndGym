#!/usr/bin/env bash
# Rolling update helper.
#   DOCKERHUB_USER=me scripts/rolling-update.sh update 3.2.4   # zero-downtime upgrade
#   scripts/rolling-update.sh rollback                         # back to the previous revision
#   scripts/rolling-update.sh status                           # rollout status + history
set -euo pipefail
CMD="${1:-status}"
case "$CMD" in
    update)
        : "${DOCKERHUB_USER:?set DOCKERHUB_USER}"
        VERSION="${2:?usage: $0 update <version>}"
        kubectl -n aceest set image deployment/aceest-rolling \
            aceest="$DOCKERHUB_USER/aceest-fitness:$VERSION"
        kubectl -n aceest annotate deployment/aceest-rolling \
            kubernetes.io/change-cause="update to $VERSION" --overwrite
        if ! kubectl -n aceest rollout status deployment/aceest-rolling --timeout=120s; then
            echo "Rollout failed - reverting to the last stable revision"
            kubectl -n aceest rollout undo deployment/aceest-rolling
            exit 1
        fi
        ;;
    rollback)
        kubectl -n aceest rollout undo deployment/aceest-rolling
        kubectl -n aceest rollout status deployment/aceest-rolling --timeout=120s
        ;;
    status)
        kubectl -n aceest rollout status deployment/aceest-rolling --timeout=5s || true
        kubectl -n aceest rollout history deployment/aceest-rolling
        ;;
    *) echo "usage: $0 update <version>|rollback|status"; exit 1;;
esac
