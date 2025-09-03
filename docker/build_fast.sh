#!/bin/bash

set -euo pipefail

# Fast path: reuse a prebuilt base image keyed by the Anki commit

ANKI_DIR="../anki"
if git -C "${ANKI_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ANKI_COMMIT=$(git -C "${ANKI_DIR}" rev-parse HEAD)
else
  echo "Error: ${ANKI_DIR} is not a git repository. Please ensure Anki is cloned as a git repo/submodule."
  exit 1
fi

echo "Target Anki commit: ${ANKI_COMMIT}"

if docker image inspect "anki-core:${ANKI_COMMIT}" >/dev/null 2>&1; then
  echo "Using cached base image anki-core:${ANKI_COMMIT}"
else
  echo "Building base image anki-core:${ANKI_COMMIT} (one-time)"
  docker build --no-cache \
    --tag "anki-core:${ANKI_COMMIT}" \
    --build-arg ANKI_COMMIT="${ANKI_COMMIT}" \
    --file Dockerfile.base \
    ..
fi

docker build \
  --tag anki-api \
  --build-arg ANKI_COMMIT="${ANKI_COMMIT}" \
  --file Dockerfile.app \
  ..

docker run -p 5001:5001 --cpus=1 --name anki-api anki-api

