#!/usr/bin/env bash
# Build every released version (git tag vX.Y.Z) and push it to Docker Hub as
# <user>/aceest-fitness:X.Y.Z, plus :latest for the newest one.
#
#   docker login                       # once
#   export DOCKERHUB_USER=<your docker hub user>
#   scripts/push-all-versions.sh        # all tags
#   scripts/push-all-versions.sh v3.2.4 # only the listed tags
#
# CONTAINER_CLI=podman works too. DRY_RUN=1 only prints the commands.
# Old tags (before the Dockerfile existed) are built with the CURRENT Dockerfile.
set -euo pipefail
: "${DOCKERHUB_USER:?set DOCKERHUB_USER to your Docker Hub username}"
CLI="${CONTAINER_CLI:-docker}"
REPO="$DOCKERHUB_USER/aceest-fitness"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
run() { echo "+ $*"; [ "${DRY_RUN:-0}" = "1" ] || "$@"; }

cd "$ROOT"
if [ "$#" -gt 0 ]; then TAGS="$*"; else TAGS="$(git tag -l 'v*' --sort=v:refname)"; fi
NEWEST="$(git tag -l 'v*' --sort=v:refname | tail -1)"
WORK="$(mktemp -d)"
trap 'git worktree prune; rm -rf "$WORK"' EXIT

for TAG in $TAGS; do
    VERSION="${TAG#v}"
    DIR="$WORK/$VERSION"
    git worktree add --detach -q "$DIR" "$TAG"
    cp "$ROOT/Dockerfile" "$ROOT/.dockerignore" "$DIR/"
    echo "=== $TAG -> $REPO:$VERSION"
    run "$CLI" build --target runtime -t "$REPO:$VERSION" "$DIR"
    run "$CLI" push "$REPO:$VERSION"
    if [ "$TAG" = "$NEWEST" ]; then
        run "$CLI" tag "$REPO:$VERSION" "$REPO:latest"
        run "$CLI" push "$REPO:latest"
    fi
    git worktree remove --force "$DIR"
done
echo "Done. Check https://hub.docker.com/r/$REPO/tags"
