#!/usr/bin/env bash
# Deploy one (or all) deployment strategies to the current Kubernetes context (Minikube).
#
#   export DOCKERHUB_USER=<your docker hub user>
#   export V_OLD=2.2.4      # version that is "live" / stable / control   (default 2.2.4)
#   export V_NEW=3.2.4      # version that is new / canary / shadow / B   (default 3.2.4)
#   scripts/k8s-deploy.sh rolling-update|blue-green|canary|shadow|ab-testing|all
#
# DRY_RUN=1 prints the rendered YAML instead of applying it.
set -euo pipefail

STRATEGY="${1:-}"
: "${DOCKERHUB_USER:?set DOCKERHUB_USER to your Docker Hub username}"
export DOCKERHUB_USER
export V_OLD="${V_OLD:-2.2.4}"
export V_NEW="${V_NEW:-3.2.4}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STRATEGIES="rolling-update blue-green canary shadow ab-testing"

command -v envsubst >/dev/null || { echo "envsubst missing: sudo dnf install -y gettext  (or apt install gettext-base)"; exit 1; }

apply() {  # render a manifest, substituting ONLY our three variables (nginx $vars stay untouched)
    if [ "${DRY_RUN:-0}" = "1" ]; then
        echo "---"; envsubst '${DOCKERHUB_USER} ${V_OLD} ${V_NEW}' < "$1"
    else
        envsubst '${DOCKERHUB_USER} ${V_OLD} ${V_NEW}' < "$1" | kubectl apply -f -
    fi
}

deploy() {
    local dir="$ROOT/k8s/$1"
    [ -d "$dir" ] || { echo "unknown strategy: $1 (choose: $STRATEGIES all)"; exit 1; }
    echo ">>> deploying $1  (old=$V_OLD new=$V_NEW image=$DOCKERHUB_USER/aceest-fitness)"
    for file in "$dir"/*.yaml; do apply "$file"; done
}

if [ -z "$STRATEGY" ]; then echo "usage: $0 {$STRATEGIES|all}"; exit 1; fi

apply "$ROOT/k8s/namespace.yaml"
if [ "${DRY_RUN:-0}" != "1" ]; then
    # secrets are created from your shell, never committed to git
    if ! kubectl -n aceest get secret aceest-secrets >/dev/null 2>&1; then
        kubectl -n aceest create secret generic aceest-secrets \
            --from-literal=secret-key="${ACEEST_SECRET_KEY:-$(head -c 24 /dev/urandom | base64)}" \
            --from-literal=admin-password="${ACEEST_ADMIN_PASSWORD:-admin}"
    fi
fi

if [ "$STRATEGY" = "all" ]; then
    for s in $STRATEGIES; do deploy "$s"; done
else
    deploy "$STRATEGY"
fi

if [ "${DRY_RUN:-0}" != "1" ]; then
    kubectl -n aceest get deploy,svc
fi
